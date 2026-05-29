@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Bilibili Subtitle Extractor Server

set "ENV_NAME=subtitle-extractor"
if defined SUBTITLE_EXTRACTOR_ENV set "ENV_NAME=%SUBTITLE_EXTRACTOR_ENV%"

if defined SUBTITLE_EXTRACTOR_PYTHON (
    if exist "%SUBTITLE_EXTRACTOR_PYTHON%" (
        call :run_doctor_direct "%SUBTITLE_EXTRACTOR_PYTHON%"
        "%SUBTITLE_EXTRACTOR_PYTHON%" app\server.py
        set "SERVER_EXIT=!ERRORLEVEL!"
        pause
        exit /b !SERVER_EXIT!
    )
    echo SUBTITLE_EXTRACTOR_PYTHON was set but does not exist:
    echo   %SUBTITLE_EXTRACTOR_PYTHON%
    pause
    exit /b 1
)

call :find_conda
if errorlevel 1 (
    echo Falling back to "python app\server.py".
    call :run_doctor_direct python
    python app\server.py
    set "SERVER_EXIT=!ERRORLEVEL!"
    pause
    exit /b !SERVER_EXIT!
)

call :run_doctor_conda
call "%CONDA%" run -n "%ENV_NAME%" python app\server.py
set "SERVER_EXIT=%ERRORLEVEL%"
if errorlevel 1 (
    echo.
    echo Failed to start with conda environment "%ENV_NAME%".
    echo Run setup_env.bat first, or set SUBTITLE_EXTRACTOR_PYTHON to a Python executable.
)
pause
exit /b %SERVER_EXIT%

:run_doctor_direct
if defined SUBTITLE_EXTRACTOR_SKIP_DOCTOR exit /b 0
echo Running preflight check...
"%~1" scripts\doctor.py
if errorlevel 1 call :doctor_warning
exit /b 0

:run_doctor_conda
if defined SUBTITLE_EXTRACTOR_SKIP_DOCTOR exit /b 0
echo Running preflight check...
call "%CONDA%" run -n "%ENV_NAME%" python scripts\doctor.py
if errorlevel 1 call :doctor_warning
exit /b 0

:doctor_warning
echo.
echo Preflight reported issues. The server may still start, but extraction can fail.
echo Common fixes:
echo   setup_env.bat
echo   powershell -ExecutionPolicy Bypass -File scripts\download_tools.ps1
echo.
echo Set SUBTITLE_EXTRACTOR_SKIP_DOCTOR=1 to skip this check.
echo Continuing startup...
echo.
exit /b 0

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
