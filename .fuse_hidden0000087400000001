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
> API d'automatisation légale/publique** — impossible à intégrer. Le board
> s'appuie uniquement sur des flux RSS publics de médias reconnus.

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
- Le workflow `daily-update.yml` tourne automatiquement chaque nuit (6h UTC)
- Tu peux aussi le lancer manuellement : Actions → "Mise à jour quotidienne
  du board" → "Run workflow" (pratique pour tester tout de suite sans
  attendre le lendemain)

### 5. Consultation PC / téléphone
- Ouvre simplement l'URL GitHub Pages sur n'importe quel appareil
- Sur iPhone/Android : "Ajouter à l'écran d'accueil" depuis le navigateur
  pour un accès en un tap, comme une app

## Personnaliser les sources

Ouvre `scripts/fetch_news.py`, section `FEEDS` : ajoute ou retire des flux RSS
par catégorie (ia / cyber / economie / geopolitique / science / politique).
Cherche `<nom du site> RSS feed` pour trouver l'URL d'un flux qui t'intéresse.

## Section investissement

Le script `build_investment_notes()` détecte les mots-clés qui reviennent le
plus dans les news du jour (Nvidia, AI Act, taux d'intérêt, etc.) et affiche
un cadre d'analyse général. **Ce n'est pas un conseil personnalisé** — à
adapter/enrichir toi-même si tu veux des règles plus précises (ex. alertes
sur un titre particulier).

## Structure des fichiers

```
index.html          → page principale (à ne pas renommer)
style.css           → identité visuelle
app.js              → logique des onglets + affichage
data/*.json         → un fichier par jour de la semaine, régénéré chaque jour
scripts/fetch_news.py → le script d'agrégation RSS
.github/workflows/daily-update.yml → l'automatisation quotidienne
```
