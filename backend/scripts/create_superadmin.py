"""
One-time bootstrap: create the first SUPER_ADMIN account.

Usage:
    python -m scripts.create_superadmin --email admin@company.com --password "..." --name "Admin"

This is intentionally NOT an HTTP endpoint — creating the root account is
an operational/deployment action, not something exposed over the API.
"""
import argparse
import asyncio
import sys

from app.db.session import AsyncSessionLocal
from app.models.user import Role
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate
from app.services.auth_service import AuthService


async def main(email: str, password: str, full_name: str) -> None:
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        existing = await repo.get_by_email(email)
        if existing:
            print(f"User {email} already exists. Aborting.", file=sys.stderr)
            return

        service = AuthService(db)
        user = await service.register(
            UserCreate(
                email=email,
                password=password,
                full_name=full_name,
                role=Role.SUPER_ADMIN,
                department="Platform",
            )
        )
        print(f"Created SUPER_ADMIN: {user.email} ({user.id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the first SUPER_ADMIN user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", required=True, dest="full_name")
    args = parser.parse_args()

    asyncio.run(main(args.email, args.password, args.full_name))
