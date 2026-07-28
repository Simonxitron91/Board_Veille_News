#!/usr/bin/env python3
"""
Récupère des flux RSS publics, les classe par catégorie, et écrit
data/<jour_de_la_semaine>.json pour alimenter le board.

Sources modifiables ci-dessous (FEEDS). Un flux cassé est ignoré
silencieusement (best effort) pour ne jamais faire échouer le run entier.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# --- Sources par catégorie -------------------------------------------------
# Ajoute / retire des flux librement. Format: (nom_source, url_rss)
FEEDS = {
    "ia": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
        ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ],
    "cyber": [
        ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
        ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
        ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ],
    "economie": [
        ("Les Echos", "https://www.lesechos.fr/rss/rss_une.xml"),
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
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
    ],
}

LABELS = {
    "ia": "Intelligence Artificielle",
    "cyber": "Cybersécurité",
    "economie": "Économie & Marchés",
    "geopolitique": "Géopolitique & Général",
    "science": "Science",
    "politique": "Politique",
}

MAX_ITEMS_PER_FEED = 4


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
                "inflation", "pétrole", "ransomware", "cyberattaque"]
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

    payload = {
        "weekday": weekday_name,
        "generated_at": now.isoformat(),
        "categories": categories,
        "investissement": build_investment_notes(categories),
    }

    out_path = DATA_DIR / f"{weekday_name}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] écrit {out_path} ({sum(len(c['items']) for c in categories.values())} signaux)")


if __name__ == "__main__":
    main()
