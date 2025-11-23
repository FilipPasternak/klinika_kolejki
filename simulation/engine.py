"""Simulation engine for an M/M/c-style clinic queue driven by SimPy."""

from dataclasses import dataclass
import math
import random
from typing import Dict, List, Optional

import simpy

from .metrics import erlang_c_metrics


@dataclass
class SimulationParams:
    arrival_rate_lambda: float  # λ [patients/hour]
    service_rate_mu: float      # μ [patients/hour/server]
    servers_c: int              # number of servers
    time_scale: float = 1.0
    priority_probability: float = 0.1  # share of patients treated as priority


@dataclass
class Patient:
    patient_id: int
    arrival_time: float
    priority: bool = False
    service_start_time: Optional[float] = None
    service_end_time: Optional[float] = None


@dataclass
class ServerSlot:
    busy: bool = False
    patient_id: Optional[int] = None
    service_end_time: float = 0.0  # absolute completion time in simulation hours


class SimulationStateSnapshot:
    def __init__(self, queue, in_service, metrics, sim_time, priority_patients):
        self.queue = queue                      # list of patient IDs
        self.in_service = in_service            # {server_index: {patient_id, remaining}}
        self.metrics = metrics                  # dict
        self.sim_time = sim_time                # float
        self.priority_patients = priority_patients  # set of patient IDs


class SimulationEngine:
    def __init__(self):
        self.params = SimulationParams(
            arrival_rate_lambda=6.0,
            service_rate_mu=4.0,
            servers_c=2,
            time_scale=1.0,
            priority_probability=0.1,
        )

        self.sim_time = 0.0
        self._running = False
        self._next_patient_id = 1

        self._patients: Dict[int, Patient] = {}
        self._priority_queue: List[int] = []
        self._regular_queue: List[int] = []
        self._servers: List[ServerSlot] = []

        self.env: Optional[simpy.Environment] = None
        self._arrival_process: Optional[simpy.events.Process] = None

        self._total_wait_time = 0.0
        self._total_system_time = 0.0
        self._served_patients = 0

        self._last_sample_time = 0.0
        self._queue_time_integral = 0.0
        self._system_time_integral = 0.0
        self._current_queue_length = 0
        self._current_system_length = 0

    # ---- public API ----

    def set_params(self, arrival_rate_lambda: float, service_rate_mu: float, servers_c: int):
        self.params.arrival_rate_lambda = float(arrival_rate_lambda)
        self.params.service_rate_mu = float(service_rate_mu)
        self.params.servers_c = int(servers_c)

    def set_priority_probability(self, probability: float):
        self.params.priority_probability = min(max(float(probability), 0.0), 1.0)

    def set_time_scale(self, time_scale: float):
        self.params.time_scale = max(float(time_scale), 0.01)

    def start(self):
        self.sim_time = 0.0
        self._running = True
        self._next_patient_id = 1

        self._patients.clear()
        self._priority_queue.clear()
        self._regular_queue.clear()
        self._servers = [ServerSlot() for _ in range(self.params.servers_c)]

        self.env = simpy.Environment()
        self._arrival_process = self.env.process(self._arrival_generator())

        self._total_wait_time = 0.0
        self._total_system_time = 0.0
        self._served_patients = 0

        self._last_sample_time = 0.0
        self._queue_time_integral = 0.0
        self._system_time_integral = 0.0
        self._current_queue_length = 0
        self._current_system_length = 0

    def pause(self):
        self._running = False

    def resume(self):
        """Resume the simulation without resetting any state."""
        if self._servers:
            self._running = True

    def is_running(self) -> bool:
        return self._running

    def step(self, dt: float):
        if not self._running or dt <= 0 or self.env is None:
            return

        target_time = self.sim_time + dt
        self.env.run(until=target_time)
        self.sim_time = self.env.now
        self._update_time_averages(self.sim_time)

    def get_snapshot(self) -> SimulationStateSnapshot:
        queue_copy = list(self._priority_queue) + list(self._regular_queue)
        in_service_view = {}
        for idx, srv in enumerate(self._servers):
            if srv.busy and srv.patient_id is not None:
                in_service_view[idx] = {
                    "patient_id": srv.patient_id,
                    "remaining": max(srv.service_end_time - self.sim_time, 0.0),
                }
            else:
                in_service_view[idx] = {"patient_id": None, "remaining": 0.0}

        priority_patients = {
            pid for pid, patient in self._patients.items() if patient.priority
        }

        metrics = self._compute_metrics_snapshot()
        return SimulationStateSnapshot(
            queue_copy, in_service_view, metrics, self.sim_time, priority_patients
        )

    # ---- internals ----

    def _arrival_generator(self):
        while True:
            interarrival = self._sample_interarrival_time()
            if math.isinf(interarrival):
                return
            yield self.env.timeout(interarrival)
            self._on_new_patient(self.env.now)

    def _on_new_patient(self, now: float):
        self._update_time_averages(now)
        pid = self._next_patient_id
        self._next_patient_id += 1
        is_priority = random.random() < self.params.priority_probability
        self._patients[pid] = Patient(
            patient_id=pid, arrival_time=now, priority=is_priority
        )
        self._enqueue_patient(pid, is_priority)
        self._refresh_lengths(now)
        self._assign_waiting_patients(now)

    def _enqueue_patient(self, pid: int, priority: bool):
        if priority:
            self._priority_queue.append(pid)
        else:
            self._regular_queue.append(pid)

    def _pop_next_patient(self) -> Optional[int]:
        if self._priority_queue:
            return self._priority_queue.pop(0)
        if self._regular_queue:
            return self._regular_queue.pop(0)
        return None

    def _assign_waiting_patients(self, now: float):
        for srv in self._servers:
            if not self._priority_queue and not self._regular_queue:
                break
            if srv.busy:
                continue
            service_time = self._sample_service_time()
            if math.isinf(service_time):
                continue

            pid = self._pop_next_patient()
            if pid is None:
                break
            patient = self._patients[pid]
            patient.service_start_time = now

            self._update_time_averages(now)
            srv.busy = True
            srv.patient_id = pid
            srv.service_end_time = now + service_time
            self._refresh_lengths(now)

            self.env.process(self._service_patient(srv, pid, service_time))

    def _service_patient(self, srv: ServerSlot, pid: int, service_time: float):
        yield self.env.timeout(service_time)
        self._on_service_completed(srv, pid, self.env.now)

    def _on_service_completed(self, srv: ServerSlot, pid: int, now: float):
        self._update_time_averages(now)
        if srv.patient_id != pid:
            return

        patient = self._patients.get(pid)
        if not patient:
            return

        patient.service_end_time = now
        if patient.service_start_time is not None:
            self._total_wait_time += (patient.service_start_time - patient.arrival_time)
        self._total_system_time += (patient.service_end_time - patient.arrival_time)
        self._served_patients += 1

        srv.busy = False
        srv.patient_id = None
        srv.service_end_time = now
        self._refresh_lengths(now)
        self._assign_waiting_patients(now)

    def _busy_servers(self) -> int:
        return sum(1 for srv in self._servers if srv.busy)

    def _refresh_lengths(self, now: float):
        self._current_queue_length = len(self._priority_queue) + len(self._regular_queue)
        self._current_system_length = self._current_queue_length + self._busy_servers()
        self._last_sample_time = now

    def _update_time_averages(self, now: float):
        dt = now - self._last_sample_time
        if dt > 0:
            self._queue_time_integral += self._current_queue_length * dt
            self._system_time_integral += self._current_system_length * dt
            self._last_sample_time = now

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

        total_time = self.sim_time if self.sim_time > 0 else None
        avg_Lq = (self._queue_time_integral / total_time) if total_time else None
        avg_L = (self._system_time_integral / total_time) if total_time else None

        analytical = erlang_c_metrics(lam, mu, c)

        return {
            "empirical": {"rho": rho, "Wq": avg_Wq, "W": avg_W, "Lq": avg_Lq, "L": avg_L},
            "theoretical": analytical,
        }
