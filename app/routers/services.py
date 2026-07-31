from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.schemas import CategoryCreate, UserCreate


async def check_parent_id(category: CategoryCreate, db: AsyncSession) -> None:
    """Проверка на существование родительского ID категории"""
    if category.parent_id is not None:
        parent_stmt = select(CategoryModel).where(CategoryModel.id == category.parent_id, CategoryModel.is_active == True)
        result = await db.scalars(parent_stmt)
        parent = result.first()
        if parent is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Родительская категория не найдена")


async def check_category_id(category_id: int, db: AsyncSession) -> CategoryModel:
    """Проверка на существование ID категории, возвращает объект-категорию"""
    smtp = select(CategoryModel).where(CategoryModel.id == category_id, CategoryModel.is_active == True)
    result = await db.scalars(smtp)
    category = result.first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Категория не найдена")

    return category


async def check_product_id(product_id: int, db: AsyncSession) -> ProductModel:
    """Проверка на существование ID продукта, возвращает объект-продукт"""
    smtp = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = (await db.scalars(smtp)).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Продукт не найден")

    return product

async def check_uniq_email(user: UserCreate, db: AsyncSession) -> None:
    """Проверка уникальность email"""
    result = await db.scalar(select(UserModel).where(UserModel.email == user.email))
    if result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Такой email уже существует')

async def check_user_id(user_id: int, db: AsyncSession) -> UserModel:
    """Проверяет существование пользователя по его ID"""
    user = await db.scalar(select(UserModel).where(UserModel.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь не найден")
    return user