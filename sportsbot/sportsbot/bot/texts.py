"""Message templates and formatting helpers (HTML parse mode)."""

from __future__ import annotations

from datetime import datetime
from typing import List

from ..db.base import RiskProfile
from .utils import esc, format_kickoff, md_to_html, pick_label

RISK_LEVEL_LABELS = {
    "low": "🟢 Faible",
    "medium": "🟡 Modéré",
    "high": "🔴 Élevé",
}

BTN_PRONOS = "📊 Pronostics du jour"
BTN_PROFILE = "🎯 Mon profil risque"
BTN_COMBO = "🎟️ Créer un combiné"
BTN_AI = "🤖 Analyse IA"
BTN_STATS = "📈 Statistiques"
BTN_SUB = "💳 Abonnement"
BTN_SETTINGS = "⚙️ Paramètres"


def welcome_message(first_name: str | None) -> str:
    name = esc(first_name or "champion")
    return (
        f"👋 <b>Bienvenue {name} sur PronoIA !</b>\n\n"
        "Je suis ton assistant de <b>pronostics sportifs premium</b> propulsé par "
        "une <b>IA d'analyse automatique</b> ⚽🤖\n\n"
        "Chaque jour, j'analyse tous les matchs disponibles (aujourd'hui et "
        "jusqu'à 5 jours) selon :\n"
        "• la forme récente des équipes\n"
        "• les statistiques offensives/défensives\n"
        "• l'historique des confrontations\n"
        "• le facteur domicile/extérieur\n"
        "• les absences importantes et les tendances\n\n"
        "Pour chaque rencontre je te donne une <b>probabilité</b>, un "
        "<b>niveau de confiance</b>, un <b>niveau de risque</b> et une "
        "<b>explication claire</b>.\n\n"
        "Commençons par définir ton <b>profil de risque</b> 👇"
    )


def profile_question() -> str:
    return (
        "🎯 <b>Quel profil souhaitez-vous ?</b>\n\n"
        "🟢 <b>Sécurisé</b> — on privilégie les choix avec la plus forte probabilité.\n"
        "🟡 <b>Équilibré</b> — un compromis entre sécurité et rendement.\n"
        "🔴 <b>Risqué</b> — on accepte plus de variance pour de meilleures cotes.\n\n"
        "Tu pourras le changer à tout moment dans « 🎯 Mon profil risque »."
    )


def menu_message(snapshot: dict) -> str:
    profile = RiskProfile.label(snapshot.get("risk_profile", RiskProfile.BALANCED))
    if snapshot.get("has_active_subscription"):
        expiry = snapshot.get("subscription_expiry")
        sub = f"✅ Premium actif (jusqu'au {expiry:%d/%m/%Y})" if expiry else "✅ Premium actif"
    else:
        sub = "🔒 Aucun abonnement actif"
    return (
        "🏠 <b>Menu principal</b>\n\n"
        f"Profil : {esc(profile)}\n"
        f"Abonnement : {sub}\n\n"
        "Choisis une option dans le menu ci-dessous 👇"
    )


def help_message() -> str:
    return (
        "ℹ️ <b>Aide — PronoIA</b>\n\n"
        "<b>Commandes disponibles :</b>\n"
        "/start — démarrer / message de bienvenue\n"
        "/menu — afficher le menu principal\n"
        "/pronos — pronostics du jour\n"
        "/profil — choisir mon profil de risque\n"
        "/combine — créer un combiné\n"
        "/ia — analyse IA des matchs\n"
        "/stats — statistiques de performance\n"
        "/abonnement — gérer mon abonnement\n"
        "/parametres — réglages\n"
        "/whoami — afficher mon identifiant Telegram\n"
        "/aide — afficher cette aide\n"
    )


def subscription_required() -> str:
    return (
        "🔒 <b>Fonctionnalité premium</b>\n\n"
        "Cette section est réservée aux membres abonnés. "
        "Active ton abonnement pour recevoir tous les pronostics, "
        "les analyses IA détaillées et les combinés optimisés.\n\n"
        "👉 Ouvre « 💳 Abonnement » pour t'abonner."
    )


def format_opportunity(opp, index: int | None = None) -> str:
    match = opp.match
    label = pick_label(opp.pick, match.home_name, match.away_name)
    prefix = f"<b>{index}.</b> " if index else ""
    risk = RISK_LEVEL_LABELS.get(opp.analysis.risk_level, "🟡 Modéré")
    return (
        f"{prefix}🏆 <i>{esc(match.league)}</i> — {esc(format_kickoff(match.kickoff))}\n"
        f"⚽ <b>{esc(match.home_name)}</b> 🆚 <b>{esc(match.away_name)}</b>\n"
        f"🎯 Pari conseillé : <b>{esc(label)}</b> @ <b>{opp.odds:.2f}</b>\n"
        f"📊 Probabilité : {opp.probability*100:.0f}% • "
        f"Confiance : {opp.confidence:.0f}% • Risque : {risk}\n"
    )


def format_day_predictions(opps: List, day: datetime, profile: str) -> str:
    head = (
        f"📊 <b>Pronostics du {day:%d/%m/%Y}</b>\n"
        f"Profil : {esc(RiskProfile.label(profile))}\n\n"
    )
    if not opps:
        return head + (
            "Aucune opportunité ne correspond à ton profil pour cette date. "
            "Essaie un autre jour ou ajuste ton profil de risque."
        )
    body = "\n".join(format_opportunity(o, i + 1) for i, o in enumerate(opps))
    return head + body


def format_match_analysis(match, analysis) -> str:
    risk = RISK_LEVEL_LABELS.get(analysis.risk_level, "🟡 Modéré")
    factors = analysis.key_factors or {}
    factor_lines = "\n".join(
        f"• <b>{esc(k)}</b> : {esc(v)}" for k, v in factors.items()
    )
    return (
        f"🤖 <b>Analyse IA</b>\n"
        f"🏆 <i>{esc(match.league)}</i> — {esc(format_kickoff(match.kickoff))}\n"
        f"⚽ <b>{esc(match.home_name)}</b> 🆚 <b>{esc(match.away_name)}</b>\n\n"
        f"📈 <b>Probabilités</b>\n"
        f"  {esc(match.home_name)} : {analysis.prob_home*100:.0f}% (cote {analysis.odds_home:.2f})\n"
        f"  Nul : {analysis.prob_draw*100:.0f}% (cote {analysis.odds_draw:.2f})\n"
        f"  {esc(match.away_name)} : {analysis.prob_away*100:.0f}% (cote {analysis.odds_away:.2f})\n\n"
        f"🎯 Recommandation : <b>{esc(pick_label(analysis.recommended_pick, match.home_name, match.away_name))}</b> "
        f"@ <b>{analysis.recommended_odds:.2f}</b>\n"
        f"🔎 Confiance : <b>{analysis.confidence:.0f}%</b> • Risque : {risk}\n"
        f"💎 Valeur estimée : <b>{analysis.value_score:+.2f}</b>\n\n"
        f"📝 <b>Détails de l'analyse :</b>\n{md_to_html(analysis.explanation)}\n\n"
        + (f"🔬 <b>Facteurs clés :</b>\n{factor_lines}" if factor_lines else "")
    )


def format_combo(combo, matches_by_id: dict, title: str = "🎟️ Combiné") -> str:
    lines = [f"{title}\n"]
    for i, sel in enumerate(combo.selections, 1):
        match = matches_by_id.get(sel.match_id)
        if not match:
            continue
        label = pick_label(sel.pick, match.home_name, match.away_name)
        lines.append(
            f"<b>{i}.</b> {esc(match.home_name)} 🆚 {esc(match.away_name)}\n"
            f"   ➜ {esc(label)} @ <b>{sel.odds:.2f}</b>"
        )
    lines.append(
        f"\n💰 <b>Cote totale : {combo.total_odds:.2f}</b>\n"
        f"📊 Probabilité combinée : {combo.combined_probability*100:.1f}%"
    )
    return "\n".join(lines)


def format_stats(global_stats: dict, per_profile: dict) -> str:
    def block(name, s):
        return (
            f"<b>{name}</b>\n"
            f"  Pronostics : {s['total']} (réglés : {s['settled']})\n"
            f"  ✅ Gagnés : {s['won']} • ❌ Perdus : {s['lost']}\n"
            f"  🎯 Taux de réussite : <b>{s['win_rate']}%</b> • ROI : {s['roi']}%\n"
        )

    text = "📈 <b>Statistiques de performance</b>\n\n"
    text += block("🌍 Global", global_stats) + "\n"
    text += block("🟢 Sécurisé", per_profile[RiskProfile.SECURE]) + "\n"
    text += block("🟡 Équilibré", per_profile[RiskProfile.BALANCED]) + "\n"
    text += block("🔴 Risqué", per_profile[RiskProfile.RISKY])
    text += (
        "\n<i>Les résultats passés alimentent le moteur d'analyse pour affiner "
        "les futures recommandations.</i>"
    )
    return text


def subscription_info(snapshot: dict, price: float, currency: str, days: int, payments_enabled: bool) -> str:
    if snapshot.get("has_active_subscription"):
        expiry = snapshot.get("subscription_expiry")
        status = f"✅ <b>Abonnement actif</b> jusqu'au <b>{expiry:%d/%m/%Y}</b>"
    elif snapshot.get("subscription_status") == "expired":
        status = "⚠️ <b>Abonnement expiré</b> — renouvelle pour réactiver l'accès."
    else:
        status = "🔒 <b>Aucun abonnement actif.</b>"
    mode = "" if payments_enabled else "\n<i>(Mode démo : paiement simulé pour les tests.)</i>"
    return (
        f"💳 <b>Abonnement Premium</b>\n\n"
        f"{status}\n\n"
        f"Tarif : <b>{price:.2f} {currency}</b> / {days} jours\n\n"
        "Avantages :\n"
        "• Tous les pronostics du jour et des 5 prochains jours\n"
        "• Analyses IA détaillées de chaque match\n"
        "• Combinés optimisés selon ton profil\n"
        "• Réception automatique des meilleurs paris\n"
        f"{mode}"
    )


def settings_message(snapshot: dict) -> str:
    notif = "🔔 Activées" if snapshot.get("notifications_enabled") else "🔕 Désactivées"
    profile = RiskProfile.label(snapshot.get("risk_profile", RiskProfile.BALANCED))
    return (
        "⚙️ <b>Paramètres</b>\n\n"
        f"Profil de risque : {esc(profile)}\n"
        f"Notifications automatiques : {notif}\n\n"
        "Utilise les boutons ci-dessous pour modifier tes réglages."
    )
