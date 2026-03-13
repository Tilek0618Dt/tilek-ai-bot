# app/handlers/menu_router.py
from __future__ import annotations

from aiogram import Router

from app.handlers import (
    start,
    menu,
    history,
    support,
    referral,
    premium,
    vip,
    chat,
    admin,
)

def get_router() -> Router:
    """
    Central router registry for Tilek AI.

    Order matters:
    - start/menu callbacks first (UX navigation)
    - feature routers next (premium/vip/referral)
    - chat last (catch-all text handler)
    - admin near the end (commands)
    """
    r = Router(name="tilek_root_router")

    # 1) Entry /start + language selection
    r.include_router(start.router)

    # 2) Menu navigation (callbacks)
    r.include_router(menu.router)

    # 3) Info pages
    r.include_router(history.router)
    r.include_router(support.router)

    # 4) Growth / monetization
    r.include_router(referral.router)
    r.include_router(premium.router)
    r.include_router(vip.router)

    # 5) Chat must be after menu callbacks (text catch-all)
    r.include_router(chat.router)

    # 6) Admin commands (/stats etc.)
    r.include_router(admin.router)

    return r
