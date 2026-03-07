# material_assign_dialog.py
# -*- coding: utf-8 -*-
import os
import sys

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRegExp
from PyQt5.QtGui import QFontDatabase, QFont, QGuiApplication, QRegExpValidator
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QHBoxLayout,
    QPushButton, QSizePolicy, QGridLayout, QLineEdit
)

# 你提供的大号数字键盘 UI
from ui_1080_py.Ui_conduit_card_keyboard_ui import Ui_Form as Ui_Keypad


def _res_path(p: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.join(os.path.abspath("."), p)


# =========================
# 大号数字键盘（Popup）：实时写回 target 编辑框；确定时发 committed(int)
# =========================
class ConduitCardKeypad(QWidget):
    committed = pyqtSignal(int)
    closed = pyqtSignal()  # 新增

    def __init__(self, target_line_edit: QLineEdit, max_val: int = 99, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.target = target_line_edit
        self.max_val = int(max_val)

        # 载入 UI
        self.ui = Ui_Keypad()
        self.ui.setupUi(self)

        # ==== 字体：优先使用阿里巴巴普惠体，失败则回退 ====
        # 路径按你的项目结构（与 GreenMessageBox 一致）
        # fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf
        try:
            font_id = QFontDatabase.addApplicationFont(
                "fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf"
            )
            fams = QFontDatabase.applicationFontFamilies(font_id)
            if fams:
                base_family = fams[0]
            else:
                # 若未找到则继承父字体；再兜底到微软雅黑
                base_family = (self.parent().font().family() if self.parent() else "Microsoft YaHei")
        except Exception:
            base_family = (self.parent().font().family() if self.parent() else "Microsoft YaHei")

        # 继承主题字号风格：按钮更大更醒目，标签略小
        try:
            btn_font = QFont(base_family, 32, QFont.Bold)  # 按钮：大号加粗
            lab_font = QFont(base_family, 22)              # 标签：常规
            for w in self.findChildren(QPushButton):
                w.setFont(btn_font)
            for w in self.findChildren(QLabel):
                w.setFont(lab_font)
        except Exception:
            pass
        # ==== 字体设置结束 ====

        # 初始缓冲
        self._buf = self._only_digits(self.target.text())

        # 绑定 0~9
        for n in range(10):
            btn = getattr(self.ui, f"btn_{n}", None)
            if btn:
                btn.clicked.connect(lambda _=None, t=str(n): self._press(t))

        # 清空 / 确定（如果 UI 有这两个对象名）
        if hasattr(self.ui, "btn_clear"):
            self.ui.btn_clear.clicked.connect(self._clear)
        if hasattr(self.ui, "btn_ok"):
            self.ui.btn_ok.clicked.connect(self._commit)

    def _only_digits(self, s: str) -> str:
        return "".join(ch for ch in str(s) if ch.isdigit())

    def closeEvent(self, e):
        try:
            self.closed.emit()
        finally:
            super().closeEvent(e)

    def _sync(self):
        txt = self._buf or ""
        self.target.setText(txt)
        self.target.setCursorPosition(len(self.target.text()))

    def _press(self, t: str):
        self._buf = (self._buf + t).lstrip("0") if (self._buf or t) else ""
        self._sync()

    def _clear(self):
        self._buf = ""
        self._sync()

    def _commit(self):
        try:
            val = int(self._buf) if self._buf != "" else 0
        except ValueError:
            val = 0
        if val < 0:
            val = 0
        if val > self.max_val:
            val = self.max_val
        self._buf = str(val) if val != 0 else ""
        self._sync()
        self.committed.emit(val)
        self.close()

    # 点击弹层外部关闭（Popup 行为）
    def mousePressEvent(self, e):
        if not self.rect().contains(e.pos()):
            self.close()
        super().mousePressEvent(e)


# =========================
# 通道选择对话框（布局/样式不动；仅在“通道号”处接入键盘）
# =========================
class ChannelSelectDialog(QWidget):
    accepted = pyqtSignal(int)
    rejected = pyqtSignal()

    def __init__(self, material_name: str, code: str, max_channel: int = 23, details: dict = None, parent=None):
        super().__init__(parent)
        self.material_name = material_name or ""
        self.code = code or ""
        self.max_channel = max(1, int(max_channel))
        self.details = details or {}
        self._selected = None
        self._pad_open = False  # ← 重入保护：避免递归触发

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("root")
        self.resize(860, 420)

        outer = QVBoxLayout(self); outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame(self); card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(card)

        wrap = QVBoxLayout(card)
        wrap.setContentsMargins(32, 28, 32, 28)
        wrap.setSpacing(18)

        # 标题
        title = QLabel(f"检测到材料：<b>{self.material_name}</b>")
        title.setObjectName("title")
        title.setTextFormat(Qt.RichText)
        wrap.addWidget(title)

        # 竖排信息 
        info_layout = QGridLayout()
        info_layout.setColumnStretch(0, 1)
        info_layout.setColumnStretch(1, 3)
        info_layout.setHorizontalSpacing(10)

        labels = [
            ("名    称", self.details.get('material_name', self.material_name)),
            ("生产日期",   self.details.get('prod_date',   '-')),
            ("有效期至",   self.details.get('expiry_date', '-')),
            ("产    地", self.details.get('origin',      '-')),
            ("编    码", self.details.get('sku',         '-')),
        ]
        for row, (k, v) in enumerate(labels):
            key_label = QLabel(f"{k}：")
            key_label.setStyleSheet("font-size:30px; font-weight:bold; color:#FF0000;")  # 左列 大小+加粗+浅绿
            val_label = QLabel(str(v))
            val_label.setStyleSheet("font-size:30px; font-weight:bold; color:#FF0000;")  # 右列 大小+加粗+浅绿

            info_layout.addWidget(key_label, row, 0, Qt.AlignRight | Qt.AlignVCenter)   # 左列靠右
            info_layout.addWidget(val_label, row, 1, Qt.AlignCenter)                    # 右列居中
        wrap.addLayout(info_layout)

        # 选择通道
        row = QHBoxLayout(); row.setSpacing(14)
        tip = QLabel("请选择要放入的通道号："); tip.setObjectName("label")
        row.addWidget(tip, 0)

        # 用 QLineEdit 承载（对象名复用 combo，以保持原外观）
        self.edit = QLineEdit(self)
        self.edit.setObjectName("combo")
        self.edit.setFixedHeight(58)
        self.edit.setMaximumWidth(240)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setText("")  # 默认为空
        self.edit.setPlaceholderText("请输入通道号")
        self.edit.setValidator(QRegExpValidator(QRegExp(r"[0-9]{1,3}"), self.edit))

        row.addWidget(self.edit, 0)
        row.addStretch(1)
        wrap.addLayout(row)

        # 底部按钮
        btns = QHBoxLayout(); btns.addStretch(1)
        self.btn_cancel = QPushButton("取消"); self.btn_cancel.setObjectName("btnGhost"); self.btn_cancel.setFixedSize(200, 66)
        self.btn_ok     = QPushButton("确定"); self.btn_ok.setObjectName("btnPrimary"); self.btn_ok.setFixedSize(200, 66)
        btns.addWidget(self.btn_cancel); btns.addWidget(self.btn_ok)
        wrap.addStretch(1); wrap.addLayout(btns)

        # 字体与样式
        self._init_font()
        self._apply_qss()

        # 事件
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_ok.clicked.connect(self._on_ok)

        # —— 只在鼠标点击时弹出键盘，避免 focusIn 递归 —— #
        _orig_mouse = self.edit.mousePressEvent
        def _mousePress(e):
            self._show_keypad()
            _orig_mouse(e)
        self.edit.mousePressEvent = _mousePress

        self.edit.setFocus()

    # 弹出数字键盘（含防重入与位置计算）
    def _show_keypad(self):
        if self._pad_open:
            return
        self._pad_open = True
        pad = ConduitCardKeypad(self.edit, max_val=self.max_channel, parent=self)

        pad.setAttribute(Qt.WA_DeleteOnClose, True)   # 关键：关闭即销毁
        pad.closed.connect(lambda: setattr(self, "_pad_open", False))  # 关键：复位

        # 位置计算（你的原逻辑保留）...
        pad.adjustSize()
        pad_sz = pad.sizeHint()
        below = self.edit.mapToGlobal(QPoint(0, self.edit.height()))
        screen = QGuiApplication.screenAt(below) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        x = below.x(); y = below.y()
        if y + pad_sz.height() > avail.bottom() - 8:
            above = self.edit.mapToGlobal(QPoint(0, -pad_sz.height()))
            x = above.x(); y = above.y() - 8
        if x + pad_sz.width() > avail.right() - 8:
            x = avail.right() - pad_sz.width() - 8
        if x < avail.left() + 8:
            x = avail.left() + 8

        pad.move(x, y)
        pad.committed.connect(lambda v: self.edit.setText(str(max(1, min(v, self.max_channel))) if v > 0 else ""))
        pad.show()


    # 其余与之前一致
    def _init_font(self):
        try:
            font_path = _res_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                family = QFontDatabase.applicationFontFamilies(font_id)[0]
                f24 = QFont(family, 24, QFont.Bold)
                f20 = QFont(family, 20, QFont.Normal)
                f32 = QFont(family, 32, QFont.Bold)

                w = self.findChild(QLabel, "title");  w and w.setFont(f24)
                w = self.findChild(QLabel, "label");  w and w.setFont(f24)
                for w in self.findChildren(QLabel, "subinfo"):
                    w.setFont(f20)

                self.edit.setFont(f24)
                self.btn_ok.setFont(f32)
                self.btn_cancel.setFont(f32)
        except Exception as e:
            print(f"[ChannelSelectDialog] font load fail: {e}")

    def _apply_qss(self):
        self.setStyleSheet("""
#card {
    /* 用登录框同款 PNG 做柔和底部阴影，替换原绿色渐变 */
    border-image: url(:/icon/order_dialog_background_2.png);
    border-radius: 26px;  /* 保留你的圆角设定 */
}
#title   { color: #2C7A4B; }
#subinfo { color: #2C7A4B; }
#label   { color: #2C7A4B; }

/* 复用 combo 外观：让编辑框与原下拉一致 */
#combo {
    background: #FFFFFF;
    border: 2px solid #BCE3C8;
    border-radius: 14px;
    padding: 0 12px;
    color: #2C7A4B;
}

#btnPrimary {
    background: #1FA463; color: #FFFFFF; border: none; border-radius: 28px;
}
#btnPrimary:hover   { background: #159355; }
#btnPrimary:pressed { background: #0F7E49; }

#btnGhost {
    background: #EEF5F0; color: #2C7A4B; border: none; border-radius: 28px;
}
#btnGhost:hover   { filter: brightness(0.98); }
#btnGhost:pressed { filter: brightness(0.95); }
""")


    def _on_cancel(self):
        self._selected = None
        self.close()
        QTimer.singleShot(0, lambda: self.rejected.emit())

    def _on_ok(self):
        text = (self.edit.text() if hasattr(self, "edit") else "").strip()
        try:
            ch = int(text) if text != "" else 1
        except Exception:
            ch = 1
        if ch < 1: ch = 1
        if ch > self.max_channel: ch = self.max_channel
        self._selected = ch
        self.close()
        QTimer.singleShot(0, lambda: self.accepted.emit(ch))

    @property
    def selected_channel(self) -> int:
        return self._selected

    def showEvent(self, e):
        super().showEvent(e)
        self._center_to_parent_or_screen()

    def _center_to_parent_or_screen(self):
        if self.parent() and self.parent().isVisible():
            p = self.parent().frameGeometry().center()
            self.move(int(p.x() - self.width()/2), int(p.y() - self.height()/2))
        else:
            screen = self.windowHandle().screen() if self.windowHandle() else QGuiApplication.primaryScreen()
            g = screen.availableGeometry(); c = g.center()
            self.move(int(c.x() - self.width()/2), int(c.y() - self.height()/2))


# 兼容别名
MaterialAssignDialog = ChannelSelectDialog
