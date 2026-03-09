from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt5 import QtCore, QtWidgets


class LanguageManager(QtCore.QObject):
    language_changed = QtCore.pyqtSignal(str)

    def __init__(self, app: QtWidgets.QApplication, settings: QtCore.QSettings, parent=None):
        super().__init__(parent)
        self._app = app
        self._settings = settings
        self._translator: Optional[QtCore.QTranslator] = None

    def current_language(self) -> str:
        return self._settings.value("i18n/lang", "zh_CN", type=str)

    def load_on_startup(self) -> None:
        lang = self.current_language()
        self.set_language(lang, persist=False)

    def set_language(self, lang_code: str, persist: bool = True) -> bool:
        lang_code = (lang_code or "zh_CN").strip()

        if lang_code in ("zh_CN", "zh-Hans", "zh_CN.UTF-8"):
            self._remove_translator()
            self._after_change(lang_code, persist)
            return True

        qm_path = self._resolve_qm(lang_code)
        if not qm_path:
            return False

        self._remove_translator()
        tr = QtCore.QTranslator()
        if not tr.load(qm_path):
            return False
        self._app.installTranslator(tr)
        self._translator = tr
        self._after_change(lang_code, persist)
        return True

    def _after_change(self, lang_code: str, persist: bool) -> None:
        if persist:
            self._settings.setValue("i18n/lang", lang_code)
            self._settings.sync()
        self.refresh_all_widgets()
        self.language_changed.emit(lang_code)

    def _remove_translator(self) -> None:
        if self._translator is None:
            return
        try:
            self._app.removeTranslator(self._translator)
        finally:
            self._translator = None

    def refresh_all_widgets(self) -> None:
        visited = set()
        for w in self._app.topLevelWidgets():
            self._refresh_widget_recursive(w, visited)

    def _refresh_widget_recursive(self, widget: QtWidgets.QWidget, visited: set) -> None:
        if widget is None:
            return
        wid = int(widget.winId()) if widget.winId() else id(widget)
        if wid in visited:
            return
        visited.add(wid)

        self.refresh_widget(widget)

        try:
            children = widget.findChildren(QtWidgets.QWidget)
        except Exception:
            children = []
        for child in children:
            self._refresh_widget_recursive(child, visited)

    def refresh_widget(self, widget: QtWidgets.QWidget) -> None:
        if widget is None:
            return
        # 1) 自定义 retranslate
        retranslate: Optional[Callable[[], None]] = getattr(widget, "retranslate", None)
        if callable(retranslate):
            try:
                retranslate()
            except Exception:
                pass

        # 2) ui.retranslateUi
        ui = getattr(widget, "ui", None)
        if ui is not None:
            cb = getattr(ui, "retranslateUi", None)
            if callable(cb):
                try:
                    cb(widget)
                except Exception:
                    pass

        # 3) 直接 retranslateUi
        cb2 = getattr(widget, "retranslateUi", None)
        if callable(cb2):
            try:
                cb2(widget)
            except Exception:
                pass

    def _resolve_qm(self, lang_code: str) -> Optional[str]:
        rel = os.path.join("i18n", f"{lang_code}.qm")
        paths = [
            os.path.join(os.path.abspath("."), rel),
        ]
        for p in paths:
            if os.path.isfile(p):
                return p
        return None

