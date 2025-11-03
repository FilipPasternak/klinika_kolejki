"""Application entry point for the clinic queue simulation GUI."""

import sys

from PyQt6.QtWidgets import QApplication

from simulation.engine import SimulationEngine
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    engine = SimulationEngine()
    window = MainWindow(engine)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
