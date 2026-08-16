import ctypes
import os
import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def _is_admin():
    if not os.name == "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _elevate():
    # on Windows, re-launch with administrator privileges (UAC prompt) unless
    # we already have them; returns True if the current process should run the
    # app, False if an elevated instance was launched and this one must exit
    if os.name != "nt" or _is_admin():
        return True
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    return result <= 32


def main():
    if not _elevate():
        return
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
