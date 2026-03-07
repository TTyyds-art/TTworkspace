from PyQt5.QtCore import QThread

from db import db_util


class MessageSaveToDB(QThread):

    def __init__(self, message_bean, parent=None):
        super().__init__(parent)
        self.message_bean = message_bean

    def run(self):
        if db_util.insert_message_info(
                self.message_bean.message_id,
                self.message_bean.message_type,
                self.message_bean.message_level,
                self.message_bean.message_content,
                self.message_bean.time):
            print("message_info 插入成功")
        else:
            print("message_info 插入失败")
    
        