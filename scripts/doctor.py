import argparse
import subprocess
import importlib
import json
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


REQUIRED_IMPORTS = [
    "cv2",
    "fastapi",
    "httpx",
    "jieba",
    "numpy",
    "paddle",
    "paddleocr",
    "pydantic",
    "pypinyin",
    "tqdm",
    "uvicorn",
]

OPTIONAL_ASR_IMPORTS = [
    "ctranslate2",
    "faster_whisper",
]


def check_import(module_name: str) -> dict:
    try:
        module = importlib.import_module(module_name)
        return {
            "ok": True,
            "version": getattr(module, "__version__", None),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def check_import_subprocess(module_name: str) -> dict:
    code = (
        "import importlib, json; "
        f"module = importlib.import_module({module_name!r}); "
        "print(json.dumps({'ok': True, 'version': getattr(module, '__version__', None)}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode == 0:
        return json.loads(proc.stdout)
    return {
        "ok": False,
        "error": proc.stderr.strip() or proc.stdout.strip(),
    }


def check_executable(name: str, local_path: Path) -> dict:
    path = local_path if local_path.exists() else None
    source = "local" if path else None
    if path is None:
        found = shutil.which(name)
        if found:
            path = Path(found)
            source = "PATH"

    return {
        "ok": path is not None,
        "path": str(path) if path else None,
        "source": source,
    }


def run_checks() -> dict:
    from core import config

    required_imports = {name: check_import(name) for name in REQUIRED_IMPORTS}
    optional_asr = {name: check_import_subprocess(name) for name in OPTIONAL_ASR_IMPORTS}
    tools = {
        "ffmpeg": check_executable("ffmpeg", APP_DIR / "ffmpeg.exe"),
        "yt-dlp": check_executable("yt-dlp", APP_DIR / "yt-dlp.exe"),
    }

    required_ok = (
        sys.version_info >= (3, 11)
        and all(item["ok"] for item in required_imports.values())
        and all(item["ok"] for item in tools.values())
    )

    return {
        "required_ok": required_ok,
        "python": sys.version,
        "config_path": str(config.config_path),
        "ocr": {
            "backend": config.ocr.get("backend"),
            "use_gpu": config.ocr.get("use_gpu"),
        },
        "asr": {
            "enabled": config.asr.get("enabled", False),
            "optional_imports": optional_asr,
        },
        "required_imports": required_imports,
        "tools": tools,
    }


def print_text(result: dict) -> None:
    print(f"Python: {result['python'].splitlines()[0]}")
    print(f"Config: {result['config_path']}")
    print(f"OCR: backend={result['ocr']['backend']} use_gpu={result['ocr']['use_gpu']}")
    print(f"ASR: enabled={result['asr']['enabled']}")
    print("")
    print("Required imports:")
    for name, item in result["required_imports"].items():
        status = "OK" if item["ok"] else "MISSING"
        suffix = f" ({item['version']})" if item.get("version") else ""
        print(f"  {status:7} {name}{suffix}")
    print("")
    print("Tools:")
    for name, item in result["tools"].items():
        status = "OK" if item["ok"] else "MISSING"
        path = item["path"] or "not found"
        print(f"  {status:7} {name}: {path}")
    print("")
    print("Optional ASR imports:")
    for name, item in result["asr"]["optional_imports"].items():
        status = "OK" if item["ok"] else "MISSING"
        suffix = f" ({item['version']})" if item.get("version") else ""
        print(f"  {status:7} {name}{suffix}")
    print("")
    print("Required baseline:", "OK" if result["required_ok"] else "FAILED")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check SubtitleExtractor runtime prerequisites.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_checks()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 0 if result["required_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
