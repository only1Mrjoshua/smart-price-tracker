from datetime import datetime, timezone, timedelta

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def days_ago(days: int) -> datetime:
    return utc_now() - timedelta(days=days)
