import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class HistoryPlotWidget(QWidget):
    """Displays the historical queue length using pyqtgraph."""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Queue length")
        self.plot_widget.setLabel("bottom", "Simulation time", units="h")

        self._curve = self.plot_widget.plot(pen=pg.mkPen(color=(239, 71, 111), width=2))
        layout.addWidget(self.plot_widget)

        self._times = []
        self._queue_lengths = []

    def reset(self):
        self._times.clear()
        self._queue_lengths.clear()
        self._curve.setData([], [])

    def update_from_snapshot(self, snapshot):
        self._times.append(snapshot.sim_time)
        self._queue_lengths.append(len(snapshot.queue))
        # Limit to last 500 points to avoid memory bloat in long sessions
        if len(self._times) > 500:
            self._times = self._times[-500:]
            self._queue_lengths = self._queue_lengths[-500:]
        self._curve.setData(self._times, self._queue_lengths)

