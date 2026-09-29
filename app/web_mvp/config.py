import os

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", os.getenv("MONGODB_DB_NAME", "rgmcet_ai"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Backward compatibility for earlier OpenAI-compatible configurations.
LEGACY_LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LEGACY_LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LEGACY_LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]