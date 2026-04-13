import cv2
import numpy as np

class VideoProcessor:
    # 【关键修复】这里必须增加 roi_ratio 参数，并设置默认值
    def __init__(self, video_path, roi_ratio=0.8):
        self.video_path = video_path # 保存路径供音频提取使用
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 【关键修复】使用传入的 roi_ratio 计算截取位置
        # 限制范围，防止参数传错导致报错
        roi_ratio = max(0.1, min(0.9, roi_ratio))
        
        self.roi_y_start = int(self.height * roi_ratio)
        self.roi_height = self.height - self.roi_y_start

    def get_time_string(self, frame_index):
        """将帧号转换为时间戳字符串 (HH:MM:SS)"""
        if self.fps == 0: return "00:00:00" # 防止除以零
        seconds = frame_index / self.fps
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))

    def is_similar(self, img1, img2, threshold=30):
        if img1 is None or img2 is None:
            return False
        
        # 宽 64 像素足够判断字幕有没有变了
        h, w = img1.shape[:2]
        scale = 256 / w
        new_size = (256, int(h * scale))
        
        try:
            s1 = cv2.resize(img1, new_size, interpolation=cv2.INTER_NEAREST)
            s2 = cv2.resize(img2, new_size, interpolation=cv2.INTER_NEAREST)
        except:
            return False

        # 转灰度
        g1 = cv2.cvtColor(s1, cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(s2, cv2.COLOR_BGR2GRAY)
        
        # 直接计算灰度图的差异，不再进行二值化
        diff = cv2.absdiff(g1, g2)
        mean_diff = np.mean(diff)
        
        # 阈值设为 10 左右比较合适
        return mean_diff < 10

    def extract_audio(self, output_audio_path):
        """
        从视频中提取音频
        :param output_audio_path: 输出音频文件路径 (.wav 或 .mp3)
        """
        import subprocess
        import os
        
        if os.path.exists(output_audio_path):
            os.remove(output_audio_path)
            
        # 假设 ffmpeg.exe 在当前工作目录或系统路径中
        ffmpeg_exe = os.path.abspath("ffmpeg.exe")
        if not os.path.exists(ffmpeg_exe):
            ffmpeg_exe = "ffmpeg" # 尝试系统路径

        cmd = [
            ffmpeg_exe,
            "-i", self.video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_audio_path,
            "-y",
            "-loglevel", "error"
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 音频提取失败: {e}")
            return False

    def extract_subtitle_frames(self, step=5):
        """
        生成器：逐帧读取，返回字幕发生变化的帧
        """
        last_roi = None
        
        current_frame_idx = 0
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # 跳帧处理
            if current_frame_idx % step != 0:
                current_frame_idx += 1
                continue

            # 1. 裁剪字幕区域 (ROI)
            # 增加 .copy() 确保内存连续
            try:
                roi = np.ascontiguousarray(frame[self.roi_y_start:self.height, 0:self.width])
            except Exception:
                current_frame_idx += 1
                continue

            # 2. 判断是否与上一帧字幕相似
            if not self.is_similar(last_roi, roi):
                timestamp = self.get_time_string(current_frame_idx)
                yield roi, timestamp, current_frame_idx
                last_roi = roi
            
            current_frame_idx += 1
        
        self.cap.release()
