class OrderBean:
    """
        {
          "order_id": "O20240619123000",//时间
          "order_time": "2024-06-19 12:30:00",
          "remarks": "不要加冰，请提前通知到达时间。"
          "state": "状态"
          "today_id"  今日取茶号
    对应的数据库是order_info

    """
    def __init__(self):
        # 主键 _id
        self.id = ''
        # id 数字时间
        self.order_id = ''
        # 时间
        self.order_time = ''
        # 备注
        self.remarks = ''
        # 今日取茶号
        self.today_id = ''
        # 茶列表
        self.tee_list = []

    def toString(self):
        print(f'self.order_id={self.order_id}\n'
              f'self.order_time={self.order_time}\n'
              f'self.remarks={self.remarks}\n'
              f'self.today_id={self.today_id}\n'
              f'self.tee_list={self.tee_list}\n')