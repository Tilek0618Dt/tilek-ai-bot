# app/handlers/premium.py
from __future__ import annotations

import uuid
from contextlib import suppress

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User, Invoice
from app.constants import PLANS, VIP_VIDEO_PACKS, VIP_MUSIC_PACKS_MINUTES
from app.config import PUBLIC_BASE_URL
from app.keyboards import kb_premium, kb_vip_video, kb_vip_music, kb_main
from app.services.cryptomus import create_invoice

router = Router(name="premium_router")


# -----------------------------
# Small helpers
# -----------------------------
def _money(x: float) -> str:
    return f"${x:.2f}"

def _plan_card(u: User) -> str:
    # Кыска, сатканча сүйлөгөн статус
    if u.plan in ("PLUS", "PRO"):
        until = u.plan_until.isoformat()[:10] if u.plan_until else "—"
        return (
            f"✅ Сенде азыр: {u.plan}\n"
            f"⏳ Мөөнөт: {until}\n\n"
            f"📌 Калган лимиттер:\n"
            f"💬 Чат: {u.chat_left}\n"
            f"🎥 Видео: {u.video_left}\n"
            f"🪉 Музыка: {u.music_left}\n"
            f"🖼 Сүрөт: {u.image_left}\n"
            f"🔊 Үн: {u.voice_left}\n"
            f"📄 Док: {u.doc_left}\n\n"
            f"🎥 VIP Video кредит: {u.vip_video_credits}\n"
            f"🪉 VIP Music минут: {u.vip_music_minutes}"
        )
    return (
        "🆓 Сен азыр FREE’десиң.\n"
        "Күч ачыш үчүн PLUS/PRO же VIP алсаң — бот “ракета” болот 😎🚀"
    )

async def _get_user(tg_id: int, username: str | None = None) -> User:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == tg_id))
        u = res.scalar_one_or_none()
        if not u:
            u = User(tg_id=tg_id, username=username)
            s.add(u)
            await s.commit()
            await s.refresh(u)
        return u

async def _save_invoice(tg_id: int, kind: str, amount: float, pay_url: str | None) -> None:
    async with SessionLocal() as s:
        inv = Invoice(
            order_id=f"{kind}-{tg_id}-{uuid.uuid4().hex[:10]}",
            tg_id=tg_id,
            kind=kind,
            amount_usd=float(amount),
            status="created",
            payment_url=pay_url,
        )
        s.add(inv)
        await s.commit()


def _kb_pay(pay_url: str, order_id: str) -> InlineKeyboardMarkup:
    # “Төлөө” + “Текшерүү” + “Артка”
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ТӨЛӨӨ (Cryptomus)", url=pay_url)],
        [InlineKeyboardButton(text="🔎 Төлөмдү текшерүү", callback_data=f"paycheck:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:premium")],
    ])


# -----------------------------
# Premium menu
# -----------------------------
@router.callback_query(F.data == "m:premium")
async def premium_menu(call: CallbackQuery):
    u = await _get_user(call.from_user.id, call.from_user.username)
    text = (
        "💎 ПРЕМИУМ ДҮКӨН\n\n"
        f"{_plan_card(u)}\n\n"
        "🔥 Эмне үчүн Premium?\n"
        "• FREE лимит бат бүтөт\n"
        "• PLUS/PRO болсоң — күнүң жеңил 😎\n"
        "• VIP болсо — кино/проф трек 🔥\n\n"
        "Танда, досум:"
    )
    await call.message.edit_text(text, reply_markup=kb_premium(), disable_web_page_preview=True)
    await call.answer()


@router.callback_query(F.data == "m:vip_video")
async def premium_vip_video(call: CallbackQuery):
    await call.message.edit_text(
        "🎥 VIP VIDEO пакеттер\n\n"
        "Бул пакет айлык лимитке кирбейт ✅\n"
        "Runway/Kling кино стиль — эң чоң күч 😈🎬\n\n"
        "Танда:",
        reply_markup=kb_vip_video(),
        disable_web_page_preview=True
    )
    await call.answer()


@router.callback_query(F.data == "m:vip_music")
async def premium_vip_music(call: CallbackQuery):
    await call.message.edit_text(
        "🪉 VIP MUSIC пакеттер\n\n"
        "Бул пакет айлык лимитке кирбейт ✅\n"
        "Минут менен эсептелет (проф трек) 🎧🔥\n\n"
        "Танда:",
        reply_markup=kb_vip_music(),
        disable_web_page_preview=True
    )
    await call.answer()


# -----------------------------
# BUY: Plan / VIP
# -----------------------------
async def _mk_invoice(call: CallbackQuery, kind: str, amount: float) -> tuple[str | None, str]:
    """
    Returns: (pay_url, order_id)
    """
    order_id = f"{kind}-{call.from_user.id}-{uuid.uuid4().hex[:10]}"
    callback_url = f"{PUBLIC_BASE_URL}/cryptomus/webhook"

    data = await create_invoice(amount_usd=float(amount), order_id=order_id, callback_url=callback_url)

    pay_url = None
    if isinstance(data, dict):
        result = data.get("result") or {}
        pay_url = result.get("url") or result.get("pay_url") or result.get("payment_url")

    # Save invoice
    async with SessionLocal() as s:
        inv = Invoice(
            order_id=order_id,
            tg_id=call.from_user.id,
            kind=kind,
            amount_usd=float(amount),
            status="created",
            payment_url=pay_url,
        )
        s.add(inv)
        await s.commit()

    return pay_url, order_id


@router.callback_query(F.data.startswith("buy:plan:"))
async def buy_plan(call: CallbackQuery):
    plan_code = call.data.split(":")[2].strip().upper()
    if plan_code not in PLANS:
        await call.answer("Ката 😅", show_alert=True)
        return

    plan = PLANS[plan_code]
    if plan_code == "FREE":
        await call.answer("FREE сатып алынбайт 😄", show_alert=True)
        return

    pay_url, order_id = await _mk_invoice(call, kind=f"PLAN_{plan_code}", amount=float(plan.price_usd))

    if not pay_url:
        await call.message.answer(
            "⚠️ Cryptomus жооптон төлөм линк чыкпай калды.\n"
            "API key / merchant / sign текшерип көр, досум 😅"
        )
        await call.answer()
        return

    text = (
        f"✅ {plan.title} тандалды 😎\n\n"
        f"💳 Баа: {_money(plan.price_usd)}\n\n"
        "📌 Төлөп бүткөндө автомат актив болуп калат.\n"
        "Эгер төлөдүң, бирок ачылбай жатса — 1 мүнөт күтүп «Төлөмдү текшерүү» бас.\n\n"
        f"🧾 Order: {order_id}"
    )
    await call.message.answer(text, reply_markup=_kb_pay(pay_url, order_id), disable_web_page_preview=True)
    await call.answer()


@router.callback_query(F.data.startswith("buy:vip_video:"))
async def buy_vip_video(call: CallbackQuery):
    n = int(call.data.split(":")[2])
    if n not in VIP_VIDEO_PACKS:
        await call.answer("Ката 😅", show_alert=True)
        return
    amount = float(VIP_VIDEO_PACKS[n])

    pay_url, order_id = await _mk_invoice(call, kind=f"VIP_VIDEO_{n}", amount=amount)
    if not pay_url:
        await call.message.answer("⚠️ Төлөм линк табылган жок. Cryptomus settings текшер 😅")
        await call.answer()
        return

    await call.message.answer("⚠️ Төлөм линк табылган жок. Cryptomus settings текшер 😅")
        await call.answer()
        return

    await call.message.answer(
        f"🎥 VIP VIDEO пакет\n\n"
        f"📦 Кредит: {n} видео\n"
        f"💳 Баа: {_money(amount)}\n\n"
        "Төлөгөндөн кийин кредит автомат кошулат ✅\n"
        f"🧾 Order: {order_id}",
        reply_markup=_kb_pay(pay_url, order_id),
        disable_web_page_preview=True
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy:vip_music:"))
async def buy_vip_music(call: CallbackQuery):
    minutes = int(call.data.split(":")[2])
    if minutes not in VIP_MUSIC_PACKS_MINUTES:
        await call.answer("Ката 😅", show_alert=True)
        return
    amount = float(VIP_MUSIC_PACKS_MINUTES[minutes])

    pay_url, order_id = await _mk_invoice(call, kind=f"VIP_MUSIC_{minutes}", amount=amount)
    if not pay_url:
        await call.message.answer("⚠️ Төлөм линк табылган жок. Cryptomus settings текшер 😅")
        await call.answer()
        return

    await call.message.answer(
        f"🪉 VIP MUSIC пакет\n\n"
        f"⏱ Кредит: {minutes} мин\n"
        f"💳 Баа: {_money(amount)}\n\n"
        "Төлөгөндөн кийин минут автомат кошулат ✅\n"
        f"🧾 Order: {order_id}",
        reply_markup=_kb_pay(pay_url, order_id),
        disable_web_page_preview=True
    )
    await call.answer()


# -----------------------------
# Optional: payment check button
# -----------------------------
@router.callback_query(F.data.startswith("paycheck:"))
async def pay_check(call: CallbackQuery):
    """
    Бул жерде реал текшерүү үчүн Cryptomus "payment info" endpoint керек.
    Азырынча UX үчүн: колдонуучуга “эгер төлөсөң webhook 1-2 мүнөттө ачат” деп айтабыз.
    """
    order_id = call.data.split(":", 1)[1]
    await call.answer()

    await call.message.answer(
        "🔎 Текшерүү…\n\n"
        "Досум, эгер төлөм өтсө — webhook 1–2 мүнөттө өзү актив кылат ✅\n"
        "Эгер 3–5 мүнөт өтүп дагы ачылбаса:\n"
        "1) Төлөм статусун Cryptomus’тан кара\n"
        "2) Support’ка order id жибер\n\n"
        f"🧾 Order: {order_id}",
        disable_web_page_preview=True
    )
