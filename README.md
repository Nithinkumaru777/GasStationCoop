# ⛽ Gas Station Simulator — Co-op Multiplayer Mod (`GasStationCoop`)

[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-4.27.2-blue?logo=unrealengine)](https://www.unrealengine.com/)
[![Mod Loader](https://img.shields.io/badge/UE4SS-v3.0.1-orange)](https://github.com/UE4SS-RE/RE-UE4SS)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2064--bit-lightgrey)](https://store.steampowered.com/app/1149620/Gas_Station_Simulator/)

A fully functional 2-player co-op multiplayer mod for **Gas Station Simulator** (Steam AppID `1149620`, UE 4.27.2). Run your desert gas station together with friends over **Same Wi-Fi (LAN)** or **Different Wi-Fi (Internet / VPN)**!

---

## 🎮 100% In-Game Experience — Two Clear Options

**No batch files or console commands required!** When you launch Gas Station Simulator from Steam, click the **`CO-OP: HOST OR JOIN`** button on the Main Menu to see two distinct options:

### 🏠 Option 1: HOST A WORLD (or press `F9`)
* Starts hosting your gas station world on port `7777`.
* Automatically detects your network IP (LAN and Radmin VPN / Tailscale).
* **Automatically copies your IP to your clipboard!**
* Displays your IP on-screen: just press `Ctrl + V` in Discord/WhatsApp to send it to your friend!
* Loads your station so it's open and ready for your friend.

### 🌐 Option 2: JOIN A WORLD (or press `F8`)
* Works across **different Wi-Fi networks** (different houses) as well as the same Wi-Fi!
* Pops up a clean IP dialog box: enter or paste your friend's Host IP (e.g. Radmin VPN `26.x.x.x`, Tailscale, or LAN `192.168.x.x`).
* Pre-fills with the last used IP so you only need to type it once!
* Clicks OK and you instantly spawn into your friend's gas station!

---

## 🌐 How to Play from Different Wi-Fi (Different Houses)

If you and your friend are in different houses on different Wi-Fi:
1. Both of you download **[Radmin VPN](https://www.radmin-vpn.com/)** (100% free, no account needed) or **[Tailscale](https://tailscale.com/)**.
2. One person clicks **Create Network** (e.g., name it `GSS-Room`) and the other clicks **Join Network**.
3. **Host**: Opens Gas Station Simulator -> Clicks **`HOST A WORLD`** (or presses `F9`). Their Radmin IP (e.g. `26.104.55.88`) is copied to clipboard. Host pastes it to the friend.
4. **Friend**: Opens Gas Station Simulator -> Clicks **`JOIN A WORLD`** (or presses `F8`). Pastes the host's IP and clicks OK.
5. Boom! You are both running the gas station together over the internet!

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

## ⚡ 1-Click Setup for Any Player (Host or Guest)

1. Download **[`GasStationCoop_Client_Package.zip`](https://github.com/Nithinkumaru777/GasStationCoop/releases/latest)** from Releases.
2. Extract the ZIP anywhere on your PC.
3. Double-click **`INSTALL_MOD.bat`** (it automatically detects your Steam game folder and installs the mod files).
4. Launch Gas Station Simulator through Steam!
5. In the Main Menu, click **`CO-OP: HOST OR JOIN`**:
   - Click **`HOST A WORLD`** to host.
   - Click **`JOIN A WORLD`** to join your friend from any Wi-Fi.

---

## ⌨️ In-Game Hotkeys

| Hotkey | Action |
|---|---|
| **F9** | **Option 1: HOST A WORLD** (Starts server, copies IP to clipboard, enters station) |
| **F8** | **Option 2: JOIN A WORLD** (Pops up IP prompt to connect from any Wi-Fi) |
| **F7** | Dump World & Player State to console |
| **F6** | Re-run SDK Dumper |

---

## 📄 License
This project is released under the [MIT License](LICENSE).
Gas Station Simulator is copyright © DRAGO entertainment / Movie Games S.A. This mod is an unofficial community project and does not modify core game binaries.
