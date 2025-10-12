@echo off
REM Minimal wrapper to call the Python CLI
setlocal
set PYTHON_EXEC=%~dp0..\..\.venv\Scripts\python.exe
if exist "%PYTHON_EXEC%" (
  "%PYTHON_EXEC%" -m pal.cli %*
) else (
  python -m pal.cli %*
)
