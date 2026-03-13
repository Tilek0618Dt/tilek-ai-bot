import os
from dotenv import load_dotenv
from typing import List

load_dotenv()


# =========================================================
# Helpers
# =========================================================

def _get_str(name: str, default: str = "", required: bool = False) -> str:
    value = os.getenv(name, default).strip()
    if required and not value:
        raise RuntimeError(f"❌ ENV '{name}' required but not set")
    return value


def _get_int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        raise RuntimeError(f"❌ ENV '{name}' must be integer")


def _get_float(name: str, default: float = 0.0) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        raise RuntimeError(f"❌ ENV '{name}' must be float")


def _get_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


def _get_list(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()]


# =========================================================
# Core Bot
# =========================================================

BOT_TOKEN = _get_str("BOT_TOKEN", required=True)
ENVIRONMENT = _get_str("ENVIRONMENT", "production")  # production / development
DEBUG = ENVIRONMENT != "production"


# =========================================================
# Database
# =========================================================

DATABASE_URL = _get_str("DATABASE_URL", required=True)

def _to_async_db(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url

DATABASE_URL = _to_async_db(DATABASE_URL)


# =========================================================
# AI Providers
# =========================================================

GROK_API_KEY = _get_str("GROK_API_KEY")
OPENAI_API_KEY = _get_str("OPENAI_API_KEY")

RUNWAY_API_KEY = _get_str("RUNWAY_API_KEY")
KLING_API_KEY = _get_str("KLING_API_KEY")
SUNO_API_KEY = _get_str("SUNO_API_KEY")
ELEVENLABS_API_KEY = _get_str("ELEVENLABS_API_KEY")


# =========================================================
# Payment (Cryptomus)
# =========================================================

CRYPTOMUS_API_KEY = _get_str("CRYPTOMUS_API_KEY")
CRYPTOMUS_MERCHANT_ID = _get_str("CRYPTOMUS_MERCHANT_ID")
CRYPTOMUS_WEBHOOK_SECRET = _get_str("CRYPTOMUS_WEBHOOK_SECRET")


# =========================================================
# Channel Gate
# =========================================================

REQUIRED_CHANNEL = _get_str("REQUIRED_CHANNEL")
CHANNEL_URL = _get_str("CHANNEL_URL")


# =========================================================
# Admins & Support
# =========================================================

ADMIN_IDS = [int(x) for x in _get_list("ADMIN_IDS") if x.isdigit()]
SUPPORT_ADMINS = _get_list("SUPPORT_ADMINS")


# =========================================================
# Public URL (Webhook)
# =========================================================

PUBLIC_BASE_URL = _get_str("PUBLIC_BASE_URL")

if PUBLIC_BASE_URL and PUBLIC_BASE_URL.endswith("/"):
    PUBLIC_BASE_URL = PUBLIC_BASE_URL[:-1]

WEBHOOK_CRYPTOMUS = f"{PUBLIC_BASE_URL}/cryptomus/webhook" if PUBLIC_BASE_URL else None


# =========================================================
# Limits & Business Controls
# =========================================================

FREE_DAILY_LIMIT = _get_int("FREE_DAILY_LIMIT", 10)
FREE_BLOCK_HOURS = _get_int("FREE_BLOCK_HOURS", 6)

MIN_WITHDRAW_USD = _get_float("MIN_WITHDRAW_USD", 20.0)

ENABLE_REFERRAL = _get_bool("ENABLE_REFERRAL", True)
ENABLE_VIP = _get_bool("ENABLE_VIP", True)


# =========================================================
# Startup Validation
# =========================================================

def validate_config():
    if ENVIRONMENT == "production":
        required_fields = [
            BOT_TOKEN,
            DATABASE_URL,
        ]
        if not all(required_fields):
            raise RuntimeError("❌ Production config incomplete")

    if DEBUG:
        print("⚠️ DEBUG MODE ACTIVE")

validate_config()


print("✅ Config loaded successfully")
