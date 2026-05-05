"""
urls.py — Feeds RSS de noticias tech/IA

Incluye feeds con XML bien formado y algunos con XML imperfecto
(Xataka, Hipertextual) para demostrar tolerancia a fallos en el analisis.
"""

SOURCES = [
    # ── Espanol — feeds con XML imperfecto (util para analisis de fallos) ──
    {
        "site": "Xataka",
        "url": "https://www.xataka.com/tag/inteligencia-artificial.xml",
        "lang": "es",
        "note": "XML malformado — namespace sin declarar",
    },
    {
        "site": "Hipertextual",
        "url": "https://hipertextual.com/tag/inteligencia-artificial/feed",
        "lang": "es",
        "note": "XML malformado — mismatched tag",
    },

    # ── Espanol — feeds confiables ─────────────────────────────────────────
    {
        "site": "El Pais Tecnologia",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada",
        "lang": "es",
    },
    {
        "site": "BBC Mundo Tecnologia",
        "url": "https://feeds.bbci.co.uk/mundo/rss.xml",
        "lang": "es",
    },

    # ── Ingles ─────────────────────────────────────────────────────────────
    {
        "site": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "lang": "en",
    },
    {
        "site": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "lang": "en",
    },
    {
        "site": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "lang": "en",
    },
    {
        "site": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "lang": "en",
    },
    {
        "site": "Wired AI",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "lang": "en",
    },
    {
        "site": "MIT Tech Review",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "lang": "en",
    },
    {
        "site": "MarkTechPost",
        "url": "https://www.marktechpost.com/feed/",
        "lang": "en",
    },
    {
        "site": "TNW Neural",
        "url": "https://thenextweb.com/neural/feed/",
        "lang": "en",
    },
]

ALL_URLS = [s["url"] for s in SOURCES]
URL_META = {s["url"]: s for s in SOURCES}