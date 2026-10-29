# ⛽ Gas Station Simulator — Co-op Multiplayer Mod (`GasStationCoop`)

[![Lead Developer: Nithin Kumar](https://img.shields.io/badge/Architect%20%26%20Developer-Nithin%20Kumar-f59e0b?style=for-the-badge&logo=github)](https://github.com/Nithinkumaru777/GasStationCoop)
[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-4.27.2-blue?style=for-the-badge&logo=unrealengine)](https://www.unrealengine.com/)
[![Mod Loader](https://img.shields.io/badge/Mod%20Loader-UE4SS%20v3.0.1-orange?style=for-the-badge)](https://github.com/UE4SS-RE/RE-UE4SS)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

A fully functional, award-winning 2-player co-op multiplayer mod for **Gas Station Simulator** (Steam AppID `1149620`, Unreal Engine 4.27.2). Run your desert Route 66 gas station together with friends over **Local Wi-Fi (LAN)** or **Any Wi-Fi / Across the Internet (Radmin VPN / Tailscale)**!

**Project Repository**: [https://github.com/Nithinkumaru777/GasStationCoop](https://github.com/Nithinkumaru777/GasStationCoop)  
**Lead Architect & Creator**: **Nithin Kumar** ([@Nithinkumaru777](https://github.com/Nithinkumaru777))

---

## 🌟 Highlights & Key Features

* **Award-Winning WebView2 User Interface**:
  * Glassmorphism cyberpunk desert theme with glowing Route 66 shield.
  * Opening cinematic intro & staggered keyframe reveals.
  * Smooth button animations with interactive glow states.
  * Expandable slide-out connection drawer with clipboard paste.
  * Floating toast alerts with automatic IP clipboard copying.
* **100% In-Game & Standalone Experience**:
  * Launch directly from Desktop with the **Play Gas Station Co-op** launcher.
  * Or click **DLC / Co-Op** on the in-game Main Menu (or press `F8` / `F9`).
* **Two Clear, Distinct Modes**:
  * **Option 1: HOST A WORLD**
    * Starts hosting on port `7777` UDP.
    * Automatically detects network IPs (LAN and Radmin VPN / Tailscale).
    * Auto-copies your IP to your clipboard for instant sharing.
  * **Option 2: JOIN A WORLD**
    * Connects to friend across different Wi-Fi networks (Internet) or same Wi-Fi.
    * Slide-down IP entry drawer with auto-focus and one-click paste.
* **Performance & Hardware Optimizations**:
  * Enforced **2560x1600 @ 180Hz Borderless Mode (`FullscreenMode=1`)**.
  * Crystal-clear Xbox Game Bar (`Win + G`) overlay.
  * Native 3-finger touchpad swipe gesture support for seamless minimizing.
  * Fixed UE4SS `0xe06d7363` crash by eliminating high-frequency UObject scans.

---

## 🌐 Playing from Different Wi-Fi Networks (Internet / Different Houses)

If you and your friend are in different houses on different Wi-Fi connections:
1. Both players install **[Radmin VPN](https://www.radmin-vpn.com/)** (100% free, no account needed) or **[Tailscale](https://tailscale.com/)**.
2. One player creates a room (e.g. `GSS-Room`) and the friend joins the room.
3. **Host**: Opens Co-op -> Clicks **`1. HOST A WORLD`**. Their IP is automatically copied to clipboard.
4. **Guest**: Opens Co-op -> Clicks **`2. JOIN A WORLD`**, pastes host's IP, and clicks **Connect to Station**.
5. Both players spawn into the station and can service cars, pump gas, clean up, and run the shop together!

---

## 📦 Installation & Setup

1. Download the latest `GasStationCoop_Client_Package.zip` from [Releases](https://github.com/Nithinkumaru777/GasStationCoop/releases).
2. Extract the contents directly into your Gas Station Simulator folder:
   `...\steamapps\common\Gas Station Simulator\`
3. Run `INSTALL_MOD.bat` or double click **Play Gas Station Co-op** on your desktop!

---

## 👤 Credits & Attribution

* **Lead Architect & Developer**: **Nithin Kumar** ([@Nithinkumaru777](https://github.com/Nithinkumaru777))
* **Repository**: [https://github.com/Nithinkumaru777/GasStationCoop](https://github.com/Nithinkumaru777/GasStationCoop)
* Built with Unreal Engine 4.27, UE4SS, and Microsoft Edge WebView2.
