import subprocess
import sys

import pytest


def test_transcribe_audio_uses_worker_and_parses_segments(monkeypatch):
    from core import asr_worker

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout='{"ok": true, "segments": [{"start": 1.0, "end": 2.0, "text": "你好"}]}',
            stderr="",
        )

    monkeypatch.setattr(asr_worker.subprocess, "run", fake_run)

    segments = asr_worker.transcribe_audio("audio.wav", model_size="small", device="cpu")

    assert segments == [{"start": 1.0, "end": 2.0, "text": "你好"}]
    assert captured["cmd"][:3] == [sys.executable, "-m", "core.asr_worker"]
    assert str(asr_worker.APP_DIR) in captured["env"]["PYTHONPATH"]
    assert captured["env"]["PYTHONIOENCODING"] == "utf-8"


def test_transcribe_audio_raises_worker_error(monkeypatch):
    from core import asr_worker

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            1,
            stdout='{"ok": false, "error": "RuntimeError: boom"}',
            stderr="details",
        )

    monkeypatch.setattr(asr_worker.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        asr_worker.transcribe_audio("audio.wav")


def test_check_asr_available_returns_false_on_worker_failure(monkeypatch):
    from core import asr_worker

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="not json", stderr="missing")

    monkeypatch.setattr(asr_worker.subprocess, "run", fake_run)

    assert asr_worker.check_asr_available() is False
