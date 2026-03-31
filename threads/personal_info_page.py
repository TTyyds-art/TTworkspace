from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


INITIAL_USER = {
    "avatarText": "XL",
    "nickname": "溪流运营员01",
    "username": "xiliu_user_001",
    "phone": "13812345678",
    "registerTime": "2026-03-20 14:22:31",
    "lastLoginTime": "2026-03-20 08:15:10",
    "accountStatus": "正常",
    "currentDevice": "Windows 客户端",
    "currentLoginTime": "2026-03-20 09:30:22",
    "version": "v1.0.0",
    "loginStatus": "在线",
    "password": "Demo@1234",
}

GREEN = "#4FA862"
GREEN_DARK = "#459457"
PAGE_BG = "#ffffff"
CARD_BG = "#edf2f2"
WHITE_CARD = "rgba(255,255,255,0.85)"
TEXT_MAIN = "#0f172a"
TEXT_SUB = "#475569"
TEXT_HINT = "#64748b"
ERROR = "#dc2626"


def mask_phone(phone: str) -> str:
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + "****" + phone[-4:]



def is_phone_valid(phone: str) -> bool:
    return len(phone) == 11 and phone.isdigit() and phone.startswith("1")



def is_username_valid(username: str) -> bool:
    return all(c.isalnum() or c == "_" for c in username)



def get_password_strength(password: str):
    if not password:
        return "未填写", 0
    score = 0
    if len(password) >= 8:
        score += 1
    if any(c.isalpha() for c in password) and any(c.isdigit() for c in password):
        score += 1
    if any(not c.isalnum() for c in password):
        score += 1
    if score <= 1:
        return "弱", 1
    if score == 2:
        return "中", 2
    return "强", 3


class UiStyle:
    _font_family_65_medium = None

    @staticmethod
    def _resolve_font_path(rel_path: str) -> str:
        try:
            import os
            import sys
            base_dir = getattr(sys, "_MEIPASS", os.path.abspath("."))
            return os.path.join(base_dir, rel_path)
        except Exception:
            return rel_path

    @staticmethod
    def ensure_font_family_65_medium() -> str:
        if UiStyle._font_family_65_medium:
            return UiStyle._font_family_65_medium
        font_path = UiStyle._resolve_font_path(
            "fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf"
        )
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                UiStyle._font_family_65_medium = families[0]
        if not UiStyle._font_family_65_medium:
            UiStyle._font_family_65_medium = "Alibaba PuHuiTi"
        return UiStyle._font_family_65_medium

    @staticmethod
    def set_app_font(app: QApplication):
        font = QFont()
        font.setFamily(UiStyle.ensure_font_family_65_medium())
        font.setPointSize(10)
        app.setFont(font)

    @staticmethod
    def primary_button() -> str:
        return f"""
        QPushButton {{
            background: {GREEN};
            color: white;
            border: none;
            border-radius: 16px;
            padding: 12px 20px;
            font-size: 18px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {GREEN_DARK}; }}
        QPushButton:pressed {{ background: {GREEN_DARK}; }}
        QPushButton:disabled {{ background: #a7cdb0; color: #f8fafc; }}
        """

    @staticmethod
    def secondary_button() -> str:
        return f"""
        QPushButton {{
            background: white;
            color: {GREEN};
            border: none;
            border-radius: 16px;
            padding: 12px 20px;
            font-size: 18px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: #f8fafc; }}
        """

    @staticmethod
    def line_edit(error: bool = False, disabled: bool = False) -> str:
        border = "#fb7185" if error else "rgba(15,23,42,0.08)"
        bg = "rgba(255,255,255,0.70)" if disabled else "white"
        return f"""
        QLineEdit {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 16px;
            min-height: 48px;
            padding: 8px 14px;
            font-size: 18px;
            color: {TEXT_MAIN};
        }}
        """

    @staticmethod
    def card() -> str:
        return f"background:{CARD_BG}; border-radius:28px;"

    @staticmethod
    def white_card() -> str:
        return "background: rgba(255,255,255,0.84); border-radius: 20px;"


class BadgeLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            """
            QLabel {
                background: #ecfdf5;
                color: #047857;
                border: 1px solid #a7f3d0;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 14px;
                font-weight: 600;
            }
            """
        )


class ToastLabel(QLabel):
    def __init__(self):
        super().__init__("")
        self.setVisible(False)
        self.setWordWrap(True)
        self.setStyleSheet(
            """
            QLabel {
                background: #ecfdf5;
                color: #065f46;
                border: 1px solid rgba(15,23,42,0.05);
                border-radius: 18px;
                padding: 12px 16px;
                font-size: 16px;
                font-weight: 600;
            }
            """
        )

    def show_message(self, text: str, error: bool = False):
        self.setText(text)
        if error:
            self.setStyleSheet(
                """
                QLabel {
                    background: #fef2f2;
                    color: #991b1b;
                    border: 1px solid rgba(15,23,42,0.05);
                    border-radius: 18px;
                    padding: 12px 16px;
                    font-size: 16px;
                    font-weight: 600;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QLabel {
                    background: #ecfdf5;
                    color: #065f46;
                    border: 1px solid rgba(15,23,42,0.05);
                    border-radius: 18px;
                    padding: 12px 16px;
                    font-size: 16px;
                    font-weight: 600;
                }
                """
            )
        self.setVisible(True)


class InfoPill(QFrame):
    def __init__(self, label: str, value: str, badge: bool = False):
        super().__init__()
        self.setStyleSheet(
            "background: rgba(255,255,255,0.78); border-radius: 16px; border: 1px solid rgba(15,23,42,0.05);"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color:{TEXT_HINT}; font-size:13px;")
        layout.addWidget(label_widget)

        if badge:
            value_widget = BadgeLabel(value)
            value_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(value_widget)
        else:
            value_widget = QLabel(value)
            value_widget.setWordWrap(True)
            value_widget.setStyleSheet(f"color:{TEXT_MAIN}; font-size:18px; font-weight:700;")
            layout.addWidget(value_widget)

        self.value_widget = value_widget

    def set_value(self, value: str):
        if isinstance(self.value_widget, QLabel):
            self.value_widget.setText(value)


class EditField(QFrame):
    def __init__(self, label: str, value: str = "", placeholder: str = "", hint: str = ""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title = QLabel(label)
        self.title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:16px; font-weight:700;")
        layout.addWidget(self.title)

        self.input = QLineEdit()
        self.input.setText(value)
        self.input.setPlaceholderText(placeholder)
        self.input.setStyleSheet(UiStyle.line_edit())
        layout.addWidget(self.input)

        self.hint = QLabel(hint)
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(f"color:{TEXT_HINT}; font-size:12px;")
        self.hint.setVisible(bool(hint))
        layout.addWidget(self.hint)

        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setStyleSheet(f"color:{ERROR}; font-size:12px;")
        self.error.setVisible(False)
        layout.addWidget(self.error)

    def text(self) -> str:
        return self.input.text()

    def set_text(self, text: str):
        self.input.setText(text)

    def set_error(self, text: str = ""):
        self.error.setVisible(bool(text))
        self.error.setText(text)
        self.input.setStyleSheet(UiStyle.line_edit(error=bool(text), disabled=not self.input.isEnabled()))

    def set_disabled(self, disabled: bool):
        self.input.setEnabled(not disabled)
        self.input.setStyleSheet(UiStyle.line_edit(error=self.error.isVisible(), disabled=disabled))


class SecurityDialog(QDialog):
    def __init__(self, title: str, desc: str, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.resize(650, 420)
        self.setStyleSheet(f"QDialog {{ background: {CARD_BG}; border-radius: 28px; }}")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(14)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:28px; font-weight:700;")
        self.main_layout.addWidget(self.title_label)

        self.desc_label = QLabel(desc)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(f"color:{TEXT_SUB}; font-size:15px;")
        self.main_layout.addWidget(self.desc_label)

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(12)
        self.main_layout.addLayout(self.body_layout)

        self.footer_layout = QHBoxLayout()
        self.footer_layout.addStretch(1)
        self.footer_layout.setSpacing(10)
        self.main_layout.addLayout(self.footer_layout)

    def add_footer_button(self, text: str, primary: bool, callback):
        btn = QPushButton(text)
        btn.setStyleSheet(UiStyle.primary_button() if primary else UiStyle.secondary_button())
        btn.clicked.connect(callback)
        self.footer_layout.addWidget(btn)
        return btn


class PasswordStrengthWidget(QFrame):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.text_label = QLabel("密码强度：未填写")
        self.text_label.setStyleSheet(f"color:{TEXT_HINT}; font-size:12px;")
        layout.addWidget(self.text_label)

        bars_layout = QHBoxLayout()
        bars_layout.setSpacing(6)
        self.bars = []
        for _ in range(3):
            bar = QFrame()
            bar.setFixedHeight(8)
            bar.setStyleSheet("background:#e2e8f0; border-radius: 4px;")
            bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            bars_layout.addWidget(bar)
            self.bars.append(bar)
        layout.addLayout(bars_layout)

    def update_strength(self, password: str):
        label, level = get_password_strength(password)
        self.text_label.setText(f"密码强度：{label}")
        for idx, bar in enumerate(self.bars, start=1):
            color = GREEN if level >= idx else "#e2e8f0"
            bar.setStyleSheet(f"background:{color}; border-radius: 4px;")


class PersonalInfoPage(QMainWindow):
    logout_requested = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.user = dict(INITIAL_USER)
        self.user_data = self.user
        self.logged_out = False
        self.is_editing_profile = False
        self.phone_countdown = 0
        self.reset_countdown = 0

        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(lambda: self.toast.setVisible(False))

        self.phone_timer = QTimer(self)
        self.phone_timer.timeout.connect(self.update_phone_countdown)

        self.reset_timer = QTimer(self)
        self.reset_timer.timeout.connect(self.update_reset_countdown)

        self._apply_font_family()

        self.setWindowTitle("个人信息")
        self.resize(1440, 960)
        self.build_ui()
        self.refresh_ui()

    def _apply_font_family(self):
        family = UiStyle.ensure_font_family_65_medium()
        if family:
            font = self.font()
            font.setFamily(family)
            self.setFont(font)
            # 强制页面内所有控件使用同一字体族，避免局部样式覆盖
            self.setStyleSheet(f"* {{ font-family: '{family}'; }}")

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background:{PAGE_BG};")
        root_layout.addWidget(scroll)

        self.page = QWidget()
        self.page.setStyleSheet(f"background:{PAGE_BG};")
        scroll.setWidget(self.page)

        self.page_layout = QVBoxLayout(self.page)
        self.page_layout.setContentsMargins(8, 8, 8, 24)
        self.page_layout.setSpacing(14)

        self.btn_back = QPushButton("返回")
        self.btn_back.setStyleSheet(UiStyle.secondary_button())
        self.btn_back.setVisible(False)

        self.refresh_btn = QPushButton("刷新信息")
        self.refresh_btn.setStyleSheet(UiStyle.primary_button())
        self.refresh_btn.clicked.connect(lambda: self.show_toast("账户信息已刷新（演示）"))
        self.refresh_btn.setVisible(False)
        self.btn_refresh = self.refresh_btn

        self.toast = ToastLabel()
        self.page_layout.addWidget(self.toast)

        self.overview_card = self.make_big_card("账户概览", "")
        self.page_layout.addWidget(self.overview_card)

        self.security_card = self.make_big_card("账号安全", "")
        self.page_layout.addWidget(self.security_card)

        self.login_card = self.make_big_card("当前登录信息", "")
        self.page_layout.addWidget(self.login_card)

        self.operation_card = self.make_big_card("登录操作", "")
        self.page_layout.addWidget(self.operation_card)

        self.logged_out_panel = QFrame()
        self.logged_out_panel.setVisible(False)
        self.logged_out_panel.setStyleSheet(UiStyle.card())
        logged_layout = QVBoxLayout(self.logged_out_panel)
        logged_layout.setContentsMargins(36, 36, 36, 36)
        logged_layout.setSpacing(24)
        logged_layout.addStretch(1)
        logged_title = QLabel("已退出登录")
        logged_title.setAlignment(Qt.AlignCenter)
        logged_title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:36px; font-weight:800;")
        logged_desc = QLabel("真实系统中这里会返回登录页，并清除本地登录状态。")
        logged_desc.setAlignment(Qt.AlignCenter)
        logged_desc.setWordWrap(True)
        logged_desc.setStyleSheet(f"color:{TEXT_SUB}; font-size:20px;")
        self.return_demo_btn = QPushButton("返回演示页面")
        self.return_demo_btn.setStyleSheet(UiStyle.primary_button())
        self.return_demo_btn.clicked.connect(self.return_demo)
        logged_layout.addWidget(logged_title)
        logged_layout.addWidget(logged_desc)
        logged_layout.addWidget(self.return_demo_btn, alignment=Qt.AlignCenter)
        logged_layout.addStretch(1)
        self.page_layout.addWidget(self.logged_out_panel)

        self.build_overview_content()
        self.build_security_content()
        self.build_login_content()
        self.build_operation_content()

    def make_big_card(self, title_text: str, desc_text: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(UiStyle.card())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(10)
        text_box = QVBoxLayout()
        title = QLabel(title_text)
        title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:26px; font-weight:800;")
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{TEXT_SUB}; font-size:16px;")
        desc.setVisible(bool(desc_text))
        text_box.addWidget(title)
        text_box.addWidget(desc)
        header.addLayout(text_box)
        header.addStretch(1)
        layout.addLayout(header)
        card.body_layout = layout
        return card

    def clear_body_keep_header(self, card: QFrame):
        layout = card.body_layout
        while layout.count() > 1:
            item = layout.takeAt(1)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.delete_layout(item.layout())

    def delete_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.delete_layout(item.layout())

    def build_overview_content(self):
        self.clear_body_keep_header(self.overview_card)
        layout = self.overview_card.body_layout

        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.edit_profile_btn = QPushButton("编辑")
        self.edit_profile_btn.setStyleSheet(UiStyle.primary_button())
        self.edit_profile_btn.clicked.connect(self.begin_edit_profile)
        top_row.addWidget(self.edit_profile_btn)
        layout.addLayout(top_row)

        profile_top = QWidget()
        profile_top_layout = QHBoxLayout(profile_top)
        profile_top_layout.setContentsMargins(0, 0, 0, 0)
        profile_top_layout.setSpacing(14)

        left_box = QFrame()
        left_box.setStyleSheet(UiStyle.white_card())
        left_layout = QHBoxLayout(left_box)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(14)

        self.avatar_label = QLabel(self.user["avatarText"])
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setFixedSize(96, 96)
        self.avatar_label.setStyleSheet(
            "background:#0f172a; color:white; border-radius:24px; font-size:30px; font-weight:800;"
        )
        left_layout.addWidget(self.avatar_label)

        name_box = QVBoxLayout()
        self.nickname_big_label = QLabel(self.user["nickname"])
        self.nickname_big_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:24px; font-weight:800;")
        self.username_big_label = QLabel(f"用户名：{self.user['username']}")
        self.username_big_label.setStyleSheet(f"color:{TEXT_HINT}; font-size:16px;")
        name_box.addWidget(self.nickname_big_label)
        name_box.addWidget(self.username_big_label)
        name_box.addWidget(BadgeLabel(self.user["accountStatus"]))
        name_box.addStretch(1)
        left_layout.addLayout(name_box)
        profile_top_layout.addWidget(left_box, 1)

        pills_widget = QWidget()
        self.pills_grid = QGridLayout(pills_widget)
        self.pills_grid.setContentsMargins(0, 0, 0, 0)
        self.pills_grid.setSpacing(12)
        self.pill_phone = InfoPill("绑定手机号", mask_phone(self.user["phone"]))
        self.pill_status = InfoPill("账户状态", self.user["accountStatus"], badge=True)
        self.pill_register = InfoPill("注册时间", self.user["registerTime"])
        self.pill_last_login = InfoPill("上次登录", self.user["lastLoginTime"])
        self.pill_device = InfoPill("当前设备", self.user["currentDevice"])
        self.pill_version = InfoPill("客户端版本", self.user["version"])
        pills = [
            self.pill_phone,
            self.pill_status,
            self.pill_register,
            self.pill_last_login,
            self.pill_device,
            self.pill_version,
        ]
        for i, pill in enumerate(pills):
            self.pills_grid.addWidget(pill, i // 3, i % 3)
        profile_top_layout.addWidget(pills_widget, 2)
        layout.addWidget(profile_top)

        editable_card = QFrame()
        editable_card.setStyleSheet(UiStyle.white_card())
        editable_layout = QVBoxLayout(editable_card)
        editable_layout.setContentsMargins(18, 18, 18, 18)
        editable_layout.setSpacing(12)
        editable_title = QLabel("可编辑账户信息")
        editable_title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:22px; font-weight:800;")
        editable_layout.addWidget(editable_title)

        fields_widget = QWidget()
        fields_layout = QGridLayout(fields_widget)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(12)

        self.field_nickname = EditField("用户昵称", self.user["nickname"], "请输入用户昵称")
        self.field_username = EditField("用户名", self.user["username"], "请输入用户名", "只能包含下划线、英文字母和数字。")
        self.field_avatar = EditField("头像简称", self.user["avatarText"], "例如 XL", "第一版先用 1~2 个字符模拟头像。")
        fields_layout.addWidget(self.field_nickname, 0, 0)
        fields_layout.addWidget(self.field_username, 0, 1)
        fields_layout.addWidget(self.field_avatar, 0, 2)
        editable_layout.addWidget(fields_widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.save_profile_btn = QPushButton("保存")
        self.save_profile_btn.setStyleSheet(UiStyle.primary_button())
        self.save_profile_btn.clicked.connect(self.save_profile)
        self.cancel_profile_btn = QPushButton("取消")
        self.cancel_profile_btn.setStyleSheet(UiStyle.secondary_button())
        self.cancel_profile_btn.clicked.connect(self.cancel_profile)
        btn_row.addWidget(self.save_profile_btn)
        btn_row.addWidget(self.cancel_profile_btn)
        btn_row.addStretch(1)
        editable_layout.addLayout(btn_row)
        layout.addWidget(editable_card)

    def build_security_content(self):
        self.clear_body_keep_header(self.security_card)
        layout = self.security_card.body_layout
        row = QHBoxLayout()
        row.setSpacing(12)

        self.change_pwd_box = self.make_action_box("登录密码", "当前密码已设置。建议定期修改密码以保障账户安全。", "修改密码", self.open_change_password)
        self.change_phone_box = self.make_action_box("绑定手机号", f"当前绑定手机号：{mask_phone(self.user['phone'])}", "更换手机号", self.open_change_phone)
        self.reset_pwd_box = self.make_action_box("找回密码", "如果忘记密码，可通过绑定手机号验证后重置密码。", "找回密码", self.open_reset_password)

        row.addWidget(self.change_pwd_box)
        row.addWidget(self.change_phone_box)
        row.addWidget(self.reset_pwd_box)
        layout.addLayout(row)

    def build_login_content(self):
        self.clear_body_keep_header(self.login_card)
        layout = self.login_card.body_layout
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        self.login_pill_device = InfoPill("当前设备", self.user["currentDevice"])
        self.login_pill_time = InfoPill("登录时间", self.user["currentLoginTime"])
        self.login_pill_version = InfoPill("客户端版本", self.user["version"])
        self.login_pill_status = InfoPill("登录状态", self.user["loginStatus"], badge=True)
        pills = [self.login_pill_device, self.login_pill_time, self.login_pill_version, self.login_pill_status]
        for i, pill in enumerate(pills):
            grid.addWidget(pill, 0, i)
        layout.addWidget(grid_widget)

    def build_operation_content(self):
        self.clear_body_keep_header(self.operation_card)
        layout = self.operation_card.body_layout
        row = QHBoxLayout()
        self.logout_btn = QPushButton("退出登录")
        self.logout_btn.setStyleSheet(UiStyle.primary_button())
        self.logout_btn.clicked.connect(self.confirm_logout)
        row.addWidget(self.logout_btn)
        row.addStretch(1)
        layout.addLayout(row)

    def make_action_box(self, title: str, desc: str, button_text: str, callback):
        box = QFrame()
        box.setStyleSheet(UiStyle.white_card())
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:20px; font-weight:800;")
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color:{TEXT_SUB}; font-size:15px;")
        btn = QPushButton(button_text)
        btn.setStyleSheet(UiStyle.primary_button())
        btn.clicked.connect(callback)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch(1)
        layout.addWidget(btn)
        box.desc_label = desc_label
        return box

    def refresh_ui(self):
        self.avatar_label.setText(self.user["avatarText"])
        self.nickname_big_label.setText(self.user["nickname"])
        self.username_big_label.setText(f"用户名：{self.user['username']}")
        self.pill_phone.set_value(mask_phone(self.user["phone"]))
        self.pill_register.set_value(self.user["registerTime"])
        self.pill_last_login.set_value(self.user["lastLoginTime"])
        self.pill_device.set_value(self.user["currentDevice"])
        self.pill_version.set_value(self.user["version"])
        self.login_pill_device.set_value(self.user["currentDevice"])
        self.login_pill_time.set_value(self.user["currentLoginTime"])
        self.login_pill_version.set_value(self.user["version"])
        self.change_phone_box.desc_label.setText(f"当前绑定手机号：{mask_phone(self.user['phone'])}")
        self.field_nickname.set_text(self.user["nickname"])
        self.field_username.set_text(self.user["username"])
        self.field_avatar.set_text(self.user["avatarText"])
        self.set_profile_editing(False)

    def load_user_data(self):
        if isinstance(self.user_data, dict):
            self.user = self.user_data
        self.refresh_ui()

    def set_profile_editing(self, editing: bool):
        self.is_editing_profile = editing
        self.edit_profile_btn.setVisible(not editing)
        self.save_profile_btn.setVisible(editing)
        self.cancel_profile_btn.setVisible(editing)
        self.field_nickname.set_disabled(not editing)
        self.field_username.set_disabled(not editing)
        self.field_avatar.set_disabled(not editing)
        if not editing:
            self.clear_profile_errors()

    def clear_profile_errors(self):
        self.field_nickname.set_error("")
        self.field_username.set_error("")
        self.field_avatar.set_error("")

    def show_toast(self, text: str, error: bool = False):
        self.toast.show_message(text, error)
        self.toast_timer.start(2600)

    def begin_edit_profile(self):
        self.set_profile_editing(True)

    def cancel_profile(self):
        self.field_nickname.set_text(self.user["nickname"])
        self.field_username.set_text(self.user["username"])
        self.field_avatar.set_text(self.user["avatarText"])
        self.set_profile_editing(False)

    def save_profile(self):
        self.clear_profile_errors()
        nickname = self.field_nickname.text().strip()
        username = self.field_username.text().strip()
        avatar = self.field_avatar.text().strip().upper()
        ok = True
        if not nickname:
            self.field_nickname.set_error("昵称不能为空")
            ok = False
        elif len(nickname) > 20:
            self.field_nickname.set_error("昵称长度不能超过 20 个字符")
            ok = False
        if not username:
            self.field_username.set_error("用户名不能为空")
            ok = False
        elif len(username) > 30:
            self.field_username.set_error("用户名长度不能超过 30 个字符")
            ok = False
        elif not is_username_valid(username):
            self.field_username.set_error("用户名只能包含英文字母、数字和下划线")
            ok = False
        if not avatar:
            self.field_avatar.set_error("头像简称不能为空")
            ok = False
        elif len(avatar) > 2:
            self.field_avatar.set_error("头像简称建议不超过 2 个字符")
            ok = False
        if not ok:
            return
        self.user["nickname"] = nickname
        self.user["username"] = username
        self.user["avatarText"] = avatar
        self.refresh_ui()
        self.show_toast("账户概览修改成功")

    def open_change_password(self):
        dialog = SecurityDialog("修改密码", "密码长度不少于 8 位，建议包含字母和数字。", self)
        old_field = EditField("当前密码", "", "请输入当前密码")
        old_field.input.setEchoMode(QLineEdit.Password)
        new_field = EditField("新密码", "", "请输入新密码")
        new_field.input.setEchoMode(QLineEdit.Password)
        strength = PasswordStrengthWidget()
        confirm_field = EditField("确认新密码", "", "请再次输入新密码")
        confirm_field.input.setEchoMode(QLineEdit.Password)

        dialog.body_layout.addWidget(old_field)
        dialog.body_layout.addWidget(new_field)
        dialog.body_layout.addWidget(strength)
        dialog.body_layout.addWidget(confirm_field)

        toggle_btn = QPushButton("显示密码")
        toggle_btn.setStyleSheet(UiStyle.secondary_button())
        dialog.body_layout.addWidget(toggle_btn, alignment=Qt.AlignLeft)

        def on_pwd_changed():
            strength.update_strength(new_field.text())

        new_field.input.textChanged.connect(on_pwd_changed)

        def toggle_show():
            show = old_field.input.echoMode() == QLineEdit.Password
            mode = QLineEdit.Normal if show else QLineEdit.Password
            for field in (old_field, new_field, confirm_field):
                field.input.setEchoMode(mode)
            toggle_btn.setText("隐藏密码" if show else "显示密码")

        def submit():
            old_field.set_error("")
            new_field.set_error("")
            confirm_field.set_error("")
            ok = True
            if not old_field.text():
                old_field.set_error("请输入当前密码")
                ok = False
            elif old_field.text() != self.user["password"]:
                old_field.set_error("当前密码不正确")
                ok = False
            if not new_field.text():
                new_field.set_error("请输入新密码")
                ok = False
            elif len(new_field.text()) < 8:
                new_field.set_error("新密码长度不能少于 8 位")
                ok = False
            elif new_field.text() == old_field.text():
                new_field.set_error("新密码不能与当前密码相同")
                ok = False
            if not confirm_field.text():
                confirm_field.set_error("请再次输入新密码")
                ok = False
            elif confirm_field.text() != new_field.text():
                confirm_field.set_error("两次输入的新密码不一致")
                ok = False
            if not ok:
                return
            self.user["password"] = new_field.text()
            dialog.accept()
            self.show_toast("密码修改成功，演示版中当前登录状态保持不变")

        toggle_btn.clicked.connect(toggle_show)
        dialog.add_footer_button("取消", False, dialog.reject)
        dialog.add_footer_button("确认修改", True, submit)
        dialog.exec_()

    def open_change_phone(self):
        dialog = SecurityDialog("更换手机号", "步骤 1：验证当前身份", self)
        stacked_holder = QFrame()
        stacked_layout = QVBoxLayout(stacked_holder)
        stacked_layout.setContentsMargins(0, 0, 0, 0)
        stacked_layout.setSpacing(12)
        dialog.body_layout.addWidget(stacked_holder)

        step1 = QWidget()
        step1_layout = QVBoxLayout(step1)
        step1_layout.setContentsMargins(0, 0, 0, 0)
        pwd_field = EditField("当前密码", "", "请输入当前登录密码")
        pwd_field.input.setEchoMode(QLineEdit.Password)
        step1_layout.addWidget(pwd_field)

        step2 = QWidget()
        step2_layout = QVBoxLayout(step2)
        step2_layout.setContentsMargins(0, 0, 0, 0)
        phone_field = EditField("新手机号", "", "请输入新的手机号")
        code_field = EditField("短信验证码", "", "请输入短信验证码")
        code_row = QHBoxLayout()
        code_row.addWidget(code_field, 1)
        self.phone_code_btn = QPushButton("获取验证码")
        self.phone_code_btn.setStyleSheet(UiStyle.secondary_button())
        code_row.addWidget(self.phone_code_btn)
        step2_layout.addWidget(phone_field)
        step2_layout.addLayout(code_row)
        step2.setVisible(False)

        stacked_layout.addWidget(step1)
        stacked_layout.addWidget(step2)

        back_btn = dialog.add_footer_button("上一步", False, lambda: None)
        cancel_btn = dialog.add_footer_button("取消", False, dialog.reject)
        next_btn = dialog.add_footer_button("下一步", True, lambda: None)
        back_btn.setVisible(False)

        state = {"step": 1}

        def update_step():
            step1.setVisible(state["step"] == 1)
            step2.setVisible(state["step"] == 2)
            back_btn.setVisible(state["step"] == 2)
            next_btn.setText("下一步" if state["step"] == 1 else "确认更换")
            dialog.desc_label.setText("步骤 1：验证当前身份" if state["step"] == 1 else "步骤 2：绑定新手机号")

        def go_next():
            if state["step"] == 1:
                pwd_field.set_error("")
                if not pwd_field.text():
                    pwd_field.set_error("请输入当前密码")
                    return
                if pwd_field.text() != self.user["password"]:
                    pwd_field.set_error("当前密码不正确")
                    return
                state["step"] = 2
                update_step()
                return
            phone_field.set_error("")
            code_field.set_error("")
            ok = True
            new_phone = phone_field.text().strip()
            code = code_field.text().strip()
            if not new_phone:
                phone_field.set_error("请输入新的手机号")
                ok = False
            elif not is_phone_valid(new_phone):
                phone_field.set_error("手机号格式不正确")
                ok = False
            elif new_phone == self.user["phone"]:
                phone_field.set_error("新手机号不能与原手机号相同")
                ok = False
            elif new_phone == "13800000000":
                phone_field.set_error("该手机号已被注册")
                ok = False
            if not code:
                code_field.set_error("请输入短信验证码")
                ok = False
            elif code != "123456":
                code_field.set_error("验证码错误或已过期")
                ok = False
            if not ok:
                return
            self.user["phone"] = new_phone
            self.refresh_ui()
            dialog.accept()
            self.show_toast("手机号更换成功")

        def go_back():
            state["step"] = 1
            update_step()

        def send_code():
            phone_field.set_error("")
            new_phone = phone_field.text().strip()
            if not new_phone:
                phone_field.set_error("请输入新的手机号")
                return
            if not is_phone_valid(new_phone):
                phone_field.set_error("手机号格式不正确")
                return
            if new_phone == self.user["phone"]:
                phone_field.set_error("新手机号不能与原手机号相同")
                return
            self.phone_countdown = 60
            self.phone_code_btn.setEnabled(False)
            self.phone_code_btn.setText("60s 后重试")
            self.phone_timer.start(1000)
            self.show_toast("验证码已发送到新手机号（演示）")

        next_btn.clicked.disconnect()
        next_btn.clicked.connect(go_next)
        back_btn.clicked.disconnect()
        back_btn.clicked.connect(go_back)
        self.phone_code_btn.clicked.connect(send_code)
        update_step()
        dialog.exec_()

    def open_reset_password(self):
        dialog = SecurityDialog("找回密码", "通过绑定手机号验证后重置密码。", self)
        phone_field = EditField("手机号", "", "请输入绑定的手机号")
        code_field = EditField("短信验证码", "", "请输入短信验证码")
        code_row = QHBoxLayout()
        code_row.addWidget(code_field, 1)
        self.reset_code_btn = QPushButton("获取验证码")
        self.reset_code_btn.setStyleSheet(UiStyle.secondary_button())
        code_row.addWidget(self.reset_code_btn)
        new_field = EditField("新密码", "", "请输入新的登录密码")
        new_field.input.setEchoMode(QLineEdit.Password)
        strength = PasswordStrengthWidget()
        confirm_field = EditField("确认新密码", "", "请再次输入新的登录密码")
        confirm_field.input.setEchoMode(QLineEdit.Password)
        toggle_btn = QPushButton("显示密码")
        toggle_btn.setStyleSheet(UiStyle.secondary_button())

        dialog.body_layout.addWidget(phone_field)
        dialog.body_layout.addLayout(code_row)
        dialog.body_layout.addWidget(new_field)
        dialog.body_layout.addWidget(strength)
        dialog.body_layout.addWidget(confirm_field)
        dialog.body_layout.addWidget(toggle_btn, alignment=Qt.AlignLeft)

        new_field.input.textChanged.connect(lambda: strength.update_strength(new_field.text()))

        def toggle_show():
            show = new_field.input.echoMode() == QLineEdit.Password
            mode = QLineEdit.Normal if show else QLineEdit.Password
            new_field.input.setEchoMode(mode)
            confirm_field.input.setEchoMode(mode)
            toggle_btn.setText("隐藏密码" if show else "显示密码")

        def send_code():
            phone_field.set_error("")
            phone = phone_field.text().strip()
            if not phone:
                phone_field.set_error("请输入手机号")
                return
            if not is_phone_valid(phone):
                phone_field.set_error("手机号格式不正确")
                return
            if phone != self.user["phone"]:
                phone_field.set_error("该手机号未注册或非当前账户绑定手机号")
                return
            self.reset_countdown = 60
            self.reset_code_btn.setEnabled(False)
            self.reset_code_btn.setText("60s 后重试")
            self.reset_timer.start(1000)
            self.show_toast("验证码已发送（演示）")

        def submit():
            phone_field.set_error("")
            code_field.set_error("")
            new_field.set_error("")
            confirm_field.set_error("")
            ok = True
            phone = phone_field.text().strip()
            code = code_field.text().strip()
            if not phone:
                phone_field.set_error("请输入手机号")
                ok = False
            elif not is_phone_valid(phone):
                phone_field.set_error("手机号格式不正确")
                ok = False
            elif phone != self.user["phone"]:
                phone_field.set_error("该手机号未注册或非当前账户绑定手机号")
                ok = False
            if not code:
                code_field.set_error("请输入验证码")
                ok = False
            elif code != "123456":
                code_field.set_error("验证码错误或已过期")
                ok = False
            if not new_field.text():
                new_field.set_error("请输入新的登录密码")
                ok = False
            elif len(new_field.text()) < 8:
                new_field.set_error("密码长度不能少于 8 位")
                ok = False
            if not confirm_field.text():
                confirm_field.set_error("请再次输入新的登录密码")
                ok = False
            elif confirm_field.text() != new_field.text():
                confirm_field.set_error("两次输入的密码不一致")
                ok = False
            if not ok:
                return
            self.user["password"] = new_field.text()
            dialog.accept()
            self.show_toast("密码重置成功，请使用新密码登录")

        self.reset_code_btn.clicked.connect(send_code)
        toggle_btn.clicked.connect(toggle_show)
        dialog.add_footer_button("取消", False, dialog.reject)
        dialog.add_footer_button("确认重置", True, submit)
        dialog.exec_()

    def confirm_logout(self):
        result = QMessageBox.question(self, "退出登录", "确定要退出当前账户吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if result == QMessageBox.Yes:
            self.logout_requested.emit()
            self.logged_out = True
            self.overview_card.setVisible(False)
            self.security_card.setVisible(False)
            self.login_card.setVisible(False)
            self.operation_card.setVisible(False)
            self.logged_out_panel.setVisible(True)
            self.show_toast("已退出登录")

    def return_demo(self):
        self.logged_out = False
        self.overview_card.setVisible(True)
        self.security_card.setVisible(True)
        self.login_card.setVisible(True)
        self.operation_card.setVisible(True)
        self.logged_out_panel.setVisible(False)

    def update_phone_countdown(self):
        if self.phone_countdown <= 0:
            self.phone_timer.stop()
            if hasattr(self, "phone_code_btn") and self.phone_code_btn:
                self.phone_code_btn.setEnabled(True)
                self.phone_code_btn.setText("获取验证码")
            return
        self.phone_countdown -= 1
        if hasattr(self, "phone_code_btn") and self.phone_code_btn:
            if self.phone_countdown <= 0:
                self.phone_code_btn.setEnabled(True)
                self.phone_code_btn.setText("获取验证码")
                self.phone_timer.stop()
            else:
                self.phone_code_btn.setText(f"{self.phone_countdown}s 后重试")

    def update_reset_countdown(self):
        if self.reset_countdown <= 0:
            self.reset_timer.stop()
            if hasattr(self, "reset_code_btn") and self.reset_code_btn:
                self.reset_code_btn.setEnabled(True)
                self.reset_code_btn.setText("获取验证码")
            return
        self.reset_countdown -= 1
        if hasattr(self, "reset_code_btn") and self.reset_code_btn:
            if self.reset_countdown <= 0:
                self.reset_code_btn.setEnabled(True)
                self.reset_code_btn.setText("获取验证码")
                self.reset_timer.stop()
            else:
                self.reset_code_btn.setText(f"{self.reset_countdown}s 后重试")




if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    UiStyle.set_app_font(app)
    window = PersonalInfoPage()
    window.show()
    sys.exit(app.exec_())
