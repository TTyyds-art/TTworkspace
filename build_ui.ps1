# 1) pyuic 生成 UI
py -3.11 -m PyQt5.uic.pyuic .\ui_1080\order_dialog_1_ui.ui -o .\ui_1080_py\Ui_order_dialog_1_ui.py

# 2) 生成资源
py -3.11 -m PyQt5.pyrcc_main .\drawable\drawable.qrc -o .\drawable_rc.py
py -3.11 -m PyQt5.pyrcc_main .\drawable\drawable.qrc -o .\drawable\drawable_rc.py
py -3.11 -m PyQt5.pyrcc_main .\drawable\drawable.qrc -o .\ui_1080_py\resources_rc.py

# 3) 确保 ui_1080_py 是包
New-Item -ItemType File -Path .\ui_1080_py\__init__.py -Force | Out-Null

# 4) 修补 import resources_rc 为包导入
(Get-Content .\ui_1080_py\ui_language_settings.py) `
  -replace '^import resources_rc$', 'from ui_1080_py import resources_rc' `
  | Set-Content .\ui_1080_py\ui_language_settings.py
