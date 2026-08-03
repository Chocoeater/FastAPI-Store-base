from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.db_depends import get_async_db
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.routers.services import check_category_id, check_product_id
from app.schemas import Product as ProductResponseSchema, ProductCreate as ProductRequestSchema, ProductList

router = APIRouter(prefix="/products", tags=["products"], )

# !TODO вынести фильтрации в pydantic модель
@router.get("/", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_all_products(page: int = Query(1, ge=1),
                           page_size: int = Query(20, ge=1, le=100),
                           category_id: int | None = Query(None, description="ID категории для фильтрации"),
                           min_price: float | None = Query(None, description="Минимальная цена товара"),
                           max_price: float | None = Query(None, description="Максимальная цена товара"),
                           in_stock: bool | None = Query(None, description="Только товара в наличии"),
                           seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
                           db: AsyncSession = Depends(get_async_db)):
    """Возвращает список всех товаров с поддержкой фильтров"""
    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)

    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)
    total = await db.scalar(total_stmt) or 0

    product_stmt = select(ProductModel).where(*filters).order_by(ProductModel.id).offset(
        (page - 1) * page_size).limit(page_size)
    items = (await db.scalars(product_stmt)).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }




@router.post("/", response_model=ProductResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductRequestSchema, db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """Создает новый товар (только для продавцов)"""
    await check_category_id(product.category_id, db)
    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
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
async def update_product(product_id: int, product: ProductRequestSchema, db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """Обновляет товар по его ID (только для текущего продавца)"""
    db_product = await check_product_id(product_id, db)
    await check_category_id(product.category_id, db)
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")

    await db.execute(update(ProductModel).where(ProductModel.id == product_id).values(**product.model_dump()))
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
    await db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False))
    await db.commit()
    await db.refresh(product)
    return product
