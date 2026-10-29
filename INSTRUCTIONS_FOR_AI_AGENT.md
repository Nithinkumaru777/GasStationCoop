# Gas Station Simulator Co-op Mod — Setup Guide for Friend's Antigravity / AI Agent

This guide is designed for **Antigravity**, **Claude Code**, or any AI coding assistant on the friend's PC to automatically install, configure, and launch the Gas Station Simulator Co-op Client Mod.

---

## 1. System Requirements & Game Identity
- **Game**: Gas Station Simulator (Steam AppID `1149620`, Unreal Engine `4.27.2`)
- **Executable**: `GSS2\Binaries\Win64\GSS2-Win64-Shipping.exe`
- **Python**: Python 3.8+ (standard library only; no pip packages required)

---

## 2. Package Contents & Target Layout

When this package is extracted, it contains:
```
GasStationCoop_Client_Package/
├── INSTALL_MOD.bat                     <-- 1-click installer
├── START_COOP_CLIENT.bat               <-- 1-click launcher
├── gss_relay.py                        <-- 60 Hz network state broker (UDP client)
├── INSTRUCTIONS_FOR_FRIEND_ANTIGRAVITY.md
└── GSS2/
    └── Binaries/
        └── Win64/
            ├── dwmapi.dll              <-- UE4SS v3.0.1 proxy loader
            ├── UE4SS.dll               <-- UE4SS core engine
            ├── UE4SS-settings.ini       <-- Pre-configured for UE 4.27
            ├── steam_appid.txt         <-- 1149620
            ├── role.txt                <-- "guest" (commits this client to guest role)
            ├── gss_relay.py
            └── Mods/
                ├── mods.txt            <-- Enables GasStationCoop
                ├── shared/             <-- UEHelpers library
                └── GasStationCoop/
                    ├── role.txt        <-- "guest"
                    └── scripts/
                        └── main.lua    <-- Co-op sync script (Phase 6)
```

---

## 3. Automated Installation (for Antigravity / Agent)

If you are an agent running on the friend's machine:

1. **Locate Gas Station Simulator Steam install**:
   Search drives `C:`, `D:`, `E:` for `steamapps\common\Gas Station Simulator`.

2. **Copy mod files into the game**:
   Copy the contents of `GSS2\` into `<GameInstallDir>\GSS2\`:
   ```powershell
   # Example PowerShell command:
   $GameDir = "D:\Steam\steamapps\common\Gas Station Simulator"
   Copy-Item -Path ".\GSS2\*" -Destination "$GameDir\GSS2" -Recurse -Force
   Copy-Item -Path ".\START_COOP_CLIENT.bat" -Destination "$GameDir\GSS2\Binaries\Win64\" -Force
   Copy-Item -Path ".\gss_relay.py" -Destination "$GameDir\GSS2\Binaries\Win64\" -Force
   ```

3. **Verify File Placement**:
   Ensure `<GameInstallDir>\GSS2\Binaries\Win64\dwmapi.dll` and `<GameInstallDir>\GSS2\Binaries\Win64\Mods\GasStationCoop\scripts\main.lua` exist.

---

## 4. How to Connect & Play

### Step 1: Obtain Host IP Address
Ask your friend (the host) for their IP address:
- **Same Wi-Fi / LAN**: Host will give their local network IP (e.g. `192.168.x.x`).
- **Across the Internet**: Both you and your friend should join the same virtual network using **Radmin VPN** (free, no account needed), **Tailscale**, or **Hamachi**. Host will give you their VPN IP (e.g., `26.x.x.x` on Radmin).

### Step 2: Launch the Client
Either:
- Double-click `START_COOP_CLIENT.bat` in the game's `GSS2\Binaries\Win64\` folder (or desktop shortcut).
- Enter the Host's IP address when prompted.

Or run manually via terminal:
```powershell
# Terminal 1: Start Client Relay
cd "<GameInstallDir>\GSS2\Binaries\Win64"
python gss_relay.py --mode client --connect <HOST_IP> --port 7777 --netdir ".\net"

# Terminal 2: Launch Game
.\GSS2-Win64-Shipping.exe -windowed -nosplash
```

### Step 3: In-Game
- Click **Start Game** or **Load Game** in the main menu.
- As soon as you enter the station world, the mod activates:
  - Your local player position is transmitted to the Host.
  - The Host's player character model is rendered in your station.
  - The shared wallet balance is synchronized automatically.
  - Gas station customer spawners on your client are suppressed so the Host's station controls traffic and pump requests.
  - Refueling mini-games and trash pickups are synchronized!

---

## 5. Troubleshooting & Verification

1. **Did UE4SS Load?**
   Check `<GameInstallDir>\GSS2\Binaries\Win64\UE4SS.log`. It should say:
   `[GasStationCoop] Initializing Co-op Mod Probe for Gas Station Simulator...`
   `Role initialized to 'guest' from role.txt`

2. **Is Relay Connected?**
   Check the command window running `gss_relay.py`.
   Once Host is reachable, it will print:
   `[CLIENT] >>> Connected to Host! Handshake OK <<<`

3. **Firewall / Port Block**:
   If the relay cannot reach the host, ensure UDP port 7777 is not blocked by Windows Defender Firewall, or allow Python through the firewall on both machines.
