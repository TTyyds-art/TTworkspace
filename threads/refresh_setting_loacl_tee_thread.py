from PyQt5.QtCore import QThread, pyqtSignal

from bean.new_tee_bean import NewTeeBean
from db import db_util


class RefreshSettingLocalTeeThread(QThread):
    return_local_tee_record = pyqtSignal(list,list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        complete_tee_list = db_util.query_tee_info_by_state_1_or_4()
        complete_bean_list = []
        for item_dict in complete_tee_list:
            tee_bean = NewTeeBean()
            tee_bean.id = str(item_dict['_id'])
            tee_bean.order_id = item_dict['order_id']
            tee_bean.product_id = item_dict['product_id']
            tee_bean.product_name = item_dict['product_name']
            tee_bean.product_sugar = item_dict['product_sugar']
            tee_bean.product_quantity = item_dict['product_quantity']
            tee_bean.product_ice = item_dict['product_ice']
            tee_bean.product_simp = item_dict['product_simp']
            tee_bean.unit_price = item_dict['unit_price']
            tee_bean.num_tee = item_dict['num_tee']
            tee_bean.state = item_dict['state']
            tee_bean.recipe = item_dict['recipe']
            complete_bean_list.append(tee_bean)

        lack_tee_list = db_util.query_tee_info_by_state_4()
        lack_bean_list = []
        for item_dict in lack_tee_list:
            tee_bean = NewTeeBean()
            tee_bean.id = str(item_dict['_id'])
            tee_bean.order_id = item_dict['order_id']
            tee_bean.product_id = item_dict['product_id']
            tee_bean.product_name = item_dict['product_name']
            tee_bean.product_sugar = item_dict['product_sugar']
            tee_bean.product_quantity = item_dict['product_quantity']
            tee_bean.product_ice = item_dict['product_ice']
            tee_bean.product_simp = item_dict['product_simp']
            tee_bean.unit_price = item_dict['unit_price']
            tee_bean.num_tee = item_dict['num_tee']
            tee_bean.state = item_dict['state']
            tee_bean.recipe = item_dict['recipe']
            lack_bean_list.append(tee_bean)

        complete_bean_list.reverse()
        lack_bean_list.reverse()
        self.return_local_tee_record.emit(complete_bean_list, lack_bean_list)