from PyQt5.QtCore import QThread
from db import db_util

class OrderNotice(QThread):

    def __init__(self, tee_bean, parent=None):
        super(OrderNotice, self).__init__(parent)
        self.tee_bean = tee_bean


    def run(self):
        # 订单完成 发送通知给服务器
        pass
        