"""
Simulation engine for an M/M/c-style clinic queue.

Current stage:
- No SimPy yet; a lightweight, manual, step-by-step loop.
- Poisson arrivals with rate λ (per hour).
- Exponential service with rate μ (per hour per server).
- c parallel servers.
- FIFO queue.
- Empirical statistics updated as patients complete service.

Intended GUI API:
    engine.set_params(...)
    engine.start()
    engine.step(dt)    # advance by dt (simulation hours)
    snap = engine.get_snapshot()

This module does not depend on PyQt.
"""

from dataclasses import dataclass
import math
import random
from typing import List, Dict, Optional

from .metrics import erlang_c_metrics

@dataclass
class SimulationParams:
    arrival_rate_lambda: float  # λ [patients/hour]
    service_rate_mu: float      # μ [patients/hour/server]
    servers_c: int              # number of servers
    time_scale: float = 1.0     # reserved for GUI use

@dataclass
class Patient:
    patient_id: int
    arrival_time: float
    service_start_time: Optional[float] = None
    service_end_time: Optional[float] = None

@dataclass
class ServerSlot:
    busy: bool = False
    patient_id: Optional[int] = None
    time_remaining: float = 0.0  # remaining service time (simulation hours)

class SimulationStateSnapshot:
    def __init__(self, queue, in_service, metrics, sim_time):
        self.queue = queue                      # list of patient IDs
        self.in_service = in_service            # {server_index: {patient_id, remaining}}
        self.metrics = metrics                  # dict
        self.sim_time = sim_time                # float

class SimulationEngine:
    def __init__(self):
        self.params = SimulationParams(
            arrival_rate_lambda=6.0,
            service_rate_mu=4.0,
            servers_c=2,
            time_scale=1.0,
        )

        self.sim_time = 0.0
        self._running = False
        self._next_patient_id = 1

        self._patients: Dict[int, Patient] = {}
        self._queue: List[int] = []
        self._servers: List[ServerSlot] = []

        self._next_arrival_time: Optional[float] = None

        self._total_wait_time = 0.0
        self._total_system_time = 0.0
        self._served_patients = 0

        self._queue_length_samples: List[int] = []
        self._system_length_samples: List[int] = []

    # ---- public API ----

    def set_params(self, arrival_rate_lambda: float, service_rate_mu: float, servers_c: int):
        self.params.arrival_rate_lambda = float(arrival_rate_lambda)
        self.params.service_rate_mu = float(service_rate_mu)
        self.params.servers_c = int(servers_c)

    def start(self):
        self.sim_time = 0.0
        self._running = True
        self._next_patient_id = 1

        self._patients.clear()
        self._queue.clear()
        self._servers = [ServerSlot() for _ in range(self.params.servers_c)]

        self._next_arrival_time = self.sim_time + self._sample_interarrival_time()

        self._total_wait_time = 0.0
        self._total_system_time = 0.0
        self._served_patients = 0

        self._queue_length_samples.clear()
        self._system_length_samples.clear()

    def pause(self):
        self._running = False

    def resume(self):
        """Resume the simulation without resetting any state."""
        if self._servers:
            self._running = True

    def is_running(self) -> bool:
        return self._running

    def step(self, dt: float):
        if not self._running or dt <= 0:
            return

        # basic sub-stepping to avoid jumping over events
        sub_dt = 0.01
        steps = max(1, int(dt / sub_dt))
        real_sub_dt = dt / steps

        for _ in range(steps):
            self._advance_one_tick(real_sub_dt)

    def get_snapshot(self) -> SimulationStateSnapshot:
        queue_copy = list(self._queue)
        in_service_view = {}
        for idx, srv in enumerate(self._servers):
            if srv.busy and srv.patient_id is not None:
                in_service_view[idx] = {
                    "patient_id": srv.patient_id,
                    "remaining": max(srv.time_remaining, 0.0),
                }
            else:
                in_service_view[idx] = {"patient_id": None, "remaining": 0.0}

        metrics = self._compute_metrics_snapshot()
        return SimulationStateSnapshot(queue_copy, in_service_view, metrics, self.sim_time)

    # ---- internals ----

    def _advance_one_tick(self, dt: float):
        old_time = self.sim_time
        new_time = self.sim_time + dt

        # arrivals that happen within (old_time, new_time]
        while self._next_arrival_time is not None and self._next_arrival_time <= new_time:
            arrival_t = self._next_arrival_time
            self.sim_time = arrival_t
            self._on_new_patient(arrival_t)
            # Allow immediately-available servers to start service at the exact
            # arrival timestamp.
            self._assign_waiting_patients()
            self._next_arrival_time = self.sim_time + self._sample_interarrival_time()

        self.sim_time = new_time

        self._update_servers(dt)
        self._assign_waiting_patients()
        self._sample_lengths()

    def _on_new_patient(self, t: float):
        pid = self._next_patient_id
        self._next_patient_id += 1
        self._patients[pid] = Patient(patient_id=pid, arrival_time=t)
        self._queue.append(pid)

    def _assign_waiting_patients(self):
        for srv in self._servers:
            if not self._queue:
                break
            if srv.busy:
                continue
            pid = self._queue.pop(0)
            patient = self._patients[pid]
            patient.service_start_time = self.sim_time
            srv.busy = True
            srv.patient_id = pid
            srv.time_remaining = self._sample_service_time()

    def _update_servers(self, dt: float):
        for srv in self._servers:
            if not srv.busy:
                continue
            srv.time_remaining -= dt
            if srv.time_remaining <= 0.0 and srv.patient_id is not None:
                overshoot = -srv.time_remaining
                completion_time = self.sim_time - overshoot
                pid = srv.patient_id
                patient = self._patients[pid]
                patient.service_end_time = completion_time
                if patient.service_start_time is not None:
                    self._total_wait_time += (patient.service_start_time - patient.arrival_time)
                self._total_system_time += (patient.service_end_time - patient.arrival_time)
                self._served_patients += 1
                srv.busy = False
                srv.patient_id = None
                srv.time_remaining = 0.0

    def _sample_lengths(self):
        q = len(self._queue)
        busy = sum(1 for s in self._servers if s.busy)
        self._queue_length_samples.append(q)
        self._system_length_samples.append(q + busy)

    def _sample_interarrival_time(self) -> float:
        lam = self.params.arrival_rate_lambda
        if lam <= 0:
            return float("inf")
        return random.expovariate(lam)

    def _sample_service_time(self) -> float:
        mu = self.params.service_rate_mu
        if mu <= 0:
            return float("inf")
        return random.expovariate(mu)

    def _compute_metrics_snapshot(self) -> dict:
        lam = self.params.arrival_rate_lambda
        mu = self.params.service_rate_mu
        c = self.params.servers_c

        rho = lam / (c * mu) if (c > 0 and mu > 0) else None

        avg_Wq = (self._total_wait_time / self._served_patients) if self._served_patients > 0 else None
        avg_W = (self._total_system_time / self._served_patients) if self._served_patients > 0 else None
        avg_Lq = (sum(self._queue_length_samples) / len(self._queue_length_samples)) if self._queue_length_samples else None
        avg_L = (sum(self._system_length_samples) / len(self._system_length_samples)) if self._system_length_samples else None

        analytical = erlang_c_metrics(lam, mu, c)

        return {
            "empirical": {"rho": rho, "Wq": avg_Wq, "W": avg_W, "Lq": avg_Lq, "L": avg_L},
            "theoretical": analytical,
        }
