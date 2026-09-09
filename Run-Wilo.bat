@echo off
setlocal enabledelayedexpansion
title Wilo AI Water Transfer System ? Launcher

:: ==============================================================================
:: Wilo AI Water Transfer System ? Jury & Production Launcher
:: ==============================================================================
:: Target Raspberry Pi: 192.168.137.64:8080
:: ==============================================================================

:: Configuration (Adjust if your Pi environment differs)
set "PI_USER=wilopi"
set "PI_HOST=192.168.137.64"
set "PI_PORT=8080"
set "WILO_URL=http://%PI_HOST%:%PI_PORT%"
set "PI_DIR=/home/%PI_USER%/Desktop/Wilo-Water-Pump-Automation"

cls
echo ==============================================================================
echo        WILO AI WATER TRANSFER SYSTEM ? PRODUCTION SYSTEM LAUNCHER
echo ==============================================================================
echo Target Host:   %PI_HOST%
echo Target URL:    %WILO_URL%
echo Target User:   %PI_USER%
echo ==============================================================================
echo.

:: -----------------------------------------------------------------------------
:: Step 1: Check Local Network Connectivity to Raspberry Pi
:: -----------------------------------------------------------------------------
echo [1/4] Checking network connectivity to Raspberry Pi (%PI_HOST%)...
ping -n 2 -w 1000 %PI_HOST% >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Cannot reach Raspberry Pi at %PI_HOST%.
    echo.
    echo Troubleshooting Steps:
    echo   1. Ensure Raspberry Pi is powered on and connected to Wi-Fi / Ethernet.
    echo   2. Verify your PC is connected to the same network / hotspot.
    echo   3. If using hotspot, check your phone's Connected Devices list for Pi IP.
    echo   4. To run in LOCAL Windows development mode instead:
    echo.
    set /p RUN_LOCAL="Do you want to launch local development dashboard (localhost:8080)? [Y/N]: "
    if /i "!RUN_LOCAL!"=="Y" (
        goto LaunchLocal
    )
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
echo       Raspberry Pi is reachable via ping [OK].
echo.

:: -----------------------------------------------------------------------------
:: Step 2: Check If Wilo Dashboard Is Already Running on Port 8080
:: -----------------------------------------------------------------------------
echo [2/4] Checking Wilo Dashboard service on port %PI_PORT%...
powershell -Command "$t = Test-NetConnection -ComputerName '%PI_HOST%' -Port %PI_PORT% -WarningAction SilentlyContinue; if ($t.TcpTestSucceeded) { exit 0 } else { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo       Wilo Dashboard is active and responding on port %PI_PORT% [OK]!
    goto LaunchBrowser
)

:: -----------------------------------------------------------------------------
:: Step 3: Service Is Not Responding ? Attempt Start via SSH
:: -----------------------------------------------------------------------------
echo       Dashboard is not currently responding on port %PI_PORT%.
echo.
echo [3/4] Attempting to verify / start Wilo services on Raspberry Pi via SSH...
echo       Connecting to %PI_USER%@%PI_HOST%...

:: Check if ssh command exists
where ssh >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] OpenSSH client is not found in PATH on this Windows machine.
    echo Please log into the Pi manually and run:
    echo    cd %PI_DIR% ^&^& ./start_wilo.sh
    echo.
    goto PollService
)

:: Send command to start services via systemctl or start_wilo.sh
echo       Sending start command to Raspberry Pi...
ssh -o ConnectTimeout=5 -o BatchMode=no %PI_USER%@%PI_HOST% "sudo systemctl start wilo-server wilo-frontend wilo-pump 2>/dev/null || (cd %PI_DIR% && nohup ./start_wilo.sh > /dev/null 2>&1 &)"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTICE] SSH command finished or password was required.
)

:: -----------------------------------------------------------------------------
:: Step 4: Wait for Port 8080 to become ready
:: -----------------------------------------------------------------------------
:PollService
echo.
echo [4/4] Waiting for Wilo Dashboard service to become ready...
set ATTEMPTS=0
:CheckLoop
set /a ATTEMPTS+=1
powershell -Command "$t = Test-NetConnection -ComputerName '%PI_HOST%' -Port %PI_PORT% -WarningAction SilentlyContinue; if ($t.TcpTestSucceeded) { exit 0 } else { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo       Service is ONLINE and ready!
    goto LaunchBrowser
)
if %ATTEMPTS% GEQ 15 (
    echo.
    echo [WARNING] Service did not respond within 15 seconds.
    echo Opening browser anyway in case it is still finishing startup...
    goto LaunchBrowser
)
echo       Attempt %ATTEMPTS%/15: Waiting 2 seconds...
powershell -Command "Start-Sleep -Seconds 2"
goto CheckLoop

:: -----------------------------------------------------------------------------
:: Step 5: Launch Browser
:: -----------------------------------------------------------------------------
:LaunchBrowser
echo.
echo ==============================================================================
echo   ?? Wilo AI Water Transfer System is Ready!
echo   Opening: %WILO_URL%
echo ==============================================================================
echo.
start "" "%WILO_URL%"
echo Launcher completed successfully.
timeout /t 5 >nul
exit /b 0

:: -----------------------------------------------------------------------------
:: Local Windows Development Fallback
:: -----------------------------------------------------------------------------
:LaunchLocal
echo.
echo ==============================================================================
echo   Starting Local Windows Development Environment
echo ==============================================================================
echo Starting Flask backend on port 5050...
start "Wilo Backend (5050)" cmd /k "python src/dashboard/server.py --port 5050"
echo Starting Vite dashboard on port 8080...
cd dashboard
start "Wilo Frontend (8080)" cmd /k "npm run dev"
cd ..
timeout /t 4 >nul
start "" "http://localhost:8080"
exit /b 0
