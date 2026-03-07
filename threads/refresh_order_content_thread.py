import time

from PyQt5.QtCore import QThread, pyqtSignal

from bean.new_tee_bean import NewTeeBean
from db import db_util


class RefreshOrderContentThread(QThread):
    return_order_tee_bean_list = pyqtSignal(list)

    def __init__(self, is_login, is_debug, parent=None):
        super().__init__(parent)
        self.is_login = is_login
        self.is_debug = is_debug
        print(f'self.is_login:{self.is_login}  self.is_debug:{self.is_debug}')

    def run(self):
        if self.is_login:
            time.sleep(0.5)
            tee_list = db_util.query_products_by_tee_state('3')
            bean_list = []
            for item_dict in tee_list:
                tee_bean = NewTeeBean()
                """
                item:{
                    'order_id': 'O20241218162244', 
                    'product_id': 'P1001', 
                    'product_name': '葡萄肉多多', 
                    'product_sugar': '常规', 
                    'product_quantity': '中杯', 
                    'product_ice': '少冰', 
                    'product_simp': '', 
                    'unit_price': '18.00',
                    'state' : '3'
                    }
                """
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
                bean_list.append(tee_bean)
            self.return_order_tee_bean_list.emit(bean_list)

        if self.is_debug:
            time.sleep(1)
            tee_list = db_util.query_products_by_tee_state('5')
            bean_list = []
            for item_dict in tee_list:
                tee_bean = NewTeeBean()
                """
                item:{
                    'order_id': 'O20241218162244', 
                    'product_id': 'P1001', 
                    'product_name': '葡萄肉多多', 
                    'product_sugar': '常规', 
                    'product_quantity': '中杯', 
                    'product_ice': '少冰', 
                    'product_simp': '', 
                    'unit_price': '18.00',
                    'state' : '5'
                    }
                """
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
                bean_list.append(tee_bean)
            self.return_order_tee_bean_list.emit(bean_list)