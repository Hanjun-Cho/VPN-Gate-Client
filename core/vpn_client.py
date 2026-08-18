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

# how long to keep retrying before the OpenVPN management interface becomes
# reachable (either on first launch or after its socket is dropped)
MANAGEMENT_RETRIES = 60
MANAGEMENT_RETRY_DELAY = 0.5

# number of whole connection attempts before giving up; each attempt picks a
# fresh management port to avoid a transient bind conflict
MAX_CONNECT_ATTEMPTS = 3

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
        fd, self._config_path = tempfile.mkstemp(suffix=".ovpn", prefix="vpngate-")
        os.close(fd)
        try:
            return self._connect_with_retries(config, cancel_event)
        finally:
            self._remove_config()

    def _connect_with_retries(self, config, cancel_event):
        for attempt in range(MAX_CONNECT_ATTEMPTS):
            port = self._free_port()
            with open(self._config_path, "w") as file:
                file.write(config)
                file.write(f"\nmanagement 127.0.0.1 {port}\n")

            kwargs = {}
            if sys.platform.startswith("win"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            stderr_log = self._open_stderr_log()
            self._process = subprocess.Popen(
                [_find_openvpn(), "--config", self._config_path],
                stdout=subprocess.DEVNULL,
                stderr=stderr_log,
                **kwargs,
            )

            self._vpn = VPN("127.0.0.1", port)
            try:
                self._wait_for_management(cancel_event)
                return self._wait_for_tunnel(cancel_event)
            except errors.ConnectError as exc:
                self.disconnect()
                if cancel_event is not None and cancel_event.is_set():
                    raise
                if attempt < MAX_CONNECT_ATTEMPTS - 1:
                    time.sleep(1)
                    continue
                raise exc

    def _wait_for_management(self, cancel_event):
        # waits until the OpenVPN management interface is reachable; the
        # socket may take a moment to bind after the process is launched
        for _ in range(MANAGEMENT_RETRIES):
            if cancel_event is not None and cancel_event.is_set():
                self.disconnect()
                raise errors.ConnectError("Connection cancelled")
            try:
                self._vpn.connect()
                return
            except errors.ConnectError:
                time.sleep(MANAGEMENT_RETRY_DELAY)
        raise errors.ConnectError("Timed out waiting for management interface")

    def _wait_for_tunnel(self, cancel_event):
        # polls the management interface until the tunnel reports CONNECTED
        for _ in range(60):
            if cancel_event is not None and cancel_event.is_set():
                self.disconnect()
                raise errors.ConnectError("Connection cancelled")
            try:
                self._vpn.clear_cache()
                state = self._vpn.state.state_name
            except OSError:
                # the management socket can be dropped while the tunnel is
                # still establishing; re-open it so polling can continue
                # instead of failing
                self._wait_for_management(cancel_event)
                continue
            if state == "CONNECTED":
                return True
            if state in ("EXITING", "RECONNECTING"):
                raise errors.ConnectError(f"VPN failed to connect (state: {state})")
            time.sleep(1)
        raise errors.ConnectError("Timed out waiting for tunnel to establish")

    def _open_stderr_log(self):
        # captures OpenVPN's diagnostics so a genuine start failure (bad
        # config, missing binary, etc.) is not silently swallowed
        fd, path = tempfile.mkstemp(suffix=".log", prefix="vpngate-")
        os.close(fd)
        self._stderr_log_path = path
        self._stderr_log = open(path, "wb")
        return self._stderr_log

    def _remove_config(self):
        # removes the temporary config and stderr log written during connect
        stderr_log = getattr(self, "_stderr_log", None)
        if stderr_log is not None:
            try:
                stderr_log.close()
            except OSError:
                pass
            self._stderr_log = None
        for path in (getattr(self, "_config_path", None), getattr(self, "_stderr_log_path", None)):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def disconnect(self):
        # disconnects if connected to a server
        if self._vpn is not None:
            self._vpn.disconnect()
            self._vpn = None
        if self._process is not None:
            self._process.terminate()
            self._process = None
        stderr_log = getattr(self, "_stderr_log", None)
        if stderr_log is not None:
            try:
                stderr_log.close()
            except OSError:
                pass
            self._stderr_log = None

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
