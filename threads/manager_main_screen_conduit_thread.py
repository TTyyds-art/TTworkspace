import time

from PyQt5.QtCore import QThread, pyqtSignal

from bean.new_conduit_bean import NewConduitBean
from db import db_util


class ManagerMainScreenConduit(QThread):
    result_conduit_bean = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True

    def run(self):
        while self.is_running:
            time.sleep(1)
            conduit_list = db_util.query_all_conduit_info()
            db_bean_list = []
            for item_dict in conduit_list:
                db_conduit_bean = NewConduitBean()
                """
                item:{
                    '_id': 'O20241218162244', 
                    'conduit': 'P1001', 
                    'margin': '葡萄肉多多', 
                    'conduit_type': '常规', 
                    'name': '中杯', 
                    'shield': '少冰', 
                    'begin_time': '', 
                    'effective_time': '18.00',
                    'red_warning_value' : '3',
                    'yellow_warning_value' : '3'
                    }
                """
                db_conduit_bean.id = str(item_dict['_id'])
                db_conduit_bean.conduit = item_dict['conduit']
                db_conduit_bean.margin = item_dict['margin']
                db_conduit_bean.max_capacity = item_dict['max_capacity']
                db_conduit_bean.conduit_type = item_dict['conduit_type']
                db_conduit_bean.name = item_dict['name']
                db_conduit_bean.shield = item_dict['shield']
                db_conduit_bean.begin_time = item_dict['begin_time']
                db_conduit_bean.effective_time = item_dict['effective_time']
                db_conduit_bean.red_warning_value = item_dict['red_warning_value']
                db_conduit_bean.yellow_warning_value = item_dict['yellow_warning_value']
                db_bean_list.append(db_conduit_bean)
            self.result_conduit_bean.emit(db_bean_list)

    def close_thread(self):
        self.is_running = False