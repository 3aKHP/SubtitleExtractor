import os
import shutil
import glob

# 你的环境路径
ENV_PATH = os.path.abspath("python_env")

# 1. 绝对安全的删除列表 (测试代码、缓存、文档)
PATTERNS_TO_DELETE = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd.idb",  # 调试符号
    "**/*.pdb",      # 调试符号 (非常大!)
    "**/tests",      # 测试文件夹
    "**/test",       # 测试文件夹
    "**/doc",        # 文档
    "**/docs",       # 文档
    "**/examples",   # 示例代码
    "**/sample_data",# 示例数据 (matplotlib等自带)
]

# 2. 针对特定库的臃肿文件夹 (根据你的目录扫描定制)
SPECIFIC_DIRS = [
    r"Lib\site-packages\numpy\core\include",  # C++ 头文件，运行时不需要
    r"Lib\site-packages\numpy\core\lib",      # 静态库
    r"Lib\site-packages\paddle\include",      # Paddle C++ 头文件 (巨大!)
    r"Lib\site-packages\paddle\fluid\tests",  # Paddle 内部测试
    r"Lib\site-packages\matplotlib\mpl-data\fonts", # 字体文件，保留基本即可，全删可能会报错，建议手动检查
    r"Lib\site-packages\scipy\io\tests",
    r"tcl", # 如果你没用 tkinter (你的前端是 Chrome 插件)，这个文件夹可以直接删
    r"Tools", # Python 自带工具
    r"include", # Python C 头文件
    r"libs", # Python 静态链接库 (保留 python3.lib 和 python38.lib 即可，其他的通常是编译用的)
]

def clean_up():
    print(f"正在清理环境: {ENV_PATH} ...")
    deleted_size = 0

    # 1. 通用模式清理
    for pattern in PATTERNS_TO_DELETE:
        full_pattern = os.path.join(ENV_PATH, pattern)
        # recursive=True 需要 python 3.5+
        for path in glob.glob(full_pattern, recursive=True):
            if os.path.exists(path):
                try:
                    size = 0
                    if os.path.isfile(path):
                        size = os.path.getsize(path)
                        os.remove(path)
                    elif os.path.isdir(path):
                        # 计算文件夹大小用于统计
                        for root, _, files in os.walk(path):
                            for f in files:
                                size += os.path.getsize(os.path.join(root, f))
                        shutil.rmtree(path)
                    
                    deleted_size += size
                    # print(f"Deleted: {path}") 
                except Exception as e:
                    print(f"无法删除 {path}: {e}")

    # 2. 指定目录清理
    for rel_path in SPECIFIC_DIRS:
        full_path = os.path.join(ENV_PATH, rel_path)
        if os.path.exists(full_path):
            try:
                size = 0
                for root, _, files in os.walk(full_path):
                    for f in files:
                        size += os.path.getsize(os.path.join(root, f))
                shutil.rmtree(full_path)
                deleted_size += size
                print(f"已删除目录: {rel_path}")
            except Exception as e:
                print(f"无法删除 {rel_path}: {e}")

    print(f"✅ 清理完成! 共释放空间: {deleted_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    # 再次确认，防止误删
    confirm = input(f"即将清理 {ENV_PATH}，这不可逆。确认? (y/n): ")
    if confirm.lower() == 'y':
        clean_up()
