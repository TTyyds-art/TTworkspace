APP_VERSION = "4.0.5"
# -*- coding: utf-8 -*-
import math
import sys
import os
import tempfile
import csv
import pandas as pd
from datetime import datetime, timedelta
import requests, time
import json
import cv2
import os, sys
import re
import time as _time

from collections import deque
from pathlib import Path
import json
from datetime import date
from requests.exceptions import HTTPError
sys.path.append(os.path.join(os.path.dirname(__file__), "control"))
# from material_assign_dialog import MaterialAssignDialog
from PyQt5.QtWidgets import QDialog
from PyQt5 import QtGui,QtCore
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QSize,QThread,QObject,QEvent,QSettings
from PyQt5.QtGui import QFontDatabase, QFont, QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QGridLayout, QScroller, QSizePolicy, QVBoxLayout, QLabel, QMessageBox,QGraphicsOpacityEffect,QProgressDialog,QProgressBar
from PyQt5 import QtWidgets
import MenuBtnStyle
from bean.menu_shopping_cart_bean import MenuShoppingCartBean
from bean.new_tee_bean import NewTeeBean
from bean.order_bean import OrderBean
from bean.order_tee_bean import TeeBean
from bean.message_bean import MessageBean
from control.item_screen_conduit_mata import ItemScreenConduitWMata
from control.order_dialog_1_mata import OrderDialog1
from control.message_dialog_mata import MessageDialog
from control.second_screen_mata import SecondScreenMata
from control.btn_page_mata import BtnPageMata
from control.camera_frame_mata import CameraFrameMata
from control.conduit_card_mata import ConduitCardWidget
from control.item_clean_load_day_mata import CleanDayLoadMata
from control.item_clean_load_week_mata import CleanWeekLoadMata
from control.item_conduit_mata import ItemConduitMata
from control.item_setting_local_message_record_mata import ItemSettingLocalMessageRecordMata
from control.item_setting_local_tee_record_mata import ItemSettingLocalTeeRecordMata
from control.login_mata import LoginMata
# from control.manager_keyboard_mata import ManagerKeyboardMata
from control.manager_keyboard_mata import ManagerKeyboardMata as ManagerKeyboardOld  # 管理页老键盘（只接收 parent）
from control.conduit_card_keyboard_mata import ManagerKeyboardMata as MaketeeKeyboard  # 泡茶页新键盘（title, x, y, parent）
from control.menu_card_mata import MenuCardWidget
from control.order_card_mata import OrderCardWidget
from control.outee_notice_mata import OutTeeNoticeMata
from db import db_util
from style_utils import MenuStyle
from threads.camera_thread import CameraThread
from threads.conduit_thread import ConduitThread,MaketeeConduitThread
from threads.date_thread import DateThread
from threads.ip_thread import IpThread
from threads.keyboard_thread import KeyboardThread
from threads.manager_main_screen_conduit_thread import ManagerMainScreenConduit
from threads.menu_tee_bean_thread import MenuTeeBeanThread
from threads.order_complete_thread import OrderNotice
from threads.order_save_to_db import OrderSaveToDB
from threads.message_save_to_db import MessageSaveToDB
from threads.order_thread import OrderThread
from threads.refresh_order_content_thread import RefreshOrderContentThread
from threads.refresh_setting_loacl_message_thread import RefreshSettingLocalMessageThread
from threads.refresh_setting_loacl_tee_thread import RefreshSettingLocalTeeThread
from tool_utils import util
from ui_1080_py.Ui_main_1080_ui import Ui_Form
from threads.SerialThread import SerialThread
from threads.conduit_serial_thread import ConduitSerialThread
# from threads.manager_second_screen_conduit_thread import ManagerSecondScreenConduit
from control.maketee_control import MaketeeController


from control.conduit_new_dialog_mata import NewConduitDialog
from bean.new_conduit_bean import NewConduitBean
from control.material_assign_dialog import ChannelSelectDialog  # 或 MaterialAssignDialog（等价）
from tool_utils.util import clear_layout_hard  # 用上面的函数
from control.update_util import (
    get_local_version, fetch_remote_version, newer_than,
    download_file,apply_update_and_restart , local_app_path,update_dirs
)
from control.menu_update_mata import MenuUpdateWidget
from control.language_settings_mata import LanguageSettingsPage
from control.language_manager import LanguageManager

ICE_CHANNELS = set("AB")      # 冰路通道，按你机器实际改
SUGAR_CANDIDATES = set("CDE") # 配方里可能出现的糖路通道（出现了才按糖量缩放）

# === 比例配置 ===
ICE_RATIO   = {"少冰": 0.6, "正常冰": 1.0, "常温": 0.0, "热饮": 0.0}
SUGAR_RATIO = {"常规": 1.0, "五分糖": 0.5, "三分糖": 0.3}

# 旧式“字母配方”时的保底集合；中文配方会用“动态集合”
ICE_CHANNELS     = set("AB")
SUGAR_CANDIDATES = set("CDE")   # 你之前已把 H 改成 E

# 名称关键词：用于“中文配方”时动态识别冰/糖路
ICE_NAME_KEYS   = {"冰", "碎冰"}
SUGAR_NAME_KEYS = {"糖", "糖浆", "果糖", "蔗糖", "黑糖", "红糖", "白砂糖", "蜂蜜", "糖水"}

LOW_STOCK_THRESHOLD_G = 50  # 任一所需通道余量 < 50g -> 置灰
LOW_STOCK_POPUP_G = 100  # 余量低于此值 -> 弹绿色提醒框
EXCLUDE_LOW_STOCK_LETTERS = {'L'}

# === WooCommerce 连接配置（先直写，可跑通再放到设置里） ===
WC_SITE = "https://xiliu.store"  # 例如 https://xiliu.store
WC_CK   = "ck_1a0347c86f80277bd149ed0e5709a9ecc88c550b"   
WC_CS   = "cs_d406696e099e30fbffbe0db2c6e67096b6c2b8c3"   

from PyQt5 import sip

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import QWidget


def current_version() -> str:
    """
    优先使用内置 APP_VERSION；没有再降级到 update_util.get_local_version()
    （get_local_version 目前是从 EXE 文件名里解析版本号）
    """
    v = str(globals().get("APP_VERSION", "")).strip()
    if v:
        return v
    # 兜底：仍然可用文件名法
    from control.update_util import get_local_version
    return get_local_version() or "0.0.0"

# === 泡茶页专用卡片（使用 conduit_card_maketee_ui.ui）===
from PyQt5 import QtCore, QtWidgets
from ui_1080_py.Ui_conduit_card_maketee_ui import Ui_Form as UiMaketeeCard  # 你上传的 pyuic 文件

class ConduitCardMaketeeWidget(QtWidgets.QWidget):
    """
    泡茶页卡片：编号 + 名称 + 预计时长（新 UI）
    目标：和管理页一样的“被选中整卡变绿”的视觉效果；字体统一阿里巴巴普惠体。
    """
    changed_conduit_card = QtCore.pyqtSignal(bool, object)

    # —— 主题色（和你项目一致）——
    _GREEN = "#2C9F61"          # 主绿
    _GREEN_DARK = "#15884A"     # 胶囊深绿（对比更好看）

    # —— 基础/选中 两套 QSS（只针对此卡片里的对象名，不会影响别处）——
    _QSS_BASE = """
    QWidget#cardRoot {
        background: #FFFFFF;
        border-radius: 28px;
        border: 2px solid rgba(44,159,97,0.20);
    }
    QLabel#conduit_card_id_2 {
        background: %(GREEN_DARK)s;
        color: #FFFFFF;
        border-radius: 24px;
        padding: 6px 18px;
    }
    QLabel#conduit_card_name_2 {
        color: %(GREEN)s;
    }
    QWidget#widget_7 {       /* 底部“预计时长”整条胶囊 */
        background: %(GREEN_DARK)s;
        border-radius: 22px;
        padding: 4px 12px;
    }
    QWidget#widget_7 QLabel {
        color: #FFFFFF;
    }
    """ % {"GREEN": _GREEN, "GREEN_DARK": _GREEN_DARK}

    _QSS_CHECKED = """
    QWidget#cardRoot {
        background: %(GREEN)s;
        border-radius: 28px;
        border: 0px solid transparent;
    }
    QLabel#conduit_card_id_2 {
        background: #FFFFFF;
        color: %(GREEN)s;
        border: 2px solid %(GREEN)s;
        border-radius: 24px;
        padding: 6px 18px;
    }
    QLabel#conduit_card_name_2 { color: #FFFFFF; }

    /* ★预计时长：白底 + 绿字（提高优先级，精确到对象名） */
    QWidget#cardRoot QWidget#widget_7 {
        background: #FFFFFF;
        border: 2px solid %(GREEN)s;
        border-radius: 22px;
        padding: 4px 12px;
    }
    /* 三个标签都变绿（expect_time / label / label_2） */
    QWidget#cardRoot QWidget#widget_7 QLabel,
    QLabel#expect_time,
    QLabel#label,
    QLabel#label_2 { 
        color: %(GREEN)s; 
    }
    """ % {"GREEN": _GREEN}

    _mk_font_family = None

    def __init__(self, bean, is_debug=False, parent=None):
        super().__init__(parent)
        self.ui = UiMaketeeCard()
        self.ui.setupUi(self)
        self._strip_inline_styles()
        self.is_debug = is_debug
        self.bean = None
        self._checked = False

        # 统一一个根节点名，样式只作用于本卡片
        try:
            self.ui.widget.setObjectName("cardRoot")  # ui 顶层容器 objectName=cardRoot
        except Exception:
            pass

        # 管理页的“对号”你已经去掉了，这里确保不显示
        for attr in ("conduit_card_mark_2", ):
            w = getattr(self.ui, attr, None)
            if w:
                w.setVisible(False)

        # 字体：编号/名称/底部“预计时长”三项统一阿里巴巴普惠体
        self._apply_puhuiti_font()

        # 首次数据/样式
        self.update_conduit_bean([bean])
        self._apply_style()

    def _strip_inline_styles(self):
        """移除 .ui 中对子控件的内联样式，避免覆盖选中态 QSS"""
        for name in ("conduit_card_id_2", "conduit_card_name_2", "widget_7"):
            w = getattr(self.ui, name, None)
            if w is not None:
                w.setStyleSheet("")

    # —— 交互：点击切换选中，并把信号抛给 Main（保持你的单选逻辑）——
    def mousePressEvent(self, e):
        self.setChecked(not self._checked)
        self.changed_conduit_card.emit(self._checked, self.bean)
        super().mousePressEvent(e)

    def setChecked(self, v: bool):
        self._checked = bool(v)
        self._apply_style()

    def isChecked(self) -> bool:
        return self._checked

    # —— 样式应用 —— 
    def _apply_style(self):
        if self._checked:
            self.ui.widget.setStyleSheet(self._QSS_CHECKED)
        else:
            self.ui.widget.setStyleSheet(self._QSS_BASE)
        # 强制刷新（有时能更快看到反转效果）
        self.ui.widget.style().unpolish(self.ui.widget)
        self.ui.widget.style().polish(self.ui.widget)
        self.ui.widget.update()
        # ★ 保险兜底：直接给三个 QLabel 设色，100% 覆盖
        green = self._GREEN if hasattr(self, "_GREEN") else "#2C9F61"
        if self._checked:
            color = green             # 选中：白底 -> 绿字
        else:
            color = "#FFFFFF"         # 未选中：绿底 -> 白字
        for name in ("expect_time", "label", "label_2"):
            w = getattr(self.ui, name, None)
            if w:
                w.setStyleSheet("color:%s;" % color)

    # —— 字体加载/应用（项目内加载，不依赖系统安装）——
    def _apply_puhuiti_font(self):
        from PyQt5.QtGui import QFontDatabase, QFont
        import os, sys

        fam = ConduitCardMaketeeWidget._mk_font_family
        if not fam:
            def _abspath(rel):
                bases = [os.getcwd(),
                         os.path.dirname(os.path.abspath(__file__)),
                         os.path.dirname(os.path.abspath(sys.argv[0]))]
                for b in bases:
                    p = os.path.join(b, rel)
                    if os.path.exists(p):
                        return p
                return rel

            candidates = [
                "fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf",
                "fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf",
            ]
            for rel in candidates:
                fid = QFontDatabase.addApplicationFont(_abspath(rel))
                if fid != -1:
                    fams = QFontDatabase.applicationFontFamilies(fid)
                    if fams:
                        fam = fams[0]
                        ConduitCardMaketeeWidget._mk_font_family = fam
                        break
        if not fam:
            # 兜底：若系统已安装过
            for tryname in ("Alibaba PuHuiTi", "Alibaba PuHuiTi 2.0", "Alibaba_PuHuiTi"):
                f = QFont(tryname)
                if f.family() != "Sans Serif":
                    fam = f.family()
                    ConduitCardMaketeeWidget._mk_font_family = fam
                    break

        id_font = QFont(fam) if fam else QFont()
        name_font = QFont(fam) if fam else QFont()
        small_font = QFont(fam) if fam else QFont()

        id_font.setPointSize(22)       # 左上编号
        id_font.setWeight(QFont.Medium)
        name_font.setPointSize(60)     # 中间名称
        name_font.setWeight(QFont.Medium)
        small_font.setPointSize(22)    # 预计时长三项

        self.ui.conduit_card_id_2.setFont(id_font)
        self.ui.conduit_card_name_2.setFont(name_font)
        for attr in ("expect_time", "label", "label_2"):
            w = getattr(self.ui, attr, None)
            if w:
                w.setFont(small_font)

    # —— 数据绑定 —— 
    @QtCore.pyqtSlot(list)
    def update_conduit_bean(self, beans):
        if not beans:
            return
        b = beans[0]
        self.bean = b

        # 编号
        raw_no = str(getattr(b, "conduit", "") or getattr(b, "conduit_no", "") or "")
        import re
        m = re.search(r"\d+", raw_no)
        self.ui.conduit_card_id_2.setText(f"#{int(m.group(0))}" if m else "#?")

        # 名称
        name = getattr(b, "name", "") or " "
        self.ui.conduit_card_name_2.setText(name)

        # ★ 新增：预计时长（数据库单位是“分钟”的整数/文本都兼容）
        et_raw = getattr(b, "expect_time", None)
        try:
            minutes = int(str(et_raw).strip()) if et_raw not in (None, "") else None
        except Exception:
            minutes = None
        self.ui.expect_time.setText(f"{minutes}min" if minutes is not None else "—")

    def retranslate_and_refresh(self):
        try:
            self.ui.retranslateUi(self)
        except Exception:
            pass
        try:
            if self.bean is not None:
                self.update_conduit_bean([self.bean])
        except Exception:
            pass



class _DownloadWorker(QThread):
    progress = pyqtSignal(int)
    done = pyqtSignal(object)   # (ok:bool, data:any)
    def __init__(self, url, tmp):
        super().__init__()
        self.url, self.tmp = url, tmp
    def run(self):
        try:
            download_file(self.url, self.tmp, progress_cb=lambda p:self.progress.emit(p))
            self.done.emit((True, self.tmp))
        except Exception as e:
            self.done.emit((False, str(e)))
def _toast(parent, text, msec=2000):
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import QTimer
        lab = QLabel(text, parent)
        lab.setObjectName("toast")
        lab.setAlignment(Qt.AlignCenter)
        lab.setStyleSheet("QLabel#toast{background:rgba(0,0,0,.78);color:#fff;padding:10px 18px;border-radius:12px;font-size:18px;}")
        lab.adjustSize()
        x = (parent.width() - lab.width())//2
        y = int(parent.height()*0.66) - lab.height()//2
        lab.move(max(12,x), max(12,y)); lab.show()
        QTimer.singleShot(msec, lab.deleteLater)
# --- 放在 Main1080Window 类中，位置随意 ---
def _force_qt_platform_plugins():
    sp = os.path.join(sys.prefix, "Lib", "site-packages")
    roots = [
        os.path.join(sp, "PyQt5", "Qt"),
        os.path.join(sp, "PyQt5", "Qt5"),
        os.path.join(sp, "qt5_applications", "Qt"),
    ]
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    os.environ.pop("QT_PLUGIN_PATH", None)

    qwindows = None
    for root in roots:
        plat = os.path.join(root, "plugins", "platforms", "qwindows.dll")
        if os.path.isfile(plat):
            qwindows = plat
            break

    if qwindows is None:
        for base, _, files in os.walk(sp):
            if "qwindows.dll" in files and base.replace("\\","/").endswith("/platforms"):
                qwindows = os.path.join(base, "qwindows.dll")
                break

    if qwindows:
        platforms = os.path.dirname(qwindows)
        plugins   = os.path.dirname(platforms)
        qtbin     = os.path.join(os.path.dirname(plugins), "bin")
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms
        os.environ["QT_PLUGIN_PATH"] = plugins
        if os.path.isdir(qtbin):
            os.environ["PATH"] = qtbin + os.pathsep + os.environ.get("PATH","")
        print("[Qt] plugins =", plugins)
        print("[Qt] platforms =", platforms)
    else:
        print("[Qt] 未找到 qwindows.dll")

_force_qt_platform_plugins()
# ---- then your other imports / QApplication ----

def normalize_drink_name(display_name: str) -> str:
    """
    去掉名字里第一个 - 及其后的所有部分。
    例: "大王奇异果 - 蔗糖" -> "大王奇异果"
        "杨枝甘露–三分糖" -> "杨枝甘露"
    """
    if not display_name:
        return ""
    # 按 - 或 – 分隔，只取前半段
    base = display_name.split(" - ")[0].split("–")[0]
    return base.strip()



import requests
from requests.exceptions import HTTPError

# ====== 菜单自动增量（Name+Recipe 唯一） ======
import json, os, re
from copy import deepcopy

# ====== 配方映射（分饮品） + 水/冰默认 ======
import os, json, re
from copy import deepcopy

# 路径：用你刚确认的 menu_xlsx 目录
def _menu_path():
    try:
        return _res_path(os.path.join("menu_xlsx", "tea_drinks_menu.json"))
    except Exception:
        return os.path.join(os.path.abspath("."), "menu_xlsx", "tea_drinks_menu.json")

def get_recipe_by_name(product_name: str) -> str:
    """根据产品名称从 tea_drinks_menu.json 获取配方"""
    if not product_name:
        return ""
    try:
        with open(_menu_path(), "r", encoding="utf-8") as f:
            items = json.load(f) or []
        for item in items:
            if item.get("Name", "").strip() == product_name.strip():
                return item.get("Recipe", "") or ""
    except Exception:
        pass
    return ""

def _backup_path():
    p = _menu_path()
    d, f = os.path.dirname(p), os.path.basename(p)
    return os.path.join(d, f.replace(".json", ".backup.json"))
def remove_menu_item_from_json(name: str) -> bool:
    """按 Name 从 tea_drinks_menu.json 删除对应条目。返回是否真的删除了。"""
    name = normalize_drink_name(name or "")
    if not name:
        return False

    mp = _menu_path()
    import json, os
    if not os.path.exists(mp):
        return False

    # 读原菜单
    with open(mp, "r", encoding="utf-8") as f:
        items = json.load(f) or []

    # 过滤掉 Name 命中的项（菜单文件的字段就是 Name）  :contentReference[oaicite:1]{index=1}
    new_items = [it for it in items if str(it.get("Name", "")).strip() != name]
    if len(new_items) == len(items):
        return False  # 没找到

    # 备份并写回
    try:
        with open(_backup_path(), "w", encoding="utf-8") as fbk:
            json.dump(items, fbk, ensure_ascii=False, indent=2)
    except Exception:
        pass
    with open(mp, "w", encoding="utf-8") as fw:
        json.dump(new_items, fw, ensure_ascii=False, indent=2)
    return True


# 同义词归一
ALIASES = {
    "海南芒果": "芒果",
    "台农芒果": "芒果",
    "金煌芒果": "芒果",
    "白砂糖": "蔗糖",
    "砂糖": "蔗糖",
}

# 默认追加
DEFAULT_WATER_ICE = {"水": 100, "冰": 100,"碎冰":100}   # 先都 100g

# 全局兜底（某些材料通用克重，如果某饮品未单独指定就用它；没有就忽略）
GLOBAL_GRAMS = {
    "蔗糖": 30,
    "西米": 40,
    "芒果": 80,
    "真果粒": 120,
    # "椰奶": 150, "柚子果肉": 30, ...
}


# ⭐ 分饮品克数映射：在这里为不同饮品细分
# 键 = 饮品名；值 = {材料: 克数}
DRINK_GRAMS = {
    "杨枝甘露": {
        "真果粒": 120,
        "西米": 40,
        "蔗糖": 25,   # 例：杨枝甘露里蔗糖 25
        "芒果": 90,
        # 水/冰不必写，这两个会在构建时自动追加为 100（也可在这里覆盖）
        # "水": 120, "冰": 80,
    },
    "椰椰杨枝甘露": {
        "真果粒": 100,
        "西米": 40,
        "蔗糖": 20,
        "芒果": 80,
        "椰奶": 120,
    },
    "大王奇异果":{
        "奇异果汁":100,
        "脆啵啵":30,
        "果糖":20,
        "蔗糖":20,
        "0脂糖":20,
    },
    "冰鲜柠檬水":{
        "柠檬":100,
        "0脂糖":20,
        "果糖":20,
        "蔗糖":20,
    },
    "棒打鲜橙":{
        "橙柚酱":40,
        "果糖":20,
        "蔗糖":20,
        "0脂糖":20,
    },
    "草莓啵啵":{
        "啵啵":40,
        "草莓果酱":40,
        "橙柚果酱":40,
        "红茶":100,
        "绿茶":100,
        "果糖":20,
        "蔗糖":20,
        "0脂糖":20,
    },
}

# ====== 预设每个饮品的小料后缀（不带前导下划线）======
DEFAULT_INGREDIENTS_BY_DRINK = {
    "草莓啵啵": "B050",
    "棒打鲜橙": "C050",  # 示例：真果粒(I)120、西米(H)040、蔗糖(C)025
    # ... 需要谁就填谁
}


FORCE_INGR_OVERRIDE = False

def _ingredients_for_name(name: str, old_item: dict | None):
    """
    返回要写入到 JSON 的 ingredients 字段：
      - FORCE_INGR_OVERRIDE=False 时：保留已有；没有才用默认表
      - FORCE_INGR_OVERRIDE=True  时：总是用默认表
    """
    preset = DEFAULT_INGREDIENTS_BY_DRINK.get((name or "").strip(), "")
    if FORCE_INGR_OVERRIDE:
        return preset
    if old_item and str(old_item.get("ingredients", "")).strip():
        return old_item.get("ingredients", "")
    return preset


DEFAULT_CUP_BY_DRINK = {
    "草莓啵啵": "成品杯",
    "棒打鲜橙": "雪克杯",
    # "黄桃果霸": "沙冰杯",
    # ... 需要谁就填谁
}

# 是否强制用上面的表覆盖菜单里已有的 cup
FORCE_CUP_OVERRIDE = False


def _cup_for_name(name: str, old_item: dict | None) -> str:
    """
    返回菜单里要写入的 cup 字段：
      - FORCE_CUP_OVERRIDE = False 时：
            先保留旧菜单里的 cup（如果有），没有再用 DEFAULT_CUP_BY_DRINK；
            都没有时兜底用“成品杯”
      - FORCE_CUP_OVERRIDE = True 时：
            不管旧菜单，直接用 DEFAULT_CUP_BY_DRINK，没有就“成品杯”
    """
    name = (name or "").strip()
    preset = DEFAULT_CUP_BY_DRINK.get(name, "").strip()

    if FORCE_CUP_OVERRIDE:
        return preset or "成品杯"

    # 先保留菜单中原有 cup 设置
    if old_item:
        old = str(old_item.get("cup", "")).strip()
        if old:
            return old

    # 没旧值就用默认表；再没有就成品杯兜底
    return preset or "成品杯"

# ====== /配置 ======

def _norm_formula_tokens(s: str):
    """'真果粒,西米;蔗糖;海南芒果' -> ['真果粒','西米','蔗糖','海南芒果']"""
    if not s:
        return []
    s = s.replace("，", ",").replace("；", ";").strip()
    toks = re.split(r"[,\;\s]+", s)
    return [t for t in (x.strip() for x in toks) if t]

def _alias(x: str) -> str:
    return ALIASES.get(x, x)

def _grams3(n: int) -> str:
    n = max(0, min(999, int(n)))
    return f"{n:03d}"

def _material_grams(drink_name: str, material: str) -> int | None:
    """
    分层查克数：优先用 DRINK_GRAMS[饮品][材料]；否则 GLOBAL_GRAMS；否则 None
    """
    dmap = DRINK_GRAMS.get(drink_name, {})
    if material in dmap:
        return dmap[material]
    if material in GLOBAL_GRAMS:
        return GLOBAL_GRAMS[material]
    return None

def build_recipe_string(drink_name: str, freeform_formula: str) -> str:
    """
    【功能】
    将“人工自由输入的饮品配方描述”，
    转换为“设备可执行的标准化出料配方字符串”。

    【典型输入】
    drink_name        : "杨枝甘露"
    freeform_formula  : "真果粒,西米;蔗糖;海南芒果"

    【典型输出】
    "真果粒120 西米040 蔗糖025 芒果090 水100 冰100"

    【核心规则说明】
    1. 支持用户随意输入（逗号/分号/空格混用）
    2. 自动进行材料同义词归一（如：海南芒果 → 芒果）
    3. 材料克重获取优先级：
       - 优先使用 DRINK_GRAMS[饮品名][材料]
       - 若无，再使用 GLOBAL_GRAMS[材料]
       - 若仍无，则忽略该材料（不写入配方）
    4. 每个材料输出格式固定为：
       - 材料名 + 三位克重（不足补零）
    5. 自动在末尾补齐“水 / 冰 / 碎冰”等基础材料：
       - 若饮品中有单独配置，用饮品配置
       - 否则使用 DEFAULT_WATER_ICE 中的默认值
       - 已存在的材料不会重复添加

    【设计目标】
    - 对人友好（输入随意）
    - 对机器严格（输出规范）
    - 保证每条配方都具备最小可执行结构
    """
    #解析 + 同义词归一 比如海南芒果 = 芒果
    tokens = [_alias(t) for t in _norm_formula_tokens(freeform_formula)]
    # 去重且保持顺序，例如真果粒，西米，真果粒-》真果粒，西米
    seen = set()
    toks = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            toks.append(t)

    out = []

    # 配方本体
    for t in toks:
        g = _material_grams(drink_name, t) #为每种材料查“标准可重” 查找规则是：先查 饮品专属配置 DRINK_GRAMS[drink_name][材料]再查 全局兜底配置 GLOBAL_GRAMS[材料] 都没有 → 忽略该材料
        if g is None:
            # 没配置的材料可选择忽略，或写 000；这里忽略更安全
            # out.append(f"{t}000")
            continue
        out.append(f"{t}{_grams3(g)}") #输出为“材料 + 三位数克重”

    # 追加水/冰（若饮品里写了具体克数，就以饮品为准；否则用 DEFAULT_WATER_ICE）
    for k, default_g in DEFAULT_WATER_ICE.items():
        g = _material_grams(drink_name, k)
        g = default_g if g is None else g
        # 避免重复（若上面因饮品配置已写过则跳过）
        if not any(x.startswith(k) for x in out):
            out.append(f"{k}{_grams3(g)}")

    return " ".join(out)

# 与你现有 JSON 字段对齐的模板
_TEMPLATE = {
    "Base Price": 12,
    "Sweetness Options": "常规,五分糖,三分糖",
    "Temperature Options": "少冰,正常冰,常温,热饮",
    "Size Options": "中杯,大杯",
    "Add-ons": "脆啵啵,芋圆,珍珠,椰果,果冻",
    "Price Calculation": "Final Price = Base Price * Size Factor + Add-ons Price",
}

def _next_id_str(items):
    mx = 0
    for it in items:
        try:
            mx = max(mx, int(str(it.get("ID","0")).strip()))
        except:
            pass
    return f"{mx+1:03d}"

def upsert_menu_item(name: str, freeform_formula: str, image_filename: str = None, base_price: int = None):
    """
    覆盖策略（满足你的新需求）：
    - 若已存在同名 Name -> 直接替换该条目的 Recipe / Image / Base Price（ID 保持不变）
    - 若不存在 -> 追加新条目（ID 递增）
    返回: (status, std_recipe)
      status: "replaced" | "created"
    """
    mp = _menu_path()
    if not os.path.exists(mp):
        raise FileNotFoundError(f"菜单文件不存在: {mp}")
    with open(mp, "r", encoding="utf-8") as f:
        menu = json.load(f)

    # 生成标准 Recipe（把自由配方转成“材料+三位数克重”的规范串；若失败就保底用原文本）
    std_recipe = build_recipe_string(name, freeform_formula).strip()
    if not std_recipe:
        std_recipe = (freeform_formula or "").strip()

    # 备份旧菜单
    try:
        with open(_backup_path(), "w", encoding="utf-8") as fbk:
            json.dump(menu, fbk, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # 查找是否已存在同名
    idx = None
    for i, it in enumerate(menu):
        if str(it.get("Name", "")).strip() == name.strip():
            idx = i
            break

    if idx is not None:
        # 覆盖：保留 ID，更新字段
        old = menu[idx]
        menu[idx] = {
            **old,
            "Name": name,
            "Base Price": base_price if base_price is not None else old.get("Base Price", _TEMPLATE["Base Price"]),
            "Sweetness Options": old.get("Sweetness Options", _TEMPLATE["Sweetness Options"]),
            "Temperature Options": old.get("Temperature Options", _TEMPLATE["Temperature Options"]),
            "Size Options": old.get("Size Options", _TEMPLATE["Size Options"]),
            "Add-ons": old.get("Add-ons", _TEMPLATE["Add-ons"]),
            "Price Calculation": old.get("Price Calculation", _TEMPLATE["Price Calculation"]),
            "Image": image_filename if image_filename else old.get("Image", f"{name}.png"),
            "Recipe": std_recipe,
            "ingredients": _ingredients_for_name(name, old),    # ★ 保留已有 ingredients
            "cup": _cup_for_name(name, old),  
        }
        with open(mp, "w", encoding="utf-8") as fw:
            json.dump(menu, fw, ensure_ascii=False, indent=2)
        return "replaced", std_recipe
    else:
        # 新增
        new_item = {
            "ID": _next_id_str(menu),
            "Name": name,
            "Base Price": base_price if base_price is not None else _TEMPLATE["Base Price"],
            "Sweetness Options": _TEMPLATE["Sweetness Options"],
            "Temperature Options": _TEMPLATE["Temperature Options"],
            "Size Options": _TEMPLATE["Size Options"],
            "Add-ons": _TEMPLATE["Add-ons"],
            "Price Calculation": _TEMPLATE["Price Calculation"],
            "Image": image_filename if image_filename else f"{name}.png",
            "Recipe": std_recipe,
            "ingredients": DEFAULT_INGREDIENTS_BY_DRINK.get(name, "") ,
            "cup": _cup_for_name(name, None),
        }
        menu.append(new_item)
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        with open(mp, "w", encoding="utf-8") as fw:
            json.dump(menu, fw, ensure_ascii=False, indent=2)
        return "created", std_recipe



def fetch_orders_query(site, ck, cs, after_iso):
    url = f"{site.rstrip('/')}/wp-json/wc/v3/orders"
    params = {
        "per_page": 20,          # ← 由 1 改 20，避免轮询间隔内漏单
        "orderby": "date",
        "order": "asc",          # ← 用升序，最早的先处理，游标更安全
        "after": after_iso,
        "consumer_key": ck,
        "consumer_secret": cs,
    }
    r = requests.get(url, params=params, timeout=(10, 60),
                     headers={"User-Agent":"PyQt-WooDebug/1.0"})
    try:
        r.raise_for_status()
    except HTTPError:
        print("[Woo][ERROR BODY][query]:", r.text)  # 打印服务器提示
        raise
    return r.json()

def fetch_orders_basic(site, ck, cs, after_iso):
    url = f"{site.rstrip('/')}/wp-json/wc/v3/orders"
    params = {
        "per_page": 20,          # ← 由 1 改 20，避免轮询间隔内漏单
        "orderby": "date",
        "order": "asc",          # ← 用升序，最早的先处理，游标更安全
        "after": after_iso,
        "consumer_key": ck,
        "consumer_secret": cs,
    }
    r = requests.get(url, params=params, auth=(ck, cs), timeout=(10, 60),
                     headers={"User-Agent":"PyQt-WooDebug/1.0"})
    try:
        r.raise_for_status()
    except HTTPError:
        print("[Woo][ERROR BODY][basic]:", r.text)
        raise
    return r.json()


class WooDebugThread(QThread):
    """
    每 poll_sec 秒请求一次 WooCommerce 订单，并把返回 JSON 发给主线程。
    只为“能收到就打印”的调试目标，不做去重与持久化。
    """
    got_text = pyqtSignal(str)   # 发字符串，便于直接显示/print
    menu_delta = pyqtSignal(dict)
    new_order_found = pyqtSignal(dict)
    

    def _read_local_account(self) -> str:
        """读取本地登录账号（登录成功后已由登录窗写入 QSettings）"""
        return (QSettings("Xiliu","Miketee").value("login/last_account","", type=str) or "").strip()

    def _resolve_customer_by_account(self, account: str):
        if not account:
            return None
        base = f"{self.site.rstrip('/')}/wp-json/wc/v3/customers"
        hdr  = {"User-Agent": "PyQt-WooDebug/1.0"}
        acc_l = account.strip().lower()

        # 1) 邮箱精确匹配
        try:
            if "@" in account:
                r = requests.get(base, params={
                    "email": account, "per_page": 1,
                    "consumer_key": self.ck, "consumer_secret": self.cs,
                }, headers=hdr, timeout=(10, 30))
                r.raise_for_status()
                arr = r.json() or []
                if arr:
                    u = arr[0]
                    return {"id": u.get("id"), "username": u.get("username"), "email": u.get("email")}
        except Exception as e:
            self.got_text.emit(f"[Woo][customer_lookup(email)] {e}")

        # 2) search 兜底（部分站点对 username 不灵，所以下面再做第3步）
        try:
            r = requests.get(base, params={
                "search": account, "per_page": 50,
                "consumer_key": self.ck, "consumer_secret": self.cs,
            }, headers=hdr, timeout=(10, 30))
            r.raise_for_status()
            for u in (r.json() or []):
                un = (u.get("username") or "").lower()
                em = (u.get("email") or "").lower()
                if un == acc_l or em == acc_l:
                    return {"id": u.get("id"), "username": u.get("username"), "email": u.get("email")}
        except Exception as e:
            self.got_text.emit(f"[Woo][customer_lookup(search)] {e}")

        # 3) 最终兜底：分页遍历 customers，并在本地比对 username/email
        try:
            page = 1
            while True:
                r = requests.get(base, params={
                    "per_page": 100, "page": page,
                    "consumer_key": self.ck, "consumer_secret": self.cs,
                }, headers=hdr, timeout=(10, 30))
                r.raise_for_status()
                arr = r.json() or []
                if not arr:
                    break
                for u in arr:
                    un = (u.get("username") or "").lower()
                    em = (u.get("email") or "").lower()
                    if un == acc_l or em == acc_l:
                        return {"id": u.get("id"), "username": u.get("username"), "email": u.get("email")}
                if len(arr) < 100:
                    break
                page += 1
        except Exception as e:
            self.got_text.emit(f"[Woo][customer_lookup(paginate)] {e}")

        return None


    def _order_belongs_to_me(self, order: dict, account: str, cust_id: int | None) -> bool:
        """二次兜底：确保订单确属当前账号"""
        if not account:
            return False
        if cust_id and order.get("customer_id") == cust_id:
            return True
        bill = order.get("billing") or {}
        # 邮箱匹配
        if "@" in account:
            em = (bill.get("email") or "").strip().lower()
            return em == account.lower()
        # 用户名无法直接从订单取到；尝试用手机号末尾匹配
        import re
        acc_digits = re.sub(r"\D+", "", account)
        phone = re.sub(r"\D+", "", bill.get("phone") or "")
        return bool(acc_digits and phone and (phone.endswith(acc_digits) or acc_digits.endswith(phone)))


    def __init__(self, site, ck, cs, poll_sec=5, parent=None):
        super().__init__(parent)
        self.site = site.rstrip("/")
        self.ck   = ck
        self.cs   = cs
        self.poll_sec = poll_sec
        # 只拉最近的（after=当前时间之前一点点，首次拉到最后一页最新）
        self.after_iso = (datetime.utcnow() - timedelta(days=1))\
                    .replace(microsecond=0).isoformat() + "Z"
        self.running = True
        self.target_device = ""
        self._asked_once = False
    # 规范化设备名：去掉“ (在线)”之类后缀
    @staticmethod
    def _norm_dev(s: str) -> str:
        if not s: return ""
        return re.sub(r"\s*\(.*\)$", "", str(s)).strip()

    def set_target_device(self, dev: str):
        self.target_device = self._norm_dev(dev)
        self.got_text.emit(f"[Woo] set_target_device -> {self.target_device}")

    @staticmethod
    def _order_device_from(order: dict) -> str:
        for m in order.get("meta_data", []):
            key = (m.get("key") or "").lower()
            if key in ("_xiliu_device", "xiliu_device"):
                return str(m.get("value") or "")
        return ""

    @staticmethod
    def _item_device_from(item: dict) -> str:
        for m in item.get("meta_data", []):
            key = (m.get("key") or "").lower()
            if key in ("_xiliu_device", "xiliu_device"):
                return str(m.get("value") or "")
        return ""

    def run(self):
        # 轮询间隔固定 5 秒
        self.poll_sec = 5

        # 已处理集合：按“订单ID + 行项目ID”去重（更精细，避免同一订单多商品重复）
        # 也可以换成只按订单ID去重：processed_orders = set()
        processed_items = set()


        # # 初始游标：回溯10分钟，避免第一次漏单
        # self.after_iso = (datetime.utcnow() - timedelta(minutes=10))\
        #                     .replace(microsecond=0).isoformat() + "Z"
        
        # —— 读取本地登录账号 —— 
        local_acc = self._read_local_account()
        if not local_acc:
            self.got_text.emit("[Woo] 本地未发现登录账号，停止拉单（只拉本人）")
            while self.running:
                time.sleep(self.poll_sec)
            return

        # —— 解析站点用户 —— 
        user = self._resolve_customer_by_account(local_acc)
        if not user:
            self.got_text.emit(f"[Woo] 账号 '{local_acc}' 在网站上未找到对应用户，停止拉单。")
            while self.running:
                time.sleep(self.poll_sec)
            return

        site_un = (user.get("username") or "").strip().lower()
        site_em = (user.get("email") or "").strip().lower()
        ok_same = (local_acc.lower() == site_un) or (local_acc.lower() == site_em)

        if not ok_same:
            self.got_text.emit(f"[Woo] 账号不一致：本地='{local_acc}'，网站用户=('{site_un}' / '{site_em}') → 停止拉单。")
            while self.running:
                time.sleep(self.poll_sec)
            return

        cust_id = int(user.get("id") or 0) or None
        self.got_text.emit(f"[Woo] 账号一致，customer_id={cust_id}，开始只拉该账号的订单。")

        while self.running:
            try:
                url = f"{self.site.rstrip('/')}/wp-json/wc/v3/orders"
                params = {
                    "per_page": 10,
                    "orderby": "date",
                    "order": "asc",          # 用升序，配合 after 游标自然前进
                    "after": self.after_iso,
                    # 如需用 query 认证（规避 Authorization 头丢失），打开下面两行并去掉 auth
                    # "consumer_key": self.ck,
                    # "consumer_secret": self.cs,
                }
                if cust_id:                     # ★ 服务端精确过滤“只此账号”
                    params["customer"] = cust_id

                r = requests.get(
                    url, params=params,
                    auth=(self.ck, self.cs),  # 如果你用上面的 query 认证，这里去掉 auth
                    headers={"User-Agent": "PyQt-WooDebug/1.0"},
                    timeout=(10, 60)
                )
                self.got_text.emit(f"[Woo] GET {r.url} -> {r.status_code}")
                r.raise_for_status()
                orders = r.json() or []


                if not orders:
                    # 没有新订单，等 5 秒再查
                    time.sleep(self.poll_sec)
                    continue

                # 记录这批里“最新”的创建时间，处理完再把 after_iso 往前推
                # 记下本批最新创建时间
                newest_gmt = None
                for order in orders:
                    oid = order.get("id")
                    gmt = order.get("date_created_gmt")
                    if gmt:
                        newest_gmt = gmt
                    
                    order_time_gmt = (order.get("date_created_gmt") or "").replace("Z","")

                    # ① 订单级设备（可能为空）
                    order_dev = self._norm_dev(self._order_device_from(order))

                    # ② 逐行项目处理（带去重与设备过滤）
                    for item in order.get("line_items", []):
                        item_id = item.get("id")
                        key = (oid, item_id)
                        if key in processed_items:
                            continue

                        # 行项目优先，其次回落到订单级
                        item_dev = self._norm_dev(self._item_device_from(item) or order_dev)

                        # 目标设备已设置时，仅处理匹配的
                        if self.target_device:
                            if not item_dev or (item_dev != self.target_device):
                                self.got_text.emit(
                                    f"[Woo][SKIP] oid={oid} item_dev='{item_dev}' != target='{self.target_device}'"
                                )
                                continue
                        # ===== 你的原解析：名称 & 配方 =====
                        raw_name  = item.get("name", "")
                        base_name = normalize_drink_name(raw_name)

                        vals = []
                        for meta in item.get("meta_data", []):
                            v = meta.get("value")
                            if v is not None and v != "":
                                vals.append(str(v))
                        formula = ";".join(vals)

                        # 判断是不是“今天下的单”
                        # 我们用本地时间来判断“今天”，可以简单用 UTC+0 当天即可
                        # （如果你要用本地时区，可以在这里加8小时再比对）
                        is_today = False
                        try:
                            # 解析订单创建时间为 datetime
                            from datetime import datetime
                            ts = order_time_gmt.split(".")[0]
                            odt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
                            # 当前 UTC 日期
                            now_utc = datetime.utcnow()
                            is_today = (odt.date() == now_utc.date())
                        except Exception as _e:
                            # 如果解析失败就当成“今天”，以便不漏单
                            is_today = True

                        # 把这个订单项标记成处理过（无论后面弹没弹窗）
                        processed_items.add(key)

                        # 如果已经问过主线程，后面就不再发弹窗，也不强制更新
                        # 不再用 _asked_once 拦截；由 UI 端排队逐一询问
                        if is_today:
                            payload = {
                                "order_id": oid,
                                "item_id": item_id,
                                "key": f"{oid}:{item_id}",   # ★ 唯一键
                                "drink_name": base_name,
                                "formula": formula,
                                "item_dev": item_dev,
                                "is_today": True,
                            }
                            self.got_text.emit(
                                f"[Woo][ASK] 今日下单 '{base_name}' dev={item_dev} formula='{formula}' key={payload['key']}"
                            )
                            self.new_order_found.emit(payload)
                        else:
                            self.got_text.emit(
                                f"[Woo][OLD] 历史订单 '{base_name}' dev={item_dev} (not today)"
                            )

                # 批处理完成后推进游标
                if newest_gmt:
                    # newest_gmt 形如 '2025-10-29T03:08:12' 或 '...Z'
                    ts = newest_gmt.replace("Z", "")
                    try:
                        dt = datetime.fromisoformat(ts)
                    except Exception:
                        # 兜底解析
                        dt = datetime.strptime(ts.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    # 往前推进 1 秒，避免同一秒重复拉取
                    nxt = (dt + timedelta(seconds=1)).replace(microsecond=0)
                    self.after_iso = nxt.isoformat() + "Z"
                    self.got_text.emit(f"[Woo] advance after -> {self.after_iso}")


            except Exception as e:
                self.got_text.emit(f"[Woo][ERROR] {e}")

            # 固定 5 秒轮询
            time.sleep(self.poll_sec)

    def stop(self):
        self.running = False


# 如果你项目里已有 db_util，就保持如下导入路径；没有就改成你的实际路径

# 绿主题弹窗（与现有UI风格一致）
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QSizePolicy,QGraphicsDropShadowEffect,QLayout
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


class _MenuRefreshBridge(QObject):
    """合并 Woo 线程里的多次 menu_delta，定时触发一次 commit() 刷新。"""
    commit = pyqtSignal(list)  # 刷新时把这段时间内变更过的饮品名列表带出去

    def __init__(self, parent=None, debounce_ms=350):
        super().__init__(parent)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(debounce_ms)
        self._debounce.timeout.connect(self._flush)
        self._pending_names = set()

    def on_menu_delta(self, payload: dict):
        name = (payload or {}).get("name")
        if name:
            self._pending_names.add(name)
        # 每次收到都重新计时（去抖）
        self._debounce.start()

    def _flush(self):
        if not self._pending_names:
            return
        names = sorted(self._pending_names)
        self._pending_names.clear()
        # 发出一次性的合并刷新
        self.commit.emit(names)

def _norm_txt(s: str) -> str:
    return (s or "").replace("，", ",").strip()

def _to_three(n: int, step: int = 5) -> str:
    if step > 1: n = int(round(n / step) * step)
    n = max(0, min(999, n))
    return f"{n:03d}"

def _index_to_letter(idx: int) -> str:
    # 1->A, 2->B, ...（最多到 26）
    return chr(ord('A') + int(idx) - 1)

def _parse_channel_index(conduit_value) -> int | None:
    """
    conduit 字段形如 '1#'、'02#'、'12#'；提取数字部分 1..26
    """
    if conduit_value is None:
        return None
    m = re.search(r'\d+', str(conduit_value))
    if not m:
        return None
    idx = int(m.group(0))
    return idx if 1 <= idx <= 26 else None



# ===================== 冰/碎冰专用：自动出冰开关（替代“屏蔽”） =====================
# 约定：通道 1# / 2#（物理冰、碎冰）的“屏蔽开关”不再参与“通道屏蔽”。
# - 开关 ON(绿色)  : 自动出冰（按配方输出液体+冰）
# - 开关 OFF(灰色) : 只输出配方液体，冰由人工添加；制作完成后提示“记得加冰”。
# 其它通道：开关仍按原语义 = “屏蔽通道”。
ICE_CONDUIT_IDXS = {1, 2}


def get_ice_channel_cfg_from_db():
    """返回 (ice_name_auto_map, ice_letters)

    ice_name_auto_map: {规范化材料名 -> 是否自动出冰}
      - 是否自动出冰：shield == '2' 视为 ON(绿色)
    ice_letters: {'A','B'} ... 便于字母配方过滤
    """
    try:
        rows = db_util.query_all_conduit_info() or []
    except Exception:
        rows = []

    name_auto = {}
    ice_letters = set()

    for row in rows:
        def g(k):
            if isinstance(row, dict):
                return row.get(k)
            return getattr(row, k, None)

        conduit_val = g('conduit') or g('channel') or g('channel_no')
        idx = _parse_channel_index(conduit_val)
        if idx not in ICE_CONDUIT_IDXS:
            continue

        name_val = g('name') or g('material_name') or g('title') or g('label')
        if not isinstance(name_val, str) or not name_val.strip():
            continue

        shield_val = str(g('shield') or '1')
        auto = (shield_val == '2')  # 绿色=ON
        name_auto[_norm_txt(name_val)] = auto
        ice_letters.add(_index_to_letter(idx))

    # fallback：老配方/默认命名
    if not name_auto:
        name_auto = { _norm_txt('冰'): True, _norm_txt('碎冰'): True }
        ice_letters = {'A', 'B'}

    return name_auto, ice_letters


def _match_any_name(key_norm: str, name_set_norm: set[str]) -> bool:
    """宽松匹配：完全相等 or 互为子串"""
    if not key_norm:
        return False
    for n in name_set_norm:
        if not n:
            continue
        if key_norm == n or (n in key_norm) or (key_norm in n):
            return True
    return False


def remove_materials_from_cjk_recipe(text_cjk: str, remove_names_norm: set[str]):
    """从中文配方中移除指定材料，返回 (new_text, removed_pairs)

    removed_pairs: [(raw_name, grams), ...]
    """
    pairs = parse_material_text_pairs(text_cjk or '')
    kept_parts = []
    removed = []
    for raw_name, val in pairs:
        key = _norm_txt(raw_name)
        if _match_any_name(key, remove_names_norm):
            removed.append((raw_name, val))
            continue
        kept_parts.append(f"{raw_name}{val}")
    return ' '.join(kept_parts).strip(), removed


def remove_letters_from_letter_recipe(text_letter: str, remove_letters: set[str]):
    """从字母配方中移除指定通道字母（例如 {'A','B'}），返回 (new_text, removed_tokens)"""
    s = (text_letter or '').strip()
    if not s:
        return s, []
    removed = []
    kept = []
    for m in re.finditer(r'([A-Z])(\d{3})', s):
        ch = m.group(1)
        gram = m.group(2)
        if ch in remove_letters:
            removed.append((ch, gram))
        else:
            kept.append(f"{ch}{gram}")
    return ' '.join(kept).strip(), removed
def get_name_to_letter_map_from_db() -> dict:
    """
    从 conduit_info 表构造 {材料名 -> 通道字母} 映射。
    需要字段：conduit（含数字编号） + name（材料名）
    """
    try:
        rows = db_util.query_all_conduit_info() or []
    except Exception as e:
        print("[ERR] 读取数据库失败：", e)
        rows = []

    name2letter = {}
    if not rows:
        print("[WARN] 数据库未返回任何通道记录。")
        return name2letter

    # rows 可能是 dict 或对象；统一取值
    for row in rows:
        def g(k):
            if isinstance(row, dict): return row.get(k)
            return getattr(row, k, None)

        conduit_val = g("conduit") or g("channel") or g("channel_no")
        name_val    = g("name") or g("material_name") or g("title") or g("label")
        shield_val  = str(g("shield") or '1')
        idx = _parse_channel_index(conduit_val)
        if not idx or not isinstance(name_val, str) or not name_val.strip():
            continue

        # 关键：屏蔽通道(shield=='2')在菜单/配方映射中视为“未绑定” → 相关饮品自动置灰。
        # 但通道 1#/2#（冰/碎冰）这里不再参与“屏蔽”，其开关仅作为“自动出冰”开关。
        if (idx not in ICE_CONDUIT_IDXS) and (shield_val == '2'):
            continue

        letter = _index_to_letter(idx)
        name2letter[_norm_txt(name_val)] = letter

    if not name2letter:
        print("[WARN] 数据库无 ‘材料名->通道’ 映射（检查 conduit_info.conduit/name 字段）")
    else:
        import time as _t
        last = getattr(get_name_to_letter_map_from_db, "_last_log", 0.0)
        now  = _t.time()
        if now - last > 30:  # 30 秒打一次
            print("[MAP] DB 映射：", name2letter)
            get_name_to_letter_map_from_db._last_log = now
    return name2letter

def get_letter_to_margin_map_from_db() -> dict[str, float]:
    """从 conduit_info 读出每个通道当前余量，返回 {字母通道: 余量g}"""
    try:
        rows = db_util.query_all_conduit_info() or []
    except Exception as e:
        print("[ERR] 读取数据库失败：", e)
        rows = []

    letter2margin = {}
    for row in rows:
        def g(k):
            if isinstance(row, dict): return row.get(k)
            return getattr(row, k, None)

        conduit_val = g("conduit") or g("channel") or g("channel_no")
        idx = _parse_channel_index(conduit_val)
        if not idx:
            continue
        letter = _index_to_letter(idx)
        try:
            margin = float(g("margin") or 0)
        except Exception:
            margin = 0.0
        letter2margin[letter] = margin
    return letter2margin


def parse_material_text_pairs(text: str):
    """
    '冰100 碎冰100 四季春茶020 糖浆100 蜂蜜100'
      -> [('冰',100), ('碎冰',100), ('四季春茶',20), ('糖浆',100), ('蜂蜜',100)]
    """
    s = _norm_txt(text)
    return [(m.group(1), int(m.group(2))) for m in re.finditer(r'([^\d\s]+)\s*(\d+)', s)]

def material_text_to_letter_recipe_via_db(text: str, step: int = 5):
    """
    用数据库映射把“中文配方”→“字母配方”；
    返回: (letter_recipe, ICE_dyn, SUGAR_dyn, missing_names)
    """
    pairs = parse_material_text_pairs(text)
    if not pairs:
        return "", set(), set(), {"<空配方>"}

    name2letter = get_name_to_letter_map_from_db()
    if not name2letter:
        return "", set(), set(), {"<数据库无映射>"}

    # 宽松匹配：最长子串优先（例如 name2letter 有“四季春茶”，配方写“春茶100”也能匹配）
    sorted_keys = sorted(name2letter.keys(), key=len, reverse=True)

    ice_name_auto_map, ice_letters = get_ice_channel_cfg_from_db()
    ice_names = set(ice_name_auto_map.keys()) or set(ICE_NAME_KEYS)


    tokens, ICE_dyn, SUGAR_dyn, missing = [], set(), set(), set()
    for raw_name, val in pairs:
        key = _norm_txt(raw_name)
        ch = name2letter.get(key)
        if not ch:
            for k in sorted_keys:
                if k in key or key in k:
                    ch = name2letter[k]; break
        if not ch:
            missing.add(key); continue

        if _match_any_name(key, ice_names):   ICE_dyn.add(ch)
        if any(k in key for k in SUGAR_NAME_KEYS): SUGAR_dyn.add(ch)

        tokens.append(f"{ch}{_to_three(val, step)}")

    tokens.sort(key=lambda t: t[0])  # 稳定输出
    return "".join(tokens), ICE_dyn, SUGAR_dyn, missing

def _floor_to_step(v: float, step: int) -> int:
    v = int(v)
    return (v // step) * step


import re

def _guess_water_letters(fallback_letter: str | None = "I") -> set[str]:
    """
    只识别“真实的水通道”，避免把“水蜜桃酱”等误判为水。

    识别规则（优先级）：
      1) name == "水"
      2) name in {"清水","纯净水"}
      3) name 符合 ^水\\d+$  (例如 水1、水2...)
    """
    exact_priority = []   # 最高优先：水/清水/纯净水
    waterN = []           # 次优先：水1、水2...

    try:
        name2letter = get_name_to_letter_map_from_db()
        for nm, ch in (name2letter or {}).items():
            n = str(nm).strip()

            if n == "水" or n in ("清水", "纯净水"):
                exact_priority.append(ch)
            elif re.match(r"^水\d+$", n):
                waterN.append(ch)

    except Exception:
        pass

    letters = set(exact_priority or waterN)

    if not letters and fallback_letter is not None:
        letters.add(fallback_letter)

    return letters



#少冰补水逻辑
def adjust_recipe_by_ice_sugar(recipe: str, ice_text: str, sugar_text: str, step: int = 5) -> str:
    if not recipe:
        return ""

    ice_mode  = _norm_txt(ice_text)          # 归一化后的冰档文本，例如 "少冰" / "正常冰" / "常温" / "热饮"
    sugar_mode = _norm_txt(sugar_text)

    ice_r   = ICE_RATIO.get(ice_mode,   1.0)
    sugar_r = SUGAR_RATIO.get(sugar_mode, 1.0)

    parts = re.findall(r'([A-Z])(\d{3})', recipe)
    if not parts:
        return ""

    used_letters = [ch for ch, _ in parts]
    used_ice   = set(used_letters) & ICE_CHANNELS
    used_sugar = set(used_letters) & SUGAR_CANDIDATES

    # 选“主冰路”= 在配方中出现顺序最靠前的那条冰通道
    primary_ice = None
    for ch, _ in parts:
        if ch in used_ice:
            primary_ice = ch
            break

    tmp = []
    # 主冰路在“步进取整后”的差值（只算这一条）
    primary_before_step = 0
    primary_after_step  = 0

    for ch, n3 in parts:
        v0 = int(n3)
        v  = v0

        if ch in used_ice:
            v_scaled = v0 * ice_r
            v = _floor_to_step(v_scaled, step)
            if ch == primary_ice:
                primary_before_step += v0          # 原来就是 step 的倍数
                primary_after_step  += v           # 取整后
        elif ch in used_sugar:
            v = _floor_to_step(v0 * sugar_r, step)

        tmp.append([ch, int(v)])

    # ★★ 只在“少冰”时，用减少的冰量补水；其他（正常冰/常温/热饮）不补水
    if primary_ice and ice_mode in ("少冰", "常温"):
        delta_ice = max(0, primary_before_step - primary_after_step)
    else:
        delta_ice = 0

    if delta_ice > 0:
        # 只从数据库中推断“水通道”（不使用硬编码兜底）
        water_letters_db = _guess_water_letters(fallback_letter=None)

        added = False
        # 1) 若配方里本来就有水通道：把 delta_ice 加到那条水通道上
        if water_letters_db:
            for i, (ch, v) in enumerate(tmp):
                if ch in water_letters_db:
                   tmp[i][1] = v + delta_ice
                   added = True
                   break

        # 2) 若配方里没有水通道：新增一条水通道，通道字母取“数据库水通道集合”的第一个
        if (not added) and water_letters_db:
            w = sorted(water_letters_db)[0]
            tmp.append([w, delta_ice])
            added = True

        # 3) 可选兜底：数据库根本没有配置任何“水”材料时，才退回固定通道（避免少冰补水丢失）
        if not added:
            tmp.append(["I", delta_ice])  # 如果你们项目默认清水不是 I，在这里改成对应字母

    return "".join(f"{ch}{_to_three(v, step)}" for ch, v in tmp)



def load_recipes(file_path): #未使用
    # 加载Excel文件
    df = pd.read_excel(file_path, index_col=0)  # 假设产品名称在第一列
    return df


def get_recipe(recipes, product_name): #未使用
    print("get_recipe")
    try:
        print(f"1:{recipes}")
        print(f"2:{product_name}")
        # 根据产品名称获取对应的配方
        recipe_row = recipes.loc[product_name]
        print(f"11:{recipe_row}")
        # 构造配方字符串 :A100B120C050，确保数字总是三位
        recipe_str = ''.join([f"{chr(65 + i)}{str(int(recipe_row[i])).zfill(3)}" for i in range(len(recipe_row)) if
                              not pd.isna(recipe_row[i])])
        print(f"22:{recipe_str}")

        return recipe_str
    except KeyError:
        return None  # 如果没有找到配方，则返回None
def _res_path(p: str) -> str:
    # 和弹窗那边一样的资源定位（兼容 PyInstaller）
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.join(os.path.abspath("."), p)


class Main1080Window(QWidget, Ui_Form):
    #定义大量的pyqtSignal。是为了对外广播状态变化，对内把 UI 操作转成后台线程可接收的事件，把后台线程的结果安全地带回 UI 主线程
    no_changed_menu_broad = pyqtSignal()
    change_menu_config_broad = pyqtSignal(str)
    close_order = pyqtSignal(int, TeeBean)
    order_control_refresh = pyqtSignal()
    no_changed_order_broad = pyqtSignal()
    notice_conduit_card = pyqtSignal(list)
    clean_begin_notice = pyqtSignal(list,int)
    clean_pause_notice = pyqtSignal(bool)
    clean_stop_notice = pyqtSignal()
    setting_local_tee_record_page_btn_no_check = pyqtSignal(int)
    setting_local_message_record_page_btn_no_check = pyqtSignal(int)
    setting_local_tee_record_notice_restore = pyqtSignal()
    notice_main_item_conduit = pyqtSignal(list)
    notice_maketee_item_conduit = pyqtSignal(list)   # 泡茶页更新信号（独立于管理页）
    notice_item_conduit = pyqtSignal(list)
    notice_make_tee_result = pyqtSignal(list)
    notice_thread_tee_begin = pyqtSignal()
    notice_thread_tee_stop = pyqtSignal()
    make_tee_notice_data = pyqtSignal(str)   #把配方字符串发给后台线程
    make_tee_camera_data = pyqtSignal(str)
    #串口
    notice_thread_serial_stop = pyqtSignal()###
    notice_thread_serial_stop_2 = pyqtSignal()
    # 退出关闭线程
    notice_close_thread = pyqtSignal()
    close_camera = pyqtSignal()
    # 扫码图标显示
    notice_camera_scan_show = pyqtSignal(bool)
    #管理按钮
    conduit_manager_out = pyqtSignal(str,list,str)
    conduit_manager_all = pyqtSignal(str,list)
    conduit_manager_one = pyqtSignal(str,list)
    #清洗
    # clean_l_date = pyqtSignal(str)
    clean_T = pyqtSignal(int)
    #订单卡片
    order_card_style = pyqtSignal()

    def __init__(self, app, parent=None):
        super(Main1080Window, self).__init__(parent)
        print(sys.executable)  # 输出当前 Python 解释器路径
        self._zip4_map = self._load_zip4_map(_res_path("data/cn_zip4_map_big.csv"))
        self.camera_frame_ui = None
        self.message_info_ui = None
        self.ip_thread = None
        self.keyboard_thread = None
        self.camera_thread = None
        self.tee_recipe = ''
        self.notice_order_complete_thread = None
        self.order_dialog_1_ui = None
        self.setting_conduit_content_Layout = None
        self.setting_conduit_gridLayout = None
        self.manager_main_conduit_thread = None
        self.second_screen_ui = None
        self.setting_local_message_page_Layout = None
        self.refresh_setting_local_message_thread = None
        self.setting_message_content_Layout = None
        self.setting_local_tee_page_Layout = None
        self.setting_order_content_Layout = None
        self.refresh_setting_local_tee_thread = None
        self.refresh_order_content_thread = None
        self._language_page_created = False
        self.save_order_db_thread = None
        self.save_message_db_thread = None
        self.today_product_id = 0
        self.order_thread = None
        self.login_ui = None
        self.time_management = None
        self.clean_week_ui = None
        self.clean_day_ui = None
        self.clean_load_Layout = None
        self.manager_keyboard_ui = None
        self.manager_conduit_gridLayout = None
        self.notice_ui = None
        self.language_settings_widget = None
        self.conduit_gridLayout = None
        self.conduit_content_Layout = None
        self.order_gridLayout = None
        self.order_content_Layout = None
        self.conduit_thread = None
        self.menu_gridLayout = None
        self.menu_content_Layout = None
        self.menu_tee_bean_thread = None
        #串口
        self.conduit_serial_thread = None   ###
        self.serial_thread = None  ###
        self.com1 = 'COM7'  #连接esp32的端口号    这里修改端口号
        self.com2 = 'COM5'  #摄像头对应的端口号
        #conduit的id
        self.conduit_id_num = 25   ###    管道数量

        #当前时间
        self.current_time = ""
        self.complete_time = ""
        self.clean_l_date_min = 00
        self.clean_l_date_sec = 00

        # 清洗顺序控制（每日清洗专用）
        self._daily_clean_channels = [
            "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"
        ]
        self._daily_clean_value = 100
        self._daily_clean_pump_delay_ms = 1000
        self._daily_clean_channel_seconds = 30
        self._daily_clean_stop_delay_ms = 1000
        self._clean_seq_active = False
        self._clean_seq_paused = False
        self._clean_seq_index = 0
        self._clean_seq_token = 0
        self._clean_seq_current_channel = ""

        self.maketee_conduit_gridLayout = None      # 泡茶页网格（若你已创建则跳过）
        self.maketee_conduit_num = 0                # 泡茶页计数（独立于 self.conduit_num）
        self.maketee_conduit_card_widgets = []      # 泡茶页卡片列表

        # 允许多选：管理页选中通道集合，形如 {'1#','3#',...}
        self._mgr_selected_cids = set()
        # 兼容旧代码：按钮里仍读取 select_conduit_bean
        self.select_conduit_bean = []
        #扫码的数据
        self.camera_data = []

        self.setupUi(self)

        self._lang_mgr = LanguageManager(app)
        self._lang_mgr.apply(self._lang_mgr.get_lang())
        # self._brew_timer = QTimer(self); self._brew_timer.timeout.connect(self._on_brew_tick)


         # === 杯型图标 & cup 缓存 ===
        self.icon_cup_finished = QtGui.QIcon(':/icon/Finished_Cup.png')
        self.icon_cup_shaker   = QtGui.QIcon(':/icon/Shaker_Cup.png')
        self.icon_cup_smoothie = QtGui.QIcon(':/icon/Smoothie_Cup.png')
        self._cup_by_drink = {}      # {饮品名(规整后): cup字符串}


        btn = getattr(self, "btn_begin_make", None)
        if btn is not None:
            print("[CupDebug] init: btn_begin_make.icon().isNull =",
                  btn.icon().isNull())

        # 让进度条能显示文字（如果你还没开）
        try:
            self.progressBar.setTextVisible(True)
        except Exception:
            pass

        # 创建控制器，并把串口传进去
        self.maketee_ctl = MaketeeController(ui=self, serial_thread=self.conduit_serial_thread)

        # 把【泡茶】按钮交给控制器（你的按钮名是 btn_maketee_out）
        self.maketee_ctl.wire_buttons(self.btn_maketee_out)

        for sw in (
            getattr(self, "stackedWidget", None),
            getattr(self, "stackedWidget_2", None),
            getattr(self, "stackedWidget_clean", None),
            getattr(self, "stackedWidget_setting", None),
        ):
            if sw:
                sw.currentChanged.connect(lambda *_: self._close_small_keyboard())

        self._low_stock_notified = set()         # 已提醒过的通道，避免反复弹
        self.low_stock_timer = QtCore.QTimer(self)
        self.low_stock_timer.setInterval(1_000) # 10s 查一次
        self.low_stock_timer.timeout.connect(self._check_low_stock_popup)
        self.low_stock_timer.start()
        QtCore.QTimer.singleShot(500, self._check_low_stock_popup)  # 启动时先查一次

        # 允许“离开手动出茶页也刷新菜单”
        self._menu_offpage_refresh = True

        # === 选中/刷新状态管理（新增） ===
        self.select_order_tee_bean = None         # 当前选中的饮品
        self.selected_order_id = None             # 用于刷新后的选中还原（假设 bean 有 id 字段）
        self.order_card_widgets = []              # 当前渲染出的卡片列表
        self._refresh_locked = False              # 制作期间暂停刷新，防止选中被冲掉

        # --- 制作完成小贴士（tips）相关 ---
        self._tips_by_drink = {}
        self._current_make_drink_name = ""
        self._current_make_tips = ""

        # 从菜单 JSON 中预加载每个饮品对应的 tips
        try:
            menu_path = _menu_path()
            import json, os
            if os.path.exists(menu_path):
                with open(menu_path, "r", encoding="utf-8") as f:
                    items = json.load(f) or []
                for item in items:
                    name = str(item.get("Name", "")).strip()
                    tips = str(item.get("tips", "")).strip()
                    if name and tips:
                        self._tips_by_drink[name] = tips
                print(f"[TipsDebug] 加载 tips 完成，共 {len(self._tips_by_drink)} 条")
            else:
                print(f"[TipsDebug] 菜单文件不存在：{menu_path}")
        except Exception as e:
            import traceback; traceback.print_exc()
            print("[TipsDebug] 加载 tips 失败：", e)

        self.maketee_selected_row = None    # 泡茶页当前选中的配方（bean/row）

        self._ice_locking_dlg = None   # 记住“正在自动摆脱中”的弹窗

        # 手动把按钮点击连接到已有的槽函数
        # self.btn_maketee_out.clicked.connect(self.on_maketee_brew_clicked)

        # 简单的UI标签显示调试文本（放到你能看见的位置；不合适就只用 print）
        self.debug_last_msg = QLabel("Woo 调试：尚未连接")
        self.debug_last_msg.setStyleSheet("color:#1FA463; font-size:16px;")
        try:
            # 如果你有合适的布局容器，就 addWidget；没有就先忽略这两行
            self.order_content_Layout.addWidget(self.debug_last_msg)
        except Exception:
            pass
        # 启动 Woo 调试线程
        self.woo_dbg = WooDebugThread(WC_SITE, WC_CK, WC_CS, poll_sec=5, parent=self)
        self.woo_dbg.got_text.connect(self._on_woo_debug_text)
        # self.woo_dbg.menu_changed.connect(self._refresh_manual_menu)  # ← 新增
        # 去抖合并器：线程 -> 合并 -> 主窗体刷新
        self._menu_refresh = _MenuRefreshBridge(self, debounce_ms=350)
        self.woo_dbg.menu_delta.connect(self._menu_refresh.on_menu_delta, type=Qt.QueuedConnection)
        self._menu_refresh.commit.connect(self._refresh_manual_menu, type=Qt.QueuedConnection)
        self.woo_dbg.start()

        from collections import deque
        from pathlib import Path
        # —— 今日“已提示”集合（持久化）——
        self._seen_file = Path.home() / ".xiliu_seen_today.json"
        self._seen_set = set()      # 当日已提示 { "oid:item_id", ... }
        self._seen_date = None
        self._load_seen_today()     # 读取/重置

        # 让 Woo 线程把"发现的新订单"回调到主界面‘

        self._woo_popup_queue = deque()     # 待询问的饮品队列
        self._woo_popup_active = False      # 是否正在弹窗中（防并发）
        self.woo_dbg.new_order_found.connect(self._on_new_order_found_from_woo)

        # menu_delta 仍然需要桥，保持你原来的连接
        self._menu_bridge = _MenuRefreshBridge(self)
        self.woo_dbg.menu_delta.connect(self._menu_bridge.on_menu_delta)
        self._menu_bridge.commit.connect(self._refresh_manual_menu)


        self.menu_config_number_l.setHidden(True)
        self.menu_config_del_btn.setHidden(True)
        self.menu_config_add_btn.setHidden(True)
        self.setGeometry(0,0,1920,1080)
        # 隐藏原店名展示
        self.init_store_name()
        self.label.setHidden(True)
        self.l_title_name.setHidden(True)
        # self.label_10.setHidden(True)
        self.label_42.setHidden(True)
        # self.label_11.setHidden(True)

        # 主菜单按钮状态
        self.wbtn_menu_outtee_isChecked = True
        self.wbtn_menu_manager_isChecked = False
        self.wbtn_menu_maketee_isChecked =False
        self.wbtn_menu_clean_isChecked = False
        self.wbtn_menu_setting_isChecked = False

        # 登录成功后的信息存储
        self.token = ''
        self.phone_number = ''
        self.store_id = ''
        self.nickname = ''

        # 出茶自动开关按钮状态
        self.auto_isChecked = False

        # 出茶界面通知
        self.is_create_notice = False
        # 管理界面键盘
        self.is_create_keyboard = False
        # 管理界面输入拼接
        self.line_context = ''

        self.lineEdit_2.installEventFilter(self)
        self.lineEdit_2.setReadOnly(True)
        self._kb = None              # 当前键盘实例
        self._kb_target = None       # 当前键盘绑定的目标 QLineEdit
        self._kb_last_close_ms = 0   # 上次关闭时间(ms)

        # 扫码出茶按钮和手动出茶按钮
        self.wbtn_scan_code_outtee_isChecked = True
        self.wbtn_mt_outtee_isChecked = False

        # 所有消息信息
        self.all_message_bean_list = []
        # 记录消息共多少页
        self.message_record_page_count = 0
        # 记录消息当前页
        self.setting_local_message_record_current_page = 0

        # 设置界面订单茶信息 完成状态 和 缺料状态
        self.is_complete = True
        self.btn_setting_out_tee.setHidden(False)
        self.complete_tee_bean_list = []
        self.lack_tee_bean_list = []
        # 选中的取料状态的茶
        self.check_tee_bean = None

        # 记录订单共多少页
        self.tee_record_page_count = 0
        # 记录订单当前页
        self.setting_local_tee_record_current_page = 0

        # 存购物车 奶茶对象
        self.menu_add_shopping_cart_beans = []
        # 管道对象集合
        self.conduit_beans = []
        self.conduit_num = 0
        # 菜单点单编号
        self.menu_order_take_sn = 1
        # 菜单集合
        self.menu_tee_beans = []
        self.menu_num = 0
        # 订单选中的对象
        self.select_order_tee_bean = None
        #未屏蔽的对象 工作时的对象
        self.work_conduit_bean = []
        #未屏蔽的数量
        self.conduit_work_number = 0
        # 管道 card 选中对象
        self.select_conduit_bean = []
        # 裸杯 单价
        self.menu_tee_price = 0.00
        # 份量 1 中  2 大
        self.menu_weight_value = '1'
        # 糖量 1 常  2 5分  3 3分
        self.menu_sugar_value = '1'
        # 温度 1 少冰  2 正常冰  3 常温
        self.menu_ice_value = '2'
        # 小料
        self.is_cbb = False
        self.is_yg = False
        self.is_zz = False
        self.is_yy = False
        self.is_mgd = False

        self.T = 2160       #清洗总时间
        self.interval = 30  #一组清洗秒数
        self.count = 12     #清洗次数
        self.is_day = True  #日洗

        self.is_show = True    #控制扫码图标的显示
        # 新增一个 QLabel
        self.inner_label = QLabel()  #扫码文字的显示存放

        # 设置窗体无边框 设置背景透明
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.add_btn_none_style = QtGui.QIcon()
        self.add_btn_none_style.addPixmap(QtGui.QPixmap(":/icon/ic_menu_add_cart_btn.png"), QtGui.QIcon.Normal,
                                          QtGui.QIcon.Off)
        self.add_btn_have_style = QtGui.QIcon()
        self.add_btn_have_style.addPixmap(QtGui.QPixmap(":/icon/add_1.png"), QtGui.QIcon.Normal,
                                          QtGui.QIcon.Off)
        # 检测屏幕
        self.screens_list = app.screens()
        print(f'检测到{len(self.screens_list)}屏幕')
        for screen in self.screens_list:
            print(f'screen:{screen.size()}')
            print(f'screen:{screen.geometry()}')
        # 副屏是否开启
        self.is_open_screen = False

        # 初始化今日取茶号
        self.today_id = 1

        # 初始化扫码界面的管道展示
        self.init_conduit_card_widget()
        self.init_maketee_conduit_control() 

        # 初始化未登录时所有状态
        self.is_login = False
        self.is_debug = False
        self.init_not_login_in_state()

        # 更改登录状态界面显示
        self.switch_login_init(self.is_login)
        self.switch_debug_init(self.is_debug)

        # 初始化时间
        self.init_date_time()

        # 清洗界面 日洗 周洗 开始暂停 切换锁定判断
        self.is_start = False
        # 清洗界面 日洗界面初始化
        self.init_clean_day_widget()

        # 初始化自定义按钮和字体
        self.init_custom_btn()
        self.init_font()

        # 初始化相机框
        self.init_camera_frame()

        # 加载菜单
        self.init_menu_card_widget()
        self.load_menu_xlsx()


        # 10s 轮询缺料并立即跑一次
        self.menu_check_timer = QTimer(self)
        self.menu_check_timer.timeout.connect(self._poll_menu_availability)
        self.menu_check_timer.start(10000)
        QTimer.singleShot(0, self._poll_menu_availability)

        # 初始化动态GUI
        self.init_order_card_widget()

        # 初始化设置菜单中的管道界面
        self.init_setting_conduit_widget()
        self.init_language_settings_page()
        #串口初始化
        self.init_conduit_serial_thread()###
        # self.conduit_serial_thread.material_detected.connect(self.on_material_detected)
        #数据库更新begin_time
        self.update_begin_time_info(self.conduit_id_num+1)### 实际+1


        # #管理按钮设置为可勾选
        # self.btn_manager_out.setCheckable(True)
        # self.btn_manager_all.setCheckable(True)
        # self.btn_manager_one.setCheckable(True)

        # 手动出茶菜单
        self.scrollArea.verticalScrollBar().setVisible(False)
        self.scrollArea.horizontalScrollBar().setVisible(False)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_2.verticalScrollBar().setVisible(False)
        self.scrollArea_2.horizontalScrollBar().setVisible(False)
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollArea_2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_3.verticalScrollBar().setVisible(False)
        self.scrollArea_3.horizontalScrollBar().setVisible(False)
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollArea_3.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_4.verticalScrollBar().setVisible(False)
        self.scrollArea_4.horizontalScrollBar().setVisible(False)
        self.scrollArea_4.setWidgetResizable(True)
        self.scrollArea_4.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_5.verticalScrollBar().setVisible(False)
        self.scrollArea_5.horizontalScrollBar().setVisible(False)
        self.scrollArea_5.setWidgetResizable(True)
        self.scrollArea_5.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_6.verticalScrollBar().setVisible(False)
        self.scrollArea_6.horizontalScrollBar().setVisible(False)
        self.scrollArea_6.setWidgetResizable(True)
        self.scrollArea_6.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_7.verticalScrollBar().setVisible(False)
        self.scrollArea_7.horizontalScrollBar().setVisible(False)
        self.scrollArea_7.setWidgetResizable(True)
        self.scrollArea_7.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_8.verticalScrollBar().setVisible(False)
        self.scrollArea_8.horizontalScrollBar().setVisible(False)
        self.scrollArea_8.setWidgetResizable(True)
        self.scrollArea_8.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 触屏滚动
        QScroller.grabGesture(self.scrollArea.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(self.scrollArea_2.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(self.scrollArea_3.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(self.scrollArea_4.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(self.scrollArea_5.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(self.scrollArea_6.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(self.scrollArea_7.viewport(), QScroller.LeftMouseButtonGesture)

        # 刷新本地记录 奶茶记录
        self.init_setting_order_content_widget()
        self.init_setting_order_content_page_btn_widget()

        # 刷新本地消息记录
        self.init_setting_message_content_widget()
        self.init_setting_message_content_page_btn_widget()

        # 映射：饮品名 -> 卡片控件；饮品名 -> Bean；禁用集合与缺料明细
        self.menu_cards_by_name = {}
        self.menu_beans_by_name = {}
        self._disabled_menu_names = set()
        self._missing_names_by_name = {}

        fid = QFontDatabase.addApplicationFont(
            r"F:\Lyq\miketee4(1080)_4.0.7\fonts\AlibabaPuHuiTi-3\AlibabaPuHuiTi-3-55-Regular\AlibabaPuHuiTi-3-55-Regular.ttf"
        )
        if fid != -1:
            fam = QFontDatabase.applicationFontFamilies(fid)[0]
            # 如果你的控件在 self.ui 下，就把 self.label_3 改成 self.ui.label_3，下面同理。
            for w in (self.label_3, self.label_5,self.progressBar):
                f = w.font()      # 保留原字号等属性
                f.setFamily(fam)  # 只换成阿里巴巴普惠体
                w.setFont(f)
        # 管理管道 清洗 校验 出料
        # self.conduit_clear_thread = ConduitClearThread()
        # self.conduit_clear_true.connect(self.conduit_clear_thread.open_clear)
        # self.conduit_clear_false.connect(self.conduit_clear_thread.close_clear)
        # self.conduit_clear_thread.auto_clear_close.connect(self.clear_auto_close)
        # self.conduit_clear_thread.auto_calibration_close.connect(self.calibration_auto_close)
        # self.conduit_clear_thread.auto_material_close.connect(self.material_auto_close)
        # self.conduit_clear_thread.data_received.connect(self.callBack_make_tee_result)
        # self.make_tee_notice_data.connect(self.conduit_clear_thread.send_data)
        # self.notice_thread_tee_begin.connect(self.conduit_clear_thread.make_tee_open)
        # self.notice_thread_tee_stop.connect(self.conduit_clear_thread.make_tee_stop)
        # self.conduit_clear_thread.result_info.connect(self.callBack_conduit_info_from_usb)
        # self.conduit_clear_thread.start()    

          # 只在程序启动或登录成功后执行一次
        self.next_take_no = db_util.query_today_order_count() + 1       # 取茶号（当日订单数量+1）
        # self.next_product_no = db_util.query_today_tea_quantity() + 1   # 奶茶流水号（当日饮品数量+1） 
        self._init_daily_serials()
        self._log_db_and_serials("__init__ done")
        print("btn_begin_make icon is null? ",
            self.btn_begin_make.icon().isNull())

               
    def init_conduit_serial_thread(self):   ###
        self.conduit_serial_thread = ConduitSerialThread(self.com1)
        # 线程信号连接
        self.conduit_serial_thread.material_detail_detected.connect(self.on_material_packet)
        self.conduit_manager_out.connect(self.conduit_serial_thread.conduit_serial_out) #管理界面_出料
        self.conduit_manager_all.connect(self.conduit_serial_thread.conduit_serial_all) #管理界面_一键满管
        self.conduit_manager_one.connect(self.conduit_serial_thread.conduit_serial_one) #管理界面_单管满管
        self.conduit_serial_thread.mA_info.connect(self.callBack_make_tee_result)  #  进度条传递运行中的电机数组
        self.make_tee_notice_data.connect(self.conduit_serial_thread.send_data)   # 发送到串口的重量信息
        self.notice_thread_tee_begin.connect(self.conduit_serial_thread.make_tee_open) #开始制作 对应的后端控制
        self.notice_thread_tee_stop.connect(self.conduit_serial_thread.make_tee_stop)  #取消   对应的后端控制
        self.notice_thread_serial_stop.connect(self.conduit_serial_thread.stop)     #退出后关闭串口
        self.conduit_serial_thread.weights_info.connect(self.callBack_conduit_info_from_usb)   #将从后端的重量信息传到数据库
        self.conduit_serial_thread.ice_locking.connect(self.on_ice_locking)
        self.conduit_serial_thread.ice_locked.connect(self.on_ice_locked)
        self.conduit_serial_thread.ice_unlock_finished.connect(self.on_ice_unlock_finished)

        self.conduit_serial_thread.temp_changed.connect(self.on_temp_changed)
        self._cur_temp = None
        self._heat_target = None
        self._heat_start = None
        self._maketee_row = None         # 选中的“泡茶卡片”对应 DB 行
        self._brew_liters = 0.0          # 编辑框输入的 L
        self._brew_seconds_left = 0


        # # 和串口线程连上
        # self.conduit_serial_thread.temp_changed.connect(self._on_temp)         # 温度刷新
        # self.conduit_serial_thread.temp_finished.connect(self._on_temp_finish) # 加热完成


        self.clean_begin_notice.connect(self.conduit_serial_thread.conduit_serial_clean_begin)  #清洗开始后端
        self.clean_pause_notice.connect(self.conduit_serial_thread.conduit_serial_clean_pause)  #清洗暂停
        self.clean_stop_notice.connect(self.conduit_serial_thread.conduit_serial_clean_stop)    #清洗停止
        self.clean_T.connect(self.clean_day_ui.clean_T)    #总时长 日洗
        self.clean_day_ui.clean_min_sec.connect(self.conduit_serial_thread.conduit_serial_clean_time)  #剩余时间，传到后端
        self.clean_day_ui.clean_min_sec.connect(self.notice_clean_time)   #剩余时间， 由前端传到main
        # 
        self.clean_T.connect(self.clean_week_ui.clean_T)   ##总时长 周洗
        self.clean_week_ui.clean_min_sec.connect(self.conduit_serial_thread.conduit_serial_clean_time)  #剩余时间，传到后端
        self.clean_week_ui.clean_min_sec.connect(self.notice_clean_time)   #剩余时间， 由前端传到main

        self.serial_thread = SerialThread(self.com2)
        self.notice_thread_serial_stop_2.connect(self.serial_thread.stop)     #退出后关闭串口
        self.make_tee_camera_data.connect(self.conduit_serial_thread.send_data)

        self.conduit_serial_thread.material_detected.connect(self.on_material_detected)

    def _on_woo_debug_text(self, text: str):
        print(text)  # 直接打印到控制台
        try:
            if hasattr(self, "debug_last_msg") and self.debug_last_msg:
                self.debug_last_msg.setText(text)
        except Exception:
            pass
    
    @pyqtSlot(float)
    def on_temp_changed(self, t: float):
        # 若 lcdNumber 允许显示小数，直接 display 即可
        try:
            self.lcdNumber.display(f"{t:.2f}")  # 37.55
        except Exception:
            # 容错：万一对象名不同或类型非 float
            self.lcdNumber.display(str(t))

    def _set_status(self, text: str):
        # 顶部“空闲中.../加热中.../浸泡中...”文案
        # 假设有 self.label_5，若你的对象名不同改成实际对象
        try:
            self.progressBar.setformat(text)
        except Exception:
            pass

    def _on_temp(self, t: float):
        # 正在加热 → 计算百分比
        if self._heat_target is not None:
            if self._heat_start is None:
                self._heat_start = self._cur_temp
            span = max(1.0, float(self._heat_target) - float(self._heat_start))
            pct = int(max(0.0, min(100.0, (self._cur_temp - self._heat_start) / span * 100)))
            try:
                self.progressBar.setValue(pct)
            except Exception:
                pass
            self._set_status(f"加热中......{pct}%")

    def closeEvent(self, e):
        try:
            self.notice_close_thread.emit()
        except Exception:
            pass

        for name in ["maketee_thread", "conduit_thread", "menu_tee_bean_thread",
                    "serial_thread", "conduit_serial_thread", "woo_thread"]:
            th = getattr(self, name, None)
            if th and th.isRunning():
                try:
                    if hasattr(th, "stop"): th.stop()
                    th.quit()
                    th.wait(800)
                except Exception:
                    pass
        super().closeEvent(e)

    def start_conduit_serial_thread(self):
        if self.conduit_serial_thread:
            self.conduit_serial_thread.start()  # 启动串口线程
        if self.serial_thread:
            self.serial_thread.start()

    def init_store_name(self):
        self.l_title_store_name.setHidden(True)
        self.l_title_store_name_2.setHidden(False)
        # self.l_title_store_name_2.setReadOnly(True)
        self.ip_thread = IpThread()
        self.ip_thread.result_ip.connect(self.set_store_name)
        self.ip_thread.start()

    def set_store_name(self, str_name):
        print(f"ip：{str_name}")
        self.l_title_store_name_2.setText(f'{str_name}喜六奶茶店')  #店名的修改
        self.l_title_store_name_2.clearFocus()

    def init_not_login_in_state(self):
        # 设置界面 未登录状态按钮隐藏
        self.btn_setting_login.setHidden(False)
        self.btn_setting_exit.setHidden(True)
        self.logo.setHidden(True)
        # self.l_title_store_name_2.setHidden(True)
        self.token = ''
        self.phone_number = ''
        self.store_id = ''
        self.nickname = ''

    def switch_login_init(self, is_login):
        if is_login:
            self.logo.setHidden(False)
            # self.l_title_store_name_2.setHidden(False)

            self.icon_tee_widget.setStyleSheet(MenuStyle.logo_login_style)
            self.tee_name_l.setText('喜六奶茶')
            # 管道管理
            self.init_conduit_control()
            # 刷新订单界面
            self.refresh_order_content()
            # 刷新本地记录 奶茶记录
            self.refresh_setting_local_tee()
            # 刷新本地消息记录
            self.refresh_setting_local_message()

            #开启串口
            self.start_conduit_serial_thread()###
            self.maketee_ctl.attach_serial(self.conduit_serial_thread)

            try:
                self.conduit_serial_thread.device_name_found.connect(self._on_device_name_found)
            except Exception:
                pass
            self._start_device_name_probe()

            self._ensure_maketee_grid()        # 若你有这个函数，确保泡茶页网格已建好
            self.init_maketee_conduit_control()


            # self.set_message_info("设备故障","红色","设备无响应，请检查设备")
            # self.set_message_info("物料到期提醒 ","黄色","请及时补充物料")

            #清除message_info数据库的数据
            # db_util.clear_message_info()
            # self.refresh_setting_local_message() #刷新message

        else:
            self.logo.setHidden(True)
            # self.l_title_store_name_2.setHidden(True)
            self.tee_name_l.setText('')
            self.open_second_screen_change(True)
            try:
                # 清除设置订单信息
                util.clear_layout(self.setting_order_content_Layout)
                util.clear_layout(self.setting_local_tee_page_Layout)
                # 清除设置消息信息
                util.clear_layout(self.setting_message_content_Layout)
                util.clear_layout(self.setting_local_message_page_Layout)
                self.notice_close_thread.emit()
                self.manager_main_conduit_thread = None
                # 清空 管理管道信息
                util.clear_layout(self.manager_conduit_gridLayout)
                util.clear_layout(self.conduit_gridLayout)
                util.clear_layout(self.order_gridLayout)
                util.clear_layout(self.setting_conduit_gridLayout)
                self.notice_thread_serial_stop.emit()###
                self.notice_thread_serial_stop_2.emit()
                self.out_clear()###
                # if self.camera_thread is not None:
                #     self.close_camera.emit()
                #     self.camera_frame_image.clear()
                #     self.camera_thread = None
                if self.is_show == False:
                    self.camera_frame_image.clear()
                    self.inner_label.clear()
                    self.is_show = True
                    self.notice_camera_scan_show.emit(self.is_show)
            except Exception as e:
                print(e)
            
            # try:
            #     if hasattr(self, "maketee_thread") and self.maketee_thread:
            #         self.maketee_thread.terminate()   # 或者提供 stop()；按你的线程实现来
            #         self.maketee_thread = None
            # except Exception as e:
            #     print(e)

            # 清空泡茶页的网格
            try:
                if self.maketee_conduit_gridLayout:
                    while self.maketee_conduit_gridLayout.count():
                        it = self.maketee_conduit_gridLayout.takeAt(0)
                        w = it.widget()
                        if w:
                            w.setParent(None)
                self.maketee_conduit_card_widgets.clear()
                self.maketee_conduit_num = 0
            except Exception as e:
                print(e)

        if hasattr(self, "btn_begin_make"): self.btn_begin_make.setEnabled(False)
        if hasattr(self, "btn_cancel_make"): self.btn_cancel_make.setEnabled(False)

    def switch_debug_init(self, is_debug):
        if is_debug:
            self.logo.setHidden(False)
            # self.l_title_store_name_2.setHidden(False)

            # 刷新订单界面
            self.refresh_order_content()

            self.icon_tee_widget.setStyleSheet(MenuStyle.logo_debug_style)
            self.tee_name_l.setText('调试中...')
            self.init_conduit_control()
            #开启串口
            self.start_conduit_serial_thread()###
            self.maketee_ctl.attach_serial(self.conduit_serial_thread)
        else:
            self.open_second_screen_change(True)
            self.logo.setHidden(True)
            # self.l_title_store_name_2.setHidden(True)
            self.tee_name_l.setText('')
            # 清除设置订单信息
            util.clear_layout(self.setting_order_content_Layout)
            util.clear_layout(self.setting_local_tee_page_Layout)
            # 清除设置消息信息
            util.clear_layout(self.setting_message_content_Layout)
            util.clear_layout(self.setting_local_message_page_Layout)
            
            self.notice_thread_serial_stop.emit()###
            self.notice_thread_serial_stop_2.emit()
            self.notice_close_thread.emit()
            self.manager_main_conduit_thread = None
            # 清空 管理管道信息
            util.clear_layout(self.manager_conduit_gridLayout)
            util.clear_layout(self.conduit_gridLayout)
            util.clear_layout(self.order_gridLayout)
            util.clear_layout(self.setting_conduit_gridLayout)
            self.out_clear()###
        self.l_title_store_name_2.clearFocus()

    def out_clear(self): ###
        self.select_conduit_bean = []
        self.conduit_beans = []
        self.conduit_num = 0
        self.line_context = ''
        self.T = 2160
        self.lineEdit.setText('')
        self.clean_complete_date.setText('00:00:00')
        
    def init_login_in_state(self, store_name):
        self.btn_setting_login.setHidden(True)
        self.btn_setting_exit.setHidden(False)
        self.logo.setHidden(False)
        # self.l_title_store_name_2.setHidden(False)
        self.tee_name_l.setText(store_name)
        
    def init_date_time(self):
        self.time_management = DateThread()
        self.time_management.return_time.connect(self.get_date_time)
        self.time_management.start()

    def get_date_time(self, date, time, week):
        self.l_title_date.setText(date)
        self.l_title_time.setText(time)
        self.l_title_week.setText(week)
    
    def init_camera_frame(self):
        size = QSize(1015, 400)
        self.camera_frame_ui = CameraFrameMata(self.camera_widget)
        self.notice_camera_scan_show.connect(self.camera_frame_ui.is_show_label) #控制摄像区域的照相机图片显示
        self.camera_frame_ui.setGeometry(0, 0, size.width(), size.height())
         # 新增：控制“原角标”深浅（不叠加）
        self.notice_camera_scan_show.connect(lambda is_show: self.camera_frame_ui.set_scanning(is_show is False))
        self.camera_frame_ui.setGeometry(0, 0, size.width(), size.height())
        

    # TODO ---> 自动出茶
    def init_order_card_widget(self):
        self.order_content_Layout = QHBoxLayout(self.order_content_widget)
        self.order_content_Layout.setObjectName("order_content_Layout")
        self.order_gridLayout = QGridLayout()
        self.order_gridLayout.setObjectName("order_gridLayout")
        self.order_gridLayout.setHorizontalSpacing(10)
        self.order_gridLayout.setVerticalSpacing(26)
        self.order_content_Layout.addLayout(self.order_gridLayout)

    # 选卡回调：统一维护选中状态
    def order_info_callBack(self, tee_bean, is_active):
        if is_active:
            self.select_order_tee_bean = tee_bean
            if hasattr(self, "btn_begin_make"): self.btn_begin_make.setEnabled(True)
            if hasattr(self, "btn_cancel_make"): self.btn_cancel_make.setEnabled(True)
            # 记住ID，刷新时可还原
            self.selected_order_id = getattr(tee_bean, "id", None)
        else:
            self.select_order_tee_bean = None
            # 尝试自动再选一杯，避免按钮一下子变灰
            if callable(getattr(self, "_auto_select_first_order", None)):
                self._auto_select_first_order()
    def refresh_order_content(self):
        if getattr(self, "_refresh_locked", False):
            return
        self.order_control_refresh.emit()
        util.clear_layout(self.order_gridLayout)
        self.refresh_order_content_thread = RefreshOrderContentThread(self.is_login, self.is_debug)
        self.refresh_order_content_thread.return_order_tee_bean_list.connect(self.add_order_tee_to_widget)
        self.refresh_order_content_thread.start()

    def _auto_select_first_order(self):
        """自动挑第一杯可做的；若拿不到 state，就不做过滤直接取第一张卡。"""
        widgets = getattr(self, "order_card_widgets", [])
        target = None
        for w in widgets:
            bean = getattr(w, "bean", None) or getattr(w, "menu", None)
            if bean is None:
                continue
            st = str(getattr(bean, "state", ""))  # 你项目里的可做状态通常是 '2'/'3'
            if st in ("2", "3") or st == "":
                target = (w, bean)
                break
        if target:
            w, bean = target
            self.select_order_tee_bean = bean
            self.selected_order_id = getattr(bean, "id", None)
            try:
                if hasattr(w, "setChecked"): w.setChecked(True)
                if hasattr(w, "setSelected"): w.setSelected(True)
            except Exception:
                pass
            if hasattr(self, "btn_begin_make"): self.btn_begin_make.setEnabled(True)
            if hasattr(self, "btn_cancel_make"): self.btn_cancel_make.setEnabled(True)
        else:
            self.select_order_tee_bean = None
            if hasattr(self, "btn_begin_make"): self.btn_begin_make.setEnabled(False)
            if hasattr(self, "btn_cancel_make"): self.btn_cancel_make.setEnabled(False)

        
    def add_order_tee_to_widget(self, tee_bean_list):
        grid = self._ensure_order_grid()
        if grid is None:
            print("[Order] 跳过添加：未能定位订单区域")
            return

        print("[CupDebug] add_order_tee_to_widget: 收到订单数量 =",
              len(tee_bean_list))

        # 只清子项，不删布局本体（防止后续 addWidget 崩溃）
        try:
            self._clear_layout_only_children(grid)
        except Exception:
            pass

        self.order_card_widgets = []
        COLS = 2
        for i, bean in enumerate(tee_bean_list):
            row, col = divmod(i, COLS)
            card = OrderCardWidget(bean)

            name = str(
                getattr(bean, "name", "") or
                getattr(bean, "tee_name", "") or
                getattr(bean, "product_name", "") or
                getattr(bean, "product_simp", "")
            ).strip()

            cup_attr = ""
            for attr in ("cup", "cup_type"):
                if hasattr(bean, attr):
                    cup_attr = getattr(bean, attr) or ""
                    break
            # 统一从 _on_card_changed 入口处理单选和图标

            if not hasattr(self, "order_card_widgets"):
                self.order_card_widgets = []

            card.changed_order.connect(
                lambda bean, is_active, c=card:
                self._on_card_changed(c, bean, is_active)
            )
            self.close_order.connect(card.cancel_order)
            self.order_control_refresh.connect(card.refresh_ui)
            self.order_card_style.connect(card.set_no_style)
            grid.addWidget(card, row, col, 1, 1)
            self.order_card_widgets.append(card)

            # 刷新后按 ID 还原选中
            if (getattr(self, "selected_order_id", None)
                    and getattr(bean, "id", None) == self.selected_order_id):
                # print("[CupDebug]   还原选中: id=", self.selected_order_id)
                self._set_single_selection(card)
                self._apply_checked_visual(card, True)
                self._current_selected_card = card
                self.select_order_tee_bean = bean
                if hasattr(self, "btn_begin_make"):
                    self.btn_begin_make.setEnabled(True)
                if hasattr(self, "btn_cancel_make"):
                    self.btn_cancel_make.setEnabled(True)

        # 可选占位，让网格整齐
        total_cells = COLS * 3
        for i in range(len(tee_bean_list), total_cells):
            row, col = divmod(i, COLS)
            ph = QWidget()
            ph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            grid.addWidget(ph, row, col, 1, 1)

        # 如果没有记忆选中，自动挑一杯
        if callable(getattr(self, "_auto_select_first_order", None)):
            self._auto_select_first_order()


    def init_conduit_card_widget(self):
        # 扫码界面 管道展示布局
        self.conduit_content_Layout = QHBoxLayout(self.sw_scan_code_conduit_widget)
        self.conduit_content_Layout.setObjectName("conduit_content_Layout")
        self.conduit_gridLayout = QGridLayout()
        self.conduit_gridLayout.setObjectName("conduit_gridLayout")
        self.conduit_gridLayout.setHorizontalSpacing(16)
        self.conduit_gridLayout.setVerticalSpacing(16)
        self.conduit_content_Layout.addLayout(self.conduit_gridLayout)
        # 管理界面 管道展示布局
        self.manager_conduit_gridLayout = QGridLayout(self.manager_conduit_content)
        self.manager_conduit_gridLayout.setObjectName('manager_conduit_gridLayout')
        self.manager_conduit_gridLayout.setHorizontalSpacing(16)
        self.manager_conduit_gridLayout.setVerticalSpacing(16)
        # 用来保存“管理页”的 ConduitCardWidget，供后面统一刷新 X 标记
        self.conduit_card_widgets = []
        self._ensure_maketee_grid()

    # —— 统一注册线程的小工具 ——  放在 Main1080Window 类里
    def _register_thread(self, t):
        if not hasattr(self, "_threads"):
            self._threads = []
        self._threads.append(t)
        # 线程结束后自动从列表里移除，避免重复 wait
        t.finished.connect(lambda: self._threads.remove(t) if t in self._threads else None)
        return t


    def init_conduit_control(self):
        self.conduit_thread = ConduitThread()
        self.conduit_thread.result_conduit_bean.connect(self.show_conduit_bean)
        self.conduit_thread.result_conduits_bean_list.connect(self.show_conduits_bean)
        self.conduit_thread.start()
        
        # 管理主界面的管道数据更新
        self.manager_main_conduit_thread = ManagerMainScreenConduit()
        self.notice_close_thread.connect(self.manager_main_conduit_thread.close_thread)
        self.manager_main_conduit_thread.result_conduit_bean.connect(self.update_conduit_data)
        self.manager_main_conduit_thread.start()
        
    def update_conduit_data(self, conduit_beans):
        self.conduit_beans = conduit_beans
        self.notice_main_item_conduit.emit(conduit_beans)
        self.notice_item_conduit.emit(conduit_beans)

    def show_conduit_bean(self, conduit_bean):
        """
        还原版：同一份数据来时，同时：
        - 在【管理】页摆一张卡片
        - 在【泡茶】页也摆一张卡片（复制一个新的控件实例，数据仍是同一个 bean）
        不再创建任何“独立线程/独立表”的数据通道。
        """
        if not (self.is_login or self.is_debug):
            return

        # --- 管理页 ---
        idx = self.conduit_num
        row, col = divmod(idx, 4)

        card_mgr = ConduitCardWidget(conduit_bean, self.is_debug)
        card_mgr.update_conduit_bean([conduit_bean])
        self.manager_conduit_gridLayout.addWidget(card_mgr, row, col, 1, 1)

        if not hasattr(self, "conduit_card_widgets"):
            self.conduit_card_widgets = []
        self.conduit_card_widgets.append(card_mgr)

        # 与管理页保持一致的更新绑定
        card_mgr.changed_conduit_card.connect(self.conduit_card_callBack)
        self.notice_main_item_conduit.connect(card_mgr.update_conduit_bean)

        # --- 泡茶页（只是复制一张卡片控件，沿用同一个 bean） ---
        # self._ensure_maketee_grid()
        # if getattr(self, "maketee_conduit_gridLayout", None):
        #     card_mk = ConduitCardWidget(conduit_bean, self.is_debug)
        #     card_mk.update_conduit_bean([conduit_bean])
        #     self.notice_main_item_conduit.connect(card_mk.update_conduit_bean)
        #     card_mk.changed_conduit_card.connect(self.conduit_card_callBack)

        #     self.maketee_conduit_gridLayout.addWidget(card_mk, row, col, 1, 1)
        #     if hasattr(self, "maketee_conduit_card_widgets"):
        #         self.maketee_conduit_card_widgets.append(card_mk)

        # 你原来就有的小条列表（12 列）逻辑，如需保留：
        try:
            scan_row, scan_col = divmod(idx, 12)
            item_conduit_card_ui = ItemConduitMata(conduit_bean)
            self.notice_main_item_conduit.connect(item_conduit_card_ui.update_conduit_bean)
            item_conduit_card_ui.setFixedSize(65, 182)
            self.conduit_gridLayout.addWidget(item_conduit_card_ui, scan_row, scan_col, 1, 1)
        except Exception:
            pass

        self.conduit_beans.append(conduit_bean)
        self.conduit_num += 1

        # 刷 “未被任何配方使用” 标志（如你项目里本来就有）
        QtCore.QTimer.singleShot(0, self._refresh_conduit_unused_marks)

    def show_maketee_conduit_bean(self, conduit_bean):
        self._dbg(f"[mk-card] arrive: is_login={self.is_login} is_debug={self.is_debug}")
        if not (self.is_login or self.is_debug):
            if not hasattr(self, "_mk_buffer"): self._mk_buffer = []
            self._mk_buffer.append(conduit_bean)
            self._dbg(f"[mk-card] buffered (size={len(self._mk_buffer)})")
            return
        self._mk_add_card(conduit_bean)

        
    def init_maketee_conduit_control(self):

        return self.init_maketee_conduit_control_from_maketee_table()
        


    def _stop_all_threads(self):
        # 按你工程里定义的线程都尝试停一下
        for t in getattr(self, "_threads", []):
            try:
                if hasattr(t, "stop"):
                    t.stop()        # 我们给 ManagerSecondScreenConduit 加了 stop
                else:
                    t.quit()        # 没有 stop 的，先尝试 quit
            except Exception:
                pass
            # 等待线程结束
            t.wait(2000)

        # 若还有特殊线程对象没通过 _register_thread 托管，单独兜底
        for name in ("woo_dbg", "conduit_thread", "manager_main_conduit_thread"):
            t = getattr(self, name, None)
            if t is None: 
                continue
            try:
                if hasattr(t, "stop"):
                    t.stop()
                else:
                    t.quit()
            except Exception:
                pass
            t.wait(2000)

    def closeEvent(self, e):
        try:
            self.notice_close_thread.emit()                 # 通知线程停
            if getattr(self, "maketee_thread", None):
                self.maketee_thread.wait(2000)              # 等最多2s
        finally:
                super().closeEvent(e)


    def _ensure_maketee_grid(self):
        from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QWidget

        # 已经初始化过：优先“重绑”指针，再返回
        if getattr(self, "_maketee_grid_inited", False):
            # 指针丢了就从 UI 结构中重新拿一次
            grid = getattr(self, "maketee_conduit_gridLayout", None)
            if grid is None:
                try:
                    holder = self.maketee_conduit_content
                    sub = holder.findChild(QWidget, "maketee_grid_container")
                    if sub:
                        lay = sub.layout()
                        if isinstance(lay, QGridLayout):
                            self.maketee_conduit_gridLayout = lay
                            grid = lay
                            self._dbg("[mk-grid] rebind grid from sub.layout()")
                except Exception as e:
                    self._err("[mk-grid] rebind failed:", e)
            # 打印真实 count（拿不到就给 0）
            try:
                c = grid.count() if grid is not None else 0
            except Exception:
                c = 0
            self._dbg(f"[mk-grid] already inited, grid={grid}, count={c}")
            return grid is not None

        # —— 首次初始化（与你现在逻辑一致）——
        try:
            holder = self.maketee_conduit_content
        except Exception as e:
            self._err("[mk-grid] holder not found:", e);  return False

        outer = holder.layout()
        if outer is None:
            self._dbg("[mk-grid] holder.layout() is None, set QVBoxLayout()")
            outer = QVBoxLayout(); outer.setContentsMargins(0, 0, 0, 0); holder.setLayout(outer)

        sub = holder.findChild(QWidget, "maketee_grid_container")
        if sub is None:
            self._dbg("[mk-grid] create sub QWidget 'maketee_grid_container'")
            sub = QWidget(holder); sub.setObjectName("maketee_grid_container"); outer.addWidget(sub)

        grid = sub.layout()
        if not isinstance(grid, QGridLayout):
            self._dbg("[mk-grid] create QGridLayout on sub")
            grid = QGridLayout(sub)
            grid.setObjectName("maketee_conduit_gridLayout")
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(16); grid.setVerticalSpacing(16)
            sub.setLayout(grid)

        self.maketee_conduit_gridLayout = grid
        self._maketee_grid_inited = True
        self._dbg("[mk-grid] READY. grid =", grid)
        return True



    def show_conduits_bean(self, conduit_beans):
        # 计算需要占位的空位置
        total_cells = 30
        used_cells = len(conduit_beans)
        empty_cells = total_cells - used_cells

        # print(f"conduit_beans:{len(conduit_beans)}")
        #获取工作时的管道
        self.get_work_conduit_bean(conduit_beans)###
        self.conduit_work_number = len(self.work_conduit_bean) - 1  ###
        print(f"conduit_work_number:{self.conduit_work_number}")

        for conduit_num in range(len(conduit_beans)):
            scan_row = conduit_num // 6
            scan_col = conduit_num % 6
            conduit_card_ui = ItemScreenConduitWMata(conduit_beans[conduit_num])
            self.notice_item_conduit.connect(conduit_card_ui.update_conduit_bean)
            conduit_card_ui.setFixedSize(250, 182)
            self.setting_conduit_gridLayout.addWidget(conduit_card_ui, scan_row, scan_col, 1, 1)

        # 填充剩余的空位置
        if empty_cells > 0:
            for num in range(used_cells, total_cells):
                row = num // 6
                col = num % 6
                # 创建一个占位控件
                placeholder_widget = QWidget()
                placeholder_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.setting_conduit_gridLayout.addWidget(placeholder_widget, row, col, 1, 1)
         


    # 原有：卡片点击后的回调，只做了互斥选中
    # 卡片点击后的回调：泡茶页仍旧互斥；管理页允许多选
    def conduit_card_callBack(self, checked, bean):
        """卡片点击回调：
        - 管理页：多选（update_check），把选中通道存到 self.select_conduit_bean(list)
        - 泡茶页：互斥单选（setChecked）
        """
        card = self.sender()
        is_manager_card = card in getattr(self, "conduit_card_widgets", [])

        if is_manager_card:
            # 多选：只改自己，不动其他
            if hasattr(card, "update_check"):
                card.update_check(bool(checked))

            # 维护集合
            if not hasattr(self, "_mgr_selected_cids"):
                self._mgr_selected_cids = set()

            # 兼容不同 bean 字段拿通道号
            cid = None
            if hasattr(bean, "get_conduit"):
                cid = str(bean.get_conduit())
            elif hasattr(bean, "conduit"):
                cid = str(getattr(bean, "conduit"))
            elif hasattr(bean, "conduit_no"):
                cid = str(getattr(bean, "conduit_no"))

            if cid:
                # 统一成 “1#” 这种格式
                cid = cid if cid.endswith("#") else f"{cid}#"
                if checked:
                    self._mgr_selected_cids.add(cid)
                else:
                    self._mgr_selected_cids.discard(cid)

            # 对外暴露为 list（按钮逻辑会用）
            try:
                import re
                self.select_conduit_bean = sorted(
                    list(self._mgr_selected_cids),
                    key=lambda s: int(re.sub(r"\D", "", s or "0") or "0"),
                )
            except Exception:
                self.select_conduit_bean = list(self._mgr_selected_cids)

            print(f"[manager] selected -> {self.select_conduit_bean}")
            return

        # ===== 泡茶页：互斥单选 =====
        for w in getattr(self, "maketee_conduit_card_widgets", []):
            if hasattr(w, "setChecked"):
                w.setChecked(w is card if checked else False)
        self.maketee_selected_row = bean if checked else None
        print(f"[maketee] selected -> {getattr(bean,'name', None)} #{getattr(bean,'conduit', getattr(bean,'conduit_no', None))}")
        try:
            if hasattr(self, "maketee_ctl") and self.maketee_ctl:
                self.maketee_ctl.set_selected_row(self.maketee_selected_row)
        except Exception:
            pass


    # 从UI兜底拿“已勾选”的订单卡片
    def _fallback_pick_selected_order(self):
        layout = getattr(self, "order_gridLayout", None)
        if not layout:
            return None
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if hasattr(w, "isChecked") and callable(getattr(w, "isChecked")) and w.isChecked():
                return getattr(w, "bean", None) or getattr(w, "menu", None)
        return None

    @pyqtSlot()
    def on_btn_begin_make_clicked(self):
        try:
            # 1) 登录/调试校验
            if not (self.is_login or self.is_debug):
                GreenMessageBox.warning(self, "未登录/调试", "请先登录或进入调试模式再制作。")
                return

            # 2) 兜底：如果成员变量还没来得及更新，从UI里取“已勾选”的卡片
            if self.select_order_tee_bean is None:
                cand = self._fallback_pick_selected_order()
                if cand is not None:
                    self.select_order_tee_bean = cand
                    self.selected_order_id = getattr(cand, "id", None)

            # 3) 再兜底：自动挑一杯可做的
            if self.select_order_tee_bean is None and callable(getattr(self, "_auto_select_first_order", None)):
                self._auto_select_first_order()
                if self.select_order_tee_bean is None:
                    GreenMessageBox.warning(self, "未选中订单", "请先选择一杯需要制作的订单。")
                    return

            # 4) 先记住本次饮品 tips（send_serial_data 里可能会追加“记得加冰”等提示，
            #    因此必须先把原始 tips 放进去，避免被后续覆盖）
            self._remember_tips_for_current_drink()

            # 5) 再发送；若“中文配方存在未匹配材料”会被内部拦截，这里早退
            ok = self.send_serial_data(self.select_order_tee_bean)
            if not ok:
                # 关键：拦截时不要清空 self.select_order_tee_bean，也不要改样式
                return
            # 6) 进入制作对话框（保持你原本的连接）
            self.order_dialog_1_ui = OrderDialog1(self.select_order_tee_bean)
            self.order_dialog_1_ui.notice_complete.connect(self.start_notice_complete_thread)
            self.order_dialog_1_ui.notice_serial_open.connect(self.notice_make_tee_begin)
            self.order_dialog_1_ui.notice_serial_stop.connect(self.callBack_make_tee_stop)
            self.order_dialog_1_ui.notice_style_no.connect(self.order_card_no_style)
            self.notice_make_tee_result.connect(self.order_dialog_1_ui.handle_data)
            self.order_dialog_1_ui.show()

            # 6) 通知后端开始
            self.notice_make_tee_begin()

            # 7) ★ 只有真正进入制作流程后，再清理当前选中
            self.select_order_tee_bean = None
        except Exception as e:
            import traceback; traceback.print_exc()
            GreenMessageBox.warning(self, "异常", f"开始制作过程中出现异常：\n{e}")

    def _on_make_flow_finished(self, *args, **kwargs):
        """
        制作流程完结的统一收尾：
        - 解锁刷新订单
        - 如果本次饮品有 tips，则弹出一个小贴士弹窗
        - 如果有错误信息，则弹出错误提示
        """
        print("[FLOW] _on_make_flow_finished args=", args, "kwargs=", kwargs)

        # ---- 1. 解析 ok / err（兼容不同线程的调用方式）----
        ok = True
        err = ""

        # 位置参数
        if args:
            first = args[0]
            if isinstance(first, bool):
                ok = first
            elif isinstance(first, str):
                err = first

        # 关键字参数
        if "ok" in kwargs and isinstance(kwargs["ok"], bool):
            ok = kwargs["ok"]
        if "err" in kwargs and isinstance(kwargs["err"], str):
            err = kwargs["err"]

        # ---- 2. 解锁 + 刷新订单列表 ----
        try:
            self._refresh_locked = False
        except Exception:
            pass

        try:
            self.refresh_order_content()
        except Exception as e:
            import traceback; traceback.print_exc()
            print("[FLOW] refresh_order_content error:", e)

        # ---- 3. 异常情况（如果有）----
        if not ok and err:
            try:
                GreenMessageBox.information(self, "制作异常", err)
            except Exception:
                QMessageBox.warning(self, "制作异常", err)
            # 有错误时就不弹 tips 了
            return

        # ---- 4. 正常完成：如果本次饮品有 tips 就弹窗 ----
        tips = (getattr(self, "_current_make_tips", "") or "").strip()
        drink_name = (getattr(self, "_current_make_drink_name", "") or "").strip()

        # 用完就清空，防止下次误用
        self._current_make_tips = ""
        self._current_make_drink_name = ""

        print(f"[TipsDebug] _on_make_flow_finished 中拿到 tips = {tips!r}, drink_name = {drink_name!r}")

        if tips:
            if drink_name:
                text = f"{tips}"
            else:
                text = tips

            # 兼容换行：QLabel 使用富文本时，用 <br> 显示换行
            if "\n" in text and "<br" not in text:
                text = text.replace("\n", "<br>")

            print(f"[TipsDebug] 展示制作完成小贴士: {text!r}")
            try:
                GreenMessageBox.warning(self, "tips", text)
            except Exception as e:
                import traceback; traceback.print_exc()
                print("[TipsDebug] 显示 tips 弹窗失败：", e)

    def order_card_no_style(self):
        self.order_card_style.emit()

    def send_serial_data(self, menu) -> bool:
        """
        仅在【中文配方存在未匹配材料】时拦截并弹绿色提示；其余情况一律发送。
        成功发送返回 True，拦截/异常返回 False（外层据此决定是否弹“制作中”界面）。
        依赖：
        - material_text_to_letter_recipe_via_db(text, step) -> (letter_base, ICE_dyn, SUGAR_dyn, missing_set)
        - adjust_recipe_by_ice_sugar(letter_recipe, ice_text, sugar_text, step) -> letter_recipe
        - 全局 ICE_CHANNELS / SUGAR_CANDIDATES
        """
        import traceback
        try:
            # 基础校验
            if menu is None:
                print("[ERR] send_serial_data: menu is None"); return False
            base_raw = (getattr(menu, "recipe", "") or "").strip()
            if not base_raw:
                print("[ERR] send_serial_data: recipe is empty"); return False


            # —— 冰/碎冰：自动出冰开关（1#/2#）
            ice_name_auto_map, ice_letters = get_ice_channel_cfg_from_db()
            manual_ice_names_in_make = {n for n, auto in ice_name_auto_map.items() if not auto}
            removed_ice = []

            # 若为手动加冰：从配方中移除冰/碎冰项（中文配方 & 字母配方都兼容）
            if manual_ice_names_in_make:
                is_letter_tmp = bool(re.search(r'[A-Z]\d{3}', base_raw))
                has_cjk_tmp   = bool(re.search(r'[\u4e00-\u9fff]', base_raw))
                if has_cjk_tmp and not is_letter_tmp:
                    base_raw2, removed_ice = remove_materials_from_cjk_recipe(base_raw, manual_ice_names_in_make)
                    base_raw = base_raw2 or base_raw
                else:
                    base_raw2, removed_ice = remove_letters_from_letter_recipe(base_raw, ice_letters)
                    base_raw = base_raw2 or base_raw

                # 手动加冰：制作完成后提示（不依赖 removed_ice 的解析结果，避免遗漏）
                cur = (getattr(self, '_current_make_tips', '') or '').strip()
                extra = '记得加冰'
                if extra not in cur:
                    self._current_make_tips = (cur + '\n' + extra).strip() if cur else ('\n' + extra)

            # UI 选择（1/2/3 -> 文本）
             # 先优先使用“这杯饮品”自己记录的冰量 / 糖量（来自购物车 or 摄像头订单）
            ice_text   = (getattr(menu, "product_ice", "") or "").strip()
            sugar_text = (getattr(menu, "product_sugar", "") or "").strip()

            # 如果订单里没有写死，再退回到当前菜单页 UI 的选择（兼容老逻辑）
            if not ice_text:
                ice_map   = {'1': '少冰', '2': '正常冰', '3': '常温'}
                ice_text   = ice_map.get(getattr(self, "menu_ice_value", '2'), '正常冰')

            if not sugar_text:
                sugar_map = {'1': '常规', '2': '五分糖', '3': '三分糖'}
                sugar_text = sugar_map.get(getattr(self, "menu_sugar_value", '1'), '常规')

            # print(f"[ICE/SUGAR] using ice={ice_text!r}, sugar={sugar_text!r}")

            # 判定中文/字母配方
            is_letter = bool(re.search(r'[A-Z]\d{3}', base_raw))
            has_cjk   = bool(re.search(r'[\u4e00-\u9fff]', base_raw))

            dynamic_ice_backup = None
            dynamic_sugar_backup = None

            # 中文配方：转字母 + “未匹配”拦截
            if has_cjk and not is_letter:
                letter_base, ICE_dyn, SUGAR_dyn, missing = material_text_to_letter_recipe_via_db(base_raw, step=5)

                if missing:  # 只保留这一个拦截点
                    miss_str = "、".join(sorted(missing))
                    GreenMessageBox.warning(self, "材料未匹配",
                                            f"以下材料没有找到对应通道：\n{miss_str}\n\n请在“管理-物料绑定”里设置后再试。")
                    print(f"[BLOCK] 未匹配材料：{sorted(missing)}；已弹窗并终止。")
                    return False

                if not letter_base:
                    GreenMessageBox.warning(self, "配方解析失败",
                                            f"无法从配方解析出任何通道：\n{base_raw}")
                    print(f"[BLOCK] 中文配方解析失败：{base_raw}")
                    return False

                # 本杯动态集合（仅本次有效）
                if ICE_dyn:
                    dynamic_ice_backup = set(ICE_CHANNELS)
                    ICE_CHANNELS.clear(); ICE_CHANNELS.update(ICE_dyn)
                if SUGAR_dyn:
                    dynamic_sugar_backup = set(SUGAR_CANDIDATES)
                    SUGAR_CANDIDATES.clear(); SUGAR_CANDIDATES.update(SUGAR_dyn)

                base_letter = letter_base
            else:
                base_letter = base_raw  # 已是字母配方

            # 少冰/几分糖 缩放
            final = adjust_recipe_by_ice_sugar(base_letter, ice_text=ice_text, sugar_text=sugar_text, step=5)

            # 还原集合
            if dynamic_ice_backup is not None:
                ICE_CHANNELS.clear(); ICE_CHANNELS.update(dynamic_ice_backup)
            if dynamic_sugar_backup is not None:
                SUGAR_CANDIDATES.clear(); SUGAR_CANDIDATES.update(dynamic_sugar_backup)

            # 兜底：缩放异常就直接发 base_letter，避免静默不发
            if not final:
                print(f"[WARN] 缩放结果为空，改为直接发送 base_letter。base={base_letter}")
                final = base_letter

            # --- 新增：把 ingredients 作为后缀拼到配方后面 ---
            ing = self._resolve_ingredients_for_menu(menu)
            if ing:
                # 防止重复下划线
                if not final.endswith("_" + ing):
                    final = f"{final}_{ing}"
            # --- 新增结束 ---

            # 真正发送
            print(f"[SEND] base_raw={base_raw} parsed={base_letter} ice={ice_text} sugar={sugar_text} -> {final}")
            self.notice_make_tee_data(final)
            return True

        except Exception as e:
            print("[EXC] send_serial_data failed:", e)
            traceback.print_exc()
            return False

    # ===================== 3) “开始制作”按钮：用返回值决定是否弹进度框 =====================
    def begin_make_btn_clicked(self):
        """
        关口：只有 send_serial_data 返回 True（已经准备并发送），才弹“制作中”进度对话框。
        """
        self._remember_tips_for_current_drink()
        ok = self.send_serial_data(self.select_order_tee_bean)
        if not ok:
            print("[FLOW] send_serial_data 被阻断：不进入制作进度界面")
            return

        # 真正要做 → 再弹进度框（你项目里的函数名可能是 show_make_dialog / show_make_progress 等）
        self.show_make_dialog()

    @pyqtSlot()
    def on_btn_cancel_make_clicked(self):   #取消制作按钮
        if self.is_login:
            # db_util.clear_order_info()
            # db_util.clear_tee_info()
            if self.select_order_tee_bean is not None:
                db_util.update_tee_info_state_by_id(self.select_order_tee_bean.id, '2')   #更新数据库信息
                db_util.clear_tee_info_state_by_id(self.select_order_tee_bean.id, "2")    #删除数据
                self.select_order_tee_bean = None   #取消选择
                self.refresh_order_content()   #刷新界面
        if self.is_debug:
            if self.select_order_tee_bean is not None:
                db_util.update_tee_info_state_by_id(self.select_order_tee_bean.id, '6') 
                db_util.clear_tee_info_state_by_id(self.select_order_tee_bean.id, "6") 
                self.select_order_tee_bean = None
                self.refresh_order_content()

    def callBack_make_tee_result(self, mA_list):
        # print(f"mA_list:{mA_list}")
        self.notice_make_tee_result.emit(mA_list)  #发射运行中的电机的信号

    def notice_make_tee_begin(self):
        print("[ScanAuto] notice_make_tee_begin -> emit notice_thread_tee_begin")
        self.notice_thread_tee_begin.emit()

    def callBack_make_tee_stop(self):
        try:
            if self.conduit_serial_thread and self.conduit_serial_thread.isRunning():
                print("[UI] 发送取消指令 -> notice_thread_tee_stop")
                self.notice_thread_tee_stop.emit()
                # 适度延迟后解锁并刷新（防止瞬时刷新把UI卡死）
                from PyQt5.QtCore import QTimer
                self._refresh_locked = False
                QTimer.singleShot(500, self.refresh_order_content)
            else:
                GreenMessageBox.warning(self, "设备未就绪", "后端串口线程未启动，无法取消。")
        except Exception as e:
            import traceback; traceback.print_exc()
            GreenMessageBox.warning(self, "异常", f"取消过程中出现异常：\n{e}")

    def _do_stop_safe(self):
        if self.conduit_serial_thread and self.conduit_serial_thread.isRunning():
            print("[UI] 发送取消指令 -> notice_thread_tee_stop")
            self.notice_thread_tee_stop.emit()  # 你原本就发的信号。:contentReference[oaicite:4]{index=4}
        else:
            GreenMessageBox.warning(self, "设备未就绪", "后端串口线程未启动，无法取消。")


    def notice_make_tee_data(self, data_str):
        print(f"[ScanAuto] notice_make_tee_data -> {data_str}")
        self.make_tee_notice_data.emit(data_str)  #这里的是将配方发射到conduit_serial_thread

    def callBack_conduit_info_from_usb(self, weights): ###
        if self.is_login or self.is_debug:
            # print(f'Weights: {weights}')
            # for i, margin in enumerate(weights):
            #     _id = i + 1  
            #     db_util.update_conduit_margin_info(_id, margin)
            data_list = [(margin, i + 1) for i, margin in enumerate(weights)]
            db_util.update_conduit_multiple_margin_info(data_list)  # 批量更新  传到数据库，传到conduit_info表内

    def update_begin_time_info(self, num):  
        ids = list(range(1, num)) #从 1 到 18
        for _id in ids:
            db_util.update_begin_time_info(_id)  # 调用单条更新方法
   
    def start_notice_complete_thread(self, tee_bean):
        """
        点击『制作完成』后被调用：
        1. 更新 tee_info.state
        2. 刷新本地记录
        3. 最后统一调用 _on_make_flow_finished（负责解锁 + 刷订单 + 弹 tips）
        """
        try:
            print("[FLOW] start_notice_complete_thread 被调用")
            print("       bean_id =", getattr(tee_bean, "id", None),
                "name =", getattr(tee_bean, "product_name", ""))

            # 1) 更新数据库状态
            if self.is_login or self.is_debug:
                try:
                    if getattr(tee_bean, "id", None) is not None:
                        db_util.update_tee_info_state_by_id(tee_bean.id, '1')
                        print("[FLOW] 已更新 tee_info.state=1, id =", tee_bean.id)
                    else:
                        print("[FLOW] tee_bean.id 为空，跳过更新数据库状态")
                except Exception as e:
                    import traceback; traceback.print_exc()
                    print("[FLOW] 更新 tee_info 状态失败：", e)
                    # 出错也调用收尾逻辑，但把错误传进去
                    self._on_make_flow_finished(ok=False, err=str(e))
                    return

            # 2) 刷新本地记录
            try:
                self.refresh_setting_local_tee()
                print("[FLOW] refresh_setting_local_tee 完成")
            except Exception as e:
                import traceback; traceback.print_exc()
                print("[FLOW] refresh_setting_local_tee 失败：", e)

            # 3) ★ 最后统一收尾：解锁 + 刷订单 + 弹 tips
            print("[FLOW] 调用 _on_make_flow_finished(ok=True)")
            self._on_make_flow_finished(ok=True, err="")
        except Exception as e:
            import traceback; traceback.print_exc()
            print("[FLOW] start_notice_complete_thread 发生异常：", e)
            self._on_make_flow_finished(ok=False, err=f"保存制作结果时发生异常：{e}")
    # TODO ---> 手动出茶
    #初始化菜单内容的布局
    def init_menu_card_widget(self):
        """只在第一次进入时创建布局；之后复用已有的网格"""
        # 如果已经有网格，就不要再创建（避免重复叠加）
        grid = getattr(self, "menu_gridLayout", None)
        if grid is not None:
            try:
                _ = grid.count()
                return
            except Exception:
                pass  # 旧指针失效，继续重建

        # 首次创建
        from PyQt5.QtWidgets import QHBoxLayout, QGridLayout
        self.menu_content_Layout = QHBoxLayout(self.menu_content_widget)
        self.menu_content_Layout.setObjectName("menu_content_Layout")

        self.menu_gridLayout = QGridLayout()
        self.menu_gridLayout.setObjectName("menu_gridLayout")
        self.menu_gridLayout.setHorizontalSpacing(28)
        self.menu_gridLayout.setVerticalSpacing(35)
        self.menu_content_Layout.addLayout(self.menu_gridLayout)

        # 首次进入时也把计数器清0
        self.menu_num = 0

    
    #启动一个线程来加载菜单数据
    def load_menu_xlsx(self):
        self.menu_tee_bean_thread = MenuTeeBeanThread()
        self.menu_tee_bean_thread.add_menu_tee_bean.connect(self.add_menu_tee_bean)
        self.menu_tee_bean_thread.start()
    

    #将加载的菜单数据显示在界面上
    def add_menu_tee_bean(self, menu_tee_bean):
        self.menu_tee_beans.append(menu_tee_bean)
        row = self.menu_num // 3
        col = self.menu_num % 3
        menu_ui = MenuCardWidget(menu_tee_bean)
        menu_ui.changed_menu_card.connect(self.menu_card_callBack)
        self.no_changed_menu_broad.connect(menu_ui.set_no_style)
        self.change_menu_config_broad.connect(menu_ui.set_config_num)
        self.menu_gridLayout.addWidget(menu_ui, row, col, 1, 1)
        self.menu_num = self.menu_num + 1
        name = menu_tee_bean.get_Name()
        self.menu_cards_by_name[name] = menu_ui
        self.menu_beans_by_name[name] = menu_tee_bean
        # 连接右上角按钮：点击删除本卡
        btn = getattr(menu_ui, "btn_close", None)
        if btn is None and hasattr(menu_ui, "ui"):
            btn = getattr(menu_ui.ui, "btn_close", None)
        if btn is not None:
            btn = getattr(menu_ui, "btn_close", None) or getattr(getattr(menu_ui, "ui", None), "btn_close", None)
            if btn:
                btn.clicked.connect(lambda _, n=name: self._confirm_delete(n))
       



    def menu_card_callBack(self, menu_tee_bean):
        name = menu_tee_bean.get_Name()
        if name in getattr(self, "_disabled_menu_names", set()):
            miss = sorted(self._missing_names_by_name.get(name, []))
            if miss:
                # 缺少的材料大字号+居中
                miss_html = "".join(
                    f"<p style='font-size:28px; font-weight:800; text-align:center; color:red; margin:8px 0'>{m}</p>"
                    for m in miss
                )
                text = (
                    "<p style='font-size:22px; font-weight:600; color:#2C7A4B;'>以下材料没有找到对应通道：</p>"
                    f"{miss_html}"
                    "<p style='font-size:20px; font-weight:600; color:#2C7A4B; margin-top:12px'>请在“管理-物料绑定”里设置后再试。</p>"
                )
                GreenMessageBox.warning(self, "材料未匹配", text)

            return


        self.no_changed_menu_broad.emit()
        name = menu_tee_bean.get_Name()
        self.menu_config_name_l.setText(name)
        try:
            price = float(menu_tee_bean.get_Base_Price())
        except (TypeError, ValueError):
            print(f"price是字符型")
        format_price = "{:.2f}".format(price)
        self.menu_tee_price = format_price
        self.weight_mid_money_l.setText(f'￥{str(format_price)}')
        big_price = float(price) * 1.2
        format_big_price = "{:.2f}".format(big_price)
        self.weight_big_money_l.setText(f'￥{str(format_big_price)}')
        self.tee_recipe = menu_tee_bean.Recipe
        self.init_menu_config_info()
        self.menu_recalculate()

    def init_menu_config_info(self):
        self.menu_config_number_l.setText('1')
        self.menu_weight_value = '1'
        self.weight_big_l.setStyleSheet(MenuStyle.weight_no_changed_style_1)
        self.weight_big_money_l.setStyleSheet(MenuStyle.weight_no_changed_style_2)
        self.weight_mid_l.setStyleSheet(MenuStyle.weight_changed_style_1)
        self.weight_mid_money_l.setStyleSheet(MenuStyle.weight_changed_style_2)
        self.menu_sugar_value = '1'
        self.menu_sugar_style_changed(True, False, False)
        self.menu_ice_value = '2'
        self.menu_ice_style_changed(False, True, False)
        self.is_cbb = False
        self.menu_small_material_cbb_l.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.is_yg = False
        self.menu_small_material_yg_l.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.is_zz = False
        self.menu_small_material_zz_l.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.is_yy = False
        self.menu_small_material_yy_l.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.is_mgd = False
        self.menu_small_material_mgd_l.setStyleSheet(MenuStyle.sugar_no_changed_style)

    @pyqtSlot()
    def on_menu_config_add_btn_clicked(self):
        num = self.menu_config_number_l.text()
        new_num = int(num) + 1
        self.menu_config_number_l.setText(str(new_num))
        self.change_menu_config_broad.emit(str(new_num))
        self.menu_recalculate()

    @pyqtSlot()
    def on_menu_config_del_btn_clicked(self):
        num = self.menu_config_number_l.text()
        if int(num) > 1:
            new_num = int(num) - 1
            self.menu_config_number_l.setText(str(new_num))
            self.change_menu_config_broad.emit(str(new_num))
            self.menu_recalculate()

    def menu_recalculate(self):
        tee_price = 0.0
        if self.menu_weight_value == '1':
            str_price = self.weight_mid_money_l.text().replace('￥', '')
            tee_price = tee_price + float(str_price)
        elif self.menu_weight_value == '2':
            str_price = self.weight_big_money_l.text().replace('￥', '')
            tee_price = tee_price + float(str_price)
        if self.is_cbb:
            tee_price = tee_price + 2.0
        if self.is_yg:
            tee_price = tee_price + 2.0
        if self.is_zz:
            tee_price = tee_price + 2.0
        if self.is_yy:
            tee_price = tee_price + 2.0
        if self.is_mgd:
            tee_price = tee_price + 2.0
        tee_number = int(self.menu_config_number_l.text())
        format_tee_price = "{:.2f}".format(tee_price * tee_number)
        self.menu_money_l.setText(str(format_tee_price))

    # 小料 糖
    def menu_sugar_style_changed(self, is_normal, is_5, is_3):
        self.menu_sugar_normal.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.menu_sugar_5.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.menu_sugar_3.setStyleSheet(MenuStyle.sugar_no_changed_style)
        if is_normal:
            self.menu_sugar_normal.setStyleSheet(MenuStyle.sugar_changed_style)
        if is_5:
            self.menu_sugar_5.setStyleSheet(MenuStyle.sugar_changed_style)
        if is_3:
            self.menu_sugar_3.setStyleSheet(MenuStyle.sugar_changed_style)

    # 小料 冰
    def menu_ice_style_changed(self, is_low, is_normal, is_0):
        self.menu_ice_low.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.menu_ice_normal.setStyleSheet(MenuStyle.sugar_no_changed_style)
        self.menu_ice_0.setStyleSheet(MenuStyle.sugar_no_changed_style)
        if is_low:
            self.menu_ice_low.setStyleSheet(MenuStyle.sugar_changed_style)
        if is_normal:
            self.menu_ice_normal.setStyleSheet(MenuStyle.sugar_changed_style)
        if is_0:
            self.menu_ice_0.setStyleSheet(MenuStyle.sugar_changed_style)

    def wbtn_menu_add_cart_btn_clicked(self):
        if self.is_login or self.is_debug:
            # 加入购物车
            menu_shopping_cart_bean = MenuShoppingCartBean()
            menu_shopping_cart_bean.set_name(self.menu_config_name_l.text())
            menu_shopping_cart_bean.set_number(self.menu_config_number_l.text())
            if self.menu_weight_value == '1':
                menu_shopping_cart_bean.set_size('中杯')
                menu_shopping_cart_bean.set_price(str(self.menu_tee_price))
            elif self.menu_weight_value == '2':
                menu_shopping_cart_bean.set_size('大杯')
                big_price = float(self.menu_tee_price) * 1.2
                format_big_price = "{:.2f}".format(big_price)
                menu_shopping_cart_bean.set_price(str(format_big_price))
            if self.menu_sugar_value == '1':
                menu_shopping_cart_bean.set_suger('常规')
            elif self.menu_sugar_value == '2':
                menu_shopping_cart_bean.set_suger('五分糖')
            elif self.menu_sugar_value == '3':
                menu_shopping_cart_bean.set_suger('三分糖')
            menu_shopping_cart_bean.set_is_cbb(self.is_cbb)
            menu_shopping_cart_bean.set_is_yg(self.is_yg)
            menu_shopping_cart_bean.set_is_zz(self.is_zz)
            menu_shopping_cart_bean.set_is_yy(self.is_yy)
            menu_shopping_cart_bean.set_is_mgd(self.is_mgd)
            if self.menu_ice_value == '1':
                menu_shopping_cart_bean.set_ice('少冰')
            elif self.menu_ice_value == '2':
                menu_shopping_cart_bean.set_ice('正常冰')
            elif self.menu_ice_value == '3':
                menu_shopping_cart_bean.set_ice('常温')
            menu_shopping_cart_bean.set_total(self.menu_money_l.text())
            menu_shopping_cart_bean.recipe = self.tee_recipe
            self.menu_add_shopping_cart_beans.append(menu_shopping_cart_bean)
            # self.change_add_btn_icon()

    def change_add_btn_icon(self):
        if len(self.menu_add_shopping_cart_beans) == 0:
            self.menu_add_cart_btn.setIcon(self.add_btn_none_style)
        else:
            self.menu_add_cart_btn.setIcon(self.add_btn_have_style)

    @pyqtSlot()
    # def on_menu_checkout_btn_clicked(self):   # 结账
    #     if self.is_login or self.is_debug:
    #         # 数据库查询 self.today_id 取茶号 今日订单数量
    #         # self.today_id = db_util.query_today_order_count() + 1
    #         # 数据库查询 self.today_product_id 今日奶茶数量
    #         # self.today_product_id = db_util.query_today_tea_quantity() + 1
    #         # 创建订单
    #         order_bean = OrderBean()
    #         date = datetime.now()
    #         order_num = date.strftime('%Y%m%d%H%M%S')
    #         order_id = f'O{order_num}'
    #         order_bean.order_id = order_id
    #         order_bean.order_time = date.strftime('%Y-%m-%d %H:%M:%S')
    #         self._ensure_daily_serials()
    #         self._log_db_and_serials("before_order")
    #         take_no = self.next_take_no
    #         order_bean.today_id = str(take_no)

    #         # prod_no = self.next_product_no
    #         print(f"[SER][build] take_no={take_no}, today_id(from DB)={order_bean.today_id}")
    #         for item_tee in self.menu_add_shopping_cart_beans:
    #             tee_bean = NewTeeBean()
    #             tee_bean.order_id = order_id
    #             tee_bean.today_id = order_bean.today_id
    #             # product_id = 'P1001'
    #             # 新：按订单的 today_id 显示为 PXXXX（4 位补零）
    #             # tee_bean.product_id = f"P{str(self.today_product_id).zfill(4)}"
    #             # self.today_product_id += 1
    #             # 先得到本单的基础 P 号（按你决定：P001、P002…）
    #             # 这里在 take_no / order_bean.today_id 已经确定之后生成 base_p
    #             # 你希望 P001 这种格式，所以用 3 位补零；超过 999 会自动变长（不会截断）
    #             try:
    #                 base_tid = int(order_bean.today_id)
    #             except Exception:
    #                 base_tid = int(take_no)

    #             base_p = f"P{base_tid:03d}"    # P001 / P002 / ...
    #             cup_seq = 0                   # 本单杯序号：01..100

    #             for item_tee in self.menu_add_shopping_cart_beans:
    #                 # 1) 读取这一行点了几杯（qty）
    #                 try:
    #                     qty = int(str(item_tee.get_number() or "1"))
    #                 except Exception:
    #                     qty = 1
    #                 qty = max(1, qty)

    #                 # 2) 计算“每杯单价”（优先用 get_price；若没有则 total/qty 兜底）
    #                 try:
    #                     unit_price_val = float(item_tee.get_price())
    #                 except Exception:
    #                     try:
    #                         unit_price_val = float(item_tee.get_total()) / qty
    #                     except Exception:
    #                         unit_price_val = 0.0
    #                 unit_price_str = "{:.2f}".format(unit_price_val)

    #                 # 3) 配料/加料选项，这一行的每杯都一样，先算一次
    #                 dishes_select = ''
    #                 if item_tee.get_is_cbb(): dishes_select += "脆啵啵,"
    #                 if item_tee.get_is_yy():  dishes_select += "芋圆,"
    #                 if item_tee.get_is_zz():  dishes_select += "珍珠,"
    #                 if item_tee.get_is_yg():  dishes_select += "椰果,"
    #                 if item_tee.get_is_mgd(): dishes_select += "玫果冻,"
    #                 dishes_select = dishes_select[:-1] if dishes_select else ''

    #                 # 4) 按 qty 拆成多杯，每杯一个 tee_bean（num_tee 固定为 1）
    #                 for _ in range(qty):
    #                     cup_seq += 1
    #                     tee_bean = NewTeeBean()
    #                     tee_bean.order_id = order_id
    #                     tee_bean.today_id = order_bean.today_id

    #                     # 核心：同单唯一杯码
    #                     tee_bean.product_id = f"{base_p}-{cup_seq:02d}"   # P001-01, P001-02...
    #                     print(f"[PDebug] menu order: base={base_p}, seq={cup_seq} -> product_id={tee_bean.product_id}")

    #                     tee_bean.product_name = str(item_tee.get_name())
    #                     tee_bean.product_sugar = item_tee.get_suger()
    #                     tee_bean.product_quantity = item_tee.get_size()
    #                     tee_bean.product_ice = item_tee.get_ice()
    #                     tee_bean.product_simp = dishes_select

    #                     tee_bean.unit_price = unit_price_str
    #                     tee_bean.num_tee = "1"

    #                     if self.is_debug:
    #                         tee_bean.state = '5'
    #                     else:
    #                         tee_bean.state = '3'

    #                     tee_bean.recipe = item_tee.recipe
    #                     order_bean.tee_list.append(tee_bean)


              
    #         # self.next_product_no = prod_no
    #         self.next_take_no += 1
    #         print(f"[SER][after_build] nextP={self.next_product_no} nextTake={self.next_take_no}")
    #         # 把订单数据保存到数据库
    #         order_bean.toString()
    #         # self.save_order_db_thread = OrderSaveToDB(order_bean)
    #         # self.save_order_db_thread.start()

    #         self.save_order_db_thread = OrderSaveToDB(order_bean)
    #         self.save_order_db_thread.done.connect(self.on_order_saved)   # 统一连这个
    #         self.save_order_db_thread.start()
    #         # 清空购物车
    #         self.menu_add_shopping_cart_beans = []
    #         # self.change_add_btn_icon()
    #         self.change_menu_add_cart_btn_state()
    #         # 刷新界面
    #         self.refresh_order_content()
    #         # 刷新记录界面
    #         # self.refresh_setting_local_tee()
    
    
    def on_menu_checkout_btn_clicked(self):   # 结账
        if self.is_login or self.is_debug:
            # 创建订单
            order_bean = OrderBean()
            date = datetime.now()
            order_num = date.strftime('%Y%m%d%H%M%S')
            order_id = f'O{order_num}'
            order_bean.order_id = order_id
            order_bean.order_time = date.strftime('%Y-%m-%d %H:%M:%S')

            # 取茶号（本单号）
            self._ensure_daily_serials()
            self._log_db_and_serials("before_order")
            take_no = self.next_take_no
            order_bean.today_id = str(take_no)

            # ===== 关键：本单基础 P 号 + 杯序号（只能在 order_bean/take_no 定义后）=====
            base_p = f"P{int(order_bean.today_id):03d}"   # P001 / P002 ...
            cup_seq = 0                                  # 本单杯序号：01..100

            print(f"[SER][build] take_no={take_no}, today_id={order_bean.today_id}, base_p={base_p}")

            # ===== 关键：只保留这一层循环，不要再套 “for item_car ...” 外层 =====
            for item_tee in self.menu_add_shopping_cart_beans:

                # 这一行点了几杯
                try:
                    qty = int(str(item_tee.get_number() or "1"))
                except Exception:
                    qty = 1
                qty = max(1, qty)

                # 单杯价：你加购物车时 set_price() 存的是单杯价
                try:
                    unit_price = str(item_tee.get_price())
                except Exception:
                    # 兜底：如果没有 get_price，就先用 get_total
                    unit_price = str(item_tee.get_total())

                # 配料选择（每杯相同）
                dishes_select = ''
                if item_tee.get_is_cbb():
                    dishes_select += "脆啵啵,"
                if item_tee.get_is_yy():
                    dishes_select += "芋圆,"
                if item_tee.get_is_zz():
                    dishes_select += "珍珠,"
                if item_tee.get_is_yg():
                    dishes_select += "椰果,"
                if item_tee.get_is_mgd():
                    dishes_select += "玫果冻,"
                dishes_select = dishes_select[:-1] if dishes_select else ''

                # 按 qty 拆成多杯：每杯一个 tee_bean，一个唯一编号
                for _ in range(qty):
                    cup_seq += 1

                    tee_bean = NewTeeBean()
                    tee_bean.order_id = order_id
                    tee_bean.today_id = order_bean.today_id

                    # 01~99 两位；100 显示 100（不会截断）
                    suffix = f"{cup_seq:02d}" if cup_seq < 100 else str(cup_seq)
                    tee_bean.product_id = f"{base_p}-{suffix}"    # P001-01, P001-02...

                    tee_bean.product_name = str(item_tee.get_name())
                    tee_bean.product_sugar = item_tee.get_suger()
                    tee_bean.product_quantity = item_tee.get_size()
                    tee_bean.product_ice = item_tee.get_ice()
                    tee_bean.product_simp = dishes_select
                    tee_bean.unit_price = unit_price

                    # 拆杯后每条都是 1 杯
                    tee_bean.num_tee = "1"

                    tee_bean.state = '5' if self.is_debug else '3'
                    tee_bean.recipe = item_tee.recipe

                    order_bean.tee_list.append(tee_bean)

                    print(f"[PDebug] {tee_bean.product_id}  name={tee_bean.product_name}  price={tee_bean.unit_price}")

            # 下一单取茶号 +1
            self.next_take_no += 1
            print(f"[SER][after_build] nextTake={self.next_take_no}")

            # 保存订单到数据库
            self.save_order_db_thread = OrderSaveToDB(order_bean)
            self.save_order_db_thread.done.connect(self.on_order_saved)
            self.save_order_db_thread.start()

            # 清空购物车并刷新界面
            self.menu_add_shopping_cart_beans = []
            self.change_menu_add_cart_btn_state()
            self.refresh_order_content()


    #设置消息的函数
    def set_message_info(self, message_type, message_level, message_content):
        message_bean = MessageBean()
        date = datetime.now()
        message_bean.message_id = db_util.get_next_message_id()
        message_bean.message_type = message_type
        message_bean.message_level = message_level
        message_bean.message_content = message_content
        message_bean.time = date.strftime('%Y-%m-%d %H:%M:%S')
        message_bean.toString()
        self.save_message_db_thread = MessageSaveToDB(message_bean)
        self.save_message_db_thread.start() 

    @pyqtSlot()
    def on_btn_title_help_clicked(self):
        print("点击了帮助")

    # TODO 手动出茶 <---

    # TODO ---> 管理界面
    def _get_manager_selected_cids(self):
        """兜底扫描管理页卡片，防止 select_conduit_bean 被别的重名函数覆盖"""
        sel = set()
        for c in getattr(self, "conduit_card_widgets", []):
            try:
                # 优先读自带的“是否选中”接口
                if hasattr(c, "get_checked"):
                    is_checked = bool(c.get_checked())
                elif hasattr(c, "checked"):
                    is_checked = bool(getattr(c, "checked"))
                elif hasattr(c, "_checked"):
                    is_checked = bool(getattr(c, "_checked"))
                else:
                    is_checked = False
            except Exception:
                is_checked = False

            if not is_checked:
                continue

            # 从卡片 UI 里拿通道号（Ui_conduit_card_ui.py 里的对象名）
            cid = None
            try:
                cid = c.ui.conduit_card_id_l.text()  # 例如 “1#”
            except Exception:
                pass
            if cid:
                cid = cid if cid.endswith("#") else f"{cid}#"
                sel.add(cid)
        return sorted(list(sel), key=lambda s: int(''.join(ch for ch in s if ch.isdigit()) or "0"))

    def out_conduit(self, operation_name: str):
        """管理页：出料/退料/单管满管 统一入口"""
        # 1) 克数
        raw = (self.lineEdit.text() if getattr(self, "lineEdit", None) else "").strip()
        grams = ''.join(ch for ch in raw if ch.isdigit())
        if grams == '':
            self.show_toast("请输入克数")
            return

        # 2) 选中的通道
        sel = getattr(self, "select_conduit_bean", None)
        if isinstance(sel, str):
            sel = [sel]
        if not sel:
            sel = self._get_manager_selected_cids()

        if not sel:
            self.show_toast("请先在管理界面选中一个通道卡片")
            return

        print(f"[manager OUT] {operation_name}, sel={sel}, grams={grams}")
        # 你的串口线程已有信号 conduit_manager_out(operation_name, sel, grams)
        self.conduit_manager_out.emit(operation_name, sel, grams)
    def on_material_packet(self, pkt: dict):
        # 取 4 位邮编来源：优先 origin，其次 origin_zip4/zip4/postal 等（按你后端实际键名选一个）
        raw_zip = pkt.get('origin') or pkt.get('origin_zip4') or pkt.get('zip4') or ""
        pretty_origin = self._lookup_zip4(raw_zip)
        if pretty_origin:
            pkt = dict(pkt)  # 复制一份，避免修改原引用
            pkt['origin'] = pretty_origin   # 弹窗会显示这个字段作为“产地”

        max_ch = getattr(self, "conduit_id_num", 23) or 23
        self._channel_picker = ChannelSelectDialog(
            material_name=pkt.get('material_name', ''),
            code=pkt.get('code',''),
            max_channel=max_ch,
            details=pkt,            # ← details 里 now: 'origin' 已是 “广东省 珠海市”
            parent=self
        )
        self._channel_picker.setWindowModality(Qt.ApplicationModal)
        self._channel_picker.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self._channel_picker.accepted.connect(lambda ch: self._apply_channel_for_material(pkt, ch))
        self._channel_picker.show(); self._channel_picker.raise_(); self._channel_picker.activateWindow()



    def _apply_channel_for_material(self, pkt: dict, channel: int):
        # 1) 更新该通道的物料名称（只改 name；如需清零库存，可在 _update_channel_material 里放开清零行）
        ok = self._update_channel_material(channel, pkt.get('material_name', ''))
        if not ok:
            QMessageBox.warning(self, "提示", f"更新失败：未找到第 {channel}# 通道或数据库写入错误")
            return

        # 2) 可选：把编码/有效期等字段也写入你们的表（若有对应字段）
        # db_util.update_conduit_extra_fields(channel, code=pkt.get('code'), ...)

        # 3) 刷新UI（把数据库里最新的通道列表回灌到前端）
        try:
            self._emit_full_conduit_refresh()
        except Exception as e:
            print(f"[refresh] emit error: {e}")

        # 4) 友好提示
        # QMessageBox.information(self, "成功", f"已将「{pkt.get('material_name','')}」分配到通道 {channel}#")


    # ========= a..w 材料识别：弹窗选通道 → 更新 DB → 刷新卡片 =========
    def on_material_detected(self, code: str, material_name: str):
        max_ch = getattr(self, "conduit_id_num", 23) or 23
        picker = ChannelSelectDialog(material_name=material_name, code=code, max_channel=max_ch, parent=self)

        def _open_editor(channel: int):
            rows = db_util.query_all_conduit_info() or []
            idx = channel - 1
            if not (0 <= idx < len(rows)):
                QMessageBox.warning(self, "提示", f"未找到第 {channel}# 通道的记录")
                return
            d = rows[idx]

            bean = NewConduitBean()
            bean.id = str(d.get('_id'))
            bean.conduit = d.get('conduit')
            bean.margin = d.get('margin')
            bean.max_capacity = d.get('max_capacity')
            bean.conduit_type = d.get('conduit_type')
            bean.name = d.get('name')
            bean.shield = d.get('shield')
            bean.begin_time = d.get('begin_time')
            bean.effective_time = d.get('effective_time')
            bean.red_warning_value = d.get('red_warning_value')
            bean.yellow_warning_value = d.get('yellow_warning_value')

            dlg = NewConduitDialog(bean, self)  # 这就是你图里的绿色编辑弹窗
            try:
                dlg.edit_name.setText(str(material_name))  # 预填名称
            except Exception as e:
                print(f"[preset name] {e}")

            if hasattr(dlg, "result_new_conduit_bean"):
                dlg.result_new_conduit_bean.connect(lambda _: self._emit_full_conduit_refresh())

            dlg.setWindowModality(Qt.ApplicationModal)
            dlg.show()

        picker.accepted.connect(_open_editor)
        picker.show()


    def _update_channel_material(self, channel: int, material_name: str) -> bool:
        """
        在不改动你 db_util 的前提下：
        - 先 query_all_conduit_info()
        - 支持按多种形式匹配通道：P100{n}/P10{nn}/'{n}#'/'{n}'
        - 命中后只改 name 字段（用你已有的 update_conduit_info），其它字段保持原值
        * 如需同时清零库存：再调用 db_util.update_conduit_margin_info(_id, '0')
        """
        rows = db_util.query_all_conduit_info()
        if not rows:
            return False

        # 候选的“conduit”值（按你项目常见的几种命名来兜底）
        cand = set()
        cand.add(f"P{1000 + channel}")         # P1001..P1023
        cand.add(f"{channel}#")                 # "1#" 这种
        cand.add(str(channel))                  # "1"   这种

        # 找到对应记录
        target = None
        for r in rows:
            cval = str(r.get("conduit", "")).strip()
            if cval in cand:
                target = r
                break

        if target is None:
            # 兜底：按顺序取第 channel 个（有些项目里就是顺序对应）
            idx = channel - 1
            if 0 <= idx < len(rows):
                target = rows[idx]
            else:
                return False

        _id = target.get("_id")
        # 读取其它原值，沿用你已有的 update_conduit_info 签名
        conduit_type = target.get("conduit_type", "")
        shield = target.get("shield", "1")
        effective_time = target.get("effective_time", "")
        begin_time = target.get("begin_time", "")
        red_warning_value = target.get("red_warning_value", "")
        yellow_warning_value = target.get("yellow_warning_value", "")

        try:
            # 只改 name，其他字段按原值回写
            db_util.update_conduit_info(
                _id=_id,
                conduit_type=conduit_type,
                name=str(material_name),
                shield=shield,
                effective_time=effective_time,
                begin_time=begin_time,
                red_warning_value=red_warning_value,
                yellow_warning_value=yellow_warning_value
            )
            # 如果你想“换料后库存清零”，放开下面这一行：
            # db_util.update_conduit_margin_info(_id, "0")
            return True
        except Exception as e:
            print(f"[on_material_detected] 更新失败: {e}")
            return False

    def _emit_full_conduit_refresh(self):
        try:
            from bean.new_conduit_bean import NewConduitBean
            rows = db_util.query_all_conduit_info()
            beans = []
            for d in rows:
                b = NewConduitBean()
                b.id = str(d.get('_id'))
                b.conduit = d.get('conduit')
                b.margin = d.get('margin')
                b.max_capacity = d.get('max_capacity')
                b.conduit_type = d.get('conduit_type')
                b.name = d.get('name')
                b.shield = d.get('shield')
                b.begin_time = d.get('begin_time')
                b.effective_time = d.get('effective_time')
                b.red_warning_value = d.get('red_warning_value')
                b.yellow_warning_value = d.get('yellow_warning_value')
                beans.append(b)
            # 直接用你现成的方法广播到 UI
            self.update_conduit_data(beans)
        except Exception as e:
            print(f"[refresh] 刷新通道卡片异常: {e}")


    @pyqtSlot()
    def on_btn_manager_out_clicked(self):
        self.out_conduit("出料")

    @pyqtSlot()
    def on_btn_manager_out_2_clicked(self):  
        self.out_conduit("退料")      
            
    @pyqtSlot()
    def on_btn_manager_all_clicked(self):
        if self.is_login or self.is_debug:
            print('一键满管')
            self._do_stop_safe()



            

    @pyqtSlot()
    def on_btn_manager_one_clicked(self):
        if self.is_login or self.is_debug:
            print('单管满管')
            # self.conduit_manager_one.emit("单管满管", self.select_conduit_bean)
            self.do_single_full_with_dialog()
    # TODO 管理界面 <---

    # TODO ---> 清洗菜单功能
    def init_clean_day_widget(self):
        self.clean_load_Layout = QHBoxLayout(self.clean_load_widget)
        self.clean_load_Layout.setObjectName("clean_load_Layout")
        self.clean_load_Layout.setContentsMargins(0, 0, 0, 0)
        self.clean_load_Layout.setSpacing(0)

    def switch_clean_day_week_load(self, is_day):
        util.clear_layout(self.clean_load_Layout)
        self.is_day = is_day
        if is_day:
            # 创建 日洗 widget
            self.clean_day_ui = CleanDayLoadMata(total_time = self.T)
            self.clean_week_ui = CleanWeekLoadMata(total_time = self.T)
            self.clean_begin_notice.connect(self.clean_day_ui.clean_begin)  # 开始按钮被按下后，传递到函数self.clean_day_ui.clean_begin中
            self.clean_pause_notice.connect(self.clean_day_ui.clean_pause)
            self.clean_stop_notice.connect(self.clean_day_ui.clean_stop)
             
            self.clean_load_Layout.addWidget(self.clean_day_ui)

            self.clean_complete_date.setText('00:00:00')
        else:
            # 创建 周洗 widget                目前周洗和日洗的剩余时间，完成时间一样
            self.clean_week_ui = CleanWeekLoadMata(total_time = self.T)
            self.clean_begin_notice.connect(self.clean_week_ui.clean_begin)
            self.clean_pause_notice.connect(self.clean_week_ui.clean_pause)
            self.clean_stop_notice.connect(self.clean_week_ui.clean_stop)
            self.clean_load_Layout.addWidget(self.clean_week_ui)

            self.clean_complete_date.setText('00:00:00')
        
            
    def get_work_conduit_bean(self, conduit_beans):  ###
        self.work_conduit_bean = []
        for conduit_item in conduit_beans:
            if str(conduit_item.get_shield()) != "2":  #等于2的是被屏蔽的，排除掉
                self.work_conduit_bean.append(conduit_item)

    def notice_clean_time(self, minutes, seconds):   ###
        self.clean_l_date_min = minutes
        self.clean_l_date_sec = seconds
        # 剩余总秒数（递减）
        self.complete_time = self.clean_l_date_min * 60 + self.clean_l_date_sec

        if self.complete_time == 0:
            # 倒计时结束：停止顺序清洗
            self._stop_daily_clean_sequence()

            # 原有逻辑：提示“清洗完成”并刷新本地记录
            self.set_message_info("清洗完成", "绿色", "清洗已完成")
            self.refresh_setting_local_message()  # 刷新message

    def calculate_completion_time(self, current_time, min, sec):   ###
        # 假设 current_time 是字符串，先转换为 datetime 对象
        current_time = datetime.strptime(current_time, "%H:%M:%S")
        # 计算完成时间
        self.complete_time = current_time + timedelta(minutes=abs(min), seconds=abs(sec))#计算完成时间 = 当前时间 + 剩余时间
        # 将完成时间格式化为字符串
        complete_time_str = self.complete_time.strftime("%H:%M:%S")
        # 设置完成时间
        return complete_time_str

    @pyqtSlot()
    def on_clean_begin_clicked(self):  # 当清洗开始按钮被按下触发
        if self.is_login or self.is_debug:  # 检查是否登录
            # 串口：开始清洗 -> 顺序清洗（日洗）
            self._start_daily_clean_sequence()

            # 清洗开始
            self.clean_pause.setChecked(False)
            self.clean_begin.setChecked(True)
            if self.is_start:        # 如果已经被按过了（暂停后再开始）
                self.clean_day_state()
            else:
                self.current_time = datetime.now().strftime('%H:%M:%S')  # 更新当前时间
                # 计算清洗总时长 以秒为单位
                if self.is_day:
                    per_channel = (
                        (self._daily_clean_pump_delay_ms + self._daily_clean_stop_delay_ms) / 1000
                        + self._daily_clean_channel_seconds
                    )
                    self.T = int(len(self._daily_clean_channels) * per_channel)
                else:
                    self.T = int(math.ceil(len(self.work_conduit_bean) / 3) * self.interval * self.count)
                print(f"self.T:{self.T}")
                print(f"{self.T / 60}分钟")
                min, sec = divmod(self.T, 60)  # 拆分成分秒
                self.complete_time = self.calculate_completion_time(self.current_time, min, sec)  # 获得完成时间
                self.clean_complete_date.setText(self.complete_time)  # 设置完成时间
                self.clean_T.emit(self.T)  # 发射开始清洗总时长
                self.clean_begin_notice.emit(self.work_conduit_bean, self.T)
                self.is_start = True

        if not self.is_login:
            self.clean_begin.setChecked(False)

    @pyqtSlot()
    def on_clean_pause_clicked(self):    # 清洗暂停按钮
        if self.is_login or self.is_debug:
            # 只有在已经开始清洗的情况下，点击暂停才发关闭命令
            if self.is_start:
                # 串口：暂停 -> 停主泵并 stop 当前通道
                self._pause_daily_clean_sequence()

                # 清洗暂停
                self.clean_begin.setChecked(False)
                self.clean_pause.setChecked(True)
                self.clean_day_state()
            else:
                self.clean_pause.setChecked(False)

        if not self.is_login:
            self.clean_pause.setChecked(False)
    @pyqtSlot()
    def on_clean_stop_clicked(self):   # 清洗停止按钮
        if self.is_login or self.is_debug:
            # 串口：停止 -> 停主泵并 stop 当前通道
            self._stop_daily_clean_sequence()

            # 清洗停止
            self.clean_begin.setChecked(False)
            self.clean_pause.setChecked(False)
            self.clean_stop_notice.emit()
            self.is_start = False
            self.clean_complete_date.setText("00:00:00")  # 设置完成时间

    def clean_day_state(self):   #暂停的状态判断
        if self.clean_pause.isChecked():
            self.clean_pause_notice.emit(False)
            # print("暂停了")
        elif not self.clean_pause.isChecked():
            self.clean_pause_notice.emit(True)
            # print("没暂停")
            self.current_time = datetime.now().strftime('%H:%M:%S')   #获取当前时间
            print(f"clean_l_date_min: {self.clean_l_date_min}, clean_l_date_sec: {self.clean_l_date_sec}")
            self.complete_time = self.calculate_completion_time(self.current_time, int(self.clean_l_date_min), int(self.clean_l_date_sec))  #暂停了再点击开始要更新时间
            self.clean_complete_date.setText(self.complete_time)#设置完成时间

    # === 每日清洗顺序控制 ===
    def _clean_seq_send(self, cmd: str):
        th = getattr(self, "conduit_serial_thread", None)
        if not (th and th.isRunning()):
            print("[clean_seq] serial thread not running")
            return False
        th.send_data(cmd)
        return True

    def _start_daily_clean_sequence(self):
        if self._clean_seq_active:
            return
        self._clean_seq_active = True
        self._clean_seq_paused = False
        self._clean_seq_index = 0
        self._clean_seq_token += 1
        self._clean_seq_current_channel = ""
        self._run_next_clean_channel(self._clean_seq_token)

    def _pause_daily_clean_sequence(self):
        if not self._clean_seq_active:
            return
        self._clean_seq_paused = True
        self._clean_seq_token += 1
        # 先关主泵，再 stop 当前通道
        self._clean_seq_send("clean1_off")
        self._clean_seq_send("stop")

    def _stop_daily_clean_sequence(self):
        if not self._clean_seq_active:
            return
        self._clean_seq_active = False
        self._clean_seq_paused = False
        self._clean_seq_token += 1
        # 先关主泵，再 stop 当前通道
        self._clean_seq_send("clean1_off")
        self._clean_seq_send("stop")
        self._clean_seq_current_channel = ""

    def _run_next_clean_channel(self, token: int):
        if not self._clean_seq_active or self._clean_seq_paused or token != self._clean_seq_token:
            return
        if self._clean_seq_index >= len(self._daily_clean_channels):
            # 全部完成
            self._clean_seq_active = False
            self._clean_seq_current_channel = ""
            self._clean_seq_send("clean1_off")
            self._clean_seq_send("stop")
            return

        ch = self._daily_clean_channels[self._clean_seq_index]
        self._clean_seq_current_channel = ch
        cmd = f"{ch}{self._daily_clean_value:03d}"
        if not self._clean_seq_send(cmd):
            return

        # 1秒后开主泵
        QtCore.QTimer.singleShot(
            self._daily_clean_pump_delay_ms,
            lambda t=token: self._clean_seq_turn_on_pump(t)
        )

    def _clean_seq_turn_on_pump(self, token: int):
        if not self._clean_seq_active or self._clean_seq_paused or token != self._clean_seq_token:
            return
        self._clean_seq_send("clean1_on")

        # 30秒后关主泵
        QtCore.QTimer.singleShot(
            self._daily_clean_channel_seconds * 1000,
            lambda t=token: self._clean_seq_turn_off_pump(t)
        )

    def _clean_seq_turn_off_pump(self, token: int):
        if not self._clean_seq_active or self._clean_seq_paused or token != self._clean_seq_token:
            return
        self._clean_seq_send("clean1_off")

        # 1秒后 stop 通道，并进入下一通道
        QtCore.QTimer.singleShot(
            self._daily_clean_stop_delay_ms,
            lambda t=token: self._clean_seq_stop_channel_and_next(t)
        )

    def _clean_seq_stop_channel_and_next(self, token: int):
        if not self._clean_seq_active or self._clean_seq_paused or token != self._clean_seq_token:
            return
        self._clean_seq_send("stop")
        self._clean_seq_index += 1
        self._run_next_clean_channel(token)

    # TODO 清洗菜单功能 <---

    # TODO ---> 设置菜单功能
    # 登录
    @pyqtSlot()
    def on_btn_setting_login_clicked(self):   #登录按钮按下
        if not self.is_debug:
            self.login_ui = LoginMata()
            self.login_ui.login_result.connect(self.result_callBack)
            self.login_ui.result_location.connect(self.set_location)
            self.login_ui.show()

    def result_login_callBack(self, phone_number, store_id, token, nickname):    #没用到
        self.token = token
        self.phone_number = phone_number
        self.store_id = store_id
        self.nickname = nickname
        self.init_login_in_state(nickname)
        self.order_thread = OrderThread(phone_number, store_id, token, nickname)
        self.order_thread.result_tee_bean.connect(self.show_tee_order)
        self.order_thread.start()

    def result_callBack(self, is_login):    #验证密码正确与错误时的不同操作
        self.is_login = is_login
        self._mk_flush_buffer()    # ← 加这一行
        self.switch_login_init(is_login)
        if is_login:
            self.btn_setting_login.setHidden(True)
            self.btn_setting_exit.setHidden(False)
        else:
            self.btn_setting_exit.setHidden(True)
            self.btn_setting_login.setHidden(False)
            self.message_info_ui = MessageDialog()
            self.message_info_ui.show()
        self.menu_btn_state_change(True, False, False, False,False)
        self.stackedWidget.setCurrentWidget(self.sw_outtee_widget)

    def login_state_callBack(self, is_login):    #退出按钮按下时的变化
        self.is_login = is_login
        self._mk_flush_buffer()    # ← 加这一行
        self.switch_login_init(is_login)
        if is_login:
            self.btn_setting_login.setHidden(True)
            self.btn_setting_exit.setHidden(False)
        else:
            self.btn_setting_exit.setHidden(True)
            self.btn_setting_login.setHidden(False)

    def set_location(self, ip):
        self.l_title_store_name_2.setText(ip)

    # 退出
    @pyqtSlot()
    def on_btn_setting_exit_clicked(self):  #退出按钮
        self.init_not_login_in_state()
        self.login_state_callBack(False)

    # 返回设置主页
    @pyqtSlot()
    def on_btn_back_setting_clicked(self):
        self.stackedWidget_setting.setCurrentWidget(self.setting_home)

    # 订单按钮
    @pyqtSlot()
    def on_btn_setting_order_clicked(self):
        if self.btn_setting_order.isChecked():
            self.stackedWidget_setting_location.setCurrentWidget(self.location_order)
            self.btn_setting_message.setChecked(False)
        self.btn_setting_order.setChecked(True)

    # 消息按钮
    @pyqtSlot()
    def on_btn_setting_message_clicked(self):
        if self.btn_setting_message.isChecked():
            self.stackedWidget_setting_location.setCurrentWidget(self.location_message)
            self.btn_setting_order.setChecked(False)
        self.btn_setting_message.setChecked(True)

    # 当订单增加时需要调用此接口
    def refresh_setting_local_tee(self):
        self.refresh_setting_local_tee_thread = RefreshSettingLocalTeeThread()
        self.refresh_setting_local_tee_thread.return_local_tee_record.connect(self.add_item_order_content)
        self.refresh_setting_local_tee_thread.start()
    
    def init_setting_order_content_widget(self):
        self.setting_order_content_Layout = QVBoxLayout(self.order_content)
        self.setting_order_content_Layout.setObjectName("setting_order_content_Layout")
        self.setting_order_content_Layout.setContentsMargins(0, 0, 0, 0)
        self.setting_order_content_Layout.setSpacing(0)

    def init_setting_order_content_page_btn_widget(self):
        self.setting_local_tee_page_Layout = QHBoxLayout(self.setting_local_tee_page)
        self.setting_local_tee_page_Layout.setObjectName("setting_local_tee_page_Layout")
        self.setting_local_tee_page_Layout.setContentsMargins(0, 0, 0, 0)
        self.setting_local_tee_page_Layout.setSpacing(16)

    @pyqtSlot()
    def on_btn_setting_order_tee_switch_clicked(self):    
        if self.is_complete:
            self.is_complete = False
            self.show_complete_or_lack_tee(self.complete_tee_bean_list)
        else:
            self.is_complete = True
            self.show_complete_or_lack_tee(self.lack_tee_bean_list)

    def add_item_order_content(self, complete_bean_list, lack_bean_list):
        self.complete_tee_bean_list = complete_bean_list
        self.lack_tee_bean_list = lack_bean_list
        self.is_complete = False
        self.show_complete_or_lack_tee(complete_bean_list)

    def selected_lack_tee_bean(self, tee_bean):
        self.setting_local_tee_record_notice_restore.emit()
        self.check_tee_bean = tee_bean

    #本地订单界面的出茶
    @pyqtSlot()
    def on_btn_setting_out_tee_clicked(self):
        # 开始制作 不创建订单 不修改原来奶茶状态
        if self.check_tee_bean is not None:
            print(f'开始制作 不创建订单 不修改原来奶茶状态:{self.check_tee_bean.product_name}')
            # print(f"配方：{self.check_tee_bean.recipe}")
            self.make_tee_notice_data.emit(self.check_tee_bean.recipe)  #可以发送命令


        # 刷新界面
        # self.refresh_order_content()
        # # 刷新记录界面
        # self.refresh_setting_local_tee()

    def show_complete_or_lack_tee(self, tee_list):    #订单界面的显示
        util.clear_layout(self.setting_order_content_Layout)
        util.clear_layout(self.setting_local_tee_page_Layout)
        order_content_first_list = tee_list[0:11]
        # 设置第一页显示
        for num in range(len(order_content_first_list)):
            is_d = False
            if num % 2 == 0:  #2，4，6，8等等位置的为True
                is_d = True
            if num == 0:
                if self.is_complete:
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(order_content_first_list[num], is_d,
                                                                                True)
                    setting_local_tee_record_ui.notice_checked.connect(self.selected_lack_tee_bean)
                    self.setting_local_tee_record_notice_restore.connect(setting_local_tee_record_ui.change_style)
                else:
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(order_content_first_list[num], is_d,
                                                                                True)
                    setting_local_tee_record_ui.notice_checked.connect(self.selected_lack_tee_bean)
                    self.setting_local_tee_record_notice_restore.connect(setting_local_tee_record_ui.change_style)
            else:
                if self.is_complete:
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(order_content_first_list[num], is_d,
                                                                                True)
                    setting_local_tee_record_ui.notice_checked.connect(self.selected_lack_tee_bean)
                    self.setting_local_tee_record_notice_restore.connect(setting_local_tee_record_ui.change_style)
                else:
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(order_content_first_list[num], is_d,
                                                                                True)
                    setting_local_tee_record_ui.notice_checked.connect(self.selected_lack_tee_bean)
                    self.setting_local_tee_record_notice_restore.connect(setting_local_tee_record_ui.change_style)
            self.setting_order_content_Layout.addWidget(setting_local_tee_record_ui)
        # 设置翻页按钮
        num = len(tee_list) // 11
        y_num = len(tee_list) % 11
        if y_num != 0:
            num += 1
        # 设置共多少页
        self.tee_record_page_count = int(num)
        self.order_number_page.setText(f'共{num}页')
        for i in range(num):
            if i == 0:
                btn_page_ui = BtnPageMata(i + 1, True)
            else:
                btn_page_ui = BtnPageMata(i + 1, False)
            btn_page_ui.switch_page.connect(self.setting_local_tee_page_switch)
            self.setting_local_tee_record_page_btn_no_check.connect(btn_page_ui.change_no_check)
            self.setting_local_tee_page_Layout.addWidget(btn_page_ui)
        # 设置容器宽度
        s_width = num * 50
        if s_width > 600:
            s_width = 600
        self.widget_84.setFixedWidth(s_width)
        self.setting_local_tee_record_current_page = 1
    
    #处理翻页操作，根据用户选择的页码显示相应页面的记录。
    def setting_local_tee_page_switch(self, num):
        # print("1111")
        if self.is_complete:
            bean_list = self.lack_tee_bean_list
        else:
            bean_list = self.complete_tee_bean_list
        self.setting_local_tee_record_page_btn_no_check.emit(num)
        if num == 1:
            index_num = 0
        else:
            index_num = (num - 1) * 11
        # 判断是不是最后一页
        if index_num + 11 > len(bean_list):
            last_index = len(bean_list) % 11
            # 是最后一页
            current_page_list = bean_list[index_num : index_num + last_index]
        else:
            current_page_list = bean_list[index_num : index_num + 11]
        util.clear_layout(self.setting_order_content_Layout)
        for item_num in range(len(current_page_list)):
            is_d = False
            if item_num % 2 == 0:
                is_d = True
            if item_num == 0:
                if self.is_complete:
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(current_page_list[item_num], is_d,
                                                                                True)
                    setting_local_tee_record_ui.notice_checked.connect(self.selected_lack_tee_bean)
                    self.setting_local_tee_record_notice_restore.connect(setting_local_tee_record_ui.change_style)
                else:
                    # setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(current_page_list[item_num], is_d,
                    #                                                             False)
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(current_page_list[item_num], is_d,
                                                                                True)
            else:
                if self.is_complete:
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(current_page_list[item_num], is_d,
                                                                                True)
                    setting_local_tee_record_ui.notice_checked.connect(self.selected_lack_tee_bean)
                    self.setting_local_tee_record_notice_restore.connect(setting_local_tee_record_ui.change_style)
                else:
                    # setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(current_page_list[item_num], is_d,
                    #                                                             False)   #True可选中历史订单，False不可选中
                    setting_local_tee_record_ui = ItemSettingLocalTeeRecordMata(current_page_list[item_num], is_d,
                                                                                True)
            self.setting_order_content_Layout.addWidget(setting_local_tee_record_ui)
        self.setting_local_tee_record_current_page = num

    # 茶订单上一页
    @pyqtSlot()
    def on_btn_order_last_page_clicked(self):
        if self.is_login:
            if self.setting_local_tee_record_current_page != 1:
                self.setting_local_tee_record_current_page -= 1
                self.setting_local_tee_page_switch(self.setting_local_tee_record_current_page)
                
    @pyqtSlot()
    def on_btn_order_next_page_clicked(self):
        if self.is_login:
            if self.setting_local_tee_record_current_page != self.tee_record_page_count:
                self.setting_local_tee_record_current_page += 1
                self.setting_local_tee_page_switch(self.setting_local_tee_record_current_page)

    # 刷新本地消息需要调用此接口
    def refresh_setting_local_message(self):
        self.refresh_setting_local_message_thread = RefreshSettingLocalMessageThread()
        self.refresh_setting_local_message_thread.return_local_message_record.connect(self.add_item_message_content)
        self.refresh_setting_local_message_thread.start()

    def init_setting_message_content_widget(self):
        self.setting_message_content_Layout = QVBoxLayout(self.message_content)
        self.setting_message_content_Layout.setObjectName("setting_message_content_Layout")
        self.setting_message_content_Layout.setContentsMargins(0, 0, 0, 0)
        self.setting_message_content_Layout.setSpacing(0)

    def init_setting_message_content_page_btn_widget(self):
        self.setting_local_message_page_Layout = QHBoxLayout(self.setting_local_message_page)
        self.setting_local_message_page_Layout.setObjectName("setting_local_message_page_Layout")
        self.setting_local_message_page_Layout.setContentsMargins(0, 0, 0, 0)
        self.setting_local_message_page_Layout.setSpacing(16)

    def add_item_message_content(self, message_list):
        if len(message_list) == 0:
            return
        util.clear_layout(self.setting_message_content_Layout)
        util.clear_layout(self.setting_local_message_page_Layout)
        self.all_message_bean_list = message_list
        # 设置出茶页面最新消息
        self.init_out_tee_message(message_list[0])
        message_content_first_list = message_list[0:11]
        # 设置第一页显示
        for num in range(len(message_content_first_list)):
            is_d = False
            if num % 2 == 0:
                is_d = True
            if num == 0:
                setting_local_tee_record_ui = ItemSettingLocalMessageRecordMata(message_content_first_list[num], is_d)
            else:
                setting_local_tee_record_ui = ItemSettingLocalMessageRecordMata(message_content_first_list[num], is_d)
            self.setting_message_content_Layout.addWidget(setting_local_tee_record_ui)
        # 设置翻页按钮
        num = len(message_list) // 11
        y_num = len(message_list) % 11
        if y_num != 0:
            num += 1
        # 设置共多少页
        self.message_record_page_count = int(num)
        self.message_number_page.setText(f'共{num}页')
        for i in range(num):
            print(f'本地记录创建message页码按钮')
            if i == 0:
                btn_page_ui = BtnPageMata(i + 1, True)
            else:
                btn_page_ui = BtnPageMata(i + 1, False)
            btn_page_ui.switch_page.connect(self.setting_local_message_page_switch)
            self.setting_local_message_record_page_btn_no_check.connect(btn_page_ui.change_no_check)
            self.setting_local_message_page_Layout.addWidget(btn_page_ui)
        # 设置容器宽度
        print(f'num:{num}')
        s_width = num * 50
        if s_width > 600:
            s_width = 600
        self.widget_89.setFixedWidth(s_width)
        self.setting_local_message_record_current_page = 1

    def setting_local_message_page_switch(self, num):
        self.setting_local_message_record_page_btn_no_check.emit(num)
        if num == 1:
            index_num = 0
        else:
            index_num = (num - 1) * 11
        # 判断是不是最后一页
        if index_num + 11 > len(self.all_message_bean_list):
            last_index = len(self.all_message_bean_list) % 11
            # 是最后一页
            current_page_list = self.all_message_bean_list[index_num: index_num + last_index]
        else:
            current_page_list = self.all_message_bean_list[index_num: index_num + 11]
        util.clear_layout(self.setting_message_content_Layout)
        for item_num in range(len(current_page_list)):
            is_d = False
            if item_num % 2 == 0:
                is_d = True
            if item_num == 0:
                setting_local_tee_record_ui = ItemSettingLocalMessageRecordMata(current_page_list[item_num], is_d)
            else:
                setting_local_tee_record_ui = ItemSettingLocalMessageRecordMata(current_page_list[item_num], is_d)
            self.setting_message_content_Layout.addWidget(setting_local_tee_record_ui)
        self.setting_local_message_record_current_page = num

    def init_out_tee_message(self, last_message_bean):
        if last_message_bean.message_level == '绿色':
            self.sw_scan_code_notice_widget.setStyleSheet(MenuStyle.sw_scan_code_notice_widget_green)
            self.icon_sw_scan_code_notice.setStyleSheet(MenuStyle.icon_sw_scan_code_notice_green)
        elif last_message_bean.message_level == '黄色':
            self.sw_scan_code_notice_widget.setStyleSheet(MenuStyle.sw_scan_code_notice_widget_yellow)
            self.icon_sw_scan_code_notice.setStyleSheet(MenuStyle.icon_sw_scan_code_notice_yellow)
        elif last_message_bean.message_level == '红色':
            self.sw_scan_code_notice_widget.setStyleSheet(MenuStyle.sw_scan_code_notice_widget_red)
            self.icon_sw_scan_code_notice.setStyleSheet(MenuStyle.icon_sw_scan_code_notice_red)
        self.msg_sw_scan_code_notice.setText(last_message_bean.message_type)

    # 消息上一页
    @pyqtSlot()
    def on_btn_message_last_page_clicked(self):
        if self.is_login:
            if self.setting_local_message_record_current_page != 1:
                self.setting_local_message_record_current_page -= 1
                self.setting_local_message_page_switch(self.setting_local_message_record_current_page)

    @pyqtSlot()
    def on_btn_message_next_page_clicked(self):
        if self.is_login:
            if self.setting_local_message_record_current_page != self.message_record_page_count:
                self.setting_local_message_record_current_page += 1
                self.setting_local_message_page_switch(self.setting_local_message_record_current_page)

    # 关闭副屏通知
    def close_second_screen(self):
        self.is_open_screen = False
        self.second_screen_ui = None
        self.wbtn_setting_second_screen.setStyleSheet(MenuStyle.screen_false_style)
    # def switch_order_and_message(self):

    def init_setting_conduit_widget(self):
        self.setting_conduit_content_Layout = QHBoxLayout(self.conduit_content)
        self.setting_conduit_content_Layout.setObjectName("order_content_Layout")
        self.setting_conduit_content_Layout.setContentsMargins(0, 30, 0, 30)
        self.setting_conduit_content_Layout.setSpacing(0)
        self.setting_conduit_gridLayout = QGridLayout()
        self.setting_conduit_gridLayout.setObjectName("order_gridLayout")
        self.setting_conduit_gridLayout.setHorizontalSpacing(20)
        self.setting_conduit_gridLayout.setVerticalSpacing(20)
        self.setting_conduit_content_Layout.addLayout(self.setting_conduit_gridLayout)

    def init_language_settings_page(self):
        if self._language_page_created:
            return
        self.language_settings_widget = LanguageSettingsPage(
            parent=self.sw_setting_widget,
            on_back=self._back_from_language_settings,
            on_apply_language=self.apply_language,
        )
        self.stackedWidget_setting.addWidget(self.language_settings_widget)
        self._language_page_created = True

    def _back_from_language_settings(self):
        self.stackedWidget_setting.setCurrentWidget(self.setting_home)

    def apply_language(self, lang: str):
        if not hasattr(self, "_lang_mgr"):
            return
        self._lang_mgr.apply(lang)
        try:
            self.retranslateUi(self)
        except Exception:
            pass
        try:
            if getattr(self, "language_settings_widget", None):
                self.language_settings_widget.ui.retranslateUi(self.language_settings_widget._mw)
        except Exception:
            pass
        try:
            if getattr(self, "language_settings_widget", None):
                ui = self.language_settings_widget.ui
                lab = getattr(ui, "label_4", None)
                txt = lab.text() if lab else None
                print(f"[lang] language_settings label_4 text -> {txt!r}")
        except Exception as e:
            print(f"[lang] debug read label_4 error: {e}")
        try:
            def _retranslate_widget(w):
                if w is None:
                    return
                try:
                    if hasattr(w, "retranslateUi"):
                        w.retranslateUi(w)
                except Exception:
                    pass
                try:
                    ui = getattr(w, "ui", None)
                    if ui is not None and hasattr(ui, "retranslateUi"):
                        ui.retranslateUi(w)
                except Exception:
                    pass
                try:
                    if hasattr(w, "retranslate_and_refresh"):
                        w.retranslate_and_refresh()
                except Exception:
                    pass

            # 订单卡片（订单号/实付等）
            for w in getattr(self, "order_card_widgets", []) or []:
                _retranslate_widget(w)

            # 菜单卡片（规格）
            for w in getattr(self, "menu_cards_by_name", {}).values():
                _retranslate_widget(w)

            # 管理页通道卡片（剩余量/到期时间）
            for w in getattr(self, "conduit_card_widgets", []) or []:
                _retranslate_widget(w)

            # 泡茶页通道卡片
            for w in getattr(self, "maketee_conduit_card_widgets", []) or []:
                _retranslate_widget(w)

            # 副屏通道卡片
            if getattr(self, "second_screen_ui", None):
                try:
                    self.second_screen_ui.retranslateUi(self.second_screen_ui)
                except Exception:
                    pass
                try:
                    for w in self.second_screen_ui.findChildren(ItemScreenConduitWMata):
                        _retranslate_widget(w)
                except Exception:
                    pass

            # 清洗页
            if getattr(self, "clean_day_ui", None):
                _retranslate_widget(self.clean_day_ui)
            if getattr(self, "clean_week_ui", None):
                _retranslate_widget(self.clean_week_ui)

            # 菜单更新页
            if getattr(self, "_menu_update_widget", None):
                _retranslate_widget(self._menu_update_widget)
        except Exception:
            pass

    def open_second_screen_change(self, is_open_screen):
            # 设置副屏显示
            if is_open_screen:
                self.is_open_screen = False
                self.on_setting_widget.setHidden(True)
                self.off_setting_widget.setHidden(False)
                if self.second_screen_ui is not None:
                    self.second_screen_ui.close()
                    self.second_screen_ui = None
            else:
                self.is_open_screen = True
                self.off_setting_widget.setHidden(True)
                self.on_setting_widget.setHidden(False)
                if len(self.screens_list) >= 2:
                    geo = self.screens_list[1].geometry()
                    self.second_screen_ui = SecondScreenMata(geo, self.conduit_beans)
                    self.second_screen_ui.show()
    # TODO 设置菜单功能 <---

    # TODO ---> 自定义按钮设置
    def init_custom_btn(self):
        # 主菜单按钮
        self.wbtn_menu_outtee.installEventFilter(self)
        self.wbtn_menu_manager.installEventFilter(self)
        self.wbtn_menu_maketee.installEventFilter(self)
        self.wbtn_menu_clean.installEventFilter(self)
        self.wbtn_menu_setting.installEventFilter(self)
        self.stackedWidget.setCurrentWidget(self.sw_outtee_widget)
        # off on 按钮切换
        self.on_off_widget.installEventFilter(self)
        self.auto_tee_state_change(True)
        # 扫码出茶 手动出茶
        self.wbtn_scan_code_outtee.installEventFilter(self)
        self.wbtn_mt_outtee.installEventFilter(self)
        self.scan_code_or_mt_state_change(True, False)
        self.stackedWidget_2.setCurrentWidget(self.sw_scan_code_widget)
        self.menu_add_cart_btn.installEventFilter(self)
        self.change_menu_add_cart_btn_state()
        # 份量
        self.menu_config_weight_big.installEventFilter(self)
        self.menu_config_weight_mid.installEventFilter(self)
        # 糖量
        self.menu_sugar_normal.installEventFilter(self)
        self.menu_sugar_5.installEventFilter(self)
        self.menu_sugar_3.installEventFilter(self)
        # 温度
        self.menu_ice_low.installEventFilter(self)
        self.menu_ice_normal.installEventFilter(self)
        self.menu_ice_0.installEventFilter(self)
        # 小料
        self.menu_small_material_cbb_l.installEventFilter(self)
        self.menu_small_material_yg_l.installEventFilter(self)
        self.menu_small_material_zz_l.installEventFilter(self)
        self.menu_small_material_yy_l.installEventFilter(self)
        self.menu_small_material_mgd_l.installEventFilter(self)
        # 扫码出茶通知栏
        self.sw_scan_code_notice_widget.installEventFilter(self)
        self.widget_2.installEventFilter(self)
        # 管理界面按钮
        # self.wbtn_manager_all.installEventFilter(self)
        # self.wbtn_manager_one.installEventFilter(self)
        # 管理界面键盘出发按钮
        self.widget_99.installEventFilter(self)
        self.lineEdit.installEventFilter(self)
        self.lineEdit.setReadOnly(True)
        self.lineEdit_2.installEventFilter(self)
        self.lineEdit_2.setReadOnly(True)
        self._mk_keyboard = None
        # 清洗界面按钮
        self.wbtn_clean_day.installEventFilter(self)
        self.wbtn_clean_week.installEventFilter(self)
        self.clean_btn_state_change(True, False, False)
        self.stackedWidget_3.setCurrentWidget(self.day_log)
        self.stackedWidget_clean.setCurrentWidget(self.clean)
        self.clean_begin.setCheckable(True)
        self.clean_begin.setChecked(False)
        # 设置界面按钮
        self.wbtn_setting_loacl_record.installEventFilter(self)
        self.wbtn_setting_debug.installEventFilter(self)
        self.wbtn_setting_second_screen.installEventFilter(self)
        self.wbtn_setting_second_screen_2.installEventFilter(self)
        self.wbtn_setting_update.installEventFilter(self)
        self._menu_update_widget = None
        # 设置开启副屏开关
        self.on_off_setting_widget.installEventFilter(self)
        self.open_second_screen_change(True)
        # 摄像头扫码
        self.camera_widget.installEventFilter(self)
        # 设置店名被点击事件
        self.l_title_store_name_2.installEventFilter(self)

    def eventFilter(self, obj, event):
        et = event.type()
        # 1) 点击任何位置：若有键盘且点击不在键盘内 -> 关闭
        if et == QEvent.MouseButtonPress:
            kb = getattr(self, "_kb", None)
            if kb and kb.isVisible():
                try:
                    if not kb.geometry().contains(event.globalPos()):
                        self._close_small_keyboard()
                except Exception:
                    self._close_small_keyboard()

        # 2) 点击/获得焦点：这些控件要弹小键盘（根据你的控件名）
        if et in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.FocusIn) \
        and obj in (getattr(self, "widget_99", None),
                    getattr(self, "lineEdit",  None),
                    getattr(self, "lineEdit_2",None)):
            # 点击图标(widget_99)时，键盘输入回填到管理页 lineEdit；
            # 点击泡茶页 lineEdit_2 时，回填到 lineEdit_2
            target = self.lineEdit if obj is getattr(self, "widget_99", None) or obj is getattr(self, "lineEdit", None) else self.lineEdit_2

            # 若键盘已打开且就是给同一 target 的，直接吞掉此次事件，防止重建引发闪烁
            if getattr(self, "_kb", None) and self._kb.isVisible() and self._kb_target is target:
                return True

            self._show_small_keyboard(target, anchor_widget=target, title="出料")
            return True  # 这类点击我们吞掉即可，避免冒泡造成二次触发

        # 3) 切到其它大页前，先收起键盘（避免键盘挡住并“看上去点不动”）
        if et == QEvent.MouseButtonPress and obj in (
            getattr(self, "wbtn_menu_outtee", None),
            getattr(self, "wbtn_menu_manager", None),
            getattr(self, "wbtn_menu_maketee", None),
            getattr(self, "wbtn_menu_clean", None),
            getattr(self, "wbtn_menu_setting", None),
        ):
            self._close_small_keyboard()


        # ---------- ③ 原有的菜单/按钮逻辑保持不变 ----------
        if event.type() == QEvent.MouseButtonPress:
            if obj == self.wbtn_menu_outtee:
                self.menu_btn_state_change(True, False, False, False, False)
                self.stackedWidget.setCurrentWidget(self.sw_outtee_widget)
            elif obj == self.wbtn_menu_manager:
                self.menu_btn_state_change(False, True, False, False, False)
                self.stackedWidget.setCurrentWidget(self.sw_manager_widget)
            elif obj == self.wbtn_menu_maketee:
                self.menu_btn_state_change(False, False, True, False, False)
                self.stackedWidget.setCurrentWidget(self.sw_maketee_widget)
            elif obj == self.wbtn_menu_clean:
                self.menu_btn_state_change(False, False, False, True, False)
                self.stackedWidget.setCurrentWidget(self.sw_clean_widget)
            elif obj == self.wbtn_menu_setting:
                self.menu_btn_state_change(False, False, False, False, True)
                self.stackedWidget.setCurrentWidget(self.sw_setting_widget)
                self.stackedWidget_setting.setCurrentWidget(self.setting_home)
                self.l_title_store_name_2.clearFocus()
            elif obj == self.on_off_widget:
                if self.is_login:
                    self.auto_tee_state_change(self.auto_isChecked)
            elif obj == self.wbtn_scan_code_outtee:
                self.scan_code_or_mt_state_change(True, False)
                self.stackedWidget_2.setCurrentWidget(self.sw_scan_code_widget)
            elif obj == self.wbtn_mt_outtee:
                self.scan_code_or_mt_state_change(False, True)
                self.stackedWidget_2.setCurrentWidget(self.sw_mt_widget)
            elif obj == self.menu_config_weight_big:
                if self.menu_weight_value == '1':
                    self.menu_weight_value = '2'
                    self.weight_big_l.setStyleSheet(MenuStyle.weight_changed_style_1)
                    self.weight_big_money_l.setStyleSheet(MenuStyle.weight_changed_style_2)
                    self.weight_mid_l.setStyleSheet(MenuStyle.weight_no_changed_style_1)
                    self.weight_mid_money_l.setStyleSheet(MenuStyle.weight_no_changed_style_2)
                    self.menu_recalculate()
            elif obj == self.menu_config_weight_mid:
                if self.menu_weight_value == '2':
                    self.menu_weight_value = '1'
                    self.weight_big_l.setStyleSheet(MenuStyle.weight_no_changed_style_1)
                    self.weight_big_money_l.setStyleSheet(MenuStyle.weight_no_changed_style_2)
                    self.weight_mid_l.setStyleSheet(MenuStyle.weight_changed_style_1)
                    self.weight_mid_money_l.setStyleSheet(MenuStyle.weight_changed_style_2)
                    self.menu_recalculate()
            elif obj == self.menu_sugar_normal:
                if self.menu_sugar_value in ('2', '3'):
                    self.menu_sugar_value = '1'
                    self.menu_sugar_style_changed(True, False, False)
            elif obj == self.menu_sugar_5:
                if self.menu_sugar_value in ('1', '3'):
                    self.menu_sugar_value = '2'
                    self.menu_sugar_style_changed(False, True, False)
            elif obj == self.menu_sugar_3:
                if self.menu_sugar_value in ('1', '2'):
                    self.menu_sugar_value = '3'
                    self.menu_sugar_style_changed(False, False, True)
            elif obj == self.menu_ice_low:
                if self.menu_ice_value in ('2', '3'):
                    self.menu_ice_value = '1'
                    self.menu_ice_style_changed(True, False, False)
            elif obj == self.menu_ice_normal:
                if self.menu_ice_value in ('1', '3'):
                    self.menu_ice_value = '2'
                    self.menu_ice_style_changed(False, True, False)
            elif obj == self.menu_ice_0:
                if self.menu_ice_value in ('1', '2'):
                    self.menu_ice_value = '3'
                    self.menu_ice_style_changed(False, False, True)
            elif obj == self.menu_small_material_cbb_l:
                self.is_cbb = not self.is_cbb
                self.menu_small_material_cbb_l.setStyleSheet(
                    MenuStyle.sugar_changed_style if self.is_cbb else MenuStyle.sugar_no_changed_style
                )
                self.menu_recalculate()
            elif obj == self.menu_small_material_yg_l:
                self.is_yg = not self.is_yg
                self.menu_small_material_yg_l.setStyleSheet(
                    MenuStyle.sugar_changed_style if self.is_yg else MenuStyle.sugar_no_changed_style
                )
                self.menu_recalculate()
            elif obj == self.menu_small_material_zz_l:
                self.is_zz = not self.is_zz
                self.menu_small_material_zz_l.setStyleSheet(
                    MenuStyle.sugar_changed_style if self.is_zz else MenuStyle.sugar_no_changed_style
                )
                self.menu_recalculate()
            elif obj == self.menu_small_material_yy_l:
                self.is_yy = not self.is_yy
                self.menu_small_material_yy_l.setStyleSheet(
                    MenuStyle.sugar_changed_style if self.is_yy else MenuStyle.sugar_no_changed_style
                )
                self.menu_recalculate()
            elif obj == self.menu_small_material_mgd_l:
                self.is_mgd = not self.is_mgd
                self.menu_small_material_mgd_l.setStyleSheet(
                    MenuStyle.sugar_changed_style if self.is_mgd else MenuStyle.sugar_no_changed_style
                )
                self.menu_recalculate()
            elif obj == self.sw_scan_code_notice_widget:
                if self.is_login:
                    if self.notice_ui is not None:
                        self.notice_ui.close()
                        self.notice_ui = None
                        self.is_create_notice = True
                    else:
                        self.notice_ui = OutTeeNoticeMata(self.all_message_bean_list[:20])
                        self.notice_ui.move(
                            self.sw_scan_code_notice_widget.mapToGlobal(self.sw_scan_code_notice_widget.pos()).x() - 20,
                            self.sw_scan_code_notice_widget.mapToGlobal(self.sw_scan_code_notice_widget.pos()).y() - 973,
                        )
                        self.notice_ui.show()
                        self.is_create_notice = False
            elif obj == self.widget_2:
                if self.notice_ui is not None:
                    if self.is_create_notice:
                        self.is_create_notice = False
                        self.notice_ui.close()
                        self.notice_ui = None
                    self.is_create_notice = True
                if getattr(self, "manager_keyboard_ui", None) is not None:
                    if getattr(self, "is_create_keyboard", True):
                        self.is_create_keyboard = False
                        self.manager_keyboard_ui.close()
                        self.manager_keyboard_ui = None
                    self.is_create_keyboard = True
                self.l_title_store_name_2.clearFocus()
            elif obj == self.wbtn_clean_day:
                if not self.is_start:
                    self.clean_btn_state_change(True, False, False)
                    self.stackedWidget_clean.setCurrentWidget(self.clean)
                    self.stackedWidget_3.setCurrentWidget(self.day_log)
            elif obj == self.wbtn_clean_week:
                if not self.is_start:
                    self.clean_btn_state_change(False, True, False)
                    self.stackedWidget_clean.setCurrentWidget(self.clean)
                    self.stackedWidget_3.setCurrentWidget(self.week_log)
            elif obj == self.wbtn_setting_loacl_record:
                self.stackedWidget_setting.setCurrentWidget(self.setting_local_record)
                self.btn_setting_order.setChecked(True)
                self.btn_setting_message.setChecked(False)
                self.stackedWidget_setting_location.setCurrentWidget(self.location_order)
            elif obj == self.wbtn_setting_debug:
                if not self.is_login:
                    if self.is_debug:
                        self.debug_state(False)
                    else:
                        self.login_ui = LoginMata()
                        self.login_ui.debug_result.connect(self.debug_callBack)
                        self.login_ui.show()
            elif obj == self.wbtn_setting_second_screen:
                self.stackedWidget_setting.setCurrentWidget(self.setting_conduit_content)
            elif obj == self.wbtn_setting_second_screen_2:
                self.init_language_settings_page()
                self.stackedWidget_setting.setCurrentWidget(self.language_settings_widget)
            elif obj == self.on_off_setting_widget:
                if self.is_login or self.is_debug:
                    self.open_second_screen_change(self.is_open_screen)
            elif obj == self.wbtn_setting_update:
                self._show_update_choice_dialog()
            elif obj == self.camera_widget:
                if self.is_login:
                    if self.is_show:
                        self.serial_thread.camera_info.connect(self.callBack_camera_info_result)
                        self.is_show = False
                        self.notice_camera_scan_show.emit(self.is_show)
                        print("扫码开启")
                    else:
                        self.serial_thread.camera_info.disconnect(self.callBack_camera_info_result)
                        self.camera_frame_image.clear()
                        self.inner_label.clear()
                        self.is_show = True
                        self.notice_camera_scan_show.emit(self.is_show)
                        print("扫码关闭")
            elif obj == self.menu_add_cart_btn:
                self.wbtn_menu_add_cart_btn_clicked()
                self.change_menu_add_cart_btn_state()
            elif obj == self.l_title_store_name_2:
                self.l_title_store_name_2.setReadOnly(False)
                self.keyboard_thread = KeyboardThread()
                self.keyboard_thread.start()
                self.l_title_store_name_2.setFocus()

        return super().eventFilter(obj, event)

    def change_menu_add_cart_btn_state(self):
        num = len(self.menu_add_shopping_cart_beans)
        if num == 0:
            # 展示icon
            self.menu_add_cart_btn_add.setHidden(True)
            self.menu_add_cart_btn_icon.setStyleSheet('border-image: url(:/icon/ic_menu_add_cart_btn.png);')
            self.menu_add_cart_btn_icon.setText('')
        else:
            # 展示加的数量
            self.menu_add_cart_btn_add.setHidden(False)
            self.menu_add_cart_btn_icon.setStyleSheet('border: 1px solid red; border-radius: 20px; color:red;')
            self.menu_add_cart_btn_icon.setText(str(num))

    def camera_image(self, image):
        resize_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        self.camera_frame_image.setPixmap(QtGui.QPixmap.fromImage(
            QtGui.QImage(resize_image.data, resize_image.shape[1], resize_image.shape[0],
                         QtGui.QImage.Format_RGB888)))

    def display_image(self, frame):
        """
        在 QLabel 中显示图像，保持比例并居中。
        """
        height, width, channel = frame.shape   #返回一个元组，包含图像的高度、宽度和通道数。
        bytes_per_line = channel * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

        # 转换为 QPixmap
        pixmap = QPixmap.fromImage(q_image)

        # 缩放 QPixmap 保持比例
        scaled_pixmap = pixmap.scaled(
            self.camera_frame_image.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # 显示到 QLabel
        self.camera_frame_image.setPixmap(scaled_pixmap)

    def camera_label_clear(self):   
        self.camera_frame_image.clear()
        self.notice_camera_scan_show.emit(True)

    # def get_recipe_from_menu(product_name):
    #     menu_path = os.path.join(os.getcwd(), "tea_drinks_menu.json")
    #     if not os.path.exists(menu_path):
    #         return ""

    #     try:
    #         with open(menu_path, "r", encoding="utf-8") as f:
    #             menu = json.load(f)
    #         for item in menu:
    #             if item.get("Name") == product_name:
    #                 return item.get("Recipe", "")
    #     except Exception as e:
    #         print("❌ 读取 tea_drinks_menu.json 失败:", e)

    #     return ""

    def callBack_camera_info_result(self, camera_data_str):      #将扫码得到的内容解析
        try:
            self.camera_data = json.loads(camera_data_str)  # 将字符串转换为列表
        except json.JSONDecodeError as e:
            print("JSON 解析错误:", e)
            self.camera_data = [] 
        print(f"[ScanAuto] 收到扫码数据: {self.camera_data}")

        # 设置布局管理器
        layout = QVBoxLayout(self.camera_frame_image)
        layout.setAlignment(Qt.AlignCenter)  # 将布局内容居中对齐
        
        self.inner_label.setWordWrap(True)  # 允许自动换行
        self.inner_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐，垂直居中对齐
        font = self.inner_label.font()
        font.setPointSize(20)  # 设置字体大小
        self.inner_label.setFont(font)
        # 将新增的 QLabel 添加到布局中
        layout.addWidget(self.inner_label)

        # self.camera_frame_image.setWordWrap(True)  # 允许自动换行
        # # self.camera_frame_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许扩展
        # self.camera_frame_image.setAlignment(Qt.AlignCenter  | Qt.AlignVCenter) # 设置文本居中对齐
        # font = self.camera_frame_image.font()# 设置字体（可选）
        # font.setPointSize(20)  # 设置字体大小
        # self.camera_frame_image.setFont(font)
         # 格式化显示内容
        formatted_text = (
            f"名称：{self.camera_data.get('product_name', '未知')}\n"
            f"糖量：{self.camera_data.get('product_sugar', '未知')}\n"
            f"容量：{self.camera_data.get('product_quantity', '未知')}\n"
            f"冰量：{self.camera_data.get('product_ice', '未知')}\n"
            f"配料：{self.camera_data.get('product_simp', '无')}\n"
            f"单价：{self.camera_data.get('unit_price', '未知')} 元"
            # f"配方：{self.camera_data.get('recipe', '未知')}"
        )
        # 设置文本内容
        # self.camera_frame_image.setText(formatted_text)
        # 设置新增 QLabel 的文本内容
        self.inner_label.setText(formatted_text)

        # 数据库查询 self.today_id 取茶号 今日订单数量
        self.today_id = db_util.query_today_order_count() + 1
        # 数据库查询 self.today_product_id 今日奶茶数量
        self.today_product_id = db_util.query_today_tea_quantity() + 1
        # 创建订单
        order_bean = OrderBean()
        date = datetime.now()
        order_num = date.strftime('%Y%m%d%H%M%S')
        order_id = f'O{order_num}'
        order_bean.order_id = order_id
        order_bean.order_time = date.strftime('%Y-%m-%d %H:%M:%S')
        # order_bean.today_id = str(self.today_id)
        self._ensure_daily_serials()            # 跨天保护
        order_bean.today_id = str(self.next_take_no)   # 固定本单取茶号（today_id）

        # for item_tee in self.camera_data:
        #     tee_bean = NewTeeBean()
        #     tee_bean.order_id = order_id
        #     tee_bean.product_id = f'P{str(self.today_product_id).zfill(4)}'  # 生成四位数的 product_id
        #     tee_bean.product_name = item_tee.get("product_name", "")
        #     tee_bean.product_sugar = item_tee.get("product_sugar", "")
        #     tee_bean.product_quantity = item_tee.get("product_quantity", "")
        #     tee_bean.product_ice = item_tee.get("product_ice", "")
        #     tee_bean.product_simp = item_tee.get("product_simp", "")
        #     tee_bean.unit_price = item_tee.get("unit_price", "0.0")
        #     tee_bean.recipe = item_tee.get("recipe", "")
        # 直接访问字典的键值对
        tee_bean = NewTeeBean()
        tee_bean.order_id = order_id
        tee_bean.today_id = order_bean.today_id

        tee_bean.product_id = f'P{str(self.today_product_id).zfill(4)}'  # 生成四位数的 product_id
        print(
            f"[OrderDebug] 新建奶茶: order_id={order_id}, "
            f"today_id={order_bean.today_id}, product_id={tee_bean.product_id}, "
            f"name={tee_bean.product_name}"
        )
        tee_bean.product_name = self.camera_data.get("product_name", "")
        tee_bean.product_sugar = self.camera_data.get("product_sugar", "")
        tee_bean.product_quantity = self.camera_data.get("product_quantity", "")
        tee_bean.product_ice = self.camera_data.get("product_ice", "")
        tee_bean.product_simp = self.camera_data.get("product_simp", "")
        tee_bean.unit_price = self.camera_data.get("unit_price", "")
        qr_recipe = self.camera_data.get("recipe", "").strip()
        tee_bean.recipe = qr_recipe if qr_recipe else get_recipe_by_name(tee_bean.product_name)
    

        tee_bean.num_tee = "1"  # 默认数量为 1，如果 JSON 里有可以用 item_tee.get("num_tee", "1")
        if self.auto_isChecked:
            tee_bean.state = '1'
        else:
            tee_bean.state = '3'
        order_bean.tee_list.append(tee_bean)
        self.today_product_id += 1
            # tee_bean.toString()
        # order_bean.toString()

        # 把订单数据保存到数据库
        if self.auto_isChecked:
            #等于true是on（扫码自动出茶）
            print(f"[ScanAuto] ON=自动出茶触发, order_id={order_id}, product_name={tee_bean.product_name}")
            # print(f"recipe:{tee_bean.get_recipe()}")
            self.save_order_db_thread = OrderSaveToDB(order_bean)
            self.save_order_db_thread.done.connect(self.on_order_saved)
            # self.save_order_db_thread.done.connect(self.refresh_order_content) 
            self.save_order_db_thread.start()
            # 统一走 send_serial_data：解析/缩放/缺料拦截逻辑一致
            ok = self.send_serial_data(tee_bean)
            print(f"[ScanAuto] send_serial_data -> {ok}")
            if ok:
                # 通知后端开始制作
                self.notice_make_tee_begin()
            # self.make_tee_camera_data.emit(tee_bean.get_recipe())  #串口发送命令
        else:
            #等于false是off
            print(f"[ScanAuto] OFF=不自动出茶, order_id={order_id}, product_name={tee_bean.product_name}")
            self.save_order_db_thread = OrderSaveToDB(order_bean)
            self.save_order_db_thread.done.connect(self.on_order_saved)
            self.save_order_db_thread.start()
            #刷新界面
            # self.refresh_order_content()
       
        # 刷新记录界面
        self.refresh_setting_local_tee()


    def debug_callBack(self, is_debug):
        self.is_debug = is_debug
        if self.is_debug:
            self.wbtn_setting_debug.setStyleSheet(MenuStyle.debug_true_style)
        else:
            self.wbtn_setting_debug.setStyleSheet(MenuStyle.debug_false_style)
            self.message_info_ui = MessageDialog()
            self.message_info_ui.show()
        self.switch_debug_init(self.is_debug)

    def debug_state(self, is_debug):
        self.is_debug = is_debug
        if self.is_debug:
            self.wbtn_setting_debug.setStyleSheet(MenuStyle.debug_true_style)
        else:
            self.wbtn_setting_debug.setStyleSheet(MenuStyle.debug_false_style)
        self.switch_debug_init(self.is_debug)

    # 清洗按钮状态更改
    def clean_btn_state_change(self, is_day, is_week, is_record):
        if is_day:
            #选中状态
            self.wbtn_clean_day.setStyleSheet(MenuStyle.clean_day_selected_style)
            self.icon_wbtn_clean_day.setStyleSheet(MenuStyle.clean_day_icon_selected_style)
            self.name_wbtn_clean_day.setStyleSheet(MenuStyle.clean_font_color_selected_style)
            self.switch_clean_day_week_load(True)
        else:
            # 未选中状态
            self.wbtn_clean_day.setStyleSheet(MenuStyle.clean_day_style)
            self.icon_wbtn_clean_day.setStyleSheet(MenuStyle.clean_day_icon_style)
            self.name_wbtn_clean_day.setStyleSheet(MenuStyle.clean_font_color_style)

        if is_week:
            #选中状态
            self.wbtn_clean_week.setStyleSheet(MenuStyle.clean_week_selected_style)
            self.icon_wbtn_clean_week.setStyleSheet(MenuStyle.clean_day_icon_selected_style)
            self.name_wbtn_clean_week.setStyleSheet(MenuStyle.clean_font_color_selected_style)
            self.switch_clean_day_week_load(False)
        else:
            # 未选中状态
            self.wbtn_clean_week.setStyleSheet(MenuStyle.clean_week_style)
            self.icon_wbtn_clean_week.setStyleSheet(MenuStyle.clean_day_icon_style)
            self.name_wbtn_clean_week.setStyleSheet(MenuStyle.clean_font_color_style)


    def edit_text_to_line(self, msg):
        self.line_context += msg
        target = getattr(self, "_target_line_edit", None) or self.lineEdit
        target.setText(self.line_context)

    # 原来：
    # def clear_line(self):
    #     self.line_context = ''
    #     self.lineEdit.setText(self.line_context)

    # 现在：
    def clear_line(self):
        self.line_context = ''
        target = getattr(self, "_target_line_edit", None) or self.lineEdit
        target.setText(self.line_context)

    # 扫码出茶和手动出茶按钮切换
    def scan_code_or_mt_state_change(self, scan_code, mt):
        if scan_code:
            self.wbtn_scan_code_outtee_isChecked = True
            self.wbtn_scan_code_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.wbtn_scan_code_outtee_selected)
            self.icon_scan_code_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_outtee_scan_code_selected)
            self.name_scan_code_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.scan_code_or_mt_name_color_select)
        else:
            self.wbtn_scan_code_outtee_isChecked = False
            self.wbtn_scan_code_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.wbtn_scan_code_outtee)
            self.icon_scan_code_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_outtee_scan_code)
            self.name_scan_code_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.scan_code_or_mt_name_color)
        if mt:
            self.wbtn_mt_outtee_isChecked = True
            self.wbtn_mt_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.wbtn_mt_outtee_selected)
            self.icon_wbtn_mt_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_outtee_mt_selected)
            self.name_wbtn_mt_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.scan_code_or_mt_name_color_select)
        else:
            self.wbtn_mt_outtee_isChecked = False
            self.wbtn_mt_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.wbtn_mt_outtee)
            self.icon_wbtn_mt_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_outtee_mt)
            self.name_wbtn_mt_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.scan_code_or_mt_name_color)

    # 是否自动出茶按钮
    def auto_tee_state_change(self, is_checked):
        if not is_checked:
            print("on")
            self.auto_isChecked = True
            self.off_widget.setVisible(False)
            self.on_widget.setVisible(True)
        else:
            print("off")
            self.auto_isChecked = False
            self.on_widget.setVisible(False)
            self.off_widget.setVisible(True)

    # 主菜单按钮设置
    def menu_btn_state_change(self, out_tee, manager,maketee, clean, setting):
        self.l_title_store_name_2.clearFocus()
        if out_tee:
            self.wbtn_menu_outtee_isChecked = True
            self.wbtn_menu_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.menu_outtee_widget_selected)
            self.icon_wbtn_menu_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_outtee_selected)
            self.name_wbtn_menu_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu_selected)
        else:
            self.wbtn_menu_outtee_isChecked = False
            self.wbtn_menu_outtee.setStyleSheet("")
            self.icon_wbtn_menu_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_outtee)
            self.name_wbtn_menu_outtee.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu)
        if manager:
            self.wbtn_menu_manager_isChecked = True
            self.wbtn_menu_manager.setStyleSheet(MenuBtnStyle.MenuStyle.menu_manager_widget_selected)
            self.icon_wbtn_menu_manager.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_manager_selected)
            self.name_wbtn_menu_manager.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu_selected)
        else:
            self.wbtn_menu_manager_isChecked = False
            self.wbtn_menu_manager.setStyleSheet("")
            self.icon_wbtn_menu_manager.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_manager)
            self.name_wbtn_menu_manager.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu)
        if maketee:
            self.wbtn_menu_maketee_isChecked = True
            self.wbtn_menu_maketee.setStyleSheet(MenuBtnStyle.MenuStyle.menu_maketee_widget_selected)
            self.icon_wbtn_menu_maketee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_maketee_selected)
            self.name_wbtn_menu_maketee.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu_selected)
        else:
            self.wbtn_menu_maketee_isChecked = False
            self.wbtn_menu_maketee.setStyleSheet("")
            self.icon_wbtn_menu_maketee.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_maketee)
            self.name_wbtn_menu_maketee.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu)
        if clean:
            self.wbtn_menu_clean_isChecked = True
            self.wbtn_menu_clean.setStyleSheet(MenuBtnStyle.MenuStyle.menu_clean_widget_selected)
            self.icon_wbtn_menu_clean.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_clean_selected)
            self.name_wbtn_menu_clean.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu_selected)
        else:
            self.wbtn_menu_clean_isChecked = False
            self.wbtn_menu_clean.setStyleSheet("")
            self.icon_wbtn_menu_clean.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_clean)
            self.name_wbtn_menu_clean.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu)
        if setting:
            self.wbtn_menu_setting_isChecked = True
            self.wbtn_menu_setting.setStyleSheet(MenuBtnStyle.MenuStyle.menu_setting_widget_selected)
            self.icon_wbtn_menu_setting.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_setting_selected)
            self.name_wbtn_menu_setting.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu_selected)
        else:
            self.wbtn_menu_setting_isChecked = False
            self.wbtn_menu_setting.setStyleSheet("")
            self.icon_wbtn_menu_setting.setStyleSheet(MenuBtnStyle.MenuStyle.icon_wbtn_menu_setting)
            self.name_wbtn_menu_setting.setStyleSheet(MenuBtnStyle.MenuStyle.name_menu)

    # TODO 自定义按钮设置 <---
    
    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font
    
    # TODO ---> 字体设置
    def init_font(self):
        AlibabaPuHuiTi_3_55_Regular_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf')
        )
        if AlibabaPuHuiTi_3_55_Regular_id != -1:
            AlibabaPuHuiTi_3_55_Regular_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_55_Regular_id)[0]

            AlibabaPuHuiTi_3_55_Regular_font_family_18 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 18)
            self.label_12.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_13.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_17.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_20.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)

            self.label_43.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            # self.label_44.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_45.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            # self.label_46.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_47.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            # self.label_48.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_50.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_51.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_52.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_53.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_55.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_56.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_59.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_60.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)

            self.label_72.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            # self.label_73.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_74.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            # self.label_75.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_76.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            # self.label_77.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_57.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_61.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_62.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_63.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_64.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_65.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_69.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)
            self.label_70.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)

            self.device_name.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_18)

            AlibabaPuHuiTi_3_55_Regular_font_family_20 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 20)
            self.l_title_store_name.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.l_title_store_name_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.weight_big_l.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.weight_mid_l.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_sugar_normal.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_sugar_5.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_sugar_3.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_small_material_cbb_l.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_small_material_yg_l.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_small_material_zz_l.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_small_material_yy_l.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_small_material_mgd_l.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_ice_low.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_ice_normal.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)
            self.menu_ice_0.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_20)

            AlibabaPuHuiTi_3_55_Regular_font_family_23 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 23, QFont.Bold)
            self.name_scan_code_outtee.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.name_wbtn_mt_outtee.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_manager_all.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_manager_one.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_manager_out.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_manager_out_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.lineEdit.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.name_wbtn_clean_day.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.name_wbtn_clean_week.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_clean_record.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_setting_order.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_setting_message.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_setting_out_tee.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_back_setting.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)

            AlibabaPuHuiTi_3_55_Regular_font_family_23 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 23, QFont.Bold)
            self.btn_maketee_all.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_maketee_one.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_maketee_out.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.btn_maketee_out_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)
            self.lineEdit_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_23)

            AlibabaPuHuiTi_3_55_Regular_font_family_25 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 25)
            self.outtee_title_material_1.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_2.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_3.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_4.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_5.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_6.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_7.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.outtee_title_material_8.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)
            self.label_34.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)



            self.label_42.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_25)

            AlibabaPuHuiTi_3_55_Regular_font_family_28 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 28)
            self.label_22.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_24.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_27.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_29.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_79.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_81.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)

            self.label_15.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_49.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_54.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_58.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)

            self.label_67.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_71.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_68.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)
            self.label_66.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_28)


            AlibabaPuHuiTi_3_55_Regular_font_family_32 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 32)


            self.label_14.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_32)
            self.label_16.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_32)


            AlibabaPuHuiTi_3_55_Regular_font_family_40 = QFont(AlibabaPuHuiTi_3_55_Regular_font_family, 40)
            self.label_30.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)
            self.label_31.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)
            self.label_32.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)
            self.label_33.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)
            self.btn_setting_order_tee_switch.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)

            self.label_36.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)
            self.label_38.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)
            self.label_39.setFont(AlibabaPuHuiTi_3_55_Regular_font_family_40)


        AlibabaPuHuiTi_3_65_Medium_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf')
        )
        if AlibabaPuHuiTi_3_65_Medium_id != -1:
            AlibabaPuHuiTi_3_65_Medium_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_65_Medium_id)[0]
            AlibabaPuHuiTi_3_65_Medium_font_family_12 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 12)
            self.l_title_date.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_12)
            self.l_title_week.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_12)
            self.weight_big_money_l.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_12)
            self.weight_mid_money_l.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_12)

            AlibabaPuHuiTi_3_65_Medium_font_family_18 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 18)
            self.order_number_page.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_18)
            self.message_number_page.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_18)

            AlibabaPuHuiTi_3_65_Medium_font_family_20 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 20)
            self.btn_message_last_page.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_20)
            self.btn_message_next_page.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_20)
            self.btn_order_last_page.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_20)
            self.btn_order_next_page.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_20)


            AlibabaPuHuiTi_3_65_Medium_font_family_32 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 32)

            self.label_19.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_32)
            self.clean_complete_date.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_32)

            AlibabaPuHuiTi_3_65_Medium_font_family_36 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 36)
            self.name_off.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_36)
            self.name_off_2.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_36)


            AlibabaPuHuiTi_3_65_Medium_font_family_40 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 40)
            self.label_21.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_40)
            self.label_23.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_40)
            self.label_26.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_40)
            self.label_28.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_40)
            self.label_78.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_40)
            self.label_80.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_40)
            

        AlibabaPuHuiTi_3_75_SemiBold_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')
        )
        if AlibabaPuHuiTi_3_75_SemiBold_id != -1:
            AlibabaPuHuiTi_3_75_SemiBold_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_75_SemiBold_id)[0]
            AlibabaPuHuiTi_3_75_SemiBold_family_40 = QFont(AlibabaPuHuiTi_3_75_SemiBold_family, 40, QFont.Bold)




        AlibabaPuHuiTi_3_85_Bold_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')
        )
        if AlibabaPuHuiTi_3_85_Bold_id != -1:
            AlibabaPuHuiTi_3_85_Bold_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_85_Bold_id)[0]
            AlibabaPuHuiTi_3_85_Bold_font_family_12 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 12, QFont.Bold)
            self.menu_money_unit_l.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_12)

            AlibabaPuHuiTi_3_85_Bold_font_family_14 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 14, QFont.Bold)
            self.l_title_name.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_14)

            AlibabaPuHuiTi_3_85_Bold_font_family_24 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 24, QFont.Bold)
            self.msg_sw_scan_code_notice.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_24)

            AlibabaPuHuiTi_3_85_Bold_custom_font_26 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 26, QFont.Bold)
            self.menu_config_number_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_26)
            self.menu_add_cart_btn_icon.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_26)
            self.menu_add_cart_btn_add.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_26)

            AlibabaPuHuiTi_3_85_Bold_font_family_30 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 30, QFont.Bold)
            self.l_title_time.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_30)

            AlibabaPuHuiTi_3_85_Bold_font_family_32 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 32, QFont.Bold)
            self.menu_add_cart_btn_name.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_32)


            AlibabaPuHuiTi_3_85_Bold_font_family_36 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 36, QFont.Bold)
            self.name_on.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_36)
            self.name_on_2.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_36)

            AlibabaPuHuiTi_3_85_Bold_font_family_60 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 60, QFont.Bold)
            self.btn_begin_make.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_60)
            self.btn_cancel_make.setFont(AlibabaPuHuiTi_3_85_Bold_font_family_60)

        AlibabaPuHuiTi_3_105_Heavy_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-105-Heavy/AlibabaPuHuiTi-3-105-Heavy.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-105-Heavy/AlibabaPuHuiTi-3-105-Heavy.ttf')
        )
        if AlibabaPuHuiTi_3_105_Heavy_id != -1:
            AlibabaPuHuiTi_3_105_Heavy_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_105_Heavy_id)[0]

            AlibabaPuHuiTi_3_105_Heavy_custom_font_20 = QFont(AlibabaPuHuiTi_3_105_Heavy_font_family, 20, QFont.Bold)
            self.tee_name_l.setFont(AlibabaPuHuiTi_3_105_Heavy_custom_font_20)

            AlibabaPuHuiTi_3_105_Heavy_font_family_27 = QFont(AlibabaPuHuiTi_3_105_Heavy_font_family, 27, QFont.Bold)
            self.name_wbtn_menu_outtee.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_27)
            self.name_wbtn_menu_manager.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_27)
            self.name_wbtn_menu_maketee.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_27)
            self.name_wbtn_menu_clean.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_27)
            self.name_wbtn_menu_setting.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_27)

            AlibabaPuHuiTi_3_105_Heavy_font_family_40 = QFont(AlibabaPuHuiTi_3_105_Heavy_font_family, 40, QFont.Bold)
            self.clean_pause.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_40)
            self.clean_begin.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_40)
            self.clean_stop.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_40)

            AlibabaPuHuiTi_3_105_Heavy_font_family_60 = QFont(AlibabaPuHuiTi_3_105_Heavy_font_family, 60, QFont.Bold)
            self.btn_setting_exit.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_60)
            self.btn_setting_login.setFont(AlibabaPuHuiTi_3_105_Heavy_font_family_60)


        PINGFANG_HEAVY_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/PingFang/PINGFANG_HEAVY.TTF'
            self.get_font_path('fonts/PingFang/PINGFANG_HEAVY.TTF')
        )
        if PINGFANG_HEAVY_font_id != -1:
            PINGFANG_HEAVY_font_family = QFontDatabase.applicationFontFamilies(
                PINGFANG_HEAVY_font_id)[0]
            PINGFANG_HEAVY_custom_font_26 = QFont(PINGFANG_HEAVY_font_family, 26)
            self.menu_config_name_l.setFont(PINGFANG_HEAVY_custom_font_26)

        PINGFANG_BOLD_0_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/PingFang/PINGFANG_BOLD_0.TTF'
            self.get_font_path('fonts/PingFang/PINGFANG_BOLD_0.TTF')
        )
        if PINGFANG_BOLD_0_font_id != -1:
            PINGFANG_BOLD_0_font_family = QFontDatabase.applicationFontFamilies(
                PINGFANG_BOLD_0_font_id)[0]
            PINGFANG_BOLD_0_custom_font_20 = QFont(PINGFANG_BOLD_0_font_family, 20)
            self.label_25.setFont(PINGFANG_BOLD_0_custom_font_20)

        DIN_Alternate_Bold_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/DIN Alternate Bold.TTF'
            self.get_font_path('fonts/DIN Alternate Bold.TTF')
        )
        if DIN_Alternate_Bold_font_id != -1:
            DIN_Alternate_Bold_font_family = QFontDatabase.applicationFontFamilies(
                DIN_Alternate_Bold_font_id)[0]
            DIN_Alternate_Bold_font_family_30 = QFont(DIN_Alternate_Bold_font_family, 30, QFont.Bold)
            self.menu_money_l.setFont(DIN_Alternate_Bold_font_family_30)

    # TODO 字体设置 <---
    @pyqtSlot()
    def on_btn_title_close_clicked(self):
        if self.notice_ui is not None:
            self.notice_ui.close()
        if self.manager_keyboard_ui is not None:
            self.manager_keyboard_ui.close()
        if self.second_screen_ui is not None:
            self.second_screen_ui.close()
            self.second_screen_ui = None
        self.close()
    def _load_zip4_map(self, csv_path: str):
        """把 cn_zip4_map_big.csv 读成 dict: {'5190':('广东省','珠海市'), ...}"""
        m = {}
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                rd = csv.DictReader(f)
                for row in rd:
                    z = str(row.get("zip4","")).strip()
                    prov = str(row.get("province","")).strip()
                    city = str(row.get("city","")).strip()
                    if len(z) == 4 and z.isdigit():
                        m[z] = (prov, city)
        except Exception as e:
            print(f"[zip4] load fail: {e}")
        print(f"[zip4] loaded prefixes: {len(m)}")
        return m

    def _lookup_zip4(self, code: str):
        """支持传 '5190' 或 '519012' 这类，返回 '广东省 珠海市' 或 None"""
        if not code:
            return None
        s = "".join(str(code).strip().split())
        if len(s) < 4 or not s[:4].isdigit():
            return None
        p4 = s[:4]
        pc = self._zip4_map.get(p4)
        if not pc:
            return None
        prov, city = pc
        if city and not city.endswith("市") and not city.endswith("区") and not city.endswith("州"):
            city = city + "市"
        return f"{prov} {city}".strip()
    # ==== 工具：判断/定位 ====
    def _widget_is_alive(self, w):
        try:
            return (w is not None) and (w is not None)  # 仅作存在性检查
        except Exception:
            return False

    def _scroll_area_of(self, w):
        # 向上找到承载它的 QScrollArea（如果有）
        try:
            from PyQt5.QtWidgets import QScrollArea
            p = w
            while p is not None and not isinstance(p, QScrollArea):
                p = p.parent()
            return p if p is not None and isinstance(p, QScrollArea) else None
        except Exception:
            return None

    def _find_menu_scroll_area(self):
        """
        精准定位“手动出茶”的菜单滚动区（就算当前不在该页也能定位）：
        1) 先从 menu_content_widget 反查所属 QScrollArea；
        2) 找不到再在 sw_mt_widget 里搜 QScrollArea，优先名字含 'menu'；
        3) 实在找不到返回 None。
        """
        from PyQt5.QtWidgets import QScrollArea
        try:
            # 1) 已渲染过菜单时，直接反查
            w = getattr(self, "menu_content_widget", None)
            if w:
                p = w
                while p is not None and not isinstance(p, QScrollArea):
                    p = p.parent()
                if isinstance(p, QScrollArea):
                    return p

            # 2) 只在“手动出茶页”的根容器里搜索，不影响其它页面
            mt = getattr(self, "sw_mt_widget", None)
            if mt is None:
                return None
            cands = mt.findChildren(QScrollArea) or []
            # 优先挑 objectName 含 “menu” 的
            for sa in cands:
                try:
                    if "menu" in sa.objectName().lower():
                        return sa
                except Exception:
                    pass
            # 退路：取第一个
            return cands[0] if cands else None
        except Exception as e:
            print("[Menu] _find_menu_scroll_area error:", e)
            return None

    # ==== 只清子项，不销毁布局本体（防止 GridLayout 被删）====
    def _clear_layout_only_children(self, layout):
        """清空布局内容：既清子控件，也把子布局完整移除；保留 layout 本体。"""
        from PyQt5 import sip
        try:
            for i in reversed(range(layout.count())):
                item = layout.takeAt(i)
                w = item.widget()
                sub = item.layout()
                if w is not None:
                    w.setParent(None); w.deleteLater()
                elif sub is not None:
                    # 递归清空并删除子布局
                    while sub.count():
                        j = sub.takeAt(0)
                        if j.widget():
                            j.widget().setParent(None); j.widget().deleteLater()
                        if j.layout():
                            sub2 = j.layout()
                            while sub2.count():
                                k = sub2.takeAt(0)
                                if k.widget(): k.widget().setParent(None); k.widget().deleteLater()
                            sip.delete(sub2)
                    sip.delete(sub)
        except Exception as e:
            print("[Menu] _clear_layout_only_children error:", e)



    # ==== 安全刷新“手动出茶-菜单” ====
    def _refresh_manual_menu(self, changed_names=None):
        """
        后台刷新“手动出茶-菜单”：
        - 只在 sw_mt_widget 内部操作；
        - 保证 menu_gridLayout 是 QGridLayout；
        - 清子项，不删布局对象；
        - 刷新前重置用于渲染的数据列表，避免重复渲染。
        """
        try:
            grid = self._ensure_menu_grid()
            if grid is None:
                print("[Menu] 跳过刷新：未找到有效菜单网格")
                return

            # 保存滚动（如果有）
            sa = None; old_v = 0
            try:
                from PyQt5.QtWidgets import QScrollArea
                p = self.menu_content_widget
                while p is not None and not isinstance(p, QScrollArea):
                    p = p.parent()
                if isinstance(p, QScrollArea):
                    sa = p; old_v = sa.verticalScrollBar().value()
            except Exception:
                pass

            # 只清子项
            self._clear_layout_only_children(grid)

            # 关键：重置渲染相关的容器，避免 load_menu_xlsx 在原有列表上 append
            if hasattr(self, "menu_tee_beans"): self.menu_tee_beans = []
            if hasattr(self, "menu_num"): self.menu_num = 0
            # 如果你有映射缓存，也一并清理（避免旧卡片的引用残留）
            if hasattr(self, "menu_cards_by_name"): self.menu_cards_by_name.clear()
            if hasattr(self, "menu_beans_by_name"): self.menu_beans_by_name.clear()

            # 重新加卡片（确保它只往 self.menu_gridLayout 填，不做 setLayout）
            if hasattr(self, "load_menu_xlsx"):
                self.load_menu_xlsx()

            # 恢复滚动
            try:
                if sa: sa.verticalScrollBar().setValue(old_v)
            except Exception:
                pass

            print("[Menu] 已安全刷新（消除重复+禁止横向拖动）",
                f"变更{len(changed_names)}项：{', '.join(changed_names)}" if changed_names else "")
        except Exception as e:
            print("[Menu][ERROR] 刷新手动出茶菜单失败：", e)
        # 在 _refresh_manual_menu() 的尾部合适位置追加
        self._refresh_conduit_unused_marks()



    def _ensure_order_grid(self):
        from PyQt5.QtWidgets import QWidget, QGridLayout, QScrollArea
        try:
            grid = getattr(self, "order_gridLayout", None)
            # 如果已存在且可用，直接返回
            if grid is not None:
                try:
                    _ = grid.count()
                    return grid
                except Exception:
                    pass  # 旧指针无效，继续重建

            # 优先把 grid 放回到你原来的容器 self.order_content_Layout
            if getattr(self, "order_content_Layout", None):
                container = QWidget()
                self.order_content_Layout.addWidget(container)
            else:
                # 退化：直接挂在窗口上（不影响其它布局）
                container = QWidget(self)

            grid = QGridLayout(container)
            grid.setObjectName("order_gridLayout")
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(26)
            container.setLayout(grid)
            self.order_gridLayout = grid
            return grid
        except Exception as e:
            print("[Order] _ensure_order_grid error:", e)
            return None


    def _clear_layout_soft(self, layout: QGridLayout):
        """温和清空网格：移除并销毁其中的控件/子布局（不替换布局本身）。"""
        try:
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                sub = item.layout()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
                elif sub is not None:
                    # 递归清子布局
                    while sub.count():
                        it2 = sub.takeAt(0)
                        w2 = it2.widget()
                        l2 = it2.layout()
                        if w2: w2.setParent(None); w2.deleteLater()
                        if l2:
                            # 清空子布局里的项
                            while l2.count():
                                it3 = l2.takeAt(0)
                                w3 = it3.widget()
                                if w3: w3.setParent(None); w3.deleteLater()
                            l2.deleteLater()
            layout.invalidate()
        except Exception as e:
            print("[Order] 清空订单网格失败：", e)
    def _apply_checked_visual(self, card, checked: bool):
        """
        把一张卡设为选中/未选中：
        - 优先调用卡片自己实现的 setXXX；
        - 再用属性 + style 刷新，保证颜色跟着变。
        """
        if card is None:
            return
        try:
            if hasattr(card, "blockSignals"):
                card.blockSignals(True)

            # 你的 OrderCardWidget 可能实现了其中任意一个
            for name in (
                "setChecked", "setSelected",
                "set_active", "setActive",
                "set_select",
                "set_choose", "setChoosed",
                "set_no_style",
            ):
                fn = getattr(card, name, None)
                if callable(fn):
                    try:
                        fn(checked)
                    except TypeError:
                        # 像 set_no_style() 这种可能不收参数，就在清样式时直接调用
                        if not checked:
                            fn()
                    break

            # 兜底：用属性驱动样式，然后强制刷新
            if hasattr(card, "setProperty"):
                card.setProperty("checked",  bool(checked))
                card.setProperty("selected", bool(checked))
                card.setProperty("active",   bool(checked))

            if hasattr(card, "style") and callable(card.style):
                card.style().unpolish(card)
                card.style().polish(card)
            if hasattr(card, "update"):
                card.update()
        finally:
            if hasattr(card, "blockSignals"):
                card.blockSignals(False)


    def _on_card_changed(self, card, bean, is_active: bool):
        """
        接管 changed_order(bean, is_active) 信号，实现“单选”并同步按钮/变量。
        """
        if is_active:
            # 1) 先取消其它卡
            self._set_single_selection(card)

            # 2) 记录当前选中
            self.select_order_tee_bean = bean
            self.selected_order_id = getattr(bean, "id", None)
            self._current_selected_card = card

            # 3) 显式给当前卡打上“选中”视觉
            self._apply_checked_visual(card, True)

            # 4) 启用按钮
            if hasattr(self, "btn_begin_make"):  self.btn_begin_make.setEnabled(True)
            if hasattr(self, "btn_cancel_make"): self.btn_cancel_make.setEnabled(True)
        else:
            if getattr(self, "_current_selected_card", None) is card:
                self._current_selected_card = None
            if self.select_order_tee_bean is bean:
                self.select_order_tee_bean = None
                self.selected_order_id = None

            # 若都没选中就置灰
            any_selected = False
            for w in getattr(self, "order_card_widgets", []):
                try:
                    # 尽力从多种来源判断是否还“选中”
                    if hasattr(w, "isChecked") and callable(getattr(w, "isChecked")) and w.isChecked():
                        any_selected = True; break
                    if hasattr(w, "property") and (w.property("checked") or w.property("selected") or w.property("active")):
                        any_selected = True; break
                except Exception:
                    pass

            if not any_selected:
                if hasattr(self, "btn_begin_make"):  self.btn_begin_make.setEnabled(False)
                if hasattr(self, "btn_cancel_make"): self.btn_cancel_make.setEnabled(False)

    def _card_set_checked(self, card, checked: bool) -> bool:
        """
        把一张卡设为选中/未选中；兼容常见自定义方法，尽量避免递归触发信号。
        返回 True 表示我们认为设置成功（样式或状态已刷新）。
        """
        if card is None:
            return False
        try:
            if hasattr(card, "blockSignals"):
                card.blockSignals(True)

            # 你的 OrderCardWidget 可能实现了其中任意一个
            for name in ("setChecked", "setSelected", "set_active", "setActive", "set_select", "setChoosed", "setChoose"):
                fn = getattr(card, name, None)
                if callable(fn):
                    fn(checked)
                    if hasattr(card, "blockSignals"):
                        card.blockSignals(False)
                    return True

            # 兜底：用 Qt 属性刷新样式
            if hasattr(card, "setProperty"):
                card.setProperty("checked", bool(checked))
                if hasattr(card, "style") and callable(card.style):
                    card.style().unpolish(card); card.style().polish(card)
                if hasattr(card, "update"): card.update()

            if hasattr(card, "blockSignals"):
                card.blockSignals(False)
            return True
        except Exception:
            try:
                if hasattr(card, "blockSignals"):
                    card.blockSignals(False)
            except Exception:
                pass
            return False


    def _set_single_selection(self, selected_card):
        """确保同一时间只有 selected_card 选中，其它全部取消并刷新样式。"""
        for w in getattr(self, "order_card_widgets", []):
            if w is selected_card:
                continue
            # 不依赖 isChecked 判定，直接清掉视觉 & 逻辑状态
            self._apply_checked_visual(w, False)


    def _update_begin_make_icon(self, bean=None):
        """
        根据订单 bean 的 cup 字段，刷新“开始制作”按钮上的图标，并打印调试信息。
        优先用 bean.cup，没有就从菜单 json 里反查。
        """
        btn = getattr(self, "btn_begin_make", None)
        if btn is None:
            print("[CupDebug] _update_begin_make_icon: 找不到 btn_begin_make")
            return

        # 1) 没有 bean：恢复默认成品杯
        if bean is None:
            print("[CupDebug] _update_begin_make_icon: bean=None，恢复默认成品杯图标")
            btn.setIcon(self.icon_cup_finished)
            print("[CupDebug] _update_begin_make_icon: 默认图标 isNull? ",
                  btn.icon().isNull())
            return

        name = str(getattr(bean, "name", "") or
                   getattr(bean, "tee_name", "")).strip()

        # 2) 先看 bean 本身有没有 cup 字段
        cup = ""
        for attr in ("cup", "cup_type"):
            if hasattr(bean, attr):
                cup = getattr(bean, attr) or ""
                break
        cup = str(cup).strip()

        # 3) 如果 bean 上没有 cup，就从菜单 json 里按饮品名反查
        if not cup:
            name = str(
                getattr(bean, "name", "") or
                getattr(bean, "tee_name", "") or
                getattr(bean, "product_name", "") or
                getattr(bean, "product_simp", "")
            ).strip()

            print("[CupDebug] _update_begin_make_icon: bean 上没 cup，尝试用名字反查：", repr(name))

            if name:
                # 懒加载菜单里的 cup 映射
                if not getattr(self, "_cup_by_drink", None):
                    try:
                        with open(_menu_path(), "r", encoding="utf-8") as f:
                            items = json.load(f) or []
                        self._cup_by_drink = {
                            normalize_drink_name(str(i.get("Name", "")).strip()):
                            str(i.get("cup", "")).strip()
                            for i in items
                            if i.get("Name")
                        }
                    except Exception as e:
                        print("[CupIcon] 加载菜单 cup 失败：", e)
                        self._cup_by_drink = {}

                key = normalize_drink_name(name)
                cup = self._cup_by_drink.get(key, "")

        cup_key = str(cup).replace(" ", "")
        icon = self.icon_cup_finished  # 默认成品杯
        icon_name = "Finished_Cup"

        if "雪克" in cup_key:
            icon = self.icon_cup_shaker
            icon_name = "Shaker_Cup"
        elif ("沙冰" in cup_key) or ("碎冰" in cup_key) or ("搅拌" in cup_key):
            icon = self.icon_cup_smoothie
            icon_name = "Smoothie_Cup"

        print("[CupDebug] _update_begin_make_icon:",
              f"order_id={getattr(bean, 'id', None)} name={name!r} "
              f"cup字段={cup!r} cup_key={cup_key!r} -> 使用图标={icon_name}")
        btn.setIcon(icon)
        print("[CupDebug] _update_begin_make_icon: 设置后 btn.icon().isNull? ",
              btn.icon().isNull())


    def _on_card_changed(self, card, bean, is_active: bool):
        """
        接管 changed_order(bean, is_active) 信号，实现“单选”并同步按钮/变量。
        """
        if is_active:
            # 1) 先取消其它卡
            self._set_single_selection(card)

            # 2) 记录当前选中
            self.select_order_tee_bean = bean
            self.selected_order_id = getattr(bean, "id", None)
            self._current_selected_card = card

            # 3) 显式给当前卡打上“选中”视觉
            self._apply_checked_visual(card, True)

            # 4) 启用按钮
            if hasattr(self, "btn_begin_make"):
                self.btn_begin_make.setEnabled(True)
            if hasattr(self, "btn_cancel_make"):
                self.btn_cancel_make.setEnabled(True)

            # 5) 同时刷新“开始制作”图标（你之前的逻辑）
            try:
                self._update_begin_make_icon(bean)
            except Exception as e:
                print("[CupDebug] _on_card_changed: 更新按钮图标异常：", e)

        else:
            # 当前卡被取消
            if getattr(self, "_current_selected_card", None) is card:
                self._current_selected_card = None
            if self.select_order_tee_bean is bean:
                self.select_order_tee_bean = None
                self.selected_order_id = None

            # 若都没选中就置灰
            any_selected = False
            for w in getattr(self, "order_card_widgets", []):
                try:
                    # 尽力从多种来源判断是否还“选中”
                    if hasattr(w, "isChecked") and callable(getattr(w, "isChecked")) and w.isChecked():
                        any_selected = True
                        break
                    if hasattr(w, "property") and (
                        w.property("checked") or
                        w.property("selected") or
                        w.property("active")
                    ):
                        any_selected = True
                        break
                except Exception:
                    pass

            if not any_selected:
                if hasattr(self, "btn_begin_make"):
                    self.btn_begin_make.setEnabled(False)
                if hasattr(self, "btn_cancel_make"):
                    self.btn_cancel_make.setEnabled(False)
                # 也可以在这里恢复默认成品杯图标
                try:
                    self._update_begin_make_icon(None)
                except Exception:
                    pass
    
    def _apply_card_availability(self, card, disabled: bool):
        if not card:
            return

        if disabled:
            # 1) 置灰（保留你原有的透明度）
            eff = QGraphicsOpacityEffect(card)
            eff.setOpacity(0.40)
            card.setGraphicsEffect(eff)
            card.setToolTip("原料未匹配或余量不足")

            # 2) 遮罩不要盖到顶部 0~60px（那里放着 X）
            #    遮罩的父亲建议用 ui.widget（卡片内部根容器），避免跨父级 raise_ 失效
            ui = getattr(card, "ui", None)
            host = getattr(ui, "widget", None) or card  # 有 ui.widget 就用它，没就退回 card
            mask = getattr(card, "_mask", None)
            if mask is None or mask.parent() is not host:
                mask = QtWidgets.QWidget(host)
                mask.setObjectName("_cardMask")
                mask.setStyleSheet("background: transparent;")  # 调试可改成 rgba(255,0,0,0.08)
                mask.setAttribute(Qt.WA_TransparentForMouseEvents, False)
                card._mask = mask

            # 关键：避开顶部 60px（X 所在条带）
            w, h = host.width(), host.height()
            mask.setGeometry(0, 60, max(0, w), max(0, h - 60))
            mask.show()
            mask.raise_()  # 先把遮罩放上来

            # 3) 再把 X 顶栏抬到遮罩之上（确保可点）
            ov  = getattr(ui, "_overlay", None)
            btn = getattr(ui, "btn_close", None)
            if ov:  ov.raise_()
            if btn: btn.raise_()
            # 取得饮品名：先用缓存，没有就反查映射
            name = getattr(card, "_menu_name", None)
            if not name:
                name = next((n for n, w in self.menu_cards_by_name.items() if w is card), "")
                setattr(card, "_menu_name", name)

            # 让遮罩点击弹窗（而不是单纯吞掉事件）
            mask.setCursor(Qt.PointingHandCursor)
            mask.mousePressEvent = lambda e, n=name: self._on_disabled_card_clicked(n, e)

        else:
            # 恢复
            card.setGraphicsEffect(None)
            card.setToolTip("")
            if hasattr(card, "_mask") and card._mask:
                card._mask.hide()



    def _poll_menu_availability(self):
        """
        单次读取 DB 映射 & 余量 → 遍历所有饮品：
        A) 有未匹配材料 → 置灰
        B) 都匹配但任一所需通道余量 < 50g（含冰/碎冰） → 置灰
        """
        try:
            name2letter = get_name_to_letter_map_from_db()     # 只查一次
            letter2margin = get_letter_to_margin_map_from_db() # 只查一次
        except Exception as e:
            print("[ERR] 读取通道映射/余量失败：", e)
            # 安全起见，全禁用一次
            for card in self.menu_cards_by_name.values():
                self._apply_card_availability(card, True)
            self._disabled_menu_names = set(self.menu_cards_by_name.keys())
            self._missing_names_by_name = {k: {"<异常>"} for k in self.menu_cards_by_name.keys()}
            return

        disabled = set()
        reason_map = {}

        IGNORE_NAMES = {"水"}

        ice_name_auto_map, ice_letters = get_ice_channel_cfg_from_db()
        manual_ice_names = {n for n, auto in ice_name_auto_map.items() if not auto}
        # 手动加冰：配方里的“冰/碎冰”不再要求映射与余量
        if manual_ice_names:
            IGNORE_NAMES |= set(manual_ice_names)

        # 为“最长子串优先”的宽松匹配准备一次 keys
        sorted_keys = sorted(name2letter.keys(), key=len, reverse=True)

        for drink_name, bean in self.menu_beans_by_name.items():
            recipe_text = (getattr(bean, "Recipe", "") or getattr(bean, "recipe", "") or "").strip()
            if not recipe_text:
                self._apply_card_availability(self.menu_cards_by_name.get(drink_name), True)
                disabled.add(drink_name); reason_map[drink_name] = {"<无配方>"}
                continue

            # ——把“中文配方”解析成 (材料名, 克数) 列表
            try:
                pairs = parse_material_text_pairs(recipe_text)   # 例如 [('冰',100), ('四季春茶',20), ...]
            except Exception as e:
                print("[ERR] 解析配方失败：", e, recipe_text)
                self._apply_card_availability(self.menu_cards_by_name.get(drink_name), True)
                disabled.add(drink_name); reason_map[drink_name] = {"<异常>"}
                continue

            # ——配方名→字母通道，记录是否未匹配，以及动态冰/糖集合
            tokens, ICE_dyn, SUGAR_dyn, missing = [], set(), set(), set()
            for raw_name, val in pairs:
                key = (raw_name or "").replace("，", ",").strip()
                key_norm = _norm_txt(key)
                is_ice_token = False
                try:
                    is_ice_token = _match_any_name(key_norm, set(ice_name_auto_map.keys()))
                except Exception:
                    is_ice_token = ("冰" in key) or ("碎冰" in key)

                # 手动加冰：跳过冰/碎冰，不参与匹配/余量/置灰
                if manual_ice_names and is_ice_token and _match_any_name(key_norm, manual_ice_names):
                    continue
                ch = name2letter.get(key)
                if not ch:
                    for k in sorted_keys:
                        if k in key or key in k:
                            ch = name2letter[k]; break
                if not ch:
                    if key not in IGNORE_NAMES:
                        missing.add(key)
                    continue
                if is_ice_token:
                    ICE_dyn.add(ch)
                if any(k in key for k in ("糖", "糖浆", "果糖", "蔗糖", "黑糖", "红糖", "白砂糖", "蜂蜜", "糖水")):
                    SUGAR_dyn.add(ch)
                tokens.append((ch, val))

            # ——A) 未匹配直接置灰
            if missing:
                self._apply_card_availability(self.menu_cards_by_name.get(drink_name), True)
                disabled.add(drink_name); reason_map[drink_name] = set(missing)
                continue

            # ——B) 余量<阈值（含冰/碎冰）
            low_stock = False
            need_letters = {ch for ch, _ in tokens}
            for ch in need_letters | ICE_dyn:    # 显式把冰/碎冰也纳入检查
                mg = float(letter2margin.get(ch, 0))
                if mg < LOW_STOCK_THRESHOLD_G:   # 50g 阈值（含 0g）
                    low_stock = True
                    break

            is_disabled = low_stock
            self._apply_card_availability(self.menu_cards_by_name.get(drink_name), is_disabled)
            if is_disabled:
                disabled.add(drink_name)
                reason_map[drink_name] = {f"余量<{LOW_STOCK_THRESHOLD_G}g"}

        # 缓存状态：点击时拦截用
        self._disabled_menu_names = disabled
        self._missing_names_by_name = reason_map
        self._refresh_conduit_unused_marks()
    def _ensure_menu_grid(self):
        """
        返回一个可靠的 QGridLayout 用于“手动出茶-菜单区”：
        - 若 container 本身是 QGridLayout -> 直接复用；
        - 若 container 是 BoxLayout（HBox/VBox）：
            1) 先扫描其中是否已有 QGridLayout 子布局，若有 -> 复用，并移除其它项；
            2) 否则清空该 BoxLayout 的所有子项（含子布局），只保留一个新的 QGridLayout；
        - 若 container 没有任何布局 -> 直接挂 QGridLayout。
        """
        from PyQt5.QtWidgets import QWidget, QGridLayout, QScrollArea, QVBoxLayout, QHBoxLayout, QLayout
        from PyQt5 import sip

        # --- 找 scrollArea（只在手动出茶页容器里找） ---
        def _find_menu_scroll_area():
            w = getattr(self, "menu_content_widget", None)
            if w:
                p = w
                while p is not None and not isinstance(p, QScrollArea):
                    p = p.parent()
                if isinstance(p, QScrollArea):
                    return p
            mt = getattr(self, "sw_mt_widget", None)
            if mt is None:
                return None
            cands = mt.findChildren(QScrollArea) or []
            for sa in cands:
                try:
                    if "menu" in sa.objectName().lower():
                        return sa
                except Exception:
                    pass
            return cands[0] if cands else None

        sa = _find_menu_scroll_area()
        if sa is None:
            print("[Menu] _ensure_menu_grid: 未定位到菜单滚动区")
            return None
        try:
            sa.setWidgetResizable(True)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass

        # 承载容器
        container = sa.widget()
        if container is None:
            container = QWidget()
            container.setObjectName("menu_content_widget")
            sa.setWidget(container)
        self.menu_content_widget = container

        lay = container.layout()

        # 情况 A：container 已是 QGridLayout
        if isinstance(lay, QGridLayout):
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setHorizontalSpacing(24)
            lay.setVerticalSpacing(24)
            self.menu_gridLayout = lay
            return lay

        # 情况 B：container 是 BoxLayout（或其它 QLayout）
        if isinstance(lay, QLayout):
            # 1) 先找是否已有 QGridLayout 子布局 -> 复用它，并移除其它项
            found_grid = None
            for i in range(lay.count()):
                it = lay.itemAt(i)
                sub_lay = it.layout()
                if isinstance(sub_lay, QGridLayout):
                    found_grid = sub_lay
                    break
            if found_grid is not None:
                # 把其它 item（widget 或 子布局）全部移除并销毁，只保留这个网格
                for i in reversed(range(lay.count())):
                    it = lay.itemAt(i)
                    if it.layout() is found_grid:
                        continue
                    lay.takeAt(i)
                    if it.widget() is not None:
                        w = it.widget(); w.setParent(None); w.deleteLater()
                    elif it.layout() is not None:
                        # 递归删除子布局
                        sub = it.layout()
                        while sub.count():
                            j = sub.takeAt(0)
                            if j.widget(): j.widget().setParent(None); j.widget().deleteLater()
                            if j.layout(): 
                                sub2 = j.layout()
                                while sub2.count():
                                    k = sub2.takeAt(0)
                                    if k.widget(): k.widget().setParent(None); k.widget().deleteLater()
                                sip.delete(sub2)
                        sip.delete(sub)
                found_grid.setContentsMargins(0, 0, 0, 0)
                found_grid.setHorizontalSpacing(24)
                found_grid.setVerticalSpacing(24)
                self.menu_gridLayout = found_grid
                return found_grid

            # 2) 没有网格子布局 -> 清空该布局的所有子项，添加一个新的 QGridLayout
            for i in reversed(range(lay.count())):
                it = lay.takeAt(i)
                if it.widget() is not None:
                    w = it.widget(); w.setParent(None); w.deleteLater()
                elif it.layout() is not None:
                    sub = it.layout()
                    # 深度清空后删除
                    while sub.count():
                        j = sub.takeAt(0)
                        if j.widget(): j.widget().setParent(None); j.widget().deleteLater()
                        if j.layout():
                            sub2 = j.layout()
                            while sub2.count():
                                k = sub2.takeAt(0)
                                if k.widget(): k.widget().setParent(None); k.widget().deleteLater()
                            sip.delete(sub2)
                    sip.delete(sub)

            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(24)
            grid.setVerticalSpacing(24)
            lay.addLayout(grid)
            self.menu_gridLayout = grid
            return grid

        # 情况 C：container 没有布局 -> 直接挂网格
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(24)
        container.setLayout(grid)
        self.menu_gridLayout = grid
        return grid
    # 放在 class Main1080Window 里面其它方法旁边
    def _resolve_ingredients_for_menu(self, menu) -> str:
        """
        返回本杯要追加的 ingredients 字符串（如 'A050'），找不到则返回空串。
        优先读 bean 上的属性；没有再到 menu_xlsx/tea_drinks_menu.json 里按 Name 匹配。
        """
        try:
            # 1) 直接从 bean 读（若你的 MenuTeeBean / TeeBean 已经带这个字段）
            ing = (getattr(menu, "ingredients", "") or "").strip()
            if ing:
                return ing

            # 2) 从 JSON 文件按 Name 匹配（显示名里可能带“-三分糖”，统一裁掉后缀）
            name = (getattr(menu, "Name", None) or
                    getattr(menu, "name", None) or
                    getattr(menu, "tee_name", None) or
                    getattr(menu, "product_name", None) or
                    getattr(menu, "productName", None) or
                    (callable(getattr(menu, "get_Name", None)) and menu.get_Name()) or "")
            name = normalize_drink_name(str(name)) if name else ""

            if not name:
                return ""
            import json
            with open(_menu_path(), "r", encoding="utf-8") as f:
                items = json.load(f) or []
            for it in items:
                if str(it.get("Name", "")).strip() == name:
                    return (it.get("ingredients") or "").strip()
        except Exception:
            pass
        return ""
    def _delete_drink_card_by_name(self, name: str):
        """从菜单网格中删除名为 name 的饮品卡片，并重排网格。"""
        if not name:
            return
        w = self.menu_cards_by_name.pop(name, None)
        self.menu_beans_by_name.pop(name, None)

        if w is not None:
            # 从布局移除并销毁
            try:
                if self.menu_gridLayout:
                    self.menu_gridLayout.removeWidget(w)
            except Exception:
                pass
            w.setParent(None)
            w.deleteLater()

            # 重新压紧网格（把空洞补齐）
            self._reflow_menu_grid()

    def _reflow_menu_grid(self):
        """根据当前 self.menu_cards_by_name 的顺序，重新把卡片按 3 列铺排。"""
        grid = getattr(self, "menu_gridLayout", None)
        if grid is None:
            return

        # 收集当前仍然存在的卡片
        cards = [w for _, w in list(self.menu_cards_by_name.items()) if w is not None]

        # 清空网格中的项（不 delete 卡片本身）
        try:
            while grid.count():
                item = grid.takeAt(0)
                sub = item.layout()
                w = item.widget()
                if w is not None:
                    grid.removeWidget(w)  # 只是移除，不销毁
                elif sub is not None:
                    # 清理子布局项
                    while sub.count():
                        it2 = sub.takeAt(0)
                        if it2.widget():
                            sub.removeWidget(it2.widget())
        except Exception:
            pass

        # 重新按 3 列铺排
        self.menu_num = 0
        for i, w in enumerate(cards):
            row, col = divmod(i, 3)
            grid.addWidget(w, row, col, 1, 1)
            self.menu_num += 1
    def _confirm_delete(self, name: str):
        if not name: 
            return
        # 富文本可以加粗饮品名
        html = f"确认要删除 <b>{name}</b> 吗？"
        if GreenConfirmBox.ask(self, "删除饮品", html, yes_text="是", no_text="否"):
            # 先删 JSON，保证持久化
            removed = remove_menu_item_from_json(name)
            # 再删界面卡片
            self._delete_drink_card_by_name(name)
            print(f"[Menu] 删除 {name} -> JSON:{'OK' if removed else '未找到'}")

    def _on_disabled_card_clicked(self, name: str, event=None):
        """灰卡片被点击时，弹出‘材料未匹配/余量不足’提示。"""
        if event: 
            event.accept()

        # 取缺失材料清单（你之前在轮询里维护的映射）
        miss = []
        try:
            miss = sorted(list(self._missing_names_by_name.get(name, [])))
        except Exception:
            pass

        if miss:
            html = (
                "以下材料没有找到对应通道：<br>"
                f"<span style='color:#E53935;font-weight:700'>{'<br>'.join(miss)}</span><br><br>"
                "请在“管理-物料绑定”里设置后再试。"
            )
            GreenMessageBox.warning(self, "材料未匹配", html)
        else:
            GreenMessageBox.warning(
                self, "暂不可制作",
                "该饮品当前不可制作，可能余量不足或尚未绑定，请在“管理-物料绑定”里检查后重试。"
            )

    def _collect_used_material_names(self) -> set:
        """遍历 tea_drinks_menu.json 的所有 Recipe，返回被使用的‘材料名’集合（严格一致）"""
        used = set()
        mp = _menu_path()
        if not os.path.exists(mp):
            alt = os.path.join(os.path.abspath("."), "tea_drinks_menu.json")
            if os.path.exists(alt):
                mp = alt
            else:
                print("[menu] 未找到 JSON：", mp, "或", alt)
                return used

        try:
            with open(mp, "r", encoding="utf-8") as f:
                items = json.load(f) or []
            for it in items:
                recipe = str(it.get("Recipe", "") or it.get("recipe", "")).strip()
                if not recipe:
                    continue
                # 只提取“材料名 + 数字”里的材料名部分，不做任何别名/包含转换
                for m in re.finditer(r'([^\d\s]+)\s*\d+', recipe):
                    name = m.group(1).strip()
                    if name:
                        used.add(name)
        except Exception as e:
            print("[menu] 解析 Recipe 失败：", e)

        print(f"[menu] used({len(used)}): {sorted(used)}")  # 调试
        return used


    def _refresh_conduit_unused_marks(self):
        used = self._collect_used_material_names()
        print(f"[menu] used({len(used)}): {sorted(list(used))}")

        for card in self.conduit_card_widgets:
            try:
                ui = card.ui
                raw_name = ui.conduit_card_name_l.text().strip()

                # ✅ 兜底：发现还是默认“红茶”或空，就从 bean 里取
                if (not raw_name) or raw_name == "红茶":
                    if hasattr(card, "bean") and getattr(card.bean, "name", ""):
                        raw_name = str(card.bean.name).strip()

                hit = raw_name in used
                # ……后面按你的逻辑显示/隐藏 X
                # ui.conduit_card_warn_close_btn.setVisible(not hit)
                # 或者 card.set_x_badge_visible(not hit)

                cid_text = ui.conduit_card_id_l.text().strip() if hasattr(ui, "conduit_card_id_l") else "?"
                print(f"[menu] card {cid_text:>3}: '{raw_name}' == any_used ? {hit}")

            except Exception as e:
                print(f"[menu] mark error: {e}")

    def _collect_used_conduit_names(self) -> set[str]:
        """
        读取 menu_xlsx/tea_drinks_menu.json，把每个条目的 Recipe 解析成材料名集合。
        例如：'冰100 碎冰100 四季春茶020 糖浆100' -> {'冰','碎冰','四季春茶','糖浆'}
        """
        used = set()
        try:
            menu_path = _res_path(os.path.join("menu_xlsx", "tea_drinks_menu.json"))
            if not os.path.exists(menu_path):
                print("[menu] JSON 不存在：", menu_path)
                return used
            import json, re
            with open(menu_path, "r", encoding="utf-8") as f:
                items = json.load(f) or []
            for it in items:
                recipe = str(it.get("Recipe", "")).strip()
                if not recipe:
                    continue
                # 把“材料名+三位数”切出来；材料名允许有空格/中文
                for m in re.finditer(r'([^\d\s]+)\s*\d{3}', recipe):
                    used.add(m.group(1).strip())
        except Exception as e:
            print("[menu] 解析 Recipe 出错：", e)
        print(f"[menu] used({len(used)}): {sorted(used)}")
        return used


    def _iter_conduit_cards(self):
        """在当前页面查找所有 ConduitCardWidget（不依赖“自己记列表”）。"""
        try:
            from control.conduit_card_mata import ConduitCardWidget
        except Exception:
            return []
        return self.findChildren(ConduitCardWidget)


    def _refresh_conduit_unused_marks(self):
        """
        根据 used 集合，显示/隐藏每张通道卡片上的“未被使用X”图标。
        ★ 不再访问 widget.ui，仅靠 findChild 查 Label。
        """
        used = self._collect_used_conduit_names()
        for w in self._iter_conduit_cards():
            name_l: QLabel = w.findChild(QLabel, "conduit_card_name_l")
            mark_l: QLabel = w.findChild(QLabel, "conduit_unused_x")
            if not name_l or not mark_l:
                # 避免刷屏，把多余日志删掉或降低频率
                # print("[menu] mark warn: 找不到 name 或 X label")
                continue
            mat_name = name_l.text().strip()
            mark_l.setVisible(mat_name not in used)
    def do_single_full_with_dialog(self):
        """
        点击“单管满管”后：
        1) 先通过原有信号把命令发给串口线程（固定 999）
        2) 再弹出绿色弹窗，按钮“停止”；点击后发送 stop 到串口
        """
        # 1) 走你现有的信号链路 -> 串口线程 conduit_serial_one('单管满管', beans)
        beans = getattr(self, "select_conduit_bean", []) or []
        self.conduit_manager_one.emit('单管满管', beans)   # 已在 __init__/init 里连接到线程方法，无需改动

        # 2) 绿色弹窗（单按钮），按钮文案设为“停止”
        #    标题可自定义，这里用“提示”；正文“单管满管中......”
        dlg = GreenMessageBox("提示", "<br>单管满管中......", self, ok_text="停止")
        if dlg.exec_() == QDialog.Accepted:
            # 点击“停止” -> 向下位机发送 stop
            # 直接用线程的 send_data，保持与你工程其它地方一致
            self.conduit_serial_thread.send_data('stop')

    def _show_update_choice_dialog(self):
        """点击更新系统卡片时弹出选择框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton
        dlg = QDialog(self)
        dlg.setWindowTitle("选择操作")
        dlg.setFixedSize(300, 150)
        dlg.setStyleSheet("QDialog{background:#fff;border-radius:12px;}")
        layout = QVBoxLayout(dlg)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        btn_sys = QPushButton("更新系统")
        btn_sys.setFixedHeight(45)
        btn_sys.setStyleSheet("QPushButton{background:#53CB31;color:white;border-radius:8px;font-size:16px;}")
        btn_sys.clicked.connect(lambda: (dlg.accept(), self.on_check_update_clicked()))
        layout.addWidget(btn_sys)
        
        btn_menu = QPushButton("更新菜单")
        btn_menu.setFixedHeight(45)
        btn_menu.setStyleSheet("QPushButton{background:#2196F3;color:white;border-radius:8px;font-size:16px;}")
        btn_menu.clicked.connect(lambda: (dlg.accept(), self._open_menu_update_page()))
        layout.addWidget(btn_menu)
        
        dlg.exec_()

    def _open_menu_update_page(self):
        """打开菜单更新页面"""
        if self._menu_update_widget is None:
            self._menu_update_widget = MenuUpdateWidget(self.setting_menu_update)
            self._menu_update_widget.btn_back.clicked.connect(self._back_from_menu_update)
            self._menu_update_widget.menu_changed.connect(self._on_menu_data_changed)
            self.verticalLayout_menu_update_page.addWidget(self._menu_update_widget)
        self.stackedWidget_setting.setCurrentWidget(self.setting_menu_update)
    
    def _back_from_menu_update(self):
        """从菜单更新页返回设置首页"""
        self.stackedWidget_setting.setCurrentWidget(self.setting_home)
    
    def _on_menu_data_changed(self):
        """菜单数据变更后刷新菜单显示"""
        try:
            self._reload_tips_from_menu()
            self._refresh_manual_menu()
        except Exception as e:
            print(f"[菜单刷新] 失败: {e}")

    def _reload_tips_from_menu(self):
        """重载 tips 映射（用于菜单更新后立即生效）"""
        try:
            menu_path = _menu_path()
            if not os.path.exists(menu_path):
                print(f"[TipsDebug] 菜单文件不存在：{menu_path}")
                return
            with open(menu_path, "r", encoding="utf-8") as f:
                items = json.load(f) or []
            tips_map = {}
            for item in items:
                name = str(item.get("Name", "")).strip()
                tips = str(item.get("tips", "")).strip()
                if name and tips:
                    tips_map[name] = tips
            self._tips_by_drink = tips_map
            print(f"[TipsDebug] reload tips 完成，共 {len(self._tips_by_drink)} 条")
        except Exception as e:
            import traceback; traceback.print_exc()
            print("[TipsDebug] reload tips 失败：", e)

    def on_check_update_clicked(self):
        # 1) 本地版本（从正在运行的 exe 名里解析 MikeTee_1.0 这种）
        local_v = current_version()

        # 2) 仅拉版本清单（JSON/TXT），不下载 exe
        remote_v, remote_url = fetch_remote_version()
        if not remote_v or not remote_url:
            _toast(self, "检查更新失败（获取版本号失败）")
            return

        # 3) 没有更高版本 → 直接提示
        if remote_v == local_v:
            _toast(self, "你已经是最新版本")
            return

        # 4) 有新版本 → 先弹确认
        fn = os.path.basename(remote_url) or f"MikeTee_{remote_v}.exe"
        dlg = GreenConfirmBox(
            "发现新版本",
            f"检测到新版本：{remote_v}<br>当前版本：{local_v}<br><br>是否更新为 {fn}？",
            self,
            yes_text="立即更新", no_text="暂不"
        )
        if dlg.exec_() != QDialog.Accepted:
            return
        # 5) 用户确认后再下载并更新
        cache_dir, _log_dir = update_dirs(local_app_path())
        tmp = os.path.join(cache_dir, fn)   # 例如  C:\你的程序目录\update_cache\MikeTee_1.0.6.exe
        prog = QProgressDialog("正在下载更新包 0%", "取消", 0, 100, self)
        prog.setWindowModality(Qt.ApplicationModal)
        prog.setAutoClose(False)
        prog.setMinimumDuration(0)
        prog.setValue(0)

        # 去掉系统标题栏“python”和“？”按钮
        prog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        prog.setWindowTitle("")  # 不再显示 python

        prog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        prog.setMinimumSize(580, 260)   # 关键：放大
        prog.resize(580, 260)

        
        fid = QFontDatabase.addApplicationFont(
            "fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-55-Regular/AlibabaPuHuiTi-3-55-Regular.ttf"
        )
        fams = QFontDatabase.applicationFontFamilies(fid)
        base_family = fams[0] if fams else "Microsoft YaHei"  # 找不到字体时回退雅黑

        font_label = QFont(base_family, 24, QFont.DemiBold)  # 标题/文字更大
        font_btn   = QFont(base_family, 22, QFont.Bold)      # 按钮更大


        # 只保留上面一行的进度文案，不让进度条再显示“0%”
        bar = prog.findChild(QProgressBar)
        if bar:
            bar.setTextVisible(False)

        if bar:
            bar.setTextVisible(False)
            bar.setFixedHeight(26)

        # 把进度弹窗里所有 QLabel / QPushButton 的字体与尺寸放大
        for lab in prog.findChildren(QLabel):
            lab.setFont(font_label)

        for btn in prog.findChildren(QPushButton):
            btn.setFont(font_btn)
            btn.setFixedSize(100, 50)  # 取消按钮更大（宽×高）
        # 绿主题样式可以继续保留
        prog.setStyleSheet("""
        QProgressDialog { background:#ffffff; border:0; }
        QLabel      { color:#2D3A32; font-size:24px; }
        QPushButton { background:#18A058; color:#fff; border-radius:14px;
                    padding:12px 28px; font-size:22px; }
        QPushButton:hover  { background:#1EC87E; }
        QPushButton:pressed{ background:#ffffff; color:#18A058; border:1px solid #18A058; }
        QProgressBar       { height:26px; background:#EDEDED; border-radius:13px; }
        QProgressBar::chunk{ background:#18A058; border-radius:13px; }
        """)
        prog.show()
        prog.move(
            self.geometry().center().x() - prog.width() // 2,
            self.geometry().center().y() - prog.height() // 2
        )
        worker = _DownloadWorker(remote_url, tmp)
        self._upd_worker = worker  # 防止线程对象被回收

        def _on_progress(p: int):
            prog.setValue(p)
            prog.setLabelText(f"正在下载更新包 {p}%")

        worker.progress.connect(_on_progress)

        def _after(res):
            prog.close()
            ok, data = res
            if not ok:
                _toast(self, f"下载失败：{data}")
                return

            # 下载完成后，再询问是否立刻重启并应用更新
            yn = GreenConfirmBox("更新就绪", f"已下载 {fn}<br>是否现在重启并应用更新？",
                                self, yes_text="立即重启", no_text="稍后").exec_()
            if yn != QDialog.Accepted:
                GreenMessageBox.warning(self, "提示", "更新包已下载，可稍后在设置里再次安装")
                return

            # 用户确认 → 用“无备份替换”的方式更新并重启
            apply_update_and_restart(local_app_path(), tmp, debug=False, rename_to=fn)
            from PyQt5.QtWidgets import QApplication
            QApplication.instance().quit()

        worker.done.connect(_after)
        prog.canceled.connect(worker.terminate)
        worker.start()
    def _graceful_stop_before_update(self):
        """尽可能释放占用：停串口/子线程 → 让 .exe 可删除"""
        try:
            self.notice_thread_serial_stop.emit()
        except Exception:
            pass
        try:
            self.notice_close_thread.emit()
        except Exception:
            pass
        QApplication.processEvents()
        try:
            import time as _t; _t.sleep(0.3)
        except Exception:
            pass

    def _do_restart_now(self, tmp_path: str):
        """用户确认‘立即重启’后调用"""
        from control.update_util import update_dirs, local_app_path
        cache_dir, _ = update_dirs(local_app_path())
        tmp_path = os.path.join(cache_dir, self._update_fn)   # 你的下载文件名 fn 已有

        # 用户点“立即重启”
        self._do_restart_now(tmp_path)
    def _check_low_stock_popup(self):
        try:
            # 从库里拿余量与“材料名→通道字母”的映射
            letter2margin = get_letter_to_margin_map_from_db() or {}  # {'A': 1944, ...}
            name2letter   = get_name_to_letter_map_from_db() or {}    # {'奇异果汁':'A', ...}
            # 反转得到 “通道字母→材料名”
            letter2name = {}
            for name, ch in name2letter.items():
                letter2name.setdefault(ch, name)

            # 组装这次需要提醒的列表（只提醒“尚未提醒过”的低余量通道）
            todo = []
            for ch, mg in letter2margin.items():
                if ch in EXCLUDE_LOW_STOCK_LETTERS:
                    continue
                try:
                    mgf = float(mg)
                except Exception:
                    mgf = 0.0
                if mgf < LOW_STOCK_POPUP_G and ch not in self._low_stock_notified:
                    idx = ord(str(ch)[0].upper()) - ord('A') + 1  # A->1, B->2...
                    mat = letter2name.get(ch, ch)
                    todo.append(f"{idx}# 管道（{mat}）剩余 {mgf:.0f}g")

            # 有新低余量 -> 弹一次绿色提醒框，并把这些通道记入“已提醒”
            if todo:
                html = "<br>".join(f"{line}，物料不足 {LOW_STOCK_POPUP_G}g" for line in todo)
                GreenMessageBox.warning(self, "物料不足", html)
                self._low_stock_notified.update(ch for ch, mg in letter2margin.items()
                                                if float(mg) < LOW_STOCK_POPUP_G)

            # 余量恢复≥阈值 -> 允许下次重新提醒
            for ch, mg in letter2margin.items():
                try:
                    if float(mg) >= LOW_STOCK_POPUP_G and ch in self._low_stock_notified:
                        self._low_stock_notified.remove(ch)
                except Exception:
                    pass
        except Exception as e:
            print("[low-stock-popup] error:", e)

    def init_maketee_conduit_control_from_maketee_table(self):
        self._dbg("[mk-init] called")
        ok = self._ensure_maketee_grid()
        grid = getattr(self, "maketee_conduit_gridLayout", None)
        self._dbg(f"[mk-init] ensure grid -> {ok}, grid={grid}")

        # ① 幂等：如果已经有卡片了（count>0），不要再清空、更不要重启线程
        cnt = 0
        try:
            cnt = grid.count() if grid else 0
        except Exception:
            cnt = 0
        if cnt > 0:
            self._dbg(f"[mk-init] grid already has {cnt} items -> skip clear & skip restart")
            return

        # ② 没有卡片才清空（事实上为空也清不出啥，但写上更安全）
        if grid:
            try:
                util.clear_layout(grid)
                self._dbg("[mk-init] grid cleared (empty)")
            except Exception as e:
                self._err("[mk-init] clear_layout err:", e)

        self.maketee_conduit_num = 0
        self.maketee_conduit_card_widgets = []

        # ③ 线程状态：不存在或已结束 -> 启动；仍在跑 -> 不重复启动
        th = getattr(self, "maketee_thread", None)
        need_start = (th is None) or (not th.isRunning())
        if not need_start:
            self._dbg("[mk-init] thread is running -> skip start")
            return

        from threads.conduit_thread import MaketeeConduitThread
        self.maketee_thread = MaketeeConduitThread()

        # 用 QueuedConnection，并打印到达
        from PyQt5.QtCore import Qt
        self.maketee_thread.result_maketee_conduit_bean.connect(
            lambda b: (self._dbg(f"[mk-slot] +1 bean to UI: conduit={getattr(b,'conduit',None)}"),
                    self.show_maketee_conduit_bean(b)),
            type=Qt.QueuedConnection
        )
        self.maketee_thread.result_maketee_conduits_bean_list.connect(
            lambda lst: self._dbg(f"[mk-slot] got beans list ({len(lst)})"),
            type=Qt.QueuedConnection
        )

        # 统一优雅退出
        if hasattr(self, "notice_close_thread"):
            try: self.notice_close_thread.disconnect(self.maketee_thread.quit)
            except Exception: pass
            self.notice_close_thread.connect(self.maketee_thread.quit)

        self._dbg("[mk-init] thread.start()")
        self.maketee_thread.start()

    def _on_maketee_beans(self, beans: list):
        """把 maketee_conduit_info 的全量数据广播给泡茶页卡片（与管理页的广播分离）。"""
        try:
            self.notice_maketee_item_conduit.emit(beans)
        except Exception:
            pass

    def _dbg(self, *a):
        print("[UI]", *a)

    def _err(self, *a):
        print("[UI-ERR]", *a)

    def _mk_add_card(self, bean):
        # 保障网格存在
        if not getattr(self, "maketee_conduit_gridLayout", None):
            self._dbg("[mk-add] grid missing -> ensure now")
            if not self._ensure_maketee_grid():
                self._err("[mk-add] ensure grid failed")
                return

        idx = getattr(self, "maketee_conduit_num", 0)
        row, col = divmod(idx, 4)

        # === 你现有的卡片创建与布置逻辑搬过来 ===
        card = ConduitCardMaketeeWidget(bean, self.is_debug)
        card.update_conduit_bean([bean])
        self.maketee_conduit_gridLayout.addWidget(card, row, col, 1, 1)
        card.changed_conduit_card.connect(self.conduit_card_callBack)
        # 订阅泡茶页的后续更新信号（你已有）
        try:
            self.notice_maketee_item_conduit.connect(card.update_conduit_bean)
        except Exception:
            pass

        # 记录
        if not hasattr(self, "maketee_conduit_card_widgets"):
            self.maketee_conduit_card_widgets = []
        self.maketee_conduit_card_widgets.append(card)
        self.maketee_conduit_num = idx + 1

    def _mk_flush_buffer(self):
        buf = getattr(self, "_mk_buffer", [])
        if not buf:
            self._dbg("[mk-buf] empty, skip");  return
        if not (self.is_login or self.is_debug):
            self._dbg("[mk-buf] gate closed, skip");  return

        self._dbg(f"[mk-buf] flushing {len(buf)} beans")

        # 1) 保证网格在位，但不要主动清空（防止把即将刷出来的卡片又清了）
        self._ensure_maketee_grid()
        self.maketee_conduit_num = 0
        self.maketee_conduit_card_widgets = []


        

        # 2) 刷卡
        for b in buf:
            self._mk_add_card(b)
        self._mk_buffer = []

        # 3) 标记“已渲染”，供 init 幂等判断使用
        self._mk_cards_rendered = True

    def _close_small_keyboard(self):
        """统一关闭并清理引用，带轻微冷却时间避免闪烁"""
        kb = getattr(self, "_kb", None)
        if kb:
            try:
                kb.hide()
                kb.close()
            except Exception:
                pass
        self._kb = None
        self._kb_target = None
        self._kb_last_close_ms = int(_time.time() * 1000)
    
    def _show_small_keyboard(self, target, anchor_widget=None, title="出料"):
        """
        仅创建/展示一个键盘实例；重复点击同一输入框不重复创建。
        anchor_widget：用于定位的锚点，小部件（默认用 target 自己）
        """
        now = int(_time.time() * 1000)
        # 冷却 150ms，避免“先关后立刻又开”的闪烁
        if now - getattr(self, "_kb_last_close_ms", 0) < 150:
            return

        # 已经有键盘并且就是给同一个 target 用的 -> 直接返回
        if getattr(self, "_kb", None) and self._kb.isVisible() and self._kb_target is target:
            return

        # 若已有其它 target 的键盘，先关
        if getattr(self, "_kb", None):
            self._close_small_keyboard()

        # === 你的泡茶页小键盘类 ===
        # from control.conduit_card_keyboard_mata import ManagerKeyboardMata as MaketeeKeyboard
        kb = MaketeeKeyboard(title, 0, 0, self)
        kb.setAttribute(Qt.WA_DeleteOnClose, True)
        kb.setWindowFlag(Qt.Tool, True)  # 悬浮小窗，不抢前台主窗口

        # --- 信号绑定（覆盖不同版本的信号名） ---
        # 逐字/逐键插入
        if hasattr(kb, "result_effective_context"):
            kb.result_effective_context.connect(lambda ch, t=target: t.insert(ch))
        elif hasattr(kb, "result_context"):
            kb.result_context.connect(lambda ch, t=target: t.insert(ch))

        # 清空
        if hasattr(kb, "result_effective_clear"):
            kb.result_effective_clear.connect(target.clear)
        elif hasattr(kb, "result_clear"):
            kb.result_clear.connect(target.clear)

        # 确认/完成 -> 关闭键盘
        for sig_name in ("switch_ui", "result_enter", "ok_clicked", "confirm"):
            if hasattr(kb, sig_name):
                getattr(kb, sig_name).connect(self._close_small_keyboard)

        # 锚点定位（默认贴着 target 底部左侧）
        aw = anchor_widget or target
        gl = aw.mapToGlobal(aw.rect().bottomLeft())
        kb.move(gl.x(), gl.y() + 8)  # 微调 8px
        kb.show()

        self._kb = kb
        self._kb_target = target

    def _kb_now_ms(self):
        from PyQt5.QtCore import QDateTime
        return QDateTime.currentMSecsSinceEpoch()

    def _kb_close(self):
        if self._kb:
            try:
                self._kb.close()
            except Exception:
                pass
        self._kb = None
        self._kb_target = None
        self._kb_last_close_ms = self._kb_now_ms()
    def _kb_open_for(self, target_edit):
        # 防抖：刚关闭 180ms 内不重开
        if self._kb_now_ms() - getattr(self, "_kb_last_close_ms", 0) < 180:
            return

        # 如果已打开且目标相同，仅确保位置与抬到最上
        if self._kb and self._kb_target is target_edit and self._kb.isVisible():
            self._kb.raise_()
            self._kb.activateWindow()
            # 重新微调位置
            gl = target_edit.mapToGlobal(target_edit.rect().bottomLeft())
            x = gl.x()
            y = gl.y() + 8
            self._kb.move(x, y)
            return

        # 目标不同或没有实例 → 关闭旧的，重建
        self._kb_close()

        kb = MaketeeKeyboard("出料", 0, 0, self)
        kb.setWindowFlags(kb.windowFlags() | Qt.Popup)  # 点击外部自动关闭
        kb.setAttribute(Qt.WA_DeleteOnClose, True)

        # 输入/清空/确认（直接复用你现有的槽函数或写入目标）
        kb.result_effective_context.connect(lambda ch, t=target_edit: t.insert(ch))
        kb.result_effective_clear.connect(target_edit.clear)
        if hasattr(kb, "switch_ui"):
            kb.switch_ui.connect(kb.close)

        # 关闭时把引用清掉 + 记录时间（用于防抖）
        kb.destroyed.connect(lambda *_: setattr(self, "_kb", None))
        kb.destroyed.connect(lambda *_: setattr(self, "_kb_target", None))
        kb.destroyed.connect(lambda *_: setattr(self, "_kb_last_close_ms", self._kb_now_ms()))

        # 定位在目标输入框左下角
        gl = target_edit.mapToGlobal(target_edit.rect().bottomLeft())
        kb.move(gl.x(), gl.y() + 8)

        kb.show()
        kb.raise_()
        kb.activateWindow()

        self._kb = kb
        self._kb_target = target_edit

    # 统一把 bean 规范成 ['3#'] 的列表
    def _normalize_selected(bean):
        if bean is None:
            return []
        # 已经是 '3#' 这种 
        if isinstance(bean, str):
            s = bean if bean.endswith('#') else (bean + '#')
            return [s]
        # 带方法的对象
        if hasattr(bean, 'get_conduit'):
            return [str(bean.get_conduit())]
        # 普通对象：有属性
        if hasattr(bean, 'conduit'):
            return [str(getattr(bean, 'conduit'))]
        return []
    def show_toast(self, text: str, msec: int = 2000):
    # 复用项目里已有的全局工具函数
        _toast(self, text, msec)


    def _start_device_name_probe(self):
        """若左上角还没有设备名，则定时向 ESP32 请求。"""
        # 当前 UI 是否已有设备名（你可以按需修改默认占位判断条件）
        try:
            raw = (self.device_name.text() or "").strip()
        except Exception:
            raw = ""
        # 取冒号后的部分，判断是否为空或 '—'
        name_part = raw.split("：", 1)[1].strip() if "：" in raw else raw
        self._devname_known = bool(name_part and name_part != "—")

        # 定时器：最多重试 8 次（~10s 左右），拿到后立即停止
        self._devname_req_tries = 0
        if not hasattr(self, "_devname_req_timer"):
            self._devname_req_timer = QtCore.QTimer(self)
            self._devname_req_timer.setInterval(1200)
            self._devname_req_timer.timeout.connect(self._tick_request_device_name)

        if not self._devname_known:
            self._devname_req_timer.start()
            QtCore.QTimer.singleShot(300, self._tick_request_device_name)  # 启动后尽快请求一次

    @QtCore.pyqtSlot()
    def _tick_request_device_name(self):
        if self._devname_known:
            self._devname_req_timer.stop()
            return
        # 线程就绪才发
        th = getattr(self, "conduit_serial_thread", None)
        if th and th.isRunning():
            try:
                th.request_device_name()  # ★ 调后端发送“请求设备名”指令
                self._devname_req_tries += 1
            except Exception:
                pass
        if self._devname_req_tries >= 8:   # 超过阈值就停（避免无休止发送）
            self._devname_req_timer.stop()

    @QtCore.pyqtSlot(str)
    def _on_device_name_found(self, name: str):
        """收到 'device_name:XXX' 后，更新左上角标签并停止重试。"""
        try:
            self.device_name.setText(f"设备名称：{name.strip() or '—'}")
            self.woo_dbg.set_target_device(name.strip())
        finally:
            self._devname_known = True
            if hasattr(self, "_devname_req_timer"):
                self._devname_req_timer.stop()

    
    @QtCore.pyqtSlot(dict)
    def _on_new_order_found_from_woo(self, payload: dict):
        """
        线程上报“设备匹配 & 今日”的行项目。
        - 若今日已提示过该 key，则忽略
        - 否则入队
        - 如空闲，立即处理队首
        """
        if not payload:
            return
        key = (payload.get("key") or "").strip()
        if not key:
            return
        # 今日已提示过 → 不再弹
        if key in self._seen_set:
            return

        # 队列里也避免重复
        in_queue = any((it.get("key")==key) for it in self._woo_popup_queue)
        if not in_queue:
            self._woo_popup_queue.append(payload)

        if not self._woo_popup_active:
            self._process_next_woo_popup()


    def _process_next_woo_popup(self):
        """
        依次处理队列：
        - 弹确认框『检测到今日下单「XX」，是否更新到配方？』
        - 点“是”：写入配方并刷新卡片；点“否”：跳过
        - 无论结果如何，都把该 key 记为“今日已提示”
        - 然后继续处理下一项
        """
        if not self._woo_popup_queue:
            self._woo_popup_active = False
            return

        self._woo_popup_active = True
        payload = self._woo_popup_queue[0]  # 先看不出队
        key = (payload.get("key") or "").strip()
        drink_name = (payload.get("drink_name") or "").strip()
        formula    = (payload.get("formula") or "").strip()

        # 如果意外发现今天已提示 → 直接丢弃
        if key in self._seen_set or not drink_name:
            self._woo_popup_queue.popleft()
            self._woo_popup_active = False
            return self._process_next_woo_popup()

        # 弹窗询问（你的绿主题对话框）
        text_html = f"检测到今日下单「{drink_name}」<br/>是否更新到配方？"
        yes = GreenConfirmBox.ask(
            self, title="发现新订单", text_html=text_html,
            yes_text="是", no_text="否"
        )

        # 无论结果如何，记为今日已提示（跨重启也不再弹）
        self._mark_seen(key)

        if yes:
            try:
                status, recipe_str = upsert_menu_item(
                    name=drink_name,
                    freeform_formula=formula
                )
                if status in ("created", "replaced"):
                    # 刷新右侧手动出茶卡片
                    self._menu_bridge.on_menu_delta({"name": drink_name})
                    self.woo_dbg.got_text.emit(
                        f"[Woo][apply:{status}] {drink_name} <- '{formula}'"
                    )
            except Exception as e:
                try:
                    _toast(self, f"菜单写入失败: {e}")
                except Exception:
                    print("[Woo][ERROR] 菜单写入异常: ", e)

        # 出队并处理下一个
        self._woo_popup_queue.popleft()
        self._woo_popup_active = False
        self._process_next_woo_popup()


    
    def _load_seen_today(self):
        """加载 ~/.xiliu_seen_today.json；如非今天则重置"""
        try:
            if self._seen_file.exists():
                data = json.loads(self._seen_file.read_text(encoding="utf-8"))
                if data.get("date") == str(date.today()):
                    self._seen_set = set(data.get("keys", []))
                    self._seen_date = data.get("date")
                    return
        except Exception as e:
            print("[Woo][seen] load fail:", e)
        # 不是今天或读取失败 → 重置
        self._seen_set = set()
        self._seen_date = str(date.today())
        self._save_seen_today()

    def _save_seen_today(self):
        """保存到 ~/.xiliu_seen_today.json"""
        try:
            payload = {"date": str(date.today()), "keys": sorted(self._seen_set)}
            self._seen_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print("[Woo][seen] save fail:", e)

    def _mark_seen(self, key: str):
        """标记某个订单项已提示（不论用户点是/否）"""
        if key:
            self._seen_set.add(key)
            self._save_seen_today()

    @QtCore.pyqtSlot(object)
    def on_order_saved(self, *_):
        try:
            print("[SER][done] OrderSaveToDB finished. Re-check DB ...")
            self._log_db_and_serials("after_save")
        except Exception as e:
            print("[SER][done] log err:", e)

        # 再刷新 UI（确保写入完成后才刷）
        try:
            self.refresh_order_content()
        except Exception as e:
            print("[SER] refresh_order_content:", e)
        try:
            self.refresh_setting_local_tee()
        except Exception as e:
            print("[SER] refresh_setting_local_tee:", e)
    
    def _init_daily_serials(self):
        self._log_db_and_serials("init:before")
        """程序启动/跨天时：从 DB 恢复今天的起始编号"""
        # 取茶号（today_id，按“单”）：今天订单数 + 1
        try:
            self.next_take_no = db_util.query_today_order_count() + 1
        except Exception:
            self.next_take_no = 1

        # 杯号（product_id，按“杯”）：今天最大 P 号 + 1（关键！）
        try:
            self.next_product_no = db_util.query_today_max_product_no() + 1
        except Exception:
            # 兜底：退回 今日杯数 + 1（可能偏小，仅异常时使用）
            self.next_product_no = db_util.query_today_tea_quantity() + 1

        self._serials_date = date.today()
        self._log_db_and_serials("init:after")

    def _ensure_daily_serials(self):
        """每次下单前调用：若跨天则重置"""
        if getattr(self, "_serials_date", None) != date.today():
            self._init_daily_serials()

    def _log_db_and_serials(self, prefix=""):
        try:
            from db import db_util
            import os, datetime
            db_abs = os.path.abspath(getattr(db_util, "db_path", ""))
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[SER][{prefix}] now={now} db_path={db_abs}")
            try:
                mx = db_util.query_today_max_product_no()
            except Exception as e:
                print(f"[SER][{prefix}] query_today_max_product_no ERROR:", e)
                mx = None
            try:
                qty = db_util.query_today_tea_quantity()
            except Exception as e:
                print(f"[SER][{prefix}] query_today_tea_quantity ERROR:", e)
                qty = None
            print(f"[SER][{prefix}] DB today maxP={mx} teaQty={qty} nextP={getattr(self,'next_product_no',None)} nextTake={getattr(self,'next_take_no',None)}")
        except Exception as e:
            print(f"[SER][{prefix}] log failed:", e)

        # 根据饮品名拿到 tips
    def _get_tips_for_drink(self, name: str) -> str:
        if not name:
            return ""
        try:
            norm = normalize_drink_name(name)
            return self._tips_by_drink.get(norm.strip(), "")
        except Exception:
            return ""

    # —— 订单 / 奶茶编号调试 —— 
    def _debug_dump_tee_list(self, prefix, tee_list):
        """打印一组奶茶记录的关键字段，用来排查 P 号、取茶号等问题。"""
        try:
            print(f"[OrderDebug] {prefix}: 共 {len(tee_list)} 杯")
            for i, bean in enumerate(tee_list):
                try:
                    bid = getattr(bean, "id", None)
                    today_id = getattr(bean, "today_id", "")
                    prod_id = getattr(bean, "product_id", "")
                    order_id = getattr(bean, "order_id", "")
                    name = getattr(bean, "product_name", "") or getattr(bean, "name", "")
                    state = getattr(bean, "state", "")
                    print(
                        f"[OrderDebug]   #{i}: "
                        f"id={bid} today_id={today_id} product_id={prod_id} "
                        f"order_id={order_id} name={name!r} state={state}"
                    )
                except Exception as e:
                    print(f"[OrderDebug]   #{i}: 打印失败: {e}, bean={bean}")
        except Exception as e:
            print(f"[OrderDebug] {prefix}: 总体打印失败: {e}")

    # 记录当前这一杯需要展示的小贴士
    def _remember_tips_for_current_drink(self):
        """在点击『开始制作』时，记住本次饮品对应的 tips。"""
        bean = getattr(self, "select_order_tee_bean", None)
        name = getattr(bean, "product_name", "") if bean else ""
        norm_name = normalize_drink_name(name)
        tips_map = getattr(self, "_tips_by_drink", {})

        print("[TipsDebug] _remember_tips_for_current_drink 被调用")
        print("           bean =", bean)
        print("           name =", repr(name))
        print("           norm_name =", repr(norm_name))
        print("           tips_map size =", len(tips_map) if isinstance(tips_map, dict) else type(tips_map))

        tips = ""
        if norm_name and isinstance(tips_map, dict):
            tips = (tips_map.get(norm_name, "") or "").strip()

        # 记在实例上，方便制作完成时使用
        self._current_make_drink_name = norm_name or name
        self._current_make_tips = tips

        print(f"[TipsDebug] 本次制作饮品 = {self._current_make_drink_name!r}, tips = {tips!r}")

    @pyqtSlot(str)
    def on_ice_locking(self, kind):
        """收到 locking / crushed_ice_locking / ice_out_locking：正在自动摆脱中"""
        # 如果之前有“正在自动摆脱中”的弹窗，先关掉
        try:
            if getattr(self, "_ice_locking_dlg", None) is not None:
                self._ice_locking_dlg.close()
        except Exception:
            pass

        # 根据类型选择提示内容
        if kind == "crushed":
            text = "碎冰模块被冰卡住，正在自动摆脱中......"
        elif kind == "ice_out":
            text = "出冰模块被冰卡住，正在自动摆脱中......"
        else:
            # 兼容老固件/未知类型：按两个模块都堵处理
            text = "碎冰和出冰模块被冰卡住，正在自动摆脱中......"

        # 新建一个弹窗，并保存引用，方便后面 unlock_finish/locked 时关闭
        dlg = GreenMessageBox(
            "提示",
            text,
            self,
            ok_text="知道了"
        )
        self._ice_locking_dlg = dlg
        dlg.finished.connect(self._clear_ice_locking_dlg)
        dlg.show()

    def _clear_ice_locking_dlg(self, *args):
        """弹窗被用户点掉后，清空引用"""
        self._ice_locking_dlg = None

    @pyqtSlot()
    def on_ice_locked(self):
        """收到 locked：自动摆脱失败"""
        # 如果“正在自动摆脱中”的弹窗还在，先关掉
        try:
            if getattr(self, "_ice_locking_dlg", None) is not None:
                self._ice_locking_dlg.close()
        except Exception:
            pass
        self._ice_locking_dlg = None

        GreenMessageBox.warning(
            self,
            "提示",
            "自动摆脱失败，请手动修复！！！",
            ok_text="知道了"
        )

    @pyqtSlot()
    def on_ice_unlock_finished(self):
        """收到 unlock_finish：自动摆脱完成"""
        # 1）如果“正在自动摆脱中”的弹窗还在，先关掉
        try:
            if getattr(self, "_ice_locking_dlg", None) is not None:
                self._ice_locking_dlg.close()
        except Exception:
            pass
        self._ice_locking_dlg = None

        # 2）弹出“自动摆脱完成”的提示
        GreenMessageBox.warning(
            self,
            "提示",
            "自动摆脱完成！！！",
            ok_text="知道了"
        )

    def _send_clean_serial(self, is_on: bool):
        """
        旧清洗按键对应的串口命令（已废弃）：
        - is_on = True  -> clean1_on
        - is_on = False -> clean1_off
        """
        th = getattr(self, "conduit_serial_thread", None)
        if not (th and th.isRunning()):
            return
        if is_on:
            th.send_data("clean1_on")
        else:
            th.send_data("clean1_off")




if __name__ == '__main__':
    app = QApplication(sys.argv)
    myShow = Main1080Window(app)
    myShow.show()
    sys.exit(app.exec_())
