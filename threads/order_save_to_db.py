from PyQt5.QtCore import QThread

from db import db_util
from PyQt5.QtCore import QThread, pyqtSignal
from db.db_util import insert_order_info, insert_tee_info

#异步将订单及其明细写入数据库，并在成功或失败时通过信号通知上层界面。
class OrderSaveToDB(QThread):
    done = pyqtSignal(object)   # 可选：保存完成后把 order_bean 回传
    failed = pyqtSignal(str)

#把外部传入的订单对象保存为成员变量。
    def __init__(self, order_bean, parent=None):
        super().__init__(parent)
        self.order_bean = order_bean

#保存订单主表（order_info），获取并回填订单主键 ob.id。
    def run(self):
        ob = self.order_bean
        try:
            # 1) 先写 order_info，回填 _id
            order_pk = insert_order_info(
                order_id=ob.order_id,
                order_time=ob.order_time,
                remarks=getattr(ob, "remarks", "") or "",
                today_id=ob.today_id,
                state='3' if getattr(ob, "state", None) in (None, "", "3") else str(ob.state)
            )
            ob.id = order_pk  # ← 关键：回填订单主键，便于后续使用

            # 2) 写 tee_info，逐条回填 _id
            #逐条保存订单明细（tee_info），并回填每个明细的主键 tb.id，便于后续业务
            for tb in getattr(ob, "tee_list", []):
                tee_pk = insert_tee_info(
                    order_id=ob.order_id,
                    product_id=tb.product_id,
                    product_name=tb.product_name,
                    product_sugar=tb.product_sugar,
                    product_quantity=tb.product_quantity,
                    product_ice=tb.product_ice,
                    product_simp=tb.product_simp,
                    unit_price=tb.unit_price,
                    num_tee=tb.num_tee,
                    state='3' if not getattr(tb, "state", None) else str(tb.state),
                    recipe=getattr(tb, "recipe", "")
                )
                tb.id = tee_pk           # ← 关键：卡片“开始制作”常用这个 id

            self.done.emit(ob)           # 通知上层刷新
        except Exception as e:
            self.failed.emit(str(e))