from PySide6.QtWidgets import QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget

from core.vpn_client import VPNClient
from ui.workers import LoadServersWorker, ConnectWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VPN Gate Client")
        self.setMinimumSize(300, 120)

        self._client = VPNClient()
        self._servers = None
        self._load_worker = None
        self._connect_worker = None

        self._button = QPushButton("Connect")
        self._button.clicked.connect(self._toggle_connect)

        self._status = QLabel("Loading servers...")
        self._status.setStyleSheet("color: gray;")

        self._server_info = QLabel("")
        self._server_info.setStyleSheet("color: gray;")

        layout = QVBoxLayout()
        layout.addWidget(self._button)
        layout.addWidget(self._status)
        layout.addWidget(self._server_info)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._load_servers()

    def _load_servers(self):
        self._button.setEnabled(False)
        self._load_worker = LoadServersWorker()
        self._load_worker.loaded.connect(self._on_servers_loaded)
        self._load_worker.message.connect(self._on_message)
        self._load_worker.start()

    def _on_servers_loaded(self, servers):
        self._servers = servers
        self._button.setEnabled(True)
        if servers is not None:
            self._status.setText("Disconnected")
        else:
            self._status.setText("Failed to load servers")

    def _toggle_connect(self):
        if self._connect_worker is not None and self._connect_worker.isRunning():
            return
        if self._client.is_connected():
            self._client.disconnect()
            self._button.setText("Connect")
            self._status.setText("Disconnected")
            self._status.setStyleSheet("color: gray;")
            self._server_info.setText("")
        else:
            self._connect()

    def _connect(self):
        self._button.setEnabled(False)
        self._status.setText("Connecting...")
        self._connect_worker = ConnectWorker(self._client, self._servers)
        self._connect_worker.connected.connect(self._on_connected)
        self._connect_worker.message.connect(self._on_message)
        self._connect_worker.finished.connect(lambda: self._button.setEnabled(True))
        self._connect_worker.start()

    def _on_connected(self, success, server):
        if success:
            self._button.setText("Disconnect")
            self._status.setText("Connected")
            self._status.setStyleSheet("color: green;")
            if server:
                self._server_info.setText(
                    f"{server.get('CountryLong', 'Unknown')} - {server.get('IP', 'Unknown')}"
                )
                self._server_info.setStyleSheet("color: green;")

    def _on_message(self, text):
        self._status.setText(text)
        self._status.setStyleSheet("color: red;")

    def closeEvent(self, event):
        if self._client.is_connected():
            self._client.disconnect()
        event.accept()
