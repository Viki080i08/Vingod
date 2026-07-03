# The Vape Shop by Jwell FDJ — Boutique en ligne

Site e-commerce complet pour la boutique **The Vape Shop by Jwell FDJ** à Ménétrol (63200).

## Fonctionnalités

### Boutique publique
- Page d'accueil avec présentation du magasin
- Catalogue produits avec recherche et filtres par catégorie
- Affichage des stocks en temps réel
- Fiche produit détaillée
- Panier et commande en ligne
- Paiement sécurisé via **Stripe**
- Adresse, téléphone et lien **Google Maps** pour l'itinéraire
- Avis **Google réels** (note, avis clients) synchronisés via API
- Avertissement +18 ans

### Espace vendeur (`/vendeur/login`)
- Tableau de bord : CA, commandes, alertes stock faible
- Gestion des produits (CRUD)
- **Deux modes d'ajout** :
  - Saisie manuelle
  - Upload de 1 à 4 photos → analyse IA qui pré-remplit le formulaire
- Gestion des stocks
- Suivi des ventes et mise à jour des statuts de commande

## Démarrage rapide

```bash
cd jwell-boutique
cp .env.example .env
# Éditez .env avec vos clés Stripe et JWT_SECRET
npm install
npm run db:setup
npm run dev
```

Ouvrez [http://localhost:3000](http://localhost:3000)

### Connexion vendeur

Un simple **code d'accès** suffit (par défaut : `123456789`).

Configurez dans `.env` :
```
SELLER_CODE=123456789
```

### Avis Google (données réelles)

Pour afficher les **vrais avis Google** sur le site :

1. Créez une clé API sur [Google Cloud Console](https://console.cloud.google.com/) avec l'API **Places (New)** activée
2. Ajoutez dans `.env` : `GOOGLE_PLACES_API_KEY=votre_cle`
3. Lancez : `npm run sync:reviews`

Les avis (note, nombre, textes) seront récupérés directement depuis Google Maps et affichés sur le site.

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLite par défaut (`file:./dev.db`) |
| `STRIPE_SECRET_KEY` | Clé secrète Stripe (live ou test) |
| `STRIPE_WEBHOOK_SECRET` | Secret webhook Stripe pour confirmer les paiements |
| `JWT_SECRET` | Secret pour l'authentification vendeur |
| `SELLER_CODE` | Code d'accès espace vendeur (défaut : `123456789`) |
| `GOOGLE_PLACES_API_KEY` | Clé API Google Places — pour les vrais avis Google |
| `GOOGLE_PLACE_ID` | Optionnel — ID du lieu Google |
| `OPENAI_API_KEY` | Optionnel — active l'analyse IA des photos produits |
| `NEXT_PUBLIC_APP_URL` | URL publique du site (ex: `https://votre-domaine.fr`) |

### Stripe Webhook

Pour que les commandes passent automatiquement en « Payée » et que le stock soit décrémenté :

1. Dans le [dashboard Stripe](https://dashboard.stripe.com/webhooks), créez un endpoint pointant vers `https://votre-domaine.fr/api/stripe/webhook`
2. Écoutez l'événement `checkout.session.completed`
3. Copiez le signing secret dans `STRIPE_WEBHOOK_SECRET`

## Stack technique

- **Next.js 14** (App Router)
- **TypeScript** + **Tailwind CSS**
- **Prisma** + SQLite
- **Stripe** (Checkout Sessions)
- **OpenAI GPT-4o-mini** (analyse photos, optionnel)
- **Zustand** (panier côté client)

## Informations boutique

- **Adresse** : Av. de Clermont Ferrand, 63200 Ménétrol, France
- **Téléphone** : 09 83 90 82 76
- **Horaires** : Lun–Sam 9h30–19h30

## Sécurité

> **Important** : Ne commitez jamais votre clé secrète Stripe dans le code source. Utilisez toujours des variables d'environnement (`.env`). Si votre clé a été exposée publiquement, régénérez-la immédiatement dans le dashboard Stripe.
