# app/handlers/referral.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.config import CHANNEL_URL
from app.constants import REF_BONUS_USD, REF_FREE_PLUS_DAYS, REF_FREE_PLUS_MIN_PAID_USD

router = Router(name="referral_router")


# -----------------------------
# Helpers
# -----------------------------
def _kb_ref(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Ссылканы бөлүшүү", url=f"https://t.me/share/url?url={link}")],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="m:premium"),
         InlineKeyboardButton(text="🆘 Жардам", callback_data="m:support")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:back")],
    ])

def _kb_withdraw() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Балансты чыгаруу (Soon)", callback_data="ref:withdraw")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:ref")],
    ])

def _fmt_money(x: float) -> str:
    return f"${x:.2f}"

def _ref_text(u: User, link: str) -> str:
    invited_by = f"{u.referrer_tg_id}" if u.referrer_tg_id else "—"
    channel = CHANNEL_URL or "—"

    return (
        "🎁 РЕФЕРАЛ СИСТЕМА (Tilek Growth Engine)\n\n"
        "😎 Досум, сенин ишиң — ссылка таратуу.\n"
        "Менин ишим — сатуу, бонус берүү, системаны айлантуу 💎\n\n"
        f"🔗 Сенин ссылкаң:\n{link}\n\n"
        "📊 Сенин статустар:\n"
        f"💰 Баланс: {_fmt_money(float(u.ref_balance_usd or 0.0))}\n"
        f"👤 Сени чакырган: {invited_by}\n"
        f"🎥 VIP Video кредит: {u.vip_video_credits}\n"
        f"🪉 VIP Music минут: {u.vip_music_minutes}\n\n"
        "⚡ Эреже (кыскача):\n"
        f"✅ Досуң PLUS сатып алса → сага +{_fmt_money(float(REF_BONUS_USD))}\n"
        f"✅ Досуң {_fmt_money(float(REF_FREE_PLUS_MIN_PAID_USD))}+ төлөсө → сага {REF_FREE_PLUS_DAYS} күн PLUS\n"
        "❌ PRO бекер берилбейт (бизнес жашасын 😅)\n\n"
        f"📣 Канал: {channel}\n\n"
        "💡 Кеңеш (сатканча):\n"
        "Ссылканы 5–10 доско ташта → 1өө төлөйт → сен бонус аласың.\n"
        "Система ушундай иштейт, досум 😈💎"
    )

async def _get_user(tg_id: int, username: str | None) -> User:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == tg_id))
        u = res.scalar_one_or_none()
        if not u:
            u = User(tg_id=tg_id, username=username)
            s.add(u)
            await s.commit()
            await s.refresh(u)
        return u


# -----------------------------
# Main referral screen
# -----------------------------
@router.callback_query(F.data == "m:ref")
async def ref_menu(call: CallbackQuery):
    u = await _get_user(call.from_user.id, call.from_user.username)

    # bot.username must exist (polling mode)
    bot_username = (call.bot.username or "").strip()
    if not bot_username:
        await call.message.answer("⚠️ Бот username табылган жок. BotFather’ден username кой 😅")
        await call.answer()
        return

    link = f"https://t.me/{bot_username}?start={call.from_user.id}"

    await call.message.answer(
        _ref_text(u, link),
        reply_markup=_kb_ref(link),
        disable_web_page_preview=True
    )
    await call.answer()


# -----------------------------
# Withdraw placeholder (future)
# -----------------------------
@router.callback_query(F.data == "ref:withdraw")
async def withdraw_info(call: CallbackQuery):
    await call.message.answer(
        "💸 Балансты чыгаруу (Soon)\n\n"
        "Досум, азырынча бул функцияны кийин кошобуз.\n"
        "Азыр эң күчтүү нерсе — рефералды көп кылуу 😎\n\n"
        "📌 План:\n"
        "1) Баланс ≥ $20 болгондо чыгаруу ачылат\n"
        "2) Админ текшерет (anti-fraud)\n"
        "3) Карта/крипто/юmoney вариант чыгарабыз\n\n"
        "Азыр болсо: ссылка тарат → бонус чогулт → масштаб 😈💎",
        reply_markup=_kb_withdraw(),
        disable_web_page_preview=True
    )
    await call.answer()
