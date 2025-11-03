import pytest

from simulation.engine import SimulationEngine
from simulation.metrics import erlang_c_metrics


@pytest.mark.parametrize(
    "lam, mu, c, expected",
    [
        (5.0, 3.0, 3, {"P0": 0.17266187050359708, "Lq": 0.37470023980815353, "Wq": 0.0749400479616307, "W": 0.40827338129496404, "L": 2.04136690647482}),
        (9.9, 5.0, 2, {"P0": 0.005025125628140686, "Lq": 97.51748743718586, "Wq": 9.8502512562814, "W": 10.050251256281399, "L": 99.49748743718585}),
    ],
)
def test_erlang_c_metrics_stable_cases(lam, mu, c, expected):
    metrics = erlang_c_metrics(lam, mu, c)
    assert metrics["rho"] == pytest.approx(lam / (c * mu))
    assert metrics["P0"] == pytest.approx(expected["P0"], rel=1e-12, abs=1e-12)
    assert metrics["Lq"] == pytest.approx(expected["Lq"], rel=1e-9)
    assert metrics["Wq"] == pytest.approx(expected["Wq"], rel=1e-9)
    assert metrics["W"] == pytest.approx(expected["W"], rel=1e-9)
    assert metrics["L"] == pytest.approx(expected["L"], rel=1e-9)
    assert metrics["Pw"] == pytest.approx(metrics["Lq"] * (1 - metrics["rho"]) / metrics["rho"] if metrics["rho"] > 0 else 0.0, rel=1e-9)


def test_erlang_c_metrics_zero_arrivals():
    metrics = erlang_c_metrics(0.0, 4.0, 3)
    assert metrics == {
        "rho": 0.0,
        "P0": 1.0,
        "Pw": 0.0,
        "Lq": 0.0,
        "Wq": 0.0,
        "W": pytest.approx(0.25),
        "L": 0.0,
    }


def test_erlang_c_metrics_unstable_and_invalid():
    unstable = erlang_c_metrics(10.0, 5.0, 2)
    assert unstable["rho"] == pytest.approx(1.0)
    for key in ("P0", "Pw", "Lq", "Wq", "W", "L"):
        assert unstable[key] is None

    invalid = erlang_c_metrics(-1.0, 5.0, 2)
    for key in ("rho", "P0", "Pw", "Lq", "Wq", "W", "L"):
        assert invalid[key] is None

    invalid_mu = erlang_c_metrics(5.0, 0.0, 2)
    for key in ("rho", "P0", "Pw", "Lq", "Wq", "W", "L"):
        assert invalid_mu[key] is None

    invalid_servers = erlang_c_metrics(5.0, 5.0, 0)
    for key in ("rho", "P0", "Pw", "Lq", "Wq", "W", "L"):
        assert invalid_servers[key] is None


def test_engine_snapshot_exposes_theoretical_metrics():
    engine = SimulationEngine()
    engine.set_params(5.0, 3.0, 3)
    engine.start()

    snapshot = engine.get_snapshot()
    theoretical = snapshot.metrics["theoretical"]
    empirical = snapshot.metrics["empirical"]

    assert theoretical["Wq"] == pytest.approx(0.0749400479616307, rel=1e-9)
    assert empirical["rho"] == pytest.approx(5.0 / (3 * 3))
