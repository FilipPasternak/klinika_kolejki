import math
import random

from simulation.engine import SimulationEngine


def regression_test_immediate_service_start():
    """Ensure an arriving patient immediately enters service if a server is idle."""

    random.seed(12345)
    engine = SimulationEngine()
    engine.set_params(arrival_rate_lambda=3.0, service_rate_mu=4.0, servers_c=1)
    engine.start()

    first_arrival_time = engine._next_arrival_time
    assert first_arrival_time is not None

    engine.step(first_arrival_time)

    patient = engine._patients[1]
    assert patient.service_start_time is not None
    assert math.isclose(patient.service_start_time, patient.arrival_time)

if __name__ == "__main__":
    regression_test_immediate_service_start()

    engine = SimulationEngine()
    engine.set_params(arrival_rate_lambda=6.0, service_rate_mu=4.0, servers_c=2)
    engine.start()

    total_sim = 2.0  # hours
    step = 0.1
    t = 0.0
    while t < total_sim:
        engine.step(step)
        t += step

    snap = engine.get_snapshot()
    print("Sim time:", snap.sim_time)
    print("Queue (patient IDs):", snap.queue)
    print("In service:", snap.in_service)
    print("Metrics:", snap.metrics)
