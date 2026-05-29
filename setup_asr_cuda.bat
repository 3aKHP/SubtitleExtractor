@echo off
setlocal
:: SubtitleExtractor optional ASR setup.
:: Run setup_env.bat first. Optional overrides:
::   set SUBTITLE_EXTRACTOR_ENV=my-env
::   set CONDA_EXE=C:\Path\To\conda.exe

set "ENV_NAME=subtitle-extractor"
if defined SUBTITLE_EXTRACTOR_ENV set "ENV_NAME=%SUBTITLE_EXTRACTOR_ENV%"
set "PIP_CONSTRAINT_ARGS="
if exist "constraints.txt" set "PIP_CONSTRAINT_ARGS=-c constraints.txt"

call :find_conda
if errorlevel 1 (
    pause
    exit /b 1
)

echo Using Conda: %CONDA%
echo Environment: %ENV_NAME%
if defined PIP_CONSTRAINT_ARGS echo Pip constraints: constraints.txt
echo.

echo [1/3] Checking conda environment...
call "%CONDA%" env list | findstr /R /C:"^%ENV_NAME%[ ]" >nul 2>nul
if errorlevel 1 (
    echo Environment "%ENV_NAME%" was not found. Run setup_env.bat first.
    pause
    exit /b 1
)

echo [2/3] Installing optional ASR dependencies...
call :run_python -m pip install -r requirements-asr.txt %PIP_CONSTRAINT_ARGS%
if errorlevel 1 (
    echo ASR dependency installation failed.
    pause
    exit /b 1
)

echo [3/3] Verifying isolated ASR worker...
call :run_python -c "import sys; sys.path.insert(0, 'app'); from core.asr_worker import check_asr_available; raise SystemExit(0 if check_asr_available() else 1)"
if errorlevel 1 (
    echo ASR worker verification failed.
    pause
    exit /b 1
)

echo.
echo Done. To enable ASR, set config.toml [asr].enabled=true.
echo Benchmark with:
echo   conda run -n %ENV_NAME% python scripts\benchmark_runtime.py ^<local-video-path^> --asr-devices cpu,cuda
pause
exit /b 0

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
