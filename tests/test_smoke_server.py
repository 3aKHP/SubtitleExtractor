import argparse

import pytest

from scripts import smoke_server


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, statuses=None):
        self.statuses = list(statuses or [])
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        if url.endswith("/health"):
            return FakeResponse({
                "status": "ok",
                "ocr_backend": "paddle",
                "ocr_use_gpu": False,
                "asr_enabled": False,
                "asr_available": True,
                "config_path": "config.toml.example",
            })
        return FakeResponse(self.statuses.pop(0))

    def post(self, url, json):
        self.posts.append((url, json))
        return FakeResponse({"task_id": "task-1"})


def make_args(**overrides):
    defaults = {
        "base_url": "http://testserver",
        "timeout": 10,
        "url": None,
        "enable_asr": False,
        "wait": False,
        "max_wait": 10,
        "poll_interval": 0,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_check_health_requires_ok_status():
    client = FakeClient()

    data = smoke_server.check_health(client, "http://testserver")

    assert data["ocr_backend"] == "paddle"


def test_submit_extract_returns_task_id():
    client = FakeClient()

    task_id = smoke_server.submit_extract(client, "http://testserver", "https://example.test/video", True)

    assert task_id == "task-1"
    assert client.posts == [
        ("http://testserver/extract", {"url": "https://example.test/video", "enable_asr": True})
    ]


def test_wait_for_task_returns_done_status():
    client = FakeClient(statuses=[
        {"status": "running", "progress": 10},
        {"status": "done", "progress": 100},
    ])

    status = smoke_server.wait_for_task(client, "http://testserver", "task-1", 10, 0)

    assert status["status"] == "done"


def test_wait_for_task_raises_on_error_status():
    client = FakeClient(statuses=[{"status": "error", "error": "boom"}])

    with pytest.raises(RuntimeError, match="boom"):
        smoke_server.wait_for_task(client, "http://testserver", "task-1", 10, 0)


def test_run_smoke_health_only(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(smoke_server.httpx, "Client", lambda timeout: fake_client)

    result = smoke_server.run_smoke(make_args())

    assert result["ok"] is True
    assert result["health"]["ocr_backend"] == "paddle"
    assert result["task_id"] is None
