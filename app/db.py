from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from app.config import DATABASE_URL


# =========================================================
# Helpers
# =========================================================

def to_async_db_url(url: str) -> str:
    """
    Render көбүнчө DATABASE_URL'ди мындай берет:
      postgres://user:pass@host:5432/dbname
    SQLAlchemy async үчүн керек:
      postgresql+asyncpg://user:pass@host:5432/dbname
    """
    url = (url or "").strip()

    if not url:
        return url

    if url.startswith("postgresql+asyncpg://"):
        return url

    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]

    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]

    # башка формат болсо — ошол бойдон калтырабыз
    return url


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "on")


# =========================================================
# Engine config (production safe defaults)
# =========================================================

ASYNC_DATABASE_URL = to_async_db_url(DATABASE_URL)

# Render'де connection pool туура иштесин:
DB_ECHO = _env_bool("DB_ECHO", False)  # True кылсаң SQL лог чыгат
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # seconds
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # seconds (30 мин)
STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))  # 30 сек


# create_async_engine: asyncpg колдонобуз
ENGINE = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=DB_ECHO,
    pool_pre_ping=True,      # өлгөн connection'ду кармайт
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    # connect_args asyncpg үчүн:
    connect_args={
        # postgres деңгээлде query timeout (миллисек)
        "server_settings": {
            "statement_timeout": str(STATEMENT_TIMEOUT_MS)
        }
    },
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# =========================================================
# Context manager: "async with db_session() as s:"
# =========================================================

@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    """
    Колдонуу:
      async with db_session() as s:
          ...
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =========================================================
# FastAPI dependency style: get_db()
# =========================================================

async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency катары колдонсо болот:
      async def route(db: AsyncSession = Depends(get_db)):
          ...
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =========================================================
# Health checks / init helpers
# =========================================================

async def db_ping() -> bool:
    """
    DB тирүүбү текшерет (Render logs'ко жакшы).
    """
    try:
        async with ENGINE.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def dispose_engine() -> None:
    """
    App shutdown болгондо connection pool жабуу үчүн.
    """
    await ENGINE.dispose()
