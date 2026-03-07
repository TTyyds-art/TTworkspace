from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget

from bean.new_tee_bean import NewTeeBean
from ui_1080_py.Ui_order_card_ui import Ui_Form
import sys
import os

class OrderCardWidget(QWidget, Ui_Form):
    changed_order = pyqtSignal(NewTeeBean, bool)

    def __init__(self, tee_bean, parent=None):
        super(OrderCardWidget, self).__init__(parent)
        self.setupUi(self)
        self.tee_bean = tee_bean
        self.is_widget_styled = False          # 初始化状态标志
        self.widget.installEventFilter(self)
        self.no_style = """
            QWidget#widget{
                background-color:rgb(236, 253, 239);
                border-bottom: 1px solid rgb(44, 159, 97, 0.2);
                border-radius:20px;
            }
        """
        self.change_style ="""
            QWidget#widget{
                background-color:rgb(140, 240, 255);
                border-bottom: 1px solid rgb(44, 159, 97, 0.2);
                border-radius:20px;
            }
        """
        self.init_font()
        self.init_ui(tee_bean)

    def init_ui(self, tee_bean):
        # 设置card id
        self.l_order_number.setText(tee_bean.product_id)
        # 设置名称
        name = tee_bean.product_name
        self.l_name.setText(name)
        # 设置价格
        real_price = tee_bean.unit_price
        self.l_price.setText(f'￥{real_price}')
        # 设置个数
        num = tee_bean.num_tee
        self.l_number.setText(f"*{num}")

    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if obj == self.widget:
                # self.changed_order.emit(self.tee_bean)
                # self.widget.setStyleSheet(self.change_style)
                # print(f"self.change_style")
                 # 切换状态标志
                self.is_widget_styled = not self.is_widget_styled
                if self.is_widget_styled:
                    # 如果状态为 True，设置为改变后的样式
                    self.changed_order.emit(self.tee_bean, True)
                    self.widget.setStyleSheet(self.change_style)
                    print(f"self.change_style")
                else:
                    # 如果状态为 False，设置为默认样式
                    self.changed_order.emit(self.tee_bean, False)
                    self.widget.setStyleSheet(self.no_style)
                    print(f"self.no_style")
        return super().eventFilter(obj, event)

    def cancel_order(self, type_order, tee_bean):
        if self.tee_bean.get_take_sn() == tee_bean.get_take_sn():
            if type_order == 1:
                # 关闭订单
                self.notice_server(tee_bean)
                print(f"cancel_order")
                self.widget.setStyleSheet(self.no_style)
                self.close()
            elif type_order == 0:
                # 订单完成 关闭
                self.close()

    def refresh_ui(self):
        print(f'{self.tee_bean.product_id}关闭')
        self.close()

    def set_no_style(self):
        # print("触发")
        self.widget.setStyleSheet(self.no_style)
        self.is_widget_styled = False

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

            AlibabaPuHuiTi_3_55_Regular_font_family_24 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 24)
            self.l_number.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_24)

            AlibabaPuHuiTi_3_55_Regular_font_family_26 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 26)
            self.l_name.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_26)

        AlibabaPuHuiTi_3_65_Medium_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf')
        )
        if AlibabaPuHuiTi_3_65_Medium_id != -1:
            AlibabaPuHuiTi_3_65_Medium_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_65_Medium_id)[0]
            AlibabaPuHuiTi_3_65_Medium_font_family_22 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 22)
            self.label_4.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_22)
            self.l_price.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_22)

        AlibabaPuHuiTi_3_85_Bold_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')
        )
        if AlibabaPuHuiTi_3_85_Bold_id != -1:
            AlibabaPuHuiTi_3_85_Bold_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_85_Bold_id)[0]
            AlibabaPuHuiTi_3_85_Bold_font_family_24 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 18, QFont.Bold)
            self.label.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_24)

            AlibabaPuHuiTi_3_85_Bold_font_family_26 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 26, QFont.Bold)
            self.l_order_number.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_26)



