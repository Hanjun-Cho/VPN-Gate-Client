import atexit
import socket
import subprocess
import tempfile
import time

from openvpn_api import VPN
from openvpn_api import errors

# launches an OpenVPN process with the given config and queries its management
# interface using the openvpn-api library
class VPNClient:
    def __init__(self):
        self._vpn = None
        self._process = None
        self._config_path = None
        atexit.register(self.cleanup)

    def cleanup(self):
        # automatically disconnects when the program stops running
        self.disconnect()

    def connect(self, config):
        self._config_path = tempfile.mktemp(suffix=".ovpn")
        port = self._free_port()
        with open(self._config_path, "w") as file:
            file.write(config)
            file.write(f"\nmanagement 127.0.0.1 {port}\n")

        self._process = subprocess.Popen(
            ["openvpn", "--config", self._config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self._vpn = VPN("127.0.0.1", port)
        for _ in range(20):
            try:
                self._vpn.connect()
                return True
            except errors.ConnectError:
                time.sleep(0.5)
        raise errors.ConnectError("Timed out waiting for management interface")

    def disconnect(self):
        # disconnects if connected to a server
        if self._vpn is not None:
            self._vpn.disconnect()
            self._vpn = None
        if self._process is not None:
            self._process.terminate()
            self._process = None

    def is_connected(self):
        return self._vpn is not None and self._vpn.is_connected

    def status(self):
        # current status of connectivity
        if not self.is_connected():
            return None
        return self._vpn.state

    @staticmethod
    def _free_port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]
