import json

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from bean.order_tee_bean import TeeBean


class OrderThread(QThread):
    result_tee_bean = pyqtSignal(TeeBean)

    def __init__(self, phone_number, store_id, token, nickname, parent=None):
        super(OrderThread, self).__init__(parent)
        self.token = token
        self.phone_number = phone_number
        self.store_id = store_id
        self.nickname = nickname

    def run(self):
        r_token = "Bearer" + " " + self.token
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Phone': f'{self.phone_number}',
            'Storeid': self.store_id,
            "authorization": r_token
        }
        order_url = 'https://cy.zhudianyou.com/api/call/order/list'
        try:
            order_res = requests.get(order_url, headers=headers)
            # print(f'order_res:{order_res.text}')
            order_all = order_res.json()['data']['order_all']
            for tee_item in order_all:
                order_sn = tee_item['order_sn']
                take_sn = tee_item['take_sn']
                create_time = tee_item['create_time']
                tee_dict = tee_item['goods_list'][0]
                id = tee_dict['id']
                uni_id = tee_dict['uni_id']
                goods_id = tee_dict['goods_id']
                name = tee_dict['name']
                cover = tee_dict['cover']
                number = tee_dict['number']
                specs_name = tee_dict['specs_name']
                old_price = tee_dict['old_price']
                real_price = tee_dict['real_price']
                dishes_select = tee_dict['dishes_select']
                tee_bean = TeeBean()
                tee_bean.set_order_sn(str(order_sn))
                tee_bean.set_take_sn(str(take_sn))
                tee_bean.set_create_time(str(create_time))
                tee_bean.set_id(str(id))
                tee_bean.set_uni_id(str(uni_id))
                tee_bean.set_goods_id(str(goods_id))
                tee_bean.set_name(str(name))
                tee_bean.set_cover(str(cover))
                tee_bean.set_number(str(number))
                tee_bean.set_specs_name(str(specs_name))
                tee_bean.set_old_price(str(old_price))
                tee_bean.set_real_price(str(real_price))
                tee_bean.set_dishes_select(str(dishes_select))
                self.result_tee_bean.emit(tee_bean)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except ValueError as ve:
            print(f"JSON decoding failed: {ve}")
        except KeyError as ke:
            print(f"KeyError: {ke}")
