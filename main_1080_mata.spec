# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_1080_mata.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main_1080_mata',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,# MikeTee.spec —— 最小化 PyQt5 插件 + UPX
# 1) 先把 UPX 放进 PATH，或在 EXE(...) 里设置 upx=True（默认会用到）

import os, PyQt5.QtCore as QC

block_cipher = None

# Qt 插件路径
qt_plugins = QC.QLibraryInfo.location(QC.QLibraryInfo.PluginsPath)

# 精选需要的插件（按需增删）
qt_bins = [
    (os.path.join(qt_plugins, "platforms", "qwindows.dll"), "platforms"),
    (os.path.join(qt_plugins, "imageformats", "qjpeg.dll"), "imageformats"),
    (os.path.join(qt_plugins, "imageformats", "qico.dll"),  "imageformats"),
    # 如果你使用 Vista 风格：
    (os.path.join(qt_plugins, "styles", "qwindowsvistastyle.dll"), "styles"),
]

a = Analysis(
    ['main_1080_mata.py'],
    pathex=[],
    binaries=qt_bins + [('pyzbar_dlls\\*', '.')],   # 你已有的二进制
    datas=[
        ('fonts\\*',         'fonts'),
        ('data\\*',          'data'),
        ('db\\*',            'db'),
        ('conduit_xlsx\\*',  'conduit_xlsx'),
        ('menu_xlsx\\*',     'menu_xlsx'),
        ('tee_image_xlsx\\*','tee_image_xlsx'),
        ('ui_1080_py\\*',    'ui_1080_py'),
        ('json.json',        '.'),
        ('tee_data.db',      '.'),
        ('auth_db.db',       'db'),
    ],
    hiddenimports=['PyQt5.QtCore','PyQt5.QtGui','PyQt5.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngineCore',
        # 如未使用，可继续排：'PyQt5.QtNetwork','PyQt5.QtSvg','numpy','pandas'
    ],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='MikeTee',
    icon='favicon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,        # Windows strip 无效，保持 False
    upx=True,           # 安装了 UPX 就会压缩
    console=False,
)

coll = COLLECT(exe, name='MikeTee')

)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main_1080_mata',
)
