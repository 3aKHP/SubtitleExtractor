import sys
import textwrap
import pytest

MINIMAL_CONFIG = textwrap.dedent("""\
    [server]
    host = "127.0.0.1"
    port = 8000

    [ocr]
    use_gpu = false
    confidence_threshold = 0.85

    [asr]
    default_model_size = "small"
    device = "cpu"

    [extraction]
    default_roi = 0.8
    default_step = 10
    default_include_timestamp = true
    similarity_threshold = 0.7
    history_size = 3

    [downloader]
    user_agent = "TestAgent/1.0"
    video_format = "best"
    socket_timeout = 30
    retries = 3
""")

@pytest.fixture(autouse=True)
def patch_config(tmp_path, monkeypatch):
    """
    每个测试前把 core.config 的各节替换为测试用值。
    直接修改已有模块对象的属性，避免重建模块导致其他模块持有旧引用。
    """
    import tomllib
    cfg = tomllib.loads(MINIMAL_CONFIG)

    import core.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "server",     cfg["server"])
    monkeypatch.setattr(cfg_mod, "ocr",        cfg["ocr"])
    monkeypatch.setattr(cfg_mod, "asr",        cfg["asr"])
    monkeypatch.setattr(cfg_mod, "extraction", cfg["extraction"])
    monkeypatch.setattr(cfg_mod, "downloader", cfg["downloader"])
