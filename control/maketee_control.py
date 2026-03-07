# control/maketee_control.py
from PyQt5.QtCore import QObject, QTimer, pyqtSlot
from PyQt5.QtWidgets import QDialog
from typing import Optional, Dict

from db import db_util

# 这些类在你的工程里已经存在；若模块路径不同，请自行调整 import
# from main_1080_mata import GreenMessageBox, GreenConfirmBox  # 若没有此模块，可用你现有的封装


# 绿主题弹窗（与现有UI风格一致）
from PyQt5.QtCore import Qt, QTimer,QSize
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QSizePolicy,QGraphicsDropShadowEffect,QLayout,QWidget
from PyQt5.QtGui import QFontDatabase, QFont, QColor

class GreenMessageBox(QDialog):
    """
    与登录框一致的外观：使用 border-image 的渐隐阴影 PNG，
    四角完全透明，底部阴影自然，不会出现突出的灰角。
    """
    def __init__(self, title: str, text_html: str, parent=None, ok_text="知道了"):
        super().__init__(parent)
        # 无边框 + 透明背景（让四角透明生效）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setObjectName("GreenMsgBox")

        # 统一字体（与项目保持一致；若未安装会回退微软雅黑）
        font_id = QFontDatabase.addApplicationFont(
            "fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf"
        )
        fams = QFontDatabase.applicationFontFamilies(font_id)
        base_family = fams[0] if fams else "Microsoft YaHei"

        # 最外层：留出少量透明边距，避免阴影被裁切
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 16)
        root.setSpacing(0)
        root.setSizeConstraint(QLayout.SetFixedSize)  # 关键：让窗口随内容自适应

        # 中心“卡片”容器
        panel = QWidget(self)
        panel.setObjectName("msgPanel")
        panel.setMinimumSize(QSize(560, 300))  # 最小宽高
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        root.addWidget(panel)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(34, 28, 34, 26)
        panel_layout.setSpacing(14)

        # 标题
        lab_title = QLabel(title, panel)
        ft_title = QFont(base_family, 28, QFont.Black)
        lab_title.setFont(ft_title)
        lab_title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        lab_title.setObjectName("title")
        panel_layout.addWidget(lab_title)

        # 正文
        lab_text = QLabel(panel)
        lab_text.setTextFormat(Qt.RichText)
        lab_text.setWordWrap(True)
        lab_text.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        ft_text = QFont(base_family, 20, QFont.DemiBold)
        lab_text.setFont(ft_text)
        lab_text.setObjectName("content")
        lab_text.setText(text_html)
        panel_layout.addWidget(lab_text, 1)

        # 按钮区域
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_ok = QPushButton(ok_text, panel)
        btn_ok.setObjectName("okBtn")
        btn_ok.setFixedSize(210, 66)
        ft_btn = QFont(base_family, 20, QFont.Bold)
        btn_ok.setFont(ft_btn)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)

        btn_row.addStretch(1)
        panel_layout.addLayout(btn_row)

        # 样式表
        self.setStyleSheet("""
        QWidget#msgPanel {
            border-image: url(:/icon/order_dialog_background_2.png);
        }
        QLabel#title   { color: #2C7A4B; }
        QLabel#content { color: #2C7A4B; }
        QPushButton#okBtn {
            background: #1FA463;
            color: #FFFFFF;
            border: none;
            border-radius: 33px;
        }
        QPushButton#okBtn:hover  { background: #159355; }
        QPushButton#okBtn:pressed{ background: #0F7E49; }
        """)

        # 根据内容自动调整窗口大小
        self.adjustSize()

    # 便捷静态方法
    @staticmethod
    def warning(parent, title, text_html, ok_text="知道了"):
        dlg = GreenMessageBox(title, text_html, parent, ok_text)
        # 居中
        if parent:
            cg = parent.frameGeometry()
            cc = parent.mapToGlobal(parent.rect().center())
            dlg.move(cc.x() - dlg.width()//2, cc.y() - dlg.height()//2)
        else:
            scr = dlg.screen().availableGeometry().center()
            dlg.move(scr.x() - dlg.width()//2, scr.y() - dlg.height()//2)
        return dlg.exec_()
    @staticmethod
    def information(parent, title, text_html, ok_text="我已加入"):
        dlg = GreenMessageBox(title, text_html, parent, ok_text)
        # 居中显示
        if parent:
            cg = parent.frameGeometry()
            cc = parent.mapToGlobal(parent.rect().center())
            dlg.move(cc.x() - dlg.width()//2, cc.y() - dlg.height()//2)
        else:
            scr = dlg.screen().availableGeometry().center()
            dlg.move(scr.x() - dlg.width()//2, scr.y() - dlg.height()//2)
        return dlg.exec_()



class GreenConfirmBox(QDialog):
    """绿主题双按钮确认框：保持与 GreenMessageBox 一致的外观与字体。"""
    def __init__(self, title: str, text_html: str, parent=None, yes_text="是", no_text="否"):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setObjectName("GreenConfirmBox")

        # 与项目一致的阿里巴巴普惠体（路径与 GreenMessageBox 相同）
        fid = QFontDatabase.addApplicationFont(
            "fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf"
        )
        fams = QFontDatabase.applicationFontFamilies(fid)
        base_family = fams[0] if fams else "Microsoft YaHei"

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 16)
        root.setSpacing(0)
        root.setSizeConstraint(QLayout.SetFixedSize)

        panel = QWidget(self)
        panel.setObjectName("msgPanel")
        panel.setMinimumSize(QSize(560, 300))
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        root.addWidget(panel)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(34, 28, 34, 26)
        lay.setSpacing(14)

        lab_title = QLabel(title, panel)
        lab_title.setFont(QFont(base_family, 28, QFont.Black))
        lab_title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        lab_title.setObjectName("title")
        lay.addWidget(lab_title)

        lab_text = QLabel(panel)
        lab_text.setTextFormat(Qt.RichText)
        lab_text.setWordWrap(True)
        lab_text.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lab_text.setFont(QFont(base_family, 20, QFont.DemiBold))
        lab_text.setObjectName("content")
        lab_text.setText(text_html)
        lay.addWidget(lab_text, 1)

        row = QHBoxLayout(); row.addStretch(1)
        btn_no  = QPushButton(no_text,  panel);  btn_no.setObjectName("noBtn")
        btn_yes = QPushButton(yes_text, panel); btn_yes.setObjectName("yesBtn")
        btn_no.setFixedSize(210, 66);  btn_yes.setFixedSize(210, 66)
        btn_no.setFont(QFont(base_family, 20, QFont.Bold))
        btn_yes.setFont(QFont(base_family, 20, QFont.Bold))
        btn_no.clicked.connect(self.reject)
        btn_yes.clicked.connect(self.accept)
        row.addWidget(btn_no); row.addSpacing(14); row.addWidget(btn_yes); row.addStretch(1)
        lay.addLayout(row)

        # 与 GreenMessageBox 一致的绿色皮肤（同一张背景图）
        self.setStyleSheet("""
        QWidget#msgPanel { border-image: url(:/icon/order_dialog_background_2.png); }
        QLabel#title   { color: #2C7A4B; }
        QLabel#content { color: #2C7A4B; }
        QPushButton#yesBtn {
            background: #1FA463; color: #FFFFFF; border: none; border-radius: 33px;
        }
        QPushButton#yesBtn:hover  { background: #159355; }
        QPushButton#yesBtn:pressed{ background: #0F7E49; }
        QPushButton#noBtn  {
            background: rgba(31,164,99,0.12); color: #1FA463; border: 2px solid #1FA463; border-radius: 33px;
        }
        QPushButton#noBtn:hover  { background: rgba(31,164,99,0.18); }
        QPushButton#noBtn:pressed{ background: rgba(31,164,99,0.24); }
        """)
        self.adjustSize()

    @staticmethod
    def ask(parent, title: str, text_html: str, yes_text="是", no_text="否") -> bool:
        dlg = GreenConfirmBox(title, text_html, parent, yes_text, no_text)
        # 居中（参考 GreenMessageBox 的做法）
        if parent:
            cg = parent.frameGeometry()
            cc = parent.mapToGlobal(parent.rect().center())
            dlg.move(cc.x() - dlg.width()//2, cc.y() - dlg.height()//2)
        return dlg.exec_() == QDialog.Accepted


class MaketeeController(QObject):
    """
    负责泡茶全流程：
      1) 读取 L 数 + 当前选中茶卡片；下发 *Lxx → (500ms) → *Cxx
      2) 监听温度，更新进度与“加热中.xx%”
      3) temp_finished → *stop → 弹出“请加入xx克” → 启动预计时长倒计时
      4) 倒计时结束 → 弹出“是否加冰xx克” → 自动则下发 AXXBXX
    """
    def __init__(self, ui, serial_thread):
        super().__init__(ui)
        self.ui = ui
        self.serial = serial_thread

        # 运行时状态
        self._cur_temp: Optional[float] = None
        self._heat_target: Optional[int] = None
        self._heat_start: Optional[float] = None
        self._maketee_row: Optional[Dict] = None
        self._heat_progress_peak: int = 0
        self._brew_liters: float = 0.0
        self._brew_seconds_left: int = 0

        # 浸泡倒计时
        self._brew_timer = QTimer(self)
        self._brew_timer.timeout.connect(self._on_brew_tick)

        self._heating_done = False
        self._finish_eps = 0.2
        self._boil_only_mode = False

        # on_brew_button_clicked() 里，在复位 UI 之前清零
        self._heating_done = False
        # —— UI 控件缓存（如果不存在会是 None，不影响）——
        self._btn_brew   = getattr(self.ui, "btn_maketee_out",   None)   # 泡茶
        self._btn_cancel = getattr(self.ui, "btn_maketee_out_2", None)   # 取消

        # 遮罩控件
        self._mask = None
        
        self._btn_fill = getattr(self.ui, "btn_maketee_all", None)   # 进水
        self._btn_boil = getattr(self.ui, "btn_maketee_one", None)   # 烧水

        # —— 自动加冰：分批状态 —— 
        self._ice_total = 0             # 本次总克数
        self._ice_remaining = 0         # 剩余克数
        self._ice_chunk_max = 900       # 单次最大 900g
        self._ice_timer = QTimer(self)  # 20s 间隔定时器
        self._ice_timer.setSingleShot(True)
        self._ice_timer.timeout.connect(self._send_next_ice_chunk)

        self._ice_stop_delay = QTimer(self)   # 500ms：*stop 后再发 A/B
        self._ice_stop_delay.setSingleShot(True)
        self._ice_stop_delay.timeout.connect(self._send_chunk_after_stop)

        if self._btn_fill:
            try: self._btn_fill.clicked.disconnect(self.on_fill_button_clicked)
            except Exception: pass
            self._btn_fill.clicked.connect(self.on_fill_button_clicked)

        if self._btn_boil:
            try: self._btn_boil.clicked.disconnect(self.on_heat90_button_clicked)
            except Exception: pass
            self._btn_boil.clicked.connect(self.on_heat90_button_clicked)

        # 绑定取消按钮（防重复绑定）
        if self._btn_cancel:
            try:
                self._btn_cancel.clicked.disconnect(self.cancel_brew)
            except Exception:
                pass
            self._btn_cancel.clicked.connect(self.cancel_brew)
        # 串口事件：温度刷新 & 加热完成
        # self.serial.temp_changed.connect(self.on_temp_changed)   # 显示到 lcdNumber
        # self.serial.temp_changed.connect(self._on_temp)          # 驱动“加热中.xx%”与进度条
        # self.serial.temp_finished.connect(self._on_temp_finish)  # 进入“加茶/倒计时/加冰”阶段
        if self.serial:
            self._bind_serial_signals()
    def _bind_serial_signals(self):
        self.serial.temp_changed.connect(self.on_temp_changed)
        self.serial.temp_changed.connect(self._on_temp)
        self.serial.temp_finished.connect(self._on_temp_finish)

    def attach_serial(self, serial_thread):
        """如果控制器先创建、串口线程后创建，用这个方法把串口补挂进来"""
        self.serial = serial_thread
        self._bind_serial_signals()

    # ---------- 对外 API ----------
    def set_selected_row(self, row: dict):
        if row is None:
            self._maketee_row = None
            return

        # 1) 统一成 dict
        if not isinstance(row, dict):
            d = {}
            for k in ("name","temp_goal","tea_coefficient","ice_coefficient","expect_time","conduit","conduit_no"):
                if hasattr(row, k):
                    d[k] = getattr(row, k)
            row = d

        # 2) 如果缺关键字段，就按 conduit/name 去 maketee_conduit_inf 里补
        need = any(row.get(k) in (None, "", 0) for k in ("tea_coefficient","ice_coefficient","expect_time","temp_goal"))
        if need:
            key, val = ("conduit", row.get("conduit") or row.get("conduit_no") or None)
            if not val:
                key, val = ("name", row.get("name") or None)
            try:
                if val:
                    conn = db_util.get_conn()   # 你项目里的封装
                    sql = f"SELECT expect_time,temp_goal,ice_coefficient,tea_coefficient FROM maketee_conduit_info WHERE {key}=? LIMIT 1"
                    cur = conn.execute(sql, (val,))
                    r = cur.fetchone()
                    if r:
                        row.setdefault("expect_time",     r["expect_time"])
                        row.setdefault("temp_goal",       r["temp_goal"])
                        row.setdefault("ice_coefficient", r["ice_coefficient"])
                        row.setdefault("tea_coefficient", r["tea_coefficient"])
            except Exception as e:
                print("[maketee] recipe fallback err:", e)

        # 3) 数值标准化（字符串 -> float/int）
        def _f(x, default=None):
            try: return float(str(x).strip())
            except: return default
        row["temp_goal"]       = int(_f(row.get("temp_goal"), 90) or 90)
        row["ice_coefficient"] = _f(row.get("ice_coefficient"), 0.0)
        row["tea_coefficient"] = _f(row.get("tea_coefficient"), 0.0)
        row["expect_time"]     = int(_f(row.get("expect_time"), 0) or 0)

        self._maketee_row = row

    def wire_buttons(self, *buttons):
        """把‘泡茶’按钮统一接到本控制器"""
        for b in buttons:
            try:
                b.clicked.disconnect()
            except Exception:
                pass
            b.clicked.connect(self.on_brew_button_clicked)

    @pyqtSlot()
    def on_brew_button_clicked(self):
        """点击‘泡茶’按钮"""
        if not self.serial:
            GreenMessageBox.warning(self.ui, "设备未就绪", "串口线程尚未创建或未挂载到控制器。")
            return
        # 1) 读取 L 数
        try:
            self._brew_liters = float((self.ui.lineEdit_2.text() or "0").strip())
        except Exception:
            self._brew_liters = 0.0
        if self._brew_liters <= 0:
            GreenMessageBox.information(self.ui, "提示", "请输入泡茶水量（单位 L）")
            return

        # 2) 读取当前选中茶卡片（若外部未 set，则先兜底取第一条）
        if not self._maketee_row:
            GreenMessageBox.warning(self.ui, "提示", "请先选择一个配方卡片")
            return

        try:
            self._brew_timer.stop()
        except Exception:
            pass
        self._brew_seconds_left = 0
        self._heating_done = False                # ★ 关键：允许再次跟随温度、再次到温
        self._boil_only_mode = False

        # 3) UI 复位 + 计算目标温度
        self._heat_target = int(self._maketee_row.get("temp_goal") or 90)
        self._heat_start = self._cur_temp if self._cur_temp is not None else 0.0
        self._heat_progress_peak = 0     # ★ 新增
        try:
            self.ui.progressBar.setValue(0)
        except Exception:
            pass
        self._set_status("加热进度：0%")

        # 4) *LXX → 500ms → *CXX
        self.serial.send_data(f"*L{int(round(self._brew_liters)):02d}")
        QTimer.singleShot(500, lambda:
            self.serial.send_data(f"*C{int(self._heat_target):02d}")
        )

        self._lock_ui()



    # ---------- 温度刷新 ----------
    @pyqtSlot(float)
    def on_temp_changed(self, t: float):
        """把 'temp:xx.xx' 实时显示到 lcdNumber"""
        self._cur_temp = t
        try:
            self.ui.lcdNumber.display(f"{t:.2f}")
        except Exception:
            self.ui.lcdNumber.display(str(t))

    def _on_temp(self, _t: float):
        # 浸泡阶段或已完成加热，忽略
        if self._brew_timer.isActive() or self._heating_done:
            return
        if self._heat_target is None:
            return

        cur = float(self._cur_temp or 0.0)
        tgt = float(self._heat_target or 1.0)
        start = self._heat_start if (self._heat_start is not None) else cur

        # 若起点已高于目标（极端场景），直接100%
        if tgt - start <= 1e-3:
            pct = 100
        else:
            raw = (cur - start) / (tgt - start) * 100.0
            clipped = max(0.0, min(100.0, raw))
            # ★ 单调不降：与峰值取 max
            pct = max(self._heat_progress_peak, int(clipped))

        # 记录峰值
        self._heat_progress_peak = pct

        try:
            self.ui.progressBar.setValue(pct)
        except Exception:
            pass
        self._set_status(f"加热进度：{pct}%")
        print(f"[heat][tick] cur={cur:.2f} start={start:.2f} tgt={tgt:.2f} raw={(cur-start)/(tgt-start)*100 if (tgt-start)>1e-3 else float('inf'):.1f}% -> pct={pct}% peak={self._heat_progress_peak}%")

        # 达标判定
        if (not self._heating_done) and cur >= tgt - getattr(self, "_finish_eps", 0.2):
            if self._boil_only_mode:
                self._heating_done = True
                self._heat_target = None
                self._heat_progress_peak = 100          # ★
                try:
                    self.ui.progressBar.setValue(100)   # ★ 强制100%
                except Exception:
                    pass
                # try:
                #     # self.serial.send_data("*stop")
                # except Exception:
                #     pass
                self._set_status(f"{int(tgt)}℃保温中......")
                self._boil_only_mode = False
                return
            else:
                QTimer.singleShot(0, self._on_temp_finish)



    # ---------- 加热完成 → 加茶 / 倒计时 ----------
    def _on_temp_finish(self):
        if self._heating_done:
            return
        self._heating_done = True
        self._heat_target = None

        # ★ 到温立即100%，并封顶峰值
        self._heat_progress_peak = 100
        try:
            self.ui.progressBar.setValue(100)
        except Exception:
            pass

        # ★ 若当前没有任何配方（例如某些情况下误触发），当成“单纯烧水完成”，只停机 + 解锁
        if not self._maketee_row:
            print("[maketee] _on_temp_finish: _maketee_row is None，视为只烧水完成，跳过加茶/浸泡/加冰流程")
            # try:
            #     self.serial.send_data("*stop")
            # except Exception:
            #     pass
            self._set_status("加热完成")
            self._unlock_ui()
            return

        # 1) 先让底层停热
        # self.serial.send_data("*stop")

        # 2) 如果是“水”，直接结束：不弹加茶，不进入浸泡/加冰
        name = str(self._maketee_row.get("name") or "").strip()
        if name == "水":
            self._brew_seconds_left = 0                 # 不进入倒计时
            self._set_status("到温，准备加冰…")
            self._after_brew_finish_show_ice_dialog()    # 直接走加冰
            
            return

        # 3) 其它茶类：计算加茶量并提示（原有流程保留）
        tea_coeff = float(self._maketee_row.get("tea_coefficient") or 0)
        tea_g = int(round(self._brew_liters * tea_coeff))
        name = self._maketee_row.get("name") or "茶叶"

        GreenMessageBox.information(
            self.ui, "加茶提示",
            f"请加入 {name} {tea_g} 克",
            ok_text="我已加入"
        )
        self.serial.send_data("*stop")
        # 4) 启动“预计时长”倒计时（分钟 → 秒）（原有逻辑保留）
        exp_min = int(self._maketee_row.get("expect_time") or 0)
        self._brew_seconds_left = max(0, exp_min * 60)
        if self._brew_seconds_left <= 0:
            self._after_brew_finish_show_ice_dialog()
            return

        self._on_brew_tick()
        self._brew_timer.start(1000)


    def _on_brew_tick(self):
        mm = self._brew_seconds_left // 60
        ss = self._brew_seconds_left % 60
        self._set_status(f"浸泡进度：{mm:02d}:{ss:02d}")

        try:
            total = max(1, int(self._maketee_row.get("expect_time") or 0) * 60)
            pct = 100 - int(self._brew_seconds_left / total * 100)
            self.ui.progressBar.setValue(max(0, min(100, pct)))
        except Exception:
            pass

        self._brew_seconds_left -= 1
        if self._brew_seconds_left < 0:
            self._brew_timer.stop()
            self._after_brew_finish_show_ice_dialog()

    # ---------- 倒计时结束 → 加冰 ----------
    def _after_brew_finish_show_ice_dialog(self):
        # 1) 计算冰量（系数单位：g/L，不要再 /1000）
        ice_coeff = float(self._maketee_row.get("ice_coefficient") or 0.0)  # g/L
        ice_g_total = int(round(self._brew_liters * ice_coeff/1000))             # 总克数
        #test
        print("[ice] liters, coeff, total=", self._brew_liters, ice_coeff, ice_g_total)

        # 2) 询问：自动 or 手动
        self.serial.send_data("*stop")
        dlg = GreenConfirmBox("加冰", f"请加入冰 {ice_g_total} 克？", self.ui,
                            yes_text="自动添加", no_text="手动添加")
        auto = (dlg.exec_() == QDialog.Accepted)

        if not auto:
            # 手动添加：直接完结
            try:
                self.ui.progressBar.setValue(100)
            except Exception:
                pass
            self._set_status("空闲中……")
            self._heat_target = None
            self._unlock_ui()
            return

        # 3) 自动添加：进入批量出冰流程（一次弹窗 + 定时分批发送）
        self._start_auto_ice(ice_g_total)
    
    def _start_auto_ice(self, total_g: int):
        """开始自动加冰：不弹窗，用进度条显示；立即进入首批"""
        self._ice_total = max(0, int(total_g))
        self._ice_remaining = self._ice_total
        # 进度条初始化
        self._update_ice_progress()
        # 发第一批
        self._send_next_ice_chunk()

    def _send_next_ice_chunk(self):
        """准备下一批（min(900, 剩余)），先 *stop，500ms 后再发 A/B"""
        if self._ice_remaining <= 0:
            self._finish_auto_ice()
            return

        self._ice_this_chunk = min(self._ice_chunk_max, self._ice_remaining)  # 暂存本批量
        # 先停机
        try:
            self.serial.send_data("stop")
        except Exception:
            pass
        # 500ms 后真正下发 A/B
        self._ice_stop_delay.start(500)

    def _finish_auto_ice(self):
        """出冰完成：收尾、解锁、状态复位"""
        self._ice_timer.stop()
        self._ice_stop_delay.stop()
        self._ice_this_chunk = 0

        try:
            self.ui.progressBar.setValue(100)
        except Exception:
            pass
        self._set_status("空闲中……")
        self._heat_target = None
        self._unlock_ui()

    def _show_ice_progress_dialog(self):
        """只创建一次“正在出冰中”对话框"""
        if self._ice_dialog:
            return
        # 复用 GreenMessageBox 的皮肤，标题+正文可更新
        self._ice_dialog = GreenMessageBox("加冰", "", self.ui, ok_text="隐藏")
        # 改成非阻塞展示；不影响后续定时发送
        try:
            # 模拟非阻塞：show() + 禁用关闭动画。你也可以 accept() 在 finish 时再关
            self._ice_dialog.show()
        except Exception:
            pass

    def _update_ice_dialog(self):
        """更新对话框内容"""
        if not self._ice_dialog:
            return
        left = max(0, int(self._ice_remaining))
        txt = f"<b>正在出冰中…</b><br/>剩余：{left} 克"
        # 直接找到内容标签并更新（GreenMessageBox 第2个子控件是正文）
        try:
            lab = self._ice_dialog.findChild(QLabel, "content")
            if lab:
                lab.setText(txt)
                self._ice_dialog.adjustSize()
        except Exception:
            pass

    # ---------- 小工具 ----------
    def _set_status(self, text: str):
        """顶部状态文案（如果你把文字显示在别的控件，改这里即可）"""
        try:
            self.ui.progressBar.setFormat(text)
            self.ui.progressBar.setTextVisible(True)
        except Exception:
            pass

    def cancel_brew(self):
        """点击取消按钮：停止一切、复位状态并解锁 UI"""
        try:
            self._brew_timer.stop()
        except Exception:
            pass
        if self.serial:
            try:
                self.serial.send_data("*stop")
            except Exception:
                pass
        # 复位状态
        self._heating_done = False
        self._heat_target = None
        self._brew_seconds_left = 0
        self._boil_only_mode = False 
        try:
            self.ui.progressBar.setValue(0)
        except Exception:
            pass
        self._set_status("空闲中……")
        self.ui.progressBar.setValue(100)

        self._ice_timer.stop()
        self._ice_stop_delay.stop()
        self._ice_this_chunk = 0
        self._ice_total = 0
        self._ice_remaining = 0
        
        # 解锁
        self._unlock_ui()
    def _mask_parent(self):
        """
        找一个能覆盖‘泡茶卡片区域’的父容器：
        优先取第一张卡的父控件；没有卡时退回主窗体。
        """
        cards = getattr(self.ui, "maketee_conduit_card_widgets", [])
        if cards:
            p = cards[0].parentWidget()
            # 如果父容器太小，你也可以向上取 parent().parent()
            return p
        return self.ui

    def _show_mask(self):
        parent = self._mask_parent()
        if parent is None:
            return
        if self._mask is None:
            self._mask = QWidget(parent)
            self._mask.setObjectName("maketeeMask")
            self._mask.setStyleSheet("#maketeeMask{background:rgba(0,0,0,0.20); border-radius:16px;}")
            self._mask.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # 捕获鼠标，阻止点到下方
            lay = QVBoxLayout(self._mask); lay.setContentsMargins(0,0,0,0)
            lab = QLabel("泡茶进行中，卡片已锁定", self._mask)
            lab.setStyleSheet("color:white; font-size:28px;")
            lab.setAlignment(Qt.AlignCenter)
            lay.addStretch(1); lay.addWidget(lab); lay.addStretch(1)

        # 覆盖父容器区域并置顶
        self._mask.setParent(parent)
        self._mask.setGeometry(parent.rect())
        self._mask.show()
        self._mask.raise_()

    def _hide_mask(self):
        if self._mask:
            self._mask.hide()

    def _lock_ui(self):
        """禁用泡茶按钮 + 卡片不可点 + 显示遮罩"""
        if self._btn_brew:
            try:
                self._btn_brew.setEnabled(False)
            except Exception:
                pass
        # 禁用所有卡片
        for w in getattr(self.ui, "maketee_conduit_card_widgets", []):
            try:
                w.setEnabled(False)
            except Exception:
                pass
        self._show_mask()

    def _unlock_ui(self):
        """恢复按钮 + 恢复卡片点击 + 隐藏遮罩"""
        if self._btn_brew:
            try:
                self._btn_brew.setEnabled(True)
            except Exception:
                pass
        for w in getattr(self.ui, "maketee_conduit_card_widgets", []):
            try:
                w.setEnabled(True)
            except Exception:
                pass
        self._hide_mask()
    def _parse_liters(self) -> int:
        """把编辑框 L 数转成 0~99 的两位整数"""
        try:
            v = float((self.ui.lineEdit_2.text() or "0").strip())
        except Exception:
            v = 0.0
        v = max(0, min(99999, int(round(v))))
        return v

    @pyqtSlot()
    def on_fill_button_clicked(self):
        """进水：*LXX（XX 来自编辑框）"""
        if not self.serial:
            GreenMessageBox.warning(self.ui, "设备未就绪", "串口线程未连接")
            return

        # ★ 新增：编辑框校验（空或非数字→提示）
        raw = (self.ui.lineEdit_2.text() or "").strip()
        if not raw:
            GreenMessageBox.warning(self.ui, "提示", "请输入进水量")
            return
        try:
            float(raw)  # 仅用于校验是否为数字
        except Exception:
            GreenMessageBox.warning(self.ui, "提示", "请输入有效数字")
            return

        xx = self._parse_liters()
        if xx <= 0:
            GreenMessageBox.warning(self.ui, "提示", "进水量必须大于 0")
            return

        self.serial.send_data(f"*L{xx:d}")
        self._set_status(f"进水中……{xx}mL")

    @pyqtSlot()
    def on_heat90_button_clicked(self):
        """烧水：*C90，同时驱动进度条以 90℃ 为目标"""
        if not self.serial:
            GreenMessageBox.warning(self.ui, "设备未就绪", "串口线程未连接")
            return

        self.serial.send_data("*C90")

        # ★ 标记为【只烧水模式】，到温后走 _on_temp 的“boil-only 分支”，不会再进 _on_temp_finish
        self._boil_only_mode = True

        # 让顶部进度条按 90℃ 目标工作（复用你已有的加热显示逻辑）
        self._heating_done = False
        self._heat_target  = 90
        self._heat_start   = self._cur_temp if self._cur_temp is not None else 0.0
        self._heat_progress_peak = 0
        try:
            self.ui.progressBar.setValue(0)
        except Exception:
            pass
        self._set_status("加热进度：0%")

    def _send_chunk_after_stop(self):
        """在 *stop 后 500ms 执行：发送 A/B，更新剩余并安排下一轮"""
        chunk = getattr(self, "_ice_this_chunk", 0)
        if chunk <= 0:
            self._finish_auto_ice()
            return

        v3 = f"{chunk:03d}"
        try:
            self.serial.send_data(f"A{v3}B{v3}")
        except Exception:
            pass

        self._ice_remaining -= chunk
        self._update_ice_progress()

        if self._ice_remaining > 0:
            # 下位机一批需要时间：20s 后再来下一批
            self._ice_timer.start(20000)
        else:
            self._finish_auto_ice()
    def _update_ice_progress(self):
        total = max(1, int(self._ice_total))
        done = max(0, int(self._ice_total - self._ice_remaining))
        pct = int(done / total * 100)
        try:
            self.ui.progressBar.setValue(pct)
        except Exception:
            pass
        self._set_status(f"出冰中……{done}/{self._ice_total}g（{pct}%）")
