import tomllib
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.toml"

def _load():
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"未找到 config.toml，请复制 config.toml.example 并重命名。\n"
            f"期望路径: {_CONFIG_PATH}"
        )
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)

_cfg = _load()

server   = _cfg["server"]
ocr      = _cfg["ocr"]
asr      = _cfg["asr"]
extraction = _cfg["extraction"]
downloader = _cfg["downloader"]
