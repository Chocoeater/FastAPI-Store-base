from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.db_depends import get_async_db
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.routers.services import check_category_id, check_product_id
from app.schemas import Product as ProductResponseSchema, ProductCreate as ProductRequestSchema

router = APIRouter(prefix="/products", tags=["products"], )


@router.get("/", response_model=list[ProductResponseSchema], status_code=status.HTTP_200_OK)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """Возвращает список всех товаров"""
    # stmt = select(ProductModel).where(ProductModel.is_active == True)
    stmt = select(ProductModel).join(CategoryModel).where(ProductModel.is_active == True,
                                                          CategoryModel.is_active == True, ProductModel.stock > 0)
    result = await db.scalars(stmt)
    products = result.all()
    return products


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
