import ctypes
import os
import sys
import tempfile

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class _SingleInstanceLock:
    # holds an exclusive lock on a file for the lifetime of the process, so at
    # most one instance can run at a time. The lock is released by the OS when
    # the process exits (even on a crash), so there is never a stale lock.
    def __init__(self):
        self._file = None

    def acquire(self):
        path = os.path.join(tempfile.gettempdir(), "vpngate.lock")
        self._file = open(path, "w")
        try:
            if os.name == "nt":
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._file.close()
            self._file = None
            return False
        self._file.seek(0)
        self._file.truncate()
        self._file.write(str(os.getpid()))
        self._file.flush()
        return True


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
    lock = _SingleInstanceLock()
    if not lock.acquire():
        # another instance already holds the lock; tell the user and exit
        QMessageBox.information(
            None,
            "VPN Gate Client",
            "VPN Gate Client is already running.\nClose this popup to exit.",
        )
        sys.exit(0)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
