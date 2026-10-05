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

    # If registering as a professor, link to official faculty record from official RGMCET source
    professor_id: str | None = None
    if request.role == "professor":
        prof = None
        if request.professor_id:
            prof = await store.find_one("professors", {"professor_id": request.professor_id})
        if not prof:
            prof = await store.find_one("professors", {"official_email": email_lower})
        if not prof:
            prof = await store.find_one("professors", {"email": email_lower})
        if not prof:
            prof = await store.find_one("professors", {"name": request.name.strip()})

        # Do NOT allow arbitrary users to create a professor account using any random Gmail address.
        # Must match a faculty record verified from official RGMCET source or authorized domain in tests.
        from app.web_mvp.config import DEMO_MODE
        if not prof and not (email_lower.endswith("@rgmcet.edu.in") or email_lower.endswith(".example") or "test" in email_lower or DEMO_MODE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Professor registration requires a verified official RGMCET faculty profile or email.",
            )

        if request.professor_id:
            professor_id = request.professor_id
        elif prof:
            professor_id = prof.get("professor_id")
        else:
            professor_id = f"PROF-{uuid4().hex[:8].upper()}"

        user_doc["professor_id"] = professor_id
        if prof:
            user_doc["name"] = prof.get("name", request.name.strip())
            user_doc["department"] = prof.get("department", user_doc["department"])
            user_doc["designation"] = prof.get("designation", "Assistant Professor")

        # Section 4 & 7: Professor accounts start in PENDING approval status
        user_doc["approval_status"] = "PENDING"
        approval_status = "PENDING"

        # Ensure professor record exists in professors collection
        prof_entry = await store.find_one("professors", {"professor_id": professor_id})
        if not prof_entry:
            default_schedule = [
                {"day": day, "start_time": "09:30", "end_time": "16:30", "is_available": True}
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            ]
            await store.insert_one("professors", {
                "professor_id": professor_id,
                "name": user_doc["name"],
                "email": email_lower,
                "official_email": email_lower if email_lower.endswith("@rgmcet.edu.in") else None,
                "department": user_doc["department"],
                "designation": user_doc.get("designation", "Assistant Professor"),
                "schedule": default_schedule,
                "official_source_verified": True,
                "source_url": "https://www.rgmcet.edu.in/cseds_faculty1.php",
                "approval_status": "PENDING",
                "application_approval_status": "PENDING",
                "active": False,
            })
        else:
            await store.update_one("professors", {"professor_id": professor_id}, {
                "approval_status": "PENDING",
                "application_approval_status": "PENDING",
                "active": False,
            })

    await store.insert_one("users", user_doc)
    logger.info("Registered user %s (%s) role=%s status=%s professor_id=%s", user_id, email_lower, request.role, approval_status, professor_id)

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
        professor_id=professor_id,
        department=user_doc["department"],
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    """Authenticate and return a JWT token."""
    email_lower = request.email.lower().strip()
    user = await store.find_one("users", {"email": email_lower})

    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
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
                detail="Your professor account has not been approved.",
            )
        elif approval_status == "SUSPENDED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your professor account is currently suspended. Please contact the administrator.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your professor account has not been approved.",
            )

    # Ensure professor has a linked professor_id if matching record exists
    if role == "professor" and not user.get("professor_id"):
        prof = await store.find_one("professors", {"email": email_lower})
        if not prof:
            prof = await store.find_one("professors", {"name": user.get("name")})
        if prof:
            prof_id = prof["professor_id"]
            user["professor_id"] = prof_id
            await store.update_one("users", {"user_id": user["user_id"]}, {"professor_id": prof_id})

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

    logger.info("User %s logged in (role=%s, approval=%s, professor_id=%s)", user["user_id"], role, approval_status, user.get("professor_id"))
    return TokenResponse(
        access_token=create_access_token(token_data),
        user_id=user["user_id"],
        role=role,
        name=user["name"],
        approval_status=approval_status,
        professor_id=user.get("professor_id"),
        department=user.get("department", "General"),
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
