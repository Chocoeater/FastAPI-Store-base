from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

from app.models import Review as ReviewModel
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.models.cart_items import CartItem as CartItemModel
from app.schemas import CategoryCreate, UserCreate


async def check_parent_id(category: CategoryCreate, db: AsyncSession) -> None:
    """Проверка на существование родительского ID категории"""
    if category.parent_id is not None:
        parent_stmt = select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                                  CategoryModel.is_active == True)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Продукт не найден")

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


async def check_review_id(review_id: int, db: AsyncSession) -> ReviewModel:
    """Проверяет существование отзыва и его активность"""
    review = await db.scalar(select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Отзыв не найден')
    return review


async def update_product_rating(product_id: int, db: AsyncSession):
    """Обновляет рейтинг продукта"""
    result = await db.execute(
        select(func.round(func.avg(ReviewModel.grade), 2)).where(ReviewModel.product_id == product_id,
                                                                 ReviewModel.is_active == True))
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating


async def check_ex_review_user(product_id: int, user_id: int, db: AsyncSession) -> None:
    """Проверяет, оставлял ли пользователь отзыв"""
    db_review = await db.scalar(
        select(ReviewModel).where(ReviewModel.product_id == product_id, ReviewModel.user_id == user_id,
                                  ReviewModel.is_active == True))
    if db_review is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Вы уже оставляли отзыв на товар')


async def ensure_product_available(db: AsyncSession, product_id: int) -> None:
    result = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )
    product = result.first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or inactive",
        )

async def get_cart_item(
    db: AsyncSession, user_id: int, product_id: int
) -> CartItemModel | None:
    result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == user_id,
            CartItemModel.product_id == product_id,
        )
    )
    return result.first()