import pytest
from pathlib import Path
import textwrap


class TestConfigLoad:
    def test_loads_all_sections(self):
        from core import config
        assert "host" in config.server
        assert "use_gpu" in config.ocr
        assert "default_model_size" in config.asr
        assert "default_roi" in config.extraction
        assert "user_agent" in config.downloader

    def test_values_match_fixture(self):
        from core import config
        assert config.server["port"] == 8000
        assert config.ocr["use_gpu"] is False
        assert config.extraction["similarity_threshold"] == 0.7

    def test_missing_config_raises(self, tmp_path, monkeypatch):
        import core.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_CONFIG_PATH", tmp_path / "nonexistent.toml")
        with pytest.raises(FileNotFoundError, match="config.toml"):
            cfg_mod._load()
