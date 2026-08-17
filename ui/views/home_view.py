from PySide6.QtWidgets import QPushButton, QLabel, QVBoxLayout, QWidget

from core.vpn_client import VPNClient
from ui.workers import LoadServersWorker, ConnectWorker
from ui.views.server_picker import PickerDialog


class HomeView(QWidget):
    # the landing view: a connect button plus status and server info labels
    def __init__(self):
        super().__init__()

        self._client = VPNClient()
        self._servers = None
        self._selected_country = None
        self._selected_server = None
        self._load_worker = None
        self._connect_worker = None

        self._country_button = QPushButton("Change Country")
        self._country_button.setEnabled(False)
        self._country_button.clicked.connect(self._open_country_picker)

        self._server_button = QPushButton("Change Server")
        self._server_button.setEnabled(False)
        self._server_button.hide()
        self._server_button.clicked.connect(self._open_server_picker)

        self._button = QPushButton("Connect")
        self._button.clicked.connect(self._toggle_connect)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.hide()
        self._cancel_button.clicked.connect(self._cancel_connect)

        self._status = QLabel("Loading servers...")
        self._status.setStyleSheet("color: gray;")

        self._server_info = QLabel("")
        self._server_info.setStyleSheet("color: gray;")

        layout = QVBoxLayout()
        layout.addWidget(self._country_button)
        layout.addWidget(self._server_button)
        layout.addWidget(self._button)
        layout.addWidget(self._cancel_button)
        layout.addWidget(self._status)
        layout.addWidget(self._server_info)
        self.setLayout(layout)

        self._load_servers()

    def is_connected(self):
        return self._client.is_connected()

    def _open_country_picker(self):
        countries = self._servers.get_countries() if self._servers else []
        dialog = PickerDialog([(c, c) for c in countries], "Change Country", self)
        dialog.selected.connect(self._on_country_selected)
        dialog.exec()

    def _on_country_selected(self, country):
        if country == self._selected_country:
            return
        self._selected_country = country
        self._selected_server = None
        self._country_button.setText(country)
        self._server_button.show()
        self._server_button.setEnabled(True)
        self._server_button.setText("Change Server")
        if self._connect_worker is not None and self._connect_worker.isRunning():
            self._cancel_connect()
        if self._client.is_connected():
            self._client.disconnect()
            self._reset_idle_ui()

    def _open_server_picker(self):
        servers = self._servers.get_servers_in_country(self._selected_country) or []
        choices = [(self._server_label(s), s) for s in servers]
        dialog = PickerDialog(choices, "Change Server", self)
        dialog.selected.connect(self._on_server_selected)
        dialog.exec()

    def _on_server_selected(self, server):
        self._selected_server = server
        self._server_button.setText(self._server_label(server))
        if self._connect_worker is not None and self._connect_worker.isRunning():
            self._cancel_connect()
        if self._client.is_connected():
            self._client.disconnect()
            self._reset_idle_ui()

    @staticmethod
    def _server_label(server):
        return f"{server.get('IP', 'Unknown')} - {server.get('HostName', 'Unknown')}"

    def disconnect(self):
        # disconnects an active connection and resets the UI to its idle state
        if self._client.is_connected():
            self._client.disconnect()
            self._reset_idle_ui()

    def _load_servers(self):
        self._button.setEnabled(False)
        self._load_worker = LoadServersWorker()
        self._load_worker.loaded.connect(self._on_servers_loaded)
        self._load_worker.message.connect(self._on_message)
        self._load_worker.start()

    def _on_servers_loaded(self, servers):
        self._servers = servers
        self._country_button.setEnabled(servers is not None)
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
            self._reset_idle_ui()
        else:
            self._connect()

    def _reset_idle_ui(self):
        self._button.setText("Connect")
        self._status.setText("Disconnected")
        self._status.setStyleSheet("color: gray;")
        self._server_info.setText("")

    def _connect(self):
        self._button.setEnabled(False)
        self._cancel_button.show()
        self._status.setText("Connecting...")
        self._connect_worker = ConnectWorker(
            self._client, self._servers, self._selected_country, self._selected_server
        )
        self._connect_worker.connected.connect(self._on_connected)
        self._connect_worker.message.connect(self._on_message)
        self._connect_worker.cancelled.connect(self._on_cancelled)
        self._connect_worker.finished.connect(self._on_connect_finished)
        self._connect_worker.start()

    def _cancel_connect(self):
        if self._connect_worker is not None:
            self._connect_worker.cancel()

    def _on_cancelled(self):
        self._cancel_button.hide()
        self._reset_idle_ui()

    def _on_connect_finished(self):
        self._cancel_button.hide()
        self._button.setEnabled(True)

    def _on_connected(self, success, server):
        self._cancel_button.hide()
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
