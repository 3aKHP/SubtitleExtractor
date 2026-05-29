import argparse
import json
import time

import httpx


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def check_health(client: httpx.Client, base_url: str) -> dict:
    response = client.get(_join_url(base_url, "/health"))
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"unexpected health status: {data}")
    if not data.get("ocr_backend"):
        raise RuntimeError(f"health response is missing ocr_backend: {data}")
    return data


def submit_extract(client: httpx.Client, base_url: str, url: str, enable_asr: bool) -> str:
    response = client.post(
        _join_url(base_url, "/extract"),
        json={"url": url, "enable_asr": enable_asr},
    )
    response.raise_for_status()
    data = response.json()
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError(f"submit response is missing task_id: {data}")
    return task_id


def get_status(client: httpx.Client, base_url: str, task_id: str) -> dict:
    response = client.get(_join_url(base_url, f"/status/{task_id}"))
    response.raise_for_status()
    return response.json()


def wait_for_task(
    client: httpx.Client,
    base_url: str,
    task_id: str,
    max_wait: float,
    poll_interval: float,
) -> dict:
    deadline = time.monotonic() + max_wait
    last_status = {}
    while time.monotonic() < deadline:
        last_status = get_status(client, base_url, task_id)
        state = last_status.get("status")
        if state == "done":
            return last_status
        if state == "error":
            raise RuntimeError(f"task failed: {last_status.get('error')}")
        time.sleep(poll_interval)
    raise TimeoutError(f"task did not finish within {max_wait:.0f}s: {last_status}")


def run_smoke(args: argparse.Namespace) -> dict:
    result = {
        "ok": True,
        "base_url": args.base_url,
        "health": None,
        "task_id": None,
        "task": None,
    }
    with httpx.Client(timeout=args.timeout) as client:
        result["health"] = check_health(client, args.base_url)
        if args.url:
            task_id = submit_extract(client, args.base_url, args.url, args.enable_asr)
            result["task_id"] = task_id
            if args.wait:
                result["task"] = wait_for_task(
                    client,
                    args.base_url,
                    task_id,
                    max_wait=args.max_wait,
                    poll_interval=args.poll_interval,
                )
    return result


def print_text(result: dict) -> None:
    health = result["health"]
    print(f"Server: {result['base_url']}")
    print(f"Health: ok, OCR={health.get('ocr_backend')} GPU={health.get('ocr_use_gpu')}")
    print(f"ASR: enabled={health.get('asr_enabled')} available={health.get('asr_available')}")
    print(f"Config: {health.get('config_path')}")
    if result.get("task_id"):
        print(f"Task: {result['task_id']}")
    if result.get("task"):
        task = result["task"]
        print(f"Task status: {task.get('status')} progress={task.get('progress')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test a running SubtitleExtractor server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--url", help="Optional video URL to submit to /extract.")
    parser.add_argument("--enable-asr", action="store_true", help="Enable ASR for the submitted URL.")
    parser.add_argument("--wait", action="store_true", help="Poll /status until the submitted task finishes.")
    parser.add_argument("--max-wait", type=float, default=1800)
    parser.add_argument("--poll-interval", type=float, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_smoke(args)
    except Exception as exc:
        result = {
            "ok": False,
            "base_url": args.base_url,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["error"])
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
