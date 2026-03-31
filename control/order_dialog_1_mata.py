import sys
import os
import time
import re
import random  
import pandas as pd
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QTimer
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QApplication, QLabel

from bean.new_tee_bean import NewTeeBean
from ui_1080_py.Ui_order_dialog_1_ui import Ui_Form


def load_recipes(file_path):
    # 加载Excel文件
    df = pd.read_excel(file_path, index_col=0)  # 假设产品名称在第一列
    return df


def get_recipe(recipes, product_name):
    try:
        # 根据产品名称获取对应的配方
        recipe_row = recipes.loc[product_name]
        # 构造配方字符串 :A100B120C050，确保数字总是三位
        recipe_str = ''.join([f"{chr(65 + i)}{str(int(recipe_row[i])).zfill(3)}" for i in range(len(recipe_row)) if
                              not pd.isna(recipe_row[i])])
        return recipe_str
    except KeyError:
        return None  # 如果没有找到配方，则返回None

def resource_path(relative_path):
    """ 获取资源的绝对路径 """
    if hasattr(sys, '_MEIPASS'):
        # 打包后的运行环境
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class OrderDialog1(QWidget, Ui_Form):
    notice_complete = pyqtSignal(NewTeeBean)
    notice_serial = pyqtSignal(str)
    notice_serial_open = pyqtSignal()
    notice_serial_stop = pyqtSignal()
    notice_style_no = pyqtSignal()

    def __init__(self, tee_bean, parent=None):
        super(OrderDialog1, self).__init__(parent)
        self.tee_bean = tee_bean
        self.setupUi(self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_no_touch_icon()
        self.init_font()
        self.init_ui(tee_bean)
        self.icon_label = QLabel(self)
        # self.icon = QPixmap(r'drawable\order_progressBar_ic.png')  # 替换为你的图标路径
        self.icon = QPixmap(resource_path(r'drawable\\order_progressBar_ic.png'))
        self.icon_label.setPixmap(self.icon)
        self.icon_label.setFixedSize(self.icon.size())
        self.progressBar.valueChanged.connect(self.update_icon_position)
        self.progressBar.setValue(0)
        QTimer.singleShot(0, self.update_icon_position)
        self.recipe = ''
        self.first_list = None  # 用于记录初始的data_list

        self.notice_serial_open.emit()

        self.send_serial_data(self.tee_bean)#

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.progress_value = 0
        # 用于记录连续接收到全 0 列表的次数
        self.zero_count = 0

    
    def handle_data(self, mA_list):
        # 将接收到的数据按换行符或空格分割
        # if len(data) > 20:
        #     print(f"Skipping long data: {data}")
        #     return
        # try:
        #     value = int(data)
        #     self.progressBar.setValue(value)

        # except ValueError:
        #     # 如果转换失败，打印错误
        #     print(f"Error converting {data} to int.")
        #     print("制作中:", data)
        # try:
        #     print(f"recipe:{self.recipe}")
        #     print(f"data_list: {data_list}")
        # except ValueError:
        #     print(f"Error converting {data_list} to int.")
        #通过ACII转码，将ABC转化成0123等等，以这些0123为索引，生成recipe_index； 再生成target_list
        # 
        # 将data_list的数据拿出来，储存到一个新的数组work_list
        # 通过if将第一次使用该函数的data_list记录为最原始的data_list命名为first_list
        #生成一个百分比数组perc_list=（first_list[recipe_index]-data_list[recipe_index]）/target_list
        #return perc_list.min()
        # try:
        #     # print(f"data_list:{data_list}")
        #     # 将配方字符串按字母和数字分割
        #     matches = re.findall(r'([A-Z])(\d+)', self.recipe)
        #     recipe_index = [ord(char) - ord('A') for char, _ in matches]
        #     target_list = [int(value) for _, value in matches]
        #     print(f"recipe_index: {recipe_index}")  #管道所在的索引
        #     print(f"target_list: {target_list}") #目标重量
        #     # 将data_list储存到一个新的数组work_list
        #     work_list = data_list[:]
        #     # 判断是否是第一次使用该函数
        #     if self.first_list is None:
        #         self.first_list = data_list[:]  # 记录为最初的data_list
        #         print(f"first_list (initial): {self.first_list}")
        #     # 根据公式计算百分比数组perc_list
        #     perc_list = [
        #         # (self.first_list[idx] - work_list[idx]) / target if idx < len(work_list) else 0
        #         # for idx, target in zip(recipe_index, target_list)
        #         max(0, (self.first_list[idx] - work_list[idx]) / target) if idx < len(work_list) and target!= 0 else 0
        #         for idx, target in zip(recipe_index, target_list)
        #     ]
        #     print(f"perc_list: {perc_list}")

        #     minPerc = min(max(0, perc) for perc in perc_list) * 100 if perc_list else 0
        #     minPerc = min(100, minPerc) if minPerc else 0
        #     # minPerc = min(perc_list)*100 if perc_list else None

        #     print(f"minPerc: {minPerc}")
            
        #     self.progressBar.setValue(int(minPerc))  #进度条显示

        # except ValueError as e:
        #     print(f"Error: {e}")
        # except Exception as e:
        #     print(f"Unexpected error: {e}")

        print(mA_list)
        if all(value == 0 for value in mA_list):
            self.zero_count += 1
            if self.zero_count >= 5: # 如果 mA_list 全部为 0，直接将进度条设置为 100%
                self.progress_value = 100
                self.progressBar.setValue(self.progress_value)
                self.timer.stop()

                self.zero_count = 0
            else:
                # 还未达到连续 2 组全 0，继续更新进度条
                self.start_progress()
        else:
            # 只要有电机在运行，就开始更新进度条
            self.start_progress()
    
    def start_progress(self):
        # self.progress_value = 0
        self.progressBar.setValue(self.progress_value)
        self.timer.start(150)  # 100ms = 0.1s

    def update_progress(self):
        if self.progress_value < 100:
            incrent = random.randint(5,10)
            self.progress_value += incrent
            self.progressBar.setValue(self.progress_value)
        else:
            self.timer.stop()
        

    def send_msg_order(self, name, volume, sugar, ice, add):
        pass

    def receive_msg_order(self, object_value):
        if object_value is str:
            return object_value
        elif object_value is int:
            self.progressBar.setValue(object_value)

    def send_serial_data(self, menu):
        # 加载配方
        # 获取menu中的产品名称
        # 获取对应的配方
        self.recipe = menu.recipe
        if self.recipe:
            # 如果找到了配方，通过串口发送
            # print(f"111:{self.recipe}")
            self.notice_serial.emit(self.recipe)
            print(f"order_dialog_1 Sent recipe to Arduino for {menu.product_name}: {self.recipe}")
        else:
            # 如果没有找到配方，打印消息
            print(f"No recipe found for {menu.product_name}")

    @pyqtSlot()
    def on_order_complete_btn_clicked(self):
        # if hasattr(self, 'serial_thread_1') and self.serial_thread_1:
        # 	# self.serial_thread_1.stop()
        # 	self.notice_serial_stop.emit()
        # 	self.serial_thread_1.wait()  # 等待线程完全结束
        # 	self.serial_thread_1 = None  # 确保资源释放
        self.notice_complete.emit(self.tee_bean)
        self.notice_serial_stop.emit()
        print("制作已完成")
        self.close()

    # # 如果需要重新启动串口线程
    # self.serial_thread_1 = SerialThread('COM10')
    # self.serial_thread_1.data_received.connect(self.handle_data)
    # self.serial_thread_1.start()

    @pyqtSlot()
    def on_order_cancel_btn_clicked(self):
        # 假设 self.serial_thread 是 SerialThread 的实例
        # if hasattr(self, 'serial_thread_1'):
        # 	self.serial_thread_1.send_data('stop')
        # 	print(f"Sent STOP to Arduino!")
        #
        # 	self.serial_thread_1.wait()  # 等待线程完全结束
        # 	self.serial_thread_1 = None  # 确保资源释放
        self.notice_serial_stop.emit()
        self.notice_style_no.emit()
        print("制作已取消")
        self.close()

    def init_ui(self, tee_bean):
        print(f'tee_bean:{tee_bean}')
        number = str(tee_bean.product_id)
        self.order_number_l.setText(number)
        name = tee_bean.product_name
        self.order_name_l.setText(str(name))

    def init_no_touch_icon(self):
        target_height = 182
        pixmap = QPixmap(':/icon/order_dialog_no_touch.png')
        if not pixmap.isNull():
            scaled = pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
            self.label_2.setPixmap(scaled)
            self.label_2.setFixedHeight(target_height)
            self.label_2.setFixedWidth(scaled.width())
            self.label_2.setStyleSheet("")

    def update_icon_position(self):
        progress_value = self.progressBar.value()
        progress_max = self.progressBar.maximum() or 100

        # 动态取进度条实际位置与宽度，避免分辨率/布局变化导致偏移
        bar_width = self.progressBar.width()
        bar_height = self.progressBar.height()
        if bar_width <= 0 or bar_height <= 0:
            # 布局未完成时，使用旧基准避免图标跑飞
            progress_bar_x = 610
            progress_bar_y = 470
            progress_bar_length = 700
            icon_x = progress_bar_x + (progress_bar_length * progress_value // progress_max) - (self.icon.width() // 2)
            icon_y = progress_bar_y - (self.icon.height() // 2)
        else:
            bar_top_left = self.progressBar.mapTo(self, QtCore.QPoint(0, 0))
            icon_x = bar_top_left.x() + (bar_width * progress_value // progress_max) - (self.icon.width() // 2)
            icon_y = bar_top_left.y() + (bar_height // 2) - (self.icon.height() // 2)

        # 约束在窗体可视范围内，避免越界
        bounds = self.rect()
        max_x = bounds.right() - self.icon.width() + 1
        max_y = bounds.bottom() - self.icon.height() + 1
        icon_x = max(bounds.left(), min(icon_x, max_x))
        icon_y = max(bounds.top(), min(icon_y, max_y))
        self.icon_label.move(icon_x, icon_y)
        self.icon_label.raise_()

    @pyqtSlot()
    def on_dialog_close_btn_clicked(self):
        # if hasattr(self, 'serial_thread_1'):
        # self.serial_thread_1.send_data('stop')  # 发送停止指令
        # self.serial_thread_1.stop()
        # self.serial_thread_1.wait()  # 等待线程完全结束
        # self.serial_thread_1 = None  # 确保资源释放
        self.notice_serial_stop.emit()
        self.notice_style_no.emit()
        print("制作已叉掉")
        self.close()

    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font
    
    def init_font(self):
        AlibabaPuHuiTi_3_85_Bold_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')
        )
        if AlibabaPuHuiTi_3_85_Bold_font_id != -1:
            AlibabaPuHuiTi_3_85_Bold_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_85_Bold_font_id)[0]
            AlibabaPuHuiTi_3_85_Bold_custom_font_32 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 32, QFont.Bold)
            self.order_cancel_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_32)
            self.order_complete_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_32)
            AlibabaPuHuiTi_3_85_Bold_custom_font_20 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 20, QFont.Bold)
            self.progressBar.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            self.order_number_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            AlibabaPuHuiTi_3_85_Bold_custom_font_24 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 24, QFont.Bold)
            self.order_name_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.label_2.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myShow = OrderDialog1(NewTeeBean)
    myShow.show()
    sys.exit(app.exec_())
