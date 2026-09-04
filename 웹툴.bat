@echo off
rem webtool labeling server launcher (ASCII-only: cmd parses this file as CP949,
rem so Korean text here breaks into garbage commands - see 2026-09-04)
cd /d "%~dp0assets_dev\train"

rem If port 8777 is already listening, just open the browser and exit.
netstat -ano | findstr /c:":8777" | findstr /c:"LISTENING" >nul 2>&1
if %errorlevel%==0 (
  echo Server already running - opening browser.
  start http://127.0.0.1:8777/
  ping -n 4 127.0.0.1 >nul
  exit /b 0
)

rem Open the browser ~3s after the server starts.
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:8777/"
echo Starting webtool server... http://127.0.0.1:8777/
echo (Closing this window stops the server.)
call C:\Users\admin\miniconda3\condabin\conda.bat run -n sugartrain --no-capture-output python -u webtool.py
pause
