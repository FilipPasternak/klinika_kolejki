"""MainWindow skeleton (GUI not wired yet)."""
from PyQt6.QtWidgets import QMainWindow

class MainWindow(QMainWindow):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clinic Queue Simulation")
        self.engine = engine
