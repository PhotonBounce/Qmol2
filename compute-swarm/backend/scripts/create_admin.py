#!/usr/bin/env python3
"""
Create an admin user from the CLI.

Usage (inside the API container):
    cd /app
    python scripts/create_admin.py admin@example.com SecureP@ssw0rd!

Or via Docker Compose:
    docker compose -f docker-compose.prod.yml exec api \
        python scripts/create_admin.py admin@example.com SecureP@ssw0rd!
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import AsyncSessionLocal, engine
from app.models import Base, User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import asyncio
from sqlalchemy import select


async def create_admin(email: str, password: str) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"ERROR: User {email} already exists.")
            sys.exit(1)

        user = User(
            email=email,
            hashed_password=pwd_context.hash(password),
            role=UserRole.admin,
            credits_balance=0.0,
            total_credits_spent=0.0,
        )
        db.add(user)
        await db.commit()

        print(f"Admin user created: {email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin user for ComputeSwarm")
    parser.add_argument("email", help="Admin email address")
    parser.add_argument("password", help="Admin password")
    args = parser.parse_args()

    asyncio.run(create_admin(args.email, args.password))


if __name__ == "__main__":
    main()
