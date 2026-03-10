@echo off
call "%USERPROFILE%\miniconda3\Scripts\activate.bat" WatchBuffer 2>nul
if %ERRORLEVEL% neq 0 (
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat" WatchBuffer 2>nul
)
if %ERRORLEVEL% neq 0 (
    call conda activate WatchBuffer
)
python "%~dp0main.py"
if %ERRORLEVEL% neq 0 (
    echo.
    echo WatchBuffer exited with an error. Press any key to close.
    pause >nul
)
