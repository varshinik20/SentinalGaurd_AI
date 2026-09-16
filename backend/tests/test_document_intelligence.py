import io
import os
import pytest
import openpyxl
import csv
from pathlib import Path
from sqlalchemy import select

from app.services.document_intelligence.text_extractor import TextExtractor
from app.services.document_intelligence.text_cleaner import TextCleaner
from app.services.document_intelligence.text_chunker import TextChunker
from app.services.document_intelligence.document_processor import DocumentProcessor
from app.models.document import Document, DocumentStatus, Classification, Sensitivity
from app.models.document_chunk import DocumentChunk
from app.repositories.document_repository import DocumentRepository


@pytest.fixture
def temp_files_dir(tmp_path):
    """Fixture to provide a temp directory for test files."""
    return tmp_path


def test_text_cleaner():
    cleaner = TextCleaner()
    raw = "\n\nHello   World! \r\n\tThis is a test.  \n\nAnother line. \n"
    cleaned = cleaner.clean(raw)
    assert cleaned == "Hello World!\nThis is a test.\nAnother line."


def test_token_chunker_basic():
    # Since transformers might fallback offline, test the chunker's logic
    chunker = TextChunker(chunk_size=10, chunk_overlap=2)
    text = "one two three four five six seven eight nine ten eleven twelve thirteen"
    chunks = chunker.chunk(text)
    assert len(chunks) > 0
    # verify that chunks have overlap or cover the text
    assert chunks[0] != ""


def test_csv_extraction(temp_files_dir):
    csv_path = temp_files_dir / "test.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Age", "Department"])
        writer.writerow(["Ananya Rao", "29", "Platform"])
        writer.writerow(["Ananya", "17 September 2026", "Singapore"])

    extractor = TextExtractor()
    extracted = extractor.extract(str(csv_path))
    assert "Ananya Rao" in extracted
    assert "17 September 2026" in extracted
    assert "Platform" in extracted


def test_xlsx_extraction(temp_files_dir):
    xlsx_path = temp_files_dir / "test.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aurora"
    ws.append(["Launch Date", "17 September 2026"])
    ws.append(["Budget", "4.2 crore"])
    wb.save(xlsx_path)

    extractor = TextExtractor()
    extracted = extractor.extract(str(xlsx_path))
    assert "17 September 2026" in extracted
    assert "4.2 crore" in extracted
    assert "Sheet: Aurora" in extracted


@pytest.mark.asyncio
async def test_document_processor_pipeline(db_session, temp_files_dir):
    # Setup database dependency session for test
    from app.db.session import engine
    from app.db.base import Base

    # Write a dummy txt file
    txt_path = temp_files_dir / "aurora.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Project Aurora launches on 17 September 2026 with 4.2 crore budget.")

    # Insert document metadata
    doc = Document(
        filename="aurora.txt",
        original_filename="aurora.txt",
        file_type=".txt",
        file_size=len(txt_path.read_bytes()),
        file_hash="dummy_hash_aurora",
        storage_path=str(txt_path),
        content_type="text/plain",
        size_bytes=len(txt_path.read_bytes()),
        department="Finance",
        owner="Ananya Rao",
        classification=Classification.HIGHLY_CONFIDENTIAL,
        sensitivity=Sensitivity.HIGH,
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    # Process document
    processor = DocumentProcessor(db_session)
    result = await processor.process(doc.id)
    assert result["status"] == "READY"
    assert result["chunks_created"] > 0

    # Retrieve chunks and verify attributes
    repo = DocumentRepository(db_session)
    chunks = await repo.get_chunks(doc.id)
    assert len(chunks) == result["chunks_created"]
    assert chunks[0].content_hash is not None
    assert chunks[0].page_number == 1
    assert chunks[0].metadata_json["source_type"] == ".txt"
    assert chunks[0].metadata_json["classification"] == "HIGHLY_CONFIDENTIAL"
