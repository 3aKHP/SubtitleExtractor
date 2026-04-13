# Bilibili Subtitle Extractor

从 B 站视频中提取硬字幕（OCR）并可选地合并 ASR 语音识别结果。

## 功能

- 基于 PaddleOCR 的硬字幕提取（支持 GPU 加速）
- 基于 Faster-Whisper 的语音识别（ASR）
- OCR + ASR 结果对齐合并
- FastAPI 后端 + Chrome 插件前端

## 环境要求

- Python 3.8（项目使用内嵌 `python_env/`，见下方安装说明）
- NVIDIA GPU（可选，CPU 模式也可运行）
- CUDA 11.x（GPU 模式需要）

## 安装

### 1. 克隆仓库

```bash
git clone <repo-url>
cd SubtitleExtractor
```

如果使用 Git LFS（存储 jieba 模型文件），需要先安装：

```bash
git lfs install
git lfs pull
```

### 2. 准备 Python 环境

`python_env/` 不纳入版本控制，需自行准备 Python 3.8 环境并安装依赖：

```bash
pip install -r requirements.txt
```

或使用项目内嵌环境（自行配置路径后运行 `start.bat`）。

### 3. 下载第三方可执行文件

将以下文件放入 `app/` 目录：

| 文件 | 下载地址 | 说明 |
|------|----------|------|
| `ffmpeg.exe` | https://github.com/BtbN/FFmpeg-Builds/releases | 选 `ffmpeg-master-latest-win64-gpl.zip`，取其中的 `ffmpeg.exe` |
| `yt-dlp.exe` | https://github.com/yt-dlp/yt-dlp/releases/latest | 直接下载 `yt-dlp.exe` |

## 启动

双击 `start.bat`，或手动运行：

```bash
cd app
python server.py
```

服务启动后访问 `http://127.0.0.1:8000`。

Chrome 插件在 `chrome_extension/` 目录，在浏览器扩展页面以开发者模式加载即可。

## 命令行使用

```bash
cd app
python main.py <视频路径> -o <输出目录> [--roi 0.8] [--cpu]
```
