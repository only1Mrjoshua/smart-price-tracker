from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import settings

client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
    global client
    if client is None:
        client = AsyncIOMotorClient(settings.MONGO_URI)
    return client

def get_db():
    return get_client()[settings.MONGO_DB_NAME]

async def ensure_indexes():
    db = get_db()

    await db.users.create_index("email", unique=True)

    await db.tracked_products.create_index(
        [("user_id", 1), ("url", 1)],
        unique=True,
        name="uniq_user_url",
    )
    await db.price_history.create_index(
        [("tracked_product_id", 1), ("timestamp", 1)],
        name="idx_price_history_product_time",
    )
    await db.alerts.create_index([("user_id", 1), ("tracked_product_id", 1)])
    await db.notifications.create_index([("user_id", 1), ("sent_at", -1)])
    await db.jobs_log.create_index([("ran_at", -1)])
    await db.track_requests.create_index([("user_id", 1), ("created_at", -1)])
    await db.track_requests.create_index([("status", 1), ("updated_at", -1)])

