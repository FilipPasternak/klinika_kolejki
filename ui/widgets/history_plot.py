from PyQt6.QtWidgets import QWidget

class HistoryPlotWidget(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
