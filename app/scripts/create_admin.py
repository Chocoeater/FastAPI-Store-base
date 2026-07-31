import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import hash_password
from app.database import async_session_maker
from app.models.users import User as UserModel

from app.config import ADMIN_EMAIL, ADMIN_PASSWORD


async def create_admin(db: AsyncSession):
    admin = await db.scalar(select(UserModel).where(UserModel.email == ADMIN_EMAIL))
    if admin:
        print('Администратор уже существует')
        return

    admin = UserModel(
        email=ADMIN_EMAIL,
        hashed_password=hash_password(ADMIN_PASSWORD),
        role='admin',
        is_active=True
    )

    try:
        db.add(admin)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    print('Администратор создан')

async def main():
    async with async_session_maker() as session:
        await create_admin(session)


if __name__ == "__main__":
    asyncio.run(main())
