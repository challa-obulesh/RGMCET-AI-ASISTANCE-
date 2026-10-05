"""Small repository boundary used by services; MongoDB is optional in demo mode."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.web_mvp.config import DATABASE_NAME, DEMO_MODE, MONGODB_URI

logger = logging.getLogger(__name__)
_client = None
_database = None
_memory: dict[str, list[dict[str, Any]]] = {}
_using_demo_store = False


def _demo_documents() -> dict[str, list[dict[str, Any]]]:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    return {
        "professors": json.loads((data_dir / "demo_professors.json").read_text(encoding="utf-8")),
        "professor_schedules": json.loads((data_dir / "demo_professor_schedules.json").read_text(encoding="utf-8")),
        "students": [{"student_id": "demo-student", "name": "Demo Student", "is_demo": True}],
        "appointments": [],
        "chat_sessions": [],
        "users": [],
    }


async def init_store() -> None:
    global _client, _database, _memory, _using_demo_store
    if MONGODB_URI and not DEMO_MODE:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient

            _client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=1000)
            _database = _client[DATABASE_NAME]
            await _client.admin.command("ping")
            # Users (authentication)
            await _database.users.create_index("user_id", unique=True)
            await _database.users.create_index("email", unique=True)
            # Professors
            await _database.professors.create_index("professor_id", unique=True)
            await _database.professors.create_index([("name", "text"), ("aliases", "text")])
            await _database.professor_schedules.create_index([("professor_id", 1), ("day", 1)])
            await _database.students.create_index("student_id", unique=True)
            # Appointments
            await _database.appointments.create_index("appointment_id", unique=True)
            await _database.appointments.create_index([("student_id", 1), ("date", -1)])
            await _database.appointments.create_index([("professor_id", 1), ("date", 1), ("status", 1)])
            await _database.appointments.update_many(
                {"status": {"$in": ["PENDING_APPROVAL", "APPROVED"]}, "slot_reserved": {"$exists": False}},
                {"$set": {"slot_reserved": True}},
            )
            await _database.appointments.create_index(
                [("professor_id", 1), ("date", 1), ("start_time", 1)],
                unique=True,
                partialFilterExpression={"slot_reserved": True},
                name="unique_active_professor_slot",
            )
            await _database.chat_sessions.create_index("session_id")

            # Seed official faculty records into MongoDB if not present
            try:
                data_dir = Path(__file__).resolve().parents[2] / "data"
                demo_profs = json.loads((data_dir / "demo_professors.json").read_text(encoding="utf-8"))
                for p in demo_profs:
                    await _database.professors.update_one(
                        {"professor_id": p["professor_id"]},
                        {"$setOnInsert": p},
                        upsert=True,
                    )
            except Exception as e:
                logger.warning("Could not seed official faculty into MongoDB: %s", e)

            logger.info("Web MVP connected to MongoDB database %s", DATABASE_NAME)
            return
        except Exception as exc:
            logger.warning("MongoDB unavailable for web MVP: %s", exc)
            if _client:
                _client.close()
            _client = None
            _database = None
    if DEMO_MODE:
        _memory = _demo_documents()
        _using_demo_store = True
        logger.warning("Web MVP is using in-memory DEMO DATA; changes will not persist")
    else:
        _memory = {}
        _using_demo_store = False


def reset_demo_data() -> None:
    global _memory
    _memory = _demo_documents()


async def close_store() -> None:
    global _client, _database
    if _client:
        _client.close()
    _client = None
    _database = None


def store_ready() -> bool:
    return _database is not None or _using_demo_store


def demo_mode_active() -> bool:
    return _using_demo_store


async def find_many(collection: str, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    query = query or {}
    if _database is not None:
        cursor = _database[collection].find(query)
        documents = await cursor.to_list(length=500)
        for document in documents:
            document["_id"] = str(document["_id"])
        return documents
    return [dict(item) for item in _memory.get(collection, []) if all(item.get(k) == v for k, v in query.items())]


async def find_one(collection: str, query: dict[str, Any]) -> dict[str, Any] | None:
    results = await find_many(collection, query)
    return results[0] if results else None


async def insert_one(collection: str, document: dict[str, Any]) -> dict[str, Any]:
    item = {**document, "created_at": document.get("created_at", datetime.now(timezone.utc).isoformat())}
    if _database is not None:
        result = await _database[collection].insert_one(item)
        item["_id"] = str(result.inserted_id)
    else:
        item.setdefault("_id", str(uuid4()))
        _memory.setdefault(collection, []).append(item)
    return item


async def insert_appointment(document: dict[str, Any]) -> dict[str, Any] | None:
    """Atomically claim an active slot as the appointment document is inserted."""
    item = {**document, "created_at": document.get("created_at", datetime.now(timezone.utc).isoformat())}
    if _database is not None:
        from pymongo.errors import DuplicateKeyError

        try:
            result = await _database.appointments.insert_one(item)
        except DuplicateKeyError:
            return None
        item["_id"] = str(result.inserted_id)
        return item

    if item.get("slot_reserved"):
        for existing in _memory.setdefault("appointments", []):
            if (
                existing.get("professor_id") == item.get("professor_id")
                and existing.get("date") == item.get("date")
                and existing.get("start_time") == item.get("start_time")
                and existing.get("status") in {"PENDING_APPROVAL", "APPROVED"}
            ):
                return None
    item.setdefault("_id", str(uuid4()))
    _memory.setdefault("appointments", []).append(item)
    return item


async def update_one(collection: str, query: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any] | None:
    fields = {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}
    if _database is not None:
        await _database[collection].update_one(query, {"$set": fields})
        return await find_one(collection, query)
    for item in _memory.get(collection, []):
        if all(item.get(k) == v for k, v in query.items()):
            item.update(fields)
            return dict(item)
    return None


async def transition_appointment(
    appointment_id: str,
    allowed_from: set[str],
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    fields = {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}
    if _database is not None:
        result = await _database.appointments.update_one(
            {"appointment_id": appointment_id, "status": {"$in": list(allowed_from)}},
            {"$set": fields},
        )
        if result.matched_count != 1:
            return None
        return await find_one("appointments", {"appointment_id": appointment_id})
    for item in _memory.get("appointments", []):
        if item.get("appointment_id") == appointment_id and item.get("status") in allowed_from:
            item.update(fields)
            return dict(item)
    return None


async def append_chat_turn(session_id: str, student_id: str, message: str, reply: str, intent: str, language: str) -> None:
    turn = {"user_message": message, "assistant_message": reply, "intent": intent, "language": language}
    if _database is not None:
        await _database.chat_sessions.update_one(
            {"session_id": session_id},
            {
                "$setOnInsert": {"session_id": session_id, "student_id": student_id},
                "$push": {"turns": turn},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
            upsert=True,
        )
        return
    for item in _memory.setdefault("chat_sessions", []):
        if item.get("session_id") == session_id:
            item.setdefault("turns", []).append(turn)
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            return
    _memory.setdefault("chat_sessions", []).append({
        "session_id": session_id,
        "student_id": student_id,
        "turns": [turn],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


async def list_chat_sessions(student_id: str) -> list[dict]:
    query = {"student_id": student_id}
    sessions = await find_many("chat_sessions", query)
    sessions.sort(key=lambda s: s.get("updated_at", s.get("created_at", "")), reverse=True)
    return sessions


async def get_chat_session(session_id: str, student_id: str) -> dict | None:
    return await find_one("chat_sessions", {"session_id": session_id, "student_id": student_id})