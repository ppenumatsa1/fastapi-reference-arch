#!/usr/bin/env python3
"""Seed baseline User data for local development."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the project root is importable even when the script is invoked directly.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.modules.users.model import User  # noqa: E402

SAMPLE_USERS = (
    {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada.lovelace@example.com",
        "is_active": True,
    },
    {
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace.hopper@example.com",
        "is_active": True,
    },
    {
        "first_name": "Alan",
        "last_name": "Turing",
        "email": "alan.turing@example.com",
        "is_active": False,
    },
)


async def seed() -> None:
    async with async_session_factory() as session:
        created = 0
        for payload in SAMPLE_USERS:
            stmt = select(User).where(User.email == payload["email"])
            result = await session.execute(stmt)
            record = result.scalars().one_or_none()
            if record:
                continue

            session.add(User(**payload))
            created += 1

        if created == 0:
            print("Sample users already seeded; nothing to do.")
            return

        await session.commit()
        print(f"Seeded {created} users.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
