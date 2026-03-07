import requests
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot,QTimer,QSettings,QEvent
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QLineEdit,QLabel
import os, sys, sqlite3
import subprocess, ctypes



from ui_1080_py.Ui_login_ui import Ui_Form

import sys
import os

def open_system_keyboard():
    """Windows 屏幕键盘 osk.exe：已打开则前置，未打开则启动"""
    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW("OSKMainClass", None)
    if hwnd:
        user32.ShowWindow(hwnd, 5)            # SW_SHOW
        user32.SetForegroundWindow(hwnd)
        return
    try:
        subprocess.Popen(["osk.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        # 兜底：显式路径
        path = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "osk.exe")
        subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def close_system_keyboard():
    """关闭 osk.exe（优雅发送关闭消息）"""
    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW("OSKMainClass", None)
    if hwnd:
        WM_SYSCOMMAND, SC_CLOSE = 0x0112, 0xF060
        user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_CLOSE, 0)


def _get_db_path():
    """
    返回 (路径, 是否外部库)：
    1) 优先用 EXE 同目录的 db/auth.db（便于运维替换，不需要重打包）；
    2) 否则用打包内置的 db/auth.db（只读打开）；
    3) 开发态兜底：当前文件同目录的 db/auth.db。
    """
    # EXE 同目录
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.abspath(".")
    ext = os.path.join(exe_dir, "db", "auth.db")
    if os.path.exists(ext):
        return ext, True

    # 打包内置（_MEIPASS）
    bundle = getattr(sys, "_MEIPASS", "")
    if bundle:
        inner = os.path.join(bundle, "db", "auth.db")
        if os.path.exists(inner):
            return inner, False

    # 开发态兜底：按源代码目录寻找
    dev = os.path.join(os.path.dirname(__file__), "db", "auth.db")
    return dev, True

def check_user(account: str, password: str) -> bool:
    """
    明文密码校验；不创建/写入任何本地文件。
    数据库表结构要求：users(account TEXT UNIQUE, password TEXT)
    """
    acc = (account or "").strip()
    if not acc:
        return False

    path, external = _get_db_path()

    # 外部库：普通方式打开；打包内置库：只读 URI 打开，避免写临时副本
    conn = (sqlite3.connect(path, check_same_thread=False)
            if external else sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False))
    try:
        row = conn.execute("SELECT password FROM users WHERE account=?", (acc,)).fetchone()
        if not row:
            return False
        stored = row[0] or ""
        return (password or "") == stored
    finally:
        conn.close()

class LoginMata(QWidget, Ui_Form):
    result_callBack = pyqtSignal(str, str, str, str)
    result_location = pyqtSignal(str)
    login_result = pyqtSignal(bool)
    debug_result = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(LoginMata, self).__init__(parent)
        self.setupUi(self)
        self.move(0, 0)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_font()
        # self.phone_l.setText('13122651742')
        # self.password_l.setText('430248615')
        self.hidden_password.installEventFilter(self)
        self.phone_l.installEventFilter(self)
        self.password_l.installEventFilter(self)
        self._load_last_login() 

    @pyqtSlot()
    def on_login_btn_clicked(self):
        account  = self.phone_l.text().strip()
        password = self.password_l.text().strip()

        if not account or not password:
            self.login_result.emit(False)
            self.debug_result.emit(False)
            return

        if check_user(account, password):
            # ✅ 登录成功：仅保存账号/可选 token，不保存明文密码
            s = QSettings("Xiliu", "Miketee")
            s.setValue("login/last_account", account)
            s.setValue("login/last_password", password)
            # s.remove("login/last_password")   # 确保不再保存密码
            s.sync()

            self.login_result.emit(True)
            self.debug_result.emit(True)
            self.close()
        else:
            self.login_result.emit(False)
            self.debug_result.emit(False)


    # # 简单“Toast”提示：居中黑底白字，N毫秒自动消失
    # def _show_toast(self, text: str, msec: int = 3000):
    #     toast = QLabel(text, self)
    #     toast.setObjectName("toast")
    #     toast.setAlignment(Qt.AlignCenter)
    #     toast.setStyleSheet("""
    #         QLabel#toast {
    #             background: rgba(0,0,0,0.78);
    #             color: #FFFFFF;
    #             padding: 10px 18px;
    #             border-radius: 12px;
    #             font-size: 20px;
    #         }
    #     """)
    #     toast.adjustSize()
    #     # 居中放在窗口下 1/3 处，视觉更像系统 Toast
    #     x = (self.width() - toast.width()) // 2
    #     y = int(self.height() * 0.66) - toast.height() // 2
    #     toast.move(max(12, x), max(12, y))
    #     toast.show()
    #     QTimer.singleShot(msec, toast.deleteLater)

    @pyqtSlot()
    def on_cancel_btn_clicked(self):
        self.close()

    @pyqtSlot()
    def on_dialog_close_btn_clicked(self):
        self.close()


    def eventFilter(self, obj, event):
        # 1) 双击账号/密码编辑框 -> 打开 Windows 键盘
        if obj in (self.phone_l, self.password_l) and event.type() == QEvent.MouseButtonDblClick:
            open_system_keyboard()
            return True

        # 2) 点击“隐藏/显示密码”的图标
        if obj == self.hidden_password and event.type() == QEvent.MouseButtonPress:
            if self.password_l.echoMode() == QLineEdit.Password:
                self.password_l.setEchoMode(QLineEdit.Normal)
            else:
                self.password_l.setEchoMode(QLineEdit.Password)
            return True

        return super().eventFilter(obj, event)
    
    def closeEvent(self, e):
        try:
            close_system_keyboard()
        finally:
            super().closeEvent(e)



    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font
    def init_font(self):
        AlibabaPuHuiTi_3_85_Bold_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')

        )
        if AlibabaPuHuiTi_3_85_Bold_font_id != -1:
            AlibabaPuHuiTi_3_85_Bold_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_85_Bold_font_id)[0]
            AlibabaPuHuiTi_3_85_Bold_custom_font_48 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 25, QFont.Bold)
            self.label.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_48)
            self.label_2.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_48)
            self.phone_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_48)
            self.password_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_48)
            self.login_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_48)
            self.cancel_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_48)
    def _settings(self) -> QSettings:
        return QSettings("Xiliu", "Miketee")

    def _load_last_login(self):
        s = self._settings()
        acc = s.value("login/last_account", "", type=str)
        pwd = s.value("login/last_password", "", type=str)
        if acc:
            self.phone_l.setText(acc)
        if pwd:
            self.password_l.setText(pwd)

    def _save_last_login(self, account: str, password: str):
        s = self._settings()
        s.setValue("login/last_account", account)
        s.setValue("login/last_password", password)
        s.sync()






