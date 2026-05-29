import tomllib
from pathlib import Path

_ROOT_DIR = Path(__file__).parent.parent.parent
_CONFIG_PATH = _ROOT_DIR / "config.toml"
_DEFAULT_CONFIG_PATH = _ROOT_DIR / "config.toml.example"


def _resolve_path() -> Path:
    if _CONFIG_PATH.exists():
        return _CONFIG_PATH
    if _DEFAULT_CONFIG_PATH.exists():
        return _DEFAULT_CONFIG_PATH
    raise FileNotFoundError(
        "未找到 config.toml 或 config.toml.example。\n"
        f"期望路径: {_CONFIG_PATH}\n"
        f"默认模板: {_DEFAULT_CONFIG_PATH}"
    )


def _load():
    path = _resolve_path()
    with open(path, "rb") as f:
        return tomllib.load(f)


config_path = _resolve_path()
_cfg = _load()

server = _cfg["server"]
ocr = _cfg["ocr"]
asr = _cfg["asr"]
extraction = _cfg["extraction"]
downloader = _cfg["downloader"]
