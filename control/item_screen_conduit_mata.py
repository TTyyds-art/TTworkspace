import random

import sys
import os
from datetime import datetime, timedelta

from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QHBoxLayout

from control.item_conduit_widget import QBarPainter
from tool_utils import util
from ui_1080_py.Ui_item_screen_conduit_ui import Ui_Form


class ItemScreenConduitWMata(QWidget, Ui_Form):


    def __init__(self, conduit_bean, parent=None):
        super().__init__(parent)
        self.Layout = None
        self.setupUi(self)
        self.conduit_bean = conduit_bean
        self.init_layout()
        self.init_font()
        self.init_ui()

    def init_layout(self):
        self.Layout = QHBoxLayout(self.widget_2)
        self.Layout.setObjectName("Layout")
        self.Layout.setContentsMargins(0, 0, 0, 0)
        self.Layout.setSpacing(0)

    def init_bar(self, p_value, max_value, y_value, r_value, is_shield, conduit_id=None):
        util.clear_layout(self.Layout)
        bar = QBarPainter(p_value, max_value, y_value, r_value, is_shield, conduit_id)
        self.Layout.addWidget(bar)

    def init_ui(self):
        self.l_conduit.setText(self.conduit_bean.conduit)
        self.l_name.setText(self.conduit_bean.name)
        margin = self.conduit_bean.margin
        self.l_margin.setText(f'{margin}g')
        h_m_list = self.conduit_bean.effective_time.split(':')
        e_hour = int(h_m_list[0])
        e_minute = int(h_m_list[1])
        end_time = datetime.strptime(self.conduit_bean.begin_time, "%Y-%m-%d %H:%M:%S") + timedelta(hours=e_hour,
                                                                                               minutes=e_minute)
        str_time = end_time.strftime('%H:%M:%S')
        self.l_time.setText(str_time)

        max_g = self.conduit_bean.max_capacity[:-1]
            # 黄色预警值
        y_value = int(self.conduit_bean.yellow_warning_value)
        r_value = int(self.conduit_bean.red_warning_value)
        is_shield = self.conduit_bean.shield
        conduit_id = self.conduit_bean.conduit  # 传入通道ID
        self.init_bar(int(margin), int(max_g), y_value, r_value, is_shield, conduit_id)

    def update_conduit_bean(self, conduit_list):
        for conduit_bean in conduit_list:
            if self.conduit_bean.conduit == conduit_bean.conduit:
                self.conduit_bean = conduit_bean
                break
        self.init_ui()

    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font
    
    def init_font(self):
        AlibabaPuHuiTi_3_55_Regular_id = QFontDatabase.addApplicationFont(
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf')
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf'
        )
        if AlibabaPuHuiTi_3_55_Regular_id != -1:
            AlibabaPuHuiTi_3_55_Regular_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_55_Regular_id)[0]
            AlibabaPuHuiTi_3_55_Regular_font_family_18 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 18)
            self.l_time.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            AlibabaPuHuiTi_3_55_Regular_font_family_25 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 22)
            self.l_conduit.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.l_name.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.l_margin.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)

