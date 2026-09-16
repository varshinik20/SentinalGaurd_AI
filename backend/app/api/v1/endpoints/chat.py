"""
Chat endpoints.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.chat_session import ChatSession
from app.models.user import User
from app.repositories.chat_session_repository import ChatSessionRepository
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionOut, ChatMessageOut
from app.services.rag.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Secure AI Workspace"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a prompt to the RAG workspace and retrieve the cleared/sanitized response.
    """
    repo = ChatSessionRepository(db)

    # 1. Resolve or create chat session
    session_id = payload.session_id
    if session_id:
        session = await repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found.",
            )
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session.",
            )
    else:
        # Create a new session
        title = payload.message[:30] + "..." if len(payload.message) > 30 else payload.message
        session = ChatSession(
            user_id=current_user.id,
            title=title,
            provider=payload.provider,
        )
        session = await repo.create(session)
        session_id = session.id

    # 2. Run RAG service
    rag_service = RAGService()
    result = await rag_service.generate_response(
        query_text=payload.message,
        user=current_user,
        db_session=db,
        session_id=session_id,
        provider_name=payload.provider,
    )

    # 3. Update session updated_at timestamp
    session.provider = payload.provider
    await db.commit()

    return result


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all chat sessions for the current user.
    """
    repo = ChatSessionRepository(db)
    return await repo.list_by_user(current_user.id)


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details of a specific chat session.
    """
    repo = ChatSessionRepository(db)
    session = await repo.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session.",
        )
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a specific chat session.
    """
    repo = ChatSessionRepository(db)
    session = await repo.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session.",
        )
    await repo.delete(session)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def list_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve message history for a specific chat session.
    """
    repo = ChatSessionRepository(db)
    session = await repo.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session.",
        )
    return await repo.list_messages(session_id)
