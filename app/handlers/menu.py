# app/handlers/menu.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.keyboards import (
    kb_main,
    kb_premium,
    kb_vip_video,
    kb_vip_music,
)
from app.db import SessionLocal
from app.models import User
from app.style_engine import tilek_card
from app.constants import PLANS

router = Router()


async def _load_user(tg_id: int) -> User:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == tg_id))
        u = res.scalar_one_or_none()
        if not u:
            u = User(tg_id=tg_id)
            s.add(u)
            await s.commit()
            await s.refresh(u)
        return u


def _status_text(u: User) -> str:
    plan = (u.plan or "FREE").upper()
    lang = (u.language or "ky")
    plan_until = u.plan_until.isoformat() if u.plan_until else "—"

    # FREEде chat_left 0 болушу мүмкүн, андыктан көрүнүктүү көрсөтөбүз
    return (
        "📊 Сенин статусуң\n\n"
        f"💎 План: {plan}\n"
        f"⏳ Мөөнөт: {plan_until}\n"
        f"🌐 Тил: {lang}\n\n"
        "📦 Лимиттер (калганы):\n"
        f"• 💬 Чат: {u.chat_left}\n"
        f"• 🎥 Видео: {u.video_left}\n"
        f"• 🪉 Музыка: {u.music_left}\n"
        f"• 🖼 Сүрөт: {u.image_left}\n"
        f"• 🔊 Үн: {u.voice_left}\n"
        f"• 📄 Документ: {u.doc_left}\n\n"
        "🎟 VIP кредиттер:\n"
        f"• 🎥 VIP Video: {u.vip_video_credits}\n"
        f"• 🪉 VIP Music: {u.vip_music_minutes} мин\n\n"
        f"🎁 Реф баланс: ${float(u.ref_balance_usd or 0):.2f}\n"
    )


async def _edit_or_send(call: CallbackQuery, text: str, kb=None):
    """
    Telegram кээде edit_text'ке уруксат бербей калат (message too old, no rights, etc.)
    Ошондо send кылып жиберебиз.
    """
    try:
        await call.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        await call.message.answer(text, reply_markup=kb, disable_web_page_preview=True)


# =========================
# MAIN MENU
# =========================
@router.callback_query(F.data == "m:back")
async def back(call: CallbackQuery):
    await _edit_or_send(call, "🏠 Башкы меню\nТанда, досум 😎", kb_main())
    await call.answer()


@router.callback_query(F.data == "m:status")
async def status(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    text = tilek_card(u, _status_text(u))
    await _edit_or_send(call, text, kb_main())
    await call.answer()


# =========================
# PREMIUM / VIP MENUS
# =========================
@router.callback_query(F.data == "m:premium")
async def premium(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    plus = PLANS.get("PLUS")
    pro = PLANS.get("PRO")

    text = (
        "💎 Премиум меню\n\n"
        "Бул жерде күч ачылат 😈⚡\n\n"
        f"✅ PLUS — ${plus.price_usd:.2f}/ай\n"
        f"• 💬 {plus.monthly_chat} чат\n"
        f"• 🎥 {plus.monthly_video} видео\n"
        f"• 🪉 {plus.monthly_music} музыка\n\n"
        f"🔴 PRO — ${pro.price_usd:.2f}/ай\n"
        f"• 💬 {pro.monthly_chat} чат\n"
        f"• 🎥 {pro.monthly_video} видео\n"
        f"• 🪉 {pro.monthly_music} музыка\n\n"
        "🎥 VIP VIDEO / 🪉 VIP MUSIC — айлык лимитке кирбейт (кредит менен) 💰"
    )

    text = tilek_card(u, text)
    await _edit_or_send(call, text, kb_premium())
    await call.answer()


@router.callback_query(F.data == "m:vip_video")
async def vip_video(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    text = (
        "🎥 VIP VIDEO\n\n"
        "Бул — кино деңгээл 😎🎬\n"
        "• Айлык лимитке кирбейт\n"
        "• Кредит болуп сакталат\n\n"
        "Пакет танда:"
    )
    text = tilek_card(u, text)
    await _edit_or_send(call, text, kb_vip_video())
    await call.answer()


@router.callback_query(F.data == "m:vip_music")
async def vip_music(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    text = (
        "🪉 VIP MUSIC\n\n"
        "Бул — проф трек 😈🎧\n"
        "• Айлык лимитке кирбейт\n"
        "• Минут болуп сакталат\n\n"
        "Пакет танда:"
    )
    text = tilek_card(u, text)
    await _edit_or_send(call, text, kb_vip_music())
    await call.answer()


# =========================
# QUICK ACTIONS
# =========================
@router.callback_query(F.data == "m:chat")
async def go_chat(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    text = tilek_card(u, "💬 Чат режим\nСурооңду жазчы, досум 😎✍️")
    await call.message.answer(text)
    await call.answer()


@router.callback_query(F.data == "m:video")
async def go_video(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    text = tilek_card(
        u,
        "🎥 Видео режим\n"
        "Тема жаз:\n"
        "Мисал: *кыргыз тоолору, ат минген баатыр, кино стиль* 😎"
    )
    await call.message.answer(text)
    await call.answer()


@router.callback_query(F.data == "m:music")
async def go_music(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    text = tilek_card(
        u,
        "🪉 Музыка режим\n"
        "Тема жаз:\n"
        "Мисал: *мотивация beats, бизнес энергия, 120bpm* 😈"
    )
    await call.message.answer(text)
    await call.answer()


@router.callback_query(F.data == "m:lang")
async def change_lang(call: CallbackQuery):
    u = await _load_user(call.from_user.id)
    text = tilek_card(
        u,
        "🌐 Тил өзгөртүү\n\n"
        "Тилди/өлкөнү кайра тандоо үчүн:\n"
        "👉 /start басып кайра өт 😎"
    )
    await call.message.answer(text)
    await call.answer()
