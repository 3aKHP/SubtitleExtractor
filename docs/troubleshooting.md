# Troubleshooting

This guide covers the expected failure modes for the current Windows/Conda release path.

## Quick Diagnosis

Run:

```powershell
conda run -n subtitle-extractor python scripts\doctor.py
```

The required baseline is healthy when the final line is:

```text
Required baseline: OK
```

Optional ASR packages may still show as `MISSING`. That is normal unless you intentionally enabled ASR.

## Conda Is Not Found

`setup_env.bat`, `setup_asr_cuda.bat`, and `start.bat` try to locate Conda automatically. If detection fails, set `CONDA_EXE`:

```powershell
$env:CONDA_EXE="E:\Anaconda3\condabin\conda.bat"
.\setup_env.bat
```

To use a custom environment name:

```powershell
$env:SUBTITLE_EXTRACTOR_ENV="my-subtitle-env"
.\setup_env.bat
```

## Python Dependencies Fail To Install

Use Python 3.11. The verified baseline uses:

```powershell
python -m pip install -r requirements.txt -c constraints.txt
```

`constraints.txt` records the dependency graph that passed the fresh install smoke on Windows/Conda. If a dependency resolver error appears, first retry with a clean Python 3.11 environment.

## PaddleOCR Downloads Models On First Start

The first PaddleOCR startup downloads model files. If the download is slow or fails, check network access to PaddleOCR's model host and retry. You can force a custom model cache directory:

```powershell
$env:PADDLE_OCR_BASE_DIR="D:\SubtitleExtractorModels\paddleocr"
conda run -n subtitle-extractor python app/server.py
```

The app can start from `config.toml.example`; a local `config.toml` is optional.

## `yt-dlp` Or `ffmpeg` Is Missing

The Python dependencies do not include external executables. Prepare them with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download_tools.ps1
```

After that, `app\yt-dlp.exe` and `app\ffmpeg.exe` should exist. Run `doctor.py` again.

## Bilibili Download Fails

Most download failures come from network instability, video availability, login/cookie requirements, or upstream changes in Bilibili. First update `yt-dlp`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download_tools.ps1 -Force
```

Then rerun the task. If only a specific video fails, verify that `yt-dlp` can read metadata:

```powershell
.\app\yt-dlp.exe "https://www.bilibili.com/video/BV1F3GH6bEGw/" --dump-json --no-playlist
```

## ASR Is Unavailable

ASR is intentionally not part of the default installation. The default release path is OCR-only. To install ASR:

```powershell
.\setup_asr_cuda.bat
```

Then copy `config.toml.example` to `config.toml` and enable ASR:

```toml
[asr]
enabled = true
device = "cuda"
```

Use `device = "cpu"` only as a fallback; long videos can be slow on CPU.

## CUDA Or cuDNN Errors

The default OCR path is PaddleOCR CPU to avoid native CUDA runtime conflicts. CUDA is only recommended for Faster-Whisper ASR. If ASR fails with CUDA errors:

- Confirm the NVIDIA driver is current.
- Confirm the installed `ctranslate2` build supports your CUDA runtime.
- Try `device = "cpu"` to separate ASR install issues from CUDA issues.
- Keep PaddleOCR GPU disabled unless you explicitly know the local cuDNN stack is compatible.

## Port 8000 Is Already In Use

Copy the config and change the port:

```powershell
Copy-Item config.toml.example config.toml
```

```toml
[server]
host = "127.0.0.1"
port = 8765
```

Then restart `start.bat`.

## `start.bat` Preflight Reports Issues

`start.bat` runs `scripts\doctor.py` before launching the server. It continues startup after a warning because `/health` can still be useful even when extraction tools are missing.

To skip the preflight check:

```powershell
$env:SUBTITLE_EXTRACTOR_SKIP_DOCTOR="1"
.\start.bat
```
