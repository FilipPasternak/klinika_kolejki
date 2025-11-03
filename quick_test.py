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

    engine.step(first_arrival_time + 1e-6)

    assert len(engine._patients) == 1
    pid, patient = next(iter(engine._patients.items()))
    assert patient.service_start_time is not None
    assert math.isclose(patient.service_start_time, patient.arrival_time)


def regression_test_single_patient_system_time_matches_service_sample():
    """Validate that a solo patient's system time equals the sampled service duration."""

    seed = 20240215
    random.seed(seed)
    engine = SimulationEngine()
    engine.set_params(arrival_rate_lambda=0.5, service_rate_mu=4.0, servers_c=1)
    engine.start()

    # Reset to a clean zero-time state and manually enqueue a single patient.
    engine.sim_time = 0.0
    engine._patients.clear()
    engine._queue.clear()
    for srv in engine._servers:
        srv.busy = False
        srv.patient_id = None
        srv.time_remaining = 0.0

    engine._on_new_patient(0.0)
    engine._assign_waiting_patients()

    srv = engine._servers[0]
    assert srv.patient_id is not None
    pid = srv.patient_id
    service_sample = srv.time_remaining

    # Prevent further arrivals so only the seeded patient is processed.
    engine._next_arrival_time = None

    # Advance past the completion moment by a deliberate overshoot to exercise the correction path.
    engine.step(service_sample + 0.05)

    patient = engine._patients[pid]
    assert patient.service_end_time is not None
    expected_completion = patient.arrival_time + service_sample

    assert engine._served_patients == 1
    assert math.isclose(patient.service_end_time, expected_completion, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(engine._total_system_time, service_sample, rel_tol=1e-9, abs_tol=1e-9)

if __name__ == "__main__":
    regression_test_immediate_service_start()
    regression_test_single_patient_system_time_matches_service_sample()

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
