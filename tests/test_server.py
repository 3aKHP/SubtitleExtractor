import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # mock 掉启动时的重型初始化
    with patch("core.ocr_engine.OCREngine.__init__", return_value=None):
        import app.server as server_mod
        server_mod.global_ocr = MagicMock()
        yield TestClient(server_mod.app)


class TestSubmitTask:
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
