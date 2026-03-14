import os
import sys
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout

from ui_1080_py.ui_language_settings import Ui_MainWindow


def _res_path(p: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.join(os.path.abspath("."), p)


class LanguageSettingsPage(QWidget):
    def __init__(self, parent=None, on_back=None, on_apply_language=None):
        super().__init__(parent)
        self._on_back = on_back
        self._on_apply_language = on_apply_language
        self._mw = QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self._mw)

        central = self._mw.centralWidget()
        central.setParent(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(central)

        self.init_font()
        if hasattr(self.ui, "label_7"):
            self.ui.label_7.mousePressEvent = self._on_back_clicked
        if hasattr(self.ui, "pushButton_language_pply"):
            self.ui.pushButton_language_pply.clicked.connect(self._on_apply_clicked)
        self._sync_selected_language()

    def _sync_selected_language(self):
        try:
            lang = str(QSettings("MikeTee", "MikeTee").value("ui/language", "zh_CN"))
        except Exception:
            lang = "zh_CN"

        # 默认简体
        if hasattr(self.ui, "radioButton"):
            self.ui.radioButton.setChecked(True)

        if lang == "zh_TW" and hasattr(self.ui, "radioButton_8"):
            self.ui.radioButton_8.setChecked(True)
        elif lang == "en" and hasattr(self.ui, "radioButton_3"):
            self.ui.radioButton_3.setChecked(True)
        elif lang == "ja" and hasattr(self.ui, "radioButton_9"):
            self.ui.radioButton_9.setChecked(True)
        elif lang == "ko" and hasattr(self.ui, "radioButton_11"):
            self.ui.radioButton_11.setChecked(True)

    def _on_back_clicked(self, _event):
        if callable(self._on_back):
            self._on_back()

    def init_font(self):
        font_id = QFontDatabase.addApplicationFont(
            _res_path("fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf")
        )
        if font_id != -1:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
            title_font = QFont(family, 20, QFont.Bold)
            subtitle_font = QFont(family, 14)
            if hasattr(self.ui, "label"):
                self.ui.label.setFont(title_font)
            if hasattr(self.ui, "label_4"):
                self.ui.label_4.setFont(subtitle_font)
            if hasattr(self.ui, "label_5"):
                self.ui.label_5.setFont(subtitle_font)

    def _on_apply_clicked(self):
        lang = "zh_CN"
        if hasattr(self.ui, "radioButton_8") and self.ui.radioButton_8.isChecked():
            lang = "zh_TW"
        elif hasattr(self.ui, "radioButton_3") and self.ui.radioButton_3.isChecked():
            lang = "en"
        elif hasattr(self.ui, "radioButton_9") and self.ui.radioButton_9.isChecked():
            lang = "ja"
        elif hasattr(self.ui, "radioButton_11") and self.ui.radioButton_11.isChecked():
            lang = "ko"

        if callable(self._on_apply_language):
            self._on_apply_language(lang)
        self._sync_selected_language()

