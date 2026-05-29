import argparse
import importlib
import json
import os
import subprocess
import sys
import time
import traceback
from contextlib import redirect_stdout
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
OPTIONAL_ASR_IMPORTS = ("ctranslate2", "faster_whisper")


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _startupinfo():
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def _worker_env() -> dict:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    paths = [str(APP_DIR)]
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _worker_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "core.asr_worker", *args]


def _run_worker(args: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        _worker_cmd(*args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_worker_env(),
        startupinfo=_startupinfo(),
        timeout=timeout,
    )


def _parse_worker_json(proc: subprocess.CompletedProcess) -> dict:
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        detail = stderr or stdout or str(exc)
        raise RuntimeError(f"ASR worker returned invalid JSON: {detail}") from exc

    if proc.returncode != 0 or not payload.get("ok"):
        error = payload.get("error") or proc.stderr.strip() or f"exit code {proc.returncode}"
        raise RuntimeError(error)

    return payload


def check_asr_available(timeout: float = 30) -> bool:
    try:
        proc = _run_worker(["--check"], timeout=timeout)
        _parse_worker_json(proc)
        return True
    except Exception:
        return False


def transcribe_audio_payload(
    audio_path: str,
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    beam_size: int = 5,
) -> dict:
    args = [audio_path, "--beam-size", str(beam_size)]
    if model_size:
        args.extend(["--model-size", model_size])
    if device:
        args.extend(["--device", device])
    if compute_type:
        args.extend(["--compute-type", compute_type])

    proc = _run_worker(args)
    return _parse_worker_json(proc)


def transcribe_audio(
    audio_path: str,
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    beam_size: int = 5,
) -> list[dict]:
    payload = transcribe_audio_payload(
        audio_path,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        beam_size=beam_size,
    )
    return payload["segments"]


def _module_versions() -> dict:
    modules = {}
    for name in OPTIONAL_ASR_IMPORTS:
        module = importlib.import_module(name)
        modules[name] = getattr(module, "__version__", None)
    importlib.import_module("core.asr_engine")
    return modules


def _check_payload() -> dict:
    with redirect_stdout(sys.stderr):
        modules = _module_versions()
    return {"ok": True, "modules": modules}


def _transcribe_payload(args: argparse.Namespace) -> dict:
    engine = None
    try:
        with redirect_stdout(sys.stderr):
            from core.asr_engine import ASREngine

            started = time.perf_counter()
            engine = ASREngine(
                model_size=args.model_size,
                device=args.device,
                compute_type=args.compute_type,
            )
            load_sec = time.perf_counter() - started
            started = time.perf_counter()
            segments = engine.transcribe(args.audio_path, beam_size=args.beam_size)
            transcribe_sec = time.perf_counter() - started

        return {
            "ok": True,
            "model_size": engine.model_size,
            "device": engine.device,
            "load_sec": load_sec,
            "transcribe_sec": transcribe_sec,
            "segments": segments,
        }
    finally:
        if engine is not None:
            with redirect_stdout(sys.stderr):
                engine.release()


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Isolated Faster-Whisper ASR worker.")
    parser.add_argument("audio_path", nargs="?", help="Path to a 16 kHz mono wav file.")
    parser.add_argument("--check", action="store_true", help="Check whether optional ASR imports work.")
    parser.add_argument("--model-size", default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--compute-type", default=None)
    parser.add_argument("--beam-size", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    _configure_stdio()
    args = parse_args()
    try:
        if args.check:
            _emit(_check_payload())
            return 0
        if not args.audio_path:
            raise ValueError("audio_path is required unless --check is used")
        _emit(_transcribe_payload(args))
        return 0
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
