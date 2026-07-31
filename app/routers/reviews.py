from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_buyer, get_current_user
from app.db_depends import get_async_db
from app.models import Review as ReviewModel
from app.models import User as UserModel
from app.routers.services import check_product_id, update_product_rating, check_review_id
from app.schemas import CreateReview as CreateReviewSchema
from app.schemas import Review as ReviewSchema

router = APIRouter(prefix='/reviews', tags=['reviews'])


@router.get('/', response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """Возвращает список всех отзывов"""
    result = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True))
    reviews = result.all()
    return reviews


@router.get('/{product_id}', response_model=ReviewSchema, status_code=status.HTTP_200_OK)
async def get_product_review(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """Возвращает отзывы по конкретному продукту"""
    await check_product_id(product_id, db)
    result = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == product_id, ReviewModel.is_active == True))
    reviews = result.all()
    return reviews


@router.post('/', response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(review: CreateReviewSchema, db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_buyer)):
    """Создает отзыв"""
    await check_product_id(review.product_id, db)
    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    await update_product_rating(db_review.product_id, db)
    return db_review


@router.delete('/{review_id}', response_model=dict, status_code=status.HTTP_200_OK)
async def delete_review(review_id: int, db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_user)):
    """Помечает отзыв как неактивный"""
    review = await check_review_id(review_id, db)
    if review.user_id != current_user.id or current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Можно удалить только свой отзыв")
    await db.execute(update(ReviewModel).where(ReviewModel.id == review_id).values(is_active=False))
    await db.commit()
    await db.refresh(review)
    await update_product_rating(review.product_id, db)
    return {"message": "Отзыв удален"}