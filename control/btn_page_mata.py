import sys
import os
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget

from db import db_util
from ui_1080_py.Ui_btn_page_ui import Ui_Form


class BtnPageMata(QWidget, Ui_Form):
    switch_page = pyqtSignal(int)

    def __init__(self, num, is_check, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.widget.installEventFilter(self)
        self.num = int(num)
        self.label.setText(str(num))
        self.setMinimumSize(34, 34)
        self.setMaximumSize(34, 34)

        self.no_check_widget_style = """
            QWidget#widget{
                background-color:transparent;
                border-radius: 4px;
                border: 1px solid rgba(44, 159, 97, 1);
            }
        """
        self.no_check_label_style = "color:rgba(44, 159, 97, 1);"

        self.check_widget_style = """
                    QWidget#widget{
                        background-color:rgba(44, 159, 97, 1);
                        border-radius: 4px;
                        border: 1px solid rgba(44, 159, 97, 1);
                    }
                """
        self.check_label_style = "color:white;"

        if is_check:
            self.widget.setStyleSheet(self.check_widget_style)
            self.label.setStyleSheet(self.check_label_style)
        else:
            self.widget.setStyleSheet(self.no_check_widget_style)
            self.label.setStyleSheet(self.no_check_label_style)

        AlibabaPuHuiTi_3_65_Medium_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf')
        )
        if AlibabaPuHuiTi_3_65_Medium_id != -1:
            AlibabaPuHuiTi_3_65_Medium_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_65_Medium_id)[0]
            AlibabaPuHuiTi_3_65_Medium_font_family_22 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 22)
            self.label.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_22)

    def change_no_check(self, num):
        self.widget.setStyleSheet(self.no_check_widget_style)
        self.label.setStyleSheet(self.no_check_label_style)
        if num == self.num:
            self.widget.setStyleSheet(self.check_widget_style)
            self.label.setStyleSheet(self.check_label_style)

    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if obj == self.widget:
                self.switch_page.emit(self.num)
        return super().eventFilter(obj, event)
    
    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font

