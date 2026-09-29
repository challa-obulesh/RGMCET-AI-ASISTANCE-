"""Import the editable demo professor and schedule JSON into MongoDB."""

import asyncio
import json
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

from app.web_mvp.config import DATABASE_NAME, MONGODB_URI


async def seed() -> None:
    if not MONGODB_URI:
        raise RuntimeError("Set MONGODB_URI before importing records into MongoDB")
    data_dir = Path(__file__).resolve().parents[1] / "data"
    client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
        database = client[DATABASE_NAME]
        for filename, collection, key in (
            ("demo_professors.json", "professors", "professor_id"),
            ("demo_professor_schedules.json", "professor_schedules", "schedule_id"),
        ):
            records = json.loads((data_dir / filename).read_text(encoding="utf-8"))
            for record in records:
                await database[collection].replace_one({key: record[key]}, record, upsert=True)
            print(f"Imported {len(records)} records into {collection}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed())