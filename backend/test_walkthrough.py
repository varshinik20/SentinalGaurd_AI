import asyncio
import os
import shutil
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.db.base import Base
from app.models.document import Document, Classification, Sensitivity, DocumentStatus
from app.models.user import User
from app.services.document_intelligence.document_processor import DocumentProcessor


import hashlib

async def run():
    # 1. Setup paths
    os.makedirs("data/uploads", exist_ok=True)
    src_file = "d:/sentinelguard-ai/data/secret_financials.txt"
    dest_file = "d:/sentinelguard-ai/data/uploads/secret_financials.txt"
    shutil.copy(src_file, dest_file)
    print(f"Copied file to storage path: {dest_file}")

    # Read content metadata
    with open(src_file, "rb") as f:
        file_bytes = f.read()
    file_size = len(file_bytes)
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # 2. Open DB Session
    engine = create_async_engine("sqlite+aiosqlite:///dev_db.db")
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with Session() as db:
        # Get admin user ID
        res = await db.execute(select(User).where(User.email == "admin@sentinelguard.ai"))
        admin = res.scalars().first()
        if not admin:
            print("Admin user not found. Run init_db.py first.")
            return

        # Check if already indexed
        doc_res = await db.execute(select(Document).where(Document.filename == "secret_financials.txt"))
        doc = doc_res.scalars().first()
        
        if not doc:
            doc = Document(
                id=uuid.uuid4(),
                filename="secret_financials.txt",
                original_filename="secret_financials.txt",
                file_type="txt",
                file_size=file_size,
                file_hash=file_hash,
                storage_path=dest_file,
                content_type="text/plain",
                size_bytes=file_size,
                status=DocumentStatus.PENDING,
                classification=Classification.CONFIDENTIAL,
                sensitivity=Sensitivity.HIGH,
                department="Finance",
                owner="Finance Lead",
                uploaded_by=admin.id
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            print(f"Created Document record in DB with ID: {doc.id}")
        else:
            print(f"Document already exists in DB with ID: {doc.id}")

        # 3. Process & index document (Module 3 + Module 4 integration)
        print("Invoking DocumentProcessor pipeline...")
        processor = DocumentProcessor(db)
        await processor.process(doc.id)
        
        # Verify status is READY
        await db.refresh(doc)
        print(f"Extraction Pipeline Complete! Document status is now: {doc.status}")


if __name__ == "__main__":
    asyncio.run(run())
