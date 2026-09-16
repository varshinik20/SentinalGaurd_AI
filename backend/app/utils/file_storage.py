"""
Local disk storage for uploaded documents.

Kept behind a small function-based interface (not a class with cached
state) so Module 3+ or a future S3-backed implementation can swap in
without touching callers. Reads `settings.UPLOAD_DIR` at call time
(not at import time) so tests can monkeypatch it per-run.
"""
import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def validate_upload(file: UploadFile) -> str:
    """Returns the expected file extension, or raises 400 if disallowed."""
    # Also support fallback checking on file extension if Content-Type is generic (e.g. application/octet-stream)
    content_type = file.content_type
    ext = ALLOWED_CONTENT_TYPES.get(content_type)
    if ext is None and file.filename:
        # Fallback to extension check
        file_ext = Path(file.filename).suffix.lower()
        if file_ext in {".pdf", ".docx", ".txt", ".csv", ".xlsx"}:
            ext = file_ext
    
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Allowed: PDF, DOCX, TXT, CSV, XLSX."
            ),
        )
    return ext


async def save_upload(file: UploadFile, document_id: uuid.UUID, ext: str) -> tuple[str, int, str]:
    """
    Streams the upload to disk in chunks (avoids loading huge files fully
    into memory) under UPLOAD_DIR/{document_id}/{document_id}{ext}.
    Returns (storage_path, size_bytes, file_hash). Enforces MAX_UPLOAD_SIZE_MB.
    """
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    doc_dir = Path(settings.UPLOAD_DIR) / str(document_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    dest_path = doc_dir / f"{document_id}{ext}"

    sha256 = hashlib.sha256()
    size = 0
    try:
        with open(dest_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    out.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit.",
                    )
                out.write(chunk)
                sha256.update(chunk)
    finally:
        await file.close()

    return str(dest_path), size, sha256.hexdigest()


def delete_document_files(document_id: uuid.UUID) -> None:
    doc_dir = Path(settings.UPLOAD_DIR) / str(document_id)
    if doc_dir.exists():
        for f in doc_dir.iterdir():
            f.unlink(missing_ok=True)
        doc_dir.rmdir()
