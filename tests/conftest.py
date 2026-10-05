"""
pytest configuration for RGMCET AI Campus Assistant.

All tests run against the in-memory demo store.
This isolates the test suite from any live MongoDB / Atlas instance
so that tests are fast, deterministic, and do not require network access.

Production behaviour (DEMO_MODE=false + real Atlas URI) is verified
separately in the Phase 12 production verification script.
"""
from __future__ import annotations

import os
import pytest

# ---------------------------------------------------------------------------
# Force demo/in-memory mode for every test session.
# Must be set BEFORE the application modules are imported so that
# config.py picks up the correct values.
# ---------------------------------------------------------------------------
os.environ["DEMO_MODE"] = "true"
os.environ.setdefault("DATABASE_NAME", "rgmcet_ai_assistant")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production-use-only")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")

# Now import and reset the store so each test session starts clean.
from app.web_mvp import store as _store  # noqa: E402 — must come after env setup


def pytest_configure(config):
    """Called once at the very start of the test session."""
    # Re-apply env override in case dotenv was already loaded.
    os.environ["DEMO_MODE"] = "true"


@pytest.fixture(autouse=True)
def reset_demo_store():
    """
    Reset the in-memory demo store before every test.

    This ensures each test starts from a clean, known state
    (demo professors + empty appointments) without leaking
    state between tests.
    """
    # Force in-memory mode on the store module globals
    _store._database = None
    _store._client = None
    _store._using_demo_store = True
    _store.reset_demo_data()
    yield
    # Cleanup after test (belt-and-suspenders)
    _store.reset_demo_data()
