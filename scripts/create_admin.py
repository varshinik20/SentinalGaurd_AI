"""
One-time bootstrap: create the first SUPER_ADMIN account.

Usage:
    python scripts/create_admin.py --email admin@sentinelguard.ai --password "AdminPass123!" --name "Root Admin"
"""
import argparse
import asyncio
import sys
import os
from dotenv import load_dotenv

# Ensure backend directory is in the Python search path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Load .env file from the backend folder
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

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

    # Run the async main function
    asyncio.run(main(args.email, args.password, args.full_name))
