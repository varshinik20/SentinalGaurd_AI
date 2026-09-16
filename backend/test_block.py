import asyncio
from app.services.rag.rag_service import RAGService
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


async def test():
    engine = create_async_engine("sqlite+aiosqlite:///dev_db.db")
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        res = await db.execute(select(User).where(User.email == "admin@sentinelguard.ai"))
        admin = res.scalars().first()
        
        # Test credit card query
        rag = RAGService()
        result = await rag.generate_response(
            query_text="My credit card number is 4111-1111-1111-1111.",
            user=admin,
            db_session=db,
            session_id=None
        )
        print("Decision Verdict:", result["decision"])
        print("Response Content:", result["response"])


if __name__ == "__main__":
    asyncio.run(test())
