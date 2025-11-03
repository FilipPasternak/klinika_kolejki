"""Main application window assembling all widgets."""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
)

from .widgets.controls_panel import ControlsPanel
from .widgets.queue_view import QueueView
from .widgets.metrics_panel import MetricsPanel
from .widgets.history_plot import HistoryPlotWidget


class MainWindow(QMainWindow):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clinic Queue Simulation")
        self.engine = engine

        self._time_step = 0.1  # simulation hours per timer tick
        self._engine_initialized = False

        self._build_ui()
        self._create_timer()
        self._prepare_new_run(clear_history=True)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        self.controls_panel = ControlsPanel(self.engine)
        self.queue_view = QueueView(self.engine)
        self.metrics_panel = MetricsPanel(self.engine)
        self.history_plot = HistoryPlotWidget(self.engine)

        layout.addWidget(self.controls_panel, stretch=0)
        layout.addWidget(self.queue_view, stretch=2)

        side_panel = QVBoxLayout()
        side_panel.setContentsMargins(0, 0, 0, 0)
        side_panel.setSpacing(8)
        side_panel.addWidget(self.metrics_panel)
        side_panel.addWidget(self.history_plot, stretch=1)

        layout.addLayout(side_panel, stretch=1)

        self.controls_panel.start_requested.connect(self._on_start_requested)
        self.controls_panel.pause_requested.connect(self._on_pause_requested)
        self.controls_panel.reset_requested.connect(self._on_reset_requested)
        self.controls_panel.params_changed.connect(self._on_params_changed)

    def _create_timer(self):
        self.simulation_timer = QTimer(self)
        self.simulation_timer.setInterval(50)
        self.simulation_timer.timeout.connect(self._advance_simulation)

    def _ensure_engine_initialised(self):
        if not self._engine_initialized:
            self.engine.start()
            self.engine.pause()
            self._engine_initialized = True

    def _prepare_new_run(self, clear_history: bool):
        self.simulation_timer.stop()
        self.queue_view.stop()
        self.engine.pause()
        self._engine_initialized = False
        self._ensure_engine_initialised()

        if clear_history:
            self.history_plot.reset()
        self.metrics_panel.reset()

        snapshot = self.engine.get_snapshot()
        self.metrics_panel.update_from_snapshot(snapshot)
        self.history_plot.update_from_snapshot(snapshot)
        self.queue_view.sync_once()
        self.controls_panel.refresh()

    def _advance_simulation(self):
        if not self.engine.is_running():
            self.simulation_timer.stop()
            return

        dt = self.engine.params.time_scale * self._time_step
        if dt <= 0:
            dt = self._time_step
        self.engine.step(dt)

        snapshot = self.engine.get_snapshot()
        self.metrics_panel.update_from_snapshot(snapshot)
        self.history_plot.update_from_snapshot(snapshot)

    def _on_start_requested(self):
        self._ensure_engine_initialised()
        self.engine.resume()
        if not self.simulation_timer.isActive():
            self.simulation_timer.start()
        self.queue_view.start()

    def _on_pause_requested(self):
        self.engine.pause()
        self.simulation_timer.stop()
        self.queue_view.stop()

    def _on_reset_requested(self):
        self._prepare_new_run(clear_history=True)

    def _on_params_changed(self, *_):
        if not self.engine.is_running():
            self._prepare_new_run(clear_history=True)

