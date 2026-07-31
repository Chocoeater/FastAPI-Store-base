import jwt
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, verify_password, create_access_token, get_current_admin, create_refresh_token
from app.config import SECRET_KEY, ALGORITHM
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.routers.services import check_uniq_email, check_user_id
from app.schemas import UserCreate, UserSchema, UserUpdateAdmin, RefreshTokenRequest

router = APIRouter(prefix='/users', tags=['users'])


@router.post('/', response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Регистрация нового пользователя с ролью 'buyer' или 'seller'"""

    await check_uniq_email(user, db)

    db_user = UserModel(email=user.email, hashed_password=hash_password(user.password), role=user.role)

    db.add(db_user)
    await db.commit()
    return db_user


@router.put('/{user_id}', response_model=UserSchema, status_code=status.HTTP_200_OK)
async def update_user(user_id: int, user: UserUpdateAdmin, db: AsyncSession = Depends(get_async_db),
                      current_user: UserModel = Depends(get_current_admin)):
    """Обновляет данные пользователя, только для администраторов"""
    db_user = await check_user_id(user_id, db)
    await db.execute(update(UserModel).where(UserModel.id == user_id).values(**user.model_dump()))
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """Аутентифицирует пользователя и возвращает JWT с email, role и id"""
    result = await db.scalar(
        select(UserModel).where(UserModel.email == form_data.username, UserModel.is_active == True))
    if not result or not verify_password(form_data.password, result.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректные пароль или email",
                            headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={"sub": result.email, "role": result.role, "id": result.id})
    refresh_token = create_refresh_token(data={"sub": result.email, "role": result.role, "id": result.id})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# !TODO вынести этапы проверки в отдельные функции
@router.post('/refresh-token')
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    """Обновляет refresh токен"""
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный refresh-token",
                                          headers={'WWW-Authenticate': 'Bearer'})

    old_refresh_token = body.refresh_token

    try:
        payload = jwt.decode(old_refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get('token_type')
        if email is None or token_type != 'refresh':
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await db.scalar(select(UserModel).where(UserModel.email == email, UserModel.is_active == True))
    if user is None:
        raise credentials_exception

    new_refresh_token = create_refresh_token(data={'sub': user.email, 'role': user.role, 'id': user.id})

    return {'refresh_token': new_refresh_token, 'token_type': 'bearer'}


@router.post('/access_token')
async def refresh_access_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    """Обновляет access токен"""
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный refresh-token",
                                          headers={'WWW-Authenticate': 'Bearer'})

    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get('token_type')
        if email is None or token_type != 'refresh':
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await db.scalar(select(UserModel).where(UserModel.email == email, UserModel.is_active == True))

    if user is None:
        raise credentials_exception

    new_access_token = create_access_token(data={'sub': user.email, 'role': user.role, 'id': user.id})

    return {'access_token': new_access_token, 'token_type': 'bearer'}

