from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal
from datetime import datetime

class CategoryCreate(BaseModel):
    """Модель для создания и обновления категории. Используется в PUT и POST запросах"""
    name: str = Field(..., min_length=3, max_length=50, description="Название категории (3-50 символов)")
    parent_id: int | None = Field(None, description="ID родительской категории, если есть")

class Category(CategoryCreate):
    """Модель для ответа с данными категории. Используется в GET запросах"""
    id: int = Field(..., description="Уникальный идентификатор категории")
    is_active: bool = Field(..., description="Активность категории")

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """Модель для создания и обновления товара. Используется в POST и PUT запросах"""
    name: str = Field(..., min_length=3, max_length=100, description="Наименование товара (3-100 символов)")
    description: str | None = Field(None, max_length=500, description="Описание товара (до 500 символов)")
    price: Decimal = Field(..., gt=0, description="Цена товара (больше нуля)", decimal_places=2)
    image_url: str | None = Field(None, max_length=200, description="URL изображения товара")
    stock: int = Field(..., ge=0, description="Количество товара на складе (не отрицательное)")
    category_id: int = Field(..., description="ID категории, к которой относится товар")

class Product(ProductCreate):
    """Модель для ответа с данными товара. Используется в GET-запросах"""
    id: int = Field(..., description="Уникальный идентификатор товара")
    is_active: bool = Field(..., description="Активность товара")
    rating: float

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Модель для создания и обновления пользователя"""
    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символов)")
    role: str = Field(default='buyer', pattern="^(buyer|seller)$", description="Роль: 'buyer', 'seller'")


class UserUpdateAdmin(BaseModel):
    """Модель для обновления данных пользователя (только для администратора)"""
    role: str = Field(default='buyer', pattern="^(buyer|seller|admin)$", description="Роль: 'buyer', 'seller', 'admin'")

class UserSchema(BaseModel):
    """Модель для ответа с данными пользователя"""
    id: int
    email: EmailStr
    is_active: bool
    role: str
    model_config = ConfigDict(from_attributes=True)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class Review(BaseModel):
    """Возвращает полную информацию по отзыву"""
    id: int
    user_id: int
    product_id: int
    comment: str | None
    comment_date: datetime
    grade: int
    is_active: bool

class CreateReview(BaseModel):
    """Модель для создания отзыва"""
    product_id: int
    comment: str | None = None
    grade: int = Field(ge=1, le= 5)

class ProductList(BaseModel):
    """Список пагинации для товаров"""
    items: list[Product] = Field(description="Товары для текущей страницы")
    total: int = Field(ge=0, description="Общее количество товаров")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")

    model_config = ConfigDict(from_attributes=True)