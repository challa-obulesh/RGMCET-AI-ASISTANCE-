#!/usr/bin/env python3
"""
Seed script for RGMCET AI Campus Assistant — Phase 3.

Populates MongoDB with:
  - Verified RGMCET professor records (with official emails where available)
  - Development demo users (student + professor accounts)
  - Demo appointment (clearly labelled as development data)

Usage:
    python scripts/seed_database.py [--drop]

Options:
    --drop    Drop existing data before seeding (WARNING: irreversible)

VERIFIED DATA POLICY:
  Only factual information supported by public RGMCET website is included.
  Email addresses and personal details are only added where officially published.
  Demo/development data is clearly labelled with is_demo=True.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.web_mvp.config import DATABASE_NAME, MONGODB_URI
from app.web_mvp.auth import hash_password


DEMO_STUDENT_EMAIL = "student.demo@rgmcet.dev"
DEMO_STUDENT_PASSWORD = "Demo@Student123"

DEMO_PROFESSOR_EMAIL = "bhaskara.rao@rgmcet.dev"  # Development demo account — not an official email
DEMO_PROFESSOR_PASSWORD = "Demo@Professor123"

# ---------------------------------------------------------------------------
# Verified RGMCET professor records
# Source: https://www.rgmcet.edu.in/cseds_faculty1.php (publicly accessible)
# Only factual designation/department information is included.
# Email addresses are NOT officially published and are therefore omitted.
# ---------------------------------------------------------------------------
VERIFIED_PROFESSORS = [
    {
        "professor_id": "PROF-BHASKARA-001",
        "name": "Dr. B.Bhaskara Rao",
        "department": "CSE Data Science",
        "designation": "Associate Professor & HOD",
        "qualification": "Ph.D.",
        "email": None,  # Not officially published
        "available": True,
        "active": True,
        "verified": True,
        "source": "https://www.rgmcet.edu.in/cseds_faculty1.php",
    },
]

# ---------------------------------------------------------------------------
# Development/demo data — clearly labelled
# ---------------------------------------------------------------------------
DEMO_USERS = [
    {
        "user_id": f"USER-DEMO-STUDENT-001",
        "name": "Demo Student",
        "email": DEMO_STUDENT_EMAIL,
        "password_hash": "",  # filled below
        "role": "student",
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "user_id": f"USER-DEMO-PROF-001",
        "name": "Dr. B.Bhaskara Rao (Demo Account)",
        "email": DEMO_PROFESSOR_EMAIL,
        "password_hash": "",  # filled below
        "role": "professor",
        "professor_id": "PROF-BHASKARA-001",
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]

DEMO_APPOINTMENT = {
    "appointment_id": f"APT-DEMO-{uuid4().hex[:10].upper()}",
    "student_id": "USER-DEMO-STUDENT-001",
    "student_name": "Demo Student",
    "professor_id": "PROF-BHASKARA-001",
    "professor_name": "Dr. B.Bhaskara Rao",
    "date": "2026-10-15",
    "start_time": "10:00",
    "end_time": "10:30",
    "reason": "[DEVELOPMENT DEMO DATA] Project discussion — seed data for testing",
    "status": "PENDING_APPROVAL",
    "slot_reserved": True,
    "is_demo": True,
}


async def seed(drop: bool = False):
    if not MONGODB_URI:
        print("ERROR: MONGODB_URI is not set in .env. Cannot seed without a MongoDB connection.")
        sys.exit(1)

    from motor.motor_asyncio import AsyncIOMotorClient

    print(f"Connecting to MongoDB: {DATABASE_NAME}")
    client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        print(f"ERROR: Cannot connect to MongoDB: {exc}")
        sys.exit(1)

    db = client[DATABASE_NAME]

    if drop:
        print("WARNING: Dropping existing collections...")
        await db.professors.drop()
        await db.users.drop()
        await db.appointments.drop()
        print("Collections dropped.")

    # ---- Seed verified professors ----
    print("\nSeeding verified professor records...")
    for prof in VERIFIED_PROFESSORS:
        doc = {**prof, "created_at": datetime.now(timezone.utc).isoformat()}
        result = await db.professors.update_one(
            {"professor_id": prof["professor_id"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
        status = "inserted" if result.upserted_id else "already exists"
        print(f"  {prof['name']} ({prof['professor_id']}): {status}")

    # ---- Seed demo users ----
    print("\nSeeding demo user accounts (development data)...")
    passwords = {
        DEMO_STUDENT_EMAIL: DEMO_STUDENT_PASSWORD,
        DEMO_PROFESSOR_EMAIL: DEMO_PROFESSOR_PASSWORD,
    }
    for user in DEMO_USERS:
        user_doc = {
            **user,
            "password_hash": hash_password(passwords[user["email"]]),
        }
        result = await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$setOnInsert": user_doc},
            upsert=True,
        )
        status = "inserted" if result.upserted_id else "already exists"
        print(f"  {user['name']} ({user['email']}) — role={user['role']}: {status}")

    # ---- Seed demo appointment ----
    print("\nSeeding demo appointment (development data)...")
    result = await db.appointments.update_one(
        {"appointment_id": DEMO_APPOINTMENT["appointment_id"]},
        {"$setOnInsert": {**DEMO_APPOINTMENT, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    status = "inserted" if result.upserted_id else "already exists"
    print(f"  Demo appointment {DEMO_APPOINTMENT['appointment_id']}: {status}")

    print(f"\nSeed complete. Database: {DATABASE_NAME}")
    print("\nDemo login credentials:")
    print(f"  Student: {DEMO_STUDENT_EMAIL} / {DEMO_STUDENT_PASSWORD}")
    print(f"  Professor: {DEMO_PROFESSOR_EMAIL} / {DEMO_PROFESSOR_PASSWORD}")
    print("\nNOTE: These are development demo accounts, NOT real RGMCET staff.")

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed RGMCET AI Campus Assistant database")
    parser.add_argument("--drop", action="store_true", help="Drop existing data before seeding")
    args = parser.parse_args()
    asyncio.run(seed(drop=args.drop))
