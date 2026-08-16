# VPN Gate Client

A desktop application for connecting to public VPN servers from the
[VPN Gate](https://www.vpngate.net/) network. It fetches the list of available
servers, checks which ones are reachable, and lets you connect to one with a
single click. Currently it automatically connects to a server in Japan.

## Installation

Download the latest release from the [Releases page](../../releases) and
install or extract the files provided there.

## Usage

1. Install [OpenVPN](https://openvpn.net/community-downloads/) (OpenVPN GUI /
   the installer). This is required because the app launches the `openvpn.exe`
   binary to establish the connection.

2. Extract the `VPNServerManager.zip` file to a folder of your choice.

3. Run `VPNServerManager.exe`. On Windows, allow the User Account Control (UAC)
   prompt so the app can set up the VPN connection.

4. Click **Connect**. The app will connect to a Japanese server and show the
   country and IP you are connected to.
