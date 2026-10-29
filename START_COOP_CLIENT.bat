@echo off
setlocal enabledelayedexpansion
title Gas Station Simulator - Co-op Client (Auto-Connect)
color 0B
cls
echo ============================================================
echo   GAS STATION SIMULATOR CO-OP - AUTO-CONNECT CLIENT
echo ============================================================
echo.
echo Searching for your friend's Host Server on the network...
echo (Minecraft-style zero-setup auto-discovery)
echo.

set TARGET_DIR=%~dp0GSS2\Binaries\Win64
if not exist "%TARGET_DIR%" set TARGET_DIR=%~dp0

echo [1/2] Launching Gas Station Simulator...
if exist "%TARGET_DIR%\GSS2-Win64-Shipping.exe" (
    start "" "%TARGET_DIR%\GSS2-Win64-Shipping.exe" -windowed -nosplash
) else (
    start steam://rungameid/1149620
)

echo [2/2] Starting Auto-Connect Network Relay...
python "%TARGET_DIR%\gss_relay.py" --mode auto --port 7777 --netdir "%TARGET_DIR%\net"

pause
