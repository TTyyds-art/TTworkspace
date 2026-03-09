from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, Qt, QSettings
from ui_1080_py.Ui_language_settings_ui import Ui_MainWindow as UiLanguageSettings


class OrderLanguageSettings(QtWidgets.QWidget):
    back_to_setting = pyqtSignal()
    language_apply = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = UiLanguageSettings()
        self._host = QtWidgets.QMainWindow()
        self.ui.setupUi(self._host)
        self._mount_centralwidget()
        self._bind_events()

    def _mount_centralwidget(self):
        central = getattr(self.ui, "centralwidget", None)
        if central is None:
            return
        try:
            base_size = self._host.size()
            central.setFixedSize(base_size)
        except Exception:
            pass
        central.setParent(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(central, alignment=Qt.AlignLeft | Qt.AlignTop)

    def _bind_events(self):
        try:
            self.ui.label_7.mousePressEvent = self._on_back_clicked
        except Exception:
            pass
        try:
            self.ui.pushButton_language_pply.clicked.connect(self._on_apply_clicked)
        except Exception:
            pass
        self._restore_selection()

    def _on_back_clicked(self, _event):
        self.close()
        self.back_to_setting.emit()

    def _on_apply_clicked(self):
        # 仅先实现繁体中文
        code = "zh_CN"
        if getattr(self.ui, "radioButton_8", None) and self.ui.radioButton_8.isChecked():
            code = "zh_TW"
        elif getattr(self.ui, "radioButton_3", None) and self.ui.radioButton_3.isChecked():
            code = "en"
        elif getattr(self.ui, "radioButton_9", None) and self.ui.radioButton_9.isChecked():
            code = "ja"
        elif getattr(self.ui, "radioButton_11", None) and self.ui.radioButton_11.isChecked():
            code = "ko"
        elif getattr(self.ui, "radioButton_10", None) and self.ui.radioButton_10.isChecked():
            code = "de"
        elif getattr(self.ui, "radioButton_12", None) and self.ui.radioButton_12.isChecked():
            code = "fr"
        self.language_apply.emit(code)

    def _restore_selection(self):
        try:
            lang = QSettings("Xiliu", "Miketee").value("i18n/lang", "zh_CN", type=str)
        except Exception:
            lang = "zh_CN"
        mapping = {
            "zh_CN": "radioButton",
            "zh_TW": "radioButton_8",
            "en": "radioButton_3",
            "ja": "radioButton_9",
            "ko": "radioButton_11",
            "de": "radioButton_10",
            "fr": "radioButton_12",
        }
        name = mapping.get(lang)
        if not name:
            return
        btn = getattr(self.ui, name, None)
        if btn is not None:
            btn.setChecked(True)
