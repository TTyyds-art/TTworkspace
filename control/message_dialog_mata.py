import sys
import os
from PyQt5.QtCore import Qt, pyqtSlot, QThread
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QApplication, QGraphicsBlurEffect
from threads.SerialThread import SerialThread

from ui_1080_py.Ui_message_dialog_ui import Ui_Form


class MessageDialog(QWidget, Ui_Form):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_font()
        self.warn_msg_l.setText(f'输入的账号密码有误,请重新输入!')


    @pyqtSlot()
    def on_order_cancel_btn_clicked(self):
        self.close()

    @pyqtSlot()
    def on_dialog_close_btn_clicked(self):
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
            self.warn_msg_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_32)

