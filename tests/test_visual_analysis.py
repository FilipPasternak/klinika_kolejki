"""Richer analytical and empirical visualisations for the queueing model."""

import json
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from simulation.engine import SimulationEngine
from simulation.metrics import erlang_c_metrics

OUTPUT_DIR = Path(__file__).parent / "artifacts"
OUTPUT_DIR.mkdir(exist_ok=True)


def _save(fig, name: str):
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=150)
    plt.close(fig)
    assert path.exists() and path.stat().st_size > 0
    return path


def test_wait_and_queue_vs_lambda_curve():
    mu = 4.0
    servers = 3
    lambdas = np.linspace(1.0, 10.0, 25)

    stable_rows = []
    for lam in lambdas:
        metrics = erlang_c_metrics(lam, mu, servers)
        if metrics["Wq"] is not None:
            stable_rows.append((lam, metrics["Wq"], metrics["W"]))

    assert len(stable_rows) >= 5, "Zbyt mało stabilnych punktów do wykresu"

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([row[0] for row in stable_rows], [row[1] for row in stable_rows], label="Wq", marker="o")
    ax.plot([row[0] for row in stable_rows], [row[2] for row in stable_rows], label="W", marker="s")
    ax.set_title("Czas oczekiwania i przebywania w systemie vs. natężenie przyjazdów")
    ax.set_xlabel("λ [pacjenci/h]")
    ax.set_ylabel("Czas [h]")
    ax.legend()

    _save(fig, "wait_vs_lambda.png")


def test_queue_length_vs_service_rate_curve():
    lam = 6.0
    servers = 3
    mu_values = np.linspace(3.5, 10.0, 30)

    rows = []
    for mu in mu_values:
        metrics = erlang_c_metrics(lam, mu, servers)
        if metrics["Lq"] is not None:
            rows.append((mu, metrics["Lq"]))

    assert len(rows) >= 10, "Brak wystarczającej liczby stabilnych punktów do krzywej"

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([row[0] for row in rows], [row[1] for row in rows], marker="^", color="tab:orange")
    ax.set_title("Średnia długość kolejki vs. wydajność serwisowania")
    ax.set_xlabel("μ [pacjenci/h/serwer]")
    ax.set_ylabel("Lq [pacjenci]")

    _save(fig, "queue_length_vs_mu.png")


def test_servers_vs_wait_and_utilisation():
    lam = 9.0
    mu = 5.0
    servers_range = range(1, 7)

    rows = []
    for c in servers_range:
        metrics = erlang_c_metrics(lam, mu, c)
        rows.append((c, metrics["rho"], metrics["W"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    ax1.plot([row[0] for row in rows], [row[1] for row in rows], marker="o")
    ax1.axhline(1.0, color="red", linestyle="--", label="granica stabilności")
    ax1.set_title("Wykorzystanie ρ vs. liczba serwerów")
    ax1.set_xlabel("c")
    ax1.set_ylabel("ρ")
    ax1.legend()

    ax2.plot([row[0] for row in rows if row[2] is not None], [row[2] for row in rows if row[2] is not None], marker="s")
    ax2.set_title("Czas w systemie W vs. c")
    ax2.set_xlabel("c")
    ax2.set_ylabel("W [h]")

    _save(fig, "servers_vs_wait_and_rho.png")


def test_probability_of_waiting_heatmap():
    mu = 4.0
    lambdas = np.linspace(1.0, 12.0, 25)
    servers_list = [1, 2, 3, 4, 5]

    heatmap = np.zeros((len(servers_list), len(lambdas))) * np.nan
    for i, servers in enumerate(servers_list):
        for j, lam in enumerate(lambdas):
            metrics = erlang_c_metrics(lam, mu, servers)
            heatmap[i, j] = metrics["Pw"] if metrics["Pw"] is not None else np.nan

    fig, ax = plt.subplots(figsize=(10, 4))
    cax = ax.imshow(
        heatmap,
        aspect="auto",
        origin="lower",
        extent=[lambdas[0], lambdas[-1], servers_list[0], servers_list[-1]],
        cmap="magma",
    )
    ax.set_title("Prawdopodobieństwo oczekiwania Pw (λ vs. liczba serwerów)")
    ax.set_xlabel("λ [pacjenci/h]")
    ax.set_ylabel("Serwery c")
    fig.colorbar(cax, ax=ax, label="Pw")

    _save(fig, "pw_heatmap.png")


def test_stability_region_for_lambda_mu_grid():
    servers = 3
    lambdas = np.linspace(1.0, 12.0, 30)
    mu_values = np.linspace(2.0, 8.0, 30)

    stability = np.zeros((len(mu_values), len(lambdas)))
    for i, mu in enumerate(mu_values):
        for j, lam in enumerate(lambdas):
            metrics = erlang_c_metrics(lam, mu, servers)
            stability[i, j] = 1 if metrics["rho"] is not None and metrics["rho"] < 1 else 0

    fig, ax = plt.subplots(figsize=(8, 5))
    cax = ax.imshow(
        stability,
        aspect="auto",
        origin="lower",
        extent=[lambdas[0], lambdas[-1], mu_values[0], mu_values[-1]],
        cmap="Greens",
    )
    ax.set_title("Strefa stabilności ρ < 1 dla siatki λ i μ (c=3)")
    ax.set_xlabel("λ [pacjenci/h]")
    ax.set_ylabel("μ [pacjenci/h/serwer]")
    fig.colorbar(cax, ax=ax, ticks=[0, 1], label="Stabilna = 1")

    _save(fig, "stability_region.png")


def _run_engine_until(metrics_probability: float) -> dict:
    random.seed(2024)
    engine = SimulationEngine()
    engine.set_params(arrival_rate_lambda=6.0, service_rate_mu=5.0, servers_c=3)
    engine.set_priority_probability(metrics_probability)
    engine.start()

    sim_horizon = 6.0
    step = 0.1
    steps = int(sim_horizon / step)
    for _ in range(steps):
        engine.step(step)

    return engine.get_snapshot().metrics["empirical"]


def test_priority_probability_effect_on_waiting_times():
    probabilities = np.linspace(0.0, 0.9, 6)

    empirical_rows = []
    for prob in probabilities:
        metrics = _run_engine_until(prob)
        if metrics["Wq"] is not None and metrics["W"] is not None:
            empirical_rows.append((prob, metrics["Wq"], metrics["W"]))

    assert len(empirical_rows) >= 4, "Symulacja nie ukończyła wystarczającej liczby pacjentów"

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([row[0] for row in empirical_rows], [row[1] for row in empirical_rows], marker="o", label="Wq")
    ax.plot([row[0] for row in empirical_rows], [row[2] for row in empirical_rows], marker="s", label="W")
    ax.set_title("Wpływ priorytetów na czasy oczekiwania (empiryczne)")
    ax.set_xlabel("Prawdopodobieństwo priorytetu")
    ax.set_ylabel("Czas [h]")
    ax.legend()

    path = _save(fig, "priority_effect.png")
    summary_path = OUTPUT_DIR / "priority_effect.json"
    summary_path.write_text(json.dumps({"rows": empirical_rows}, indent=2), encoding="utf-8")
    assert summary_path.exists() and summary_path.stat().st_size > 0
