from datetime import datetime, timezone, timedelta

import jwt
from fastapi import HTTPException, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.users import User as UserModel

from app.config import SECRET_KEY, ALGORITHM
from app.db_depends import get_async_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
oauth2_cheme = OAuth2PasswordBearer(tokenUrl='users/token')


def hash_password(password: str) -> str:
    """Преобразует пароль в хэш с использованием bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли введенный пароль сохраненному хэшу"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    """Создает JWT access с payload (sub, role, id, exp)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "token_type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    """Создает JWT refresh"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "token_type": "refresh"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_cheme), db: AsyncSession = Depends(get_async_db)):
    """Проверяет JWT и возвращает пользователя из базы"""
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Не удалось проверить учетные данные",
                                          headers={'WWW-Authenticate': 'Bearer'})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get("token_type")
        if email is None or token_type != 'access':
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истек",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.PyJWTError:
        raise credentials_exception
    result = await db.scalar(select(UserModel).where(UserModel.email == email, UserModel.is_active))
    if result is None:
        raise credentials_exception
    return result

async def get_current_seller(current_user: UserModel = Depends(get_current_user)):
    """Проверяет, что пользователь имеет роль 'seller'"""
    if current_user.role != "seller":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Только для продавцов')
    return current_user


async def get_current_admin(current_user: UserModel = Depends(get_current_user)):
    """Проверяет, что пользователь имеет роль 'admin'"""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Только для администраторов')
    return current_user