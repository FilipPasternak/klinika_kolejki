from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QHBoxLayout,
    QLabel,
)


def _format_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-weight: bold;")
    return label


class ControlsPanel(QWidget):
    """Panel providing controls for manipulating the simulation engine."""

    start_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    params_changed = pyqtSignal(float, float, int)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build_ui()
        self._sync_with_engine()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        form_layout = QFormLayout()
        form_layout.setFormAlignment(form_layout.formAlignment() | Qt.AlignmentFlag.AlignLeft)

        self.lambda_spin = QDoubleSpinBox()
        self.lambda_spin.setRange(0.1, 1000.0)
        self.lambda_spin.setDecimals(2)
        self.lambda_spin.setSingleStep(0.1)
        self.lambda_spin.valueChanged.connect(self._on_params_changed)

        self.mu_spin = QDoubleSpinBox()
        self.mu_spin.setRange(0.1, 1000.0)
        self.mu_spin.setDecimals(2)
        self.mu_spin.setSingleStep(0.1)
        self.mu_spin.valueChanged.connect(self._on_params_changed)

        self.servers_spin = QSpinBox()
        self.servers_spin.setRange(1, 20)
        self.servers_spin.setSingleStep(1)
        self.servers_spin.valueChanged.connect(self._on_params_changed)

        form_layout.addRow(_format_label("Arrival rate λ"), self.lambda_spin)
        form_layout.addRow(_format_label("Service rate μ"), self.mu_spin)
        form_layout.addRow(_format_label("Servers c"), self.servers_spin)

        layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_requested.emit)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_requested.emit)
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_requested.emit)

        button_row.addWidget(self.start_button)
        button_row.addWidget(self.pause_button)
        button_row.addWidget(self.reset_button)

        layout.addLayout(button_row)
        layout.addStretch()

    def _sync_with_engine(self):
        params = self.engine.params
        self._set_spin_value(self.lambda_spin, params.arrival_rate_lambda)
        self._set_spin_value(self.mu_spin, params.service_rate_mu)
        self._set_spin_value(self.servers_spin, params.servers_c)

    @staticmethod
    def _set_spin_value(spinbox, value):
        try:
            block = spinbox.blockSignals(True)
            spinbox.setValue(value)
        finally:
            spinbox.blockSignals(block)

    def _on_params_changed(self):
        lam = self.lambda_spin.value()
        mu = self.mu_spin.value()
        servers = self.servers_spin.value()
        self.engine.set_params(lam, mu, servers)
        self.params_changed.emit(lam, mu, servers)

    def refresh(self):
        """Public method to resynchronise the controls with the engine state."""
        self._sync_with_engine()
