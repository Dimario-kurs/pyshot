@echo off
rem Zapusk PyShot bez okna konsoli
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0..\main.py"
    exit /b
)
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw "%~dp0..\main.py"
    exit /b
)
start "" python "%~dp0..\main.py"
