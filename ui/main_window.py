from PySide6.QtWidgets import (
    QMainWindow,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
    QApplication,
)
from PySide6.QtGui import QAction, QIcon, QPixmap, QColor
from PySide6.QtCore import Qt

from ui.views import HomeView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VPN Gate Client")
        self.setMinimumSize(500, 300)

        self._view = HomeView()
        self.setCentralWidget(self._view)

        self._tray = self._create_tray()
        self._view.connection_changed.connect(self._set_tray_color)
        self._view.connecting_changed.connect(self._set_tray_connecting)

    def _create_tray(self):
        # generates a simple colored icon since the app ships no image assets
        icon = self._make_icon("#ef4444")
        icon.addPixmap(self._make_pixmap("#ef4444"))

        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_window)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        tray = QSystemTrayIcon(icon, self)
        tray.setContextMenu(menu)
        tray.setToolTip("VPN Gate Client")
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        return tray

    @staticmethod
    def _make_pixmap(color):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        from PySide6.QtGui import QPainter

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        painter.end()
        return pixmap

    def _make_icon(self, color):
        icon = QIcon()
        icon.addPixmap(self._make_pixmap(color))
        return icon

    def _set_tray_color(self, connected):
        self._tray.setIcon(self._make_icon("#22c55e" if connected else "#ef4444"))

    def _set_tray_connecting(self, connecting):
        if connecting:
            self._tray.setIcon(self._make_icon("#3b82f6"))
        else:
            self._tray.setIcon(self._make_icon("#ef4444"))

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()


    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        if self._view.is_connected():
            answer = QMessageBox.warning(
                self,
                "VPN Gate Client",
                "A VPN connection is currently active.\n"
                "Exiting will terminate the connection.\n\n"
                "Do you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._view.disconnect()
        QApplication.instance().quit()

    def closeEvent(self, event):
        # closing the window hides it to the system tray instead of quitting
        event.ignore()
        if self._view.is_connected():
            self._tray.showMessage(
                "VPN Gate Client",
                "VPN connection is still active.\n"
                "The app remains running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
        self.hide()
