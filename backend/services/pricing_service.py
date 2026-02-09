from backend.db import get_db
from backend.utils.time import utc_now
from backend.utils.ids import oid_str

def compute_discount_percent(reference_price: float, current_price: float) -> float:
    if reference_price <= 0:
        return 0.0
    return max(0.0, (reference_price - current_price) / reference_price * 100.0)

async def insert_price_point(tracked_product_id, price: float, currency: str):
    db = get_db()
    await db.price_history.insert_one({
        "tracked_product_id": tracked_product_id,
        "timestamp": utc_now(),
        "price": price,
        "currency": currency,
    })

async def create_notification(user_id, tracked_product_id, message: str, channel: str, status: str):
    db = get_db()
    await db.notifications.insert_one({
        "user_id": user_id,
        "tracked_product_id": tracked_product_id,
        "message": message,
        "channel": channel,  # "email" | "in_app"
        "sent_at": utc_now(),
        "status": status,    # "sent" | "failed"
    })

async def evaluate_alerts_and_notify(tracked_product: dict, latest_price: float, currency: str,
                                     send_email_fn):
    """
    Alert rules:
      - target_price: trigger if latest_price <= target_price
      - discount_threshold: trigger if discount% >= threshold AND tracked_product has reference_price
    """
    db = get_db()
    alerts = db.alerts.find({
        "tracked_product_id": tracked_product["_id"],
        "user_id": tracked_product["user_id"],
        "is_active": True,
    })

    async for alert in alerts:
        triggered = False
        reasons = []

        target_price = alert.get("target_price")
        if target_price is not None and latest_price <= float(target_price):
            triggered = True
            reasons.append(f"Price is now {latest_price:.2f} {currency} (<= target {float(target_price):.2f}).")

        discount_threshold = alert.get("discount_threshold")
        reference_price = tracked_product.get("reference_price")
        if discount_threshold is not None and reference_price:
            disc = compute_discount_percent(float(reference_price), latest_price)
            if disc >= float(discount_threshold):
                triggered = True
                reasons.append(f"Discount is {disc:.1f}% (>= {float(discount_threshold):.1f}%).")

        if not triggered:
            continue

        if alert.get("notify_once") and alert.get("has_notified_once"):
            continue

        message = (
            f"Deal alert for '{tracked_product.get('title','(unknown)')}' on {tracked_product.get('platform')}.\n"
            + "\n".join(reasons)
            + f"\nURL: {tracked_product.get('url')}"
        )

        # In-app notification
        try:
            await create_notification(tracked_product["user_id"], tracked_product["_id"], message, "in_app", "sent")
        except Exception:
            # non-fatal
            pass

        # Email notification
        user = await db.users.find_one({"_id": tracked_product["user_id"]})
        if user and user.get("email"):
            try:
                send_email_fn(user["email"], "Smart Price Tracker Alert", message)
                await create_notification(tracked_product["user_id"], tracked_product["_id"], message, "email", "sent")
            except Exception as e:
                await create_notification(tracked_product["user_id"], tracked_product["_id"], message, "email", "failed")

        if alert.get("notify_once"):
            await db.alerts.update_one({"_id": alert["_id"]}, {"$set": {"has_notified_once": True}})
