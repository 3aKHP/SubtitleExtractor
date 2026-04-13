"""
pipeline.py — 核心编排层

CLI 和 server 都调用这里，不直接互相依赖。
"""
import os
import gc
import subprocess
from core import config
from core.video_processor import VideoProcessor
from core.ocr_engine import OCREngine
from core.utils import clean_text, is_duplicate

def extract_audio(video_path: str, audio_path: str) -> bool:
    """用 ffmpeg 从视频提取 16k 单声道 wav。"""
    ffmpeg_exe = os.path.abspath("ffmpeg.exe") if os.path.exists("ffmpeg.exe") else "ffmpeg"

    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        audio_path,
    ]

    startupinfo = None
    if os.name == "nt":
        import subprocess as _sp
        startupinfo = _sp.STARTUPINFO()
        startupinfo.dwFlags |= _sp.STARTF_USESHOWWINDOW

    try:
        subprocess.run(
            cmd, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"音频提取失败: {e}")
        return False
    except FileNotFoundError:
        print("❌ 未找到 ffmpeg，请确保 ffmpeg 在系统路径或 app/ 目录下")
        return False


def run_ocr(
    video_path: str,
    output_dir: str,
    ocr_engine: OCREngine,
    roi_ratio: float = None,
    step: int = None,
    include_timestamp: bool = None,
    progress_callback=None,
) -> str:
    """
    对单个视频跑 OCR，结果写入 output_dir，同时返回文本内容。
    progress_callback(percent: int, msg: str)
    """
    roi_ratio = roi_ratio if roi_ratio is not None else config.extraction["default_roi"]
    step = step if step is not None else config.extraction["default_step"]
    include_timestamp = include_timestamp if include_timestamp is not None else config.extraction["default_include_timestamp"]
    threshold = config.extraction["similarity_threshold"]
    history_size = config.extraction["history_size"]

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_path = os.path.join(output_dir, f"subtitle_{base_name}.txt")

    processor = VideoProcessor(video_path, roi_ratio=roi_ratio)

    if progress_callback:
        progress_callback(0, "正在初始化 OCR...")

    history = []
    lines = []

    with open(output_path, "w", encoding="utf-8") as f:
        for roi_image, timestamp, frame_id in processor.extract_subtitle_frames(step=step):
            if progress_callback:
                percent = int((frame_id / processor.total_frames) * 100)
                progress_callback(percent, f"正在提取字幕 ({timestamp})...")

            text = clean_text(ocr_engine.recognize(roi_image))
            if not text:
                continue
            if is_duplicate(text, history, threshold):
                continue

            line = f"[{timestamp}] {text}" if include_timestamp else text
            f.write(line + "\n")
            f.flush()
            lines.append(line)

            history.append(text)
            if len(history) > history_size:
                history.pop(0)

    if progress_callback:
        progress_callback(100, "OCR 提取完成")

    return "\n".join(lines)


def run_full_pipeline(
    video_path: str,
    output_dir: str,
    ocr_engine: OCREngine,
    roi_ratio: float = None,
    step: int = None,
    include_timestamp: bool = None,
    enable_asr: bool = True,
    asr_model_size: str = None,
    progress_callback=None,
) -> dict:
    """
    完整流程：OCR + 可选 ASR + 对齐合并。
    返回 {"ocr_raw": str, "asr_raw": str, "merged": str}
    """
    os.makedirs(output_dir, exist_ok=True)

    def _progress(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)

    # --- OCR ---
    def ocr_cb(p, msg):
        # 映射到整体进度 0~70%
        _progress(int(p * 0.7), msg)

    ocr_raw = run_ocr(
        video_path, output_dir, ocr_engine,
        roi_ratio=roi_ratio, step=step,
        include_timestamp=include_timestamp,
        progress_callback=ocr_cb,
    )

    # --- ASR ---
    asr_results = []
    asr_raw = ""

    if enable_asr:
        try:
            from core.asr_engine import ASREngine
        except ImportError:
            print("⚠️ ASR 不可用，跳过")
            enable_asr = False

    if enable_asr:
        _progress(72, "正在提取音频...")
        audio_path = os.path.splitext(video_path)[0] + "_asr.wav"

        if extract_audio(video_path, audio_path):
            _progress(75, f"正在加载 ASR 模型...")
            try:
                asr_engine = ASREngine(model_size=asr_model_size)
                _progress(80, "正在语音识别...")
                asr_results = asr_engine.transcribe(audio_path)
                asr_engine.release()
                del asr_engine

                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
                gc.collect()

                from core.alignment import AlignmentModule
                asr_raw = "\n".join(
                    f"[{AlignmentModule().format_timestamp(s['start'])}] {s['text']}"
                    for s in asr_results
                )
            except Exception as e:
                print(f"⚠️ ASR 失败: {e}")
                asr_raw = f"ASR Error: {e}"
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)

    # --- 对齐合并 ---
    _progress(95, "正在合并校对...")
    if asr_results and ocr_raw:
        from core.alignment import AlignmentModule
        merged = AlignmentModule().align(ocr_raw, asr_results)
    else:
        merged = ocr_raw

    _progress(100, "完成")
    return {"ocr_raw": ocr_raw, "asr_raw": asr_raw, "merged": merged}
