from __future__ import annotations

import re
import uuid
import time
import datetime as dt
from typing import Optional


# =========================================================
# Time helpers (UTC)
# =========================================================
def utcnow() -> dt.datetime:
    """
    Always return timezone-aware UTC datetime.
    """
    return dt.datetime.now(dt.timezone.utc)


def to_utc(d: Optional[dt.datetime]) -> Optional[dt.datetime]:
    """
    Normalize datetime to timezone-aware UTC.
    - None => None
    - naive => assume UTC
    - aware => convert to UTC
    """
    if d is None:
        return None
    if d.tzinfo is None:
        return d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def day_key_utc(now: Optional[dt.datetime] = None) -> str:
    """
    UTC day key used for FREE daily reset.
    Example: '2026-02-25'
    """
    n = to_utc(now) or utcnow()
    return n.strftime("%Y-%m-%d")


def in_minutes(minutes: int, from_dt: Optional[dt.datetime] = None) -> dt.datetime:
    base = to_utc(from_dt) or utcnow()
    return base + dt.timedelta(minutes=int(minutes))


def in_hours(hours: int, from_dt: Optional[dt.datetime] = None) -> dt.datetime:
    base = to_utc(from_dt) or utcnow()
    return base + dt.timedelta(hours=int(hours))


def in_days(days: int, from_dt: Optional[dt.datetime] = None) -> dt.datetime:
    base = to_utc(from_dt) or utcnow()
    return base + dt.timedelta(days=int(days))


def in_30_days(from_dt: Optional[dt.datetime] = None) -> dt.datetime:
    return in_days(30, from_dt=from_dt)


def is_expired(plan_until: Optional[dt.datetime], now: Optional[dt.datetime] = None) -> bool:
    """
    Plan expiry checker.
    """
    pu = to_utc(plan_until)
    if not pu:
        return False
    n = to_utc(now) or utcnow()
    return n >= pu


def seconds_left(until: Optional[dt.datetime], now: Optional[dt.datetime] = None) -> int:
    """
    How many seconds left until datetime 'until'.
    Returns 0 if already passed or None.
    """
    u = to_utc(until)
    if not u:
        return 0
    n = to_utc(now) or utcnow()
    diff = (u - n).total_seconds()
    return max(0, int(diff))


def minutes_left(until: Optional[dt.datetime], now: Optional[dt.datetime] = None) -> int:
    return seconds_left(until, now=now) // 60


def human_left(until: Optional[dt.datetime], now: Optional[dt.datetime] = None) -> str:
    """
    Pretty remaining time:
    - 2h 15m
    - 35m
    - 10s
    """
    sec = seconds_left(until, now=now)
    if sec <= 0:
        return "0m"

    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    parts: list[str] = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if not parts and s:
        parts.append(f"{s}s")
    return " ".join(parts)


# =========================================================
# IDs / Tokens / Orders
# =========================================================
def short_uuid(n: int = 10) -> str:
    """
    Random short id for order_id suffix etc.
    """
    return uuid.uuid4().hex[: max(6, min(32, int(n)))]


def make_order_id(kind: str, tg_id: int) -> str:
    """
    Stable readable order_id:
    PLAN_PLUS-12345-<short>
    """
    k = re.sub(r"[^A-Za-z0-9_]+", "_", (kind or "ORDER"))[:40]
    return f"{k}-{int(tg_id)}-{short_uuid(12)}"


def unix_ts() -> int:
    return int(time.time())


# =========================================================
# Text helpers (Telegram safe-ish)
# =========================================================
def clamp_text(text: str, limit: int = 3500) -> str:
    """
    Telegram message limit ~4096 chars.
    Keep margin for markdown/extra.
    """
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 1].rstrip() + "…"


def safe_username(username: Optional[str]) -> str:
    """
    Normalize username for logging/UI.
    """
    if not username:
        return ""
    u = username.strip().lstrip("@")
    u = re.sub(r"[^A-Za-z0-9_]+", "", u)
    return u[:32]


def money_usd(amount: float) -> str:
    """
    Format USD with 2 decimals.
    """
    try:
        return f"${float(amount):.2f}"
    except Exception:
        return "$0.00"


# =========================================================
# Plan / Limits helpers (generic)
# =========================================================
def is_paid_plan(plan: Optional[str]) -> bool:
    return (plan or "").upper() in ("PLUS", "PRO")


def normalize_plan(plan: Optional[str]) -> str:
    p = (plan or "FREE").strip().upper()
    return p if p in ("FREE", "PLUS", "PRO") else "FREE"


# =========================================================
# Small UX helpers
# =========================================================
def pick_language_default(country_lang: Optional[str], fallback: str = "ky") -> str:
    """
    If country provided lang is empty => fallback.
    """
    l = (country_lang or "").strip().lower()
    if not l:
        return fallback
    return l[:8]


def now_iso() -> str:
    return utcnow().isoformat()
