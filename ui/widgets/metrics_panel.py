from PyQt6.QtWidgets import QWidget

class MetricsPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
