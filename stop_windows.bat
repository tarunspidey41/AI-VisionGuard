@echo off
echo Stopping AI VisionGuard server...
taskkill /FI "WINDOWTITLE eq AI VisionGuard Server*" /T /F >nul 2>&1
echo Done. You can close this window.
pause
