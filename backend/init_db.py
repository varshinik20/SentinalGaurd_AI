import asyncio
import uuid
from app.db.base import Base
from app.models.user import User, Role
from app.core.security import hash_password
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


async def init():
    engine = create_async_engine("sqlite+aiosqlite:///dev_db.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    Session = async_sessionmaker(bind=engine, class_=AsyncSession)
    async with Session() as session:
        from sqlalchemy import select
        res = await session.execute(select(User).where(User.email == "admin@sentinelguard.ai"))
        if not res.scalars().first():
            admin = User(
                id=uuid.uuid4(),
                email="admin@sentinelguard.ai",
                hashed_password=hash_password("AdminPass123!"),
                full_name="Root Administrator",
                role=Role.SUPER_ADMIN,
                department="Platform"
            )
            employee = User(
                id=uuid.uuid4(),
                email="employee@sentinelguard.ai",
                hashed_password=hash_password("UserPass123!"),
                full_name="Standard Employee",
                role=Role.EMPLOYEE,
                department="Marketing"
            )
            session.add(admin)
            session.add(employee)
            await session.commit()
            print("Successfully initialized database and seeded users.")


if __name__ == "__main__":
    asyncio.run(init())
