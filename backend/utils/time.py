from datetime import datetime, timedelta, timezone

def utc_now():
    """Return current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)

def days_ago(days: int):
    """Return datetime from X days ago as timezone-aware"""
    return datetime.now(timezone.utc) - timedelta(days=days)

def ensure_aware(dt):
    """Ensure datetime is timezone-aware (assume UTC if naive)"""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt