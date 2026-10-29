@echo off
setlocal enabledelayedexpansion
title Gas Station Simulator Co-op Mod - 1-Click Installer
color 0E
cls
echo ============================================================
echo   GAS STATION SIMULATOR CO-OP - CLIENT INSTALLER
echo ============================================================
echo.

set GSS_DIR=

:: Check common Steam library paths
for %%D in (C D E F G H) do (
    if exist "%%D:\SteamLibrary\steamapps\common\Gas Station Simulator\GSS2\Binaries\Win64" (
        set "GSS_DIR=%%D:\SteamLibrary\steamapps\common\Gas Station Simulator"
    )
    if exist "%%D:\Program Files (x86)\Steam\steamapps\common\Gas Station Simulator\GSS2\Binaries\Win64" (
        set "GSS_DIR=%%D:\Program Files (x86)\Steam\steamapps\common\Gas Station Simulator"
    )
    if exist "%%D:\Steam\steamapps\common\Gas Station Simulator\GSS2\Binaries\Win64" (
        set "GSS_DIR=%%D:\Steam\steamapps\common\Gas Station Simulator"
    )
)

if "%GSS_DIR%"=="" (
    echo [INFO] Could not auto-detect Steam folder.
    echo Please enter the path where Gas Station Simulator is installed.
    echo Example: D:\Steam\steamapps\common\Gas Station Simulator
    echo.
    set /p GSS_DIR="Install Path: "
)

echo.
echo Installing into: %GSS_DIR%
if not exist "%GSS_DIR%\GSS2\Binaries\Win64" (
    echo [ERROR] Invalid folder! Could not find GSS2\Binaries\Win64.
    echo Please make sure you selected the main "Gas Station Simulator" folder.
    pause
    exit /b 1
)

echo.
echo [1/3] Copying UE4SS and Co-op Mod files...
xcopy /E /I /Y "%~dp0GSS2" "%GSS_DIR%\GSS2" >nul

echo [2/3] Copying Network Relay and Launchers...
copy /Y "%~dp0START_COOP_CLIENT.bat" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0gss_relay.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul

echo [3/3] Creating Desktop Shortcut...
set DESKTOP_DIR=%USERPROFILE%\Desktop
echo @echo off > "%DESKTOP_DIR%\Play GSS Co-op (Join Friend).bat"
echo cd /d "%GSS_DIR%\GSS2\Binaries\Win64" >> "%DESKTOP_DIR%\Play GSS Co-op (Join Friend).bat"
echo call START_COOP_CLIENT.bat >> "%DESKTOP_DIR%\Play GSS Co-op (Join Friend).bat"

echo.
echo ============================================================
echo  [INSTALL COMPLETE!]
echo  A shortcut named "Play GSS Co-op (Join Friend).bat"
echo  has been created on your Desktop!
echo.
echo  To play:
echo  1. Get the Host IP from your friend.
echo  2. Double-click the desktop shortcut.
echo  3. Enter the IP, and enjoy co-op!
echo ============================================================
echo.
pause
