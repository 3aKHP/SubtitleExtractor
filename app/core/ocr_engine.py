import base64
from concurrent.futures import ThreadPoolExecutor
from typing import List

import cv2
import httpx
import numpy as np
from core import config


class PaddleOCREngine:
    """PaddleOCR 引擎 (CPU, 检测+识别质量最高)"""
    def __init__(self, **kwargs):
        use_gpu = kwargs.get("use_gpu", config.ocr["use_gpu"])
        self._confidence = config.ocr["confidence_threshold"]
        self._use_gpu = use_gpu
        self.ocr = self._create_engine(use_gpu)

    def _create_engine(self, use_gpu: bool):
        from paddleocr import PaddleOCR

        engine = PaddleOCR(
            use_angle_cls=False,
            lang="ch",
            det_db_thresh=0.2,
            det_db_box_thresh=0.3,
            det_db_unclip_ratio=2.5,
            use_gpu=use_gpu,
            show_log=False,
        )
        mode = "GPU" if use_gpu else "CPU"
        print(f"OCR 引擎初始化完成 [PaddleOCR | {mode}]")
        return engine

    def recognize(self, image: np.ndarray) -> str:
        try:
            result = self.ocr.ocr(image, cls=False)
        except RuntimeError as e:
            if not self._use_gpu:
                raise
            print(f"⚠️ PaddleOCR GPU 推理失败，回退到 CPU: {e}")
            self._use_gpu = False
            self.ocr = self._create_engine(False)
            result = self.ocr.ocr(image, cls=False)

        if not result or not result[0]:
            return ""
        texts = [
            line[1][0]
            for line in result[0]
            if line[1][1] >= self._confidence
        ]
        return " ".join(texts) if texts else ""


class RemoteOCREngine:
    def __init__(self, **kwargs):
        self._api_key = kwargs.get("api_key") or config.ocr.get("remote_api_key", "")
        self._base_url = kwargs.get("base_url") or config.ocr.get("remote_url", "")
        self._model = kwargs.get("model") or config.ocr.get("remote_model", "")
        self._timeout = kwargs.get("timeout") or config.ocr.get("remote_timeout", 30)
        self._max_concurrency = kwargs.get("max_concurrency") or config.ocr.get("remote_max_concurrency", 3)

        if not self._api_key:
            raise ValueError(
                "remote_api_key is required when using remote OCR backend. "
                "Set it in config.toml [ocr] section."
            )

        self._auth_header = {"Authorization": f"Bearer {self._api_key}"}
        print(f"远程 OCR 引擎初始化完成 [model={self._model}]")

    def recognize(self, image: np.ndarray) -> str:
        data_uri = self._encode_image(image)
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {
                            "type": "text",
                            "text": (
                                "Extract any Chinese text visible in this image. "
                                "Return ONLY the text found. If no Chinese text is visible, respond with [EMPTY]. "
                                "Do not describe, translate, or add anything."
                            ),
                        },
                    ],
                }
            ],
        }
        try:
            response = httpx.post(
                self._base_url,
                json=payload,
                headers=self._auth_header,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return self._filter_noise(content.strip() if content else "")
        except httpx.HTTPStatusError as e:
            print(f"远程 OCR API 错误 [{e.response.status_code}]: {e.response.text[:200]}")
            return ""
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            print(f"远程 OCR 网络错误: {e}")
            return ""
        except (KeyError, IndexError, ValueError) as e:
            print(f"远程 OCR 响应解析失败: {e}")
            return ""

    def _filter_noise(self, text: str) -> str:
        """过滤 VLM 幻觉输出。"""
        if not text:
            return ""
        if text.strip().upper() in ("[EMPTY]", "[NO_TEXT]", "NONE"):
            return ""

        # 过长（单帧字幕不应超 200 字符）
        if len(text) > 200:
            return ""

        # 中文字符占比检测
        chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
        total_chars = len(text.replace(" ", "").replace("\n", ""))
        if total_chars > 0 and chinese_chars / max(total_chars, 1) < 0.05:
            return ""

        # 代码/英文噪音特征
        noise_keywords = [
            "public static void", "npm install", "Copyright", "All Rights Reserved",
            "@Override", "@Deprecated", "Click here", "Subscribe", "Please type",
            "StringBuilder", "IOException", "SELECT", "</p>", "</a>", "</table>",
            "@param", "@return", "@since", "Download", "Lorem ipsum",
        ]
        for kw in noise_keywords:
            if kw.lower() in text.lower():
                return ""

        return text.strip()

    def recognize_batch(self, images: List[np.ndarray], concurrency: int = None) -> List[str]:
        concurrency = concurrency if concurrency is not None else self._max_concurrency
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(self.recognize, images))
        return results

    def _encode_image(self, image: np.ndarray) -> str:
        success, buffer = cv2.imencode(".png", image)
        if not success:
            raise ValueError("Failed to encode image to PNG")
        b64 = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{b64}"


def create_ocr_engine(**kwargs):
    backend = config.ocr.get("backend", "paddle")
    if backend == "remote":
        return RemoteOCREngine(**kwargs)
    if backend == "paddle":
        return PaddleOCREngine(**kwargs)
    if backend in ("rapidocr", "local"):
        raise ValueError("RapidOCR is not supported in the distributable build; use backend='paddle'.")
    raise ValueError(f"Unsupported OCR backend: {backend}")
