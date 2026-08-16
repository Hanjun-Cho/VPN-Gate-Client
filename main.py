import asyncio

from core.servers import Servers

async def main():
    servers = await Servers.create()
    print(servers.get_countries())
    print(servers.get_servers_in_country('Japan'))

asyncio.run(main())
