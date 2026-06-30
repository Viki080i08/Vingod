"""Curated baseline Elo ratings for clubs and national teams.

These give the analysis engine a credible starting point for well-known teams.
For any unknown team the engine starts at the default 1500 and then *learns*
the real strength automatically from incoming results (Elo update), so coverage
improves on its own over time. Names are matched case-insensitively, with a few
aliases to bridge naming differences between data sources.
"""

from __future__ import annotations

import unicodedata

DEFAULT_ELO = 1500.0

CLUB_ELO = {
    # Ligue 1
    "paris sg": 1985, "paris saint-germain": 1985, "marseille": 1760,
    "monaco": 1780, "lille": 1750, "lyon": 1730, "nice": 1740, "lens": 1745,
    "rennes": 1735, "reims": 1660, "strasbourg": 1650, "nantes": 1620,
    "montpellier": 1600,
    # Premier League
    "manchester city": 2050, "arsenal": 1980, "liverpool": 1985,
    "manchester united": 1820, "manchester utd": 1820, "chelsea": 1830,
    "tottenham": 1840, "tottenham hotspur": 1840, "newcastle": 1830,
    "newcastle united": 1830, "aston villa": 1820, "brighton": 1780,
    "west ham": 1740, "west ham united": 1740, "everton": 1680, "wolves": 1690,
    # La Liga
    "real madrid": 2030, "barcelona": 1990, "barcelone": 1990,
    "atletico madrid": 1930, "atletico de madrid": 1930, "real sociedad": 1820,
    "villarreal": 1800, "real betis": 1770, "betis": 1770,
    "athletic bilbao": 1810, "athletic club": 1810, "valencia": 1720,
    "valence": 1720, "sevilla": 1780, "seville": 1780, "getafe": 1690,
    "osasuna": 1700, "celta vigo": 1680,
    # Serie A
    "inter milan": 1985, "inter": 1985, "juventus": 1900, "ac milan": 1900,
    "milan": 1900, "napoli": 1910, "naples": 1910, "roma": 1850, "lazio": 1830,
    "atalanta": 1880, "fiorentina": 1800, "bologna": 1770, "bologne": 1770,
    "torino": 1720,
    # Bundesliga
    "bayern munich": 2010, "bayern munchen": 2010, "borussia dortmund": 1900,
    "dortmund": 1900, "rb leipzig": 1900, "leipzig": 1900,
    "bayer leverkusen": 1950, "leverkusen": 1950, "eintracht frankfurt": 1800,
    "francfort": 1800, "freiburg": 1760, "fribourg": 1760, "wolfsburg": 1720,
    "stuttgart": 1820,
}

# Approximate World Football Elo for major national teams (World Cup, friendlies).
NATIONAL_ELO = {
    "argentina": 2100, "france": 2050, "brazil": 2020, "spain": 2000,
    "england": 1985, "germany": 1935, "portugal": 1960, "netherlands": 1950,
    "belgium": 1905, "italy": 1900, "croatia": 1880, "uruguay": 1875,
    "colombia": 1855, "morocco": 1845, "mexico": 1800, "usa": 1790,
    "united states": 1790, "switzerland": 1820, "denmark": 1820, "japan": 1825,
    "senegal": 1820, "south korea": 1780, "korea republic": 1780,
    "serbia": 1800, "poland": 1790, "ecuador": 1800, "austria": 1810,
    "ukraine": 1800, "sweden": 1770, "wales": 1760, "norway": 1780,
    "scotland": 1760, "turkey": 1790, "nigeria": 1790, "ghana": 1750,
    "ivory coast": 1780, "cameroon": 1760, "egypt": 1790, "algeria": 1800,
    "tunisia": 1740, "australia": 1770, "canada": 1780, "qatar": 1700,
    "saudi arabia": 1710, "iran": 1790, "peru": 1760, "chile": 1770,
    "paraguay": 1740, "venezuela": 1720, "greece": 1760, "czech republic": 1780,
    "czechia": 1780, "hungary": 1770, "romania": 1750, "ireland": 1740,
    "republic of ireland": 1740, "slovakia": 1740, "slovenia": 1740,
}


def _normalize(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return n.strip().lower()


def elo_for(name: str) -> float:
    key = _normalize(name)
    if key in CLUB_ELO:
        return float(CLUB_ELO[key])
    if key in NATIONAL_ELO:
        return float(NATIONAL_ELO[key])
    return DEFAULT_ELO


def is_known(name: str) -> bool:
    key = _normalize(name)
    return key in CLUB_ELO or key in NATIONAL_ELO
