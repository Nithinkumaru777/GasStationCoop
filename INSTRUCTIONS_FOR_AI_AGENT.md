# 🤖 Instructions for AI Coding Assistants (Antigravity, Claude Code, Cursor, Windsurf)

This document provides step-by-step technical instructions for any AI assistant tasked with installing and configuring the **Gas Station Simulator Co-op Mod** on a user's machine.

---

## 🎯 Target Game Details
* **Game**: Gas Station Simulator
* **Steam AppID**: `1149620`
* **Engine**: Unreal Engine `4.27.2`
* **Executable**: `GSS2\Binaries\Win64\GSS2-Win64-Shipping.exe`

---

## 📋 Installation Steps for AI Agent

### Step 1: Locate the User's Game Directory
Query the Windows registry or standard Steam paths:
```powershell
# Common locations:
# C:\Program Files (x86)\Steam\steamapps\common\Gas Station Simulator
# D:\SteamLibrary\steamapps\common\Gas Station Simulator
# D:\steam\steamapps\common\Gas Station Simulator
```

### Step 2: Install Mod Files
Copy the contents of `GSS2\` from this repository (or from `GasStationCoop_Client_Package.zip`) directly into the game's root directory:
```
<GameRoot>\
└── GSS2\
    └── Binaries\
        └── Win64\
            ├── dwmapi.dll                   (UE4SS proxy loader)
            ├── UE4SS.dll                    (Mod engine runtime)
            ├── UE4SS-settings.ini           (Mod engine configuration)
            ├── gss_relay.py                 (Background LAN broker)
            ├── role.txt                     ('auto' default)
            └── Mods\
                ├── mods.txt                 (Load order)
                └── GasStationCoop\
                    ├── enabled.txt
                    └── scripts\
                        └── main.lua         (Co-op sync engine & in-game menu)
```

### Step 3: Verify Integrity
Ensure:
1. `role.txt` contains `auto`.
2. `dwmapi.dll` exists in `GSS2\Binaries\Win64\`.
3. `Mods\GasStationCoop\scripts\main.lua` exists.

### Step 4: Advise the User
Inform the user:
* The mod is fully installed!
* They can launch **Gas Station Simulator** normally from Steam.
* In the Main Menu:
  * To **Host**: Click **`HOST CO-OP GAME`** (or press **`F9`**).
  * To **Join**: When a friend is hosting on LAN/VPN, the menu dynamically displays **`JOIN: [FRIEND]'S GAS STATION`** (or press **`F8`**).
