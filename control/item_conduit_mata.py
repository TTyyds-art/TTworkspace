import random
import sys
import os
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QApplication

from control.item_conduit_widget import QBarPainter
from tool_utils import util
from ui_1080_py.Ui_item_conduit_ui import Ui_Form


class ItemConduitMata(QWidget, Ui_Form):

    def __init__(self, conduit_bean, parent=None):
        super(ItemConduitMata, self).__init__(parent)
        self.setupUi(self)
        self.conduit_bean = conduit_bean
        self.init_ui()
        self.init_font()

    def init_ui(self):
        self.l_name.setText(self.conduit_bean.conduit)
        margin = self.conduit_bean.margin
        max_g = self.conduit_bean.max_capacity[:-1]
        # 黄色预警值
        y_value = int(self.conduit_bean.yellow_warning_value)
        r_value = int(self.conduit_bean.red_warning_value)
        is_shield = self.conduit_bean.shield
        self.init_bar(int(margin), int(max_g) ,y_value, r_value, is_shield, self.conduit_bean.conduit)

    def init_bar(self, p_value, max_value, y_value, r_value, is_shield, conduit_id=None):
        util.clear_layout(self.Layout)
        # p_value = random.randint(0, max_value)
        bar = QBarPainter(p_value, max_value, y_value, r_value, is_shield, conduit_id)
        self.Layout.addWidget(bar)

    def update_conduit_bean(self, conduits_list):
        # print(f'conduit_list:{conduits_list}')
        for conduit_bean in conduits_list:
            if self.conduit_bean.conduit == conduit_bean.conduit:
                self.conduit_bean = conduit_bean
                break
        self.init_ui()

    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font

    def init_font(self):
        AlibabaPuHuiTi_3_105_Heavy_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-105-Heavy/AlibabaPuHuiTi-3-105-Heavy.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-105-Heavy/AlibabaPuHuiTi-3-105-Heavy.ttf')
        )
        if AlibabaPuHuiTi_3_105_Heavy_id != -1:
            AlibabaPuHuiTi_3_105_Heavy_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_105_Heavy_id)[0]
            AlibabaPuHuiTi_3_105_Heavy_font_family_20 = QFont(AlibabaPuHuiTi_3_105_Heavy_font_family, 20, QFont.Bold)
            self.l_name.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_20)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = ItemConduitMata()
    window.show()
    sys.exit(app.exec_())