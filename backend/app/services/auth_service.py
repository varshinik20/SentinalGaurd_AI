"""
Authentication business logic. Endpoints stay thin; all decisions
(credential checks, token issuance/rotation, revocation) live here so
they can be reused (e.g. by a future CLI admin tool) and unit tested
without spinning up FastAPI.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserCreate


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    async def register(self, payload: UserCreate) -> User:
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
            department=payload.department,
        )
        return await self.users.create(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated.",
            )
        return user

    async def issue_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role.value, "department": user.department},
        )
        refresh_jwt, jti, expires_at = create_refresh_token(subject=str(user.id))
        await self.refresh_tokens.create(
            RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
        )
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()
        return TokenResponse(access_token=access, refresh_token=refresh_jwt)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token."
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token."
            )

        jti = payload["jti"]
        stored = await self.refresh_tokens.get_by_jti(jti)
        if not stored or not self.refresh_tokens.is_valid(stored):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or expired.",
            )

        # Rotate: revoke the old one, issue a brand new pair
        await self.refresh_tokens.revoke(jti)
        user = await self.users.get_by_id(stored.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active."
            )
        return await self.issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            return  # already invalid; nothing to revoke
        jti = payload.get("jti")
        if jti:
            await self.refresh_tokens.revoke(jti)
