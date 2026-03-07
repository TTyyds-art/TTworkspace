import random

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScroller

from control.item_notice_message_mata import ItemNoticeMessageMata
from control.item_notice_remind_mata import ItemNoticeRemindMata
from control.item_notice_warn_mata import ItemNoticeWarnMata
from ui_1080_py.Ui_outtee_notice_ui import Ui_Form


class OutTeeNoticeMata(QWidget, Ui_Form):

    def __init__(self, message_list, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        # 设置窗体无边框 设置背景透明
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.scrollArea.horizontalScrollBar().setVisible(False)
        QScroller.grabGesture(self.scrollArea.viewport(), QScroller.LeftMouseButtonGesture)
        self.content_list_Layout = QVBoxLayout(self.content_list_widget)
        self.content_list_Layout.setObjectName("content_list_Layout")

        ui = None
        for message_bean in message_list:
            if message_bean.message_level == '绿色':
                ui = ItemNoticeMessageMata(message_bean.message_type, message_bean.message_content)
            elif message_bean.message_level == '黄色':
                ui = ItemNoticeRemindMata(message_bean.message_type, message_bean.message_content)
            elif message_bean.message_level == '红色':
                ui = ItemNoticeWarnMata(message_bean.message_type,message_bean.message_content)

            self.content_list_Layout.addWidget(ui)