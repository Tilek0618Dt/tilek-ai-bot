# app/handlers/vip.py
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.config import ADMIN_IDS
from app.constants import PLANS
from app.style_engine import tilek_wrap, limit_ad_text

# Media services (азырынча stub; кийин реальный API кошобуз)
from app.services.media.runway import generate_video_stub
from app.services.media.suno import generate_music_stub

router = Router()

# =========================================================
# MVP State (in-memory)
# =========================================================
# user_id -> ("video"|"music", started_ts)
VIP_STATE: Dict[int, Tuple[str, float]] = {}


# =========================================================
# UX Keyboards
# =========================================================
def kb_vip_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 VIP VIDEO", callback_data="vip:video")],
        [InlineKeyboardButton(text="🪉 VIP MUSIC", callback_data="vip:music")],
        [InlineKeyboardButton(text="📦 Менин балансым", callback_data="vip:balance")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:back")],
    ])


def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="vip:cancel")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="vip:home")],
    ])


def kb_upsell() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Премиум", callback_data="m:premium")],
        [InlineKeyboardButton(text="🎥 VIP VIDEO пакет", callback_data="m:vip_video")],
        [InlineKeyboardButton(text="🪉 VIP MUSIC пакет", callback_data="m:vip_music")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="vip:home")],
    ])


# =========================================================
# Helpers
# =========================================================
def _is_admin(tg_id: int) -> bool:
    return tg_id in (ADMIN_IDS or [])


def _clean_prompt(text: str, max_len: int = 500) -> str:
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    if len(t) > max_len:
        t = t[: max_len - 20].rstrip() + " …"
    return t


async def _get_user(tg_id: int, username: Optional[str] = None) -> User:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == tg_id))
        u = res.scalar_one_or_none()
        if not u:
            u = User(tg_id=tg_id, username=username)
            s.add(u)
            await s.commit()
            await s.refresh(u)
        return u


async def _save_user(u: User) -> None:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == u.tg_id))
        db_u = res.scalar_one()
        # copy fields we touched
        db_u.plan = u.plan
        db_u.plan_until = u.plan_until
        db_u.video_left = u.video_left
        db_u.music_left = u.music_left
        db_u.vip_video_credits = u.vip_video_credits
        db_u.vip_music_minutes = u.vip_music_minutes
        db_u.style_counter = u.style_counter
        await s.commit()


def _vip_balance_text(u: User) -> str:
    return (
        "📦 VIP баланс\n\n"
        f"🎥 VIP VIDEO кредит: {u.vip_video_credits}\n"
        f"🪉 VIP MUSIC минут: {u.vip_music_minutes}\n\n"
        f"💎 План: {u.plan}\n"
        f"🎥 План видео лимит: {u.video_left}\n"
        f"🪉 План музыка лимит: {u.music_left}\n"
    )


def _need_text(kind: str) -> str:
    if kind == "video":
        return (
            "🎥 VIP VIDEO керек болуп калды, досум 😭\n\n"
            "Сенде азыр:\n"
            "• VIP кредит жок же\n"
            "• PLUS/PRO видео лимит бүттү\n\n"
            "👉 Пакет алсаң — дароо ачылат 😎"
        )
    return (
        "🪉 VIP MUSIC керек болуп калды, досум 😭\n\n"
        "Сенде азыр:\n"
        "• VIP минут жок же\n"
        "• PLUS/PRO музыка лимит бүттү\n\n"
        "👉 Пакет алсаң — дароо ачылат 😎"
    )


def _consume_video(u: User) -> bool:
    """
    Priority:
    1) VIP credits
    2) Plan monthly video_left (PLUS/PRO)
    Return True if consumed successfully.
    """
    if (u.vip_video_credits or 0) > 0:
        u.vip_video_credits -= 1
        return True
    if u.plan in ("PLUS", "PRO") and (u.video_left or 0) > 0:
        u.video_left -= 1
        return True
    return False


def _consume_music(u: User, minutes_need: int = 1) -> bool:
    """
    Priority:
    1) VIP minutes
    2) Plan monthly music_left (PLUS/PRO) -> count-based (1 генерация = 1)
    """
    if (u.vip_music_minutes or 0) >= minutes_need:
        u.vip_music_minutes -= minutes_need
        return True
    if u.plan in ("PLUS", "PRO") and (u.music_left or 0) > 0:
        u.music_left -= 1
        return True
    return False


# =========================================================
# Entry points from main menu buttons:
# You already have callbacks: m:video / m:music
# We'll handle them here too for VIP experience.
# =========================================================
@router.callback_query(F.data == "m:video")
async def entry_from_main_video(call: CallbackQuery):
    await call.message.answer("🎥 Досум, VIP VIDEO үчүн теманы жаз:\nМисал: *кыргыз тоолору, ат минип бара жаткан баатыр, кино стил* 😎",
                             reply_markup=kb_cancel())
    VIP_STATE[call.from_user.id] = ("video", time.time())
    await call.answer()


@router.callback_query(F.data == "m:music")
async def entry_from_main_music(call: CallbackQuery):
    await call.message.answer("🪉 Досум, VIP MUSIC үчүн теманы жаз:\nМисал: *motivational trap beat, бизнес энергия* 😈",
                             reply_markup=kb_cancel())
    VIP_STATE[call.from_user.id] = ("music", time.time())
    await call.answer()


# Optional: vip:home screen
@router.callback_query(F.data == "vip:home")
async def vip_home(call: CallbackQuery):
    await call.message.answer("🎛 VIP Panel\nКайсыны жасайбыз, досум? 😎", reply_markup=kb_vip_home())
    await call.answer()


@router.callback_query(F.data == "vip:balance")
async def vip_balance(call: CallbackQuery):
    u = await _get_user(call.from_user.id, call.from_user.username)
    await call.message.answer(_vip_balance_text(u))
    await call.answer()


@router.callback_query(F.data == "vip:video")
async def vip_video(call: CallbackQuery):
    await call.message.answer("🎥 Теманы жазчы (1 видео):\nМисал: *cinematic, runway style, neon city* 😎",
                             reply_markup=kb_cancel())
    VIP_STATE[call.from_user.id] = ("video", time.time())
    await call.answer()


@router.callback_query(F.data == "vip:music")
async def vip_music(call: CallbackQuery):
    await call.message.answer("🪉 Теманы жазчы (1 мин):\nМисал: *epic orchestral + trap drums* 😈",
                             reply_markup=kb_cancel())
    VIP_STATE[call.from_user.id] = ("music", time.time())
    await call.answer()


@router.callback_query(F.data == "vip:cancel")
async def vip_cancel(call: CallbackQuery):
    VIP_STATE.pop(call.from_user.id, None)
    await call.message.answer("❌ Токтоттум, досум. Кайра менюдан тандай бер 😎")
    await call.answer()


# =========================================================
# Handle prompts
# =========================================================
@router.message(F.text)
async def on_text(message: Message):
    state = VIP_STATE.get(message.from_user.id)
    if not state:
        return  # VIP эмес, башка chat handler кармайт

    kind, _ts = state
    prompt = _clean_prompt(message.text)

    u = await _get_user(message.from_user.id, message.from_user.username)

    # Consume credits/limits first (so users can't spam)
    if kind == "video":
        ok = _consume_video(u)
        if not ok:
            VIP_STATE.pop(message.from_user.id, None)
            await message.answer(_need_text("video"), reply_markup=kb_upsell())
            return

        await _save_user(u)
        VIP_STATE.pop(message.from_user.id, None)

        # Generate (stub)
        await message.answer("⏳ Видео даярдап жатам... (demo режим) 😎🎥")
        result_text = await generate_video_stub(prompt=prompt)

        # Style wrap
        styled = tilek_wrap(u, result_text)
        await _save_user(u)
        await message.answer(styled)

    elif kind == "music":
        ok = _consume_music(u, minutes_need=1)
        if not ok:
            VIP_STATE.pop(message.from_user.id, None)
            await message.answer(_need_text("music"), reply_markup=kb_upsell())
            return

        await _save_user(u)
        VIP_STATE.pop(message.from_user.id, None)

        await message.answer("⏳ Музыка жасап жатам... (demo режим) 😎🪉")
        result_text = await generate_music_stub(prompt=prompt, minutes=1)

        styled = tilek_wrap(u, result_text)
        await _save_user(u)
        await message.answer(styled)

    else:
        VIP_STATE.pop(message.from_user.id, None)
        await message.answer("😅 Түшүнбөй калдым. Кайра менюдан тандап көрчү.")


# =========================================================
# Admin tools: give credits
# =========================================================
@router.message(Command("vip_give"))
async def vip_give(message: Message):
    """
    Admin only.
    Usage:
      /vip_give <tg_id> video 5
      /vip_give <tg_id> music 10
    """
    if not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) != 4:
        await message.answer(
            "⚙️ Usage:\n"
            "/vip_give <tg_id> video <n>\n"
            "/vip_give <tg_id> music <minutes>\n\n"
            "Мисал:\n"
            "/vip_give 123456789 video 3"
        )
        return

    tg_id_s, kind, amount_s = parts[1], parts[2].lower(), parts[3]
    if not tg_id_s.isdigit():
        await message.answer("❌ tg_id сан болуш керек.")
        return
    try:
        amount = int(amount_s)
    except Exception:
        await message.answer("❌ amount сан болуш керек.")
        return
    if amount <= 0:
        await message.answer("❌ amount > 0 болуш керек.")
        return

    target_id = int(tg_id_s)
    u = await _get_user(target_id)

    if kind == "video":
        u.vip_video_credits += amount
        await _save_user(u)
        await message.answer(f"✅ Берилди: tg_id={target_id} VIP_VIDEO +{amount}")
    elif kind == "music":
        u.vip_music_minutes += amount
        await _save_user(u)
        await message.answer(f"✅ Берилди: tg_id={target_id} VIP_MUSIC +{amount} мин")
    else:
        await message.answer("❌ kind: video/music гана.")
        return
