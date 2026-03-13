from dataclasses import dataclass
from typing import Dict


# =========================================================
# Product / Business switches (негизги бизнес эрежелер)
# =========================================================

APP_NAME = "TILEK AI"
APP_BRAND = "Tilek"
CURRENCY = "USD"


# =========================================================
# FREE правила
# =========================================================

FREE_DAILY_QUESTIONS = 10      # FREE: күнүнө 10 суроо
BLOCK_HOURS_FREE = 6           # лимит бүтсө 6 саат блок
FREE_MAX_TEXT_LEN = 3500       # спамдан коргоо (узун текст)
FREE_COOLDOWN_SECONDS = 2      # flood control жеңил (2 сек)


# =========================================================
# Plan models
# =========================================================

@dataclass(frozen=True)
class Plan:
    code: str
    title: str
    price_usd: float

    monthly_chat: int
    monthly_video: int
    monthly_music: int
    monthly_image: int
    monthly_voice: int
    monthly_doc: int

    priority: int  # UX: PRO = 2, PLUS = 1, FREE = 0


# 3 план (сен айткандай — так 3 эле)
PLANS: Dict[str, Plan] = {
    "FREE": Plan(
        code="FREE",
        title="FREE",
        price_usd=0.0,
        monthly_chat=0,
        monthly_video=0,
        monthly_music=0,
        monthly_image=0,
        monthly_voice=0,
        monthly_doc=0,
        priority=0,
    ),
    "PLUS": Plan(
        code="PLUS",
        title="PLUS",
        price_usd=12.0,
        monthly_chat=600,
        monthly_video=3,
        monthly_music=3,
        monthly_image=15,
        monthly_voice=5,
        monthly_doc=5,
        priority=1,
    ),
    "PRO": Plan(
        code="PRO",
        title="PRO",
        price_usd=28.0,
        monthly_chat=1200,
        monthly_video=6,
        monthly_music=3,
        monthly_image=30,
        monthly_voice=15,
        monthly_doc=15,
        priority=2,
    ),
}

PLAN_ORDER = ["FREE", "PLUS", "PRO"]


# =========================================================
# VIP Packs (кредит болуп сакталат, айлык лимитке кирбейт)
# =========================================================

# ВИП ВИДЕО — сан менен кредит
VIP_VIDEO_PACKS_USD = {
    1: 19.99,
    3: 49.99,
    5: 79.99,
}

# ВИП МУЗЫКА — минут менен кредит
VIP_MUSIC_PACKS_MIN_USD = {
    1: 14.99,   # 1 мин
    3: 29.99,   # 3 мин
    5: 49.99,   # 5 мин
}


# =========================================================
# Referral rules (өсүү мотор)
# =========================================================

REF_ENABLED = True
REF_BONUS_USD = 3.0                 # дос PLUS алса → $3 баланс
REF_FREE_PLUS_DAYS = 7              # $5+ төлөсө → 7 күн PLUS
REF_FREE_PLUS_MIN_PAID_USD = 5.0    # threshold
REF_MIN_WITHDRAW_USD = 20.0         # кийин payout кошобуз


# =========================================================
# Payment kinds (Invoice.kind үчүн стандарт)
# =========================================================

KIND_PLAN_PLUS = "PLAN_PLUS"
KIND_PLAN_PRO = "PLAN_PRO"

def kind_vip_video(n: int) -> str:
    return f"VIP_VIDEO_{n}"

def kind_vip_music(minutes: int) -> str:
    return f"VIP_MUSIC_{minutes}"


# =========================================================
# UX / Text templates (сатуучу тексттер)
# =========================================================

def text_free_block() -> str:
    return (
        "🚫 Лимит бүттү, досум 😭\n\n"
        f"FREE: күнүнө {FREE_DAILY_QUESTIONS} суроо гана.\n"
        f"⏳ {BLOCK_HOURS_FREE} сааттан кийин кайра ачылат.\n\n"
        "💎 PLUS – көп чат + 3 видео + 3 музыка\n"
        "🔴 PRO – приоритет + 1200 чат + 6 видео\n"
        "🎥 VIP VIDEO – кино стил (кредит)\n"
        "🪉 VIP MUSIC – проф трек (минут кредит)\n\n"
        "👉 «💎 Премиум» менюдан танда да, күчкө кир 😎"
    )

def text_premium_header() -> str:
    return (
        "💎 Премиум пландар\n\n"
        "Досум, кайсы режим сага туура келет — танда 😎"
    )

def text_vip_video_header() -> str:
    return (
        "🎥 VIP VIDEO\n"
        "Бул айлык лимитке кирбейт. Кредит болуп сакталат.\n"
        "Кино стил, күчтүү монтаж, premium output 😈"
    )

def text_vip_music_header() -> str:
    return (
        "🪉 VIP MUSIC\n"
        "Бул айлык лимитке кирбейт. Минут кредит болуп сакталат.\n"
        "Проф трек, мотив/бизнес/эмоция — сен айткандай 😎"
    )

def text_referral_info(balance_usd: float, ref_link: str) -> str:
    return (
        "🎁 Реферал\n\n"
        f"Сенин ссылкаң:\n{ref_link}\n\n"
        f"💰 Баланс: ${balance_usd:.2f}\n\n"
        "Эреже:\n"
        f"✅ Досуң PLUS алса → +${REF_BONUS_USD}\n"
        f"✅ Досуң ${REF_FREE_PLUS_MIN_PAID_USD}+ төлөсө → {REF_FREE_PLUS_DAYS} күн PLUS\n"
        "❌ PRO бекер берилбейт (банкрот болбойлу 😅)\n"
        f"💸 Withdraw min: ${REF_MIN_WITHDRAW_USD}\n"
    )
    
