# ⚽🤖 PronoIA — Bot Telegram de pronostics sportifs premium

PronoIA est un assistant Telegram complet qui **analyse automatiquement les
matchs sportifs grâce à une IA d'analyse**, génère des recommandations
**personnalisées selon le profil de risque** de chaque utilisateur, et envoie
des pronostics aux abonnés premium. Le projet inclut le bot Telegram, les
paiements Telegram, un moteur d'analyse, une base PostgreSQL, des tâches
programmées et un **dashboard administrateur web**.

> ⚠️ **Sécurité — important**
> Le token de bot a été partagé en clair lors de la demande. **Régénérez-le
> immédiatement** via [@BotFather](https://t.me/BotFather) (`/revoke` puis
> `/token`). Ne committez **jamais** un token : il se configure uniquement dans
> le fichier `.env` (ignoré par git).

---

## ✨ Fonctionnalités

### 🤖 Bot Telegram
- Inscription automatique et **message de bienvenue** au `/start`
- **Onboarding** : choix du profil de risque dès la première utilisation
- Menu complet avec clavier :
  - 📊 Pronostics du jour
  - 🎯 Mon profil risque
  - 🎟️ Créer un combiné
  - 🤖 Analyse IA
  - 📈 Statistiques
  - 💳 Abonnement
  - ⚙️ Paramètres
- Commandes : `/start`, `/menu`, `/pronos`, `/profil`, `/combine`, `/ia`,
  `/stats`, `/abonnement`, `/parametres`, `/aide`, `/whoami`

### 🧠 Moteur d'analyse IA — 100% maison, **sans API sportive**
L'IA est entièrement développée dans ce projet et **ne dépend d'aucune API
sportive externe**. Elle combine deux techniques de référence puis les fusionne
pour plus de robustesse :

1. **Système de notes Elo** (comme aux échecs / FiveThirtyEight) : une note de
   force par équipe, qui **s'auto-améliore en continu** à partir des résultats.
2. **Modèle de buts de Poisson avec correction de Dixon-Coles** (standard
   académique du football), qui corrige notamment la sous-estimation des petits
   scores (0-0, 1-0, 0-1, 1-1).

S'y ajoutent les signaux contextuels : forme récente, résultats précédents,
stats offensives/défensives, confrontations directes, domicile/extérieur,
absences importantes, tendances (momentum).

Pour chaque rencontre, l'IA produit : **probabilité estimée**, **niveau de
confiance**, **niveau de risque**, **cotes (équitables et marché)**, **valeur
attendue** et une **explication détaillée** en français. Tout est pur-Python,
déterministe et rapide — aucune dépendance ML lourde, aucun flux de données
payant.

Le **moteur interne** maintient une table de **notes de force réalistes** pour
les grands clubs européens, génère un calendrier cohérent de matchs (jour J +
jusqu'à 5 jours) et met à jour les notes Elo à mesure que les résultats
tombent : le modèle s'améliore donc tout seul, sans intervention.

### 🎯 Personnalisation par profil
- 🟢 **Sécurisé** — privilégie les plus fortes probabilités
- 🟡 **Équilibré** — compromis sécurité / rendement
- 🔴 **Risqué** — accepte plus de variance pour de meilleures cotes

Le profil est sauvegardé et l'IA adapte ses recommandations en conséquence.

### ⚽ Génération automatique des pronostics
Chaque jour, le système :
1. récupère les matchs disponibles (aujourd'hui + jusqu'à **5 jours**) ;
2. analyse toutes les rencontres ;
3. classe les meilleures opportunités par profil ;
4. génère des **pronostics simples** et un **combiné optimisé** ;
5. **envoie automatiquement** les pronostics aux abonnés.

### 🎟️ Création de combinés
L'utilisateur sélectionne des matchs et des paris, voit la **cote totale**, et
peut demander une **proposition optimisée par l'IA** selon son profil.

### 💳 Paiements (Telegram Payments)
- Abonnement mensuel via Telegram Payments
- Validation automatique (`pre_checkout` + `successful_payment`)
- **Activation du compte** après paiement
- **Expiration automatique** et **blocage** en fin d'abonnement
- Stockage : ID Telegram, statut, date d'expiration, **historique des paiements**
- **Mode démo** sans token de paiement (activation simulée pour tester)

### 📊 Statistiques & amélioration continue
Suivi des pronostics envoyés, des résultats, du **taux de réussite** et du ROI
par profil. Les résultats passés mettent à jour les statistiques des équipes
(forme, moyennes de buts, momentum) qui alimentent les futures analyses.

### 🖥️ Dashboard administrateur (web)
Interface protégée (HTTP Basic) pour consulter les utilisateurs, les
abonnements, les analyses IA, les paiements et les statistiques globales.

---

## 🏗️ Architecture

```
sportsbot/
├── sportsbot/
│   ├── config.py            # configuration via variables d'environnement
│   ├── ai/                  # moteur d'analyse (engine.py, profiles.py)
│   ├── providers/           # sources de données (demo, football-data.org)
│   ├── services/            # sync, génération de tips & combos
│   ├── db/                  # modèles SQLAlchemy, sessions, repositories
│   ├── bot/                 # application Telegram, handlers, claviers, textes
│   ├── scheduler/           # tâches programmées (JobQueue)
│   ├── admin/               # dashboard web FastAPI + templates
│   └── main.py              # point d'entrée CLI
├── tests/smoke_test.py      # test hors-ligne de bout en bout
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

**Stack** : Python 3.12 • python-telegram-bot 21 • SQLAlchemy 2 • PostgreSQL •
APScheduler (JobQueue) • FastAPI + Jinja2 • httpx.

---

## 🚀 Démarrage rapide (local)

```bash
cd sportsbot

# 1. Dépendances
python -m venv .venv && source .venv/bin/activate   # (ou virtualenv .venv)
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Éditez .env : renseignez TELEGRAM_BOT_TOKEN et ADMIN_IDS au minimum.

# 3. Lancer le bot + le dashboard
python -m sportsbot all
```

Par défaut, la base est **SQLite** (`pronoia.db`) et le fournisseur de données
est **demo** (matchs réalistes générés localement, sans clé API). Le tout
fonctionne donc immédiatement, hors-ligne.

### Commandes CLI
```bash
python -m sportsbot check    # diagnostic : vérifie la config + le token
python -m sportsbot bot      # bot Telegram uniquement
python -m sportsbot admin    # dashboard web uniquement
python -m sportsbot all      # les deux (dashboard dans un thread)
python -m sportsbot sync     # synchronisation + analyse ponctuelle
python -m sportsbot initdb   # créer les tables et quitter
```

> 💡 Commencez **toujours** par `python -m sportsbot check` : il confirme que
> votre token Telegram est valide avant de lancer le bot.

## 🟢 Faire tourner le bot en continu (24/7)

Le bot doit tourner sur une machine **toujours allumée** (votre serveur, un VPS,
un Raspberry Pi, un PaaS…). Deux options « tout le temps jusqu'à désactivation » :

**Option A — script auto-redémarrage** (simple) :
```bash
./scripts/run_forever.sh      # relance automatiquement en cas d'arrêt
```

**Option B — service systemd** (recommandé sur serveur Linux) :
```bash
sudo cp deploy/pronoia.service /etc/systemd/system/pronoia.service
sudo systemctl daemon-reload
sudo systemctl enable --now pronoia     # démarre + relance au boot
journalctl -u pronoia -f                # voir les logs en direct
# Pour désactiver : sudo systemctl stop pronoia
```

**Option C — Docker** : `docker compose up -d --build` (redémarre tout seul).

> ⚠️ Tant qu'aucun de ces processus ne tourne sur une machine allumée, cliquer
> dans Telegram ne déclenche rien : c'est lui qui « écoute » et répond.

---

## 🐘 Production avec PostgreSQL (Docker)

```bash
cp .env.example .env   # renseignez au moins TELEGRAM_BOT_TOKEN et ADMIN_IDS
docker compose up --build
```

`docker-compose.yml` démarre PostgreSQL et l'application (bot + dashboard sur le
port `8080`). La variable `DATABASE_URL` est automatiquement pointée vers le
service Postgres.

Pour utiliser PostgreSQL sans Docker, définissez dans `.env` :
```
DATABASE_URL=postgresql+psycopg2://prono:prono@localhost:5432/prono
```

---

## 🔑 Configuration (.env)

| Variable | Description | Défaut |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token @BotFather (**obligatoire**) | — |
| `ADMIN_IDS` | IDs Telegram admins (séparés par virgules) | — |
| `TELEGRAM_PAYMENT_PROVIDER_TOKEN` | Token paiement (vide = mode démo) | vide |
| `SUBSCRIPTION_PRICE_EUR` | Prix de l'abonnement | `19.99` |
| `SUBSCRIPTION_DURATION_DAYS` | Durée de l'abonnement | `30` |
| `DATABASE_URL` | Connexion base de données | SQLite |
| `DATA_PROVIDER` | `demo` ou `footballdata` | `demo` |
| `FOOTBALL_DATA_API_KEY` | Clé football-data.org (si réel) | vide |
| `FORECAST_HORIZON_DAYS` | Jours analysés (max 5) | `5` |
| `DAILY_SYNC_TIME` / `DAILY_PUSH_TIME` / `RESULTS_UPDATE_TIME` | Heures des tâches | `06:00` / `09:00` / `23:30` |
| `ADMIN_WEB_*` | Hôte, port, identifiants du dashboard | `0.0.0.0:8080`, `admin/changeme` |

### Activer les vraies données football
1. Créez une clé gratuite sur [football-data.org](https://www.football-data.org/).
2. Dans `.env` : `DATA_PROVIDER=footballdata` et `FOOTBALL_DATA_API_KEY=...`.
En cas d'erreur ou de quota dépassé, le système bascule automatiquement sur le
fournisseur **demo** pour rester fonctionnel.

### Activer les paiements Telegram
1. `@BotFather` → votre bot → *Payments* → connectez un fournisseur (ex. Stripe).
2. Renseignez `TELEGRAM_PAYMENT_PROVIDER_TOKEN` dans `.env`.
Sans ce token, le bouton « S'abonner » fonctionne en **mode démo** (activation
simulée), ce qui permet de tester tout le parcours.

---

## 🛠️ Commandes administrateur (dans Telegram)
Réservées aux `ADMIN_IDS` :
- `/admin` — panneau de contrôle
- `/sync` — synchroniser et analyser les matchs
- `/push` — envoyer les pronostics du jour aux abonnés
- `/broadcast <message>` — message à tous les utilisateurs
- `/grant <telegram_id> [jours]` — offrir un abonnement
- `/revoke <telegram_id>` — révoquer un abonnement

Dashboard web : `http://localhost:8080` (identifiants `ADMIN_WEB_*`).

---

## ✅ Tests

```bash
python -m tests.smoke_test
```

Test hors-ligne qui vérifie le moteur d'analyse, le fournisseur demo, la
synchronisation, la génération des opportunités/combos, le cycle d'abonnement
et le règlement des résultats — sans token Telegram ni serveur Postgres.

---

## ⚖️ Avertissement
Les paris sportifs comportent des risques. Ce logiciel est fourni à des fins
éducatives et de divertissement. Aucune garantie de gain. Jouez de manière
responsable et respectez la législation de votre pays.
