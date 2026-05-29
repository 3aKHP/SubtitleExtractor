# Release Audit

Date: 2026-05-29

This audit records the current evidence for the first public, clone-friendly release direction.

## Objective

Make SubtitleExtractor distributable as an out-of-the-box GitHub project by stabilizing:

- PaddleOCR CPU as the default OCR path.
- Optional ASR acceleration.
- Dependency separation.
- Runtime diagnostics and performance evaluation.

## Evidence

| Requirement | Current Evidence | Status |
| --- | --- | --- |
| PaddleOCR CPU default | `config.toml.example` uses `backend = "paddle"` and `use_gpu = false`; `/health` reports `ocr_backend=paddle`, `ocr_use_gpu=false`. | Verified |
| RapidOCR excluded from distribution path | `config.toml.example` documents only `paddle` / `remote`; `create_ocr_engine()` raises for `rapidocr`, `local`, and unknown backends; tests cover these cases. | Verified |
| ASR optional by default | `config.toml.example` uses `[asr] enabled = false`; `requirements.txt` excludes Faster-Whisper / ctranslate2; `requirements-asr.txt` contains the ASR layer. | Verified |
| Reproducible baseline dependencies | `constraints.txt` records the dependency graph from the fresh Windows/Conda/Python 3.11 install smoke, and setup scripts install with those constraints when present. | Verified |
| ASR native dependency isolation | `core.asr_worker` handles ASR import/model/transcription in a child Python process; server startup and pipeline call the worker instead of importing `core.asr_engine` in-process. | Verified |
| Clone-friendly Windows startup | `setup_env.bat`, `setup_asr_cuda.bat`, and `start.bat` auto-detect Conda and support environment-variable overrides; `start.bat` runs a preflight doctor check before startup. | Verified |
| Local-only artifacts excluded | `.gitignore` excludes `config.toml`, `.env`, downloaded tools, local models, benchmark output, and diagnostics. | Verified |
| No vendored `jieba` / no Git LFS checkout requirement | `app/jieba` and `.gitattributes` are removed; `requirements.txt` includes `jieba`; tests pass using the PyPI package. | Verified |
| Diagnostics | `scripts/doctor.py` checks baseline imports/tools and optional ASR imports in subprocesses. | Verified |
| Troubleshooting docs | `docs/troubleshooting.md` covers setup, external tools, PaddleOCR model download, Bilibili download issues, ASR, CUDA, and port conflicts. | Verified |
| Server smoke | `scripts/smoke_server.py` checks `/health` and can optionally submit/poll `/extract`. | Verified |
| Performance baseline | `docs/performance.md` records the Bilibili sample, CPU OCR timing, CPU ASR timing, CUDA ASR timing, and reproduction commands. | Verified |
| CI guardrails | GitHub Actions run lint, compileall, entrypoint help checks, and tests without pulling heavy OCR/ASR model stacks. | Verified |
| Tag-triggered release automation | `.github/workflows/release.yml` runs lightweight verification on `v*` tags, creates source and Chrome extension archives, writes SHA256 checksums, and publishes a GitHub Release. | Ready |
| Chrome extension API contract | `popup.js` submits `roi_bottom`, `roi_top`, `enable_asr`, and `model_size`; tests guard these fields and ASR opt-in default. | Verified |

## Latest Local Verification

Executed in the `subtitle-extractor` conda environment:

```powershell
python -m pytest -q
python -m flake8 app/core app/main.py app/server.py scripts --select=F
python -m compileall -q app tests scripts
python app/main.py --help
python scripts/benchmark_runtime.py --help
python scripts/smoke_server.py --help
python scripts/doctor.py
python scripts/smoke_server.py --json
```

Observed results:

- Test suite: 92 passed.
- Lint: passed.
- Compileall: passed.
- Help entrypoints: passed.
- Doctor: `Required baseline: OK`.
- Real server smoke: `/health` returned `status=ok`, `ocr_backend=paddle`, `ocr_use_gpu=false`, `asr_available=true`.

## Committed-Tree Smoke

After the distributable baseline commit, a temporary local clone was created under `local_dev/release_clone_smoke` and checked with the existing `subtitle-extractor` conda environment:

```powershell
python -m pytest -q
python -m flake8 app/core app/main.py app/server.py scripts --select=F
python -m compileall -q app tests scripts
python app/main.py --help
python scripts/benchmark_runtime.py --help
python scripts/smoke_server.py --help
```

Observed results:

- Test suite: 92 passed.
- Lint: passed.
- Compileall: passed.
- Help entrypoints: passed.

## Fresh Install Smoke

To verify the from-zero setup path, a new local clone and a new Conda prefix environment were created on 2026-05-29:

- Clone: `local_dev/fresh_clone_requirements_smoke_20260529_104055`
- Conda prefix: `local_dev/conda_fresh_smoke_20260529_104055`
- Python: 3.11.15

Executed in the fresh clone:

```powershell
python -m pip install -r requirements.txt
python app/main.py --help
python scripts/benchmark_runtime.py --help
python scripts/smoke_server.py --help
$env:PADDLE_OCR_BASE_DIR = "<fresh clone>/paddleocr_cache_empty"
python -c "import sys, json; sys.path.insert(0, 'app'); import server; print(json.dumps(server.health(), ensure_ascii=False, sort_keys=True))"
python scripts/doctor.py
powershell -ExecutionPolicy Bypass -File scripts/download_tools.ps1
python scripts/doctor.py
```

Observed results:

- `pip install -r requirements.txt`: passed with `paddleocr==2.10.0` and `paddlepaddle==2.6.2`.
- Help entrypoints: passed.
- First server import initialized PaddleOCR CPU and downloaded PaddleOCR models into the forced fresh `PADDLE_OCR_BASE_DIR`.
- `/health` equivalent import check returned `status=ok`, `ocr_backend=paddle`, `ocr_use_gpu=false`, `asr_enabled=false`, `asr_available=false`.
- HTTP smoke against a real uvicorn process on `127.0.0.1:8765`: passed.
- `doctor.py` before tool download reported Python imports OK and `yt-dlp` missing, as expected.
- `scripts/download_tools.ps1`: downloaded clone-local `app/yt-dlp.exe` and `app/ffmpeg.exe`.
- `doctor.py` after tool download: `Required baseline: OK`.
- Direct PaddleOCR CPU inference on an in-memory test image returned `HELLO 123`.
- End-to-end `/extract` smoke against the Bilibili sample `BV1F3GH6bEGw`: passed with ASR disabled.
- The fresh clone produced `output/subtitle_BV1F3GH6bEGw.txt` and returned task status `done`, progress `100`, title `在AI时代，许多数学博士生都感到无比的迷茫`.

## Remaining Release Actions

- Tag or publish only after reviewing generated release notes from `CHANGELOG.md`.
