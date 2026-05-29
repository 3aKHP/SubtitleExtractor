# Performance Baseline

This project should be distributable from a stable CPU baseline first. GPU acceleration is valuable, but it must stay optional because the OCR and ASR stacks depend on different native CUDA/runtime components.

## Baseline Decision

- Default OCR backend: PaddleOCR on CPU.
- Default ASR behavior: disabled until optional ASR dependencies are installed.
- Recommended acceleration path: Faster-Whisper ASR on CUDA.
- Not recommended as a default path: PaddleOCR GPU. On the current Windows test host, GPU initialization succeeds but inference fails when `cudnn64_8.dll` is unavailable.

## Test Case

- Date: 2026-05-29
- Host OS: Windows
- Python: 3.11 conda environment `subtitle-extractor`
- Video URL: `https://www.bilibili.com/video/BV1F3GH6bEGw/`
- Downloaded format: 480P, 30 FPS, H.264 video + m4a audio
- Duration: about 11:24
- OCR region: bottom 20% of the frame
- OCR step: every 10 frames
- ASR model: `small`

## Results

| Task | Runtime | Notes |
| --- | ---: | --- |
| Download | about 5s | Network dependent |
| Audio extraction | 0.57s | ffmpeg to 16 kHz mono wav |
| PaddleOCR CPU only | 71.44s | 365 OCR calls, 160 output lines |
| Faster-Whisper small CPU | 168.13s | 280 segments |
| Faster-Whisper small CUDA | 29.40s | 303 segments |

Estimated full processing time for this video:

| Mode | Estimated Runtime | Interpretation |
| --- | ---: | --- |
| OCR only, CPU | about 1m11s | Fast enough for default distribution |
| OCR CPU + ASR CPU | about 4m00s | Usable fallback, but not a polished long-video experience |
| OCR CPU + ASR CUDA | about 1m41s | Good recommended accelerated path |

## Interpretation

The practical bottleneck is ASR, not OCR. PaddleOCR CPU is fast enough on this sample, while PaddleOCR GPU adds native dependency risk without clear distribution value. Faster-Whisper CUDA provides the largest speedup and should be treated as the advanced acceleration path.

For distribution, install `requirements.txt` first and treat `requirements-asr.txt` as an optional layer. On Windows, `setup_env.bat` prepares the CPU baseline, and `setup_asr_cuda.bat` adds the ASR layer afterward. Both scripts auto-detect Conda and accept `SUBTITLE_EXTRACTOR_ENV` / `CONDA_EXE` overrides. This keeps the default clone-and-run path free of Faster-Whisper, ctranslate2, and CUDA runtime surprises.

The application can boot from `config.toml.example` when `config.toml` is absent. Copy `config.toml.example` to `config.toml` only when local overrides are needed.

Use `scripts/doctor.py` after setup to confirm Python packages and local `ffmpeg.exe` / `yt-dlp.exe` are available. On Windows, `scripts/download_tools.ps1` can fetch those two executable tools automatically. The doctor checks optional ASR imports in a subprocess so PaddleOCR's native runtime does not contaminate the Faster-Whisper/ctranslate2 check.

The application pipeline follows the same isolation rule: OCR runs in the main process, while ASR model loading and transcription run through `core.asr_worker` in a child Python process. The benchmark script uses that worker for ASR measurements as well. This keeps the default server process clone-friendly and avoids import-order dependent CUDA DLL behavior.

## Reproducing

Download the sample:

```powershell
& .\app\yt-dlp.exe "https://www.bilibili.com/video/BV1F3GH6bEGw/" -f "bestvideo[vcodec^=avc][height<=720]+bestaudio/best[ext=mp4][height<=720]" --merge-output-format mp4 --ffmpeg-location app -o "local_dev\bench_BV1F3GH6bEGw.%(ext)s"
```

Run the benchmark:

```powershell
conda run -n subtitle-extractor python scripts\benchmark_runtime.py local_dev\bench_BV1F3GH6bEGw.mp4 --asr-devices cpu,cuda
```

The script writes a JSON result file under `local_dev/bench_output/`.
