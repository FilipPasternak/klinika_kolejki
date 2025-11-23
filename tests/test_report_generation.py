import json
from pathlib import Path

import matplotlib
import numpy as np

from simulation.metrics import erlang_c_metrics

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (deferred backend selection)


def _collect_metrics_for_lambdas(lambdas, mu, servers):
    data = []
    for lam in lambdas:
        metrics = erlang_c_metrics(lam, mu, servers)
        if metrics["Wq"] is None:
            continue
        data.append({"lambda": lam, **metrics})
    return data


def _collect_pw_heatmap(lambdas, servers_list, mu):
    heatmap = np.zeros((len(servers_list), len(lambdas))) * np.nan
    for i, servers in enumerate(servers_list):
        for j, lam in enumerate(lambdas):
            metrics = erlang_c_metrics(lam, mu, servers)
            heatmap[i, j] = metrics["Pw"] if metrics["Pw"] is not None else np.nan
    return heatmap


def test_generate_queueing_report(tmp_path: Path):
    """Generate a visual report with classical queueing dependencies.

    The test builds four plots commonly inspected in M/M/c systems:
    - Waiting time (Wq) vs. arrival rate (lambda) for a fixed server pool.
    - Queue length (Lq) vs. arrival rate (lambda).
    - Probability of waiting (Pw) heatmap across arrival rates and server counts.
    - Time in system (W) as the number of servers changes for a fixed load.

    The resulting figure and JSON summary allow quick inspection of stability
    regions and how utilization drives queue growth. The test asserts that the
    artifacts are produced with non-zero size to catch regressions in the
    reporting workflow.
    """

    mu = 4.0
    servers = 3
    lambda_values = np.linspace(1.0, 10.5, 12)

    data = _collect_metrics_for_lambdas(lambda_values, mu, servers)
    assert data, "No stable points collected for lambda sweep"

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    axes[0, 0].plot([row["lambda"] for row in data], [row["Wq"] for row in data], marker="o")
    axes[0, 0].set_title("Oczekiwanie w kolejce vs. natężenie przyjazdów")
    axes[0, 0].set_xlabel("λ [pacjenci/h]")
    axes[0, 0].set_ylabel("Wq [h]")

    axes[0, 1].plot([row["lambda"] for row in data], [row["Lq"] for row in data], marker="s", color="darkorange")
    axes[0, 1].set_title("Średnia długość kolejki vs. λ")
    axes[0, 1].set_xlabel("λ [pacjenci/h]")
    axes[0, 1].set_ylabel("Lq [liczba pacjentów]")

    server_choices = [1, 2, 3, 4]
    heatmap = _collect_pw_heatmap(lambda_values, server_choices, mu)
    heatmap_plot = axes[1, 0].imshow(heatmap, aspect="auto", origin="lower", extent=[lambda_values[0], lambda_values[-1], server_choices[0], server_choices[-1]])
    axes[1, 0].set_title("Prawdopodobieństwo oczekiwania Pw")
    axes[1, 0].set_xlabel("λ [pacjenci/h]")
    axes[1, 0].set_ylabel("Liczba serwerów")
    fig.colorbar(heatmap_plot, ax=axes[1, 0], label="Pw")

    lambda_fixed = 8.0
    w_per_servers = []
    for c in server_choices:
        metrics = erlang_c_metrics(lambda_fixed, mu, c)
        if metrics["W"] is not None:
            w_per_servers.append((c, metrics["W"]))
    axes[1, 1].plot([c for c, _ in w_per_servers], [w for _, w in w_per_servers], marker="^", color="seagreen")
    axes[1, 1].set_title("Czas w systemie vs. liczba serwerów")
    axes[1, 1].set_xlabel("Serwery c")
    axes[1, 1].set_ylabel("W [h]")

    plt.tight_layout()

    report_path = tmp_path / "queueing_report.png"
    fig.savefig(report_path, dpi=150)
    assert report_path.exists() and report_path.stat().st_size > 0

    summary = {
        "mu": mu,
        "server_pool": servers,
        "lambda_values": list(lambda_values),
        "stable_points": data,
        "servers_vs_W": w_per_servers,
    }

    summary_path = tmp_path / "queueing_report_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    assert summary_path.exists() and summary_path.stat().st_size > 0
