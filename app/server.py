import os
import shutil
import threading
import uuid
import gc
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core import config
from core.ocr_engine import OCREngine
from core.pipeline import run_full_pipeline
from core.downloader import get_video_metadata, download_video

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    temp_dir = os.path.abspath("temp_download")
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    os.makedirs(temp_dir, exist_ok=True)
    yield

app = FastAPI(title="Bilibili Subtitle Extractor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 任务状态表（内存，重启清空）
TASKS: dict = {}
_TASK_LOCK = threading.Lock()

print("🚀 正在初始化全局 OCR 引擎...")
global_ocr = OCREngine()

class VideoRequest(BaseModel):
    url: str
    roi: float = config.extraction["default_roi"]
    step: int = config.extraction["default_step"]
    timestamp: bool = config.extraction["default_include_timestamp"]
    enable_asr: bool = True
    model_size: str = config.asr["default_model_size"]


def background_task(task_id: str, request: VideoRequest):
    base_dir = os.getcwd()
    temp_dir = os.path.join(base_dir, "temp_download")
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    def update(percent: int, msg: str):
        with _TASK_LOCK:
            TASKS[task_id]["progress"] = percent
            TASKS[task_id]["message"] = msg
        print(f"[{task_id[:6]}] {percent}%: {msg}")

    video_path = None
    try:
        update(5, "正在获取视频信息...")
        info = get_video_metadata(request.url)
        video_title = info.get("title", "Unknown")

        update(10, f"正在下载: {video_title}...")
        filename = f"{info.get('id', 'video')}.mp4"
        video_path = os.path.join(temp_dir, filename)

        if not os.path.exists(video_path):
            download_video(request.url, video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError("视频下载失败")

        def pipeline_cb(pct, msg):
            # 映射到整体进度 15~98%
            update(15 + int(pct * 0.83), msg)

        result = run_full_pipeline(
            video_path,
            output_dir,
            global_ocr,
            roi_ratio=request.roi,
            step=request.step,
            include_timestamp=request.timestamp,
            enable_asr=request.enable_asr,
            asr_model_size=request.model_size,
            progress_callback=pipeline_cb,
        )

        with _TASK_LOCK:
            TASKS[task_id]["status"] = "done"
            TASKS[task_id]["progress"] = 100
            TASKS[task_id]["message"] = "完成"
            TASKS[task_id]["result"] = {
                "video_title": video_title,
                "merged_subtitles": result["merged"],
                "ocr_raw": result["ocr_raw"],
                "asr_raw": result["asr_raw"],
            }

    except Exception as e:
        print(f"❌ 任务崩溃: {e}")
        with _TASK_LOCK:
            TASKS[task_id]["status"] = "error"
            TASKS[task_id]["error"] = str(e)
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass


@app.post("/extract")
def submit_task(request: VideoRequest):
    task_id = str(uuid.uuid4())
    with _TASK_LOCK:
        TASKS[task_id] = {"status": "running", "progress": 0, "message": "任务已提交", "result": None}
    t = threading.Thread(target=background_task, args=(task_id, request), daemon=True)
    t.start()
    return {"task_id": task_id}


@app.get("/status/{task_id}")
def get_status(task_id: str):
    with _TASK_LOCK:
        task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


if __name__ == "__main__":
    uvicorn.run(app, host=config.server["host"], port=config.server["port"])
