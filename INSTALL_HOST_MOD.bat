@echo off
setlocal enabledelayedexpansion
title Gas Station Simulator Co-op Mod - Host Installer
color 0A
cls
echo ============================================================
echo   GAS STATION SIMULATOR CO-OP - HOST INSTALLER
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
    pause
    exit /b 1
)

echo.
echo [1/3] Copying UE4SS and Co-op Mod files...
xcopy /E /I /Y "%~dp0GSS2" "%GSS_DIR%\GSS2" >nul

echo [2/3] Setting Host Role...
echo host > "%GSS_DIR%\GSS2\Binaries\Win64\role.txt"

echo [3/3] Copying Host Launcher and Relay...
copy /Y "%~dp0START_COOP_SERVER.bat" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0gss_relay.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul

set DESKTOP_DIR=%USERPROFILE%\Desktop
echo @echo off > "%DESKTOP_DIR%\Start GSS Co-op (Host Server).bat"
echo cd /d "%GSS_DIR%\GSS2\Binaries\Win64" >> "%DESKTOP_DIR%\Start GSS Co-op (Host Server).bat"
echo call START_COOP_SERVER.bat >> "%DESKTOP_DIR%\Start GSS Co-op (Host Server).bat"

echo.
echo ============================================================
echo  [HOST INSTALL COMPLETE!]
echo  A shortcut named "Start GSS Co-op (Host Server).bat"
echo  has been created on your Desktop!
echo.
echo  To host:
echo  1. Double-click the desktop shortcut.
echo  2. Send your IP to your friend.
echo  3. Load your save and play together!
echo ============================================================
echo.
pause
