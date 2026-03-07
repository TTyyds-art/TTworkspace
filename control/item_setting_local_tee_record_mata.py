from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget

from bean.new_tee_bean import NewTeeBean
from db import db_util
from ui_1080_py.Ui_item_setting_local_tee_record_ui import Ui_Form
import sys
import os
# 控件实例来显示每条记录
class ItemSettingLocalTeeRecordMata(QWidget, Ui_Form):
    notice_checked = pyqtSignal(NewTeeBean)

    def __init__(self, tee_bean, is_d, is_check, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        if is_check:
            self.widget.installEventFilter(self)
        self.style_d = """
        QWidget#widget{
            background-color:rgba(239, 255, 247, 1);
        }
        """
        self.style_s = """
        QWidget#widget{
            background-color:rgba(255, 255, 255, 1);
        }
        """
        self.no_checked_font_color = 'color:rgba(102, 102, 102, 1);'
        self.check_style = """
        QWidget#widget{
            background-color:rgba(83, 203, 49, 1);
        }
        """
        self.no_check_style = """
        QWidget#widget{
            background-color:rgba(83, 203, 49, 0);
        }
        """
        self.checked_font_color = 'color:white;'

        self.tee_bean = tee_bean
        self.is_d = is_d
        if is_d:
            self.widget.setStyleSheet(self.style_d)   #true时的背景2，4，6等等
        else:
            self.widget.setStyleSheet(self.style_s)
        # 状态 1.已出茶   2.取消   3.未出茶  4.缺料
        if tee_bean.state == '1':
            self.tee_state = '已出茶'
        elif tee_bean.state == '2':
            self.tee_state = '取消'
        elif tee_bean.state == '3':
            self.tee_state = '未出茶'
        elif tee_bean.state == '4':
            self.tee_state = '缺料'

        today_id = db_util.query_today_id_by_order_id(tee_bean.order_id)
        time = db_util.query_order_time_by_order_id(tee_bean.order_id)
        self.l_1.setText(tee_bean.id)           #序号
        self.l_2.setText(today_id)              #取茶号
        self.l_3.setText(tee_bean.product_name) #茶品名称
        self.l_4.setText(time)                  #订单时间
        self.l_5.setText(self.tee_state)        #出茶状态

        AlibabaPuHuiTi_3_55_Regular_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf')
        )
        if AlibabaPuHuiTi_3_55_Regular_id != -1:
            AlibabaPuHuiTi_3_55_Regular_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_55_Regular_id)[0]

            AlibabaPuHuiTi_3_55_Regular_font_family_38 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 38)
            self.l_1.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_38)
            self.l_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_38)
            self.l_3.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_38)
            self.l_4.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_38)
            self.l_5.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_38)

         # 添加一个标志位来记录是否选中
        self.is_selected = False

    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font

    def change_style(self):
        if self.is_d:
            self.widget.setStyleSheet(self.style_d)
        else:
            self.widget.setStyleSheet(self.style_s)
        self.l_1.setStyleSheet(self.no_checked_font_color)
        self.l_2.setStyleSheet(self.no_checked_font_color)
        self.l_3.setStyleSheet(self.no_checked_font_color)
        self.l_4.setStyleSheet(self.no_checked_font_color)
        self.l_5.setStyleSheet(self.no_checked_font_color)
        # print("未选中")

    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if obj == self.widget:
                # print("选中了")
                # self.notice_checked.emit(self.tee_bean)
                # self.widget.setStyleSheet(self.check_style)
                # self.l_1.setStyleSheet(self.checked_font_color)
                # self.l_2.setStyleSheet(self.checked_font_color)
                # self.l_3.setStyleSheet(self.checked_font_color)
                # self.l_4.setStyleSheet(self.checked_font_color)
                # self.l_5.setStyleSheet(self.checked_font_color)
                if self.is_selected:
                    # 如果已经选中，取消选中
                    self.change_style()
                    self.is_selected = False
                else:
                    # 如果未选中，进行选中操作
                    self.notice_checked.emit(self.tee_bean)
                    self.widget.setStyleSheet(self.check_style)
                    self.l_1.setStyleSheet(self.checked_font_color)
                    self.l_2.setStyleSheet(self.checked_font_color)
                    self.l_3.setStyleSheet(self.checked_font_color)
                    self.l_4.setStyleSheet(self.checked_font_color)
                    self.l_5.setStyleSheet(self.checked_font_color)
                    self.is_selected = True
        return super().eventFilter(obj, event)
    