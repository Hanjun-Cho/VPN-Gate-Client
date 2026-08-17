import atexit
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

from openvpn_api import VPN
from openvpn_api import errors

# resolves the path to the openvpn executable, which is not always on PATH
# (particularly on Windows). Honors an explicit override via the
# OPENVPN_PATH environment variable.
def _find_openvpn():
    env_path = os.environ.get("OPENVPN_PATH")
    if env_path:
        return env_path

    which = shutil.which("openvpn")
    if which:
        return which

    if sys.platform.startswith("win"):
        candidates = [
            r"C:\Program Files\OpenVPN\bin\openvpn.exe",
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate

    raise FileNotFoundError(
        "Could not locate the OpenVPN executable. "
        "Set the OPENVPN_PATH environment variable to its full path."
    )

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

    def connect(self, config, cancel_event=None):
        self._config_path = tempfile.mktemp(suffix=".ovpn")
        port = self._free_port()
        with open(self._config_path, "w") as file:
            file.write(config)
            file.write(f"\nmanagement 127.0.0.1 {port}\n")

        kwargs = {}
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        self._process = subprocess.Popen(
            [_find_openvpn(), "--config", self._config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )

        self._vpn = VPN("127.0.0.1", port)
        for _ in range(60):
            if cancel_event is not None and cancel_event.is_set():
                self.disconnect()
                raise errors.ConnectError("Connection cancelled")
            try:
                self._vpn.connect()
                break
            except errors.ConnectError:
                time.sleep(0.5)
        else:
            raise errors.ConnectError("Timed out waiting for management interface")

        for _ in range(60):
            if cancel_event is not None and cancel_event.is_set():
                self.disconnect()
                raise errors.ConnectError("Connection cancelled")
            try:
                self._vpn.clear_cache()
                state = self._vpn.state.state_name
            except OSError:
                self._reconnect_management()
                continue
            if state == "CONNECTED":
                return True
            if state in ("EXITING", "RECONNECTING"):
                raise errors.ConnectError(f"VPN failed to connect (state: {state})")
            time.sleep(1)
        raise errors.ConnectError("Timed out waiting for tunnel to establish")

    def _reconnect_management(self):
        # the management socket can be dropped while the tunnel is still
        # establishing; re-open it so polling can continue instead of failing
        for _ in range(3):
            try:
                self._vpn.connect()
                return
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
        if self._vpn is None:
            return False
        try:
            self._vpn.clear_cache()
            return self._vpn.state.state_name == "CONNECTED"
        except (errors.ConnectError, errors.NotConnectedError, OSError):
            return False

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
