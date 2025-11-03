# Clinic Queue Simulation

A desktop application for experimenting with an M/M/c clinic queue. The project bundles a lightweight discrete-event simulation engine, a PyQt6 GUI, and helper scripts for validating the queueing math. Use it to explore how staffing (``c``), arrivals (``λ``), and service capabilities (``μ``) change patient experience.

## Project goals
- Provide an interactive GUI that visualises patients moving between the waiting room and servers in real time.
- Offer tunable parameters so clinicians can run "what-if" analyses on staffing and arrival rates.
- Report both empirical (simulation-based) and analytical (Erlang C) performance metrics for quick comparison.
- Serve as a foundation for future experiments such as SimPy-backed engines or richer reporting.

## Prerequisites
- Python 3.10 or later.
- A virtual environment is recommended (``venv`` or ``conda``).
- System packages for Qt rendering (on Linux, ensure an X server or Wayland session is available).

## Installation
```bash
# create and activate a virtual environment (example shown for venv)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# install Python dependencies
pip install -r requirements.txt
```
The requirements file installs PyQt6, pyqtgraph, numpy, and other dependencies needed by both the simulation engine and GUI.

## Launching the GUI
```bash
python main.py
```
This boots a PyQt6 window (`ui/main_window.py`) that wires the `SimulationEngine` into several widgets:
- **Controls panel** – adjust λ, μ, and c and control the simulation run state (`ui/widgets/controls_panel.py`).
- **Queue view** – animated representation of the waiting room and servers (`ui/widgets/queue_view.py`).
- **Metrics panel** – live empirical and analytical metrics (`ui/widgets/metrics_panel.py`).
- **History plot** – queue length over time using `pyqtgraph` (`ui/widgets/history_plot.py`).

Use the **Start**, **Pause**, and **Reset** buttons to manage a session. Parameter edits while paused automatically restart the simulation with fresh state.

## Simulation parameters (λ, μ, c)
- **Arrival rate (λ)** – expected patient arrivals per simulation hour (`SimulationParams.arrival_rate_lambda`). Lowering λ reduces demand; increasing λ creates heavier load.
- **Service rate (μ)** – expected patients served per hour *per server* (`SimulationParams.service_rate_mu`). Higher μ shortens service times.
- **Number of servers (c)** – parallel service channels (e.g., number of clinicians) (`SimulationParams.servers_c`).

Behind the scenes the engine draws exponential inter-arrival and service samples (`simulation/engine.py`) and advances patient state in sub-steps so arrivals and completions happen at the correct timestamps.

## Interpreting the metrics
Every GUI refresh calls `SimulationEngine.get_snapshot()`, which returns:
- **Empirical metrics** – rolling statistics updated each time a patient completes service (`simulation/engine.py`). These include:
  - `ρ` (utilisation) calculated from λ, μ, and c.
  - `Wq` and `W` (waiting time and total time in system) averaged over served patients.
  - `Lq` and `L` (queue/system lengths) averaged from periodic samples.
- **Analytical metrics** – closed-form Erlang C results from `simulation.metrics.erlang_c_metrics()`, giving theoretical `P0`, `Pw`, `Lq`, `Wq`, `W`, and `L` when the system is stable.

Comparing both sets highlights the gap between the random empirical sample path and the steady-state theory. When ρ ≥ 1 the analytical values return `None`, indicating an unstable configuration.

## Repository structure
```
├── simulation/          # Core engine and Erlang C formulas
│   ├── engine.py        # Discrete-event simulation and snapshot assembly
│   └── metrics.py       # Analytical queueing helpers (Erlang C)
├── ui/                  # PyQt6 application modules
│   ├── main_window.py   # Glues controls, visualisation, and timers
│   └── widgets/         # Individual GUI widgets (controls, metrics, queue view, history plot)
├── resources/           # Placeholder for future icons, styles, translations
├── main.py              # GUI entry point
├── quick_test.py        # Headless regression checks and demo runner
├── tests/               # Pytest suite focusing on analytical correctness
└── requirements.txt     # Python dependency lock-in
```

## Running the headless demo
The repository keeps a CLI smoke test that runs without a GUI:
```bash
python quick_test.py
```
The script executes regression-style checks on the engine and then advances a short 2-hour simulation, printing the queue, server assignments, and metric snapshots to the console.

## Validating with tests and coverage
Automated tests live under `tests/` and concentrate on `erlang_c_metrics` and the snapshot API.
```bash
pytest
```
For lightweight coverage feedback you can add `pytest --cov=simulation --cov-report=term-missing` (requires `pytest-cov`, which you can install manually if desired).

## Analytical vs. empirical calculations
Analytical metrics are calculated on demand via `erlang_c_metrics`, which implements the Erlang C closed forms and guards against unstable parameter sets. Empirical metrics are accumulated incrementally in `SimulationEngine._compute_metrics_snapshot()` by sampling queue lengths each tick and averaging wait/system times once patients finish service. This dual approach gives immediate theoretical baselines alongside observed performance.

## What remains to be done
- **Integrate richer simulation backends.** The engine currently uses a hand-rolled loop; migrating to SimPy (or adding calendar-based events) would improve fidelity and extensibility.
- **Persist and reload scenarios.** Saving parameter presets, importing CSV arrival traces, or exposing command-line configuration is still future work.
- **Polish the GUI.** The interface lacks theming, icons in `resources/`, accessibility auditing, and comprehensive error handling for invalid inputs.
- **Expand automated testing.** Only analytical helpers are covered; adding end-to-end GUI smoke tests or stochastic regression baselines would catch regressions sooner.
- **Document deployment.** Packaging for installers or frozen binaries (PyInstaller, Briefcase, etc.) is not yet addressed.
