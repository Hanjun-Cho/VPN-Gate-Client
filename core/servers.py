import asyncio
import base64
import csv
import io
import subprocess
import sys
import urllib.request

class Servers:
    def __init__(self):
        self.servers = []
        self.countries = []
        self.initialized = False

    @classmethod
    async def create(cls):
        self = cls()

        self.servers = await self.get_server_list()
        self.countries = await self.get_countries_available()
        self.initialized = True

        return self

    # parses CSV list at https://www.vpngate.net/api/iphone/
    async def get_server_list(self):
        print("Retrieving All VPN Servers...")

        url = "https://www.vpngate.net/api/iphone/"
        with urllib.request.urlopen(url) as response:
            text = response.read().decode("utf-8")
        text = text.split("\n", 1)[1]
        text = text.replace("#HostName", "HostName", 1)
        rows = list(csv.DictReader(io.StringIO(text)))

        print("Checking VPN Server Availability...")
        results = await asyncio.gather(
            *(asyncio.to_thread(self.is_server_available, row["IP"]) for row in rows)
        )
        return [row for row, available in zip(rows, results) if available]

    # gets a list of servers and prints the list of countries with available servers
    async def get_countries_available(self):
        return sorted({server["CountryLong"] for server in self.servers if server["CountryLong"]})

    # gets all available servers from given country
    def get_servers_in_country(self, country):
        return [server for server in self.servers if server["CountryLong"] == country]

    # pings IP to check if server is reachable
    def is_server_available(self, ip):
        if not ip:
            return False
        if sys.platform.startswith("win"):
            cmd = ["ping", "-n", "2", "-w", "1000", ip]
        else:
            cmd = ["ping", "-c", "2", "-W", "1", ip]
        result = subprocess.run(cmd,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0

    # from the given server decode the 'OpenVPN_ConfigData_Base64' and save as config.ovpn file
    def get_server_as_config(self, server):
        config_data = base64.b64decode(server["OpenVPN_ConfigData_Base64"]).decode("utf-8")
        with open("config.ovpn", "w") as file:
            file.write(config_data)
        return config_data

    def get_servers(self):
        return self.servers

    def get_countries(self):
        return self.countries

    def is_initialized(self):
        return self.initialized
