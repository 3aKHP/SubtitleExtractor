import pytest
from pathlib import Path
import textwrap


class TestConfigLoad:
    def test_loads_all_sections(self):
        from core import config
        assert "host" in config.server
        assert "use_gpu" in config.ocr
        assert "enabled" in config.asr
        assert "default_model_size" in config.asr
        assert "default_roi_bottom" in config.extraction
        assert "user_agent" in config.downloader

    def test_values_match_fixture(self):
        from core import config
        assert config.server["port"] == 8000
        assert config.ocr["use_gpu"] is False
        assert config.asr["enabled"] is False
        assert config.extraction["similarity_threshold"] == 0.7

    def test_ocr_remote_defaults(self):
        from core import config
        assert config.ocr["backend"] == "paddle"
        assert config.ocr["remote_url"] == "https://api.siliconflow.cn/v1/chat/completions"
        assert config.ocr["remote_api_key"] == ""
        assert config.ocr["remote_model"] == "deepseek-ai/DeepSeek-OCR"
        assert config.ocr["remote_timeout"] == 120
        assert config.ocr["remote_max_concurrency"] == 3

    def test_load_falls_back_to_example(self, tmp_path, monkeypatch):
        import core.config as cfg_mod
        example_path = tmp_path / "config.toml.example"
        example_path.write_text(textwrap.dedent("""\
            [server]
            host = "127.0.0.1"
            port = 9001

            [ocr]
            backend = "paddle"
            use_gpu = false
            confidence_threshold = 0.6

            [asr]
            enabled = false
            default_model_size = "small"
            device = "cpu"

            [extraction]
            default_roi_bottom = 0.0
            default_roi_top = 0.2
            default_step = 10
            default_include_timestamp = true
            similarity_threshold = 0.7
            history_size = 3

            [downloader]
            user_agent = "TestAgent/1.0"
            video_format = "best"
            socket_timeout = 30
            retries = 3
        """), encoding="utf-8")

        monkeypatch.setattr(cfg_mod, "_CONFIG_PATH", tmp_path / "nonexistent.toml")
        monkeypatch.setattr(cfg_mod, "_DEFAULT_CONFIG_PATH", example_path)
        cfg = cfg_mod._load()
        assert cfg["server"]["port"] == 9001

    def test_missing_config_and_example_raises(self, tmp_path, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_CONFIG_PATH", tmp_path / "nonexistent.toml")
        monkeypatch.setattr(cfg_mod, "_DEFAULT_CONFIG_PATH", tmp_path / "missing.example.toml")
        with pytest.raises(FileNotFoundError, match="config.toml"):
            cfg_mod._load()
