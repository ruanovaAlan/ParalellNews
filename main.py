"""
main.py — Punto de entrada del ParallelNews Scraper

Uso:
  python main.py --mode sequential
  python main.py --mode parallel --workers 4
  python main.py --mode benchmark   # corre ambos y genera gráficas
"""

import argparse
import logging
import queue
import threading
from urls import ALL_URLS
from producer import URLProducer
from worker import WorkerThread, parse_feed
from metrics import RunMetrics, Timer, save_results, plot_speedup, plot_per_site

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Modo secuencial ───────────────────────────────────────────────────────────

def run_sequential() -> tuple[dict, RunMetrics]:
    """
    Versión de referencia: procesa cada URL una por una en el hilo principal.
    Sin hilos, sin locks, sin colas. Sirve como baseline de tiempo.
    """
    logger.info("══ MODO SECUENCIAL ══")
    results = {}

    with Timer() as t:
        for url in ALL_URLS:
            result = parse_feed(url)
            results[url] = result

    successful = sum(1 for r in results.values() if not r["error"])
    metrics = RunMetrics(
        mode="sequential",
        num_workers=1,
        total_urls=len(ALL_URLS),
        successful=successful,
        failed=len(ALL_URLS) - successful,
        total_time_s=t.elapsed,
        per_site=[{"site": r["site"], "time": r["duration_s"]} for r in results.values()],
    )
    metrics.compute_derived()
    return results, metrics


# ── Modo paralelo ─────────────────────────────────────────────────────────────

def run_parallel(num_workers: int, max_concurrent: int = 5) -> tuple[dict, RunMetrics]:
    """
    Versión paralela con:
      - URLProducer (hilo productor)
      - N WorkerThreads (hilos consumidores)
      - queue.Queue como canal de comunicación
      - threading.Lock para proteger el dict de resultados
      - threading.Semaphore para limitar conexiones simultáneas
    """
    logger.info(f"══ MODO PARALELO — {num_workers} workers ══")

    url_queue = queue.Queue()
    results   = {}                                    # recurso compartido
    lock      = threading.Lock()                      # protege `results`
    semaphore = threading.Semaphore(max_concurrent)   # limita conexiones HTTP

    # Crear producer y workers
    producer = URLProducer(url_queue, num_workers)
    workers  = [
        WorkerThread(url_queue, results, lock, semaphore, i + 1)
        for i in range(num_workers)
    ]

    with Timer() as t:
        producer.start()
        for w in workers:
            w.start()

        # Esperar a que todos los workers terminen
        for w in workers:
            w.join()

    successful = sum(1 for r in results.values() if not r["error"])
    metrics = RunMetrics(
        mode="parallel",
        num_workers=num_workers,
        total_urls=len(ALL_URLS),
        successful=successful,
        failed=len(ALL_URLS) - successful,
        total_time_s=t.elapsed,
        per_site=[{"site": r["site"], "time": r["duration_s"]} for r in results.values()],
    )
    metrics.compute_derived()
    return results, metrics


# ── Modo benchmark ────────────────────────────────────────────────────────────

def run_benchmark():
    """
    Corre secuencial + paralelo con 2, 4, 8 workers.
    Genera gráficas de speedup y tiempos por sitio.
    """
    logger.info("══ BENCHMARK COMPLETO ══")

    # 1. Secuencial (baseline)
    seq_results, seq_metrics = run_sequential()
    seq_metrics.print_summary()
    save_results(seq_results, seq_metrics)
    plot_per_site(seq_results)

    # 2. Paralelo con distintos números de workers
    parallel_times = {}
    for n in [2, 4, 6, 8]:
        par_results, par_metrics = run_parallel(num_workers=n)
        par_metrics.compute_derived(sequential_time=seq_metrics.total_time_s)
        par_metrics.print_summary()
        save_results(par_results, par_metrics)
        parallel_times[n] = par_metrics.total_time_s

    # 3. Gráfica de speedup
    plot_speedup(seq_metrics.total_time_s, parallel_times)
    print("\n✓ Benchmark completo. Resultados en ./results/")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ParallelNews Tech/AI Scraper")
    parser.add_argument("--mode", choices=["sequential", "parallel", "benchmark"],
                        default="benchmark", help="Modo de ejecución")
    parser.add_argument("--workers", type=int, default=4,
                        help="Número de hilos worker (solo en modo parallel)")
    args = parser.parse_args()

    if args.mode == "sequential":
        results, metrics = run_sequential()
        metrics.print_summary()
        save_results(results, metrics)

    elif args.mode == "parallel":
        results, metrics = run_parallel(args.workers)
        metrics.compute_derived()
        metrics.print_summary()
        save_results(results, metrics)

    elif args.mode == "benchmark":
        run_benchmark()


if __name__ == "__main__":
    main()