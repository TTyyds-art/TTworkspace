# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_1080_mata.py'],
    pathex=[],
    binaries=[('pyzbar_dlls\\*', '.')],
    datas=[('fonts', 'fonts'), ('data', 'data'), ('db', 'db'), ('conduit_xlsx', 'conduit_xlsx'), ('menu_xlsx', 'menu_xlsx'), ('tee_image_xlsx', 'tee_image_xlsx'), ('ui_1080_py', 'ui_1080_py'), ('json.json', '.'), ('tee_data.db', '.')],
    hiddenimports=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngineCore'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MikeTee',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['favicon.ico'],
)
