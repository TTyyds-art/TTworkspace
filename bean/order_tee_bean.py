class TeeBean:
    def __init__(self):
        self.id = ''
        self.order_sn = ''
        self.take_sn = ''
        self.uni_id = ''
        self.goods_id = ''
        self.name = ''
        self.cover = ''
        self.number = ''
        self.specs_name = ''
        self.old_price = ''
        self.real_price = ''
        self.dishes_select = ''
        self.create_time = ''

    def set_take_sn(self, take_sn):
        self.take_sn = take_sn

    def get_take_sn(self):
        return self.take_sn

    def set_create_time(self, create_time):
        self.create_time = create_time

    def get_create_time(self):
        return self.create_time

    def set_dishes_select(self, dishes_select):
        self.dishes_select = dishes_select

    def get_dishes_select(self):
        return self.dishes_select

    def set_real_price(self, real_price):
        self.real_price = real_price

    def get_real_price(self):
        return self.real_price

    def set_old_price(self, old_price):
        self.old_price = old_price

    def get_old_price(self):
        return self.old_price

    def set_specs_name(self, specs_name):
        self.specs_name = specs_name

    def get_specs_name(self):
        return self.specs_name

    def set_number(self, number):
        self.number = number

    def get_number(self):
        return self.number

    def set_cover(self, cover):
        self.cover = cover

    def get_cover(self):
        return self.cover

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def set_goods_id(self, goods_id):
        self.goods_id = goods_id

    def get_goods_id(self):
        return self.goods_id

    def set_uni_id(self, uni_id):
        self.uni_id = uni_id

    def get_uni_id(self):
        return self.uni_id

    def set_id(self, id):
        self.id = id

    def get_id(self):
        return self.id

    def set_order_sn(self, order_sn):
        self.order_sn = order_sn

    def get_order_sn(self):
        return self.order_sn

    def __str__(self):
        return (f"TeeBean(order_sn={self.order_sn}, id={self.id}, take_sn={self.take_sn}, uni_id={self.uni_id}, "
                f"goods_id={self.goods_id}, name={self.name}, cover={self.cover}, "
                f"number={self.number}, specs_name={self.specs_name}, old_price={self.old_price}, "
                f"real_price={self.real_price}, dishes_select={self.dishes_select}, "
                f"create_time={self.create_time})")
