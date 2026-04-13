import os
import gc

# 1. 强制使用国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 2. 【新增】禁用符号链接，强制使用文件复制 (解决 WinError 1314)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from faster_whisper import WhisperModel

class ASREngine:
    def __init__(self, model_size="small", device="cuda", compute_type="float16"):
        """
        初始化 Faster-Whisper 引擎
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

        base_dir = os.getcwd()
        model_cache_dir = os.path.join(base_dir, "models")
        
        print(f"🚀 [ASR] 正在加载模型: {self.model_size} (期望设备: {self.device})...")
        print(f"📂 [ASR] 模型缓存路径: {model_cache_dir}")
        
        try:
            # 【关键修改】加入 download_root 参数
            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type,
                download_root=model_cache_dir  # 指定下载/读取路径
            )
            print("✅ [ASR] 模型加载成功 (CUDA)")
        except Exception as e:
            # ... 异常处理里也要加 download_root ...
            print(f"⚠️ [ASR] CUDA 失败: {e}, 尝试 CPU...")
            self.device = "cpu"
            self.compute_type = "int8"
            self.model = WhisperModel(
                self.model_size, 
                device="cpu", 
                compute_type="int8",
                download_root=model_cache_dir # 这里也要加
            )
            print("✅ [ASR] CPU 模型加载成功")
        except Exception as e_cpu:
            print(f"❌ [ASR] 彻底失败: {e_cpu}")
            raise e_cpu
        
    def transcribe(self, audio_path, beam_size=5):
        """
        执行语音转文字
        """
        if not self.model:
            raise Exception("ASR 模型未初始化")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件未找到: {audio_path}")

        print(f"🎙️ [ASR] 开始识别: {os.path.basename(audio_path)}...")
        
        # language="zh" 强制中文，避免 B 站视频里的日语歌导致识别成日文
        segments, info = self.model.transcribe(
            audio_path, 
            beam_size=beam_size, 
            language="zh",
            initial_prompt="简体中文" ,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        result = []
        # segments 是一个生成器，这里遍历它才会真正开始推理
        for segment in segments:
            result.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
        
        print(f"✅ [ASR] 识别完成，共 {len(result)} 条字幕")
        return result

    def release(self):
        """
        显式释放资源，配合 server.py 使用
        """
        if self.model:
            del self.model
            self.model = None
        # 强制垃圾回收
        gc.collect()
