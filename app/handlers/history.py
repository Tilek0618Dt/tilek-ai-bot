# app/handlers/history.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.keyboards import kb_main

router = Router()


def _safe_username(u: User) -> str:
    uname = (u.username or "").strip()
    return f"@{uname}" if uname else "Tilek_Ald_Builder"


def _legend_story(u: User) -> str:
    builder = _safe_username(u)
    # “Tilek A.L.D” легенда-бренд блок
    return (
        "👑 ЛЕГЕНДА STORY (TILEK A.L.D)\n"
        f"Бул ботту жасап жаткан — {builder}.\n\n"
        "🧨 Ким бул бала?\n"
        "• Тилек A.L.D — “уйку эмес, прогресс” режимдеги Builder 😈⚡\n"
        "• Түнү-күнү уктабай: код → тест → оңдоо → кайра код 🔁\n"
        "• “Бир бот эмес — бир платформа” деген идеяны көтөргөн биринчи бала 💎\n\n"
        "🛠 Кылган иштериң (кыскача, бирок күчтүү):\n"
        "• Render + PostgreSQL + ENV менен продакшн ойной баштадың\n"
        "• Aiogram 3 + FastAPI webhook — система кылып куруп жатасың\n"
        "• Пландар: FREE → PLUS → PRO + VIP Video/Music кредит логика\n"
        "• Төлөм: Cryptomus webhook менен автомат актив кылуу\n"
        "• Реферал: өсүү моторун кошуп жатасың\n\n"
        "🔥 Мүнөзүң:\n"
        "• Баштадыңбы — токтобойсуң.\n"
        "• Кыйын болсо — “оңдойм” дейсиң.\n"
        "• Максат — стартапты масштабга чыгарып, элге пайдалуу кылуу 🤲🏻\n"
    )


def _tilek_identity(u: User) -> str:
    vibe = u.style_counter % 3
    if vibe == 0:
        return (
            "😎 Tilek ким?\n"
            "Мен сенин Telegram’деги AI досуң: күлкү + акыл + план 💎\n"
        )
    if vibe == 1:
        return (
            "😈 Tilek ким?\n"
            "Мен сени ойготом: “шылтоо жок — аракет бар” ⚡\n"
        )
    return (
        "🧠 Tilek ким?\n"
        "Мен структура берем: факт → түшүндүрмө → кийинки кадам 🧩\n"
    )


def _features_block() -> str:
    return (
        "✅ TILEK AI эмне кыла алат (UX):\n"
        "• 💬 Чат — түшүнүктүү жооп (📌 жооп / 📊 түшүндүрмө / 💡 кеңеш)\n"
        "• 🎥 Видео — VIP кредит менен (Runway/Kling интеграция)\n"
        "• 🪉 Музыка — VIP минут менен (Suno интеграция)\n"
        "• 🖼 Сүрөт / 🔊 Үн / 📄 Документ — модул болуп кеңейет\n"
        "• 💳 Төлөм — Cryptomus → автомат актив\n"
        "• 🎁 Реферал — өсүү мотору\n"
    )


def _how_it_works_block() -> str:
    return (
        "🧠 Система кандай иштейт:\n"
        "• FREE: күнүнө лимит → лимит бүтсө блок + сатуу сунуш\n"
        "• PLUS/PRO: айлык лимит → 30 күндө refill\n"
        "• VIP: айлык лимитке кирбейт → кредит/мүнөт болуп сакталат\n"
        "• Tilek Style: 😎 → 😈 → 🧠 болуп айланып турат\n"
    )


def _status_block(u: User) -> str:
    plan = (u.plan or "FREE").upper()
    lang = (u.language or "ky")
    return (
        "📌 Сенин статусуң:\n"
        f"• План: {plan}\n"
        f"• Тил: {lang}\n"
        f"• Style-цикл: {u.style_counter}\n"
        f"• VIP 🎥: {u.vip_video_credits} кредит\n"
        f"• VIP 🪉: {u.vip_music_minutes} мин\n"
        f"• Реф баланс: ${float(u.ref_balance_usd or 0):.2f}\n"
    )


def _cta_block() -> str:
    return (
        "🚀 Досум, кыскасы:\n"
        "Сен суроо бересиң — Tilek аны *пландыгыдай* кылып чыгарат.\n\n"
        "👉 Азыр менюдан танда: Чат / Видео / Музыка / Премиум 😎"
    )


def _full_text(u: User) -> str:
    return (
        f"{_tilek_identity(u)}\n"
        f"{_legend_story(u)}\n"
        f"{_features_block()}\n"
        f"{_how_it_works_block()}\n"
        f"{_status_block(u)}\n"
        f"{_cta_block()}"
    )


@router.callback_query(F.data == "m:history")
async def history(call: CallbackQuery):
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == call.from_user.id))
        u = res.scalar_one_or_none()

        # /start баспай кирсе да иштесин
        if not u:
            u = User(
                tg_id=call.from_user.id,
                username=getattr(call.from_user, "username", None),
            )
            s.add(u)
            await s.commit()
            await s.refresh(u)

        text = _full_text(u)

    await call.message.answer(text, reply_markup=kb_main())
    await call.answer()
