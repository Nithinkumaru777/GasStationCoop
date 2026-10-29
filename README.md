# ⛽ Gas Station Simulator — Co-op Multiplayer Mod (`GasStationCoop`)

[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-4.27.2-blue?logo=unrealengine)](https://www.unrealengine.com/)
[![Mod Loader](https://img.shields.io/badge/UE4SS-v3.0.1-orange)](https://github.com/UE4SS-RE/RE-UE4SS)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2064--bit-lightgrey)](https://store.steampowered.com/app/1149620/Gas_Station_Simulator/)

A fully functional 2-player co-op multiplayer mod for **Gas Station Simulator** (Steam AppID `1149620`, UE 4.27.2). Run your desert gas station together with friends over Local LAN or the Internet!

---

## 🎮 100% In-Game Experience (Minecraft-Style Auto-Detect)

**No batch files, command lines, or manual IP typing required!** Both you and your friends can host or join directly from inside the game menu:

1. **Launch the Game normally** from Steam or desktop.
2. **To Host**:
   - In the Main Menu, click **`HOST CO-OP GAME`** (or press **`F9`**).
   - Your station opens for co-op and begins broadcasting to your LAN/VPN!
3. **To Join**:
   - When your friend is hosting, open your game.
   - The Main Menu automatically detects their server and displays:  
     👉 **`JOIN: [FRIEND]'S GAS STATION`** (e.g. `JOIN: NITHIN'S GAS STATION`).
   - Click it (or press **`F8`**) and you instantly join their gas station!

---

## 🌟 Co-op Features

* **Minecraft-Style LAN Discovery**: Background UDP beacon auto-detects games on your local network or virtual LAN (Radmin VPN / Tailscale / Hamachi) in under 10 milliseconds.
* **In-Game Main Menu Integration**: Directly embedded buttons and on-screen HUD banners inside Gas Station Simulator's Main Menu.
* **Real-time Player Visualization**: Both players see each other in 3D with full position and rotation streaming at 30 Hz.
* **Shared Station Economy & Wallet**: Host-authoritative financial balance synced to the cent in real time.
* **Fueling Subsystem Sync**: Minigame completion and customer pump servicing are replicated between players.
* **Cash Register Mutual Exclusion**: Lock mechanism ensures players take turns at the checkout counter without colliding.
* **Station Cleaning & Maintenance**: Picking up trash or cleaning graffiti removes it synchronously on both screens.
* **Customer Traffic Authority**: Host manages customer car queues and spawner timing; client spawners are suppressed to avoid duplicate traffic.
* **Zero Engine Crashes**: Built on an out-of-process 60 Hz state broker that bypasses shipping game map-travel limitations.

---

## ⚡ 1-Click Setup for Friends & Other Players

### For Any Player (You or Your Friends)
1. Download **[`GasStationCoop_Client_Package.zip`](https://github.com/Nithinkumaru777/GasStationCoop/releases/latest)** from Releases.
2. Extract the ZIP anywhere on your PC.
3. Double-click **`INSTALL_MOD.bat`** (it automatically detects your Steam game folder and installs the mod files).
4. Launch Gas Station Simulator through Steam!
5. In the Main Menu:
   - Click **`HOST CO-OP GAME`** to host your station.
   - Or click **`JOIN: [HOST]'S GAS STATION`** to join your friend!

---

## 🤖 1-Click Setup for AI Assistants (Antigravity / Claude Code / Cursor)

If your friend has an AI assistant, they can simply send this prompt to their assistant:

```markdown
I want to install the Gas Station Simulator Co-op Mod.
Repository: https://github.com/Nithinkumaru777/GasStationCoop

Please set up the mod for me:
1. Locate my Steam installation of Gas Station Simulator (AppID 1149620).
2. Download or copy the GSS2 mod files into my GSS2\Binaries\Win64 folder.
3. Verify that dwmapi.dll and UE4SS are installed.
4. Launch the game from Steam — co-op auto-detection and in-game Host/Join buttons are ready in the Main Menu!
```

Detailed instructions for AI assistants can be found in [`INSTRUCTIONS_FOR_AI_AGENT.md`](INSTRUCTIONS_FOR_AI_AGENT.md).

---

## 🌐 Playing Over the Internet (Different Locations)

If you and your friend are on different Wi-Fi networks:
1. Both of you download and open **[Radmin VPN](https://www.radmin-vpn.com/)** (free, no sign-up) or **[Tailscale](https://tailscale.com/)**.
2. Join the same virtual room (e.g., "GSS-Coop").
3. Launch the game — Minecraft-style LAN auto-discovery works automatically over Radmin/Tailscale!

---

## ⌨️ In-Game Hotkeys

| Hotkey | Action |
|---|---|
| **F9** | **Host Co-op Game** (Commits to Host role & loads station) |
| **F8** | **Join Co-op Game** (Connects to detected LAN/VPN server) |
| **F7** | Dump World & Player State to console |
| **F6** | Re-run SDK Dumper |

---

## 🛠️ Architecture & Technical Details

Gas Station Simulator (`GSS2-Win64-Shipping.exe`) inherits `AGSS2GameMode` from single-player `AGameModeBase`, which omits native shipping listen-server socket bindings across level travel.

`GasStationCoop` implements a twin-tier architecture:
1. **In-Process Mod Hook (UE4SS v3.0.1 Lua)**:
   - Injected via proxy `dwmapi.dll`.
   - Hijacks main menu buttons and draws on-screen discovery HUD.
   - Hooks player location, rotation, and subsystem events (`FuelMiniGame_C`, `00_TrashItem_C`, `CashShop`).
   - Reads/writes state from local `net/` directory.
2. **High-Speed Network Broker (`gss_relay.py`)**:
   - Out-of-process Python daemon running in the background.
   - Broadcasts presence beacons and answers discovery probes (`GSS_BEACON` / `GSS_DISCOVER` / `GSS_OFFER`).
   - Transmits position buffers (`POS:`) and event deltas (`EVT:`) over zero-drop UDP.

---

## 📄 License
This project is released under the [MIT License](LICENSE).
Gas Station Simulator is copyright © DRAGO entertainment / Movie Games S.A. This mod is an unofficial community project and does not modify core game binaries.
