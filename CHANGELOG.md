# Changelog

## Unreleased

- Set PaddleOCR CPU as the default supported OCR path.
- Split Faster-Whisper / ctranslate2 into optional ASR dependencies.
- Run ASR health checks and transcription through an isolated worker process.
- Add runtime diagnostics, server smoke testing, and performance benchmarking scripts.
- Make Windows setup/start scripts clone-friendly and configurable.
- Add verified dependency constraints for the PaddleOCR CPU baseline.
- Run a startup preflight check from `start.bat`.
- Add troubleshooting documentation for setup, tools, PaddleOCR model downloads, Bilibili downloads, ASR, CUDA, and port conflicts.
- Remove vendored `jieba` and Git LFS requirements; use the PyPI dependency instead.
- Keep local config, downloaded tools, model caches, diagnostics, and benchmark output out of version control.
