from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget

from db import db_util
from ui_1080_py.Ui_item_setting_local_message_record_ui import Ui_Form
import sys
import os

class ItemSettingLocalMessageRecordMata(QWidget, Ui_Form):

    def __init__(self, message_bean, is_d, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        style_d = """
        QWidget#widget{
            background-color:rgba(239, 255, 247, 1);
        }
        """
        style_s = """
        QWidget#widget{
            background-color:rgba(255, 255, 255, 1);
        }
        """
        if is_d:
            self.widget.setStyleSheet(style_d)
        else:
            self.widget.setStyleSheet(style_s)

        if message_bean.message_level == '绿色':
            self.l_2.setStyleSheet('color:rgba(44, 159, 97, 1);')
        elif message_bean.message_level == '黄色':
            self.l_2.setStyleSheet('color:rgba(255, 154, 24, 1);')
        elif message_bean.message_level == '红色':
            self.l_2.setStyleSheet('color:rgba(255, 83, 74, 1);')

        self.l_1.setText(message_bean.id)
        self.l_2.setText(message_bean.message_content)
        self.l_3.setText(message_bean.time)

        AlibabaPuHuiTi_3_55_Regular_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf')
        )
        if AlibabaPuHuiTi_3_55_Regular_id != -1:
            AlibabaPuHuiTi_3_55_Regular_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_55_Regular_id)[0]

            AlibabaPuHuiTi_3_55_Regular_font_family_25 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 25)
            self.l_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.l_1.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.l_3.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)

    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font

