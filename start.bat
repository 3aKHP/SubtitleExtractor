@echo off
title Bilibili Subtitle Extractor Server

set PY=E:\Anaconda3\envs\subtitle-extractor\python.exe

if not exist "%PY%" (
    echo 未找到 conda 环境，请先运行 setup_env.bat
    pause
    exit /b 1
)

cd /d "%~dp0app"
"%PY%" server.py
pause
