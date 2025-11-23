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
    QGroupBox,
)


def _format_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-weight: bold; color: #102a43;")
    return label


class ControlsPanel(QWidget):
    """Panel providing controls for manipulating the simulation engine."""

    start_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    params_changed = pyqtSignal(float, float, int)
    priority_changed = pyqtSignal(float)
    time_scale_changed = pyqtSignal(float)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build_ui()
        self._sync_with_engine()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        header = QLabel("Sterowanie symulacją")
        header.setObjectName("controls-header")
        header.setProperty("class", "section-title")
        helper = QLabel("Dostosuj parametry i zarządzaj przebiegiem symulacji w jednym miejscu.")
        helper.setWordWrap(True)
        helper.setProperty("class", "helper-text")
        layout.addWidget(header)
        layout.addWidget(helper)

        parameters_group = QGroupBox("Parametry wejściowe")
        form_layout = QFormLayout()
        form_layout.setFormAlignment(form_layout.formAlignment() | Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        self.lambda_spin = QDoubleSpinBox()
        self.lambda_spin.setRange(0.1, 1000.0)
        self.lambda_spin.setDecimals(2)
        self.lambda_spin.setSingleStep(0.1)
        self.lambda_spin.setToolTip("Średnia liczba pacjentów napływających w ciągu godziny")
        self.lambda_spin.valueChanged.connect(self._on_params_changed)

        self.mu_spin = QDoubleSpinBox()
        self.mu_spin.setRange(0.1, 1000.0)
        self.mu_spin.setDecimals(2)
        self.mu_spin.setSingleStep(0.1)
        self.mu_spin.setToolTip("Średnia szybkość obsługi pacjentów na stanowisku")
        self.mu_spin.valueChanged.connect(self._on_params_changed)

        self.servers_spin = QSpinBox()
        self.servers_spin.setRange(1, 20)
        self.servers_spin.setSingleStep(1)
        self.servers_spin.setToolTip("Liczba równoległych stanowisk obsługi")
        self.servers_spin.valueChanged.connect(self._on_params_changed)

        self.priority_spin = QDoubleSpinBox()
        self.priority_spin.setRange(0.0, 100.0)
        self.priority_spin.setDecimals(1)
        self.priority_spin.setSingleStep(1.0)
        self.priority_spin.setSuffix(" %")
        self.priority_spin.setToolTip("Procent pacjentów obsługiwanych priorytetowo")
        self.priority_spin.valueChanged.connect(self._on_priority_changed)

        self.time_scale_spin = QDoubleSpinBox()
        self.time_scale_spin.setRange(0.1, 20.0)
        self.time_scale_spin.setDecimals(2)
        self.time_scale_spin.setSingleStep(0.1)
        self.time_scale_spin.setSuffix("×")
        self.time_scale_spin.setToolTip("Przyspieszenie symulowanego czasu względem rzeczywistego")
        self.time_scale_spin.valueChanged.connect(self._on_time_scale_changed)

        form_layout.addRow(_format_label("Natężenie napływu λ [pacj./h]"), self.lambda_spin)
        form_layout.addRow(_format_label("Szybkość obsługi μ [pacj./h]"), self.mu_spin)
        form_layout.addRow(_format_label("Liczba stanowisk c"), self.servers_spin)
        form_layout.addRow(_format_label("Udział priorytetów"), self.priority_spin)
        form_layout.addRow(_format_label("Przyspieszenie czasu"), self.time_scale_spin)

        parameters_group.setLayout(form_layout)
        layout.addWidget(parameters_group)

        actions_group = QGroupBox("Sterowanie przebiegiem")
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_requested.emit)
        self.start_button.setMinimumHeight(38)
        self.pause_button = QPushButton("Pauza")
        self.pause_button.clicked.connect(self.pause_requested.emit)
        self.pause_button.setMinimumHeight(38)
        self.reset_button = QPushButton("Resetuj")
        self.reset_button.clicked.connect(self.reset_requested.emit)
        self.reset_button.setMinimumHeight(38)

        button_row.addWidget(self.start_button)
        button_row.addWidget(self.pause_button)
        button_row.addWidget(self.reset_button)

        actions_group.setLayout(button_row)
        layout.addWidget(actions_group)
        layout.addStretch()

    def _sync_with_engine(self):
        params = self.engine.params
        self._set_spin_value(self.lambda_spin, params.arrival_rate_lambda)
        self._set_spin_value(self.mu_spin, params.service_rate_mu)
        self._set_spin_value(self.servers_spin, params.servers_c)
        self._set_spin_value(self.priority_spin, params.priority_probability * 100.0)
        self._set_spin_value(self.time_scale_spin, params.time_scale)

    @staticmethod
    def _set_spin_value(spinbox, value):
        try:
            block = spinbox.blockSignals(True)
            spinbox.setValue(value)
        finally:
            spinbox.blockSignals(block)

    def _on_params_changed(self, *_):
        lam = self.lambda_spin.value()
        mu = self.mu_spin.value()
        servers = self.servers_spin.value()
        self.engine.set_params(lam, mu, servers)
        self.params_changed.emit(lam, mu, servers)

    def _on_priority_changed(self, value: float):
        probability = max(min(value / 100.0, 1.0), 0.0)
        self.engine.set_priority_probability(probability)
        self.priority_changed.emit(probability)

    def _on_time_scale_changed(self, value: float):
        scale = value
        self.engine.set_time_scale(scale)
        self.time_scale_changed.emit(scale)

    def refresh(self):
        """Public method to resynchronise the controls with the engine state."""
        self._sync_with_engine()
