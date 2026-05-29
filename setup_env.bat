@echo off
setlocal
:: SubtitleExtractor CPU baseline setup.
:: Optional overrides:
::   set SUBTITLE_EXTRACTOR_ENV=my-env
::   set CONDA_EXE=C:\Path\To\conda.exe

set "ENV_NAME=subtitle-extractor"
if defined SUBTITLE_EXTRACTOR_ENV set "ENV_NAME=%SUBTITLE_EXTRACTOR_ENV%"

call :find_conda
if errorlevel 1 (
    pause
    exit /b 1
)

echo Using Conda: %CONDA%
echo Environment: %ENV_NAME%
echo.

echo [1/4] Ensuring conda environment (Python 3.11)...
call "%CONDA%" env list | findstr /R /C:"^%ENV_NAME%[ ]" >nul 2>nul
if errorlevel 1 (
    call "%CONDA%" create -n "%ENV_NAME%" python=3.11 -y
    if errorlevel 1 (
        echo Failed to create conda environment.
        pause
        exit /b 1
    )
) else (
    echo Environment already exists, skipping creation.
)

echo [2/4] Installing CPU baseline dependencies...
call :run_python -m pip install --upgrade pip
if errorlevel 1 goto :pip_failed
call :run_python -m pip install -r requirements.txt
if errorlevel 1 goto :pip_failed

echo [3/4] Installing development verification tools...
call :run_python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :pip_failed

echo [4/4] Verifying PaddleOCR baseline imports...
call :run_python -c "import paddleocr, paddle; print('PaddleOCR:', paddleocr.__version__, '| paddle:', paddle.__version__)"
if errorlevel 1 (
    echo Baseline import verification failed.
    pause
    exit /b 1
)

echo.
echo Done. Start the service with:
echo   start.bat
echo.
echo Download ffmpeg.exe and yt-dlp.exe before first extraction:
echo   powershell -ExecutionPolicy Bypass -File scripts\download_tools.ps1
echo.
echo Optional ASR setup:
echo   setup_asr_cuda.bat
pause
exit /b 0

:pip_failed
echo Dependency installation failed.
pause
exit /b 1

:run_python
call "%CONDA%" run -n "%ENV_NAME%" python %*
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

echo Conda was not found. Install Miniconda/Anaconda or set CONDA_EXE.
exit /b 1
