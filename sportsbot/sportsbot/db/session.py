"""Engine and session factory shared across the application."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from ..logging_conf import get_logger
from .base import Base

logger = get_logger(__name__)

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _build_engine() -> Engine:
    settings = get_settings()
    url = make_url(settings.database_url)

    connect_args = {}
    engine_kwargs = {"pool_pre_ping": True, "future": True}

    if url.get_backend_name().startswith("sqlite"):
        # Needed so the SQLite connection can be shared across threads
        # (the bot's job queue and the admin web run in separate threads).
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs.update(pool_size=10, max_overflow=20)

    return create_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionFactory


def get_session() -> Session:
    return get_session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables if they do not yet exist."""
    # Import models so they are registered on the metadata before create_all.
    from . import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database initialised (%s)", engine.url.render_as_string(hide_password=True))
