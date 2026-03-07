import sys
import os
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QWidget

from bean.conduit_bean import ConduitBean
from ui_1080_py.Ui_conduit_dialog_ui import Ui_Form

#没用到
class ConduitDialog(QWidget, Ui_Form):
    result_new_conduit_bean = pyqtSignal(ConduitBean)

    def __init__(self, conduit_bean, parent=None):
        super(ConduitDialog, self).__init__(parent)
        self.conduit_bean = conduit_bean
        self.setupUi(self)
        self.move(0,0)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_font()
        self.dialog_config_4.addItem('低')
        self.dialog_config_4.addItem('中')
        self.dialog_config_4.addItem('高')
        self.dialog_config_7.addItem('1')
        self.dialog_config_7.addItem('2')
        self.dialog_config_7.addItem('3')
        self.init_ui()

    def init_ui(self):
        self.dialog_config_1.setText(self.conduit_bean.get_conduit())
        self.dialog_config_2.setText(self.conduit_bean.get_conduit_type())
        self.dialog_config_3.setText(self.conduit_bean.get_name())
        self.dialog_config_4.setCurrentText(self.conduit_bean.get_speed())
        self.dialog_config_5.setText(f'{str(self.conduit_bean.get_allowance())}g')
        self.dialog_config_7.setCurrentText(str(self.conduit_bean.get_level()))

    @pyqtSlot()
    def on_conduit_save_btn_clicked(self):
        self.conduit_bean.set_name(self.dialog_config_3.text())
        self.conduit_bean.set_speed(self.dialog_config_4.currentText())
        self.conduit_bean.set_level(self.dialog_config_7.currentText())
        self.result_new_conduit_bean.emit(self.conduit_bean)
        self.close()

    @pyqtSlot()
    def on_conduit_cancel_btn_clicked(self):
        self.close()

    @pyqtSlot()
    def on_dialog_close_btn_clicked(self):
        self.close()
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
            AlibabaPuHuiTi_3_85_Bold_custom_font_24 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 24, QFont.Bold)
            self.dialog_name_1.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_name_2.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_name_3.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_name_4.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_name_5.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_name_6.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_name_7.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_config_1.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_config_2.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_config_3.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_config_4.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_config_5.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_config_6.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            self.dialog_config_7.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_24)
            AlibabaPuHuiTi_3_85_Bold_custom_font_32 = QFont(AlibabaPuHuiTi_3_85_Bold_font_family, 32, QFont.Bold)
            self.conduit_save_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_32)
            self.conduit_cancel_btn.setFont(AlibabaPuHuiTi_3_85_Bold_custom_font_32)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myShow = ConduitDialog()
    myShow.show()
    sys.exit(app.exec_())
