@echo off
title SatQuery AI - One-Click Launcher
cd /d "%~dp0"

echo.
echo  ============================================================
echo   SatQuery AI - One-Click Setup and Launch
echo  ============================================================
echo.

where powershell >nul 2>&1
if %ERRORLEVEL%==0 (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-satquery.ps1"
  goto :end
)

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-satquery.ps1"
  goto :end
)

echo [X] PowerShell not found. Install PowerShell and try again.
pause
exit /b 1

:end
echo.
if errorlevel 1 (
  echo Launcher exited with an error.
  pause
)
