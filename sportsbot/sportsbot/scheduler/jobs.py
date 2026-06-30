"""Scheduled jobs wired into python-telegram-bot's JobQueue.

Jobs:
  * daily sync + analysis of fixtures (today + horizon days)
  * daily broadcast of personalised tips to active subscribers
  * results reconciliation + tip/combo settlement
  * subscription expiry sweep (auto-block expired users)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import Application, ContextTypes

from ..config import get_settings
from ..db import repo, session_scope
from ..db.base import RiskProfile
from ..logging_conf import get_logger
from ..services.sync import sync_fixtures_and_analyse, update_results_and_settle
from ..services.tips import generate_broadcast_tips
from ..bot import texts

logger = get_logger(__name__)


def run_sync() -> dict:
    """Blocking sync used by jobs (via to_thread) and admin commands."""
    fixtures = sync_fixtures_and_analyse()
    results = update_results_and_settle()
    return {"fixtures": fixtures, "results": results}


async def run_daily_push(bot: Bot) -> dict:
    """Generate today's broadcast tips and push them to active subscribers."""
    # Generate tips inside a worker thread (sync DB work).
    summary = await asyncio.to_thread(_generate_and_collect)

    sent, failed, blocked = 0, 0, 0
    subscribers = summary["subscribers"]
    for sub in subscribers:
        profile = sub["risk_profile"]
        opps = summary["by_profile"].get(profile, [])
        if not opps:
            continue
        text = _format_push(opps, profile)
        try:
            await bot.send_message(
                chat_id=sub["telegram_id"], text=text, parse_mode=ParseMode.HTML
            )
            sent += 1
        except Forbidden:
            blocked += 1
        except TelegramError as exc:  # noqa: BLE001
            logger.warning("Push to %s failed: %s", sub["telegram_id"], exc)
            failed += 1
        await asyncio.sleep(0.05)  # gentle rate limiting

    logger.info("Daily push: %s sent, %s failed, %s blocked.", sent, failed, blocked)
    return {"sent": sent, "failed": failed, "blocked": blocked}


def _generate_and_collect() -> dict:
    """Create broadcast tips and snapshot the data needed for sending."""
    with session_scope() as session:
        raw = generate_broadcast_tips(session, limit_per_profile=3)
        by_profile = {}
        for profile, opps in raw.items():
            serialised = []
            for o in opps:
                serialised.append(
                    {
                        "league": o.match.league,
                        "kickoff": o.match.kickoff,
                        "home": o.match.home_name,
                        "away": o.match.away_name,
                        "pick": o.pick,
                        "odds": o.odds,
                        "probability": o.probability,
                        "confidence": o.confidence,
                        "risk_level": o.analysis.risk_level,
                    }
                )
            by_profile[profile] = serialised

        subscribers = [
            {"telegram_id": u.telegram_id, "risk_profile": u.risk_profile}
            for u in repo.active_subscribers(session)
        ]
    return {"by_profile": by_profile, "subscribers": subscribers}


def _format_push(opps: list[dict], profile: str) -> str:
    from ..bot.utils import esc, format_kickoff, pick_label

    head = (
        f"🔥 <b>Pronostics du jour</b> — {datetime.utcnow():%d/%m/%Y}\n"
        f"Profil : {RiskProfile.label(profile)}\n\n"
    )
    risk_labels = texts.RISK_LEVEL_LABELS
    lines = []
    for i, o in enumerate(opps, 1):
        label = pick_label(o["pick"], o["home"], o["away"])
        lines.append(
            f"<b>{i}.</b> 🏆 <i>{esc(o['league'])}</i> — {esc(format_kickoff(o['kickoff']))}\n"
            f"⚽ <b>{esc(o['home'])}</b> 🆚 <b>{esc(o['away'])}</b>\n"
            f"🎯 {esc(label)} @ <b>{o['odds']:.2f}</b> "
            f"({o['probability']*100:.0f}% • conf. {o['confidence']:.0f}% • "
            f"{risk_labels.get(o['risk_level'], '🟡')})\n"
        )
    return head + "\n".join(lines) + "\n\n💡 <i>Ouvre 🤖 Analyse IA pour le détail.</i>"


# --------------------------------------------------------------------------- #
# JobQueue callbacks
# --------------------------------------------------------------------------- #
async def _job_sync(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Running scheduled fixture sync...")
    await asyncio.to_thread(sync_fixtures_and_analyse)


async def _job_results(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Running scheduled results update...")
    await asyncio.to_thread(update_results_and_settle)


async def _job_push(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Running scheduled daily push...")
    await run_daily_push(context.bot)


async def _job_expiry(context: ContextTypes.DEFAULT_TYPE) -> None:
    def _expire():
        with session_scope() as session:
            return repo.expire_due_subscriptions(session)

    count = await asyncio.to_thread(_expire)
    if count:
        logger.info("Expired %s subscriptions.", count)


def register_jobs(application: Application) -> None:
    settings = get_settings()
    jq = application.job_queue
    if jq is None:
        logger.warning("JobQueue unavailable; scheduled jobs disabled.")
        return

    jq.run_daily(_job_sync, time=settings.daily_sync_time, name="daily_sync")
    jq.run_daily(_job_push, time=settings.daily_push_time, name="daily_push")
    jq.run_daily(_job_results, time=settings.results_update_time, name="results_update")
    # Expiry sweep every hour.
    jq.run_repeating(_job_expiry, interval=3600, first=300, name="expiry_sweep")
    # Initial sync shortly after startup so the bot has data immediately.
    jq.run_once(_job_sync, when=5, name="startup_sync")

    logger.info(
        "Scheduled jobs registered (sync %s, push %s, results %s).",
        settings.daily_sync_time,
        settings.daily_push_time,
        settings.results_update_time,
    )
