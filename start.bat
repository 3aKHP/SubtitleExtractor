@echo off
title Bilibili Subtitle Extractor Server
echo 正在启动字幕提取后端...
echo 请勿关闭此窗口！

:: 设置 Python 路径为当前目录下的 python_env
set PYTHON_EXE=%~dp0python_env\python.exe

:: 切换到 app 目录
cd /d "%~dp0app"

:: 启动服务器
"%PYTHON_EXE%" server.py

pause
