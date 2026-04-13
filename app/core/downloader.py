import os
import json
import subprocess
from core import config

def _app_dir() -> str:
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def _ytdlp_exe() -> str:
    local = os.path.join(_app_dir(), "yt-dlp.exe")
    return local if os.path.exists(local) else "yt-dlp"

def _popen_flags() -> int:
    return 0x08000000 if os.name == "nt" else 0

def get_video_metadata(url: str) -> dict:
    cmd = [
        _ytdlp_exe(), url,
        "--dump-json", "--no-playlist", "--no-warnings",
        "--socket-timeout", str(config.downloader["socket_timeout"]),
        "--retries", str(config.downloader["retries"]),
        "--user-agent", config.downloader["user_agent"],
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="ignore",
        creationflags=_popen_flags()
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"获取元数据失败: {stderr}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError("无法解析视频元数据 JSON")

def download_video(url: str, save_path: str) -> None:
    cmd = [
        _ytdlp_exe(), url,
        "-f", config.downloader["video_format"],
        "--merge-output-format", "mp4",
        "-o", save_path,
        "--ffmpeg-location", _app_dir(),
        "--no-warnings", "--no-playlist",
        "--socket-timeout", str(config.downloader["socket_timeout"]),
        "--retries", str(config.downloader["retries"]),
        "--fragment-retries", str(config.downloader["retries"]),
        "--user-agent", config.downloader["user_agent"],
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="ignore",
        creationflags=_popen_flags()
    )
    _, stderr = proc.communicate()
    if proc.returncode != 0 and not os.path.exists(save_path):
        raise RuntimeError(f"下载失败: {stderr}")
