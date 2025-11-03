"""Analytical queueing theory helpers."""

from __future__ import annotations

import math
from typing import Dict, Optional


def _empty_metrics(rho: Optional[float] = None) -> Dict[str, Optional[float]]:
    return {
        "rho": rho,
        "P0": None,
        "Pw": None,
        "Lq": None,
        "Wq": None,
        "W": None,
        "L": None,
    }


def erlang_c_metrics(lambda_rate: float, mu_rate: float, servers_c: int) -> Dict[str, Optional[float]]:
    r"""Return closed-form M/M/c (Erlang C) metrics.

    The returned dictionary contains:

    ``rho`` Traffic intensity per server (:math:`\rho = \lambda/(c\mu)`).
    ``P0``  Probability of zero patients in system.
    ``Pw``  Probability that an arrival waits (i.e. all servers busy).
    ``Lq``  Expected queue length.
    ``Wq``  Expected queueing delay.
    ``W``   Expected time in system.
    ``L``   Expected number of patients in system.

    ``None`` is returned for the analytical values when the system is
    unstable (:math:`\rho \ge 1`) or the parameters are invalid.
    """

    # Validate inputs first. All parameters must be finite real numbers.
    if (
        not isinstance(servers_c, int)
        or servers_c <= 0
        or not math.isfinite(lambda_rate)
        or not math.isfinite(mu_rate)
        or mu_rate <= 0
        or lambda_rate < 0
    ):
        return _empty_metrics()

    if lambda_rate == 0:
        rho = 0.0
        base = _empty_metrics(rho)
        base.update({
            "P0": 1.0,
            "Pw": 0.0,
            "Lq": 0.0,
            "Wq": 0.0,
            "W": 1.0 / mu_rate,
            "L": 0.0,
        })
        return base

    rho = lambda_rate / (servers_c * mu_rate)
    if rho >= 1.0:
        return _empty_metrics(rho)

    offered_load = lambda_rate / mu_rate  # a = λ / μ

    # Compute the normalisation constant P0 denominator.
    term = 1.0
    partial_sum = 1.0  # includes n = 0 term
    for n in range(1, servers_c):
        term *= offered_load / n
        partial_sum += term

    term_c = term * (offered_load / servers_c)
    denom_tail_factor = (servers_c * mu_rate) / (servers_c * mu_rate - lambda_rate)
    denominator = partial_sum + term_c * denom_tail_factor

    if denominator == 0:
        return _empty_metrics(rho)

    P0 = 1.0 / denominator
    Pw = term_c * denom_tail_factor * P0

    Lq = Pw * rho / (1.0 - rho)
    Wq = Lq / lambda_rate
    W = Wq + 1.0 / mu_rate
    L = lambda_rate * W

    return {
        "rho": rho,
        "P0": P0,
        "Pw": Pw,
        "Lq": Lq,
        "Wq": Wq,
        "W": W,
        "L": L,
    }
