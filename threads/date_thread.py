import time
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal


class DateThread(QThread):
    return_time = pyqtSignal(str, str, str)
    def __init__(self, parent=None):
        super(DateThread, self).__init__(parent)
        self.now = ''

    def run(self):
        while True:
            time.sleep(0.5)
            self.now = datetime.now()
            formatted_date = self.now.strftime('%m月%d日')
            formatted_time = self.now.strftime('%H:%M')
            formatted_week = self.now.strftime('%A')
            
            week = formatted_week
            if formatted_week == 'Monday':
                week = '星期一'
            elif formatted_week == 'Tuesday':
                week = '星期二'
            elif formatted_week == 'Wednesday':
                week = '星期三'
            elif formatted_week == 'Thursday':
                week = '星期四'
            elif formatted_week == 'Friday':
                week = '星期五'
            elif formatted_week == 'Saturday':
                week = '星期六'
            elif formatted_week == 'Sunday':
                week = '星期日'
            self.return_time.emit(formatted_date, formatted_time, week)

