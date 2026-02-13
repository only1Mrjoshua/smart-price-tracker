"""
Seed script:
  - creates an admin user if it doesn't exist
Usage:
  python -m backend.seed
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
from backend.db import get_db, ensure_indexes
from backend.utils.time import utc_now
from backend.services.auth_service import make_password_hash

ADMIN_EMAIL = "sorochijoshua30@gmail.com"
ADMIN_PASSWORD = "LovuLord2022$$"  # change immediately in real use

async def main():
    await ensure_indexes()
    db = get_db()

    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing:
        print("Admin already exists:", ADMIN_EMAIL)
        return

    await db.users.insert_one({
        "name": "System Admin",
        "email": ADMIN_EMAIL,
        "password_hash": make_password_hash(ADMIN_PASSWORD),
        "role": "ADMIN",
        "created_at": utc_now(),
    })
    print("Created admin:", ADMIN_EMAIL)
    print("Password:", ADMIN_PASSWORD)

if __name__ == "__main__":
    asyncio.run(main())
