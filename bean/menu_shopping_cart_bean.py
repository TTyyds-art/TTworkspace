class MenuShoppingCartBean:
##加入购物车的数据
    def __init__(self):
        self.name = ''
        self.number = ''
        self.price = ''
        self.suger = ''
        self.size = ''
        self.is_cbb = False
        self.is_yg = False
        self.is_zz = False
        self.is_yy = False
        self.is_mgd = False
        self.ice = ''
        self.total = ''
        self.recipe = ''

    # Getter and Setter for name
    def get_size(self):
        return self.size

    def set_size(self, size):
        self.size = size

    # Getter and Setter for name
    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    # Getter and Setter for number
    def get_number(self):
        return self.number

    def set_number(self, number):
        self.number = number

    # Getter and Setter for price
    def get_price(self):
        return self.price

    def set_price(self, price):
        self.price = price

    # Getter and Setter for suger
    def get_suger(self):
        return self.suger

    def set_suger(self, suger):
        self.suger = suger

    # Getter and Setter for is_cbb
    def get_is_cbb(self):
        return self.is_cbb

    def set_is_cbb(self, is_cbb):
        self.is_cbb = is_cbb

    # Getter and Setter for is_yg
    def get_is_yg(self):
        return self.is_yg

    def set_is_yg(self, is_yg):
        self.is_yg = is_yg

    # Getter and Setter for is_zz
    def get_is_zz(self):
        return self.is_zz

    def set_is_zz(self, is_zz):
        self.is_zz = is_zz

    # Getter and Setter for is_yy
    def get_is_yy(self):
        return self.is_yy

    def set_is_yy(self, is_yy):
        self.is_yy = is_yy

    # Getter and Setter for is_mgd
    def get_is_mgd(self):
        return self.is_mgd

    def set_is_mgd(self, is_mgd):
        self.is_mgd = is_mgd

    # Getter and Setter for ice
    def get_ice(self):
        return self.ice

    def set_ice(self, ice):
        self.ice = ice

    # Getter and Setter for total
    def get_total(self):
        return self.total

    def set_total(self, total):
        self.total = total

    # toString method
    def __str__(self):
        return (f"MenuShoppingCartBean(name='{self.name}', number='{self.number}', price='{self.price}', "
                f"suger='{self.suger}', is_cbb={self.is_cbb}, is_yg={self.is_yg}, is_zz={self.is_zz}, "
                f"is_yy={self.is_yy}, is_mgd={self.is_mgd}, ice='{self.ice}', total='{self.total}')")
