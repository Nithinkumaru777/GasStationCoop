@echo off
setlocal enabledelayedexpansion
title Gas Station Simulator Co-op Mod - 1-Click Installer
color 0A
cls
echo ============================================================
echo   GAS STATION SIMULATOR CO-OP MULTIPLAYER - 1-CLICK INSTALLER
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
echo [1/4] Copying UE4SS and Co-op Mod files...
xcopy /E /I /Y "%~dp0GSS2" "%GSS_DIR%\GSS2" >nul

echo [2/4] Installing Starter Station Save (Enables Instant Level Entry)...
if not exist "%LOCALAPPDATA%\GSS2\Saved\SaveGames" mkdir "%LOCALAPPDATA%\GSS2\Saved\SaveGames"
if not exist "%GSS_DIR%\GSS2\Saved\SaveGames" mkdir "%GSS_DIR%\GSS2\Saved\SaveGames"
if exist "%~dp0SaveGames" (
    copy /Y "%~dp0SaveGames\*.sav" "%LOCALAPPDATA%\GSS2\Saved\SaveGames\" >nul
    copy /Y "%~dp0SaveGames\*.sav" "%GSS_DIR%\GSS2\Saved\SaveGames\" >nul
)

echo [3/4] Installing Route 66 Launcher & Background Relay...
copy /Y "%~dp0play_coop.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0coop_menu.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0gss_relay.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0play_coop.py" "%GSS_DIR%\" >nul
copy /Y "%~dp0coop_menu.py" "%GSS_DIR%\" >nul
copy /Y "%~dp0gss_relay.py" "%GSS_DIR%\" >nul

echo [4/4] Creating Desktop Shortcut...
set DESKTOP_DIR=%USERPROFILE%\Desktop
echo @echo off > "%DESKTOP_DIR%\Play Gas Station Co-op.bat"
echo cd /d "%GSS_DIR%\GSS2\Binaries\Win64" >> "%DESKTOP_DIR%\Play Gas Station Co-op.bat"
echo start "" pythonw play_coop.py >> "%DESKTOP_DIR%\Play Gas Station Co-op.bat"

echo.
echo ============================================================
echo   ✨ INSTALLATION COMPLETE! CO-OP MOD IS READY! ✨
echo ============================================================
echo.
echo How to play:
echo   1. Launch Gas Station Simulator through Steam normally!
echo   2. In the Main Menu:
echo      - To Host: Click "HOST CO-OP GAME" (or press F9)
echo      - To Join: When your friend hosts, click "JOIN SERVER" (or press F8)
echo.
echo Have fun running your gas station together!
echo.
pause
