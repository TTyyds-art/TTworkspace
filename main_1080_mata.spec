# -*- mode: python ; coding: utf-8 -*-

import os
import PyQt5.QtCore as QC
from PyInstaller.building.datastruct import Tree

block_cipher = None

# Qt 插件路径
qt_plugins = QC.QLibraryInfo.location(QC.QLibraryInfo.PluginsPath)

# 精选需要的插件（按需增删）
qt_bins = [
    (os.path.join(qt_plugins, "platforms", "qwindows.dll"), "platforms"),
    (os.path.join(qt_plugins, "imageformats", "qjpeg.dll"), "imageformats"),
    (os.path.join(qt_plugins, "imageformats", "qico.dll"), "imageformats"),
    # 如果你使用 Vista 风格：
    (os.path.join(qt_plugins, "styles", "qwindowsvistastyle.dll"), "styles"),
]

a = Analysis(
    ['main_1080_mata.py'],
    pathex=[],
    binaries=qt_bins + [('pyzbar_dlls\\*', '.')],
    datas=[
        ('data\\*',           'data'),
        ('db\\*',             'db'),
        ('conduit_xlsx\\*',   'conduit_xlsx'),
        ('menu_xlsx\\*',      'menu_xlsx'),
        ('tee_image_xlsx\\*', 'tee_image_xlsx'),
        ('ui_1080_py\\*',     'ui_1080_py'),
        ('drawable\\*',       'drawable'),
        ('json.json',          '.'),
        ('tee_data.db',        '.'),
        ('db\\auth.db',        'db'),
    ],
    hiddenimports=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngineCore',
        # 如未使用，可继续排：'PyQt5.QtNetwork','PyQt5.QtSvg','numpy','pandas'
    ],
    noarchive=False,
)

# 递归打包字体目录（保留层级）
a.datas += Tree('fonts', prefix='fonts')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main_1080_mata',
    icon='favicon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='main_1080_mata',
)
