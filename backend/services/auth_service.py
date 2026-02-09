from datetime import timedelta
from backend.utils.security import hash_password, verify_password
from backend.utils.jwt import create_token
from backend.config import settings

def make_password_hash(password: str) -> str:
    return hash_password(password)

def check_password(password: str, password_hash: str) -> bool:
    return verify_password(password, password_hash)

def make_access_token(user_id: str) -> str:
    return create_token(user_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_MINUTES))

def make_refresh_token(user_id: str) -> str:
    return create_token(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_DAYS))
