# app/handlers/start.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.keyboards import kb_main
from app.utils import utcnow, day_key_utc
from app.data.countries import COUNTRIES, DEFAULT_LANG  # сенде 100+ болушу керек
from app.config import CHANNEL_URL, REQUIRED_CHANNEL

router = Router(name="start_router")

PER_PAGE = 12


# -----------------------------
# DB helpers
# -----------------------------
async def _get_or_create_user(tg_id: int, username: str | None, referrer: int | None) -> User:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == tg_id))
        u = res.scalar_one_or_none()

        if not u:
            u = User(
                tg_id=tg_id,
                username=username,
                language=DEFAULT_LANG or "ky",
                free_day_key=day_key_utc(),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            if referrer and referrer != tg_id:
                u.referrer_tg_id = referrer
            s.add(u)
            await s.commit()
            await s.refresh(u)
            return u

        # update username if changed
        if username and (u.username != username):
            u.username = username
            u.updated_at = utcnow()

        # save referrer only if empty (бир жолу гана)
        if referrer and referrer != tg_id and not u.referrer_tg_id:
            u.referrer_tg_id = referrer
            u.updated_at = utcnow()

        await s.commit()
        return u


# -----------------------------
# UX helpers
# -----------------------------
def _kb_onboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Тил/Өлкө тандоо (100+)", callback_data="lang:page:0")],
        [InlineKeyboardButton(text="⚡ Дароо баштайм (Skip)", callback_data="lang:skip")],
    ])

def _slice_countries(page: int):
    # COUNTRIES: dict like {"KG": {"name":"Kyrgyzstan","flag":"🇰🇬","lang":"ky"}, ...}
    items = list(COUNTRIES.items())
    total = len(items)
    start = page * PER_PAGE
    end = start + PER_PAGE
    return items[start:end], total

def _kb_lang_page(page: int) -> InlineKeyboardMarkup:
    chunk, total = _slice_countries(page)
    rows: list[list[InlineKeyboardButton]] = []

    row: list[InlineKeyboardButton] = []
    for code, info in chunk:
        name = info.get("name", code)
        flag = info.get("flag", "🌐")
        row.append(InlineKeyboardButton(
            text=f"{flag} {name}",
            callback_data=f"lang:set:{code}:{page}"
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"lang:page:{page-1}"))
    if (page + 1) * PER_PAGE < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"lang:page:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="⚡ Skip", callback_data="lang:skip")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _onboarding_text(first_time: bool = True) -> str:
    if first_time:
        return (
            "😎 Салам досум! TILEK AI’ге кош келдиң!\n\n"
            "Мен сенин Telegram’деги AI досуңмун:\n"
            "💬 Чат — түшүнүктүү план менен\n"
            "🎥 Видео — VIP кредит менен\n"
            "🪉 Музыка — минут менен\n"
            "📌 Баары бизнес режимде иштейт 💎\n\n"
            "🌍 Биринчи кадам: тилди/өлкөңдү танда (100+).\n"
            "Кааласаң Skip кылып дароо баштай берсең да болот 😈"
        )
    return (
        "😎 Досум кайра келдиң!\n"
        "🌍 Тилди өзгөртөбүзбү же дароо баштайбызбы?"
    )

def _ready_text() -> str:
    return (
        "✅ Даяр!\n\n"
        "Эми менюдан танда:\n"
        "💬 Чат, 🎥 Видео, 🪉 Музыка, 🖼 Сүрөт...\n\n"
        "😈 Досум, суроо бер — мен план кылып жооп берем 💎"
    )

def _soft_channel_hint() -> str:
    # Middleware gate сенде бар, бирок бул “жумшак” hint
    if not REQUIRED_CHANNEL:
        return ""
    return (
        "\n\n"
        "📣 Эскертүү: каналга катталбасаң айрым функциялар жабык болушу мүмкүн.\n"
        f"👉 {CHANNEL_URL or REQUIRED_CHANNEL}"
    )


# -----------------------------
# /start
# -----------------------------
@router.message(CommandStart(deep_link=True))
@router.message(CommandStart())
async def start(message: Message):
    # parse referral id: /start 12345
    referrer = None
    parts = (message.text or "").split()
    if len(parts) > 1 and parts[1].isdigit():
        referrer = int(parts[1])

    # create / update user
    u = await _get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        referrer=referrer
    )

    # First time heuristic: if country_code is empty => onboarding
    first_time = not bool(u.country_code)

    await message.answer(
        _onboarding_text(first_time=first_time) + _soft_channel_hint(),
        reply_markup=_kb_onboard(),
        disable_web_page_preview=True
    )


# -----------------------------
# Language pagination
# -----------------------------
@router.callback_query(F.data.startswith("lang:page:"))
async def lang_page(call: CallbackQuery):
    page = int(call.data.split(":")[-1])
    await call.message.edit_text(
        "🌍 Өлкө/тил танда (100+)\n\n"
        "Тандалгандан кийин мен жоопторду ошол тилге ылайыктап берем 😎",
        reply_markup=_kb_lang_page(page),
        disable_web_page_preview=True
    )
    await call.answer()


@router.callback_query(F.data.startswith("lang:set:"))
async def lang_set(call: CallbackQuery):
    _, _, code, page = call.data.split(":")
    info = COUNTRIES.get(code)

    if not info:
        await call.answer("Ката 😅", show_alert=True)
        return

    lang = info.get("lang", "ky")
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == call.from_user.id))
        u = res.scalar_one_or_none()
        if not u:
            u = User(tg_id=call.from_user.id, username=call.from_user.username)
            s.add(u)
            await s.flush()

        u.country_code = code
        u.language = lang
        u.updated_at = utcnow()
        await s.commit()

    await call.message.answer(
        f"✅ Тандалды: {info.get('flag','🌐')} {info.get('name', code)}\n"
        f"🗣 Тил: {lang}\n\n"
        f"{_ready_text()}",
        reply_markup=kb_main(),
        disable_web_page_preview=True
    )
    await call.answer()


@router.callback_query(F.data == "lang:skip")
async def lang_skip(call: CallbackQuery):
    # leave default language, just go to main
    await call.message.answer(_ready_text(), reply_markup=kb_main())
    await call.answer()
