"""
producer.py — Hilo productor
Carga las URLs en la cola compartida y emite señales de terminación.

Concepto de concurrencia aplicado:
  - Modelo Producer-Consumer
  - queue.Queue es thread-safe por diseño (usa un Lock interno)
  - Las señales None (poison pills) permiten terminar workers limpiamente
"""

import queue
import threading
import logging
from urls import ALL_URLS

logger = logging.getLogger(__name__)


class URLProducer(threading.Thread):
    """
    Hilo productor: encola todas las URLs y envía una 'poison pill'
    por cada worker para señalar el fin de trabajo.
    """

    def __init__(self, url_queue: queue.Queue, num_workers: int):
        super().__init__(name="Producer", daemon=True)
        self.url_queue = url_queue
        self.num_workers = num_workers

    def run(self):
        logger.info(f"[Producer] Encolando {len(ALL_URLS)} URLs...")

        for url in ALL_URLS:
            self.url_queue.put(url)
            logger.debug(f"[Producer] Encolada: {url}")

        # Poison pills: una por worker para que cada uno sepa cuándo parar
        for _ in range(self.num_workers):
            self.url_queue.put(None)

        logger.info("[Producer] Todas las URLs encoladas. Poison pills enviadas.")
