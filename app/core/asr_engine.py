import os
import gc

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from faster_whisper import WhisperModel
from core import config

_APP_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

class ASREngine:
    def __init__(self, model_size=None, device=None, compute_type=None):
        self.model_size = model_size or config.asr["default_model_size"]
        self.device = device or config.asr["device"]
        self.compute_type = compute_type or ("float16" if self.device == "cuda" else "int8")
        self.model = None

        model_cache_dir = os.path.join(_APP_DIR, "models")

        print(f"🚀 [ASR] 正在加载模型: {self.model_size} (设备: {self.device})...")

        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=model_cache_dir
            )
            print(f"✅ [ASR] 模型加载成功 ({self.device.upper()})")
        except Exception as e:
            print(f"⚠️ [ASR] 在线加载失败: {e}")
            print("⚠️ [ASR] 尝试本地离线模式...")
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=model_cache_dir,
                    local_files_only=True
                )
                print(f"✅ [ASR] 离线模型加载成功 ({self.device.upper()})")
            except Exception as e2:
                print(f"⚠️ [ASR] 离线加载也失败: {e2}，回退到 CPU...")
                try:
                    self.device = "cpu"
                    self.compute_type = "int8"
                    self.model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                        download_root=model_cache_dir,
                        local_files_only=True
                    )
                    print("✅ [ASR] CPU 离线模型加载成功")
                except Exception as e_cpu:
                    print(f"❌ [ASR] 彻底失败: {e_cpu}")
                    raise

    def transcribe(self, audio_path, beam_size=5):
        if not self.model:
            raise RuntimeError("ASR 模型未初始化")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件未找到: {audio_path}")

        print(f"🎙️ [ASR] 开始识别: {os.path.basename(audio_path)}...")

        segments, _ = self.model.transcribe(
            audio_path,
            beam_size=beam_size,
            language="zh",
            initial_prompt="简体中文",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        result = [
            {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
            for seg in segments
        ]
        print(f"✅ [ASR] 识别完成，共 {len(result)} 条")
        return result

    def release(self):
        if self.model:
            del self.model
            self.model = None
        gc.collect()
