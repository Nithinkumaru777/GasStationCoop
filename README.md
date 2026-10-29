# ⛽ Gas Station Simulator — Co-op Multiplayer Mod (`GasStationCoop`)

[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-4.27.2-blue?logo=unrealengine)](https://www.unrealengine.com/)
[![Mod Loader](https://img.shields.io/badge/UE4SS-v3.0.1-orange)](https://github.com/UE4SS-RE/RE-UE4SS)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2064--bit-lightgrey)](https://store.steampowered.com/app/1149620/Gas_Station_Simulator/)

A fully functional 2-player co-op multiplayer mod for **Gas Station Simulator** (Steam AppID `1149620`, UE 4.27.2). Run your desert gas station together with a friend over Local LAN or the Internet!

---

## 🌟 Co-op Features

* **Real-time Player Visualization**: Both players see each other in 3D with full position and rotation streaming at 30 Hz.
* **Shared Station Economy & Wallet**: Host-authoritative financial balance synced to the cent in real time.
* **Fueling Subsystem Sync**: Minigame completion and customer pump servicing are replicated between players.
* **Cash Register Mutual Exclusion**: Lock mechanism ensures players take turns at the checkout counter without colliding.
* **Station Cleaning & Maintenance**: Picking up trash or cleaning graffiti removes it synchronously on both screens.
* **Customer Traffic Authority**: Host manages customer car queues and spawner timing; client spawners are suppressed to avoid duplicate traffic.
* **Zero Engine Crashes**: Built on an out-of-process 60 Hz state broker that bypasses shipping game map-travel limitations.

---

## ⚡ Quick Start for Players

### For the Host (Server)
1. Clone or download this repository.
2. Double-click **`START_COOP_SERVER.bat`**.
3. It will display your **IP address** (e.g., `192.168.0.x` for LAN, or your Radmin VPN / Tailscale IP for Internet play).
4. Share that IP with your friend.
5. In the game window, click **Continue** or **New Game** — your station is now ready for your friend!

---

### For the Friend (Client)
1. Download **[`GasStationCoop_Client_Package.zip`](https://github.com/Nithinkumaru777/GasStationCoop/releases/latest)** from Releases.
2. Extract the ZIP anywhere on your PC.
3. Double-click **`INSTALL_MOD.bat`** (it automatically detects your Steam game folder and installs the mod files).
4. Double-click **`START_COOP_CLIENT.bat`**, enter your friend's Host IP, and hit Enter.
5. In the game window, click **Start Game** or **Load Game** — you will spawn into your friend's station!

---

## 🤖 1-Click Setup for AI Assistants (Antigravity / Claude Code / Cursor)

If your friend has an AI coding assistant (like **Antigravity**, **Claude Code**, or **Cursor**), they can simply give this prompt to their AI:

```markdown
I want to install the Gas Station Simulator Co-op Mod.
Repository: https://github.com/Nithinkumaru777/GasStationCoop

Please set up the mod for me:
1. Locate my Steam installation of Gas Station Simulator (AppID 1149620).
2. Download or copy the GSS2 mod files and START_COOP_CLIENT.bat into my GSS2\Binaries\Win64 folder.
3. Verify that role.txt is set to 'guest' and dwmapi.dll is installed.
4. Launch START_COOP_CLIENT.bat so I can connect to my friend's Host IP.
```

The AI assistant can read [`INSTRUCTIONS_FOR_AI_AGENT.md`](INSTRUCTIONS_FOR_AI_AGENT.md) in this repo for detailed technical instructions.

---

## 🌐 Playing Over the Internet (Different Locations)

If you and your friend are on different Wi-Fi networks (different houses):
1. Both of you download and open **[Radmin VPN](https://www.radmin-vpn.com/)** (free, no account required) or **[Tailscale](https://tailscale.com/)**.
2. One player creates a network (e.g., "GSS-Coop"), and the other joins it.
3. The host shares their **Radmin/Tailscale IP address** (e.g. `26.x.x.x`).
4. The friend enters that IP into `START_COOP_CLIENT.bat`.

---

## 🛠️ Architecture & Technical Details

Gas Station Simulator (`GSS2-Win64-Shipping.exe`) inherits `AGSS2GameMode` from single-player `AGameModeBase`, which omits native shipping listen-server socket bindings across level travel.

`GasStationCoop` implements a twin-tier architecture:
1. **In-Process Mod Hook (UE4SS v3.0.1 Lua)**:
   - Injected via proxy `dwmapi.dll`.
   - Hooks player location, rotation, and subsystem events (`FuelMiniGame_C`, `00_TrashItem_C`, `CashShop`).
   - Reads/writes state from local `net/` directory.
2. **High-Speed Network Broker (`gss_relay.py`)**:
   - Out-of-process Python daemon running at 60 Hz.
   - Transmits position buffers (`POS:`) and event deltas (`EVT:`) over zero-drop UDP.
   - Supports `--mode host` (server), `--mode client` (guest), and `--mode local` (single-PC twin-instance testing).

---

## 📄 License
This project is released under the [MIT License](LICENSE).
Gas Station Simulator is copyright © DRAGO entertainment / Movie Games S.A. This mod is an unofficial community project and does not modify core game binaries.
