import os
import argparse
from pathlib import Path
from tqdm import tqdm

from core import config
from core.ocr_engine import create_ocr_engine
from core.pipeline import run_full_pipeline

def main():
    parser = argparse.ArgumentParser(description="视频硬字幕提取工具")
    parser.add_argument("input", help="输入视频文件或目录")
    parser.add_argument("-o", "--output", default="output", help="结果输出目录")
    parser.add_argument("--roi", type=float, default=None, help="字幕区域起始位置比例")
    parser.add_argument("--step", type=int, default=None, help="采样步长（帧）")
    parser.add_argument("--no-timestamp", action="store_true", help="输出不含时间戳")
    parser.add_argument("--asr", action="store_true", help="启用 ASR")
    parser.add_argument("--no-asr", action="store_true", help="禁用 ASR")
    parser.add_argument("--asr-model", default=None, help="ASR 模型大小")
    parser.add_argument("--cpu", action="store_true", help="强制 CPU 模式")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    enable_asr = config.asr.get("enabled", False)
    if args.asr:
        enable_asr = True
    if args.no_asr:
        enable_asr = False

    print("正在初始化 OCR 引擎...")
    ocr_engine = create_ocr_engine(use_gpu=not args.cpu)

    input_path = Path(args.input)
    if input_path.is_file():
        video_files = [input_path]
    elif input_path.is_dir():
        video_files = [
            f for ext in ("*.mp4", "*.mkv", "*.avi", "*.mov", "*.flv")
            for f in input_path.glob(ext)
        ]
    else:
        print("⚠️  未找到视频文件。")
        return

    for v_file in tqdm(video_files, desc="总进度", unit="video"):
        try:
            run_full_pipeline(
                str(v_file),
                args.output,
                ocr_engine,
                roi_top=args.roi,
                step=args.step,
                include_timestamp=not args.no_timestamp,
                enable_asr=enable_asr,
                asr_model_size=args.asr_model,
            )
            print(f"✅ {v_file.name} 完成")
        except Exception as e:
            print(f"❌ {v_file.name} 失败: {e}")

if __name__ == "__main__":
    main()
