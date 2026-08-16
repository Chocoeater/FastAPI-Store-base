from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File
from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.db_depends import get_async_db
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.routers.services import check_category_id, check_product_id
from app.schemas import Product as ProductResponseSchema, ProductCreate as ProductRequestSchema, ProductList, \
    ProductPagination, ProductSort
from app.utils.images import save_product_image, remove_product_image




router = APIRouter(prefix="/products", tags=["products"], )


@router.get("/", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_all_products(pagination: ProductPagination = Depends(), db: AsyncSession = Depends(get_async_db)):
    """Возвращает список всех товаров с поддержкой фильтров"""
    if pagination.min_price is not None and pagination.max_price is not None:
        if pagination.max_price < pagination.min_price:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Максимальная цена должна быть больше либо равна минимальной")

    filters = [ProductModel.is_active == True]

    if pagination.category_id is not None:
        filters.append(ProductModel.category_id == pagination.category_id)
    if pagination.min_price is not None:
        filters.append(ProductModel.price >= pagination.min_price)
    if pagination.max_price is not None:
        filters.append(ProductModel.price <= pagination.max_price)
    if pagination.in_stock is not None:
        filters.append(ProductModel.stock > 0 if pagination.in_stock else ProductModel.stock == 0)
    if pagination.seller_id is not None:
        filters.append(ProductModel.seller_id == pagination.seller_id)

    sort_data = {ProductSort.id: ProductModel.id, ProductSort.created_at: ProductModel.created_at}

    order_by = sort_data.get(pagination.sort_by)

    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)
    rank_col = None
    if pagination.search:
        search_value = pagination.search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery('english', search_value)
            filters.append(ProductModel.tsv.op('@@')(ts_query))
            rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label("rank")
            total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    total = await db.scalar(total_stmt) or 0

    if rank_col is not None:
        product_stmt = select(ProductModel, rank_col).where(*filters).order_by(desc(rank_col), ProductModel.id).offset(
            (pagination.page - 1) * pagination.page_size).limit(pagination.page_size)
        result = await db.execute(product_stmt)
        rows = result.all()
        items = [row[0] for row in rows]
    else:
        product_stmt = select(ProductModel).where(*filters).order_by(order_by).offset(
            (pagination.page - 1) * pagination.page_size).limit(pagination.page_size)
        items = (await db.scalars(product_stmt)).all()

    return {"items": items, "total": total, "page": pagination.page, "page_size": pagination.page_size}


@router.post("/", response_model=ProductResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductRequestSchema = Depends(ProductRequestSchema.as_form),
                         image: UploadFile | None = File(None),
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """Создает новый товар (только для продавцов)"""
    await check_category_id(product.category_id, db)

    image_url = await save_product_image(image) if image else None

    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id, image_url=image_url)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.get("/category/{category_id}", response_model=list[ProductResponseSchema], status_code=status.HTTP_200_OK)
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """Возвращает список товаров в указанной категории по ее ID"""
    await check_category_id(category_id, db)
    stmt = select(ProductModel).where(ProductModel.category_id == category_id, ProductModel.is_active == True)
    result = await db.scalars(stmt)
    products = result.all()
    return products


@router.get("/{product_id}", response_model=ProductResponseSchema, status_code=status.HTTP_200_OK)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """Возвращает детальную информацию о товаре по его ID"""
    product = await check_product_id(product_id, db)
    await check_category_id(product.category_id, db)
    return product


@router.put("/{product_id}", response_model=ProductResponseSchema, status_code=status.HTTP_200_OK)
async def update_product(product_id: int,
                         product: ProductRequestSchema = Depends(ProductRequestSchema.as_form),
                         image: UploadFile | None = File(None),
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """Обновляет товар по его ID (только для текущего продавца)"""
    db_product = await check_product_id(product_id, db)
    await check_category_id(product.category_id, db)
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")

    await db.execute(update(ProductModel).where(ProductModel.id == product_id).values(**product.model_dump()))

    if image:
        remove_product_image(db_product.image_url)
        db_product.image_url = await save_product_image(image)

    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """Логически удаляет товар по его ID"""
    product = await check_product_id(product_id, db)
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own products")
    remove_product_image(product.image_url)
    await db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False, image_url=None))
    await db.commit()
    await db.refresh(product)
    return product
