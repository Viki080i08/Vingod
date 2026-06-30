"""FastAPI-powered administrator dashboard.

Provides a protected web UI to inspect users, subscriptions, AI analyses,
payments and aggregate statistics. Authentication uses HTTP Basic with the
credentials defined in the environment.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from ..config import get_settings
from ..db import init_db, session_scope
from ..db import repo
from ..db.base import RiskProfile
from ..db.models import Analysis, Match
from ..logging_conf import get_logger
from sqlalchemy import select

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
security = HTTPBasic()


def _auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    settings = get_settings()
    user_ok = secrets.compare_digest(credentials.username, settings.admin_web_username)
    pass_ok = secrets.compare_digest(credentials.password, settings.admin_web_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def create_admin_app() -> FastAPI:
    init_db()
    app = FastAPI(title="PronoIA — Administration", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, _: str = Depends(_auth)):
        with session_scope() as session:
            total_users = repo.count_users(session)
            active_subs = repo.count_active_subscribers(session)
            global_stats = repo.tip_stats(session)
            per_profile = {
                p: repo.tip_stats(session, p) for p in RiskProfile.ALL
            }
            now = datetime.utcnow()
            upcoming = len(repo.matches_between(session, now, now + timedelta(days=5)))
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "active": "dashboard",
                "total_users": total_users,
                "active_subs": active_subs,
                "global_stats": global_stats,
                "per_profile": per_profile,
                "upcoming": upcoming,
                "profile_labels": RiskProfile.LABELS,
            },
        )

    @app.get("/users", response_class=HTMLResponse)
    def users(request: Request, _: str = Depends(_auth)):
        with session_scope() as session:
            rows = [
                {
                    "telegram_id": u.telegram_id,
                    "username": u.username,
                    "first_name": u.first_name,
                    "profile": RiskProfile.label(u.risk_profile),
                    "status": u.subscription_status,
                    "expiry": u.subscription_expiry,
                    "active": u.has_active_subscription,
                    "blocked": u.is_blocked,
                    "created": u.created_at,
                }
                for u in repo.all_users(session)
            ]
        return templates.TemplateResponse(
            "users.html", {"request": request, "active": "users", "rows": rows}
        )

    @app.get("/matches", response_class=HTMLResponse)
    def matches(request: Request, _: str = Depends(_auth)):
        now = datetime.utcnow()
        with session_scope() as session:
            ms = repo.matches_between(session, now - timedelta(days=2), now + timedelta(days=5), only_scheduled=False)
            rows = []
            for m in ms:
                a = m.analysis
                rows.append(
                    {
                        "league": m.league,
                        "kickoff": m.kickoff,
                        "home": m.home_name,
                        "away": m.away_name,
                        "status": m.status,
                        "score": (
                            f"{m.home_score}-{m.away_score}"
                            if m.home_score is not None
                            else "—"
                        ),
                        "pick": a.recommended_pick if a else "—",
                        "confidence": a.confidence if a else 0,
                        "risk": a.risk_level if a else "—",
                        "prob": (
                            f"{a.prob_home*100:.0f}/{a.prob_draw*100:.0f}/{a.prob_away*100:.0f}"
                            if a else "—"
                        ),
                    }
                )
        return templates.TemplateResponse(
            "matches.html", {"request": request, "active": "matches", "rows": rows}
        )

    @app.get("/payments", response_class=HTMLResponse)
    def payments(request: Request, _: str = Depends(_auth)):
        from ..db.models import Payment, User

        with session_scope() as session:
            stmt = select(Payment, User).join(User, Payment.user_id == User.id).order_by(
                Payment.created_at.desc()
            )
            rows = [
                {
                    "telegram_id": user.telegram_id,
                    "amount": p.amount,
                    "currency": p.currency,
                    "provider": p.provider,
                    "days": p.period_days,
                    "created": p.created_at,
                }
                for p, user in session.execute(stmt).all()
            ]
        return templates.TemplateResponse(
            "payments.html", {"request": request, "active": "payments", "rows": rows}
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def run_admin() -> None:
    import uvicorn

    settings = get_settings()
    logger.info(
        "Starting admin dashboard on http://%s:%s",
        settings.admin_web_host,
        settings.admin_web_port,
    )
    uvicorn.run(
        create_admin_app(),
        host=settings.admin_web_host,
        port=settings.admin_web_port,
        log_level=settings.log_level.lower(),
        # Force the standard asyncio loop. Otherwise uvicorn installs the
        # uvloop event-loop policy process-wide, which breaks the Telegram
        # bot's long polling running in the main thread.
        loop="asyncio",
    )
