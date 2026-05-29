# Bilibili Subtitle Extractor

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

从 B 站视频中提取硬字幕（OCR）并可选地合并 ASR 语音识别结果。

## 功能

- 基于 PaddleOCR 的硬字幕提取（当前可用主线）
- 基于 Faster-Whisper 的语音识别（ASR）
- OCR + ASR 结果对齐合并
- FastAPI 后端 + Chrome 插件前端

## 环境要求

- Python 3.11
- Anaconda / Miniconda（推荐，默认环境名：`subtitle-extractor`）
- NVIDIA GPU（可选，CPU 模式也可运行）
- CUDA 12.x（GPU 模式需要）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/3aKHP/SubtitleExtractor.git
cd SubtitleExtractor
```

### 2. 准备 Python 环境

推荐使用 `setup_env.bat` 创建/更新 CPU 基线环境：

```powershell
.\setup_env.bat
```

脚本会自动查找 Conda，并创建默认环境 `subtitle-extractor`。如需改环境名：

```powershell
$env:SUBTITLE_EXTRACTOR_ENV="my-env"
.\setup_env.bat
```

也可以手动准备 Python 3.11 环境并安装依赖：

```powershell
python -m pip install -r requirements.txt
```

默认依赖只保证 PaddleOCR 硬字幕提取和 Web 服务可用，不安装 ASR 语音识别依赖。

### 3. 准备配置

首次运行可以直接使用 `config.toml.example` 中的默认配置。需要自定义端口、ASR、远程 OCR 等设置时，再复制配置模板：

```powershell
Copy-Item config.toml.example config.toml
```

默认 OCR 后端为 `paddle`。这是当前实际端点测试确认可用的主线；RapidOCR 不属于当前支持的分发路径。

默认 ASR 为关闭状态。如需语音识别/校对，先安装可选依赖：

```powershell
.\setup_asr_cuda.bat
```

然后在 `config.toml` 中设置：

```toml
[asr]
enabled = true
device = "cuda"  # 无 CUDA 时可改为 "cpu"
```

ASR 会在独立 Python 子进程中运行，以隔离 Faster-Whisper / ctranslate2 与 PaddleOCR 的原生运行时依赖。

### 4. 下载第三方可执行文件

运行工具下载脚本，将 `ffmpeg.exe` 和 `yt-dlp.exe` 放入 `app/` 目录：

```powershell
.\scripts\download_tools.ps1
```

如果网络环境不适合自动下载，也可以手动准备：

| 文件 | 下载地址 | 说明 |
|------|----------|------|
| `ffmpeg.exe` | https://github.com/BtbN/FFmpeg-Builds/releases | 选 `ffmpeg-master-latest-win64-gpl.zip`，取其中的 `ffmpeg.exe` |
| `yt-dlp.exe` | https://github.com/yt-dlp/yt-dlp/releases/latest | 直接下载 `yt-dlp.exe` |

### 5. 检查环境

```powershell
conda run -n subtitle-extractor python scripts\doctor.py
```

## 启动

双击 `start.bat`，或手动运行：

```powershell
conda run -n subtitle-extractor python app/server.py
```

如果不用 Conda，可以直接运行 `python app/server.py`，或设置 `SUBTITLE_EXTRACTOR_PYTHON` 后再运行 `start.bat`。

服务启动后访问 `http://127.0.0.1:8000`。

启动后可检查健康状态：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

也可以运行 smoke 脚本检查正在运行的服务：

```powershell
conda run -n subtitle-extractor python scripts/smoke_server.py
```

如需提交一个视频 URL 做端到端任务 smoke：

```powershell
conda run -n subtitle-extractor python scripts/smoke_server.py --url "https://www.bilibili.com/video/BV1F3GH6bEGw/" --wait
```

Chrome 插件在 `chrome_extension/` 目录，在浏览器扩展页面以开发者模式加载即可。

## 性能评估

当前分发策略以 PaddleOCR CPU 为稳定默认路径，ASR CUDA 作为推荐加速路径。实测数据和复跑命令见 [docs/performance.md](docs/performance.md)。

发布前检查项见 [docs/release_checklist.md](docs/release_checklist.md)，当前发布审计见 [docs/release_audit.md](docs/release_audit.md)，版本变更见 [CHANGELOG.md](CHANGELOG.md)。

## 命令行使用

```bash
python app/main.py <视频路径> -o <输出目录> [--asr] [--no-asr] [--cpu]
```


## License

Copyright (C) 2026 3aKHP

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This project calls [ffmpeg](https://ffmpeg.org/) as an external process (GPL v2+) and uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) as a downloaded local tool. See [LICENSE](LICENSE) for details.
