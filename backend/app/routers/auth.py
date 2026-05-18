from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt

from app.database import get_db
from app.models import User
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.token_expire_hours)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return int(payload.get("sub"))
    except Exception:
        return None


class RegisterRequest(BaseModel):
    username: str
    password: str
    device_token: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str
    device_token: Optional[str] = None


class TokenResponse(BaseModel):
    token: str
    user_id: int
    username: str


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        device_token=req.device_token
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_token(user.id)
    return TokenResponse(token=token, user_id=user.id, username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if req.device_token:
        user.device_token = req.device_token
        await db.commit()
    
    token = create_token(user.id)
    return TokenResponse(token=token, user_id=user.id, username=user.username)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="认证格式错误")
    
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return user


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "username": current_user.username}
