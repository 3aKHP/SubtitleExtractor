# Release Checklist

This checklist defines the minimum bar before publishing SubtitleExtractor as a clone-friendly GitHub project.

## Baseline Runtime

- `requirements.txt` installs the CPU baseline only.
- `constraints.txt` records the verified Windows/Conda/Python 3.11 dependency graph.
- `requirements-asr.txt` remains optional and contains Faster-Whisper / ctranslate2.
- `config.toml.example` defaults to PaddleOCR CPU and ASR disabled.
- The app can boot without a local `config.toml`.
- `scripts/download_tools.ps1` can prepare `app/ffmpeg.exe` and `app/yt-dlp.exe`.
- `scripts/doctor.py` reports `Required baseline: OK` after setup and tool download.
- `start.bat` starts the server without hardcoded machine-local Python paths and runs a preflight check before startup.
- `scripts/smoke_server.py` passes against a running server.

## Optional ASR

- `setup_asr_cuda.bat` installs only the optional ASR layer.
- ASR health checks and transcription run through `core.asr_worker` in a child Python process.
- The default server process does not import `core.asr_engine` in-process.
- CPU ASR is documented as a fallback, not the recommended long-video path.
- CUDA ASR benchmark data is recorded in `docs/performance.md`.
- RapidOCR is not part of the supported distribution path.

## Repository Hygiene

- `config.toml`, `.env`, local model caches, downloads, benchmark output, and diagnostic images are ignored.
- `app/ffmpeg.exe` and `app/yt-dlp.exe` are not tracked; users fetch them with `scripts/download_tools.ps1`.
- Dangerous local environment cleanup scripts are not tracked.
- Do not vendor `jieba` under `app/`; rely on the PyPI dependency from `requirements.txt`.
- Git LFS is not required for the default repository checkout.
- `CHANGELOG.md` describes the pending public release changes.
- `docs/troubleshooting.md` covers setup, download, PaddleOCR, ASR, CUDA, and port conflicts.
- `docs/release_audit.md` records the latest evidence for release readiness.

## Verification Commands

Run these before tagging or announcing a release:

```powershell
conda run -n subtitle-extractor python -m pytest -q
conda run -n subtitle-extractor python -m flake8 app/core app/main.py app/server.py scripts --select=F
conda run -n subtitle-extractor python -m compileall -q app tests scripts
conda run -n subtitle-extractor python scripts/doctor.py
conda run -n subtitle-extractor python scripts/smoke_server.py
```

For benchmark refreshes:

```powershell
conda run -n subtitle-extractor python scripts/benchmark_runtime.py local_dev\bench_BV1F3GH6bEGw.mp4 --asr-devices cpu,cuda
```
