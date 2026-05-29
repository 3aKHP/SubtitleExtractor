@echo off
setlocal
title Bilibili Subtitle Extractor Server

set "ENV_NAME=subtitle-extractor"
if defined SUBTITLE_EXTRACTOR_ENV set "ENV_NAME=%SUBTITLE_EXTRACTOR_ENV%"

if defined SUBTITLE_EXTRACTOR_PYTHON (
    if exist "%SUBTITLE_EXTRACTOR_PYTHON%" (
        "%SUBTITLE_EXTRACTOR_PYTHON%" app\server.py
        pause
        exit /b %ERRORLEVEL%
    )
    echo SUBTITLE_EXTRACTOR_PYTHON was set but does not exist:
    echo   %SUBTITLE_EXTRACTOR_PYTHON%
    pause
    exit /b 1
)

call :find_conda
if errorlevel 1 (
    echo Falling back to "python app\server.py".
    python app\server.py
    pause
    exit /b %ERRORLEVEL%
)

call "%CONDA%" run -n "%ENV_NAME%" python app\server.py
if errorlevel 1 (
    echo.
    echo Failed to start with conda environment "%ENV_NAME%".
    echo Run setup_env.bat first, or set SUBTITLE_EXTRACTOR_PYTHON to a Python executable.
)
pause
exit /b %ERRORLEVEL%

:find_conda
if defined CONDA_EXE (
    if exist "%CONDA_EXE%" (
        set "CONDA=%CONDA_EXE%"
        exit /b 0
    )
)

for /f "delims=" %%I in ('where conda 2^>nul') do (
    set "CONDA=%%I"
    exit /b 0
)

for %%I in (
    "%USERPROFILE%\miniconda3\Scripts\conda.exe"
    "%USERPROFILE%\anaconda3\Scripts\conda.exe"
    "C:\ProgramData\miniconda3\Scripts\conda.exe"
    "C:\ProgramData\Anaconda3\Scripts\conda.exe"
) do (
    if exist "%%~I" (
        set "CONDA=%%~I"
        exit /b 0
    )
)

exit /b 1
