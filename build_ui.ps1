# 1) pyuic 生成 UI
py -3.11 -m PyQt5.uic.pyuic .\ui_1080\order_dialog_1_ui.ui -o .\ui_1080_py\Ui_order_dialog_1_ui.py

# 2) 生成资源
py -3.11 -m PyQt5.pyrcc_main .\drawable\drawable.qrc -o .\ui_1080_py\resources_rc.py

# 3) 确保 ui_1080_py 是包
New-Item -ItemType File -Path .\ui_1080_py\__init__.py -Force | Out-Null

# 4) 修补 import resources_rc 为包导入
(Get-Content .\ui_1080_py\Ui_order_dialog_1_ui.py) `
  -replace '^import resources_rc$', 'from ui_1080_py import resources_rc' `
  | Set-Content .\ui_1080_py\Ui_order_dialog_1_ui.py

# # 5) 生成繁体中文翻译源文件（.ts）
# py -3.11 -m PyQt5.pylupdate_main `
#   .\ui_1080\btn_page_ui.ui `
#   .\ui_1080\camera_frame_ui.ui `
#   .\ui_1080\clean_day_load_ui.ui `
#   .\ui_1080\clean_week_load_ui.ui `
#   .\ui_1080\conduit_card_keyboard_ui.ui `
#   .\ui_1080\conduit_card_maketee_ui.ui `
#   .\ui_1080\conduit_card_ui.ui `
#   .\ui_1080\conduit_dialog_ui.ui `
#   .\ui_1080\conduit_new_dialog_ui.ui `
#   .\ui_1080\item_conduit_ui.ui `
#   .\ui_1080\item_notice_message_ui.ui `
#   .\ui_1080\item_notice_remind_ui.ui `
#   .\ui_1080\item_notice_warn_ui.ui `
#   .\ui_1080\item_screen_conduit_ui.ui `
#   .\ui_1080\item_setting_local_message_record_ui.ui `
#   .\ui_1080\item_setting_local_tee_record_ui.ui `
#   .\ui_1080\login_ui.ui `
#   .\ui_1080\main_1080_ui.ui `
#   .\ui_1080\main_1080_ui_1.ui `
#   .\ui_1080\main_ui.ui `
#   .\ui_1080\manager_keyboard_ui.ui `
#   .\ui_1080\menu_card_ui.ui `
#   .\ui_1080\message_dialog_ui.ui `
#   .\ui_1080\order_card_ui.ui `
#   .\ui_1080\order_dialog_1_ui.ui `
#   .\ui_1080\order_dialog_2_ui.ui `
#   .\ui_1080\outtee_notice_ui.ui `
#   .\ui_1080\second_screen_ui.ui `
#   .\ui_1080\ui_language_settings.ui `
#   .\main_1080_mata.py `
#   .\control\order_language_settings.py `
#   -ts .\i18n\zh_TW.ts

# # 6) 编译繁体中文翻译文件（.qm）
# py -3.11 -m PyQt5.lrelease .\i18n\zh_TW.ts -qm .\i18n\zh_TW.qm
