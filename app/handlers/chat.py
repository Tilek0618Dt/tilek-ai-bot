from __future__ import annotations

import datetime as dt
from typing import Optional, Literal

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.constants import FREE_DAILY_QUESTIONS, BLOCK_HOURS_FREE, PLANS
from app.utils import utcnow, minutes_left
from app.style_engine import tilek_wrap, limit_ad_text, soft_error_text
from app.keyboards import kb_main, kb_premium
from app.services.grok import grok_chat

router = Router()

Mode = Literal["chat", "video", "music", "image", "voice", "doc"]

# ---------------------------
# In-memory UX state (MVP)
# NOTE: restart болгондо тазаланат. Кийин DB'га кошобуз.
# ---------------------------
_user_mode: dict[int, Mode] = {}
_last_msg_at: dict[int, dt.datetime] = {}


def _set_mode(tg_id: int, mode: Mode) -> None:
    _user_mode[tg_id] = mode


def _get_mode(tg_id: int) -> Mode:
    return _user_mode.get(tg_id, "chat")


def _flood_ok(tg_id: int) -> bool:
    """Simple anti-spam: 1.2 сек ичинде кайра жазса - токтотот."""
    now = utcnow()
    prev = _last_msg_at.get(tg_id)
    _last_msg_at[tg_id] = now
    if not prev:
        return True
    return (now - prev).total_seconds() >= 1.2


async def _load_or_create_user(m: Message) -> User:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == m.from_user.id))
        u = res.scalar_one_or_none()
        if u:
            # update username sometimes
            if m.from_user.username and u.username != m.from_user.username:
                u.username = m.from_user.username
                u.updated_at = utcnow()
                await s.commit()
            return u

        u = User(
            tg_id=m.from_user.id,
            username=m.from_user.username,
            plan="FREE",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u


def _is_blocked(u: User) -> bool:
    return bool(u.blocked_until and utcnow() < u.blocked_until)


def _is_premium(u: User) -> bool:
    return u.plan in ("PLUS", "PRO")


async def _save_user(u: User) -> None:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == u.tg_id))
        dbu = res.scalar_one_or_none()
        if not dbu:
            return
        # copy mutable fields we change here
        dbu.plan = u.plan
        dbu.plan_until = u.plan_until
        dbu.chat_left = u.chat_left
        dbu.video_left = u.video_left
        dbu.music_left = u.music_left
        dbu.image_left = u.image_left
        dbu.voice_left = u.voice_left
        dbu.doc_left = u.doc_left
        dbu.free_today_count = u.free_today_count
        dbu.free_day_key = u.free_day_key
        dbu.blocked_until = u.blocked_until
        dbu.style_counter = u.style_counter
        dbu.vip_video_credits = u.vip_video_credits
        dbu.vip_music_minutes = u.vip_music_minutes
        dbu.updated_at = utcnow()
        await s.commit()


# ---------------------------
# Menu actions: set mode
# ---------------------------
@router.callback_query(F.data == "m:chat")
async def cb_chat(call: CallbackQuery):
    _set_mode(call.from_user.id, "chat")
    await call.message.answer("💬 Досум, сурооңду жаза бер 😎", reply_markup=kb_main())
    await call.answer()


@router.callback_query(F.data == "m:video")
async def cb_video(call: CallbackQuery):
    _set_mode(call.from_user.id, "video")
    await call.message.answer(
        "🎥 Досум, видео үчүн тема жаз:\n"
        "Мисал: *кыргыз тоолору, кинематографик, slow motion*\n\n"
        "⚠️ VIP VIDEO кредит керек (пакет менен алынат).",
        reply_markup=kb_main()
    )
    await call.answer()


@router.callback_query(F.data == "m:music")
async def cb_music(call: CallbackQuery):
    _set_mode(call.from_user.id, "music")
    await call.message.answer(
        "🪉 Досум, музыка үчүн тема жаз:\n"
        "Мисал: *мотивация trap beat, кыргыз вайб, 120 bpm*\n\n"
        "⚠️ VIP MUSIC минут керек (пакет менен алынат).",
        reply_markup=kb_main()
    )
    await call.answer()


@router.callback_query(F.data == "m:image")
async def cb_image(call: CallbackQuery):
    _set_mode(call.from_user.id, "image")
    await call.message.answer("🖼 Досум, сүрөт үчүн prompt жаз (кейин интеграциялайбыз) 😎", reply_markup=kb_main())
    await call.answer()


@router.callback_query(F.data == "m:voice")
async def cb_voice(call: CallbackQuery):
    _set_mode(call.from_user.id, "voice")
    await call.message.answer("🔊 Досум, үн үчүн текст жаза бер (кейин ElevenLabs кошобуз) 😎", reply_markup=kb_main())
    await call.answer()


@router.callback_query(F.data == "m:doc")
async def cb_doc(call: CallbackQuery):
    _set_mode(call.from_user.id, "doc")
    await call.message.answer("📄 Досум, документ боюнча суроо жаза бер (кийин PDF анализ кошобуз) 😎", reply_markup=kb_main())
    await call.answer()


# ---------------------------
# Quick user stats
# ---------------------------
@router.message(F.text.in_({"/me", "/profile"}))
async def me(m: Message):
    u = await _load_or_create_user(m)
    text = (
        f"👤 *Профиль*\n\n"
        f"• План: *{u.plan}*\n"
        f"• Chat left: *{u.chat_left}*\n"
        f"• VIP VIDEO: *{u.vip_video_credits}*\n"
        f"• VIP MUSIC min: *{u.vip_music_minutes}*\n"
    )
    if _is_blocked(u):
        text += f"\n⛔ FREE блок: *{minutes_left(u.blocked_until)} мүнөт* калды\n"
    await m.answer(text, reply_markup=kb_main())


# ---------------------------
# Main text handler
# ---------------------------
@router.message(F.text)
async def on_text(m: Message):
    # anti spam
    if not _flood_ok(m.from_user.id):
        await m.answer("🐌 Досум жайыраак 😅 1 секунд күтө тур.")
        return

    u = await _load_or_create_user(m)

    # block check
    if _is_blocked(u):
        left = minutes_left(u.blocked_until)
        await m.answer(
            f"⛔ Досум, FREE блок актив 😭\n"
            f"⏳ Калганы: *{left} мүнөт*\n\n"
            f"{limit_ad_text()}",
            reply_markup=kb_premium()
        )
        return

    mode = _get_mode(m.from_user.id)
    prompt = (m.text or "").strip()
    if not prompt:
        await m.answer("😅 Досум, текст жаза салчы.")
        return

    # ==========
    # 1) CHAT MODE
    # ==========
    if mode == "chat":
        # premium limits
        if _is_premium(u):
            if u.chat_left <= 0:
                await m.answer("🚫 Айлык чат лимит бүттү 😭\n\n" + limit_ad_text(), reply_markup=kb_premium())
                return
            u.chat_left -= 1
        else:
            # FREE daily limit
            if u.free_today_count >= FREE_DAILY_QUESTIONS:
                u.blocked_until = utcnow() + dt.timedelta(hours=BLOCK_HOURS_FREE)
                await _save_user(u)
                await m.answer(limit_ad_text(), reply_markup=kb_premium())
                return
            u.chat_left -= 1
        else:
            # FREE daily limit
            if u.free_today_count >= FREE_DAILY_QUESTIONS:
                u.blocked_until = utcnow() + dt.timedelta(hours=BLOCK_HOURS_FREE)
                await _save_user(u)
                await m.answer(limit_ad_text(), reply_markup=kb_premium())
                return
            u.free_today_count += 1

        try:
            ai = await grok_chat(prompt, lang=u.language or "ky", is_pro=(u.plan == "PRO"))
        except Exception:
            await m.answer(soft_error_text(), reply_markup=kb_main())
            return

        styled = tilek_wrap(u, ai)
        await _save_user(u)
        await m.answer(styled, reply_markup=kb_main())
        return

    # ==========
    # 2) VIDEO MODE (VIP credit required)
    # ==========
    if mode == "video":
        if u.vip_video_credits <= 0:
            await m.answer(
                "🎥 Досум, VIP VIDEO кредит жок 😭\n\n"
                "👉 «💎 Премиум» → «VIP VIDEO пакет» тандап сатып ал 😎",
                reply_markup=kb_premium()
            )
            return

        # MVP: азырынча генерация stub (real API кийин services/media/runway.py)
        u.vip_video_credits -= 1
        await _save_user(u)
        await m.answer(
            "🎬 *Видео заказ кабыл алынды!* 😎\n\n"
            f"📌 Тема: {prompt}\n"
            "⏳ Азырынча MVP режим: API кошулганда видео файл келип түшөт.\n\n"
            "✅ VIP VIDEO кредит: -1",
            reply_markup=kb_main()
        )
        return

    # ==========
    # 3) MUSIC MODE (VIP minutes required)
    # ==========
    if mode == "music":
        if u.vip_music_minutes <= 0:
            await m.answer(
                "🪉 Досум, VIP MUSIC минут жок 😭\n\n"
                "👉 «💎 Премиум» → «VIP MUSIC пакет» тандап сатып ал 😎",
                reply_markup=kb_premium()
            )
            return

        # MVP: азырынча 1 суроо = 1 мин деп алабыз (кийин duration параметр кошобуз)
        u.vip_music_minutes -= 1
        await _save_user(u)
        await m.answer(
            "🎧 *Музыка заказ кабыл алынды!* 😎\n\n"
            f"📌 Тема: {prompt}\n"
            "⏳ Азырынча MVP режим: API кошулганда mp3 файл келет.\n\n"
            "✅ VIP MUSIC минут: -1",
            reply_markup=kb_main()
        )
        return

    # ==========
    # Other modes: placeholders
    # ==========
    await m.answer(
        "🧩 Досум бул модуль азырынча *MVP placeholder*.\n"
        "Кийинки кадамда сервис API кошуп беребиз 😎",
        reply_markup=kb_main()
    )
