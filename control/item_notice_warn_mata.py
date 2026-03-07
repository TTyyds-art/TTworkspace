from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget

from ui_1080_py.Ui_item_notice_warn_ui import Ui_Form
import sys
import os

class ItemNoticeWarnMata(QWidget, Ui_Form):

    def __init__(self, title, content, parent=None):
        super(ItemNoticeWarnMata, self).__init__(parent)
        self.setupUi(self)
        self.l_title.setText(title)
        self.l_content.setText(content)
        self.init_font()

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

            AlibabaPuHuiTi_3_55_Regular_font_family_22 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 22)
            self.l_content.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_22)

            AlibabaPuHuiTi_3_55_Regular_font_family_24 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 24)
            self.l_title.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_24)

    @pyqtSlot()
    def on_btn_close_clicked(self):
        self.close()