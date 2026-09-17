@echo off
rem P7M Manager - inspect signed .p7m containers and extract what they carry
rem Copyright (C) 2026 Marco Lombardo
rem SPDX-License-Identifier: AGPL-3.0-or-later
rem
rem Run P7M Manager from a source checkout, creating the virtual environment on
rem first use. Nothing is installed system-wide.
setlocal
set "HERE=%~dp0.."
set "VENV=%HERE%\.venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo Creating the virtual environment in .venv ...
    py -3 -m venv "%VENV%" || python -m venv "%VENV%" || goto :nopython
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip >nul
    "%VENV%\Scripts\python.exe" -m pip install -r "%HERE%\requirements.txt" || goto :failed
)

start "" "%VENV%\Scripts\pythonw.exe" -m p7mmanager %*
exit /b 0

:nopython
echo Python 3.10 or later is required: https://www.python.org/downloads/
pause
exit /b 1

:failed
echo Could not install the dependencies. See the messages above.
pause
exit /b 1
