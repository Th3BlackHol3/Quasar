@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Quasar is not set up yet. Run setup.bat first.
  exit /b 2
)
".venv\Scripts\python.exe" "quasar.py" %*
exit /b %ERRORLEVEL%
