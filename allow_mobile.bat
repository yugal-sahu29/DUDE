@echo off
title DUDE - Configure Windows Firewall for Mobile Access
color 0b

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ========================================================
    echo   DUDE - Mobile Access Firewall Setup
    echo ========================================================
    echo.
    echo   [!] Administrator privileges required.
    echo   [!] Requesting elevation prompt...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   DUDE - Mobile Access Firewall Setup
echo ========================================================
echo.
echo [*] Removing any old DUDE firewall rules...
netsh advfirewall firewall delete rule name="DUDE Server (Port 8000)" >nul 2>&1

echo [*] Adding Inbound Firewall Rule for Port 8000 (Any Profile)...
netsh advfirewall firewall add rule name="DUDE Server (Port 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any >nul

echo [*] Unblocking python.exe in Windows Firewall...
powershell -NoProfile -Command "Get-NetFirewallRule -DisplayName '*python*' | Where-Object {$_.Direction -eq 'Inbound'} | Set-NetFirewallRule -Action Allow -Enabled True" >nul 2>&1

echo.
echo ========================================================
echo   SUCCESS! Windows Firewall is now configured.
echo ========================================================
echo.
echo   You can now open DUDE on your mobile phone:
echo.
echo   URL: http://10.98.107.121:8000
echo.
echo   (Make sure your phone is connected to the same Wi-Fi / Hotspot!)
echo ========================================================
echo.
pause
