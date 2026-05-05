"""
worker.py — Hilos consumidores con parsing de RSS

Conceptos de concurrencia aplicados:
  - threading.Thread (multihilo)
  - threading.Semaphore (limitar conexiones simultaneas)
  - threading.Lock (proteger el dict de resultados compartido)
  - queue.Queue como canal de comunicacion con el producer
"""

import socket
import threading
import logging
import time
import feedparser
from urls import URL_META

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
MAX_ITEMS = 8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TechAI-RSSReader/2.0)",
}


def parse_feed(url: str) -> dict:
    """
    Descarga y parsea un feed RSS/Atom.
    feedparser maneja ambos formatos automaticamente.

    Nota sobre bozo:
      feedparser marca bozo=True cuando el XML tiene errores (como Xataka o
      Hipertextual), pero aun asi intenta rescatar las entradas que pueda.
      Solo tratamos bozo como error fatal si no se recupero ninguna entrada.
    """
    meta = URL_META.get(url, {})
    site = meta.get("site", url)

    result = {
        "site": site,
        "url": url,
        "lang": meta.get("lang", "en"),
        "headlines": [],
        "links": [],
        "published": [],
        "error": None,
        "duration_s": 0.0,
        "thread": threading.current_thread().name,
        "total_items_in_feed": 0,
    }

    t0 = time.perf_counter()
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(REQUEST_TIMEOUT)
        feed = feedparser.parse(url, request_headers=HEADERS)
        socket.setdefaulttimeout(old_timeout)

        if feed.bozo:
            if feed.entries:
                # XML imperfecto pero hay entradas rescatadas — continuar
                logger.warning(
                    f"[{site}] XML imperfecto, pero se recuperaron "
                    f"{len(feed.entries)} entradas (bozo: {feed.bozo_exception})"
                )
            else:
                # Sin entradas = feed inutilizable
                raise ValueError(f"XML invalido sin entradas recuperables: {feed.bozo_exception}")

        result["total_items_in_feed"] = len(feed.entries)

        for entry in feed.entries[:MAX_ITEMS]:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "")
            pub   = entry.get("published", entry.get("updated", ""))
            if title:
                result["headlines"].append(title)
                result["links"].append(link)
                result["published"].append(pub)

        if not result["headlines"]:
            result["error"] = "Feed vacio o sin titulares"

    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"[{site}] Error: {e}")
    finally:
        result["duration_s"] = round(time.perf_counter() - t0, 3)

    return result


class WorkerThread(threading.Thread):
    """
    Hilo consumidor. Toma URLs de la cola y llama a parse_feed().
    - Semaphore: limita conexiones HTTP simultaneas
    - Lock: protege escrituras en el dict compartido de resultados
    """

    def __init__(self, url_queue, results, lock, semaphore, worker_id):
        super().__init__(name=f"Worker-{worker_id}", daemon=True)
        self.url_queue = url_queue
        self.results   = results
        self.lock      = lock
        self.semaphore = semaphore
        self.worker_id = worker_id

    def run(self):
        logger.info(f"[{self.name}] Iniciado")

        while True:
            url = self.url_queue.get()

            if url is None:
                logger.info(f"[{self.name}] Poison pill recibida. Terminando.")
                break

            with self.semaphore:
                logger.info(f"[{self.name}] Parseando feed -> {url}")
                result = parse_feed(url)

            with self.lock:
                self.results[url] = result

            status = (
                f"{len(result['headlines'])} titulares"
                if not result["error"]
                else f"ERROR: {result['error']}"
            )
            logger.info(
                f"[{self.name}] {result['site']} — {status} ({result['duration_s']}s)"
            )