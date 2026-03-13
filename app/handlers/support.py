# app/handlers/support.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from app.config import SUPPORT_ADMINS, ADMIN_IDS
from app.keyboards import kb_main  # сенде бар болсо
from app.style_engine import limit_ad_text  # бар болсо (жок болсо алып сал)


router = Router()

# =========================================================
# In-memory state (MVP). Кийин DB/Redis кылабыз.
# =========================================================
# user_id -> state
SUPPORT_STATE: Dict[int, bool] = {}  # True = waiting message
# anti-spam: user_id -> last_ticket_ts
LAST_TICKET_TS: Dict[int, float] = {}

# admin reply map: admin_message_id -> user_id (reply routing)
ADMIN_REPLY_MAP: Dict[Tuple[int, int], int] = {}  # (admin_id, msg_id) -> user_id


# =========================================================
# UX keyboards
# =========================================================
def kb_support_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✍️ Support'ка жазуу", callback_data="support:write")],
        [InlineKeyboardButton(text="📌 Эреже / FAQ", callback_data="support:faq")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_support_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="support:cancel")],
            [InlineKeyboardButton(text="⬅️ Башкы меню", callback_data="m:back")],
        ]
    )


# =========================================================
# Helpers
# =========================================================
def _admins_text() -> str:
    # SUPPORT_ADMINS: ["@Timka_Bro999", "@Mentor_006T"]
    if SUPPORT_ADMINS:
        return "\n".join([f"• {a}" for a in SUPPORT_ADMINS])
    return "• (админдер кошула элек 😅)"


def _can_create_ticket(user_id: int, cooldown_sec: int = 60) -> bool:
    last = LAST_TICKET_TS.get(user_id, 0.0)
    return (time.time() - last) >= cooldown_sec


def _mark_ticket(user_id: int) -> None:
    LAST_TICKET_TS[user_id] = time.time()


def _is_admin(user_id: int) -> bool:
    return user_id in (ADMIN_IDS or [])


def _safe_text(s: str, max_len: int = 3500) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 50].rstrip() + "\n\n…(кыска кесилди) 😅"


async def _notify_admins(bot, text: str, user: Message, original: Message) -> int:
    """
    Send ticket to admins. Returns count sent.
    """
    sent = 0
    for admin in (ADMIN_IDS or []):
        try:
            msg = await bot.send_message(admin, text)
            # admin reply map: (admin_id, bot_msg_id) -> user_id
            ADMIN_REPLY_MAP[(admin, msg.message_id)] = user.from_user.id
            sent += 1
        except Exception:
            pass
    return sent


# =========================================================
# Entry point from menu
# =========================================================
@router.callback_query(F.data == "m:support")
async def support_entry(call: CallbackQuery):
    text = (
        "🆘 Support / Жардам\n\n"
        "Досум, маселе болсо — мага жаз да, мен админдерге жеткирип берем 😎\n\n"
        f"👨‍💻 Админдер:\n{_admins_text()}\n\n"
        "Төмөндөн танда 👇"
    )
    await call.message.answer(text, reply_markup=kb_support_menu())
    await call.answer()


@router.callback_query(F.data == "support:faq")
async def support_faq(call: CallbackQuery):
    text = (
        "📌 FAQ / Эреже\n\n"
        "1) Төлөм төлөдүң, бирок ачылган жокпу?\n"
        "   → Төлөмдүн скриншотун + order_id жибер.\n\n"
        "2) Лимит бүтүп калдыбы?\n"
        "   → FREE: 10 суроо/күн, анан 6 саат блок.\n"
        "   → PLUS/PRO: ай сайын reset.\n\n"
        "3) Бот жооп бербей жатабы?\n"
        "   → 1 мүнөттөн кийин кайра аракет кыл.\n\n"
        "💡 Кеңеш:\n"
        "Канча так жазсаң — ошончо тез чечилет 😎"
    )
    await call.message.answer(text, reply_markup=kb_support_menu())
    await call.answer()


@router.callback_query(F.data == "support:write")
async def support_write(call: CallbackQuery):
    uid = call.from_user.id

    # anti-spam
    if not _can_create_ticket(uid, cooldown_sec=60):
        await call.message.answer("⏳ Досум, 1 мүнөт күтүп кайра жазчы 😅", reply_markup=kb_support_menu())
        await call.answer()
        return

    SUPPORT_STATE[uid] = True
    await call.message.answer(
        "✍️ Досум, маселенди 1 билдирүү кылып жаз:\n\n"
        "✅ Эң жакшы формат:\n"
        "1) Эмне болду?\n"
        "2) Кайсы убакта?\n"
        "3) Скрин/чек болсо кош\n\n"
        "Жазып жибер — мен админге дароо өткөрөм 😎",
        reply_markup=kb_support_cancel()
    )
    await call.answer()


@router.callback_query(F.data == "support:cancel")
async def support_cancel(call: CallbackQuery):
    SUPPORT_STATE.pop(call.from_user.id, None)
    await call.message.answer("❌ Жардам режими токтотулду. Башкы менюга кайттык 😎", reply_markup=kb_main())
    await call.answer()


# =========================================================
# User sends message while in support mode
# =========================================================
@router.message(F.text)
async def support_catch_text(message: Message):
    uid = message.from_user.id
    if not SUPPORT_STATE.get(uid):
        return  # бул support эмес, башка handler кармайт

    SUPPORT_STATE.pop(uid, None)
    _mark_ticket(uid)

    username = f"@{message.from_user.username}" if message.from_user.username else "(username жок)"
    meta = (
        f"🆘 Жаңы тикет\n\n"
        f"👤 User: {message.from_user.full_name} {username}\n"
        f"🆔 tg_id: {uid}\n"
        f"🕒 time: {int(time.time())}\n\n"
        f"📩 Текст:\n{_safe_text(message.text)}\n\n"
        "↩️ Админ: ушул билдирүүгө *Reply* кылсаң — бот user'ге жоопту жиберет."
    )

    sent = await _notify_admins(message.bot, meta, message, message)
    if sent <= 0:
        await message.answer("😅 Азыр админдер жеткиликсиз болуп жатат. Кийинчерээк кайра жазып көр, досум.")
        return

    await message.answer("✅ Досум, жөнөттүм! Админ жакында жооп берет 😎🫂", reply_markup=kb_main())


# =========================================================
# User can also send photo/document (support mode)
# =========================================================
@router.message(F.photo | F.document)
async def support_catch_media(message: Message):
    uid = message.from_user.id
    if not SUPPORT_STATE.get(uid):
        return

    SUPPORT_STATE.pop(uid, None)
    _mark_ticket(uid)

    username = f"@{message.from_user.username}" if message.from_user.username else "(username жок)"
    caption = _safe_text(message.caption or "")

    meta = (
        f"🆘 Жаңы тикет (media)\n\n"
        f"👤 User: {message.from_user.full_name} {username}\n"
        f"🆔 tg_id: {uid}\n"
        f"📎 Type: photo/document\n\n"
        f"📝 Caption:\n{caption if caption else '(жок)'}\n\n"
        "↩️ Админ: ушул билдирүүгө *Reply* кылсаң — бот user'ге жоопту жиберет."
    )

    sent = 0
    for admin in (ADMIN_IDS or []):
        try:
            # forward media first
            fwd = await message.forward(admin)
            ADMIN_REPLY_MAP[(admin, fwd.message_id)] = uid
            # then send meta
            msg = await message.bot.send_message(admin, meta)
            ADMIN_REPLY_MAP[(admin, msg.message_id)] = uid
            sent += 1
        except Exception:
            pass

    if sent <= 0:
        await message.answer("😅 Азыр админдер жеткиликсиз. Кийинчерээк кайра жиберчи, досум.")
        return

    await message.answer("✅ Досум, скрин/файл да кетти! Админ көрүп жооп берет 😎🫂", reply_markup=kb_main())


# =========================================================
# Admin replies to support ticket -> send to user
# =========================================================
@router.message(F.reply_to_message)
async def admin_reply_router(message: Message):
    """
    Admin can reply to bot's ticket message or forwarded message.
    Bot will deliver reply to the original user.
    """
    if not _is_admin(message.from_user.id):
        return

    reply = message.reply_to_message
    if not reply:
        return

    key = (message.from_user.id, reply.message_id)
    user_id = ADMIN_REPLY_MAP.get(key)
    if not user_id:
        return  # бул reply support тикет эмес

    text = _safe_text(message.text or "")
    if not text:
        await message.answer("😅 Текст жок болуп калды. Жөн эле текст менен reply кылчы.")
        return

    out = (
        "🆘 Support жооп\n\n"
        f"{text}\n\n"
        "— Админ ✅"
    )

    try:
        await message.bot.send_message(user_id, out)
        await message.answer("✅ Жооп user'ге кетти.")
    except TelegramBadRequest:
        await message.answer("⚠️ User ботту блоктоп койгон окшойт.")
    except Exception:
        await message.answer("⚠️ Жооп жөнөтүүдө ката болду.")
