# server.py (修复版)
import os
import sys
import subprocess
import json
import shutil
import threading
import uuid
import gc
import torch # 用于清理显存
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core.ocr_engine import OCREngine
from core.alignment import AlignmentModule
from main import process_single_video

# 动态导入 ASR，防止启动报错
try:
    from core.asr_engine import ASREngine
    ASR_AVAILABLE = True
except ImportError:
    print("⚠️ 未找到 core/asr_engine.py，ASR 功能将不可用")
    ASR_AVAILABLE = False

FAKE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    temp_dir = os.path.abspath("temp_download")
    if os.path.exists(temp_dir):
        try: shutil.rmtree(temp_dir)
        except: pass
    os.makedirs(temp_dir, exist_ok=True)
    
    yield
    
    # Shutdown logic (if needed)

app = FastAPI(title="Bilibili Subtitle Extractor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TASKS = {}

# 全局只加载 OCR，因为它加载慢且占用相对稳定
print("🚀 正在初始化全局 OCR 引擎 (GPU)...")
global_ocr = OCREngine(use_gpu=True)
global_alignment = AlignmentModule()

class VideoRequest(BaseModel):
    url: str
    roi: float = 0.8
    step: int = 10
    timestamp: bool = True
    enable_asr: bool = True
    model_size: str = "small" 

# --- 工具函数 ---

def extract_audio_simple(video_path, audio_path):
    """
    使用 ffmpeg 提取音频 (16k采样率, 单声道, wav格式)
    """
    ffmpeg_exe = "ffmpeg" # 假设环境变量里有，如果没有，请改为绝对路径
    # 如果当前目录下有 ffmpeg.exe，优先使用
    if os.path.exists("ffmpeg.exe"):
        ffmpeg_exe = os.path.abspath("ffmpeg.exe")
        
    cmd = [
        ffmpeg_exe, "-y", 
        "-i", video_path, 
        "-vn", # 去除视频流
        "-acodec", "pcm_s16le", 
        "-ar", "16000", 
        "-ac", "1", 
        audio_path
    ]
    
    # 隐藏控制台窗口
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        return True
    except subprocess.CalledProcessError as e:
        print(f"音频提取失败: {e}")
        return False
    except FileNotFoundError:
        print("❌ 未找到 ffmpeg，请确保 ffmpeg 在系统路径或根目录下")
        return False

# --- 下载函数 (保持原样) ---
def get_video_metadata(url: str):
    exe_path = os.path.abspath("yt-dlp.exe")
    # clean_url = url.split('?')[0]
    cmd = [
        exe_path, url, 
        "--dump-json", "--no-playlist", "--no-warnings", 
        "--socket-timeout", "30", "--retries", "10",
        "--user-agent", FAKE_USER_AGENT
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=0x08000000 if os.name == 'nt' else 0)
    stdout, stderr = process.communicate()
    if process.returncode != 0: raise Exception(f"获取元数据失败: {stderr}")
    try: return json.loads(stdout)
    except: raise Exception("无法解析视频元数据 JSON")

def download_video_pure(url: str, save_path: str):
    exe_path = os.path.abspath("yt-dlp.exe")
    ffmpeg_dir = os.getcwd()
    # clean_url = url.split('?')[0]
    format_str = "bestvideo[vcodec^=avc][height<=720]+bestaudio/best[ext=mp4][height<=720]"
    cmd = [
        exe_path, url, 
        "-f", format_str, 
        "--merge-output-format", "mp4", 
        "-o", save_path, 
        "--ffmpeg-location", ffmpeg_dir, 
        "--no-warnings", "--no-playlist", "--socket-timeout", "30", 
        "--retries", "10", "--fragment-retries", "10",
        "--user-agent", FAKE_USER_AGENT
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=0x08000000 if os.name == 'nt' else 0)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        if not os.path.exists(save_path): raise Exception(f"下载失败: {stderr}")

# --- 核心任务逻辑 ---

def background_task(task_id: str, request: VideoRequest):
    base_dir = os.getcwd()
    temp_dir = os.path.join(base_dir, "temp_download")
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    def update_progress(percent, msg):
        TASKS[task_id]["progress"] = percent
        TASKS[task_id]["message"] = msg
        print(f"[{task_id[:4]}] {percent}%: {msg}")

    video_path = None
    audio_path = None
    
    try:
        # 1. 下载阶段
        update_progress(5, "正在获取视频信息...")
        info = get_video_metadata(request.url)
        video_title = info.get('title', 'Unknown')
        
        update_progress(10, f"正在下载: {video_title}...")
        filename = f"{info.get('id', 'video')}.mp4"
        video_path = os.path.join(temp_dir, filename)
        
        if not os.path.exists(video_path):
            download_video_pure(request.url, video_path)
            
        if not os.path.exists(video_path):
            raise FileNotFoundError("下载失败")

        # 2. ASR 阶段 (独立显存管理)
        asr_results = []
        asr_text_content = ""
        
        if request.enable_asr and ASR_AVAILABLE:
            update_progress(20, "正在提取音频...")
            audio_path = os.path.splitext(video_path)[0] + ".wav"
            
            if extract_audio_simple(video_path, audio_path):
                update_progress(25, "正在加载 ASR 模型 (这可能需要几秒)...")
                try:
                    # 【关键】局部实例化，用完即焚
                    # 建议使用 small 模型，平衡速度和显存
                    asr_engine = ASREngine(model_size=request.model_size, device="cuda")
                    
                    update_progress(30, f"正在进行语音识别 ({request.model_size})...")
                    asr_results = asr_engine.transcribe(audio_path)
                    
                    # 生成纯 ASR 文本备份
                    asr_lines = []
                    for item in asr_results:
                        t_str = global_alignment.format_timestamp(item['start'])
                        asr_lines.append(f"[{t_str}] {item['text']}")
                    asr_text_content = "\n".join(asr_lines)
                    
                    # 【关键】销毁实例，释放显存
                    del asr_engine
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    print("✅ ASR 完成，显存已释放")
                    
                except Exception as e:
                    print(f"⚠️ ASR 运行失败: {e}")
                    asr_text_content = f"ASR Error: {e}"
            else:
                print("⚠️ 音频提取失败，跳过 ASR")
        
        # 3. OCR 阶段
        update_progress(50, "正在进行硬字幕提取 (OCR)...")
        
        def ocr_callback(p, msg):
            # 映射进度 50% -> 90%
            update_progress(50 + int(p * 0.4), msg)

        process_single_video(
            video_path,
            output_dir,
            global_ocr,
            roi_ratio=request.roi,
            step=request.step,
            include_timestamp=request.timestamp,
            progress_callback=ocr_callback
        )
        
        # 读取 OCR 结果
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        ocr_txt_path = os.path.join(output_dir, f"subtitle_{base_name}.txt")
        
        ocr_content = ""
        if os.path.exists(ocr_txt_path):
            with open(ocr_txt_path, "r", encoding="utf-8") as f:
                ocr_content = f.read()
        else:
            ocr_content = "OCR 提取未生成文件"

        # 4. 合并阶段
        update_progress(95, "正在合并校对...")
        final_content = ""
        
        if asr_results and ocr_content:
            final_content = global_alignment.align(ocr_content, asr_results)
        else:
            # 降级处理：如果没有 ASR，就只返回 OCR
            final_content = ocr_content

        # 清理临时文件
        try:
            if video_path and os.path.exists(video_path): os.remove(video_path)
            if audio_path and os.path.exists(audio_path): os.remove(audio_path)
        except: pass
        
        TASKS[task_id]["status"] = "done"
        TASKS[task_id]["progress"] = 100
        TASKS[task_id]["message"] = "完成"
        TASKS[task_id]["result"] = {
            "video_title": video_title,
            "merged_subtitles": final_content,
            "ocr_raw": ocr_content,
            "asr_raw": asr_text_content
        }

    except Exception as e:
        print(f"❌ 任务崩溃: {e}")
        TASKS[task_id]["status"] = "error"
        TASKS[task_id]["error"] = str(e)
        # 发生错误也尝试清理
        try:
            if video_path and os.path.exists(video_path): os.remove(video_path)
        except: pass

@app.post("/extract")
def submit_task(request: VideoRequest):
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "status": "running",
        "progress": 0,
        "message": "任务已提交",
        "result": None
    }
    t = threading.Thread(target=background_task, args=(task_id, request))
    t.daemon = True
    t.start()
    return {"task_id": task_id}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id]

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
