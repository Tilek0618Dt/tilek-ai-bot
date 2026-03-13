from __future__ import annotations

from typing import Dict, Tuple, List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# =========================================================
# Callback prefixes (бир стандарт)
# =========================================================
CB_MENU = "m"          # m:chat, m:premium ...
CB_BUY = "buy"         # buy:plan:PLUS, buy:vip_video:3 ...
CB_LANG = "lang"       # lang:choose:KG, lang:page:2
CB_ADMIN = "adm"       # adm:panel, adm:users ...


# =========================================================
# Helpers
# =========================================================
def _btn(text: str, cb: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=cb)


def _kb(rows: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================================================
# MAIN MENU (сатуучу UX)
# =========================================================
def kb_main() -> InlineKeyboardMarkup:
    """
    Башкы меню — эң көп колдонулуучу.
    """
    return _kb([
        [_btn("💬 AI Чат", f"{CB_MENU}:chat"), _btn("⚡ Профиль", f"{CB_MENU}:profile")],
        [_btn("🎥 Видео", f"{CB_MENU}:video"), _btn("🪉 Музыка", f"{CB_MENU}:music")],
        [_btn("🖼 Сүрөт", f"{CB_MENU}:image"), _btn("🔊 Үн", f"{CB_MENU}:voice")],
        [_btn("📄 Документ", f"{CB_MENU}:doc"), _btn("📚 Тарых", f"{CB_MENU}:history")],
        [_btn("💎 Премиум", f"{CB_MENU}:premium"), _btn("🎁 Реферал", f"{CB_MENU}:ref")],
        [_btn("🌍 Тил/Өлкө", f"{CB_MENU}:lang"), _btn("🆘 Жардам", f"{CB_MENU}:support")],
    ])


# =========================================================
# BACK/COMMON NAV
# =========================================================
def kb_back(to: str = "home") -> InlineKeyboardMarkup:
    """
    to="home" => m:home
    to="premium" => m:premium
    """
    return _kb([
        [_btn("⬅️ Артка", f"{CB_MENU}:{to}")]
    ])


def kb_home_row() -> InlineKeyboardMarkup:
    return _kb([
        [_btn("🏠 Башкы меню", f"{CB_MENU}:home")]
    ])


# =========================================================
# PREMIUM MENUS
# =========================================================
def kb_premium() -> InlineKeyboardMarkup:
    return _kb([
        [_btn("💎 PLUS — $12/ай", f"{CB_BUY}:plan:PLUS")],
        [_btn("🔴 PRO — $28/ай", f"{CB_BUY}:plan:PRO")],
        [_btn("🎥 VIP VIDEO (пакет)", f"{CB_MENU}:vip_video")],
        [_btn("🪉 VIP MUSIC (пакет)", f"{CB_MENU}:vip_music")],
        [_btn("📦 Баалар/Планды көрүү", f"{CB_MENU}:plans")],
        [_btn("⬅️ Артка", f"{CB_MENU}:home")],
    ])


def kb_vip_video() -> InlineKeyboardMarkup:
    return _kb([
        [_btn("🎥 1 Видео — $14.99", f"{CB_BUY}:vip_video:1")],
        [_btn("🎥 3 Видео — $35.99", f"{CB_BUY}:vip_video:3")],
        [_btn("🎥 5 Видео — $55.99", f"{CB_BUY}:vip_video:5")],
        [_btn("⬅️ Артка", f"{CB_MENU}:premium")],
    ])


def kb_vip_music() -> InlineKeyboardMarkup:
    return _kb([
        [_btn("🪉 1 Мин — $14.99", f"{CB_BUY}:vip_music:1")],
        [_btn("🪉 3 Мин — $29.99", f"{CB_BUY}:vip_music:3")],
        [_btn("🪉 5 Мин — $49.99", f"{CB_BUY}:vip_music:5")],
        [_btn("⬅️ Артка", f"{CB_MENU}:premium")],
    ])


# =========================================================
# PROFILE / STATUS
# =========================================================
def kb_profile() -> InlineKeyboardMarkup:
    return _kb([
        [_btn("📊 Менин лимиттер", f"{CB_MENU}:limits")],
        [_btn("💳 Төлөмдөр тарыхы", f"{CB_MENU}:payments")],
        [_btn("🎁 Реферал баланс", f"{CB_MENU}:ref_balance")],
        [_btn("⬅️ Артка", f"{CB_MENU}:home")],
    ])


def kb_after_answer() -> InlineKeyboardMarkup:
    """
    Жооп бергенден кийин UX: кайра суроо берүү / премиум көрүү.
    """
    return _kb([
        [_btn("💬 Дагы суроо", f"{CB_MENU}:chat"), _btn("💎 Премиум", f"{CB_MENU}:premium")],
        [_btn("🏠 Меню", f"{CB_MENU}:home")]
    ])


def kb_blocked_upsell() -> InlineKeyboardMarkup:
    """
    FREE блок болгондо эң күчтүү сатуу кнопкалары.
    """
    return _kb([
        [_btn("💎 PLUS/PRO ачуу", f"{CB_MENU}:premium")],
        [_btn("🎥 VIP VIDEO", f"{CB_MENU}:vip_video"), _btn("🪉 VIP MUSIC", f"{CB_MENU}:vip_music")],
        [_btn("🏠 Меню", f"{CB_MENU}:home")],
    ])


# =========================================================
# SUPPORT
# =========================================================
def kb_support() -> InlineKeyboardMarkup:
    return _kb([
        [_btn("🧾 Маселени жазам", f"{CB_MENU}:support_ticket")],
        [_btn("⬅️ Артка", f"{CB_MENU}:home")],
    ])


# =========================================================
# LANGUAGE/COUNTRY SELECT (100+ пагинация)
# COUNTRIES форматы: { "KG": {"name":"Kyrgyzstan","flag":"🇰🇬","lang":"ky"}, ... }
# =========================================================
def kb_lang_page(
    countries: Dict[str, Dict[str, str]],
    page: int = 0,
    per_page: int = 12,
) -> InlineKeyboardMarkup:
    """
    2 колонка * 6 катар = 12 кнопка.
    Навигация: ⬅️ ➡️
    """
    items: List[Tuple[str, Dict[str, str]]] = list(countries.items())
    total = len(items)

    if per_page <= 0:
        per_page = 12

    max_page = max(0, (total - 1) // per_page)
    page = max(0, min(page, max_page))

    start = page * per_page
    chunk = items[start : start + per_page]

    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []

    for code, info in chunk:
        flag = info.get("flag", "🌍")
        name = info.get("name", code)
        row.append(_btn(f"{flag} {name}", f"{CB_LANG}:choose:{code}:{page}"))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    nav: List[InlineKeyboardButton] = []
    if page > 0:
        nav.append(_btn("⬅️", f"{CB_LANG}:page:{page - 1}"))
    nav.append(_btn(f"{page + 1}/{max_page + 1}", f"{CB_LANG}:noop:{page}"))
    if page < max_page:
        nav.append(_btn("➡️", f"{CB_LANG}:page:{page + 1}"))

    rows.append(nav)
    rows.append([_btn("🏠 Меню", f"{CB_MENU}:home")])

    return _kb(rows)


# =========================================================
# ADMIN (минимал, бирок UX күчтүү)
# =========================================================
def kb_admin_panel() -> InlineKeyboardMarkup:
    return _kb([
        [_btn("📊 Статистика", f"{CB_ADMIN}:stats"), _btn("👥 Колдонуучулар", f"{CB_ADMIN}:users")],
        [_btn("💳 Төлөмдөр", f"{CB_ADMIN}:payments"), _btn("🚫 Бан/Unban", f"{CB_ADMIN}:ban")],
        [_btn("📣 Broadcast", f"{CB_ADMIN}:broadcast")],
        [_btn("🏠 Меню", f"{CB_MENU}:home")],
    ])
