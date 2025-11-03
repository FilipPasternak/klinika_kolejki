"""
Analytical + empirical metrics helpers.

Placeholder for Erlang C / M/M/c closed-form expressions.
"""
import math

def erlang_c_metrics(lambda_rate: float, mu_rate: float, servers_c: int):
    """Return dict with rho, Wq, W, Lq, L for M/M/c if stable, else None values.
    This is a stub; closed-form computation to be added later.
    """
    if servers_c <= 0 or mu_rate <= 0:
        return {"rho": None, "Wq": None, "W": None, "Lq": None, "L": None}

    rho = lambda_rate / (servers_c * mu_rate)
    if rho >= 1.0:
        return {"rho": rho, "Wq": None, "W": None, "Lq": None, "L": None}

    # TODO: add actual Erlang C formula here
    return {"rho": rho, "Wq": None, "W": None, "Lq": None, "L": None}
