import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # mock 掉启动时的重型初始化
    with (
        patch("core.ocr_engine.create_ocr_engine", return_value=MagicMock()),
        patch("core.asr_worker.check_asr_available", return_value=False),
    ):
        import app.server as server_mod
        server_mod.global_ocr = MagicMock()
        server_mod._asr_available = False
        yield TestClient(server_mod.app)


def test_startup_uses_asr_worker_check(monkeypatch):
    sys.modules.pop("app.server", None)
    monkeypatch.delitem(sys.modules, "core.asr_engine", raising=False)

    import core.asr_worker as asr_worker

    calls = []
    monkeypatch.setattr(asr_worker, "check_asr_available", lambda: calls.append(True) or False)

    with patch("core.ocr_engine.create_ocr_engine", return_value=MagicMock()):
        import app.server as server_mod

    assert calls == [True]
    assert server_mod._asr_available is False
    assert "core.asr_engine" not in sys.modules


class TestSubmitTask:
    def test_request_defaults_disable_asr(self, client):
        import app.server as server_mod
        request = server_mod.VideoRequest(url="https://www.bilibili.com/video/BV1")
        assert request.enable_asr is False

    def test_returns_task_id(self, client):
        with patch("app.server.background_task"):
            resp = client.post("/extract", json={"url": "https://www.bilibili.com/video/BV1"})
        assert resp.status_code == 200
        assert "task_id" in resp.json()

    def test_task_initially_running(self, client):
        with patch("app.server.background_task"):
            resp = client.post("/extract", json={"url": "https://www.bilibili.com/video/BV1"})
        task_id = resp.json()["task_id"]

        status = client.get(f"/status/{task_id}")
        assert status.json()["status"] == "running"


class TestGetStatus:
    def test_health(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "ok"
        assert data["ocr_backend"] == "paddle"
        assert data["asr_enabled"] is False
        assert "asr_available" in data

    def test_404_for_unknown_task(self, client):
        resp = client.get("/status/nonexistent-id")
        assert resp.status_code == 404

    def test_returns_task_state(self, client):
        import app.server as server_mod
        task_id = "test-task-123"
        server_mod.TASKS[task_id] = {
            "status": "done", "progress": 100,
            "message": "完成", "result": {"merged_subtitles": "hello"}
        }
        resp = client.get(f"/status/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"
