from simulation.engine import SimulationEngine

if __name__ == "__main__":
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
