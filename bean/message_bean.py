class MessageBean:
    """
    {
    "message_id": "MSG001",
    "message_type": "设备故障",
    "message_level": "红色",
    "message_content": "设备无响应，请检查设备。某某管道没响应。",
    "time": "2024-06-19 12:00:00"
    }，
    对应的数据库是 message_info
    """
    def __init__(self):
        # 主键 _id
        self.id = ''
        # "MSG001"
        self.message_id = ''
        # "设备故障",
        self.message_type = ''
        # "红色"
        self.message_level = ''
        # "设备无响应，请检查设备。某某管道没响应。"
        self.message_content = ''
        # "2024-06-19 12:00:00"
        self.time = ''

    def toString(self):
        print(
            f'self.id={self.id}\n'
            f'self.message_id={self.message_id}\n'
            f'self.message_type={self.message_type}\n'
            f'self.message_level={self.message_level}\n'
            f'self.message_content={self.message_content}\n'
            f'self.time={self.time}\n')