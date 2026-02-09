from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from backend.db import get_db
from backend.utils.time import utc_now
from backend.utils.ids import oid_str
from backend.services.auth_service import make_password_hash, check_password, make_access_token, make_refresh_token
from backend.utils.jwt import safe_decode

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

def get_bearer_token(authorization: str | None):
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

async def get_current_user(authorization: str | None = Header(default=None)):
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = safe_decode(token)
    if not payload or payload.get("typ") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    db = get_db()
    from bson import ObjectId
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/register")
async def register(data: RegisterIn):
    db = get_db()
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    doc = {
        "name": data.name.strip(),
        "email": data.email.lower(),
        "password_hash": make_password_hash(data.password),
        "role": "USER",
        "created_at": utc_now(),
    }
    res = await db.users.insert_one(doc)
    user_id = str(res.inserted_id)

    return TokenOut(
        access_token=make_access_token(user_id),
        refresh_token=make_refresh_token(user_id),
    )

@router.post("/login")
async def login(data: LoginIn):
    db = get_db()
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not check_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user["_id"])
    return TokenOut(
        access_token=make_access_token(user_id),
        refresh_token=make_refresh_token(user_id),
    )

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "id": oid_str(user["_id"]),
        "name": user.get("name"),
        "email": user.get("email"),
        "role": user.get("role"),
        "created_at": user.get("created_at"),
    }
