# Veille IA & Monde — Board quotidien

Board de veille (IA, cybersécurité, économie, géopolitique, science) avec 7 onglets
(un par jour de la semaine), résumés cliquables, et repères d'investissement.
100% gratuit, hébergé sur GitHub Pages, mis à jour automatiquement chaque jour via
GitHub Actions.

## Aperçu du fonctionnement

```
Chaque nuit (cron GitHub Actions)
        │
        ▼
scripts/fetch_news.py  → lit des flux RSS publics (TechCrunch, Le Monde,
        │                  Krebs on Security, Nature, etc.)
        ▼
data/<jour>.json        → écrit/écrase le fichier du jour de la semaine en cours
        │
        ▼
git commit + push        → GitHub Pages republie automatiquement le site
        │
        ▼
index.html (dans ton navigateur, PC ou téléphone)
```

Comme demandé, il y a **un onglet par jour de la semaine** (Lundi → Dimanche).
Chaque jour, le script écrase les données de l'onglet correspondant au jour
courant. Donc l'onglet "aujourd'hui" est toujours frais ; les 6 autres onglets
gardent les données de leur dernière occurrence (ex. l'onglet "Mardi" contient
les infos du dernier mardi passé, jusqu'à ce qu'il soit rafraîchi la semaine
suivante).

> Limite honnête : **X (Twitter)** n'est pas inclus car l'API gratuite est
> trop restreinte pour une automatisation fiable, et **WhatsApp n'a aucune
> API d'automatisation légale/publique** — impossible à intégrer, même en
> fournissant tes identifiants. Le board s'appuie sur des flux RSS publics
> de médias reconnus, sur l'API gratuite CoinGecko pour les prix crypto, et
> (depuis peu) sur 2 newsletters personnelles lues par email (voir
> ci-dessous).

## Newsletters personnelles (email)

En plus des flux RSS publics, le board récupère chaque jour l'édition la
plus récente de 2 newsletters reçues par email :

- **La Cour des Grands** (`news@lacourdesgrands.co`)
- **The Next Big Shit** (`luc@the-nbs.fr`)

Pour chacune, `fetch_newsletters()` dans `scripts/fetch_news.py` :
- se connecte en IMAP à la boîte Gmail qui reçoit ces newsletters,
- récupère l'email le plus récent de chaque expéditeur,
- en extrait le titre (objet de l'email), le lien vers l'article en ligne,
  et un **résumé synthétique** (les points clés du jour, sans les
  sponsors/pubs/sondages),
- range le tout dans une nouvelle catégorie **"Newsletters"** du board.

### Configuration requise (à faire une seule fois, sur GitHub)

1. Sur le compte Gmail qui reçoit ces 2 newsletters, active la validation en
   2 étapes si ce n'est pas déjà fait, puis génère un **mot de passe
   d'application** : myaccount.google.com → Sécurité → Validation en 2
   étapes → Mots de passe des applications.
2. Dans le dépôt GitHub : Settings → Secrets and variables → Actions → "New
   repository secret", et ajoute :
   - `GMAIL_ADDRESS` : l'adresse Gmail concernée
   - `GMAIL_APP_PASSWORD` : le mot de passe d'application généré à l'étape 1
     (16 caractères, pas ton mot de passe Gmail habituel)

Sans ces 2 secrets, la catégorie "Newsletters" reste simplement vide (aucun
échec du run — même tolérance aux pannes que le reste du script).

> ⚠️ **Décalage possible sur "The Next Big Shit"** : cette newsletter arrive
> généralement entre 7h et 9h heure de Paris, donc après le cron quotidien
> du board (6h UTC). Ce jour-là, le board affiche encore l'édition de la
> veille (la fenêtre de recherche IMAP couvre 2 jours). "La Cour des
> Grands", elle, arrive vers 4h30 UTC et est donc toujours à jour.

## Cryptomonnaies

- **News** : CoinDesk, Cointelegraph, Decrypt (flux RSS publics)
- **Prix** : snapshot BTC / ETH / SOL / XRP via l'API publique CoinGecko
  (gratuite, sans clé, en EUR et USD, avec variation 24h)
- Modifiable dans `scripts/fetch_news.py`, variables `FEEDS["crypto"]` et
  `CRYPTO_IDS` (identifiants CoinGecko, ex. ajouter `"cardano"`, `"binancecoin"`)

## Déploiement (10 minutes, gratuit)

### 1. Crée le dépôt GitHub
- Va sur github.com → "New repository" → nomme-le par ex. `veille-ia-board`
- Coche "Public" (nécessaire pour GitHub Pages gratuit)

### 2. Envoie les fichiers
Depuis ce dossier (`ai-board/`), dans un terminal :
```bash
git init
git add .
git commit -m "Premier déploiement du board"
git branch -M main
git remote add origin https://github.com/TON-PSEUDO/veille-ia-board.git
git push -u origin main
```

### 3. Active GitHub Pages
- Dans le dépôt : Settings → Pages
- Source : "Deploy from a branch" → branche `main`, dossier `/ (root)`
- Sauvegarde. Ton site sera visible sous quelques minutes à :
  `https://TON-PSEUDO.github.io/veille-ia-board/`

### 4. Active le workflow automatique
- Onglet "Actions" du dépôt → autorise les workflows si demandé
- Le workflow `daily-update.yml` tourne automatiquement chaque nuit à 6h00 UTC,
  soit **7h00 (heure d'hiver) ou 8h00 (heure d'été) à Paris** — prêt avant ton
  petit-déjeuner et avant l'ouverture d'Euronext Paris à 9h00
- Tu peux aussi le lancer manuellement : Actions → "Mise à jour quotidienne
  du board" → "Run workflow" (pratique pour tester tout de suite sans
  attendre le lendemain)

> ⚠️ **Fiabilité de l'horaire** : sur le plan gratuit, GitHub ne garantit pas
> une exécution à la minute près — un retard de 5 à 20 minutes est normal,
> occasionnellement plus en cas de forte charge sur leurs serveurs. Si tu
> constates régulièrement un retard gênant, avance le cron à `0 5 * * *`
> (5h00 UTC) dans `.github/workflows/daily-update.yml` pour plus de marge.

### 5. Consultation PC / téléphone
- Ouvre simplement l'URL GitHub Pages sur n'importe quel appareil
- Sur iPhone/Android : "Ajouter à l'écran d'accueil" depuis le navigateur
  pour un accès en un tap, comme une app

## Personnaliser les sources

Ouvre `scripts/fetch_news.py`, section `FEEDS` : ajoute ou retire des flux RSS
par catégorie (ia / cyber / economie / geopolitique / science / politique).
Cherche `<nom du site> RSS feed` pour trouver l'URL d'un flux qui t'intéresse.

## Section investissement

La section "Repères Investissement" comprend maintenant :
- **Signaux du jour** : mots-clés fréquents détectés dans les news (`build_investment_notes()`)
- **Indices de marché** : CAC 40, S&P 500, Nasdaq, Dow Jones, DAX, Nikkei — snapshot via
  l'API gratuite Stooq (`fetch_market_indices()`), variation calculée depuis l'ouverture du jour
- **ETF à connaître** : liste statique de référence (large cap, IA/semi-conducteurs,
  cybersécurité, crypto) dans `index.html`, à adapter librement
- **Sociétés mentionnées** : détection automatique des entreprises citées dans les flux
  du jour (`detect_mentioned_companies()`) — purement factuel, pas une sélection de valeurs
- **Acteurs majeurs par secteur** : liste statique de référence dans `index.html`

**Je n'inclus volontairement aucune recommandation de titres individuels peu connus**
(small/mid caps) — c'est un conseil d'investissement personnalisé à fort risque que je ne
suis pas en mesure de fournir de façon responsable. Pour ça, utilise un screener indépendant
(Zonebourse, TradingView, Boursorama) et fais ta propre analyse.

Tout ceci reste une **synthèse générale, pas une recommandation personnalisée** — adapte les
listes statiques à tes propres critères si besoin.

## Structure des fichiers

```
index.html          → page principale (à ne pas renommer)
style.css           → identité visuelle
app.js              → logique des onglets + affichage
data/*.json         → un fichier par jour de la semaine, régénéré chaque jour
scripts/fetch_news.py → le script d'agrégation RSS
.github/workflows/daily-update.yml → l'automatisation quotidienne
```
