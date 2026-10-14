@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0custom-pcsx2\nightly-test-2.9.127\Test-Runtime.ps1" -Action Prepare
pause
