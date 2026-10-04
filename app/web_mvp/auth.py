"""JWT authentication and password hashing utilities."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — read at import time so tests can monkeypatch os.environ
# ---------------------------------------------------------------------------

from app.web_mvp.config import JWT_EXPIRE_MINUTES as CONFIG_JWT_EXPIRE_MINUTES, JWT_SECRET as CONFIG_JWT_SECRET


def _jwt_secret() -> str:
    return os.environ.get("JWT_SECRET", CONFIG_JWT_SECRET)


def _jwt_expire_minutes() -> int:
    try:
        return int(os.environ.get("JWT_EXPIRE_MINUTES", str(CONFIG_JWT_EXPIRE_MINUTES)))
    except ValueError:
        return 60



_bearer = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Password utilities (passlib / bcrypt)
# ---------------------------------------------------------------------------

try:
    import bcrypt as _bcrypt

    def hash_password(plain: str) -> str:
        # Pre-hash with SHA-256 to handle passwords longer than 72 bytes safely
        import hashlib, base64
        digest = base64.b64encode(hashlib.sha256(plain.encode()).digest())
        return _bcrypt.hashpw(digest, _bcrypt.gensalt()).decode()

    def verify_password(plain: str, hashed: str) -> bool:
        import hashlib, base64
        digest = base64.b64encode(hashlib.sha256(plain.encode()).digest())
        try:
            return _bcrypt.checkpw(digest, hashed.encode())
        except Exception:
            return False

except ImportError:
    try:
        from passlib.context import CryptContext
        _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        def hash_password(plain: str) -> str:  # type: ignore[misc]
            return _pwd_context.hash(plain[:72])  # bcrypt limit

        def verify_password(plain: str, hashed: str) -> bool:  # type: ignore[misc]
            return _pwd_context.verify(plain[:72], hashed)

    except ImportError:
        import hashlib, hmac, base64  # noqa: E401

        logger.warning("bcrypt/passlib not available — using SHA-256 fallback (install bcrypt for production)")

        def hash_password(plain: str) -> str:  # type: ignore[misc]
            salt = os.urandom(16)
            hashed = hmac.new(salt, plain.encode(), hashlib.sha256).digest()
            return base64.b64encode(salt + hashed).decode()

        def verify_password(plain: str, stored: str) -> bool:  # type: ignore[misc]
            raw = base64.b64decode(stored.encode())
            salt, stored_hash = raw[:16], raw[16:]
            check = hmac.new(salt, plain.encode(), hashlib.sha256).digest()
            return hmac.compare_digest(check, stored_hash)


# ---------------------------------------------------------------------------
# JWT utilities (python-jose)
# ---------------------------------------------------------------------------

try:
    from jose import JWTError, jwt as _jose_jwt

    def create_access_token(data: dict[str, Any]) -> str:
        payload = {
            **data,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=_jwt_expire_minutes()),
            "iat": datetime.now(timezone.utc),
        }
        return _jose_jwt.encode(payload, _jwt_secret(), algorithm="HS256")

    def decode_token(token: str) -> dict[str, Any]:
        try:
            return _jose_jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

except ImportError:
    import base64, hashlib, hmac, json as _json  # noqa: E401,F811 — fallback

    logger.warning("python-jose not available — using simple HMAC token fallback")

    def create_access_token(data: dict[str, Any]) -> str:  # type: ignore[misc]
        expire = datetime.now(timezone.utc) + timedelta(minutes=_jwt_expire_minutes())
        payload = {**data, "exp": expire.isoformat()}
        body = base64.urlsafe_b64encode(_json.dumps(payload).encode()).decode()
        sig = hmac.new(_jwt_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{sig}"

    def decode_token(token: str) -> dict[str, Any]:  # type: ignore[misc]
        try:
            body, sig = token.rsplit(".", 1)
            expected = hmac.new(_jwt_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                raise ValueError("Bad signature")
            payload = _json.loads(base64.urlsafe_b64decode(body.encode() + b"=="))
            if datetime.fromisoformat(payload["exp"]) < datetime.now(timezone.utc):
                raise ValueError("Token expired")
            return payload
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def _get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


async def get_current_user(
    payload: dict[str, Any] = Depends(_get_current_user_payload),
) -> dict[str, Any]:
    """Return token payload. Any authenticated user is accepted."""
    return payload


async def require_student(
    payload: dict[str, Any] = Depends(_get_current_user_payload),
) -> dict[str, Any]:
    """Allow students and admins."""
    if payload.get("role") not in {"student", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")
    return payload


async def require_professor(
    payload: dict[str, Any] = Depends(_get_current_user_payload),
) -> dict[str, Any]:
    """Allow approved professors and admins."""
    role = payload.get("role")
    if role not in {"professor", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Professor access required")
    if role == "professor":
        from app.web_mvp import store
        user = await store.find_one("users", {"user_id": payload.get("sub")})
        if user:
            approval = user.get("approval_status", "APPROVED")
            if approval != "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Professor account is {approval.lower()}. Access denied.",
                )
        elif payload.get("approval_status") and payload.get("approval_status") != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Professor account is not approved. Access denied.",
            )
    return payload


async def require_any_role(
    payload: dict[str, Any] = Depends(_get_current_user_payload),
) -> dict[str, Any]:
    """Allow any authenticated user (student, professor, admin)."""
    role = payload.get("role")
    if role not in {"student", "professor", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return payload


async def require_admin(
    payload: dict[str, Any] = Depends(_get_current_user_payload),
) -> dict[str, Any]:
    """Allow admins only."""
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return payload
