import sys
import traceback
from PyQt5.QtWidgets import QApplication
from app import MainWindow


def _excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)


if __name__ == "__main__":
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setApplicationName("WatchBuffer")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
