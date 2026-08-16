import asyncio

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

    def __init__(self, client, servers):
        super().__init__()
        self._client = client
        self._servers = servers

    def run(self):
        try:
            if not self._servers.get_servers():
                self.message.emit("No available servers")
                self.connected.emit(False, None)
                return
            server = self._servers.get_servers()[0]
            print(f"Connecting to {server.get('CountryLong', 'Unknown')} - {server.get('IP', 'Unknown')}")
            config = self._servers.get_server_as_config(server)
            self._client.connect(config)
            self.connected.emit(True, server)
        except Exception as exc:
            self.message.emit(str(exc))
            self.connected.emit(False, None)
