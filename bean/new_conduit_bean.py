class NewConduitBean:
    """
    对应的数据库conduit_info
    """
    def __init__(self):
        # 主键id
        self.id = ''
        # 管道
        self.conduit = ''
        # 余量
        self.margin = ''
        # 最大量
        self.max_capacity = ''
        # 类型
        self.conduit_type = ''
        # 名称
        self.name = ''
        # 是否屏蔽 1.不屏蔽 2.屏蔽
        self.shield = ''
        # 开始时间
        self.begin_time = ''
        # 有效时间
        self.effective_time = ''
        # 红色预警值
        self.red_warning_value = ''
        # 黄色预警值
        self.yellow_warning_value = ''

    def get_id(self):
        return self.id

    def set_id(self, id):
        self.id = id

    def get_conduit(self):
        return self.conduit

    def set_conduit(self, conduit):
        self.conduit = conduit

    def get_margin(self):
        return self.margin

    def set_margin(self, margin):
        self.margin = margin

    def get_max_capacity(self):
        return self.max_capacity

    def set_max_capacity(self, max_capacity):
        self.max_capacity = max_capacity

    def get_conduit_type(self):
        return self.conduit_type

    def set_conduit_type(self, conduit_type):
        self.conduit_type = conduit_type

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_shield(self):
        return self.shield

    def set_shield(self, shield):
        self.shield = shield

    def get_begin_time(self):
        return self.begin_time

    def set_begin_time(self, begin_time):
        self.begin_time = begin_time

    def get_effective_time(self):
        return self.effective_time

    def set_effective_time(self, effective_time):
        self.effective_time = effective_time

    def get_red_warning_value(self):
        return self.red_warning_value

    def set_red_warning_value(self, red_warning_value):
        self.red_warning_value = red_warning_value

    def get_yellow_warning_value(self):
        return self.yellow_warning_value

    def set_yellow_warning_value(self, yellow_warning_value):
        self.yellow_warning_value = yellow_warning_value

    def toString(self):
        print(
            f'self.id={self.id}\n'
            f'self.conduit={self.conduit}\n'
            f'self.margin={self.margin}\n'
            f'self.conduit_type={self.conduit_type}\n'
            f'self.name={self.name}\n'
            f'self.shield={self.shield}\n'
            f'self.begin_time={self.begin_time}\n'
            f'self.effective_time={self.effective_time}\n'
            f'self.red_warning_value={self.red_warning_value}\n'
            f'self.yellow_warning_value={self.yellow_warning_value}\n')
        
    def is_shielded(self):
        # 【新增】冰 / 碎冰永远不算屏蔽
        if str(self.conduit) in ("1", "2"):
            return False
        return self.shield == "2"

