"""
TASK 3+4: MongoDB Atlas connection test and persistence verification.
Run with: .venv\Scripts\python scripts/test_mongodb_atlas.py
"""
import asyncio
import sys
from dotenv import load_dotenv
import os

load_dotenv(override=True)

MONGODB_URI = os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "rgmcet_ai_assistant")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}

print("=" * 60)
print("PHASE 12 — MONGODB ATLAS VERIFICATION")
print("=" * 60)
print(f"DATABASE_NAME: {DATABASE_NAME}")
print(f"DEMO_MODE: {DEMO_MODE}")
print(f"MONGODB_URI: {'CONFIGURED' if MONGODB_URI.startswith('mongodb') else 'MISSING'}")
print()

if not MONGODB_URI:
    print("FAIL: MONGODB_URI is not configured in .env")
    sys.exit(1)

if DEMO_MODE:
    print("FAIL: DEMO_MODE=true will prevent MongoDB from being used!")
    print("Fix: Set DEMO_MODE=false in .env")
    sys.exit(1)


async def run_tests():
    from motor.motor_asyncio import AsyncIOMotorClient

    results = {}

    # --- TASK 3: Connection Test ---
    print("TASK 3: Testing MongoDB Atlas connection...")
    client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=15000)
    try:
        ping = await client.admin.command("ping")
        results["cluster_reachable"] = ping.get("ok") == 1.0
        print(f"  Ping: {'PASS' if results['cluster_reachable'] else 'FAIL'}")
    except Exception as e:
        results["cluster_reachable"] = False
        print(f"  Ping FAIL: {e}")
        client.close()
        return results

    # Authentication check
    try:
        db = client[DATABASE_NAME]
        await db.list_collection_names()
        results["authentication"] = True
        print("  Authentication: PASS")
    except Exception as e:
        results["authentication"] = False
        print(f"  Authentication FAIL: {e}")

    # Database access
    try:
        collections = await db.list_collection_names()
        results["database_access"] = True
        print(f"  Database access: PASS (collections: {collections or '[empty - new db]'})")
    except Exception as e:
        results["database_access"] = False
        print(f"  Database access FAIL: {e}")

    # Server version (non-sensitive info)
    try:
        build_info = await client.admin.command("buildInfo")
        version = build_info.get("version", "unknown")
        print(f"  MongoDB version: {version}")
    except Exception:
        pass

    # --- TASK 4: Persistence Test ---
    print()
    print("TASK 4: Testing persistence (write/read/delete)...")
    test_collection = db["_verification_test"]
    test_doc = {
        "test_id": "phase12-atlas-verification",
        "purpose": "MongoDB Atlas persistence test",
        "project": "RGMCET AI Campus Assistant",
    }

    # Write
    try:
        result = await test_collection.insert_one(dict(test_doc))
        inserted_id = result.inserted_id
        results["persistence_write"] = True
        print(f"  Write: PASS (id={inserted_id})")
    except Exception as e:
        results["persistence_write"] = False
        results["persistence_read"] = False
        results["persistence_cleanup"] = False
        print(f"  Write FAIL: {e}")
        client.close()
        return results

    # Read back
    try:
        found = await test_collection.find_one({"test_id": "phase12-atlas-verification"})
        results["persistence_read"] = found is not None and found.get("purpose") == test_doc["purpose"]
        print(f"  Read: {'PASS' if results['persistence_read'] else 'FAIL'}")
    except Exception as e:
        results["persistence_read"] = False
        print(f"  Read FAIL: {e}")

    # Cleanup
    try:
        del_result = await test_collection.delete_many({"test_id": "phase12-atlas-verification"})
        results["persistence_cleanup"] = del_result.deleted_count >= 1
        print(f"  Cleanup: {'PASS' if results['persistence_cleanup'] else 'FAIL'} ({del_result.deleted_count} docs deleted)")
    except Exception as e:
        results["persistence_cleanup"] = False
        print(f"  Cleanup FAIL: {e}")

    # Drop test collection
    try:
        await test_collection.drop()
    except Exception:
        pass

    client.close()
    return results


results = asyncio.run(run_tests())

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
all_pass = all(results.values())
for key, val in results.items():
    status = "PASS" if val else "FAIL"
    print(f"  {key}: {status}")

print()
print(f"Overall MongoDB Atlas: {'PASS' if all_pass else 'FAIL'}")
sys.exit(0 if all_pass else 1)
