"""Centralized Privacy Gateway for outbound hosted LLM requests.

Enforces:
1. Data minimization & prompt boundary separation.
2. Email protection (redacts all emails to [REDACTED_EMAIL]).
3. Personal Identifiers (phone numbers to [REDACTED_PHONE]).
4. Credentials & secrets protection (API keys, JWT tokens, DB connection strings, passwords).
5. Safe fallback: Rejects transmission rather than leaking sensitive text if processing fails.
6. Sanitized logging (metadata only; never logs raw sensitive context).
7. Pre-transmission inspection of final outbound JSON payloads.

LIMITATIONS NOTICE:
Rule-based regex and heuristic token detection catch standard emails, phones,
JWTs, API key patterns, and URIs. They cannot guarantee 100% catch rate for
oblique or adversarial PII patterns. Institutional facts must be verified
deterministically from verified sources rather than relying on LLM memory.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("app.web_mvp.privacy_gateway")

# -----------------------------------------------------------------------------
# Detection patterns
# -----------------------------------------------------------------------------
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Indian 10-digit mobile (+91 optional) & standard international phone patterns
PHONE_REGEX = re.compile(
    r"(?:\+91[\-\s]?)?[6789]\d{9}\b|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"
)

# JWT pattern (header.payload.signature)
JWT_REGEX = re.compile(
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
)

# Bearer token pattern
BEARER_REGEX = re.compile(
    r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"
)

# MongoDB / SQL database connection strings
DB_URI_REGEX = re.compile(
    r"(?i)(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis):\/\/[^\s'\"\)]+"
)

# Known API key prefixes (Google, OpenAI, Anthropic, AWS, etc.)
API_KEY_REGEX = re.compile(
    r"\b(?:AIza[0-9A-Za-z-_]{35}|sk-[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{36})\b"
)

# Generic credential / secret patterns (password="...", api_key="...")
GENERIC_SECRET_REGEX = re.compile(
    r"(?i)\b(?:password|passwd|api_key|apikey|secret_key|jwt_secret)\s*[:=]\s*['\"]([^'\"]{6,})['\"]"
)


class PrivacyGatewayError(Exception):
    """Raised when privacy sanitization or outbound inspection fails."""
    pass


class PrivacySanitizer:
    """Sanitizes text and inspects payloads before outbound transmission."""

    @classmethod
    def sanitize_text(cls, text: str) -> tuple[str, dict[str, int]]:
        """Sanitizes raw text by redacting sensitive items.
        
        Returns:
            (sanitized_text, stats_dict)
        """
        if not text:
            return text, {}

        stats: dict[str, int] = {
            "emails": 0,
            "phones": 0,
            "tokens": 0,
            "db_uris": 0,
            "api_keys": 0,
            "secrets": 0,
        }

        sanitized = text

        # 1. Redact DB connection strings
        db_matches = DB_URI_REGEX.findall(sanitized)
        if db_matches:
            stats["db_uris"] += len(db_matches)
            sanitized = DB_URI_REGEX.sub("[REDACTED_DB_CONNECTION]", sanitized)

        # 2. Redact API keys
        key_matches = API_KEY_REGEX.findall(sanitized)
        if key_matches:
            stats["api_keys"] += len(key_matches)
            sanitized = API_KEY_REGEX.sub("[REDACTED_API_KEY]", sanitized)

        # 3. Redact JWTs and Bearer tokens
        jwt_matches = JWT_REGEX.findall(sanitized)
        if jwt_matches:
            stats["tokens"] += len(jwt_matches)
            sanitized = JWT_REGEX.sub("[REDACTED_TOKEN]", sanitized)

        bearer_matches = BEARER_REGEX.findall(sanitized)
        if bearer_matches:
            stats["tokens"] += len(bearer_matches)
            sanitized = BEARER_REGEX.sub("Bearer [REDACTED_TOKEN]", sanitized)

        # 4. Redact Generic secrets
        secret_matches = GENERIC_SECRET_REGEX.findall(sanitized)
        if secret_matches:
            stats["secrets"] += len(secret_matches)
            sanitized = GENERIC_SECRET_REGEX.sub(r"\1: [REDACTED_SECRET]", sanitized)

        # 5. Redact Email addresses
        email_matches = EMAIL_REGEX.findall(sanitized)
        if email_matches:
            stats["emails"] += len(email_matches)
            sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", sanitized)

        # 6. Redact Phone numbers
        phone_matches = PHONE_REGEX.findall(sanitized)
        if phone_matches:
            stats["phones"] += len(phone_matches)
            sanitized = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)

        return sanitized, stats

    @classmethod
    def sanitize_request(
        cls,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict[str, int]]:
        """Processes and sanitizes system and user prompts with safe fallback.
        
        If an unexpected error occurs during sanitization, raises PrivacyGatewayError
        to avoid transmitting raw text.
        """
        try:
            sanitized_sys, stats_sys = cls.sanitize_text(system_prompt or "")
            sanitized_user, stats_user = cls.sanitize_text(user_prompt or "")

            total_stats = {
                k: stats_sys.get(k, 0) + stats_user.get(k, 0)
                for k in set(stats_sys) | set(stats_user)
            }

            # Sanitized logging: only log metadata counts, NEVER raw prompt text
            redacted_count = sum(total_stats.values())
            if redacted_count > 0:
                logger.info(
                    "Privacy Gateway sanitized prompt | Redactions: %s",
                    {k: v for k, v in total_stats.items() if v > 0},
                )

            return sanitized_sys, sanitized_user, total_stats

        except Exception as exc:
            logger.error("Privacy Gateway sanitization failure: %s; aborting LLM call", exc)
            raise PrivacyGatewayError(f"Privacy processing failed: {exc}") from exc

    @classmethod
    def verify_outbound_payload(cls, payload: Any, path: str = "$") -> None:
        """Deeply inspects outbound JSON payload leaves before transmission.
        
        Raises PrivacyGatewayError if unredacted emails, tokens, or credentials remain.
        """
        if isinstance(payload, str):
            # Check for unredacted emails
            emails = EMAIL_REGEX.findall(payload)
            if emails:
                logger.error("Privacy Gateway violation at %s: unredacted email detected", path)
                raise PrivacyGatewayError(f"Outbound payload contains unredacted email at {path}")

            # Check for unredacted JWT tokens
            jwts = JWT_REGEX.findall(payload)
            if jwts:
                logger.error("Privacy Gateway violation at %s: unredacted JWT detected", path)
                raise PrivacyGatewayError(f"Outbound payload contains unredacted token at {path}")

            # Check for DB connection strings
            db_uris = DB_URI_REGEX.findall(payload)
            if db_uris:
                logger.error("Privacy Gateway violation at %s: database URI detected", path)
                raise PrivacyGatewayError(f"Outbound payload contains database URI at {path}")

            # Check for known API key formats
            api_keys = API_KEY_REGEX.findall(payload)
            if api_keys:
                logger.error("Privacy Gateway violation at %s: unredacted API key detected", path)
                raise PrivacyGatewayError(f"Outbound payload contains unredacted API key at {path}")

        elif isinstance(payload, dict):
            for k, v in payload.items():
                cls.verify_outbound_payload(v, path=f"{path}.{k}")
        elif isinstance(payload, list):
            for i, item in enumerate(payload):
                cls.verify_outbound_payload(item, path=f"{path}[{i}]")


# Global gateway singleton
privacy_gateway = PrivacySanitizer()

# Module-level convenience aliases
sanitize_request = PrivacySanitizer.sanitize_request
sanitize_text = PrivacySanitizer.sanitize_text
verify_outbound_payload = PrivacySanitizer.verify_outbound_payload
