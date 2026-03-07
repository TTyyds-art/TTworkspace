from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget

from ui_1080_py.Ui_manager_keyboard_ui import Ui_Form
import sys
import os

class ManagerKeyboardMata(QWidget, Ui_Form):
    result_context = pyqtSignal(str)
    result_clear = pyqtSignal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_font()

    @pyqtSlot()
    def on_btn_1_clicked(self):
        self.result_context.emit('1')

    @pyqtSlot()
    def on_btn_2_clicked(self):
        self.result_context.emit('2')

    @pyqtSlot()
    def on_btn_3_clicked(self):
        self.result_context.emit('3')

    @pyqtSlot()
    def on_btn_4_clicked(self):
        self.result_context.emit('4')

    @pyqtSlot()
    def on_btn_50_clicked(self):
        self.result_context.emit('50')

    @pyqtSlot()
    def on_btn_6_clicked(self):
        self.result_context.emit('6')

    @pyqtSlot()
    def on_btn_7_clicked(self):
        self.result_context.emit('7')

    @pyqtSlot()
    def on_btn_8_clicked(self):
        self.result_context.emit('8')

    @pyqtSlot()
    def on_btn_9_clicked(self):
        self.result_context.emit('9')

    @pyqtSlot()
    def on_btn_0_clicked(self):
        self.result_context.emit('0')

    @pyqtSlot()
    def on_btn_5_5_clicked(self):
        self.result_context.emit('5')

    @pyqtSlot()
    def on_btn_10_clicked(self):
        self.result_context.emit('10')

    @pyqtSlot()
    def on_btn_20_clicked(self):
        self.result_context.emit('20')

    @pyqtSlot()
    def on_btn_clear_clicked(self):
        self.result_clear.emit()

    @pyqtSlot()
    def on_btn_ok_clicked(self):
        self.close()

    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font
    def init_font(self):
        DIN_Alternate_Bold_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/DIN Alternate Bold.TTF'
            self.get_font_path('fonts/DIN Alternate Bold.TTF')
        )
        if DIN_Alternate_Bold_font_id != -1:
            DIN_Alternate_Bold_font_family = QFontDatabase.applicationFontFamilies(
                DIN_Alternate_Bold_font_id)[0]
            DIN_Alternate_Bold_font_family_40 = QFont(DIN_Alternate_Bold_font_family, 40, QFont.Bold)
            self.btn_1.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_2.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_3.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_4.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_50.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_6.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_7.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_8.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_9.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_0.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_10.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_20.setFont(DIN_Alternate_Bold_font_family_40)
            self.btn_5_5.setFont(DIN_Alternate_Bold_font_family_40)

        AlibabaPuHuiTi_3_65_Medium_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf')
        )
        if AlibabaPuHuiTi_3_65_Medium_id != -1:
            AlibabaPuHuiTi_3_65_Medium_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_65_Medium_id)[0]
            AlibabaPuHuiTi_3_65_Medium_font_family_32 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 32, QFont.Medium)
            self.btn_ok.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_32)
            self.btn_clear.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_32)