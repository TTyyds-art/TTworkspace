from PyQt5.QtCore import QThread, pyqtSignal

from bean.message_bean import MessageBean
from db import db_util


class RefreshSettingLocalMessageThread(QThread):
    return_local_message_record = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        message_list = db_util.query_all_message_info()
        bean_list = []
        for item_dict in message_list:
            message_bean = MessageBean()
            message_bean.id = str(item_dict['_id'])
            message_bean.message_id = item_dict['message_id']
            message_bean.message_type = item_dict['message_type']
            message_bean.message_level = item_dict['message_level']
            message_bean.message_content = item_dict['message_content']
            message_bean.time = item_dict['time']
            bean_list.append(message_bean)
        bean_list.reverse()
        self.return_local_message_record.emit(bean_list)