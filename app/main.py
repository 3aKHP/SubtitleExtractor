# main.py

import os
import cv2
import argparse
from pathlib import Path
from tqdm import tqdm
from core.video_processor import VideoProcessor
from core.ocr_engine import OCREngine
from core.utils import clean_text
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

# 【修改】增加 progress_callback 参数
def process_single_video(video_path, output_dir, ocr_engine, roi_ratio=0.8, step=10, include_timestamp=True, debug=False, progress_callback=None):
    """
    处理单个视频的逻辑封装
    """
    video_path = str(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    output_filename = f"subtitle_{base_name}.txt"
    output_file_path = os.path.join(output_dir, output_filename)

    processor = VideoProcessor(video_path, roi_ratio=roi_ratio)
    
    print(f"\n🎬 正在处理: {base_name}")
    
    # 如果有回调，初始化
    if progress_callback:
        progress_callback(0, "正在初始化 OCR...")

    history_buffer = [] 
    history_size = 3
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        pbar = tqdm(total=processor.total_frames, unit='frame', desc="提取进度")
        last_frame_id = 0
        
        # 【修复BUG】这里之前写死了 step=10，现在改为使用传入的 step
        for roi_image, timestamp, current_frame_id in processor.extract_subtitle_frames(step=step):
            
            update_val = current_frame_id - last_frame_id
            pbar.update(update_val)
            last_frame_id = current_frame_id
            
            # 【新增】汇报进度 (每处理一帧都汇报，或者你可以加个计数器每10帧汇报一次)
            if progress_callback:
                # 计算百分比 (0-100)
                percent = int((current_frame_id / processor.total_frames) * 100)
                progress_callback(percent, f"正在提取字幕 ({timestamp})...")
            
            if debug:
                cv2.imwrite(f"output/debug_{base_name}.jpg", roi_image)

            raw_text = ocr_engine.recognize(roi_image)
            text = clean_text(raw_text)

            if not text:
                continue
            
            if history_buffer and text == history_buffer[-1]:
                continue
                
            is_duplicate = False
            for old_text in history_buffer:
                if similar(text, old_text) > 0.7 or (text in old_text and len(old_text) - len(text) < 5):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue

            if include_timestamp:
                output_line = f"[{timestamp}] {text}\n"
            else:
                output_line = f"{text}\n"
                
            f.write(output_line)
            f.flush()
            
            history_buffer.append(text)
            if len(history_buffer) > history_size:
                history_buffer.pop(0)
        
        pbar.update(processor.total_frames - last_frame_id)
        pbar.close()
        
    # 完成回调
    if progress_callback:
        progress_callback(100, "提取完成")

def main():
    # 命令行入口保持不变，为了兼容性
    parser = argparse.ArgumentParser(description="视频硬字幕提取工具 (GPU加速版)")
    parser.add_argument("input", help="输入视频文件路径")
    parser.add_argument("-o", "--output", default="output", help="结果输出文件夹")
    parser.add_argument("--roi", type=float, default=0.8, help="字幕区域起始位置比例")
    parser.add_argument("--cpu", action="store_true", help="强制使用 CPU 模式")
    parser.add_argument("--debug", action="store_true", help="保存调试图片")
    
    # 命令行暂时不支持 step 和 timestamp 参数，如果需要可以自己加，这里主要服务 server.py
    args = parser.parse_args()

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    use_gpu = not args.cpu
    print("正在初始化 OCR 引擎...")
    ocr_engine = OCREngine(use_gpu=use_gpu)

    input_path = Path(args.input)
    video_files = []

    if input_path.is_file():
        video_files.append(input_path)
    elif input_path.is_dir():
        extensions = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.flv']
        for ext in extensions:
            video_files.extend(list(input_path.glob(ext)))
    
    if not video_files:
        print("⚠️  未找到视频文件。")
        return

    for i, v_file in enumerate(video_files):
        try:
            process_single_video(
                v_file, 
                args.output, 
                ocr_engine, 
                roi_ratio=args.roi,
                debug=args.debug
            )
        except Exception as e:
            print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main()
