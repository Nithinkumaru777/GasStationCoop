@echo off
setlocal enabledelayedexpansion
title Gas Station Simulator - Co-op Client (Join Friend)
color 0B
cls
echo ============================================================
echo   GAS STATION SIMULATOR CO-OP - CLIENT / GUEST LAUNCHER
echo ============================================================
echo.

set HOST_IP=
if exist "%~dp0host_ip.txt" (
    set /p HOST_IP=<"%~dp0host_ip.txt"
)

if "!HOST_IP!"=="" (
    set /p HOST_IP="Enter your Friend's (Host) IP Address: "
    echo !HOST_IP!>"%~dp0host_ip.txt"
) else (
    echo Using saved Host IP: !HOST_IP!
    echo (To connect to a different IP, edit or delete "%~dp0host_ip.txt")
    echo.
)

if "!HOST_IP!"=="" (
    echo [ERROR] No Host IP provided. Exiting.
    pause
    exit /b 1
)

echo.
echo [1/2] Starting Co-op Client Network Relay connecting to !HOST_IP!:7777 (UDP)...
start "GSS Co-op Relay [CLIENT]" python "%~dp0gss_relay.py" --mode client --connect !HOST_IP! --port 7777 --netdir "%~dp0net"

echo [2/2] Launching Gas Station Simulator...
if exist "%~dp0GSS2-Win64-Shipping.exe" (
    start "" "%~dp0GSS2-Win64-Shipping.exe" -windowed -nosplash
) else (
    echo Launching via Steam...
    start steam://rungameid/1149620
)

echo.
echo ============================================================
echo  CLIENT CONNECTED!
echo  When the game opens, click Start or Load game.
echo  Your player will automatically connect and sync with Host!
echo ============================================================
echo.
pause
