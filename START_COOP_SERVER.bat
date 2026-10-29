@echo off
setlocal enabledelayedexpansion
title Gas Station Simulator - Co-op Server (Host)
color 0A
cls
echo ============================================================
echo   GAS STATION SIMULATOR CO-OP - HOST / SERVER LAUNCHER
echo ============================================================
echo.

:: Get IP using python
for /f "tokens=*" %%i in ('python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2^>nul') do set LOCAL_IP=%%i
if "%LOCAL_IP%"=="" set LOCAL_IP=127.0.0.1

echo [HOST IP] Your Local Network IP is: %LOCAL_IP%
echo.
echo ------------------------------------------------------------
echo  CONNECTION GUIDE FOR YOUR FRIEND:
echo  * If on the SAME Wi-Fi / Local Network:
echo    Give your friend this IP: %LOCAL_IP%
echo.
echo  * If playing over the INTERNET (different houses):
echo    Connect via Radmin VPN, Hamachi, or Tailscale,
echo    and give your friend your VPN IP address.
echo ------------------------------------------------------------
echo.
echo [1/2] Starting Co-op Network Relay (Port 7777 UDP)...
start "GSS Co-op Relay [HOST]" python "C:\anitgravity fix\fix anything\coop-anything\games\gas-station-simulator\tools\gss_relay.py" --mode host --port 7777 --netdir "D:\coop-sandbox\gss\A\GSS2\Binaries\Win64\net"

echo [2/2] Launching Host Game Sandbox A...
start "" powershell -NoProfile -ExecutionPolicy Bypass -File "C:\anitgravity fix\fix anything\coop-anything\local\gas-station-simulator\launch.ps1" A

echo.
echo ============================================================
echo  HOST SERVER IS RUNNING!
echo  1. Load or Start your game in the Gas Station window.
echo  2. Have your friend start their game and connect to:
echo     %LOCAL_IP%
echo ============================================================
echo.
pause
