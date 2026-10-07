@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0repo\ops\bootstrap.ps1" -Root "%~dp0." -HostTarget codex
if errorlevel 1 pause
