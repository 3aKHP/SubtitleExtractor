import pytest
import numpy as np
import httpx
from unittest.mock import patch, MagicMock


def _make_mock_response(content, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


class TestCreateEngine:
    def test_defaults_to_paddle(self):
        from core.ocr_engine import create_ocr_engine, PaddleOCREngine
        with patch.object(PaddleOCREngine, "__init__", return_value=None):
            engine = create_ocr_engine()
        assert isinstance(engine, PaddleOCREngine)

    def test_rapidocr_backend_is_not_supported(self, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setitem(cfg_mod.ocr, "backend", "rapidocr")
        from core.ocr_engine import create_ocr_engine
        with pytest.raises(ValueError, match="RapidOCR is not supported"):
            create_ocr_engine()

    def test_legacy_local_backend_is_not_supported(self, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setitem(cfg_mod.ocr, "backend", "local")
        from core.ocr_engine import create_ocr_engine
        with pytest.raises(ValueError, match="RapidOCR is not supported"):
            create_ocr_engine()

    def test_paddle_backend_with_use_gpu_argument(self, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setitem(cfg_mod.ocr, "backend", "paddle")
        from core.ocr_engine import create_ocr_engine, PaddleOCREngine
        with patch.object(PaddleOCREngine, "__init__", return_value=None):
            engine = create_ocr_engine(use_gpu=False)
        assert isinstance(engine, PaddleOCREngine)

    def test_unknown_backend_raises(self, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setitem(cfg_mod.ocr, "backend", "unknown")
        from core.ocr_engine import create_ocr_engine
        with pytest.raises(ValueError, match="Unsupported OCR backend"):
            create_ocr_engine()

    def test_remote_backend_requires_api_key(self, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setitem(cfg_mod.ocr, "backend", "remote")
        monkeypatch.setitem(cfg_mod.ocr, "remote_api_key", "")
        from core.ocr_engine import create_ocr_engine
        with pytest.raises(ValueError, match="remote_api_key"):
            create_ocr_engine()

    def test_remote_backend_with_key(self, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setitem(cfg_mod.ocr, "backend", "remote")
        monkeypatch.setitem(cfg_mod.ocr, "remote_api_key", "sk-test")
        from core.ocr_engine import create_ocr_engine, RemoteOCREngine
        engine = create_ocr_engine()
        assert isinstance(engine, RemoteOCREngine)


class TestPaddleOCREngine:
    def test_gpu_runtime_error_falls_back_to_cpu(self):
        from core.ocr_engine import PaddleOCREngine

        gpu_ocr = MagicMock()
        gpu_ocr.ocr.side_effect = RuntimeError("cudnn64_8.dll missing")
        cpu_ocr = MagicMock()
        cpu_ocr.ocr.return_value = [[
            [None, ("测试字幕", 0.95)],
        ]]

        engine = PaddleOCREngine.__new__(PaddleOCREngine)
        engine._confidence = 0.6
        engine._use_gpu = True
        engine.ocr = gpu_ocr
        engine._create_engine = MagicMock(return_value=cpu_ocr)

        result = engine.recognize(np.zeros((10, 10, 3), dtype=np.uint8))

        assert result == "测试字幕"
        assert engine._use_gpu is False
        engine._create_engine.assert_called_once_with(False)

    def test_cpu_runtime_error_is_not_swallowed(self):
        from core.ocr_engine import PaddleOCREngine

        cpu_ocr = MagicMock()
        cpu_ocr.ocr.side_effect = RuntimeError("unexpected failure")

        engine = PaddleOCREngine.__new__(PaddleOCREngine)
        engine._confidence = 0.6
        engine._use_gpu = False
        engine.ocr = cpu_ocr

        with pytest.raises(RuntimeError, match="unexpected failure"):
            engine.recognize(np.zeros((10, 10, 3), dtype=np.uint8))


class TestRemoteOCREngineRecognize:
    @pytest.fixture
    def engine(self):
        from core.ocr_engine import RemoteOCREngine
        return RemoteOCREngine(api_key="sk-test", base_url="http://fake/api", model="test-model")

    @pytest.fixture
    def sample_image(self):
        return np.zeros((50, 200, 3), dtype=np.uint8)

    def test_recognize_success(self, engine, sample_image):
        with patch("httpx.post", return_value=_make_mock_response("测试字幕")):
            result = engine.recognize(sample_image)
        assert result == "测试字幕"

    def test_recognize_empty_content(self, engine, sample_image):
        with patch("httpx.post", return_value=_make_mock_response("")):
            result = engine.recognize(sample_image)
        assert result == ""

    def test_recognize_http_400(self, engine, sample_image):
        with patch("httpx.post", return_value=_make_mock_response("", 400)):
            result = engine.recognize(sample_image)
        assert result == ""

    def test_recognize_http_429(self, engine, sample_image):
        with patch("httpx.post", return_value=_make_mock_response("", 429)):
            result = engine.recognize(sample_image)
        assert result == ""

    def test_recognize_http_500(self, engine, sample_image):
        with patch("httpx.post", return_value=_make_mock_response("", 500)):
            result = engine.recognize(sample_image)
        assert result == ""

    def test_recognize_connect_error(self, engine, sample_image):
        with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
            result = engine.recognize(sample_image)
        assert result == ""

    def test_recognize_timeout(self, engine, sample_image):
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            result = engine.recognize(sample_image)
        assert result == ""

    def test_recognize_malformed_json(self, engine, sample_image):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"no_choices_here": []}
        resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=resp):
            result = engine.recognize(sample_image)
        assert result == ""

    def test_image_encoding_format(self, engine, sample_image):
        data_uri = engine._encode_image(sample_image)
        assert data_uri.startswith("data:image/png;base64,")
        b64_part = data_uri[len("data:image/png;base64,"):]
        assert len(b64_part) > 0


class TestRemoteOCREngineBatch:
    @pytest.fixture
    def engine(self):
        from core.ocr_engine import RemoteOCREngine
        return RemoteOCREngine(api_key="sk-test", base_url="http://fake/api", model="test-model")

    @pytest.fixture
    def images(self):
        return [np.zeros((50, 200, 3), dtype=np.uint8) for _ in range(3)]

    def test_batch_preserves_order(self, engine, images):
        call_count = [0]

        def mock_recognize(img):
            idx = call_count[0]
            call_count[0] += 1
            return f"text_{idx}"

        with patch.object(engine, "recognize", side_effect=mock_recognize):
            results = engine.recognize_batch(images)
        assert results == ["text_0", "text_1", "text_2"]

    def test_batch_respects_concurrency(self, engine, images):
        with patch.object(engine, "recognize", return_value="ok"):
            results = engine.recognize_batch(images, concurrency=2)
        assert results == ["ok", "ok", "ok"]
