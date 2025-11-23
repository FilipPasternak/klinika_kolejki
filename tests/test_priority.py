import random

from simulation.engine import SimulationEngine


def test_priority_patients_move_to_front_and_keep_order():
    random.seed(42)
    engine = SimulationEngine()
    engine.set_params(arrival_rate_lambda=1.0, service_rate_mu=0.0, servers_c=1)
    engine.set_priority_probability(0.0)
    engine.start()

    engine._on_new_patient(0.0)  # regular patient

    engine.set_priority_probability(1.0)
    engine._on_new_patient(0.1)  # priority patient
    engine._on_new_patient(0.2)  # another priority patient

    snapshot = engine.get_snapshot()

    assert snapshot.queue == [2, 3, 1]
    assert snapshot.priority_patients == {2, 3}
