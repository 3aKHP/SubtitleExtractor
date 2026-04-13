import sys
import os
import paddle
from paddleocr import PaddleOCR
import logging
import numpy as np # 引入 numpy

# 压制日志
logging.getLogger("ppocr").setLevel(logging.WARNING)

class OCREngine:
    def __init__(self, use_gpu=True):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 动态寻找 DLL 路径
        # 你的环境结构可能是: python_env/Lib/site-packages/paddle/libs
        # 我们尝试在 sys.prefix (当前 Python 解释器目录) 下找
        env_root = sys.prefix 
        
        dll_paths = [
            os.path.join(env_root, "Library", "bin"),
            os.path.join(env_root, "Lib", "site-packages", "paddle", "libs"),
            # 也可以保留项目根目录下的 libs 文件夹作为备用
            os.path.join(base_dir, "libs") 
        ]
        
        for p in dll_paths:
            if os.path.exists(p):
                if hasattr(os, 'add_dll_directory'):
                    os.add_dll_directory(p)
                os.environ['PATH'] = p + os.pathsep + os.environ['PATH']

        if use_gpu:
            # 【新增】在启动前，先检查关键 DLL 是否存在，不存在就别硬撑了
            import ctypes.util
            # 检查常见的 CUDA 库名，根据你的 paddle 版本可能是 cudart64_110.dll 或其他
            cuda_exists = ctypes.util.find_library("cudart64_110.dll") or \
                          ctypes.util.find_library("cudart64_102.dll") or \
                          os.path.exists(os.path.join(p, "cudart64_110.dll")) # 检查 paddle/libs 下有没有
            
            if not cuda_exists:
                print("⚠️  警告: 未检测到 CUDA 动态库 (cudart64_xx.dll)！")
                print("⚠️  系统将强制切换回 CPU 模式，以防止 OCR 输出为空。")
                use_gpu = False
            else:
                try:
                    paddle.set_device('gpu')
                    gpu_name = paddle.device.cuda.get_device_name(0)
                    print(f"✅ 成功切换到 GPU 模式！硬件: {gpu_name}")
                except Exception as e:
                    print(f"❌ GPU 初始化失败: {e}")
                    use_gpu = False

        if not use_gpu:
            paddle.set_device('cpu')
            print("🔧 正在使用 CPU 模式 (已启用 MKLDNN 加速)")
        
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
            print(f"初始化失败: {e}")
            self.ocr = PaddleOCR(use_angle_cls=False, lang="ch", use_gpu=False)

    def recognize(self, image):
        # 1. 确保图片格式正确 (Paddle 偏好 RGB，OpenCV 是 BGR，虽然通常通用，但转一下更稳)
        # image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) 
        # 暂时先保持 BGR，通常没问题，重点是下面的调试信息
        
        # 移除 try-except，让错误爆出来！
        
        # 调用 OCR
        result = self.ocr.ocr(image, cls=False)
        
        # 【调试信息】如果结果为空，打印出来
        if result is None or result == [None]:
            # print("⚠️ OCR 未检测到任何文字") # 嫌吵可以注释掉
            return ""

        texts = []
        
        # 处理返回结构
        lines = result[0] if (result and isinstance(result[0], list)) else result
        
        if lines:
            for line in lines:
                # line 结构: [[x,y], [text, confidence]]
                if line and len(line) >= 2 and line[1]:
                    text = line[1][0]
                    confidence = line[1][1]
                    
                    # 【调试信息】打印所有识别到的内容和置信度
                    # print(f"🔍 识别到: '{text}' (置信度: {confidence:.2f})")
                    
                    # 既然你之前设 0.6 都不行，我们这次先设极低 0.1，看看是不是置信度的问题
                    if confidence > 0.85: 
                        texts.append(text)
        
        return " ".join(texts)
