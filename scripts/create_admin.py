"""Create or reset an Admin account directly in MongoDB."""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from app.web_mvp.auth import hash_password
from app.web_mvp.config import DATABASE_NAME, MONGODB_URI

ADMIN_NAME = "System Administrator"
ADMIN_EMAIL = "admin@rgmcet.edu.in"
ADMIN_PASSWORD = "AdminPass123!"

async def create_admin(name=ADMIN_NAME, email=ADMIN_EMAIL, password=ADMIN_PASSWORD):
    if not MONGODB_URI:
        print("ERROR: MONGODB_URI is not set in .env")
        sys.exit(1)

    from motor.motor_asyncio import AsyncIOMotorClient

    print(f"Connecting to database: {DATABASE_NAME}...")
    client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        print(f"ERROR: Cannot connect to MongoDB: {exc}")
        sys.exit(1)

    db = client[DATABASE_NAME]
    email_clean = email.lower().strip()

    existing = await db.users.find_one({"email": email_clean})
    password_hash = hash_password(password)

    if existing:
        await db.users.update_one(
            {"email": email_clean},
            {
                "$set": {
                    "role": "admin",
                    "approval_status": "APPROVED",
                    "password_hash": password_hash,
                    "name": name,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        print(f"\n[SUCCESS] Updated existing user '{email_clean}' to role=admin with the new password.")
    else:
        user_id = f"USER-{uuid4().hex[:12].upper()}"
        doc = {
            "user_id": user_id,
            "name": name,
            "email": email_clean,
            "password_hash": password_hash,
            "role": "admin",
            "approval_status": "APPROVED",
            "department": "Administration",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(doc)
        print(f"\n[SUCCESS] Created new admin user '{email_clean}' (ID: {user_id}).")

    print("\n--- Admin Login Credentials ---")
    print(f"Email:    {email_clean}")
    print(f"Password: {password}")
    print("Role:     admin")
    print("--------------------------------")

    client.close()

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else ADMIN_EMAIL
    password = sys.argv[2] if len(sys.argv) > 2 else ADMIN_PASSWORD
    name = sys.argv[3] if len(sys.argv) > 3 else ADMIN_NAME
    asyncio.run(create_admin(name=name, email=email, password=password))
