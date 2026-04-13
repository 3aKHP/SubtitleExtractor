@echo off
:: SubtitleExtractor 环境安装脚本
:: 前提：已安装 Anaconda，CUDA 12.x 驱动

set CONDA=E:\Anaconda3\Scripts\conda.exe
set ENV_NAME=subtitle-extractor
set PY=E:\Anaconda3\envs\%ENV_NAME%\python.exe
set MIRROR=-i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

echo [1/4] 创建 conda 环境 (Python 3.11)...
%CONDA% create -n %ENV_NAME% python=3.11 -y
if errorlevel 1 (
    echo 环境已存在，跳过创建
)

echo [2/4] 安装 onnxruntime-gpu (CUDA 12.x, ~207MB)...
%PY% -m pip install onnxruntime-gpu==1.24.4 %MIRROR%

echo [3/4] 安装其余依赖...
%PY% -m pip install ^
    rapidocr-onnxruntime==1.2.3 ^
    faster-whisper==1.1.0 ^
    ctranslate2 ^
    "opencv-python>=4.10.0" ^
    "fastapi>=0.110.0" ^
    "uvicorn>=0.29.0" ^
    "pydantic>=2.0" ^
    "numpy>=2.0" ^
    tqdm pypinyin jieba ^
    httpx pytest pytest-cov ^
    %MIRROR%

echo [4/4] 验证...
%PY% -c "import onnxruntime; print('onnxruntime:', onnxruntime.__version__, '| providers:', onnxruntime.get_available_providers())"
%PY% -c "import rapidocr_onnxruntime; print('RapidOCR OK')"
%PY% -c "import faster_whisper; print('faster-whisper OK')"

echo.
echo 完成！启动服务请运行：
echo   %PY% app\server.py
pause
