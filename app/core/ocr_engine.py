import numpy as np
from rapidocr_onnxruntime import RapidOCR
from core import config


class OCREngine:
    def __init__(self, use_gpu: bool = None):
        use_gpu = config.ocr["use_gpu"] if use_gpu is None else use_gpu
        self._confidence = config.ocr["confidence_threshold"]

        # DirectML 后端：RapidOCR 不支持直接传 provider，
        # 通过环境变量让 onnxruntime 优先选 DmlExecutionProvider。
        # CPU 模式下不设置，onnxruntime 默认使用 CPUExecutionProvider。
        if use_gpu:
            import os
            os.environ.setdefault("ORT_DIRECTML_ENABLE", "1")

        self.ocr = RapidOCR()

        mode = "GPU (DirectML)" if use_gpu else "CPU"
        print(f"OCR 引擎初始化完成 [{mode}]")

    def recognize(self, image: np.ndarray) -> str:
        """
        image: BGR numpy array (来自 cv2.imread 或 VideoProcessor)
        返回识别到的文本，置信度低于阈值的行被过滤。
        """
        result, _ = self.ocr(image)

        if not result:
            return ""

        texts = [
            line[1]
            for line in result
            if line and len(line) >= 3 and line[2] >= self._confidence
        ]
        return " ".join(texts)
