from __future__ import annotations

import datetime as dt
from contextlib import suppress

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatMemberStatus

from sqlalchemy import select

from app.config import REQUIRED_CHANNEL, CHANNEL_URL
from app.db import SessionLocal
from app.models import User
from app.utils import utcnow


# ==========================================
# Helper
# ==========================================

def _is_channel_id(val: str) -> bool:
    return val.strip().lstrip("-").isdigit()


# ==========================================
# MAIN MIDDLEWARE
# ==========================================

class ChannelGateMiddleware(BaseMiddleware):
    """
    Бул middleware 4 функция аткарат:

    1) Каналга катталуу текшерүү
    2) FREE блок текшерүү (blocked_until)
    3) План мөөнөтү бүткөнүн текшерүү
    4) Flood control (спам токтотуу)
    """

    async def call(self, handler, event: TelegramObject, data: dict):

        bot = data.get("bot")
        user_obj = data.get("event_from_user")

        if not bot or not user_obj:
            return await handler(event, data)

        user_id = user_obj.id

        # ====================================================
        # 1️⃣ DATABASE USER LOAD / CREATE
        # ====================================================
        async with SessionLocal() as s:
            res = await s.execute(select(User).where(User.tg_id == user_id))
            user = res.scalar_one_or_none()

            if not user:
                user = User(
                    tg_id=user_id,
                    username=user_obj.username
                )
                s.add(user)
                await s.commit()
                await s.refresh(user)

        data["db_user"] = user  # башка handler'лер колдонсун

        # ====================================================
        # 2️⃣ PLAN EXPIRE CHECK
        # ====================================================
        if user.plan != "FREE" and user.plan_until:
            if utcnow() > user.plan_until:
                async with SessionLocal() as s:
                    res = await s.execute(select(User).where(User.tg_id == user_id))
                    u = res.scalar_one_or_none()
                    if u:
                        u.plan = "FREE"
                        u.plan_until = None
                        u.chat_left = 0
                        u.video_left = 0
                        u.music_left = 0
                        u.image_left = 0
                        u.voice_left = 0
                        u.doc_left = 0
                        await s.commit()

                with suppress(Exception):
                    await bot.send_message(
                        user_id,
                        "⏳ Премиум мөөнөтү бүттү, досум.\nFREE режимге кайтып келдиң 😎"
                    )

        # ====================================================
        # 3️⃣ FREE BLOCK CHECK
        # ====================================================
        if user.blocked_until:
            if utcnow() < user.blocked_until:
                remaining = user.blocked_until - utcnow()
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)

                text = (
                    f"🚫 FREE лимит бүттү 😭\n\n"
                    f"⏳ Күтүү: {hours} саат {minutes} мүнөт\n\n"
                    "💎 Премиум ал — дароо ачылат 😎"
                )

                if isinstance(event, Message):
                    await event.answer(text)
                elif isinstance(event, CallbackQuery):
                    await event.message.answer(text)
                    await event.answer()

                return

        # ====================================================
        # 4️⃣ CHANNEL SUBSCRIBE CHECK
        # ====================================================
        if REQUIRED_CHANNEL:

            try:
                chat = (
                    int(REQUIRED_CHANNEL)
                    if _is_channel_id(REQUIRED_CHANNEL)
                    else REQUIRED_CHANNEL
                )

                member = await bot.get_chat_member(chat_id=chat, user_id=user_id)

                if member.status not in (
                    ChatMemberStatus.MEMBER,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.OWNER
                ):
                    raise TelegramBadRequest("Not subscribed")

            except TelegramBadRequest:

                text = (
                    "🚪 Досум, биринчи каналга каттал!\n\n"
                    f"👉 {CHANNEL_URL or REQUIRED_CHANNEL}\n\n"
                    "Катталгандан кийин кайра аракет кыл 😎"
                )

                if isinstance(event, Message):
                    await event.answer(text)
                elif isinstance(event, CallbackQuery):
                    await event.message.answer(text)
                    await event.answer()

                return

            except Exception:
                # канал туура эмес болсо бот токтобошу керек
                pass

        # ====================================================
        # 5️⃣ FLOOD PROTECTION (simple anti spam)
        # ====================================================
        now = utcnow()

        if hasattr(user, "last_action_at") and user.last_action_at:
            delta = (now - user.last_action_at).total_seconds()
            if delta < 1:  # 1 секунда ичинде көп жазса
                if isinstance(event, Message):
                    await event.answer("⏱ Жайыраак досум 😅")
                return

        # save last action
        async with SessionLocal() as s:
            res = await s.execute(select(User).where(User.tg_id == user_id))
            u = res.scalar_one_or_none()
            if u:
                u.last_action_at = now
                await s.commit()

        # ====================================================
        # OK → allow дальше
        # ====================================================
        return await handler(event, data)
