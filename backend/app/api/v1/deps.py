"""
Shared request-scoped dependencies used across every module's endpoints:
- `get_current_user`: decodes the bearer access token, loads the User
- `require_roles(...)`: RBAC guard factory for protecting admin-only routes

Later modules (Vault upload, Chat, Security Explanation) will import
`get_current_user` to know *who* is asking, and the Policy Engine will
read `current_user.role` / `.department` off of it.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import Role, User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    subject = payload.get("sub")
    if subject is None:
        raise credentials_exception

    user = await UserRepository(db).get_by_id(uuid.UUID(subject))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_roles(*allowed_roles: Role):
    """Dependency factory: `Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))`."""

    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return _guard
