from PyQt5.QtWidgets import QWidget, QLabel,QFrame
from PyQt5.QtCore import Qt
from ui_1080_py.Ui_camera_frame_ui import Ui_Form


# class CameraFrameMata(QWidget, Ui_Form):
#     def __init__(self,parent=None):
#         super().__init__(parent)
#         self.setupUi(self)
#         # url(:/icon/icon_scan.png)
#         self.icon_label = QLabel(self)
#         self.icon_label.setStyleSheet('border-image:url(:/icon/icon_scan_2.png)')  #摄像头图片
#         self.icon_label.setFixedSize(217, 200)
#         self.icon_label.move(int(1046 / 2 - 108), int(400 / 2 - 100))
 
        

#     def is_show_label(self, is_show):
#         if is_show:
#             # print("展示")
#             self.icon_label.setHidden(False)
#         else:
#             # print("隐藏")
#             self.icon_label.setHidden(True)


class CameraFrameMata(QWidget, Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # 摄像头图标（你原来的逻辑保留）
        self.icon_label = QLabel(self)
        self.icon_label.setStyleSheet('border-image:url(:/icon/icon_scan_2.png)')
        self.icon_label.setFixedSize(217, 200)
        self.icon_label.move(int(1046 / 2 - 108), int(400 / 2 - 100))

        # === 角标四个 QLabel（来自 Ui_camera_frame_ui：label/label_2/label_3/label_4）===
        self._corner_widgets = [self.label, self.label_2, self.label_3, self.label_4]
        self._corner_qss_idle = [w.styleSheet() for w in self._corner_widgets]

        self._idle_rgb = "rgb(242, 254, 244)"
        self._scan_rgb = "rgb(44, 159, 97)"   # 主绿
        self._corner_qss_scan = [qss.replace(self._idle_rgb, self._scan_rgb) for qss in self._corner_qss_idle]

        # =========================
        # ★ 新增：扫码中静态 HintLayer
        # =========================
        self._hint_layer = QWidget(self)
        self._hint_layer.setAttribute(Qt.WA_StyledBackground, True)
        self._hint_layer.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 不抢鼠标事件
        self._hint_layer.setStyleSheet("background: transparent;")
        self._hint_layer.hide()

        # 扫描线（静态）
        self._scan_line = QFrame(self._hint_layer)
        self._scan_line.setFixedHeight(4)
        self._scan_line.setStyleSheet(
            "background: rgba(44,159,97,0.55);"   # 半透明亮线（静态）
            "border-radius: 2px;"
        )

        # Hint 文案（静态）
        self._hint_text = QLabel("扫码中：请将二维码对准取景框", self._hint_layer)
        self._hint_text.setAlignment(Qt.AlignCenter)
        self._hint_text.setStyleSheet(
            "color: rgba(44,159,97,0.95);"
            "background: rgba(255,255,255,0.85);"
            "border: 1px solid rgba(44,159,97,0.25);"
            "padding: 10px 16px;"
            "border-radius: 16px;"
            "font-size: 22px;"
        )

        # 默认状态：浅绿 + 不显示 hint
        self.set_scanning(False)

    def resizeEvent(self, e):
        """保证 HintLayer 永远覆盖整个取景框，并把线/文案放到合适位置"""
        super().resizeEvent(e)
        self._hint_layer.setGeometry(0, 0, self.width(), self.height())

        # 扫描线：横向贯穿（留边距）
        margin_x = 90
        line_w = max(100, self.width() - margin_x * 2)
        self._scan_line.setFixedWidth(line_w)

        # 放在中间略偏上（行业常见）
        y_line = int(self.height() * 0.46)
        self._scan_line.move(int((self.width() - line_w) / 2), y_line)

        # 文案：线下方
        self._hint_text.adjustSize()
        y_text = y_line + 24
        self._hint_text.move(int((self.width() - self._hint_text.width()) / 2), y_text)

    def is_show_label(self, is_show: bool):
        # 你原来的逻辑保留：True=显示摄像头icon；False=隐藏icon
        self.icon_label.setHidden(not is_show)

    def set_scanning(self, scanning: bool):
        """
        scanning=True：角标深绿 + 显示扫描线/文案
        scanning=False：恢复浅绿 + 隐藏扫描线/文案
        """
        qss_list = self._corner_qss_scan if scanning else self._corner_qss_idle
        for w, qss in zip(self._corner_widgets, qss_list):
            w.setStyleSheet(qss)

        self._hint_layer.setVisible(bool(scanning))