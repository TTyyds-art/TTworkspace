import time

from PyQt5.QtCore import QThread, pyqtSignal


class TimeThread(QThread):
    # result = pyqtSignal()
    result = pyqtSignal(int)

    # def __init__(self, parent=None):
    #     super(TimeThread, self).__init__(parent)
    #     self.is_stop = True
    #     self.is_pause = True

    # def run(self):
    #     while self.is_stop:
    #         time.sleep(0.5)
    #         if self.is_pause:
    #             self.result.emit()

    # def clean_begin(self):
    #     pass

    # def clean_stop(self):
    #     self.is_stop = False

    # def clean_pause(self, is_continue):
    #     self.is_pause = is_continue

    def __init__(self, total_time=2700, parent=None):  # 默认45分钟
        super(TimeThread, self).__init__(parent)
        self.is_stop = True
        self.is_pause = False
        self.remaining_time = total_time  # 剩余时间

    def run(self):
        while self.is_stop and self.remaining_time > 0:
            if not self.is_pause:
                self.remaining_time -= 1
                self.result.emit(self.remaining_time)  # 发射剩余时间信号
            time.sleep(1)  # 每秒更新一次

    def clean_begin(self):
        pass

    def clean_stop(self):
        self.is_stop = False
        self.remaining_time = 0  # 重置剩余时间

    def clean_pause(self, is_continue):
        self.is_pause = not is_continue