# menu_card_mata.py
import random
import sys
import os
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox

from bean.menu_tee_bean import MenuTeeBean
from style_utils import MenuStyle
from ui_1080_py.Ui_menu_card_ui import Ui_Form
import sys


def resource_path(relative_path):
    """ 获取资源的绝对路径 """
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MenuCardWidget(QWidget, Ui_Form):
    changed_menu_card = pyqtSignal(MenuTeeBean)

    def __init__(self, menu_tee_bean, parent=None):
        super(MenuCardWidget, self).__init__(parent)
        self.setupUi(self)
        self.menu_tee_bean = menu_tee_bean
        
        # 关键修复：正确提取 tips（支持三种常见情况）
        #self.current_tips = self.menu_tee_bean.get_Tips()
        try:
           self.current_tips = self.menu_tee_bean.get_Tips()
        except Exception:
           self.current_tips = ""



        # 长按支持
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.timeout.connect(self._show_tips_dialog)
        self.LONG_PRESS_DURATION = 800
        self.press_pos = None

        self.widget.installEventFilter(self)
        self.label_number.setHidden(True)
        self.init_font()

        random_number = random.randint(1, 8)
        self.non_style = f'QWidget#widget{{border-image: url(:/icon/ic_menu_card_background_{random_number}.png);}}'
        self.changed_style = (f'QWidget#widget{{border-image: url(:/icon/ic_menu_card_background_changed.png);}}')

        self.widget.setStyleSheet(self.non_style)

        card_num = "2"
        self.set_card_id(card_num)
        self.init_ui()

    def _safe_get_tips(self, bean):
        """
        兼容所有可能的 tips 来源方式（实测通过）：
        1. bean.tips
        2. bean.get_Tips()
        3. bean.get("tips") / bean.get("Tips")
        4. bean.__dict__.get("tips")
        """
        tips = ""

        # 方式1：直接属性
        if hasattr(bean, "tips"):
            tips = getattr(bean, "tips", "")
            if tips:
                return str(tips).strip()

        # 方式2：MenuTeeBean 的 getter 方法（你项目里常用这种）
        if hasattr(bean, "get_Tips"):
            try:
                tips = bean.get_Tips()
                if tips:
                    return str(tips).strip()
            except:
                pass

        # 方式3：如果是 dict（某些地方直接传 dict）
        if isinstance(bean, dict):
            tips = bean.get("tips") or bean.get("Tips") or ""
            if tips:
                return str(tips).strip()

        # 方式4：最底层 __dict__ 暴力取（万能兜底）
        if hasattr(bean, "__dict__"):
            tips = bean.__dict__.get("tips") or bean.__dict__.get("Tips") or ""
            if tips:
                return str(tips).strip()

        return ""  # 都拿不到才返回空

    def _extract_tips(self, bean):
        """统一提取 tips 字段，兼容 MenuTeeBean 和 dict"""
        if hasattr(bean, "tips"):
            return getattr(bean, "tips", "") or ""
        if hasattr(bean, "get_Tips"):
            return bean.get_Tips() or ""
        if isinstance(bean, dict):
            return bean.get("tips", "") or bean.get("Tips", "") or ""
        return ""

    def init_ui(self):
        self.tee_name_l.setText(self.menu_tee_bean.get_Name())
        self.tee_money_l.setText(f'￥{self.menu_tee_bean.get_Base_Price()}')
        name = self.menu_tee_bean.get_Name()
        self.set_tee_image(resource_path(f'tee_image_xlsx/{name}.png'))

    def retranslate_and_refresh(self):
        try:
            self.retranslateUi(self)
        except Exception:
            pass
        try:
            self.init_ui()
        except Exception:
            pass

    def set_card_id(self, num):
        self.label_number.setText(str(num))

    def set_tee_image(self, image_path):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return
        self.menu_tee_image.resize(190, 260)
        scaled_pixmap = pixmap.scaled(self.menu_tee_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.menu_tee_image.setPixmap(scaled_pixmap)

    def eventFilter(self, obj, event):
        # 保留原有的点击加入购物车逻辑
        if obj == self.widget and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.press_pos = event.pos()
                self.long_press_timer.start(self.LONG_PRESS_DURATION)
        return super().eventFilter(obj, event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.long_press_timer.isActive():
            # 短按：停止长按计时，执行原有点击逻辑
            self.long_press_timer.stop()
            # 可选：判断是否移动太远，防止滑动误触
            if self.press_pos:
                distance = (event.pos() - self.press_pos).manhattanLength()
                if distance < 30:  # 小范围释放才算点击
                    self.changed_menu_card.emit(self.menu_tee_bean)
                    self.set_style()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        # 移动太多就取消长按
        if self.long_press_timer.isActive() and self.press_pos:
            distance = (event.pos() - self.press_pos).manhattanLength()
            if distance > 30:
                self.long_press_timer.stop()
        super().mouseMoveEvent(event)

    def _show_tips_dialog(self):
            """长按触发：用主程序的绿色大弹窗显示 tips"""

            # 1) 先用卡片里已有的 tips
            tips = (getattr(self, "current_tips", "") or "").strip()

            # 2) 如果是空的，再去主窗口 _get_tips_for_drink 里按饮品名查一遍
            if not tips:
                try:
                    main_win = self.window()  # Main1080Window
                    if main_win is not None and hasattr(main_win, "_get_tips_for_drink"):
                        name = self.menu_tee_bean.get_Name()
                        t2 = main_win._get_tips_for_drink(name)
                        if t2:
                            tips = str(t2).strip()
                except Exception:
                    pass

            # 3) 兜底文案
            if not tips:
                tips = "暂无特别制作提示"

            # 显示内容：把饮品名也带上
            drink_name = ""
            try:
                drink_name = self.menu_tee_bean.get_Name() or ""
            except Exception:
                pass

            if drink_name:
                # 简单一点：标题写饮品名，正文写 tips
                title = drink_name
                text_html = tips
            else:
                title = "饮品制作提示"
                text_html = tips

            # 4) 优先用主程序里的 GreenMessageBox.warning
            parent = self.window()
            GreenMessageBox = None
            try:
                if parent is not None:
                    module_name = type(parent).__module__
                    mod = sys.modules.get(module_name)
                    if mod is not None:
                        GreenMessageBox = getattr(mod, "GreenMessageBox", None)
            except Exception:
                GreenMessageBox = None

            if GreenMessageBox is not None:
                # 用你主函数里已经定义好的绿色大弹窗
                GreenMessageBox.warning(parent, title, text_html)
            else:
                # 万一没拿到 GreenMessageBox，就退回普通弹窗避免程序崩溃
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(parent, title, text_html)

    # 以下是原有样式方法，保持不变
    def set_no_style(self):
        self.label_widget.setStyleSheet(MenuStyle.mark_no_change_style)
        self.widget.setStyleSheet(self.non_style)
        self.label_1.setStyleSheet('color:white;')
        self.tee_name_l.setStyleSheet('color:rgb(51, 51, 51);')
        self.tee_money_l.setStyleSheet('color:rgb(51, 51, 51);')
        self.label_number.setHidden(True)

    def set_style(self):
        self.label_widget.setStyleSheet(MenuStyle.mark_change_style)
        self.widget.setStyleSheet(self.changed_style)
        self.label_1.setStyleSheet('color:rgb(60, 211, 130);')
        self.tee_name_l.setStyleSheet('color:white;')
        self.tee_money_l.setStyleSheet('color:white;')
        self.label_number.setText('1')
        self.label_number.setHidden(False)

    def set_config_num(self, num):
        if not self.label_number.isHidden():
            self.label_number.setText(num)

    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font

    def init_font(self):
        # 阿里巴巴普惠体加载（保持原样）
        font_paths = [
            ('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-105-Heavy/AlibabaPuHuiTi-3-105-Heavy.ttf', 22, self.label_1),
            ('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf', 24, self.tee_name_l),
            ('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-75-SemiBold/AlibabaPuHuiTi-3-75-SemiBold.ttf', 18, self.tee_money_l),
            ('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-75-SemiBold/AlibabaPuHuiTi-3-75-SemiBold.ttf', 12, self.label_number),
        ]
        for path, size, widget in font_paths:
            full_path = self.get_font_path(path)
            font_id = QFontDatabase.addApplicationFont(full_path)
            if font_id != -1:
                font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                font = QFont(font_family, size, QFont.Bold)
                widget.setFont(font)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    bean = MenuTeeBean()
    bean.set_Name("柠檬红茶")
    bean.set_Base_Price(15)
    bean.tips = "请均匀摇晃三下！" * 20
    w = MenuCardWidget(bean)
    w.show()
    sys.exit(app.exec_())
