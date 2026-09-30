"""Authentication API — register, login, me."""
from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, Depends

from app.web_mvp import store
from app.web_mvp.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.web_mvp.auth_schemas import (
    TokenResponse,
    UserLoginRequest,
    UserProfile,
    UserRegisterRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: UserRegisterRequest):
    """Register a new student or professor account."""
    email_lower = request.email.lower().strip()

    # Duplicate check
    existing = await store.find_one("users", {"email": email_lower})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    user_id = f"USER-{uuid4().hex[:12].upper()}"
    password_hash = hash_password(request.password)

    user_doc: dict = {
        "user_id": user_id,
        "name": request.name.strip(),
        "email": email_lower,
        "password_hash": password_hash,
        "role": request.role,
    }

    # If registering as a professor, link to professor record if one exists
    professor_id: str | None = None
    if request.role == "professor":
        prof = await store.find_one("professors", {"email": email_lower})
        if prof:
            professor_id = prof.get("professor_id")
            user_doc["professor_id"] = professor_id

    await store.insert_one("users", user_doc)
    logger.info("Registered user %s (%s) role=%s", user_id, email_lower, request.role)

    token_data = {
        "sub": user_id,
        "email": email_lower,
        "role": request.role,
        "name": request.name.strip(),
    }
    if professor_id:
        token_data["professor_id"] = professor_id

    return TokenResponse(
        access_token=create_access_token(token_data),
        user_id=user_id,
        role=request.role,
        name=request.name.strip(),
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    """Authenticate and return a JWT token."""
    email_lower = request.email.lower().strip()
    user = await store.find_one("users", {"email": email_lower})

    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token_data = {
        "sub": user["user_id"],
        "email": email_lower,
        "role": user["role"],
        "name": user["name"],
    }
    if user.get("professor_id"):
        token_data["professor_id"] = user["professor_id"]

    logger.info("User %s logged in", user["user_id"])
    return TokenResponse(
        access_token=create_access_token(token_data),
        user_id=user["user_id"],
        role=user["role"],
        name=user["name"],
    )


@router.get("/me", response_model=UserProfile)
async def me(payload: dict = Depends(get_current_user)):
    """Return the current user's profile (no password hash)."""
    return UserProfile(
        user_id=payload["sub"],
        name=payload.get("name", ""),
        email=payload.get("email", ""),
        role=payload.get("role", "student"),
        professor_id=payload.get("professor_id"),
    )
