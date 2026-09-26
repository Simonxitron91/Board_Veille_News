#!/usr/bin/env python3
"""
Récupère des flux RSS publics, les classe par catégorie, et écrit
data/<jour_de_la_semaine>.json pour alimenter le board.

Sources modifiables ci-dessous (FEEDS). Un flux cassé est ignoré
silencieusement (best effort) pour ne jamais faire échouer le run entier.
"""
import email
import imaplib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser

try:
    from deep_translator import GoogleTranslator
    _TRANSLATOR_AVAILABLE = True
except ImportError:
    _TRANSLATOR_AVAILABLE = False

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# Sources déjà rédigées en français -> pas besoin de traduction
FRENCH_SOURCES = {"Les Echos", "France 24", "Le Monde", "Le Monde Politique", "Le Point Politique"}

_translate_cache: dict = {}


def translate_to_french(text: str) -> str:
    """Traduit un texte en français (best effort, avec cache).
    En cas d'échec (réseau, quota Google Translate, etc.), on retourne le
    texte original pour ne jamais faire échouer le run entier -- même
    logique de tolérance aux pannes que le reste du script."""
    if not text or not _TRANSLATOR_AVAILABLE:
        return text
    if text in _translate_cache:
        return _translate_cache[text]
    try:
        translated = GoogleTranslator(source="auto", target="fr").translate(text)
        result = translated.strip() if translated else text
    except Exception as e:
        print(f"[warn] échec traduction: {e}", file=sys.stderr)
        result = text
    _translate_cache[text] = result
    return result

WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# --- Sources par catégorie -------------------------------------------------
# Ajoute / retire des flux librement. Format: (nom_source, url_rss)
FEEDS = {
    "ia": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
        ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
        ("OpenAI News", "https://openai.com/news/rss.xml"),
        ("Google DeepMind News", "https://deepmind.google/blog/rss.xml"),
    ],
    "cyber": [
        ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
        ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
        ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ],
    "economie": [
        ("Les Echos", "https://www.lesechos.fr/rss/rss_une.xml"),
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
        ("Investing.com", "https://www.investing.com/rss/news_14.rss"),
    ],
    "crypto": [
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Cointelegraph", "https://cointelegraph.com/rss"),
        ("Decrypt", "https://decrypt.co/feed"),
    ],
    "geopolitique": [
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("France 24", "https://www.france24.com/fr/rss"),
        ("Le Monde", "https://www.lemonde.fr/rss/une.xml"),
    ],
    "science": [
        ("Nature News", "https://www.nature.com/nature.rss"),
        ("Ars Technica Science", "https://feeds.arstechnica.com/arstechnica/science"),
    ],
    "politique": [
        ("Le Monde Politique", "https://www.lemonde.fr/politique/rss_full.xml"),
        ("Le Point Politique", "https://www.lepoint.fr/arc/outboundfeeds/rss/category/politique/"),
    ],
    "productivite": [
        ("One Thing at a Time (Marc Zao-Sanders)", "https://marczaosanders.substack.com/feed"),
    ],
}

LABELS = {
    "ia": "Intelligence Artificielle",
    "cyber": "Cybersécurité",
    "economie": "Économie & Marchés",
    "crypto": "Cryptomonnaies",
    "geopolitique": "Géopolitique & Général",
    "science": "Science",
    "politique": "Politique",
    "productivite": "Productivité & Time Management",
    "missions": "Missions & Demandes de services",
    "newsletters": "Newsletters",
}

# --- Newsletters personnelles reçues par email -----------------------------
# Contrairement aux autres catégories (flux RSS publics), celle-ci lit
# directement la boîte mail (IMAP) pour récupérer l'édition du jour de 2
# newsletters suivies par Nicolas, et en extrait titre + lien + un résumé
# synthétique (points clés), sans le contenu sponsorisé/pubs/sondages.
NEWSLETTER_SOURCES = [
    {"name": "La Cour des Grands", "sender": "news@lacourdesgrands.co", "extractor": "lcdg", "domain": "lacourdesgrands.co"},
    {"name": "The Next Big Shit", "sender": "luc@the-nbs.fr", "extractor": "nbs", "domain": "the-nbs.fr"},
]
# Fenêtre de recherche élargie à 2 jours : "The Next Big Shit" est envoyée
# ~7h-9h heure de Paris, donc après le cron quotidien (6h UTC). Ce jour-là,
# le board affiche l'édition de la veille (encore dans la fenêtre) plutôt
# qu'une catégorie vide -- 1 jour de décalage possible sur cette source.
NEWSLETTER_LOOKBACK_DAYS = 2
MAX_HIGHLIGHTS = 5


def _decode_subject(raw_subject: str) -> str:
    if not raw_subject:
        return ""
    decoded = ""
    for text, enc in decode_header(raw_subject):
        if isinstance(text, bytes):
            decoded += text.decode(enc or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded.strip()


def _get_plaintext_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition") or "")
            if part.get_content_type() == "text/plain" and "attachment" not in disposition:
                charset = part.get_content_charset() or "utf-8"
                try:
                    return part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    continue
        return ""
    charset = msg.get_content_charset() or "utf-8"
    try:
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    except Exception:
        return str(msg.get_payload() or "")


def _clean_markdown(text: str) -> str:
    """Retire la syntaxe markdown des newsletters (gras/italique/liens) pour
    ne garder qu'un texte brut lisible dans le résumé."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"==(.+?)==", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^[^\w(«]+", "", text.strip())  # emoji de tête
    text = re.sub(r"\s+", " ", text).strip(" -:*")
    return text.strip()


def _extract_link(body: str, domain: str) -> str:
    m = re.search(rf"https://www\.{re.escape(domain)}/p/\S+", body)
    return m.group(0).rstrip(".,)") if m else ""


def _extract_highlights_lcdg(body: str) -> list:
    """"La Cour des Grands" liste ses points clés du jour sous "Au menu du
    jour :" avant le premier article -- c'est ce bloc qu'on synthétise."""
    block = re.search(r"Au menu du jour\s*:(.*?)(?:Et bien plus encore|———+)", body, re.S)
    highlights = []
    if block:
        for line in block.group(1).splitlines():
            line = line.strip().lstrip("*").strip()
            if not line:
                continue
            cleaned = _clean_markdown(line)
            if cleaned:
                highlights.append(cleaned)
    return highlights[:MAX_HIGHLIGHTS]


def _extract_highlights_nbs(body: str) -> list:
    """"The Next Big Shit" structure ses actus du jour en titres de ligne
    "## **#1 ...**", "## **#2 ...**", etc. -- on récupère ces titres de
    section (le markdown de la source est parfois mal formé, ex. doubles
    "****", donc on nettoie par simple suppression des astérisques plutôt
    que par un regex de paires gras/gras)."""
    highlights = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("##"):
            continue
        text = line.lstrip("#").strip().replace("*", "").strip()
        text = re.sub(r"^#?\d+\s*", "", text)  # retire la numérotation "#3 "
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            highlights.append(text)
    return highlights[:MAX_HIGHLIGHTS]


_EXTRACTORS = {"lcdg": _extract_highlights_lcdg, "nbs": _extract_highlights_nbs}


def fetch_newsletters() -> list:
    """Récupère la dernière édition de chaque newsletter suivie par email
    (IMAP Gmail). Best effort : si les identifiants (secrets GitHub
    GMAIL_ADDRESS / GMAIL_APP_PASSWORD) sont absents ou la connexion échoue,
    la catégorie reste vide sans faire échouer le run -- même logique de
    tolérance que le reste du script."""
    address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not address or not app_password:
        print("[warn] GMAIL_ADDRESS/GMAIL_APP_PASSWORD absents -> catégorie newsletters vide", file=sys.stderr)
        return []

    items = []
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(address, app_password)
        imap.select("INBOX")
        since = (datetime.now(timezone.utc) - timedelta(days=NEWSLETTER_LOOKBACK_DAYS)).strftime("%d-%b-%Y")

        for src in NEWSLETTER_SOURCES:
            try:
                status, data = imap.search(None, f'(FROM "{src["sender"]}" SINCE {since})')
                if status != "OK" or not data or not data[0]:
                    print(f"[warn] aucune édition récente trouvée pour {src['name']}", file=sys.stderr)
                    continue
                latest_id = data[0].split()[-1]  # le plus récent dans la fenêtre
                status, msg_data = imap.fetch(latest_id, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = _decode_subject(msg.get("Subject", ""))
                body = _get_plaintext_body(msg)
                highlights = _EXTRACTORS[src["extractor"]](body)
                link = _extract_link(body, src["domain"])
                try:
                    msg_date = parsedate_to_datetime(msg.get("Date")).strftime("%Y-%m-%d")
                except Exception:
                    msg_date = ""
                summary = "\n".join(f"• {h}" for h in highlights) if highlights else clean_summary(body, max_len=400)
                items.append({
                    "title": subject or src["name"],
                    "summary": summary,
                    "source": src["name"],
                    "url": link,
                    "date": msg_date,
                })
            except Exception as e:
                print(f"[warn] échec newsletter {src['name']}: {e}", file=sys.stderr)
                continue
        imap.logout()
    except Exception as e:
        print(f"[warn] échec connexion IMAP: {e}", file=sys.stderr)
    return items

# --- Missions freelance & demandes de services -----------------------------
# Contrairement aux autres catégories (agrégation brute de flux presse),
# celle-ci filtre un flux généraliste de petites annonces freelance par
# mots-clés pour ne garder que ce qui correspond au profil de Nicolas
# (conseil IT, Agile/Scrum, cloud, IA) ou aux demandes ponctuelles de type
# création/audit/correction de site web, automatisation de tâches.
MISSIONS_FEED = ("Codeur.com", "https://www.codeur.com/projects.rss")
MAX_MISSIONS = 15
MISSION_KEYWORDS = [
    # Site web : création, refonte, audit, correctifs, maintenance
    "site web", "site internet", "wordpress", "refonte de site", "refonte du site",
    "création de site", "créer un site", "audit de site", "audit du site",
    "audit technique", "corriger mon site", "corriger le site", "bug sur mon site",
    "mise à jour site", "mise à jour du site", "maintenance site", "maintenance du site",
    "webmaster", "landing page", "site e-commerce",
    # Automatisation de tâches récurrentes
    "automatisation", "automatiser", "tâches récurrentes", "tâche récurrente",
    "script python", "rpa", "zapier", "make.com", "workflow", "intégration api",
    # Conseil IT / Agile / Cloud / IA — cœur de profil
    "consultant it", "consultant informatique", "audit informatique",
    "migration cloud", "cloud aws", "cloud azure", "scrum master", "product owner",
    "gestion de projet agile", "intelligence artificielle", "chatgpt", "chatbot",
    "automatisation ia", "ia générative",
]


def fetch_missions() -> list:
    """Filtre le flux généraliste Codeur.com par mots-clés du profil.
    Best effort comme le reste du script : un flux cassé ne fait pas
    échouer le run, il donne juste une catégorie vide ce jour-là."""
    source_name, url = MISSIONS_FEED
    items = []
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            print(f"[warn] flux illisible: {source_name} ({url})", file=sys.stderr)
            return items
        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            summary = clean_summary(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            blob = f"{title} {summary}".lower()
            if not any(kw in blob for kw in MISSION_KEYWORDS):
                continue
            link = getattr(entry, "link", "")
            try:
                date_str = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d") if getattr(entry, "published_parsed", None) else ""
            except Exception:
                date_str = ""
            items.append({
                "title": title,
                "summary": summary,
                "source": source_name,
                "url": link,
                "date": date_str,
            })
            if len(items) >= MAX_MISSIONS:
                break
    except Exception as e:
        print(f"[warn] échec du flux {source_name}: {e}", file=sys.stderr)
    return items

# Indices suivis (symboles Stooq, gratuits sans clé)
MARKET_INDICES = [
    ("^spx", "S&P 500"),
    ("^ndq", "Nasdaq Composite"),
    ("^dji", "Dow Jones"),
    ("^cac", "CAC 40"),
    ("^dax", "DAX"),
    ("^nkx", "Nikkei 225"),
]


def fetch_market_indices() -> list:
    """Snapshot des principaux indices via l'API CSV gratuite Stooq.
    Variation calculée entre l'ouverture et le dernier cours du jour
    (pas de J-1 disponible sans API payante -> libellé 'depuis l'ouverture')."""
    symbols = ",".join(s for s, _ in MARKET_INDICES)
    url = f"https://stooq.com/q/l/?s={symbols}&f=sd2t2ohlc&h&e=csv"
    results = []
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            text = resp.read().decode("utf-8")
        lines = [l for l in text.strip().split("\n") if l]
        header = lines[0].split(",")
        name_map = dict(MARKET_INDICES)
        for line in lines[1:]:
            parts = line.split(",")
            row = dict(zip(header, parts))
            symbol = row.get("Symbol", "").lower()
            try:
                open_p = float(row.get("Open", "0") or 0)
                close_p = float(row.get("Close", "0") or 0)
                change_pct = round((close_p - open_p) / open_p * 100, 2) if open_p else 0.0
            except (ValueError, ZeroDivisionError):
                close_p, change_pct = None, 0.0
            results.append({
                "symbol": symbol,
                "name": name_map.get(symbol, symbol),
                "value": close_p,
                "change_pct": change_pct,
            })
    except Exception as e:
        print(f"[warn] échec récupération indices Stooq: {e}", file=sys.stderr)
    return results


def detect_mentioned_companies(categories: dict) -> list:
    """Repère les entreprises qui reviennent le plus dans les news du jour
    (IA, cyber, économie, crypto). Purement factuel/descriptif -> pas une
    recommandation d'achat, juste ce qui fait l'actualité aujourd'hui."""
    watch_list = [
        "Nvidia", "OpenAI", "Anthropic", "Google", "Alphabet", "Meta", "Microsoft",
        "Apple", "Amazon", "Tesla", "AMD", "Intel", "TSMC", "Coinbase", "Binance",
        "Palantir", "CrowdStrike", "Palo Alto Networks", "Broadcom", "ASML",
        "Airbus", "BitMart", "Ripple",
    ]
    text_blob = " ".join(
        it["title"] + " " + it["summary"]
        for cat in categories.values() for it in cat["items"]
    )
    mentions = []
    for name in watch_list:
        count = text_blob.count(name)
        if count > 0:
            mentions.append({"name": name, "mentions": count})
    mentions.sort(key=lambda x: -x["mentions"])
    return mentions[:8]
CRYPTO_IDS = ["bitcoin", "ethereum", "solana", "ripple"]

MAX_ITEMS_PER_FEED = 4


def fetch_crypto_prices() -> list:
    """Snapshot de prix via l'API publique CoinGecko (gratuite, sans clé,
    limite ~10-30 requêtes/minute -> largement suffisant pour un run quotidien)."""
    ids = ",".join(CRYPTO_IDS)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price?ids={ids}"
        f"&vs_currencies=eur,usd&include_24hr_change=true"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        prices = []
        for coin_id in CRYPTO_IDS:
            if coin_id not in data:
                continue
            entry = data[coin_id]
            prices.append({
                "id": coin_id,
                "symbol": coin_id.upper()[:3] if coin_id != "ripple" else "XRP",
                "eur": entry.get("eur"),
                "usd": entry.get("usd"),
                "change_24h": round(entry.get("usd_24h_change", 0), 2),
            })
        return prices
    except Exception as e:
        print(f"[warn] échec récupération prix CoinGecko: {e}", file=sys.stderr)
        return []


def clean_summary(raw: str, max_len: int = 260) -> str:
    """Retire les balises HTML et tronque proprement."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def fetch_category(name: str, sources: list) -> list:
    items = []
    for source_name, url in sources:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                print(f"[warn] flux illisible: {source_name} ({url})", file=sys.stderr)
                continue
            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                title = getattr(entry, "title", "").strip()
                if not title:
                    continue
                summary = clean_summary(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                if source_name not in FRENCH_SOURCES:
                    title = translate_to_french(title)
                    summary = translate_to_french(summary)
                link = getattr(entry, "link", "")
                published = getattr(entry, "published", "") or getattr(entry, "updated", "")
                try:
                    date_str = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d") if getattr(entry, "published_parsed", None) else ""
                except Exception:
                    date_str = ""
                items.append({
                    "title": title,
                    "summary": summary,
                    "source": source_name,
                    "url": link,
                    "date": date_str or published[:10],
                })
        except Exception as e:
            print(f"[warn] échec du flux {source_name}: {e}", file=sys.stderr)
            continue
    return items


def build_investment_notes(categories: dict) -> dict:
    """Génère une synthèse simple à partir des mots-clés fréquents des news IA/cyber/économie.
    Ce n'est PAS un conseil personnalisé, juste un repère de tendance basé sur la fréquence
    des sujets qui reviennent dans les flux du jour."""
    keywords = ["Nvidia", "OpenAI", "Anthropic", "Google", "Meta", "Microsoft",
                "quantique", "semi-conducteur", "AI Act", "régulation", "taux d'intérêt",
                "inflation", "pétrole", "ransomware", "cyberattaque",
                "Bitcoin", "Ethereum", "ETF", "halving", "stablecoin", "SEC"]
    text_blob = " ".join(
        it["title"] + " " + it["summary"]
        for cat in categories.values() for it in cat["items"]
    )
    signaux = []
    for kw in keywords:
        count = text_blob.lower().count(kw.lower())
        if count > 0:
            signaux.append(f"'{kw}' mentionné {count}x dans les flux du jour")
    signaux = signaux[:6]

    framework = (
        "Cadre d'analyse à moyen/long terme : privilégier la diversification sectorielle "
        "plutôt que le pari sur un seul acteur IA ; suivre les échéances réglementaires "
        "(AI Act, textes nationaux) qui peuvent créer de la volatilité court-terme sur les "
        "valeurs tech ; garder une exposition mesurée à l'énergie/matières premières en "
        "période de tensions géopolitiques ; le dollar-cost averaging (investissement "
        "périodique) reste une approche disciplinée pour lisser la volatilité sur les "
        "valeurs IA et semi-conducteurs, historiquement très cycliques."
    )
    disclaimer = (
        "Ceci est une synthèse d'information générale et non une recommandation "
        "personnalisée. Elle ne remplace pas l'avis d'un conseiller en investissement "
        "financier agréé, et ne tient pas compte de votre situation personnelle."
    )
    return {"signaux": signaux, "framework": framework, "disclaimer": disclaimer}


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    weekday_idx = now.weekday()  # 0 = lundi
    weekday_name = WEEKDAYS_FR[weekday_idx]

    categories = {}
    for cat_key, sources in FEEDS.items():
        items = fetch_category(cat_key, sources)
        categories[cat_key] = {"label": LABELS[cat_key], "items": items}

    categories["newsletters"] = {"label": LABELS["newsletters"], "items": fetch_newsletters()}

    # Catégorie "missions" à part : filtrage par mots-clés d'un flux
    # généraliste, pas une simple agrégation presse -> exclue des analyses
    # sociétés mentionnées / signaux d'investissement ci-dessous.
    news_categories = dict(categories)
    categories["missions"] = {"label": LABELS["missions"], "items": fetch_missions()}

    crypto_prices = fetch_crypto_prices()
    market_indices = fetch_market_indices()
    mentioned_companies = detect_mentioned_companies(news_categories)

    payload = {
        "weekday": weekday_name,
        "generated_at": now.isoformat(),
        "categories": categories,
        "crypto_prices": crypto_prices,
        "market_indices": market_indices,
        "mentioned_companies": mentioned_companies,
        "investissement": build_investment_notes(news_categories),
    }

    out_path = DATA_DIR / f"{weekday_name}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] écrit {out_path} ({sum(len(c['items']) for c in categories.values())} signaux)")


if __name__ == "__main__":
    main()
