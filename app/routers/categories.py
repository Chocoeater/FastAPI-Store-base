from fastapi import APIRouter, Depends, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_admin
from app.db_depends import get_async_db
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.routers.services import check_parent_id, check_category_id
from app.schemas import Category as CategorySchema, CategoryCreate

router = APIRouter(prefix="/categories", tags=["categories"], )


@router.get("/", response_model=list[CategorySchema], status_code=status.HTTP_200_OK)
async def get_all_categories(db: AsyncSession = Depends(get_async_db)):
    """Возвращает список всех категорий товаров"""
    stmt = select(CategoryModel).where(CategoryModel.is_active == True)
    result = await db.scalars(stmt)
    categories = result.all()
    return categories


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_async_db),
                          current_user: UserModel = Depends(get_current_admin)):
    """Создает новую категорию, только для администратора"""
    # Проверка, существует ли parent_id, если указан
    await check_parent_id(category, db)
    # Создание новой категории
    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category


@router.put("/{category_id}", status_code=status.HTTP_200_OK, response_model=CategorySchema)
async def update_category(category_id: int, category: CategoryCreate, db: AsyncSession = Depends(get_async_db),
                          current_user: UserModel = Depends(get_current_admin)):
    """Обновляет категорию по ее ID"""
    # Проверка существования
    db_category = await check_category_id(category_id, db)

    # Проверка существования родительской
    await check_parent_id(category, db)

    # Обновление категории
    update_data = category.model_dump(exclude_unset=True)
    await db.execute(update(CategoryModel).where(CategoryModel.id == category_id).values(**update_data))
    await db.commit()
    await db.refresh(db_category)
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_async_db),
                          current_user: UserModel = Depends(get_current_admin)):
    """Логически удаляет категорию по ее ID"""
    # Проверка на существование
    await check_category_id(category_id, db)

    # Логическое удаление категории

    await db.execute(update(CategoryModel).where(CategoryModel.id == category_id).values(is_active=False))
    await db.commit()

    return {"status": "success", "message": "Категория помечена неактивной"}
