@echo off
setlocal
cd /d "%~dp0"
py -3.13 build.py
if errorlevel 1 echo Build stopped. Send Build.log from this folder.
echo.
pause
