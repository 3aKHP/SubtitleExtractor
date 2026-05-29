import argparse
import json
import sys
import time
from pathlib import Path

import cv2

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class CountingOCR:
    def __init__(self, inner):
        self.inner = inner
        self.calls = 0
        self.nonempty = 0
        self.ocr_seconds = 0.0

    def recognize(self, image):
        self.calls += 1
        started = time.perf_counter()
        text = self.inner.recognize(image)
        self.ocr_seconds += time.perf_counter() - started
        if text:
            self.nonempty += 1
        return text


def get_video_info(video_path: Path) -> dict:
    cap = cv2.VideoCapture(str(video_path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        cap.release()

    duration = frames / fps if fps else 0
    return {
        "fps": fps,
        "frames": frames,
        "width": width,
        "height": height,
        "duration_sec": duration,
    }


def benchmark_ocr(args, output_dir: Path) -> dict:
    from core.ocr_engine import create_ocr_engine
    from core.pipeline import run_ocr

    engine = CountingOCR(create_ocr_engine(use_gpu=args.ocr_use_gpu))
    started = time.perf_counter()
    text = run_ocr(
        str(args.video),
        str(output_dir),
        engine,
        roi_bottom=args.roi_bottom,
        roi_top=args.roi_top,
        step=args.step,
        include_timestamp=True,
    )
    elapsed = time.perf_counter() - started
    lines = [line for line in text.splitlines() if line.strip()]
    return {
        "enabled": True,
        "elapsed_sec": elapsed,
        "ocr_calls": engine.calls,
        "ocr_nonempty": engine.nonempty,
        "ocr_inner_sec": engine.ocr_seconds,
        "output_lines": len(lines),
        "chars": len(text),
        "sample": lines[:5],
    }


def ensure_audio(video_path: Path, output_dir: Path) -> tuple[Path, float]:
    from core.pipeline import extract_audio

    audio_path = output_dir / f"{video_path.stem}_asr.wav"
    started = time.perf_counter()
    ok = extract_audio(str(video_path), str(audio_path))
    elapsed = time.perf_counter() - started
    if not ok:
        raise RuntimeError("failed to extract audio")
    return audio_path, elapsed


def benchmark_asr(audio_path: Path, model_size: str, device: str) -> dict:
    from core.asr_worker import transcribe_audio_payload

    started = time.perf_counter()
    payload = transcribe_audio_payload(str(audio_path), model_size=model_size, device=device)
    worker_wall_sec = time.perf_counter() - started
    segments = payload["segments"]
    load_sec = payload.get("load_sec", 0.0)
    transcribe_sec = payload.get("transcribe_sec", 0.0)

    return {
        "requested_device": device,
        "actual_device": payload.get("device"),
        "model_size": payload.get("model_size", model_size),
        "load_sec": load_sec,
        "transcribe_sec": transcribe_sec,
        "total_sec": load_sec + transcribe_sec,
        "worker_wall_sec": worker_wall_sec,
        "segments": len(segments),
        "sample": [seg["text"] for seg in segments[:5]],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark OCR and ASR runtime on a local video.")
    parser.add_argument("video", type=Path, help="Local video path.")
    parser.add_argument("--output-dir", type=Path, default=Path("local_dev/bench_output"))
    parser.add_argument("--roi-bottom", type=float, default=0.0)
    parser.add_argument("--roi-top", type=float, default=0.2)
    parser.add_argument("--step", type=int, default=10)
    parser.add_argument("--skip-ocr", action="store_true")
    parser.add_argument("--skip-asr", action="store_true")
    parser.add_argument("--ocr-use-gpu", action="store_true")
    parser.add_argument("--asr-model", default="small")
    parser.add_argument("--asr-devices", default="cpu,cuda", help="Comma-separated devices, e.g. cpu,cuda.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.video = args.video.resolve()
    if not args.video.exists():
        print(f"Video not found: {args.video}", file=sys.stderr)
        return 2

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "video": str(args.video),
        "video_info": get_video_info(args.video),
        "settings": {
            "roi_bottom": args.roi_bottom,
            "roi_top": args.roi_top,
            "step": args.step,
            "ocr_use_gpu": args.ocr_use_gpu,
            "asr_model": args.asr_model,
            "asr_devices": args.asr_devices,
        },
        "ocr": {"enabled": False},
        "audio_extract": {"enabled": False},
        "asr": [],
    }

    if not args.skip_ocr:
        result["ocr"] = benchmark_ocr(args, output_dir)

    if not args.skip_asr:
        audio_path, audio_sec = ensure_audio(args.video, output_dir)
        result["audio_extract"] = {
            "enabled": True,
            "audio_path": str(audio_path),
            "elapsed_sec": audio_sec,
        }
        devices = [item.strip() for item in args.asr_devices.split(",") if item.strip()]
        for device in devices:
            try:
                result["asr"].append(benchmark_asr(audio_path, args.asr_model, device))
            except Exception as exc:
                result["asr"].append({
                    "requested_device": device,
                    "error": f"{type(exc).__name__}: {exc}",
                })

    output_path = output_dir / f"benchmark_{args.video.stem}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nSaved benchmark result: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
