from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models import User, UserRole, Worker

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WorkerRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    capabilities: dict[str, Any] = Field(default_factory=dict)


class WorkerRegisterResponse(BaseModel):
    worker_id: uuid.UUID
    api_key: str


class WorkerRefreshResponse(BaseModel):
    api_key: str


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    credits_balance: float
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except ExpiredSignatureError:
        raise expired_exception
    except JWTError as exc:
        raise credentials_exception from exc

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def get_current_worker(
    api_key: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Worker:
    # Workers authenticate via a custom X-Worker-Api-Key header or form field.
    # For simplicity in this router we accept it as a query/header dependency injected elsewhere,
    # but here we define a helper that looks up by hashed key.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use get_current_worker_dependency from the request directly.",
    )


def _hash_api_key(plain: str) -> str:
    return pwd_context.hash(plain)


def _verify_api_key(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        hashed_password=await asyncio.to_thread(_hash_password, payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = _create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = {}
        email = body.get("email")
        password = body.get("password")
    else:
        try:
            form = await request.form()
        except Exception:
            form = {}
        email = form.get("username")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None or not await asyncio.to_thread(_verify_password, password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = _create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserMeResponse:
    return current_user


@router.post("/worker-register", response_model=WorkerRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_worker(
    payload: WorkerRegister,
    db: AsyncSession = Depends(get_db),
) -> WorkerRegisterResponse:
    plain_api_key = secrets.token_urlsafe(32)
    worker = Worker(
        name=payload.name,
        capabilities=payload.capabilities,
        api_key_hashed=await asyncio.to_thread(_hash_api_key, plain_api_key),
        api_key_prefix=plain_api_key[:8],
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return WorkerRegisterResponse(worker_id=worker.id, api_key=plain_api_key)


@router.post("/worker-refresh", response_model=WorkerRefreshResponse)
async def refresh_worker_api_key(
    api_key: str,
    db: AsyncSession = Depends(get_db),
) -> WorkerRefreshResponse:
    prefix = api_key[:8]
    stmt = select(Worker).where(Worker.api_key_prefix == prefix)
    result = await db.execute(stmt)
    workers = result.scalars().all()

    target_worker: Worker | None = None
    for w in workers:
        if await asyncio.to_thread(_verify_api_key, api_key, w.api_key_hashed):
            target_worker = w
            break

    if target_worker is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    new_plain_key = secrets.token_urlsafe(32)
    target_worker.api_key_hashed = await asyncio.to_thread(_hash_api_key, new_plain_key)
    target_worker.api_key_prefix = new_plain_key[:8]
    await db.commit()
    return WorkerRefreshResponse(api_key=new_plain_key)
