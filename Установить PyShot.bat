@echo off
rem Ustanovka PyShot dlya tekushchego polzovatelya (bez prav administratora)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install.ps1"
if errorlevel 1 pause
