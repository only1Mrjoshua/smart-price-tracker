from fastapi import APIRouter, HTTPException, Depends
from backend.db import get_db
from backend.utils.ids import to_object_id, oid_str
from backend.routers.auth import get_current_user
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
async def list_notifications(user=Depends(get_current_user)):
    """Get all notifications for the current user"""
    db = get_db()
    cursor = db.notifications.find({"user_id": user["_id"]}).sort("sent_at", -1).limit(100)
    out = []
    async for n in cursor:
        out.append({
            "id": oid_str(n["_id"]),
            "tracked_product_id": oid_str(n["tracked_product_id"]) if n.get("tracked_product_id") else None,
            "message": n.get("message"),
            "channel": n.get("channel"),
            "sent_at": n.get("sent_at"),
            "status": n.get("status"),
            "read": n.get("read", False),
            "type": n.get("type", "Price Alert"),
        })
    return out

@router.post("/read-all")
async def mark_all_as_read(user=Depends(get_current_user)):
    """Mark all notifications as read for the current user"""
    logger.info(f"POST /read-all called by user: {user['_id']}")
    db = get_db()
    
    result = await db.notifications.update_many(
        {"user_id": user["_id"], "read": {"$ne": True}},
        {"$set": {"read": True}}
    )
    
    logger.info(f"Marked {result.modified_count} notifications as read")
    return {"ok": True}

@router.delete("/clear-all")
async def clear_all_notifications(user=Depends(get_current_user)):
    """Delete all notifications for the current user"""
    logger.info(f"DELETE /clear-all called by user: {user['_id']}")
    
    db = get_db()
    result = await db.notifications.delete_many({"user_id": user["_id"]})
    
    logger.info(f"Deleted {result.deleted_count} notifications")
    
    return {
        "ok": True, 
        "deleted_count": result.deleted_count
    }

@router.patch("/{notification_id}/read")
async def mark_as_read(notification_id: str, user=Depends(get_current_user)):
    """Mark a single notification as read"""
    logger.info(f"PATCH /{notification_id}/read called")
    
    try:
        nid = to_object_id(notification_id)
    except Exception as e:
        logger.error(f"Invalid notification ID: {notification_id}, error: {e}")
        raise HTTPException(status_code=400, detail="Invalid notification ID")
    
    db = get_db()
    result = await db.notifications.update_one(
        {"_id": nid, "user_id": user["_id"]},
        {"$set": {"read": True}}
    )
    
    if result.matched_count == 0:
        logger.warning(f"Notification not found: {notification_id} for user {user['_id']}")
        raise HTTPException(status_code=404, detail="Notification not found")
    
    logger.info(f"Marked notification {notification_id} as read")
    return {"ok": True}

@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, user=Depends(get_current_user)):
    """Delete a single notification"""
    logger.info(f"DELETE /{notification_id} called")
    
    try:
        nid = to_object_id(notification_id)
    except Exception as e:
        logger.error(f"Invalid notification ID: {notification_id}, error: {e}")
        raise HTTPException(status_code=400, detail="Invalid notification ID")
    
    db = get_db()
    result = await db.notifications.delete_one(
        {"_id": nid, "user_id": user["_id"]}
    )
    
    if result.deleted_count == 0:
        logger.warning(f"Notification not found: {notification_id} for user {user['_id']}")
        raise HTTPException(status_code=404, detail="Notification not found")
    
    logger.info(f"Deleted notification {notification_id}")
    return {"ok": True}