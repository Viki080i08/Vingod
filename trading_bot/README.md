# 🤖 Assistant IA de Trading — Bot Telegram

Bot Telegram intelligent d'analyse de marché et d'aide au trading. Il combine
**analyse technique, fondamentale, quantitative et machine learning** pour
identifier des configurations de marché intéressantes en temps réel sur les
**cryptos, le forex, les actions et les indices**, directement dans Telegram.

> ⚠️ **Avertissement.** Cet outil est une aide à la décision à but éducatif. Ce
> n'est **pas** un conseil en investissement. Le trading comporte un risque de
> perte en capital et **aucun gain n'est garanti**.

---

## ✨ Fonctionnalités

- **Données temps réel** sans clé API :
  - **Crypto** (1000+ paires Binance + 10 000+ via CoinGecko) — tapez `BTC`, `ETH`, `PEPE` ou `BTCUSDT`
  - **Actions** (AAPL, TSLA, NVDA…) via Yahoo Finance
  - **Forex** (EURUSD, GBPUSD, XAUUSD…) via Yahoo Finance
  - **Indices** (SPX, NAS100, DAX…) via Yahoo Finance
  - Optionnel : Twelve Data si `TWELVE_DATA_API_KEY` est configurée
- **Actualités & sentiment** : agrégation de news (NewsAPI ou flux RSS publics) avec
  analyse de sentiment (VADER + lexique financier).
- **Calendrier économique** : événements macro importants à venir.
- **Moteur IA** combinant :
  - Analyse technique avancée (EMA, RSI, MACD, Bollinger, ADX, Stochastique, OBV…)
  - Analyse fondamentale (contexte news / variation)
  - Analyse quantitative (recherche d'analogues historiques par plus proche voisin)
  - Machine learning (classifieur `GradientBoosting` entraîné à la volée par actif)
  - Reconnaissance de patterns (chandeliers + figures graphiques)
- **Score IA 0–100** pondéré sur 6 facteurs : qualité de tendance, confirmation des
  indicateurs, volatilité, volume, historique similaire, contexte de marché.
- **Système d'apprentissage** : chaque signal est enregistré, comparé au résultat
  réel (win / loss / expiré) et une performance agrégée est calculée.
- **Alertes automatiques** : un scanner de fond pousse les meilleures opportunités
  aux abonnés.
- **Sécurité** : anti-spam (rate limiting glissant), gestion des utilisateurs,
  utilisateurs bloqués, clés API via variables d'environnement uniquement.

## 🧩 Commandes Telegram

| Commande | Description |
|----------|-------------|
| `/start` | Présentation du bot |
| `/analyse BTCUSDT [TF]` | Analyse complète d'un actif (TF : 15m, 1h, 4h, 1d) |
| `/signaux` | Meilleures opportunités détectées (score ≥ seuil) |
| `/top` | Classement des trades par score IA |
| `/news [sujet]` | Actualités importantes + sentiment |
| `/calendrier` | Événements économiques à venir |
| `/risque CAPITAL RISQUE% ENTREE STOP [OBJECTIF]` | Taille de position & risque |
| `/portfolio` | Suivi de portefeuille (`add` / `clear`) |
| `/alertes on\|off` | S'abonner aux alertes automatiques |
| `/perf` | Performance historique de l'IA |
| `/aide` | Aide détaillée |
| `/stats` | Statistiques (admin) |

### Format d'une alerte

```
📊 SIGNAL IA

Actif : BTCUSDT (crypto)
Type : 🔴 SHORT (vente)
Entrée : 59 931.08
Objectif : 58 564.65
Stop Loss : 60 614.29
Risque/Rendement : 1:2.0
Durée estimée : 1 à 3 jours (TF 1h)

Score IA : 58/100  ██████░░░░
Probabilité estimée : 72%

Analyse :
• Technique : Tendance baissière (ADX 29), RSI 66, ATR 0.8%…
• Fondamentale : Contexte news négatif…
• Sentiment : Négatif (-0.20)
• Raisons du signal : …
```

## 🏗️ Architecture

```
trading_bot/
├── main.py                # Point d'entrée (polling)
├── config.py              # Configuration via variables d'environnement
├── models.py              # Dataclasses partagées (Quote, TradingSignal, …)
├── risk.py                # Calcul de taille de position / risque
├── data/                  # Acquisition de données
│   ├── market_data.py     # Prix & bougies (Binance / Twelve Data / Alpha Vantage)
│   ├── news.py            # News + sentiment (NewsAPI / RSS)
│   ├── economic_calendar.py
│   └── symbols.py         # Classification des tickers
├── ai/                    # Moteur d'intelligence artificielle
│   ├── indicators.py      # Indicateurs techniques vectorisés
│   ├── technical.py       # Évaluation technique structurée
│   ├── patterns.py        # Patterns + analogues historiques
│   ├── sentiment.py       # Sentiment (VADER + lexique finance)
│   ├── ml_model.py        # Modèle ML de direction
│   ├── scoring.py         # Moteur de score 0–100
│   └── engine.py          # Orchestration → TradingSignal
├── storage/database.py    # Persistance SQLite (users, portfolio, prédictions)
├── services/
│   ├── signal_scanner.py  # Scan du watchlist + cache
│   └── learning.py        # Résolution des prédictions & performance
├── bot/
│   ├── telegram_bot.py    # Handlers de commandes + jobs
│   ├── formatting.py      # Mise en forme des messages (FR, HTML)
│   └── security.py        # Rate limiting / contrôle d'accès
└── tests/                 # Tests unitaires (pytest)
```

## 🚀 Installation

```bash
cd trading_bot
pip install -r requirements.txt
cp .env.example .env         # puis éditez .env
```

Renseignez au minimum `TELEGRAM_BOT_TOKEN` dans `.env` (créez un bot avec
[@BotFather](https://t.me/BotFather)).

Les cryptos fonctionnent sans clé API (API publique Binance). Pour le forex /
actions / indices, ajoutez une clé `TWELVE_DATA_API_KEY` ou
`ALPHA_VANTAGE_API_KEY`. Pour de meilleures news, ajoutez `NEWS_API_KEY`
(sinon des flux RSS publics sont utilisés).

## ▶️ Lancement

Depuis la racine du dépôt :

```bash
python -m trading_bot.main
```

## 🌐 Déploiement 24/7

Le bot utilise le *long-polling* (connexions sortantes uniquement, aucun port à
ouvrir). Pour qu'il tourne en continu, hébergez-le sur une machine persistante
(VPS, Raspberry Pi, ou une plateforme type Railway / Fly.io / Render).

### Option A — Docker (recommandé)

```bash
cd trading_bot
cp .env.example .env         # renseignez TELEGRAM_BOT_TOKEN
docker compose up -d --build # démarre en arrière-plan, redémarre tout seul
docker compose logs -f       # suivre les logs
```

`restart: unless-stopped` relance le conteneur automatiquement en cas de crash
ou de redémarrage du serveur. La base SQLite est persistée dans un volume Docker.

### Option B — systemd (serveur Linux)

```bash
# Dépôt cloné dans /opt/Vingod, dépendances installées, .env configuré
sudo cp trading_bot/deploy/trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trading-bot   # démarre + activation au boot
journalctl -u trading-bot -f              # logs en direct
```

`Restart=always` garantit le redémarrage automatique.

> ℹ️ Un unique processus doit interroger l'API Telegram à la fois. Ne lancez pas
> deux instances avec le même token (sinon conflit de polling).

## 🧪 Tests

```bash
python -m pytest trading_bot/tests -q
```

## 🔐 Sécurité des clés

- Aucune clé n'est stockée dans le code. Tout passe par des variables
  d'environnement / le fichier `.env` (git-ignoré).
- **Ne partagez jamais votre token en clair.** S'il a fuité, régénérez-le
  immédiatement via @BotFather.
- Rate limiting anti-spam par utilisateur, gestion des utilisateurs bloqués.

## ⚙️ Variables d'environnement

Voir [`.env.example`](.env.example) pour la liste complète et commentée
(providers de données, seuil de score, intervalle de scan, limites anti-spam,
watchlist par défaut, etc.).
