class NewTeeBean:
    """
    {
      "order_id": "O20240619123000",//时间
      "order_time": "2024-06-19 12:30:00",
      {
        "product_id": "P1001",//在菜单上的编号
        "product_name": "珍珠奶茶",
        "product_sugar": "半糖",
        "product_quantity": "中杯",
        "product_ice": "少冰",
        “product_simp”: "珍珠, 椰果, 果冻",
        "unit_price": 15.0
      },
      {
        "product_id": "P1002", //在菜单上的编号
        "product_name": "椰果奶茶",
        "product_sugar": "微糖",
        "product_quantity": "大杯 ",
        "product_ice": "正常冰",
        “product_simp”: "珍珠, 椰果, 果冻",
        "unit_price": 12.0
      },
      "remarks": "不要加冰，请提前通知到达时间。"
    }
订单字段
对应的数据库是tee_info

    """
    def __init__(self):
        # 主键 _id
        self.id = ''
        # id 数字时间
        self.order_id = ''
        # 在菜单上的编号
        self.product_id = ''
        # 产品名称
        self.product_name = ''
        # "半糖"
        self.product_sugar = ''
        # 中杯
        self.product_quantity = ''
        # 少冰
        self.product_ice = ''
        # "珍珠, 椰果, 果冻"
        self.product_simp = ''
        # 15.0
        self.unit_price = ''
        # 杯数
        self.num_tee = ''
        # 状态 1.已出茶   2.取消   3.未出茶  4.缺料  5.debug未出茶  6.debug取消  7.debug已出茶
        self.state = ''
        # 配方
        self.recipe = ''
    
    def get_id(self):
        return self.id

    def set_id(self, id):
        self.id = id

    def get_order_id(self):
        return self.order_id

    def set_order_id(self, order_id):
        self.order_id = order_id

    def get_product_id(self):
        return self.product_id

    def set_product_id(self, product_id):
        self.product_id = product_id

    def get_product_name(self):
        return self.product_name

    def set_product_name(self, product_name):
        self.product_name = product_name

    def get_product_sugar(self):
        return self.product_sugar

    def set_product_sugar(self, product_sugar):
        self.product_sugar = product_sugar

    def get_product_quantity(self):
        return self.product_quantity

    def set_product_quantity(self, product_quantity):
        self.product_quantity = product_quantity

    def get_product_ice(self):
        return self.product_ice

    def set_product_ice(self, product_ice):
        self.product_ice = product_ice

    def get_product_simp(self):
        return self.product_simp

    def set_product_simp(self, product_simp):
        self.product_simp = product_simp

    def get_unit_price(self):
        return self.unit_price

    def set_unit_price(self, unit_price):
        self.unit_price = unit_price

    def get_num_tee(self):
        return self.num_tee

    def set_num_tee(self, num_tee):
        self.num_tee = num_tee

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def get_recipe(self):
        return self.recipe

    def set_recipe(self, recipe):
        self.recipe = recipe

    def toString(self):
        print(
            f'self.id={self.id}\n'
            f'self.order_id={self.order_id}\n'
            f'self.product_id={self.product_id}\n'
            f'self.product_name={self.product_name}\n'
            f'self.product_sugar={self.product_sugar}\n'
            f'self.product_quantity={self.product_quantity}\n'
            f'self.product_ice={self.product_ice}\n'
            f'self.product_simp={self.product_simp}\n'
            f'self.unit_price={self.unit_price}\n'
            f'self.num_tee={self.num_tee}\n'
            f'self.state={self.state}')
