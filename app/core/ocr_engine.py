import numpy as np
from rapidocr_onnxruntime import RapidOCR
from core import config


class OCREngine:
    def __init__(self, use_gpu: bool = None):
        use_gpu = config.ocr["use_gpu"] if use_gpu is None else use_gpu
        self._confidence = config.ocr["confidence_threshold"]

        # RapidOCR 通过 onnxruntime provider 控制 GPU/CPU
        # use_det/use_cls/use_rec 全部保持默认 True
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu \
                    else ["CPUExecutionProvider"]

        self.ocr = RapidOCR(
            det_use_cuda=use_gpu,
            rec_use_cuda=use_gpu,
        )

        mode = "GPU (CUDA)" if use_gpu else "CPU"
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
