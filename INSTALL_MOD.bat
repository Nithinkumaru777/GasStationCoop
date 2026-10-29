@echo off
setlocal enabledelayedexpansion
title Gas Station Simulator Co-op Mod - 1-Click Installer
color 0E
cls
echo ============================================================
echo   GAS STATION SIMULATOR CO-OP - MOD INSTALLER
echo   Lead Architect & Creator: Nithin Kumar (@Nithinkumaru777)
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
echo [1/5] Copying UE4SS and Co-op Mod files...
xcopy /E /I /Y "%~dp0GSS2" "%GSS_DIR%\GSS2" >nul

echo [2/5] Installing Starter Station Save (Enables Instant Level Entry)...
if not exist "%LOCALAPPDATA%\GSS2\Saved\SaveGames" mkdir "%LOCALAPPDATA%\GSS2\Saved\SaveGames"
if not exist "%GSS_DIR%\GSS2\Saved\SaveGames" mkdir "%GSS_DIR%\GSS2\Saved\SaveGames"
if exist "%~dp0SaveGames" (
    copy /Y "%~dp0SaveGames\*.sav" "%LOCALAPPDATA%\GSS2\Saved\SaveGames\" >nul
    copy /Y "%~dp0SaveGames\*.sav" "%GSS_DIR%\GSS2\Saved\SaveGames\" >nul
)

echo [3/5] Copying Route 66 Launcher & Network Relay...
copy /Y "%~dp0play_coop.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0coop_menu.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0gss_relay.py" "%GSS_DIR%\GSS2\Binaries\Win64\" >nul
copy /Y "%~dp0play_coop.py" "%GSS_DIR%\" >nul
copy /Y "%~dp0coop_menu.py" "%GSS_DIR%\" >nul
copy /Y "%~dp0gss_relay.py" "%GSS_DIR%\" >nul

echo [4/5] Enabling Windows Firewall for Co-op (UDP Port 7777)...
netsh advfirewall firewall add rule name="Gas Station Simulator Co-op (UDP 7777)" dir=in action=allow protocol=UDP localport=7777 >nul 2>&1

echo [5/5] Creating Desktop Shortcut...
set DESKTOP_DIR=%USERPROFILE%\Desktop
echo @echo off > "%DESKTOP_DIR%\Play Gas Station Co-op.bat"
echo cd /d "%GSS_DIR%\GSS2\Binaries\Win64" >> "%DESKTOP_DIR%\Play Gas Station Co-op.bat"
echo start "" pythonw play_coop.py >> "%DESKTOP_DIR%\Play Gas Station Co-op.bat"

echo.
echo ============================================================
echo   ✨ INSTALLATION COMPLETE! CO-OP MOD IS READY! ✨
echo   Lead Architect & Creator: Nithin Kumar (@Nithinkumaru777)
echo.
echo   A shortcut "Play Gas Station Co-op.bat" has been placed
echo   on your Desktop!
echo ============================================================
echo.
pause
