"""
Aggregates every versioned sub-router. Future modules (documents, chat,
security) each add one line here — main.py never needs to change again.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, chat, audit

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
