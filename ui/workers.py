import asyncio
import threading

from PySide6.QtCore import QThread, Signal

from core.servers import Servers


class LoadServersWorker(QThread):
    # emits the loaded Servers object on success, None on failure
    loaded = Signal(object)
    message = Signal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            servers = asyncio.run(Servers.create())
            self.loaded.emit(servers)
        except Exception as exc:
            self.message.emit(str(exc))
            self.loaded.emit(None)


class ConnectWorker(QThread):
    # emits True and the connected server dict on success, (False, None) otherwise
    connected = Signal(bool, object)
    message = Signal(str)
    cancelled = Signal()

    def __init__(self, client, servers, country=None, server=None):
        super().__init__()
        self._client = client
        self._servers = servers
        self._country = country
        self._server = server
        self._cancel_event = threading.Event()

    def cancel(self):
        # asks the running connection attempt to abort
        self._cancel_event.set()

    def run(self):
        try:
            server = self._server
            if server is None:
                servers = (
                    self._servers.get_servers_in_country(self._country)
                    if self._country
                    else self._servers.get_servers()
                )
                if not servers:
                    self.message.emit("No available servers")
                    self.connected.emit(False, None)
                    return
                server = servers[0]
            print(f"Connecting to {server.get('CountryLong', 'Unknown')} - {server.get('IP', 'Unknown')}")
            config = self._servers.get_server_as_config(server)
            self._client.connect(config, cancel_event=self._cancel_event)
            self.connected.emit(True, server)
        except Exception as exc:
            if self._cancel_event.is_set():
                self.cancelled.emit()
                self.connected.emit(False, None)
                return
            self.message.emit(str(exc))
            self.connected.emit(False, None)
