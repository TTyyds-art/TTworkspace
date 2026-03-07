from datetime import datetime, timedelta
import sys
import os
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QApplication

from bean.new_conduit_bean import NewConduitBean
from control.conduit_new_dialog_mata import NewConduitDialog
from ui_1080_py.Ui_conduit_card_ui import Ui_Form
from tool_utils.condiut_enum import ConduitEnum


# ===================== 冰/碎冰专用：自动出冰开关（替代“屏蔽”） =====================
# 约定：通道 1# / 2#（物理冰、碎冰）的“屏蔽开关”不再参与“通道屏蔽”。
# - 开关 ON(绿色)  : 自动出冰（按配方输出液体+冰）
# - 开关 OFF(灰色) : 只输出配方液体，冰由人工添加
ICE_CONDUIT_IDXS = {1, 2}


def _parse_channel_index(conduit_value):
    """conduit 字段形如 '1#'、'02#'、'12#'；提取数字部分 1..26"""
    if conduit_value is None:
        return None
    import re
    m = re.search(r'\d+', str(conduit_value))
    if not m:
        return None
    idx = int(m.group(0))
    return idx if 1 <= idx <= 26 else None


class ConduitCardWidget(QWidget, Ui_Form):
    changed_conduit_card = pyqtSignal(bool, NewConduitBean)

    def __init__(self, conduit_bean, is_debug, parent=None):
        super(ConduitCardWidget, self).__init__(parent)
        self.conduit_dialog_ui = None
        self.setupUi(self)
        self.is_select = False
        self.is_debug = is_debug
        self.widget.installEventFilter(self)
        self.conduit_card_mark_l.setHidden(True)
        self.init_font()
        self.conduit_bean = conduit_bean
        h_m_list = conduit_bean.effective_time.split(':')
        e_hour = int(h_m_list[0])
        e_minute = int(h_m_list[1])
        self.end_time = datetime.strptime(conduit_bean.begin_time, "%Y-%m-%d %H:%M:%S") + timedelta(hours=e_hour,
                                                                                                         minutes=e_minute)
        self.set_no_style()

    def init_ui(self):
        self.set_card_id(self.conduit_bean.conduit)
        self.conduit_card_name_l.setText(self.conduit_bean.name)
        self.conduit_card_g_l.setText(f'{str(self.conduit_bean.margin)}g')
        h_m_list = self.conduit_bean.effective_time.split(':')
        e_hour = int(h_m_list[0])
        e_minute = int(h_m_list[1])
        self.end_time = datetime.strptime(self.conduit_bean.begin_time, "%Y-%m-%d %H:%M:%S") + timedelta(hours=e_hour,
                                                                                                    minutes=e_minute)
        str_time = self.end_time.strftime('%H:%M')
        if self.is_debug:
            self.l_date.setText('00:00')
            #self.conduit_card_g_l.setText('-1000g')
        else:
            self.l_date.setText(str_time)
        if self.is_select:
            self.set_changed_style()
        else:
            self.set_no_style()

        # 末尾统一处理：
        # - 非冰/碎冰通道：shield=='2' 视为【屏蔽】=> 卡片置灰 + 右上角显示“屏”
        # - 冰/碎冰(1#/2#)：shield 开关改为【自动出冰】=>
        #     ON(绿色, shield=='2')  卡片正常（白底），不显示“屏”
        #     OFF(灰色,  shield=='1') 卡片置灰，不显示“屏”
        self._apply_shield_or_ice_visual()


    def _set_mark(self, visible: bool, text: str = '屏'):
        """右上角的小圆标识。

        说明：不同 UI 版本里该控件可能不存在；因此用 hasattr 做兼容。
        """
        try:
            if hasattr(self, 'conduit_card_mark_l') and self.conduit_card_mark_l is not None:
                self.conduit_card_mark_l.setText(text)
                self.conduit_card_mark_l.setHidden(not visible)
        except Exception:
            pass


    def _apply_grey_card_base(self):
        """将卡片背景改为灰色（用于：被屏蔽通道 / 冰手动加冰状态）。"""
        try:
            self.widget.setStyleSheet('''
                QWidget#widget{
                    background-color:rgb(230, 230, 230);
                    border-radius:30px;
                }
            ''')
            # 主标题灰
            self.conduit_card_name_l.setStyleSheet('color:rgb(128, 128, 128);')
            # 剩余量标题/数值适度变灰（不影响红/黄告警色的显示逻辑时保持原逻辑）
            # 这里不强行覆盖 conduit_card_g_l 的告警色，避免影响补料告警视觉。
        except Exception:
            pass


    def _apply_shield_or_ice_visual(self):
        """统一处理：
        - 通道 1#/2#：开关表示【自动出冰】，不显示“屏”，OFF 时卡片置灰。
        - 其它通道：开关表示【屏蔽通道】，shield=='2' 时卡片置灰并显示“屏”。
        """
        idx = _parse_channel_index(getattr(self.conduit_bean, 'conduit', None))
        shield_val = str(getattr(self.conduit_bean, 'shield', '1') or '1')

        # 冰 / 碎冰：永远不显示“屏”
        if idx in ICE_CONDUIT_IDXS:
            self._set_mark(False)
            auto_ice_on = (shield_val == '2')  # 绿色=ON
            if not auto_ice_on:
                # OFF：手动加冰，卡片置灰
                self._apply_grey_card_base()
            return

        # 其它通道：shield=='2' 视为屏蔽
        is_shielded = (shield_val == '2')
        if is_shielded:
            self._apply_grey_card_base()
            self._set_mark(True, '屏')
        else:
            self._set_mark(False)


    def set_card_id(self, card_id):
        self.conduit_card_id_l.setText(card_id)

    def update_conduit_bean(self, conduits_list):
        for conduit_bean in conduits_list:
            if self.conduit_bean.conduit == conduit_bean.conduit:
                self.conduit_bean = conduit_bean
                break
        self.init_ui()

    def update_info(self, weights):
        try:
            num = 0
            if self.conduit_bean.get_conduit == 'A':
                num = ConduitEnum.A
            elif self.conduit_bean.get_conduit == 'B':
                num = ConduitEnum.B
            elif self.conduit_bean.get_conduit == 'C':
                num = ConduitEnum.C
            elif self.conduit_bean.get_conduit == 'D':
                num = ConduitEnum.D
            elif self.conduit_bean.get_conduit == 'E':
                num = ConduitEnum.E
            elif self.conduit_bean.get_conduit == 'F':
                num = ConduitEnum.F
            elif self.conduit_bean.get_conduit == 'G':
                num = ConduitEnum.G
            elif self.conduit_bean.get_conduit == 'H':
                num = ConduitEnum.H
            elif self.conduit_bean.get_conduit == 'I':
                num = ConduitEnum.I
            elif self.conduit_bean.get_conduit == 'J':
                num = ConduitEnum.J
            elif self.conduit_bean.get_conduit == 'K':
                num = ConduitEnum.K
            elif self.conduit_bean.get_conduit == 'L':
                num = ConduitEnum.L
            elif self.conduit_bean.get_conduit == 'M':
                num = ConduitEnum.M
            elif self.conduit_bean.get_conduit == 'N':
                num = ConduitEnum.N
            elif self.conduit_bean.get_conduit == 'O':
                num = ConduitEnum.O
            elif self.conduit_bean.get_conduit == 'P':
                num = ConduitEnum.P
            elif self.conduit_bean.get_conduit == 'Q':
                num = ConduitEnum.Q
            rounded_num = round(weights[num], 2)
            self.conduit_bean.set_margin(str(rounded_num))
            self.conduit_card_g_l.setText(f'{str(self.conduit_bean.get_margin())}g')
        except Exception as e:
            pass
            # print(f'检查一下是否 数组超界：{e}')

    def set_changed_style(self):
        # 选中样式（不在这里决定“屏”标识，统一在 _apply_shield_or_ice_visual() 处理）
        self.widget.setStyleSheet('''
            QWidget#widget{
                background-color:rgb(21, 136, 74);
                border-radius:30px;
            }
        ''')
        self.conduit_card_id_l.setStyleSheet('''
            background-color:rgb(255, 255, 255);
            color:rgb(21, 136, 74);
            border-radius:25px;
        ''')
        self.conduit_card_name_l.setStyleSheet('''
            color:rgb(255, 255, 255);
        ''')
        if int(self.conduit_bean.yellow_warning_value) <= int(self.conduit_bean.margin):
            self.conduit_card_g_l.setStyleSheet('color:rgb(255, 255, 255);')
            self.conduit_card_title_l.setStyleSheet('color:rgb(255, 255, 255);')
        elif int(self.conduit_bean.red_warning_value) < int(self.conduit_bean.margin) <= int(
                self.conduit_bean.yellow_warning_value):
            self.conduit_card_g_l.setStyleSheet('color:rgba(255, 154, 24, 1);')
            self.conduit_card_title_l.setStyleSheet('color:rgba(255, 154, 24, 1);')
        elif int(self.conduit_bean.margin) <= int(self.conduit_bean.red_warning_value):
            self.conduit_card_g_l.setStyleSheet('color:rgba(251, 13, 92, 1);')
            self.conduit_card_title_l.setStyleSheet('color:rgba(251, 13, 92, 1);')

        # 选中/未选中都需要叠加“屏蔽/自动出冰”视觉
        self._apply_shield_or_ice_visual()

        # 选中样式设置完成后，再叠加“屏蔽/自动出冰”视觉规则
        self._apply_shield_or_ice_visual()
        self.label.setStyleSheet("""
            border-image: url(:/icon/icon_conduit_card_clock_green.png);
        """)

        current_time = datetime.now()
        if self.is_debug:
            # 设置正常背景
            self.widget_7.setStyleSheet("""
                                        QWidget#widget_7{
                                            background-color:white;
                                            border-radius:23px;
                                        }
                                    """)
            self.l_date.setStyleSheet('color:rgb(44, 159, 97);')
            self.label_2.setStyleSheet('color:rgb(44, 159, 97);')
        else:
            if current_time > self.end_time:
                # 设置超时背景
                self.widget_7.setStyleSheet("""
                                        QWidget#widget_7{
                                            background-color:rgba(255, 154, 24, 1);
                                            border-radius:23px;
                                        }
                                    """)
                self.l_date.setStyleSheet('color:white;')
                self.label_2.setStyleSheet('color:white;')
            else:
                # 设置正常背景
                self.widget_7.setStyleSheet("""
                            QWidget#widget_7{
                                background-color:white;
                                border-radius:23px;
                            }
                        """)
                self.l_date.setStyleSheet('color:rgb(44, 159, 97);')
                self.label_2.setStyleSheet('color:rgb(44, 159, 97);')

    def set_no_style(self):
        # 未选中样式（不在这里决定“屏”标识，统一在 _apply_shield_or_ice_visual() 处理）
        self.widget.setStyleSheet('''
            QWidget#widget{
                background-color:rgb(255, 255, 255);
                border-radius:30px;
            }
        ''')
        self.conduit_card_id_l.setStyleSheet('''
            background-color:rgb(21, 136, 74);
            color:rgb(255, 255, 255);
            border-radius:25px;
        ''')
        self.conduit_card_name_l.setStyleSheet('''
            color:rgb(44, 159, 97);
        ''')
        if int(self.conduit_bean.yellow_warning_value) <= int(self.conduit_bean.margin):
            self.conduit_card_g_l.setStyleSheet('color:rgb(44, 159, 97);')
            self.conduit_card_title_l.setStyleSheet('color:rgb(44, 159, 97);')
        elif int(self.conduit_bean.red_warning_value) < int(self.conduit_bean.margin) <= int(
                self.conduit_bean.yellow_warning_value):
            self.conduit_card_g_l.setStyleSheet('color:rgba(255, 154, 24, 1);')
            self.conduit_card_title_l.setStyleSheet('color:rgba(255, 154, 24, 1);')
        elif int(self.conduit_bean.margin) <= int(self.conduit_bean.red_warning_value):
            self.conduit_card_g_l.setStyleSheet('color:rgba(251, 13, 92, 1);')
            self.conduit_card_title_l.setStyleSheet('color:rgba(251, 13, 92, 1);')

        # 选中/未选中都需要叠加“屏蔽/自动出冰”视觉
        self._apply_shield_or_ice_visual()

        # 选中/未选中都需要叠加“屏蔽/自动出冰”视觉
        self._apply_shield_or_ice_visual()

        # 未选中样式设置完成后，再叠加“屏蔽/自动出冰”视觉规则
        self._apply_shield_or_ice_visual()
        self.label.setStyleSheet("""
            border-image: url(:/icon/icon_conduit_card_clock_white.png);
        """)

        current_time = datetime.now()
        if self.is_debug:
            # 设置正常背景
            self.widget_7.setStyleSheet("""
                                                QWidget#widget_7{
                                                    background-color:rgb(44, 159, 97);
                                                    border-radius:23px;
                                                }
                                            """)
            self.l_date.setStyleSheet('color:white;')
            self.label_2.setStyleSheet('color:white;')
        else:
            if current_time > self.end_time:
                # 设置超时背景
                self.widget_7.setStyleSheet("""
                                                QWidget#widget_7{
                                                    background-color:rgba(255, 154, 24, 1);
                                                    border-radius:23px;
                                                }
                                            """)
                self.l_date.setStyleSheet('color:white;')
                self.label_2.setStyleSheet('color:white;')
            else:
                # 设置正常背景
                self.widget_7.setStyleSheet("""
                                    QWidget#widget_7{
                                        background-color:rgb(44, 159, 97);
                                        border-radius:23px;
                                    }
                                """)
                self.l_date.setStyleSheet('color:white;')
                self.label_2.setStyleSheet('color:white;')
    def get_font_path(self, font):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, font)
        return font

    def init_font(self):
        AlibabaPuHuiTi_3_65_Medium_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf')
        )
        if AlibabaPuHuiTi_3_65_Medium_id != -1:
            AlibabaPuHuiTi_3_65_Medium_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_65_Medium_id)[0]
            AlibabaPuHuiTi_3_65_Medium_font_family_22 = QFont(AlibabaPuHuiTi_3_65_Medium_font_family, 22)
            self.label_2.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_22)
            self.l_date.setFont(AlibabaPuHuiTi_3_65_Medium_font_family_22)

        AlibabaPuHuiTi_3_105_Heavy_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-105-Heavy/AlibabaPuHuiTi-3-105-Heavy.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-105-Heavy/AlibabaPuHuiTi-3-105-Heavy.ttf')
        )
        if AlibabaPuHuiTi_3_105_Heavy_font_id != -1:
            AlibabaPuHuiTi_3_105_Heavy_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_105_Heavy_font_id)[0]
            AlibabaPuHuiTi_3_85_Bold_custom_font_24 = QFont(AlibabaPuHuiTi_3_105_Heavy_font_family, 24, QFont.Bold)
            self.conduit_card_id_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)

        AlibabaPuHuiTi_3_85_Bold_font_id = QFontDatabase.addApplicationFont(
            # 'fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf'
            self.get_font_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf')
        )
        if AlibabaPuHuiTi_3_85_Bold_font_id != -1:
            AlibabaPuHuiTi_3_85_Bold_font_family = QFontDatabase.applicationFontFamilies(
                AlibabaPuHuiTi_3_85_Bold_font_id)[0]
            AlibabaPuHuiTi_3_85_Bold_custom_font_55 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 55, QFont.Bold)
            self.conduit_card_name_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_55)
            AlibabaPuHuiTi_3_85_Bold_custom_font_30 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 22)
            self.conduit_card_title_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_30)
            self.conduit_card_g_l.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_30)

    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if obj == self.widget:
                if self.is_select:
                    self.is_select = False
                    self.set_no_style()
                    self.changed_conduit_card.emit(False, self.conduit_bean)
                else:
                    self.is_select = True
                    self.set_changed_style()
                    self.changed_conduit_card.emit(True, self.conduit_bean)
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.conduit_dialog_ui = NewConduitDialog(self.conduit_bean)
            self.conduit_dialog_ui.result_new_conduit_bean.connect(self.result_callBack)
            self.conduit_dialog_ui.show()

    def result_callBack(self, conduit_bean):
        self.conduit_bean = conduit_bean
        self.conduit_card_name_l.setText(conduit_bean.name)
        self.conduit_card_g_l.setText(f'{str(conduit_bean.margin)}g')
        h_m_list = conduit_bean.effective_time.split(':')
        e_hour = int(h_m_list[0])
        e_minute = int(h_m_list[1])
        self.end_time = datetime.strptime(conduit_bean.begin_time, "%Y-%m-%d %H:%M:%S") + timedelta(hours=e_hour,
                                                                                               minutes=e_minute)
        str_time = self.end_time.strftime('%H:%M')
        if self.is_debug:
            #self.conduit_card_g_l.setText('-1000g')
            self.l_date.setText('00:00')
        else:
            self.l_date.setText(str_time)
        if self.is_select:
            self.set_changed_style()
        else:
            self.set_no_style()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myShow = ConduitCardWidget('2')
    myShow.show()
    sys.exit(app.exec_())
