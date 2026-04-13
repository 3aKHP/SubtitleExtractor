import sys
import os
import logging
import numpy as np
import paddle
from paddleocr import PaddleOCR
from core import config

logging.getLogger("ppocr").setLevel(logging.WARNING)

class OCREngine:
    def __init__(self, use_gpu=None):
        use_gpu = config.ocr["use_gpu"] if use_gpu is None else use_gpu
        self._confidence = config.ocr["confidence_threshold"]

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_root = sys.prefix

        dll_paths = [
            os.path.join(env_root, "Library", "bin"),
            os.path.join(env_root, "Lib", "site-packages", "paddle", "libs"),
            os.path.join(base_dir, "libs"),
        ]

        for p in dll_paths:
            if os.path.exists(p):
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(p)
                os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

        if use_gpu:
            import ctypes.util
            # 在已知的 dll_paths 里找 CUDA 库
            cuda_found = any(
                os.path.exists(os.path.join(p, dll))
                for p in dll_paths if os.path.exists(p)
                for dll in ("cudart64_110.dll", "cudart64_102.dll")
            ) or bool(ctypes.util.find_library("cudart64_110") or ctypes.util.find_library("cudart64_102"))

            if not cuda_found:
                print("⚠️  未检测到 CUDA 动态库，强制切换 CPU 模式")
                use_gpu = False
            else:
                try:
                    paddle.set_device("gpu")
                    gpu_name = paddle.device.cuda.get_device_name(0)
                    print(f"✅ GPU 模式: {gpu_name}")
                except Exception as e:
                    print(f"❌ GPU 初始化失败: {e}，回退 CPU")
                    use_gpu = False

        if not use_gpu:
            paddle.set_device("cpu")
            print("🔧 CPU 模式 (MKLDNN 加速)")

        try:
            self.ocr = PaddleOCR(
                use_angle_cls=False,
                lang="ch",
                use_gpu=use_gpu,
                show_log=False,
                enable_mkldnn=not use_gpu
            )
            print("OCR 引擎初始化完成。")
        except Exception as e:
            print(f"OCR 初始化失败: {e}，尝试 CPU fallback")
            self.ocr = PaddleOCR(use_angle_cls=False, lang="ch", use_gpu=False)

    def recognize(self, image) -> str:
        result = self.ocr.ocr(image, cls=False)

        if result is None or result == [None]:
            return ""

        lines = result[0] if (result and isinstance(result[0], list)) else result
        if not lines:
            return ""

        texts = [
            line[1][0]
            for line in lines
            if line and len(line) >= 2 and line[1] and line[1][1] > self._confidence
        ]
        return " ".join(texts)
