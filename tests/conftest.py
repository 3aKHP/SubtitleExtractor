import sys
import os
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
    每个测试前写一份临时 config.toml，并把 core.config 的路径指向它。
    autouse=True 保证所有测试都能 import core.config 而不报 FileNotFoundError。
    """
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(MINIMAL_CONFIG, encoding="utf-8")

    # 重新加载 config 模块，指向临时文件
    import importlib
    # 先确保模块已在 sys.modules 里（可能还没 import）
    if "core.config" in sys.modules:
        del sys.modules["core.config"]
    if "core" in sys.modules:
        del sys.modules["core"]

    monkeypatch.setenv("SUBTITLE_CONFIG_PATH", str(cfg_file))

    # patch config 模块里的 _CONFIG_PATH
    import core.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "_CONFIG_PATH", cfg_file)
    # 重新执行加载
    cfg_mod._cfg = cfg_mod._load()
    cfg_mod.server     = cfg_mod._cfg["server"]
    cfg_mod.ocr        = cfg_mod._cfg["ocr"]
    cfg_mod.asr        = cfg_mod._cfg["asr"]
    cfg_mod.extraction = cfg_mod._cfg["extraction"]
    cfg_mod.downloader = cfg_mod._cfg["downloader"]
