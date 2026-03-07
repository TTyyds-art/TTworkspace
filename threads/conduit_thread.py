from PyQt5.QtCore import QThread, pyqtSignal
from bean.new_conduit_bean import NewConduitBean
from db import db_util

# —— 管理页：conduit_info ——
class ConduitThread(QThread):
    result_conduit_bean = pyqtSignal(NewConduitBean)
    result_conduits_bean_list = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        rows = db_util.query_all_conduit_info()
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

            # 【新增】冰 / 碎冰通道永远视为未屏蔽
            if str(b.conduit) in ("1", "2"):
                b.shield = "1"   # 强制未屏蔽
                
            b.begin_time = d.get('begin_time', '')
            b.effective_time = d.get('effective_time', '')
            b.red_warning_value = d.get('red_warning_value', '')
            b.yellow_warning_value = d.get('yellow_warning_value', '')
            beans.append(b)
            self.result_conduit_bean.emit(b)
        self.result_conduits_bean_list.emit(beans)

# —— 泡茶页：maketee_conduit_info ——
class MaketeeConduitThread(QThread):
    result_maketee_conduit_bean = pyqtSignal(NewConduitBean)
    result_maketee_conduits_bean_list = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        print("[mk-thread] run() begin")
        rows = db_util.query_all_maketee_conduit_info()
        print(f"[mk-thread] rows fetched = {len(rows)}")
        beans = []
        for idx, d in enumerate(rows):
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

            # ★ 新增：把数据库 expect_time 带进来
            b.expect_time = d.get('expect_time', '')

            beans.append(b)
            print(f"[mk-thread] emit single bean #{idx+1}: conduit={b.conduit}, name={b.name}")
            self.result_maketee_conduit_bean.emit(b)
        print(f"[mk-thread] emit list ({len(beans)})")
        self.result_maketee_conduits_bean_list.emit(beans)
        print("[mk-thread] run() end")
__all__ = ["ConduitThread", "MaketeeConduitThread"]  # 放在类定义之后
