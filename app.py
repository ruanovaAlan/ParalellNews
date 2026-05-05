"""
app.py — Servidor web Flask para ParallelNews Scraper
"""

import json
import os
import queue
import threading
import logging

from flask import Flask, render_template, jsonify, send_from_directory

from urls import ALL_URLS, SOURCES
from producer import URLProducer
from worker import WorkerThread, parse_feed
from metrics import RunMetrics, Timer, save_results, plot_speedup, plot_per_site

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(threadName)s] %(message)s")
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
NUM_WORKERS = 6


def run_parallel(num_workers=NUM_WORKERS, max_concurrent=5):
    url_queue = queue.Queue()
    results   = {}
    lock      = threading.Lock()
    semaphore = threading.Semaphore(max_concurrent)

    producer = URLProducer(url_queue, num_workers)
    workers  = [WorkerThread(url_queue, results, lock, semaphore, i+1) for i in range(num_workers)]

    with Timer() as t:
        producer.start()
        for w in workers: w.start()
        for w in workers: w.join()

    successful = sum(1 for r in results.values() if not r["error"])
    metrics = RunMetrics(
        mode="parallel", num_workers=num_workers,
        total_urls=len(ALL_URLS), successful=successful,
        failed=len(ALL_URLS) - successful, total_time_s=t.elapsed,
        per_site=[{"site": r["site"], "time": r["duration_s"], "error": r["error"]}
                  for r in results.values()],
    )
    metrics.compute_derived()
    return results, metrics


def run_sequential():
    results = {}
    with Timer() as t:
        for url in ALL_URLS:
            results[url] = parse_feed(url)

    successful = sum(1 for r in results.values() if not r["error"])
    metrics = RunMetrics(
        mode="sequential", num_workers=1,
        total_urls=len(ALL_URLS), successful=successful,
        failed=len(ALL_URLS) - successful, total_time_s=t.elapsed,
        per_site=[{"site": r["site"], "time": r["duration_s"], "error": r["error"]}
                  for r in results.values()],
    )
    metrics.compute_derived()
    return results, metrics


@app.route("/")
def index():
    return render_template("index.html", feeds=len(SOURCES), workers=NUM_WORKERS)


@app.route("/benchmark")
def benchmark_page():
    return render_template("benchmark.html")


@app.route("/api/scrape")
def api_scrape():
    results, metrics = run_parallel(num_workers=NUM_WORKERS)
    save_results(results, metrics)

    articles = []
    for r in results.values():
        for i, title in enumerate(r["headlines"]):
            articles.append({
                "site":      r["site"],
                "lang":      r["lang"],
                "title":     title,
                "link":      r["links"][i] if i < len(r["links"]) else "#",
                "published": r["published"][i] if i < len(r["published"]) else "",
                "thread":    r["thread"],
            })

    return jsonify({
        "articles": articles,
        "metrics": {
            "total_urls":  metrics.total_urls,
            "successful":  metrics.successful,
            "failed":      metrics.failed,
            "total_time_s": metrics.total_time_s,
            "throughput":  metrics.throughput_urls_s,
            "num_workers": metrics.num_workers,
        }
    })


@app.route("/api/benchmark")
def api_benchmark():
    _, seq = run_sequential()
    seq.compute_derived()

    parallel_data = []
    for n in [2, 4, 6, 8]:
        _, par = run_parallel(num_workers=n)
        par.compute_derived(sequential_time=seq.total_time_s)
        parallel_data.append({
            "workers":    n,
            "time_s":     par.total_time_s,
            "speedup":    par.speedup,
            "efficiency": round(par.efficiency * 100, 1),
            "throughput": par.throughput_urls_s,
            "successful": par.successful,
            "failed":     par.failed,
        })

    os.makedirs(RESULTS_DIR, exist_ok=True)
    plot_speedup(seq.total_time_s, {d["workers"]: d["time_s"] for d in parallel_data})
    last_results, _ = run_parallel(num_workers=NUM_WORKERS)
    plot_per_site(last_results)

    return jsonify({"sequential": {
        "time_s": seq.total_time_s, "throughput": seq.throughput_urls_s,
        "successful": seq.successful, "failed": seq.failed,
    }, "parallel": parallel_data})


# Servir PNGs generados por matplotlib
@app.route("/results/<path:filename>")
def serve_results(filename):
    return send_from_directory(RESULTS_DIR, filename)


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    app.run(debug=True, port=5000)