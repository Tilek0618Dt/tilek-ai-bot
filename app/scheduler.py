from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Float,
    Text,
    Boolean,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# =========================
# Base
# =========================
class Base(DeclarativeBase):
    pass


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# =========================
# User
# =========================
class User(Base):
    __tablename__ = "users"

    # internal id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # telegram
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # locale
    language: Mapped[str] = mapped_column(String(8), default="ky")
    country_code: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)

    # plan
    plan: Mapped[str] = mapped_column(String(16), default="FREE")  # FREE/PLUS/PRO
    plan_until: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # monthly limits (remaining)
    chat_left: Mapped[int] = mapped_column(Integer, default=0)
    video_left: Mapped[int] = mapped_column(Integer, default=0)
    music_left: Mapped[int] = mapped_column(Integer, default=0)
    image_left: Mapped[int] = mapped_column(Integer, default=0)
    voice_left: Mapped[int] = mapped_column(Integer, default=0)
    doc_left: Mapped[int] = mapped_column(Integer, default=0)

    last_monthly_reset: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    # FREE daily limit + block
    free_day_key: Mapped[str] = mapped_column(String(16), default="")  # "YYYY-MM-DD"
    free_today_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_until: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Style engine loop counter 😎😈🧠
    style_counter: Mapped[int] = mapped_column(Integer, default=0)

    # Referral
    referrer_tg_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ref_balance_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # VIP credits (not monthly)
    vip_video_credits: Mapped[int] = mapped_column(Integer, default=0)   # count
    vip_music_minutes: Mapped[int] = mapped_column(Integer, default=0)  # minutes

    # system/flood/admin
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    last_action_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_users_plan", "plan"),
        Index("ix_users_country_code", "country_code"),
    )


# =========================
# Invoice (Payments)
# =========================
class Invoice(Base):
    """
    kind examples:
      - PLAN_PLUS
      - PLAN_PRO
      - VIP_VIDEO_1 / VIP_VIDEO_3 / VIP_VIDEO_5
      - VIP_MUSIC_1 / VIP_MUSIC_3 / VIP_MUSIC_5
    status:
      - created
      - paid
      - failed
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    order_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    tg_id: Mapped[int] = mapped_column(Integer, index=True)

    kind: Mapped[str] = mapped_column(String(32))
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(16), default="created")
    payment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    provider: Mapped[str] = mapped_column(String(16), default="cryptomus")  # future: stripe, etc.
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # store webhook/invoice json text

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_kind", "kind"),
    )


# =========================
# Optional: Admin logs
# =========================
class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_tg_id: Mapped[int] = mapped_column(Integer, index=True)

    action: Mapped[str] = mapped_column(String(64))  # ban_user, unban_user, give_plus, etc.
    target_tg_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_admin_logs_action", "action"),
    )
