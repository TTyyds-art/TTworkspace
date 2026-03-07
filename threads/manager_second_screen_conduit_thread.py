import time

from PyQt5.QtCore import QThread, pyqtSignal

from bean.new_conduit_bean import NewConduitBean
from db import db_util


class ManagerSecondScreenConduit(QThread):
    result_conduit_bean = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        while not self._stop:
            try:
                rows = db_util.query_all_maketee_conduit_info() or []
            except Exception:
                rows = []

            beans = []
            for d in rows:
                b = NewConduitBean()
                b.id = str(d.get('_id', ''))
                b.conduit = d.get('conduit', '')
                b.margin = d.get('margin', '')
                b.max_capacity = d.get('max_capacity', '')
                b.conduit_type = d.get('conduit_type', '')
                b.name = d.get('name', '')
                b.shield = d.get('shield', '')
                b.begin_time = d.get('begin_time', '')
                b.effective_time = d.get('effective_time', '')
                b.red_warning_value = d.get('red_warning_value', '')
                b.yellow_warning_value = d.get('yellow_warning_value', '')
                beans.append(b)

            print(f"[maketee] emit {len(beans)} beans")
            self.result_conduit_bean.emit(beans)
            time.sleep(1)
