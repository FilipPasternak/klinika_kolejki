from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QGroupBox,
)


def _metric_label(name: str) -> QLabel:
    label = QLabel(name)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    label.setStyleSheet("font-weight: bold;")
    return label


def _value_label() -> QLabel:
    label = QLabel("–")
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return label


class MetricsPanel(QWidget):
    """Displays empirical and theoretical metrics from the simulation engine."""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.empirical_group, self.empirical_values = self._create_metrics_group(
            "Metryki empiryczne"
        )
        self.theoretical_group, self.theoretical_values = self._create_metrics_group(
            "Metryki analityczne"
        )

        layout.addWidget(self.empirical_group)
        layout.addWidget(self.theoretical_group)
        layout.addStretch()

    def _create_metrics_group(self, title: str):
        group = QGroupBox(title)
        grid = QGridLayout()
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        keys = ["rho", "Lq", "Wq", "L", "W"]
        labels = {}
        for row, key in enumerate(keys):
            grid.addWidget(_metric_label(key), row, 0)
            value = _value_label()
            labels[key] = value
            grid.addWidget(value, row, 1)

        group.setLayout(grid)
        return group, labels

    def reset(self):
        for label in self.empirical_values.values():
            label.setText("–")
        for label in self.theoretical_values.values():
            label.setText("–")

    def update_from_snapshot(self, snapshot):
        metrics = snapshot.metrics
        empirical = metrics.get("empirical", {})
        theoretical = metrics.get("theoretical", {})

        for key, label in self.empirical_values.items():
            label.setText(self._format_value(empirical.get(key)))

        for key, label in self.theoretical_values.items():
            label.setText(self._format_value(theoretical.get(key)))

    @staticmethod
    def _format_value(value):
        if value is None:
            return "–"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

