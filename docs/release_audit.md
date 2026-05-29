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
| ASR native dependency isolation | `core.asr_worker` handles ASR import/model/transcription in a child Python process; server startup and pipeline call the worker instead of importing `core.asr_engine` in-process. | Verified |
| Clone-friendly Windows startup | `setup_env.bat`, `setup_asr_cuda.bat`, and `start.bat` auto-detect Conda and support environment-variable overrides. | Verified |
| Local-only artifacts excluded | `.gitignore` excludes `config.toml`, `.env`, downloaded tools, local models, benchmark output, and diagnostics. | Verified |
| No vendored `jieba` / no Git LFS checkout requirement | `app/jieba` and `.gitattributes` are removed; `requirements.txt` includes `jieba`; tests pass using the PyPI package. | Verified |
| Diagnostics | `scripts/doctor.py` checks baseline imports/tools and optional ASR imports in subprocesses. | Verified |
| Server smoke | `scripts/smoke_server.py` checks `/health` and can optionally submit/poll `/extract`. | Verified |
| Performance baseline | `docs/performance.md` records the Bilibili sample, CPU OCR timing, CPU ASR timing, CUDA ASR timing, and reproduction commands. | Verified |
| CI guardrails | GitHub Actions run lint, compileall, entrypoint help checks, and tests without pulling heavy OCR/ASR model stacks. | Verified |
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

## Remaining Release Actions

- Optionally run `setup_env.bat` on a clean Windows machine or VM for a full fresh-clone install proof.
- Tag or publish only after reviewing generated release notes from `CHANGELOG.md`.
