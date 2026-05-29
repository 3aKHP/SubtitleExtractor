# Changelog

## Unreleased

- Set PaddleOCR CPU as the default supported OCR path.
- Split Faster-Whisper / ctranslate2 into optional ASR dependencies.
- Run ASR health checks and transcription through an isolated worker process.
- Add runtime diagnostics, server smoke testing, and performance benchmarking scripts.
- Make Windows setup/start scripts clone-friendly and configurable.
- Remove vendored `jieba` and Git LFS requirements; use the PyPI dependency instead.
- Keep local config, downloaded tools, model caches, diagnostics, and benchmark output out of version control.
