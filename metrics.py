"""
metrics.py — Cálculo y visualización de métricas de rendimiento

Métricas implementadas:
  - Tiempo total de ejecución
  - Speedup (Ley de Amdahl en la práctica)
  - Eficiencia paralela
  - Throughput (URLs por segundo)
  - Tasa de éxito
"""

import json
import time
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
import matplotlib
matplotlib.use("Agg")          # Sin GUI, genera archivo PNG
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

logger = logging.getLogger(__name__)
RESULTS_DIR = "results"


# ── Estructura de métricas ────────────────────────────────────────────────────

@dataclass
class RunMetrics:
    mode: str                       # "sequential" | "parallel"
    num_workers: int
    total_urls: int
    successful: int
    failed: int
    total_time_s: float
    throughput_urls_s: float = 0.0  # URLs procesadas por segundo
    speedup: float = 1.0            # relativo a la versión secuencial
    efficiency: float = 1.0         # speedup / num_workers
    per_site: list = field(default_factory=list)

    def compute_derived(self, sequential_time: Optional[float] = None):
        """Calcula throughput, speedup y eficiencia."""
        self.throughput_urls_s = round(self.total_urls / self.total_time_s, 3)
        if sequential_time and self.mode == "parallel":
            self.speedup    = round(sequential_time / self.total_time_s, 2)
            self.efficiency = round(self.speedup / self.num_workers, 3)

    def print_summary(self):
        print("\n" + "═" * 52)
        print(f"  MODO          : {self.mode.upper()}")
        print(f"  Workers       : {self.num_workers}")
        print(f"  URLs totales  : {self.total_urls}")
        print(f"  Exitosas      : {self.successful}  ✓")
        print(f"  Fallidas      : {self.failed}  ✗")
        print(f"  Tiempo total  : {self.total_time_s:.2f} s")
        print(f"  Throughput    : {self.throughput_urls_s} URLs/s")
        if self.mode == "parallel":
            print(f"  Speedup       : {self.speedup}×")
            print(f"  Eficiencia    : {self.efficiency * 100:.1f}%")
        print("═" * 52 + "\n")


# ── Guardado de resultados ────────────────────────────────────────────────────

def save_results(results: dict, metrics: RunMetrics):
    """Guarda titulares y métricas en JSON."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    fname = f"{RESULTS_DIR}/results_{metrics.mode}.json"

    payload = {
        "metrics": asdict(metrics),
        "articles": list(results.values()),
    }
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(f"Resultados guardados en {fname}")
    return fname


# ── Gráficas ──────────────────────────────────────────────────────────────────

def plot_speedup(seq_time: float, parallel_times: dict[int, float]):
    """
    Genera gráfica de Speedup vs Número de Workers.
    parallel_times: {num_workers: tiempo_en_segundos}
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    workers = sorted(parallel_times.keys())
    speedups = [round(seq_time / parallel_times[w], 2) for w in workers]
    ideal    = workers  # speedup ideal = N workers

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(workers, ideal,   "--", color="#AAAAAA", label="Speedup ideal")
    ax.plot(workers, speedups, "o-", color="#1D9E75", linewidth=2,
            markersize=7, label="Speedup real")

    for w, s in zip(workers, speedups):
        ax.annotate(f"{s}×", (w, s), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9)

    ax.set_xlabel("Número de workers (hilos)")
    ax.set_ylabel("Speedup (T_sec / T_par)")
    ax.set_title("Speedup real vs ideal — ParallelNews Scraper")
    ax.legend()
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    path = f"{RESULTS_DIR}/speedup.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Gráfica guardada en {path}")
    return path


def plot_per_site(results: dict):
    """Tiempo de respuesta por sitio (barras horizontales)."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    items = sorted(results.values(), key=lambda r: r["duration_s"], reverse=True)
    sites  = [r["site"] for r in items]
    times  = [r["duration_s"] for r in items]
    colors = ["#E24B4A" if r["error"] else "#1D9E75" for r in items]

    fig, ax = plt.subplots(figsize=(9, max(4, len(sites) * 0.5)))
    bars = ax.barh(sites, times, color=colors, height=0.6)
    ax.set_xlabel("Tiempo de respuesta (s)")
    ax.set_title("Tiempo por sitio — verde = éxito, rojo = error")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(5))
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()

    path = f"{RESULTS_DIR}/per_site.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Gráfica por sitio guardada en {path}")
    return path


# ── Cronómetro de contexto ────────────────────────────────────────────────────

class Timer:
    """Uso: with Timer() as t: ...; print(t.elapsed)"""
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, *_):
        self.elapsed = round(time.perf_counter() - self._start, 3)
