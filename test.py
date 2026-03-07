import drawable.drawable_rc  # 确保资源已导入
from PyQt5.QtCore import QFile

for name in ["Finished_Cup.png", "Shaker_Cup.png", "Smoothie_Cup.png"]:
    path = f":/icon/{name}"
    print(path, QFile.exists(path))