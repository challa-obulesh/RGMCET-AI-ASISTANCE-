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

    # Professor accounts start in PENDING approval status unless admin
    approval_status = "PENDING" if request.role == "professor" else "APPROVED"

    user_doc: dict = {
        "user_id": user_id,
        "name": request.name.strip(),
        "email": email_lower,
        "password_hash": password_hash,
        "role": request.role,
        "approval_status": approval_status,
        "department": request.department or "General",
    }

    # If registering as a professor, link to professor record if one exists
    professor_id: str | None = None
    if request.role == "professor":
        prof = await store.find_one("professors", {"email": email_lower})
        if prof:
            professor_id = prof.get("professor_id")
            user_doc["professor_id"] = professor_id
            user_doc["department"] = prof.get("department", user_doc["department"])

    await store.insert_one("users", user_doc)
    logger.info("Registered user %s (%s) role=%s status=%s", user_id, email_lower, request.role, approval_status)

    token_data = {
        "sub": user_id,
        "email": email_lower,
        "role": request.role,
        "name": request.name.strip(),
        "approval_status": approval_status,
        "department": user_doc["department"],
    }
    if professor_id:
        token_data["professor_id"] = professor_id

    return TokenResponse(
        access_token=create_access_token(token_data),
        user_id=user_id,
        role=request.role,
        name=request.name.strip(),
        approval_status=approval_status,
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

    role = user.get("role", "student")
    approval_status = user.get("approval_status", "APPROVED")

    # If professor account is not approved, block login
    if role == "professor" and approval_status != "APPROVED":
        if approval_status == "PENDING":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your professor account is pending admin approval.",
            )
        elif approval_status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your professor account request has been rejected.",
            )
        elif approval_status == "SUSPENDED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your professor account is suspended. Please contact the administrator.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Professor account is not approved.",
            )

    token_data = {
        "sub": user["user_id"],
        "email": email_lower,
        "role": role,
        "name": user["name"],
        "approval_status": approval_status,
        "department": user.get("department", "General"),
    }
    if user.get("professor_id"):
        token_data["professor_id"] = user["professor_id"]

    logger.info("User %s logged in (role=%s, approval=%s)", user["user_id"], role, approval_status)
    return TokenResponse(
        access_token=create_access_token(token_data),
        user_id=user["user_id"],
        role=role,
        name=user["name"],
        approval_status=approval_status,
    )


@router.get("/me", response_model=UserProfile)
async def me(payload: dict = Depends(get_current_user)):
    """Return the current user's profile (no password hash)."""
    user = await store.find_one("users", {"user_id": payload.get("sub")})
    return UserProfile(
        user_id=payload["sub"],
        name=payload.get("name", user.get("name", "") if user else ""),
        email=payload.get("email", user.get("email", "") if user else ""),
        role=payload.get("role", user.get("role", "student") if user else "student"),
        department=user.get("department") if user else payload.get("department"),
        professor_id=payload.get("professor_id", user.get("professor_id") if user else None),
        approval_status=user.get("approval_status", payload.get("approval_status", "APPROVED")) if user else payload.get("approval_status", "APPROVED"),
    )
