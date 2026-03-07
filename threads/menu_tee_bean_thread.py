import json
import sys
import os
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal

from bean.menu_tee_bean import MenuTeeBean


class MenuTeeBeanThread(QThread):
    add_menu_tee_bean = pyqtSignal(MenuTeeBean)

    def __init__(self, parent=None):
        super(MenuTeeBeanThread, self).__init__(parent)

    def run(self):
        # file_path = 'menu_xlsx/tea_drinks_menu.xlsx'
        # df = pd.read_excel(file_path)
        # for _, row in df.iterrows():
        #     tee_bean = MenuTeeBean()
        #     tee_bean.set_ID(row['ID'])
        #     tee_bean.set_Name(row['Name'])
        #     tee_bean.set_Base_Price(row['Base Price'])
        #     tee_bean.set_Sweetness_Options(row['Sweetness Options'])
        #     tee_bean.set_Temperature_Options(row['Temperature Options'])
        #     tee_bean.set_Size_Options(row['Size Options'])
        #     tee_bean.set_Add_ons(row['Add-ons'])
        #     tee_bean.set_Image_path(row['Image'])
        #     tee_bean.Recipe = row['Recipe']
        #     self.add_menu_tee_bean.emit(tee_bean)
        # file_path = 'menu_xlsx/tea_drinks_menu.json'
        file_path = self.resource_path('menu_xlsx/tea_drinks_menu.json')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                tee_bean = MenuTeeBean()
                tee_bean.set_ID(item['ID'])
                tee_bean.set_Name(item['Name'])
                tee_bean.set_Base_Price(item['Base Price'])
                tee_bean.set_Sweetness_Options(item['Sweetness Options'])
                tee_bean.set_Temperature_Options(item['Temperature Options'])
                tee_bean.set_Size_Options(item['Size Options'])
                tee_bean.set_Add_ons(item['Add-ons'])
                tee_bean.Image_path = item['Image']
                tee_bean.Recipe = item['Recipe']
                self.add_menu_tee_bean.emit(tee_bean)
        except FileNotFoundError:
            print(f"文件 {file_path} 未找到。")
        except json.JSONDecodeError:
            print(f"无法解析 {file_path} 中的 JSON 数据。")
      
        



    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)
