import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.app.main_window import MainWindow


def main():
    if sys.platform == "win32":
        import ctypes
        app_id = "FileDeduplicator.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    
    app = QApplication(sys.argv)
    app.setApplicationName("FileDeduplicator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FileDeduplicator")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
