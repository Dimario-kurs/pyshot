@echo off
rem Sborka PyShot.exe (odin fail, bez konsoli)
cd /d "%~dp0.."
py -m pip install --quiet --upgrade pyinstaller || goto :err
py tools\make_ico.py || goto :err
py -m PyInstaller --noconfirm --clean --noconsole --onefile ^
    --name PyShot --icon assets\PyShot.ico ^
    --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick ^
    --exclude-module PySide6.QtQuickWidgets --exclude-module PySide6.Qt3DCore ^
    --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtMultimedia ^
    --exclude-module tkinter --exclude-module unittest ^
    main.py || goto :err
echo.
echo Gotovo: dist\PyShot.exe
pause
exit /b 0
:err
echo.
echo Sborka ne udalas.
pause
exit /b 1
