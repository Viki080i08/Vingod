"""Human-friendly (French) formatting of analyses, signals and reports.

Messages are formatted with Telegram HTML parse mode.
"""
from __future__ import annotations

import html
from typing import Dict, List

from ..ai.engine import Analysis
from ..models import (
    EconomicEvent,
    NewsItem,
    ScoreBreakdown,
    SignalDirection,
    TradingSignal,
)
from ..risk import RiskResult

DISCLAIMER = (
    "\n\n<i>⚠️ Ceci n'est pas un conseil en investissement. Le trading comporte des "
    "risques de perte. Aucun gain n'est garanti. Faites vos propres recherches.</i>"
)


def _esc(text: str) -> str:
    return html.escape(str(text))


def fmt_price(value: float) -> str:
    if value == 0:
        return "0"
    abs_v = abs(value)
    if abs_v >= 1000:
        return f"{value:,.2f}"
    if abs_v >= 1:
        return f"{value:,.4f}"
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _direction_emoji(direction: SignalDirection) -> str:
    return {
        SignalDirection.LONG: "🟢 LONG (achat)",
        SignalDirection.SHORT: "🔴 SHORT (vente)",
        SignalDirection.NEUTRAL: "⚪ NEUTRE",
    }[direction]


def _score_bar(score: float) -> str:
    filled = int(round(score / 10.0))
    filled = max(0, min(10, filled))
    return "█" * filled + "░" * (10 - filled)


def format_signal(signal: TradingSignal, include_disclaimer: bool = True) -> str:
    lines = [
        "📊 <b>SIGNAL IA</b>",
        "",
        f"<b>Actif :</b> {_esc(signal.symbol)} ({signal.asset_class.value})",
        f"<b>Type :</b> {_direction_emoji(signal.direction)}",
        f"<b>Entrée :</b> {fmt_price(signal.entry)}",
        f"<b>Objectif :</b> {fmt_price(signal.target)}",
        f"<b>Stop Loss :</b> {fmt_price(signal.stop_loss)}",
        f"<b>Risque/Rendement :</b> 1:{signal.risk_reward}",
        f"<b>Durée estimée :</b> {_esc(signal.estimated_duration)} (TF {signal.timeframe})",
        "",
        f"<b>Score IA :</b> {signal.score:.0f}/100  {_score_bar(signal.score)}",
        f"<b>Probabilité estimée :</b> {signal.probability:.0f}%",
        "",
        "<b>Analyse :</b>",
        f"• <b>Technique :</b> {_esc(signal.technical_summary)}",
        f"• <b>Fondamentale :</b> {_esc(signal.fundamental_summary)}",
        f"• <b>Sentiment :</b> {_esc(signal.sentiment_summary)}",
    ]
    if signal.reasons:
        lines.append("• <b>Raisons du signal :</b>")
        for reason in signal.reasons:
            lines.append(f"   – {_esc(reason)}")

    text = "\n".join(lines)
    if include_disclaimer:
        text += DISCLAIMER
    return text


def format_score_breakdown(breakdown: ScoreBreakdown) -> str:
    b = breakdown.as_dict()
    labels = {
        "trend_quality": "Qualité de tendance",
        "indicator_confirmation": "Confirmation indicateurs",
        "volatility": "Volatilité",
        "volume": "Volume",
        "historical_analog": "Historique similaire",
        "market_context": "Contexte de marché",
    }
    lines = ["<b>Détail du score IA :</b>"]
    for key, label in labels.items():
        lines.append(f"• {label} : {b[key]:.1f}")
    return "\n".join(lines)


def format_analysis(analysis: Analysis) -> str:
    signal = analysis.signal
    quote = analysis.market_data.quote
    header = [
        f"🔎 <b>Analyse complète — {_esc(signal.symbol)}</b>",
        f"<b>Prix actuel :</b> {fmt_price(quote.price)}",
    ]
    if quote.change_pct_24h is not None:
        header.append(f"<b>Variation 24h :</b> {quote.change_pct_24h:+.2f}%")
    if quote.volume_24h:
        header.append(f"<b>Volume 24h :</b> {quote.volume_24h:,.0f}")
    header.append("")

    body = format_signal(signal, include_disclaimer=False)
    breakdown = format_score_breakdown(signal.score_breakdown)

    ml_line = ""
    if analysis.ml_trained:
        ml_line = (
            f"\n\n🤖 <b>Modèle ML :</b> probabilité de hausse {analysis.ml_proba_up*100:.0f}% "
            f"(précision backtest {analysis.ml_accuracy*100:.0f}%)"
        )

    return "\n".join(header) + "\n" + body + "\n\n" + breakdown + ml_line + DISCLAIMER


def format_signal_list(signals: List[TradingSignal], title: str) -> str:
    if not signals:
        return f"<b>{_esc(title)}</b>\n\nAucune opportunité détectée pour le moment."
    lines = [f"<b>{_esc(title)}</b>", ""]
    for i, s in enumerate(signals, start=1):
        emoji = "🟢" if s.direction == SignalDirection.LONG else "🔴"
        lines.append(
            f"{i}. {emoji} <b>{_esc(s.symbol)}</b> — {s.direction.value} | "
            f"Score {s.score:.0f} | Prob {s.probability:.0f}% | R:R 1:{s.risk_reward}"
        )
        lines.append(f"    Entrée {fmt_price(s.entry)} · TP {fmt_price(s.target)} · SL {fmt_price(s.stop_loss)}")
    lines.append("\nUtilisez /analyse SYMBOLE pour le détail complet.")
    return "\n".join(lines) + DISCLAIMER


def format_news(items: List[NewsItem], title: str = "📰 Actualités importantes") -> str:
    if not items:
        return f"<b>{_esc(title)}</b>\n\nAucune actualité disponible pour le moment."
    lines = [f"<b>{_esc(title)}</b>", ""]
    for item in items:
        emoji = "🟢" if item.sentiment >= 0.1 else ("🔴" if item.sentiment <= -0.1 else "⚪")
        title_txt = _esc(item.title[:160])
        if item.url:
            lines.append(f'{emoji} <a href="{_esc(item.url)}">{title_txt}</a>')
        else:
            lines.append(f"{emoji} {title_txt}")
        lines.append(f"    <i>{_esc(item.source)} · sentiment {item.sentiment:+.2f}</i>")
    avg = sum(i.sentiment for i in items) / len(items)
    lines.append(f"\n<b>Sentiment global :</b> {avg:+.2f}")
    return "\n".join(lines)


def format_economic_events(events: List[EconomicEvent]) -> str:
    if not events:
        return "<b>📅 Événements économiques</b>\n\nAucun événement majeur à venir."
    lines = ["<b>📅 Événements économiques à venir</b>", ""]
    impact_emoji = {"high": "🔴", "medium": "🟠", "low": "🟡"}
    for e in events:
        when = e.when.strftime("%d/%m %H:%M UTC") if e.when else "—"
        emoji = impact_emoji.get(e.importance.lower(), "⚪")
        lines.append(f"{emoji} <b>{_esc(e.title)}</b> ({_esc(e.country)})")
        detail = f"    {when}"
        if e.forecast:
            detail += f" · prév. {_esc(e.forecast)}"
        if e.previous:
            detail += f" · préc. {_esc(e.previous)}"
        lines.append(detail)
    return "\n".join(lines)


def format_risk(result: RiskResult, symbol: str) -> str:
    return "\n".join(
        [
            f"🧮 <b>Calcul du risque — {_esc(symbol)}</b>",
            "",
            f"<b>Capital :</b> {result.account_balance:,.2f}",
            f"<b>Risque :</b> {result.risk_pct:.2f}% = {result.risk_amount:,.2f}",
            f"<b>Entrée :</b> {fmt_price(result.entry)}",
            f"<b>Stop Loss :</b> {fmt_price(result.stop_loss)} "
            f"(distance {result.stop_distance_pct:.2f}%)",
            "",
            f"<b>Taille de position :</b> {result.position_size} unités",
            f"<b>Valeur de position :</b> {result.position_value:,.2f}",
            f"<b>Risque/Rendement :</b> 1:{result.risk_reward}" if result.risk_reward else "",
        ]
    ).strip() + DISCLAIMER


def format_portfolio(positions: List[Dict], valuations: List[Dict]) -> str:
    if not positions:
        return (
            "💼 <b>Votre portefeuille est vide.</b>\n\n"
            "Ajoutez une position : <code>/portfolio add BTCUSDT 0.5 30000</code>\n"
            "Videz-le : <code>/portfolio clear</code>"
        )
    lines = ["💼 <b>Votre portefeuille</b>", ""]
    total_cost = 0.0
    total_value = 0.0
    for v in valuations:
        total_cost += v["cost"]
        total_value += v["value"]
        pnl = v["value"] - v["cost"]
        pnl_pct = (pnl / v["cost"] * 100) if v["cost"] else 0.0
        emoji = "🟢" if pnl >= 0 else "🔴"
        price_txt = fmt_price(v["price"]) if v["price"] is not None else "n/a"
        lines.append(
            f"{emoji} <b>{_esc(v['symbol'])}</b> — {v['quantity']} @ {fmt_price(v['entry_price'])}"
        )
        lines.append(
            f"    Prix {price_txt} · Valeur {v['value']:,.2f} · P&L {pnl:+,.2f} ({pnl_pct:+.2f}%)"
        )
    total_pnl = total_value - total_cost
    total_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
    lines.append("")
    lines.append(
        f"<b>Total :</b> valeur {total_value:,.2f} · investi {total_cost:,.2f} · "
        f"P&L {total_pnl:+,.2f} ({total_pct:+.2f}%)"
    )
    return "\n".join(lines) + DISCLAIMER
