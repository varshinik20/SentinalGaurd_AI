from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        return result.scalar_one_or_none()

    async def revoke(self, jti: str) -> None:
        await self.db.execute(
            update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True)
        )
        await self.db.commit()

    def is_valid(self, token: RefreshToken) -> bool:
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            # Some backends (e.g. SQLite, used in tests) don't round-trip
            # tzinfo on DateTime(timezone=True) columns; Postgres does.
            # Values are always written in UTC, so it's safe to assume UTC
            # here rather than raise on offset-naive/aware comparison.
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return (not token.revoked) and expires_at > datetime.now(timezone.utc)
