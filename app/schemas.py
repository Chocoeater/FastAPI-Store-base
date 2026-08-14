from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, EmailStr


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
    role: str = Field(default='buyer', pattern="^(buyer|seller|admin)$",
                      description="Роль: 'buyer', 'seller', 'admin'")


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
    grade: int = Field(ge=1, le=5)


class ProductList(BaseModel):
    """Список пагинации для товаров"""
    items: list[Product] = Field(description="Товары для текущей страницы")
    total: int = Field(ge=0, description="Общее количество товаров")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")

    model_config = ConfigDict(from_attributes=True)


class ProductSort(Enum):
    id = "id"
    created_at = "created_at"


class ProductPagination(BaseModel):
    """Фильтры и пагинация для продуктов"""
    page: int = Field(ge=1, default=1, description="Текущая станица")
    page_size: int = Field(ge=1, le=100, default=10, description="Количество объектов на странице")
    search: str | None = Field(default=None, min_length=1, description="Поиск по названию товара")
    category_id: int | None = Field(default=None, description="ID категории для фильтрации")
    min_price: float | None = Field(default=None, description="Минимальная цена товара")
    max_price: float | None = Field(default=None, description="Максимальная цена товара")
    in_stock: bool | None = Field(default=None, description="Только товара в наличии")
    seller_id: int | None = Field(default=None, description="ID продавца для фильтрации")
    sort_by: ProductSort = Field(default=ProductSort.id)


class CartItemBase(BaseModel):
    product_id: int = Field(description="ID товара")
    quantity: int = Field(ge=1, description="Количество товара")


class CartItemCreate(CartItemBase):
    """Модель для добавления нового товара в корзину."""
    pass


class CartItemUpdate(BaseModel):
    """Модель для обновления количества товара в корзине."""
    quantity: int = Field(..., ge=1, description="Новое количество товара")


class CartItem(BaseModel):
    """Товар в корзине с данными продукта."""
    id: int = Field(..., description="ID позиции корзины")
    quantity: int = Field(..., ge=1, description="Количество товара")
    product: Product = Field(..., description="Информация о товаре")

    model_config = ConfigDict(from_attributes=True)


class Cart(BaseModel):
    """Полная информация о корзине пользователя."""
    user_id: int = Field(..., description="ID пользователя")
    items: list[CartItem] = Field(default_factory=list, description="Содержимое корзины")
    total_quantity: int = Field(..., ge=0, description="Общее количество товаров")
    total_price: Decimal = Field(..., ge=0, description="Общая стоимость товаров")

    model_config = ConfigDict(from_attributes=True)


class OrderItem(BaseModel):
    id: int = Field(..., description="ID позиции заказа")
    product_id: int = Field(..., description="ID товара")
    quantity: int = Field(..., ge=1, description="Количество")
    unit_price: Decimal = Field(..., ge=0, description="Цена за единицу на момент покупки")
    total_price: Decimal = Field(..., ge=0, description="Сумма по позиции")
    product: Product | None = Field(None, description="Полная информация о товаре")

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    id: int = Field(..., description="ID заказа")
    user_id: int = Field(..., description="ID пользователя")
    status: str = Field(..., description="Текущий статус заказа")
    total_amount: Decimal = Field(..., ge=0, description="Общая стоимость")
    created_at: datetime = Field(..., description="Когда заказ был создан")
    updated_at: datetime = Field(..., description="Когда последний раз обновлялся")
    items: list[OrderItem] = Field(default_factory=list, description="Список позиций")

    model_config = ConfigDict(from_attributes=True)

class OrderList(BaseModel):
    items: list[Order] = Field(..., description="Заказы на текущей странице")
    total: int = Field(ge=0, description="Общее количество заказов")
    page: int = Field(ge=1, description="Текущая страница")
    page_size: int = Field(ge=1, description="Размер страницы")

    model_config = ConfigDict(from_attributes=True)