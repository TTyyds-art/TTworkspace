from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGridLayout, QSizePolicy, QScroller

from control.item_screen_conduit_mata import ItemScreenConduitWMata
from threads.manager_second_screen_conduit_thread import ManagerSecondScreenConduit
from tool_utils import util
from ui_1080_py.Ui_second_screen_ui import Ui_Form
import sys
import os

class SecondScreenMata(QWidget, Ui_Form):
    notice_close = pyqtSignal()
    notice_item_conduit = pyqtSignal(list)

    def __init__(self, geo, conduit_beans, parent=None):
        super().__init__(parent)
        self.manager_thread = None
        self.conduit_gridLayout = None
        self.conduit_beans = conduit_beans
        self.conduit_content_Layout = None
        self.setupUi(self)
        self.on_off_widget.installEventFilter(self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.auto_isChecked = True
        self.off_widget.setVisible(False)
        self.on_widget.setVisible(True)
        self.move(geo.x(), geo.y())
        self.init_font()
        self.init_gridLayout_widget()
        self.show_conduit_bean(conduit_beans)
        self.manager_conduit_thread()

    def manager_conduit_thread(self):
        self.manager_thread = ManagerSecondScreenConduit()
        self.manager_thread.result_conduit_bean.connect(self.update_conduit_data)
        self.manager_thread.start()

    def update_conduit_data(self, conduit_beans):
        self.conduit_beans = conduit_beans
        self.notice_item_conduit.emit(conduit_beans)

    def show_conduit_bean(self, conduit_beans):
        # 计算需要占位的空位置
        total_cells = 30
        used_cells = len(conduit_beans)
        empty_cells = total_cells - used_cells

        for conduit_num in range(len(conduit_beans)):
            scan_row = conduit_num // 6
            scan_col = conduit_num % 6
            conduit_card_ui = ItemScreenConduitWMata(conduit_beans[conduit_num])
            self.notice_item_conduit.connect(conduit_card_ui.update_conduit_bean)
            conduit_card_ui.setFixedSize(250, 182)
            self.conduit_gridLayout.addWidget(conduit_card_ui, scan_row, scan_col, 1, 1)

        # 填充剩余的空位置
        if empty_cells > 0:
            for num in range(used_cells, total_cells):
                row = num // 6
                col = num % 6
                # 创建一个占位控件
                placeholder_widget = QWidget()
                placeholder_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.conduit_gridLayout.addWidget(placeholder_widget, row, col, 1, 1)

    def init_gridLayout_widget(self):
        self.scrollArea.verticalScrollBar().setVisible(False)
        self.scrollArea.horizontalScrollBar().setVisible(False)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scrollArea.viewport(), QScroller.LeftMouseButtonGesture)
        self.conduit_content_Layout = QHBoxLayout(self.conduit_content)
        self.conduit_content_Layout.setObjectName("order_content_Layout")
        self.conduit_content_Layout.setContentsMargins(30, 30, 0, 30)
        self.conduit_content_Layout.setSpacing(0)
        self.conduit_gridLayout = QGridLayout()
        self.conduit_gridLayout.setObjectName("order_gridLayout")
        self.conduit_gridLayout.setHorizontalSpacing(30)
        self.conduit_gridLayout.setVerticalSpacing(30)
        self.conduit_content_Layout.addLayout(self.conduit_gridLayout)

    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if obj == self.on_off_widget:
                self.auto_tee_state_change(self.auto_isChecked)
        return super().eventFilter(obj, event)

    def auto_tee_state_change(self, is_checked):
        if not is_checked:
            self.auto_isChecked = True
            self.off_widget.setVisible(False)
            self.on_widget.setVisible(True)
            self.show_conduit_bean(self.conduit_beans)
        else:
            self.auto_isChecked = False
            self.off_widget.setVisible(True)
            self.on_widget.setVisible(False)
            util.clear_layout(self.conduit_gridLayout)

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

            AlibabaPuHuiTi_3_55_Regular_font_family_25 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 25)
            self.outtee_title_material_1.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_3.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_4.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.label.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.label.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)

        AlibabaPuHuiTi_3_85_Bold_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')
        )
        if AlibabaPuHuiTi_3_85_Bold_id != -1:
            AlibabaPuHuiTi_3_85_Bold_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_85_Bold_id)[0]

            AlibabaPuHuiTi_3_85_Bold_font_family_35 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 36, QFont.Bold)
            self.name_on.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_35)
            self.name_off.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_35)











