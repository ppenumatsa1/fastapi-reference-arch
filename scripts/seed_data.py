#!/usr/bin/env python3
"""Seed baseline TODO data for local development."""
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
from app.models.todo import Todo  # noqa: E402

SAMPLE_TODOS = (
    {
        "title": "Wire up FastAPI",
        "description": "Hook routes to services and ensure OpenAPI docs load.",
    },
    {
        "title": "Add Alembic migrations",
        "description": "Verify the todos table exists and migrations run cleanly.",
    },
    {
        "title": "Polish CI",
        "description": "Run lint/format/tests in GitHub Actions before merging.",
    },
)


async def seed() -> None:
    async with async_session_factory() as session:
        created = 0
        for payload in SAMPLE_TODOS:
            stmt = select(Todo).where(Todo.title == payload["title"])
            result = await session.execute(stmt)
            record = result.scalars().one_or_none()
            if record:
                continue

            session.add(Todo(**payload))
            created += 1

        if created == 0:
            print("Sample TODOs already seeded; nothing to do.")
            return

        await session.commit()
        print(f"Seeded {created} todo items.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
