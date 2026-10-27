@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo [ERROR] Python 3.10+ not found. Install it from https://www.python.org/downloads/windows/ and ensure it is available in PATH.
exit /b 127
:use_py
py -3 bootstrap.py %*
exit /b %ERRORLEVEL%
:use_python
python bootstrap.py %*
exit /b %ERRORLEVEL%
