import os
import sys
import json,re
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QMessageBox
import calendar
from bean.new_conduit_bean import NewConduitBean
from control.conduit_card_keyboard_mata import ManagerKeyboardMata
from db import db_util
from threads.keyboard_thread import KeyboardThread
from ui_1080_py.Ui_conduit_new_dialog_ui import Ui_Form
from maketee_control import GreenMessageBox 




class NewConduitDialog(QWidget, Ui_Form):
    result_new_conduit_bean = pyqtSignal(NewConduitBean)
    red_and_yellow = pyqtSignal(int, int)

    def __init__(self, conduit_bean, parent=None):
        super().__init__(parent)
        self.keyboard_thread = None
        self.conduit_bean = conduit_bean
        self.content_text = ''
        self.is_shield = True
        self.keyboard_ui = None
        self.time_label_style = 'background-color:rgba(176, 233, 202, 1);'
        self.time_label_select_style = 'background-color:rgb(255, 207, 207);'
        self.setupUi(self)
        self.widget.installEventFilter(self)
        self.on_off_widget.installEventFilter(self)
        self.widget_10.installEventFilter(self)
        self.widget_11.installEventFilter(self)
        self.move(0,0)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_font()
        self.init_ui()

    def init_ui(self):
        
        self.edit_type.setReadOnly(False)
        self.edit_name.setReadOnly(False)

        self.i1.setText(self.conduit_bean.conduit)
        self.i2.setText(f'{self.conduit_bean.margin}g')
        self.edit_type.setText(self.conduit_bean.conduit_type)
        self.edit_name.setText(self.conduit_bean.name)
        
        # 【新增】通道 1#(冰) / 2#(碎冰) 不再使用‘屏蔽’语义，而是作为‘出冰’开关
        # ON(绿色)=按配方出冰；OFF(灰色)=不出冰(手动加冰)
        # 说明：不同 UI 版本中“屏蔽:”对应的 QLabel 对象名可能不同（之前用 l6 会误改到其它字段）。
        # 因此这里用“按文字匹配”的方式，精准把“屏蔽:”替换为“自动出冰:”。
        try:
            m = re.search(r'\d+', str(self.conduit_bean.conduit))
            idx_ = int(m.group(0)) if m else None
            if idx_ in (1, 2):
                for attr in dir(self):
                    try:
                        w = getattr(self, attr)
                        if isinstance(w, QLabel):
                            # 不同 UI 版本里可能是："屏蔽:" / "屏蔽：" / "屏蔽" / 甚至带空格。
                            # 这里用“包含匹配”避免漏改，同时仅匹配“屏蔽”两字，不会误改“有效期/开始时间”等字段。
                            t = (w.text() or '').strip()
                            if '屏蔽' in t:
                                w.setText('出冰:')
                    except Exception:
                        continue
        except Exception:
            pass
        
        if self.conduit_bean.shield == '1':
            self.is_shield = True
        elif self.conduit_bean.shield == '2':
            self.is_shield = False
        if self.is_shield:
            self.on_widget.setVisible(False)
            self.off_widget.setVisible(True)
        else:
            self.on_widget.setVisible(True)
            self.off_widget.setVisible(False)

        # 有效时间
        h_m_list = self.conduit_bean.effective_time.split(':')
        e_hour = h_m_list[0]
        e_minute = h_m_list[1]
        self.h.setText(e_hour)
        self.m.setText(e_minute)

        # 开始时间
        date_begin = datetime.strptime(self.conduit_bean.begin_time, "%Y-%m-%d %H:%M:%S")
        # print(f"date_begin:{date_begin}")
        self.b_d.setText(date_begin.strftime('%d'))
        self.b_h.setText(date_begin.strftime('%H'))
        self.b_m.setText(date_begin.strftime('%M'))
        # print(f"d:{date_begin.strftime('%d')}")
        # print(f"h:{date_begin.strftime('%H')}")
        # print(f"m:{date_begin.strftime('%M')}")

        self.l_red.setText(self.conduit_bean.red_warning_value)
        self.l_yellow.setText(self.conduit_bean.yellow_warning_value)
        self._build_assoc_row()
        self._refresh_assoc_list()
        self.edit_name.textChanged.connect(lambda _=None: self._refresh_assoc_list())

        

        # === 名称唯一性校验（未屏蔽通道唯一；屏蔽通道不参与唯一性） ===
    def _norm_name(self, s: str) -> str:
        return str(s or '').strip()

    def _is_shielded_value(self, v) -> bool:
        # 你们工程：'2' 表示【屏蔽】；'1' 表示【未屏蔽】
        return str(v).strip() == '2'

    def _ui_shield_value(self) -> str:
        # self.is_shield == True -> 未屏蔽 -> 保存为 '1'
        # self.is_shield == False -> 屏蔽   -> 保存为 '2'
        return '1' if self.is_shield else '2'

    def _set_ui_shield_by_value(self, v: str):
        # v=='2' -> 屏蔽 -> on_widget 显示；v=='1' -> 未屏蔽 -> off_widget 显示
        if self._is_shielded_value(v):
            self.is_shield = False
            self.on_widget.setVisible(True)
            self.off_widget.setVisible(False)
        else:
            self.is_shield = True
            self.on_widget.setVisible(False)
            self.off_widget.setVisible(True)

    def _has_name_conflict_with_unshielded(self, new_name: str) -> bool:
        # 仅检查【未屏蔽】通道（shield != '2'）是否已占用该名称；排除自己
        name = self._norm_name(new_name)
        if not name:
            return False
        try:
            rows = db_util.query_all_conduit_info() or []
        except Exception:
            rows = []
        self_id = str(getattr(self.conduit_bean, 'id', '') or '')
        for r in rows:
            rid = str(r.get('id') or r.get('_id') or '')
            if self_id and rid == self_id:
                continue
            rname = self._norm_name(r.get('name'))
            rshield = r.get('shield')
            if (not self._is_shielded_value(rshield)) and rname == name:
                return True
        return False

    @pyqtSlot()
    def on_conduit_save_btn_clicked(self):
        # 通过id保存变更的数据
        _id = self.conduit_bean.id
        conduit_type = self.edit_type.text()
        name = self.edit_name.text()
        shield = ''
        if self.is_shield:
            shield = '1'
        else:
            shield = '2'
        # 【新增】名称唯一性规则：
        # 1) 未屏蔽通道（shield=='1'）之间，名称必须唯一；
        # 2) 屏蔽通道（shield=='2'）不参与唯一性约束，可与其它通道重名；
        # 3) 从【屏蔽->未屏蔽】解除屏蔽时，如发生重名冲突：提示并保持屏蔽。
        new_name = self._norm_name(name)
        old_shield = getattr(self.conduit_bean, 'shield', None)
        # 当前保存后的状态是否为未屏蔽
        will_be_unshielded = (not self._is_shielded_value(shield))
        conflict = self._has_name_conflict_with_unshielded(new_name)

        # A) 改名/保存为未屏蔽时：若与其它未屏蔽通道重名 -> 修改失败
        if will_be_unshielded and conflict:
            # 如果是【解除屏蔽】导致的冲突，走更明确的提示（见 B）
            if self._is_shielded_value(old_shield) and (not self._is_shielded_value(shield)):
                GreenMessageBox.warning(
                    self,
                    "提示",
                    f"已有{new_name}通道，请修改名字",
                    ok_text="知道了"
                )

                # 保持屏蔽（把 UI 开关拨回屏蔽态）
                self._set_ui_shield_by_value('2')
                return
            GreenMessageBox.warning(
                self,
                "修改失败",
                f"修改失败，已有{new_name}通道",
                ok_text="知道了"
            )

            return

        effective_time = f'{self.h.text()[-2:]}:{self.m.text()[-2:]}'

        date_time = datetime.strptime(self.conduit_bean.begin_time, "%Y-%m-%d %H:%M:%S")
        year = date_time.strftime('%Y')
        month = date_time.strftime('%m')
        s = date_time.strftime('%S')
        if int(self.b_d.text()[-2:]) == 0:
            return
        begin_time = f'{year}-{month}-{self.b_d.text()[-2:]} {self.b_h.text()[-2:]}:{self.b_m.text()[-2:]}:{s}'
        red_warning_value = self.l_red.text()
        yellow_warning_value = self.l_yellow.text()

        db_util.update_conduit_info(
            _id, conduit_type, name, shield, effective_time, begin_time, red_warning_value, yellow_warning_value
        )

        self.conduit_bean.conduit_type = conduit_type
        self.conduit_bean.name = name
        self.conduit_bean.shield = shield
        self.conduit_bean.effective_time = effective_time
        self.conduit_bean.begin_time = begin_time
        self.conduit_bean.red_warning_value = red_warning_value
        self.conduit_bean.yellow_warning_value = yellow_warning_value
        self.result_new_conduit_bean.emit(self.conduit_bean)
        if self.keyboard_ui is not None:
            self.keyboard_ui.close()
        # self.keyboard_ui.close()
        self.close()


    @pyqtSlot()
    def on_btn_type_clicked(self):
        self.edit_type.setReadOnly(False)
        self.keyboard_thread = KeyboardThread()
        self.keyboard_thread.start()
        self.edit_type.setFocus()

    @pyqtSlot()
    def on_btn_name_clicked(self):
        self.edit_name.setReadOnly(False)
        self.keyboard_thread = KeyboardThread()
        self.keyboard_thread.start()
        self.edit_name.setFocus()

    @pyqtSlot()
    def on_btn_effective_time_clicked(self):
        self.h.setStyleSheet(self.time_label_select_style)
        self.keyboard_ui = ManagerKeyboardMata('设置时', 960, 300)
        self.keyboard_ui.result_effective_context.connect(self.set_effective)
        self.keyboard_ui.result_effective_clear.connect(self.clear_effective)
        self.keyboard_ui.switch_ui.connect(self.switch_new_ui)
        self.keyboard_ui.show()
        self.content_text = ''

    def set_effective(self, msg):
        self.content_text += msg
        if len(self.content_text) > 2:
            self.content_text = self.content_text[-2:]
        self.h.setText(self.content_text)

    def clear_effective(self):
        self.content_text = ''
        self.h.setText(self.content_text)

    def switch_new_ui(self):
        self.h.setStyleSheet(self.time_label_style)
        self.m.setStyleSheet(self.time_label_select_style)
        self.keyboard_ui = ManagerKeyboardMata('设置分', 960, 300)
        self.keyboard_ui.result_effective_context.connect(self.set_effective_m)
        self.keyboard_ui.result_effective_clear.connect(self.clear_effective_m)
        self.keyboard_ui.switch_ui.connect(self.return_m_style)
        self.keyboard_ui.show()
        self.content_text = ''

    def return_m_style(self):
        self.m.setStyleSheet(self.time_label_style)

    def set_effective_m(self, msg):
        self.content_text += msg
        if len(self.content_text) > 2:
            self.content_text = self.content_text[-2:]
        if int(self.content_text) > 60:
            self.content_text = '60'
        self.m.setText(self.content_text)

    def clear_effective_m(self):
        self.content_text = ''
        self.m.setText(self.content_text)

    @pyqtSlot()
    def on_btn_begin_time_clicked(self):
        self.b_d.setStyleSheet(self.time_label_select_style)
        self.keyboard_ui = ManagerKeyboardMata('设置日', 330, 300)
        self.keyboard_ui.result_effective_context.connect(self.set_begin_time_d)
        self.keyboard_ui.result_effective_clear.connect(self.clear_begin_time_d)
        self.keyboard_ui.switch_ui.connect(self.switch_begin_time_h_ui)
        self.keyboard_ui.show()
        self.content_text = ''

    def set_begin_time_d(self, msg):
        self.content_text += msg
        if len(self.content_text) > 2:
            self.content_text = self.content_text[-2:]
        # 获取当前日期
        now = datetime.now()
        year = now.year
        month = now.month
        # 获取当前月的天数
        _, days_in_month = calendar.monthrange(year, month)
        if int(self.content_text) > days_in_month:
            self.content_text = '0'
        self.b_d.setText(self.content_text)

    def clear_begin_time_d(self):
        self.content_text = ''
        self.b_d.setText(self.content_text)

    def switch_begin_time_h_ui(self):
        self.b_d.setStyleSheet(self.time_label_style)
        self.b_h.setStyleSheet(self.time_label_select_style)
        self.keyboard_ui = ManagerKeyboardMata('设置时', 330, 300)
        self.keyboard_ui.result_effective_context.connect(self.set_begin_time_h)
        self.keyboard_ui.result_effective_clear.connect(self.clear_begin_time_h)
        self.keyboard_ui.switch_ui.connect(self.switch_begin_time_m_ui)
        self.keyboard_ui.show()
        self.content_text = ''

    def set_begin_time_h(self, msg):
        self.content_text += msg
        if len(self.content_text) > 2:
            self.content_text = self.content_text[-2:]
        if int(self.content_text) > 24:
            self.content_text = '2'
        self.b_h.setText(self.content_text)

    def clear_begin_time_h(self):
        self.content_text = ''
        self.b_h.setText(self.content_text)

    def switch_begin_time_m_ui(self):
        self.b_h.setStyleSheet(self.time_label_style)
        self.b_m.setStyleSheet(self.time_label_select_style)
        self.keyboard_ui = ManagerKeyboardMata('设置分', 330, 300)
        self.keyboard_ui.result_effective_context.connect(self.set_begin_time_m)
        self.keyboard_ui.result_effective_clear.connect(self.clear_begin_time_m)
        self.keyboard_ui.switch_ui.connect(self.return_b_m_style)
        self.keyboard_ui.show()
        self.content_text = ''

    def return_b_m_style(self):
        self.b_m.setStyleSheet(self.time_label_style)

    def set_begin_time_m(self, msg):
        self.content_text += msg
        if len(self.content_text) > 2:
            self.content_text = self.content_text[-2:]
        if int(self.content_text) > 60:
            self.content_text = '60'
        self.b_m.setText(self.content_text)

    def clear_begin_time_m(self):
        self.content_text = ''
        self.b_m.setText(self.content_text)

    @pyqtSlot()
    def on_btn_red_clicked(self):
        self.keyboard_ui = ManagerKeyboardMata('设置红色预警值', 960, 300)
        self.keyboard_ui.result_effective_context.connect(self.set_btn_red)
        self.keyboard_ui.result_effective_clear.connect(self.clear_btn_red)
        self.keyboard_ui.show()
        self.content_text = ''

    def set_btn_red(self, msg):
        self.content_text += msg
        self.l_red.setText(self.content_text)

    def clear_btn_red(self):
        self.content_text = ''
        self.l_red.setText('0')

    @pyqtSlot()
    def on_btn_yellow_clicked(self):
        self.keyboard_ui = ManagerKeyboardMata('设置黄色预警值', 330, 300)
        self.keyboard_ui.result_effective_context.connect(self.set_btn_yellow)
        self.keyboard_ui.result_effective_clear.connect(self.clear_btn_yellow)
        self.red_and_yellow.connect(self.keyboard_ui.get_red_and_yellow)
        self.keyboard_ui.show()
        self.content_text = ''

    def set_btn_yellow(self, msg):
        self.content_text += msg
        self.l_yellow.setText(self.content_text)
        #将红色值和黄色值发送到keyboard
        self.red_and_yellow.emit(int(self.l_red.text()), int(self.l_yellow.text()))

        # #下面的是设置黄色值需要大于红色值才能设置的操作，实际有问题先不去管了
        # self.content_text += msg
        # try:
        #     red_value = float(self.l_red.text())
        #     yellow_value = float(self.content_text)
        #     if yellow_value > red_value:
        #         self.l_yellow.setText(self.content_text)
        #     else:
        #         # 黄色预警值不大于红色预警值，不更新显示
        #         pass
        # except ValueError:
        #     # 处理输入不是有效数字的情况
        #     pass

    def clear_btn_yellow(self):
        self.content_text = ''
        self.l_yellow.setText('0')


    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if obj == self.widget:
                # if self.keyboard_ui is not None:
                #     self.keyboard_ui.close()
                pass
            elif obj == self.on_off_widget:
                self.shield_change(self.is_shield)
            elif obj == self.widget_10:
                self.edit_type.setReadOnly(False)
                self.edit_type.setFocus()
            elif obj == self.widget_11:
                self.edit_name.setReadOnly(False)
                self.edit_name.setFocus()
        return super().eventFilter(obj, event)

        # 是否自动出茶按钮

    def shield_change(self, is_checked):
        if not is_checked:
            # print("开")
            self.is_shield = True
            self.on_widget.setVisible(False)
            self.off_widget.setVisible(True)
        else:
            # print("关")
            self.is_shield = False
            self.off_widget.setVisible(False)
            self.on_widget.setVisible(True)

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

            AlibabaPuHuiTi_3_85_Bold_custom_font_20 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 20, QFont.Bold)
            self.lh.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            self.lm.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            self.lbd.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            self.lbh.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            self.lbm.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            self.label_5.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)
            self.label_6.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_20)

            AlibabaPuHuiTi_3_85_Bold_custom_font_24 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 24, QFont.Bold)
            self.l1.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l2.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l3.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l4.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l5.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l6.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l7.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l8.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l9.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            # 与其它标题/内容统一到 24 号加粗
            if hasattr(self, "l_assoc"):
                self.l_assoc.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            if hasattr(self, "i_assoc"):
                self.i_assoc.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)


            self.i1.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.i2.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.edit_type.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.edit_name.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l_red.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.l_yellow.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)

            self.h.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.m.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.b_d.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.b_h.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.b_m.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)

            self.conduit_save_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.conduit_cancel_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)



    @pyqtSlot()
    def on_conduit_cancel_btn_clicked(self):
        if self.keyboard_ui is not None:
            self.keyboard_ui.close()
        self.close()

    @pyqtSlot()
    def on_dialog_close_btn_clicked(self):
        if self.keyboard_ui is not None:
            self.keyboard_ui.close()
        self.close()
    def _build_assoc_row(self):
        """在‘类型/名称/屏蔽’下面插入‘关联配方’一行"""
        self.widget_assoc = QWidget(self.widget_7)
        self.widget_assoc.setObjectName("widget_assoc")
        row = QHBoxLayout(self.widget_assoc)
        row.setContentsMargins(0, 0, 0, 0); row.setSpacing(0)

        # 左边占位（和其它行一致：150px）
        left_pad = QLabel(self.widget_assoc)
        left_pad.setMinimumSize(150, 0); left_pad.setMaximumSize(150, 16777215)
        row.addWidget(left_pad)

        # 标题
        self.l_assoc = QLabel("关联配方：", self.widget_assoc)
        self.l_assoc.setMinimumSize(101, 50); self.l_assoc.setMaximumSize(101, 50)
        self.l_assoc.setStyleSheet("color:rgb(44, 159, 97);")
        row.addWidget(self.l_assoc)

        # 内容（可换行显示饮品名）
        self.i_assoc = QLabel(self.widget_assoc)
        self.i_assoc.setMinimumSize(0, 50); self.i_assoc.setMaximumSize(2000, 50)
        self.i_assoc.setWordWrap(True)
        self.i_assoc.setStyleSheet("color:rgb(51, 51, 51);")
        row.addWidget(self.i_assoc, 1)

        # 插入到纵向布局：widget_3(管道) -> widget_5(类型/名称/屏蔽) -> 这里
        self.verticalLayout.insertWidget(2, self.widget_assoc)
        # 颜色与尺寸统一（和其它标题/内容一致）
        self.l_assoc.setStyleSheet("color:rgb(44, 159, 97);")
        self.i_assoc.setStyleSheet("color:rgb(51, 51, 51);")
        self.l_assoc.setMinimumSize(150, 50); self.l_assoc.setMaximumSize(150, 50)
        self.i_assoc.setMinimumSize(0,   50); self.i_assoc.setMaximumSize(2000, 50)

        # 直接复用现有控件的字体，保持“完全一致”
        self.l_assoc.setFont(self.l3.font())            # 跟“类型/名称/屏蔽”的标题一致（24 号加粗）
        self.i_assoc.setFont(self.edit_name.font())     # 跟右侧内容/输入框一致（24 号加粗）


    # === 3) 找到 tea_drinks_menu.json 的路径（按你项目常见位置摸排） ===
    def _menu_json_path(self) -> str | None:
        # 依次在 _MEIPASS、exe 同目录、源码同目录、当前工作目录查找
        bases = []
        if hasattr(sys, "_MEIPASS"):
            bases.append(sys._MEIPASS)  # PyInstaller --onefile 临时解包目录
        # exe/启动目录（onedir 或某些启动方式）
        bases.append(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else "")
        # 源码所在目录
        bases.append(os.path.abspath(os.path.dirname(__file__)))
        # 当前工作目录（最后兜底）
        bases.append(os.path.abspath("."))

        candidates = [
            ("menu_xlsx", "tea_drinks_menu.json"),
            ("tea_drinks_menu.json",),
        ]
        for base in bases:
            for parts in candidates:
                if not base:  # 为空就只拼候选相对路径
                    p = os.path.join(*parts)
                else:
                    p = os.path.join(base, *parts)
                if os.path.exists(p):
                    return p
        return None

    # === 4) 从菜单里找出使用某材料的所有饮品 ===
    def _drinks_using_material(self, material_name: str):
        material = (material_name or "").strip()
        if not material:
            return []
        path = self._menu_json_path()
        if not path:
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f) or []
        except Exception:
            return []

        # 解析 Recipe 中的“材料名+三位数克重”，示例：四季春茶100 冰100 …（见你的 JSON）
        pat = re.compile(r"([^\d\s]+)\s*\d+")
        hit = []
        for it in items:
            name = str(it.get("Name", "")).strip()
            recipe = str(it.get("Recipe", ""))
            mats = [m.strip() for m in pat.findall(recipe)]

            # ✅ 严格匹配：材料名必须与配方里的材料完全一致
            if material in mats:
                if name:
                    hit.append(name)
        return sorted(set(hit))

    # === 5) 刷新“关联配方”文本 ===
    def _refresh_assoc_list(self):
        mats = self.edit_name.text().strip()
        names = self._drinks_using_material(mats)
        self.i_assoc.setText("、".join(names) if names else "（暂无）") 
    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    myShow = NewConduitDialog()
    myShow.show()
    sys.exit(app.exec_())
