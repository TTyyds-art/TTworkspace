from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel
from threads.time_thread import TimeThread
from ui_1080_py.Ui_clean_week_load_ui import Ui_Form
import sys
import os

def resource_path(relative_path):
    """ 获取资源的绝对路径 """
    if hasattr(sys, '_MEIPASS'):
        # 打包后的运行环境
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CleanWeekLoadMata(QWidget, Ui_Form):
    clean_begin_notice = pyqtSignal(list)
    clean_pause_notice = pyqtSignal(bool)
    clean_stop_notice = pyqtSignal()
    clean_log = pyqtSignal(str)
    clean_min_sec = pyqtSignal(int, int)

    def __init__(self, total_time, parent=None):
        super().__init__(parent)
        self.executed_log = [False] * 11
        # self.test_thread = None
        # self.setupUi(self)
        # self.l_date.setText('00:00:00')
        self.test_thread = None
        self.total_time = total_time  # 总时间3600秒（60分钟）
        self.number = 0
        self.setupUi(self)
        self.l_date.setText('00:00:00')
        
        self.start_style = """
            background-color:rgba(179, 226, 197, 1);
            border-radius:9px;
        """
        self.end_style = """
            background-color:rgba(44, 159, 97, 1);
            border-radius:9px;
        """
        self.start_image_style = """
            border-image:url(:/icon/icon_clean_load_no_over.png);
        """
        self.end_image_style = """
            border-image:url(:/icon/icon_clean_load_over.png);
        """
        self.begin_style = """
                QProgressBar{
                    color:white;
                    border-radius:20px;
                    background-color:rgb(179, 226, 197);
                    text-align:center;
                }
                QProgressBar::chunk{
                    border-radius:20px;			
                    background-color:rgb(44, 159, 97);
                }
                """
        self.pause_style = """
                        QProgressBar{
                            color:white;
                            border-radius:20px;
                            background-color:rgb(179, 226, 197);
                            text-align:center;
                        }
                        QProgressBar::chunk{
                            border-radius:20px;			
                            background-color:rgba(255, 192, 0, 1);
                        }
                        """
        self.init_font()
        self.icon_label = QLabel(self)
        # self.icon = QPixmap(r'drawable\icon_clean_progress_load.png')  # 替换为你的图标路径
        # self.icon_pause = QPixmap(r'drawable\icon_clean_progress_load_pause.png')  # 替换为你的图标路径
        self.icon = QPixmap(resource_path(r'drawable\icon_clean_progress_load.png'))
        self.icon_pause = QPixmap(resource_path(r'drawable\icon_clean_progress_load_pause.png'))
        self.icon_label.setPixmap(self.icon)
        self.icon_label.setFixedSize(self.icon.size())
        self.progressBar.valueChanged.connect(self.update_icon_position)

        self.init_state()
        self.icon_label.move(self.progressBar.geometry().x() - 36, self.progressBar.geometry().y() + 77)
        # 创建一个时间线程
        self.number = 0

    def clean_T(self, T):
        self.total_time = T

    def test_time(self):
        # self.test_thread = TimeThread()
        # self.test_thread.result.connect(self.change_progress)
        self.test_thread = TimeThread(total_time=self.total_time)
        self.test_thread.result.connect(self.update_time_and_progress)
        self.clean_begin_notice.connect(self.test_thread.clean_begin)
        self.clean_pause_notice.connect(self.test_thread.clean_pause)
        self.clean_stop_notice.connect(self.test_thread.clean_stop)
        self.test_thread.start()

    def clean_begin(self,conduit_beans, T):
        self.total_time = T
        self.test_time()
        self.progressBar.setRange(0, self.total_time)  # 设置进度条范围

    def clean_stop(self):
        self.clean_stop_notice.emit()
        self.number = 0
        self.progressBar.setValue(self.number)
        self.l_date.setText('00:00:00')
        self.progressBar.setStyleSheet(self.begin_style)
        self.icon_label.setPixmap(self.icon)
        self.init_state()

    def clean_pause(self, is_continue):
        self.clean_pause_notice.emit(is_continue)
        if is_continue:
            self.progressBar.setStyleSheet(self.begin_style)
            self.icon_label.setPixmap(self.icon)
        else:
            self.progressBar.setStyleSheet(self.pause_style)
            self.icon_label.setPixmap(self.icon_pause)

    def update_time_and_progress(self, remaining_time):
        # 更新剩余时间
        minutes, seconds = divmod(remaining_time, 60)
        self.l_date.setText(f"00:{minutes:02}:{seconds:02}")
        self.clean_min_sec.emit(minutes, seconds)
        # 更新进度条
        elapsed_time = self.total_time - remaining_time
        self.progressBar.setValue(elapsed_time)
        self.number = (elapsed_time * 100) // self.total_time  # 根据进度条计算 self.number
        if self.number == 0:
            self.init_state()
            self.executed_log = [False] * 11
        if 0 < self.number < 10:
            self.state_1()
        elif 10 <= self.number < 20:
            self.state_2()
        elif 20 <= self.number < 30:
            self.state_3()
        elif 30 <= self.number < 40:
            self.state_4()
        elif 40 <= self.number < 50:
            self.state_5()
        elif 50 <= self.number < 60:
            self.state_6()
        elif 60 <= self.number < 70:
            self.state_7()
        elif 70 <= self.number < 80:
            self.state_8()
        elif 80 <= self.number < 90:
            self.state_9()
        elif 90 <= self.number < 95:
            self.state_10()
        elif 95 <= self.number < 100:
            self.state_11()
        elif self.number == 100:
            self.number = -1
        self.number += 1
        # 如果时间到，停止任务
        if remaining_time == 0:
            self.clean_stop()

    def change_progress(self):
        self.progressBar.setValue(self.number)
        if self.number == 0:
            self.init_state()
            self.executed_log = [False] * 11
        if 0 < self.number < 8:
            self.state_1()
        elif 8 <= self.number < 16:
            self.state_2()
        elif 16 <= self.number < 24:
            self.state_3()
        elif 24 <= self.number < 32:
            self.state_4()
        elif 32 <= self.number < 40:
            self.state_5()
        elif 40 <= self.number < 48:
            self.state_6()
        elif 48 <= self.number < 56:
            self.state_7()
        elif 56 <= self.number < 64:
            self.state_8()
        elif 64 <= self.number < 72:
            self.state_9()
        elif 72 <= self.number < 80:
            self.state_10()
        elif 80 <= self.number < 88:
            self.state_11()
        elif 88 <= self.number < 93:
            self.state_12()
        elif 93 <= self.number < 100:
            self.state_13()
        elif self.number == 100:
            self.number = -1
        self.number += 1


    def update_icon_position(self):
        progress_bar_x = self.progressBar.geometry().x()
        progress_bar_y = self.progressBar.geometry().y() + 90
        progress_bar_length = self.progressBar.geometry().size().width()
        progress_value = self.progressBar.value()
        progress_max = self.progressBar.maximum()
        icon_x = progress_bar_x + (progress_bar_length * progress_value // progress_max) - (self.icon.width() // 2)
        icon_y = progress_bar_y - (self.icon.height() // 2)
        self.icon_label.move(icon_x, icon_y)
        self.icon_label.raise_()


    def init_state(self):
        self.progressBar.setValue(0)
        self.l_1.setStyleSheet(self.start_style)
        self.i_1.setStyleSheet(self.start_image_style)
        self.l_2.setStyleSheet(self.start_style)
        self.i_2.setStyleSheet(self.start_image_style)
        self.l_3.setStyleSheet(self.start_style)
        self.i_3.setStyleSheet(self.start_image_style)
        self.l_4.setStyleSheet(self.start_style)
        self.i_4.setStyleSheet(self.start_image_style)
        self.l_5.setStyleSheet(self.start_style)
        self.i_5.setStyleSheet(self.start_image_style)
        self.l_6.setStyleSheet(self.start_style)
        self.i_6.setStyleSheet(self.start_image_style)
        self.l_7.setStyleSheet(self.start_style)

    def state_1(self):
        self.l_1.setStyleSheet(self.end_style)

    def state_2(self):
        self.state_1()
        self.i_1.setStyleSheet(self.end_image_style)

    def state_3(self):
        self.state_2()
        self.l_2.setStyleSheet(self.end_style)

    def state_4(self):
        self.state_3()
        self.i_2.setStyleSheet(self.end_image_style)

    def state_5(self):
        self.state_4()
        self.l_3.setStyleSheet(self.end_style)

    def state_6(self):
        self.state_5()
        self.i_3.setStyleSheet(self.end_image_style)

    def state_7(self):
        self.state_6()
        self.l_4.setStyleSheet(self.end_style)

    def state_8(self):
        self.state_7()
        self.i_4.setStyleSheet(self.end_image_style)

    def state_9(self):
        self.state_8()
        self.l_5.setStyleSheet(self.end_style)

    def state_10(self):
        self.state_9()
        self.i_5.setStyleSheet(self.end_image_style)

    def state_11(self):
        self.state_10()
        self.l_6.setStyleSheet(self.end_style)

    def state_12(self):
        self.state_10()
        self.i_6.setStyleSheet(self.end_image_style)

    def state_13(self):
        self.state_10()
        self.l_7.setStyleSheet(self.end_style)


    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font
    def init_font(self):
        AlibabaPuHuiTi_3_55_Regular_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf')
        )
        if AlibabaPuHuiTi_3_55_Regular_id != -1:
            AlibabaPuHuiTi_3_55_Regular_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_55_Regular_id)[0]

            AlibabaPuHuiTi_3_55_Regular_font_family_20 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 18)


            AlibabaPuHuiTi_3_55_Regular_font_family_28 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 28)
            self.label_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.l_date.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_24.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_26.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_27.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_28.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_29.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_30.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_25.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)


