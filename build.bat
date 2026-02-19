@echo off
REM ────────────────────────────────────────────
REM  WG Monitor – Build Script (Windows .bat)
REM  Génère un .exe standalone dans dist/
REM ────────────────────────────────────────────

echo [WG Monitor] Installation des dependances...
pip install -r requirements.txt

echo.
echo [WG Monitor] Detection du chemin customtkinter...

REM Detecte automatiquement le chemin de customtkinter via Python
FOR /F "delims=" %%i IN ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') DO SET CTK_PATH=%%i

IF "%CTK_PATH%"=="" (
    echo ERREUR : customtkinter introuvable. Verifiez que pip install a fonctionne.
    pause
    exit /b 1
)

echo Chemin trouve : %CTK_PATH%

echo.
echo [WG Monitor] Compilation en .exe avec PyInstaller...
pyinstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "WGMonitor" ^
  --add-data "%CTK_PATH%;customtkinter" ^
  wg_monitor.py

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERREUR lors de la compilation. Voir les logs ci-dessus.
    pause
    exit /b 1
)

echo.
echo ====================================
echo  Build termine avec succes !
echo  dist\WGMonitor.exe est pret.
echo ====================================
pause