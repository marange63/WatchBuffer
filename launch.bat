@echo off
call conda activate WatchBuffer
python "%~dp0main.py"
if %ERRORLEVEL% neq 0 (
    echo.
    echo WatchBuffer exited with an error. Press any key to close.
    pause >nul
)
