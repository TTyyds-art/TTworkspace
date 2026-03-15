import os
import sys
from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication


def _res_path(p: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.join(os.path.abspath("."), p)


_OPENCC_CONVERTER = None


def _get_opencc_converter():
    global _OPENCC_CONVERTER
    if _OPENCC_CONVERTER is not None:
        return _OPENCC_CONVERTER if _OPENCC_CONVERTER is not False else None
    try:
        from opencc import OpenCC
        _OPENCC_CONVERTER = OpenCC("s2t")
    except Exception:
        _OPENCC_CONVERTER = False
    return _OPENCC_CONVERTER if _OPENCC_CONVERTER is not False else None


def get_saved_language(settings_org: str = "MikeTee", settings_app: str = "MikeTee") -> str:
    try:
        return str(QSettings(settings_org, settings_app).value("ui/language", "zh_CN"))
    except Exception:
        return "zh_CN"


def maybe_convert_zh_tw(text: str, settings_org: str = "MikeTee", settings_app: str = "MikeTee") -> str:
    if text is None:
        return text
    raw = str(text)
    lang = get_saved_language(settings_org=settings_org, settings_app=settings_app)
    if lang and lang.lower() in ("zh_tw", "zh-hant", "zh_hant", "tw", "zh-tw"):
        converter = _get_opencc_converter()
        if converter:
            try:
                return converter.convert(raw)
            except Exception:
                return raw
    return raw


def apply_zh_tw_to_widget_tree(root, settings_org: str = "MikeTee", settings_app: str = "MikeTee") -> None:
    if root is None:
        return
    lang = get_saved_language(settings_org=settings_org, settings_app=settings_app)
    if not (lang and lang.lower() in ("zh_tw", "zh-hant", "zh_hant", "tw", "zh-tw")):
        return
    converter = _get_opencc_converter()
    if not converter:
        return

    try:
        from PyQt5 import QtWidgets
    except Exception:
        return

    def _convert_text(txt: str) -> str:
        if txt is None:
            return txt
        try:
            return converter.convert(str(txt))
        except Exception:
            return str(txt)

    def _handle_widget(w):
        try:
            if hasattr(w, "text") and hasattr(w, "setText"):
                t = w.text()
                if t:
                    w.setText(_convert_text(t))
        except Exception:
            pass

        try:
            if isinstance(w, QtWidgets.QLineEdit):
                ph = w.placeholderText()
                if ph:
                    w.setPlaceholderText(_convert_text(ph))
        except Exception:
            pass

        try:
            if isinstance(w, QtWidgets.QComboBox):
                for i in range(w.count()):
                    t = w.itemText(i)
                    if t:
                        w.setItemText(i, _convert_text(t))
        except Exception:
            pass

        try:
            if isinstance(w, QtWidgets.QTabWidget):
                for i in range(w.count()):
                    t = w.tabText(i)
                    if t:
                        w.setTabText(i, _convert_text(t))
        except Exception:
            pass

        try:
            if isinstance(w, QtWidgets.QGroupBox):
                t = w.title()
                if t:
                    w.setTitle(_convert_text(t))
        except Exception:
            pass

        try:
            if isinstance(w, QtWidgets.QAbstractButton):
                t = w.text()
                if t:
                    w.setText(_convert_text(t))
        except Exception:
            pass

    try:
        _handle_widget(root)
        for w in root.findChildren(QtWidgets.QWidget):
            _handle_widget(w)
        for act in root.findChildren(QtWidgets.QAction):
            try:
                t = act.text()
                if t:
                    act.setText(_convert_text(t))
            except Exception:
                pass
    except Exception:
        return


class LanguageManager:
    def __init__(self, app, settings_org: str = "MikeTee", settings_app: str = "MikeTee"):
        self._app = app
        self._settings = QSettings(settings_org, settings_app)
        self._translator = QTranslator()

    def get_lang(self) -> str:
        return str(self._settings.value("ui/language", "zh_CN"))

    def set_lang(self, lang: str) -> None:
        self._settings.setValue("ui/language", lang)

    def apply(self, lang: str) -> bool:
        try:
            QCoreApplication.removeTranslator(self._translator)
        except Exception:
            pass

        if lang and lang.lower() not in ("zh_cn", "zh-hans", "cn"):
            qm_path = self._qm_path(lang)
            print(f"[lang] apply: lang={lang!r} qm_path={qm_path!r} exists={os.path.exists(qm_path)}")
            if os.path.exists(qm_path):
                loaded = self._translator.load(qm_path)
                print(f"[lang] translator.load -> {loaded}")
                if loaded:
                    QCoreApplication.installTranslator(self._translator)
                    try:
                        sample = QCoreApplication.translate("MainWindow", "语言选择")
                        print(f"[lang] sample translate(MainWindow,'语言选择') -> {sample!r}")
                    except Exception as e:
                        print(f"[lang] sample translate error: {e}")
            else:
                print("[lang] missing qm file, skip installTranslator")
        else:
            print(f"[lang] apply: lang={lang!r} -> default zh_CN, no qm load")

        self.set_lang(lang)
        return True

    def _qm_path(self, lang: str) -> str:
        # 兼容 en/en_US 等别名
        aliases = [lang]
        low = (lang or "").lower()
        if low == "en":
            aliases.append("en_US")
        elif low == "en_us":
            aliases.append("en")

        candidates = []
        for key in aliases:
            candidates.append(_res_path(os.path.join("i18n", f"{key}.qm")))
            candidates.append(_res_path(f"{key}.qm"))

        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]
