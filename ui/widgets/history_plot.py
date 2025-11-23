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
        self.plot_widget.setBackground("#ffffff")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        axis_pen = pg.mkPen(color="#52606d", width=1)
        for axis in ("left", "bottom"):
            ax = self.plot_widget.getAxis(axis)
            ax.setPen(axis_pen)
            ax.setTextPen(axis_pen)
        self.plot_widget.setLabel("left", "Długość kolejki")
        self.plot_widget.setLabel("bottom", "Czas symulacji", units="h")
        self.plot_widget.setTitle("Historia zmian natężenia kolejki", color="#102a43")

        pen = pg.mkPen(color=(45, 125, 210), width=3)
        self._curve = self.plot_widget.plot(pen=pen, fillLevel=0, brush=(45, 125, 210, 40))
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

