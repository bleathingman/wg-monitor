@echo off
REM ────────────────────────────────────────────
REM  WG Monitor – Build Script (Windows .bat)
REM  Génère un .exe standalone dans dist/
REM ────────────────────────────────────────────

echo [WG Monitor] Installation des dépendances...
pip install -r requirements.txt

echo.
echo [WG Monitor] Compilation en .exe avec PyInstaller...
pyinstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "WGMonitor" ^
  --icon NONE ^
  --add-data "%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\customtkinter;customtkinter" ^
  wg_monitor.py

echo.
echo [WG Monitor] Build terminé !
echo Votre .exe se trouve dans : dist\WGMonitor.exe
pause
