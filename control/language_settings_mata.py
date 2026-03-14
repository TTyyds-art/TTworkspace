import os
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout

from ui_1080_py.ui_language_settings import Ui_MainWindow


def _res_path(p: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.join(os.path.abspath("."), p)


class LanguageSettingsPage(QWidget):
    def __init__(self, parent=None, on_back=None):
        super().__init__(parent)
        self._on_back = on_back
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

