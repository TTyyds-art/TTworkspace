# -*- coding: utf-8 -*-
"""菜单更新管理模块 - 三Tab界面：菜单管理/配方管理/导入导出"""
import json
import os
import re
import shutil
import socket
import threading
import http.server
import urllib.parse
from datetime import datetime
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QLineEdit, QLabel, QTextEdit, QFileDialog,
                             QMessageBox, QHeaderView, QComboBox, QScrollArea,
                             QDialog)
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFontDatabase, QFont
import qrcode
from io import BytesIO

def _res_path(rel):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

MENUS_PATH = _res_path("menu_xlsx/menus_v1.json")
RECIPES_PATH = _res_path("menu_xlsx/recipes_v1.json")
OLD_MENU_PATH = _res_path("menu_xlsx/tea_drinks_menu.json")
IMAGE_DIR = _res_path("tee_image_xlsx")

# 冰量/糖量规则映射
ICE_RULES = {"少冰": 0.5, "正常冰": 1.0, "常温": 0.0, "去冰": 0.0, "多冰": 1.5}
SUGAR_RULES = {"三分糖": 0.3, "五分糖": 0.5, "七分糖": 0.7, "常规": 1.0, "无糖": 0.0}

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_recipe_text(text):
    """解析配方文本 '冰220 碎冰220 红茶100' -> [('冰',220), ('碎冰',220), ('红茶',100)]"""
    pairs = []
    for token in text.strip().split():
        m = re.match(r'^(.+?)(\d{1,4})$', token)
        if m:
            pairs.append((m.group(1), int(m.group(2))))
    return pairs

def build_recipe_text(pairs):
    """[('冰',220), ('红茶',100)] -> '冰220 红茶100'"""
    return " ".join(f"{name}{gram}" for name, gram in pairs)

def convert_old_menu_to_new(old_item):
    """将旧格式菜单转换为新的Menu+Recipe结构"""
    menu_id = old_item.get("ID", "")
    recipe_id = f"R{menu_id}"
    
    menu = {
        "menu_id": menu_id,
        "name": old_item.get("Name", ""),
        "base_price": old_item.get("Base Price", 0),
        "image": old_item.get("Image", ""),
        "cup": old_item.get("cup", "成品杯"),
        "tips": old_item.get("tips", ""),
        "base_recipe_id": recipe_id,
        "options": {
            "sweetness": old_item.get("Sweetness Options", "").split(","),
            "temperature": old_item.get("Temperature Options", "").split(","),
            "size": old_item.get("Size Options", "").split(","),
            "addons": old_item.get("Add-ons", "").split(",")
        }
    }
    
    recipe_text = old_item.get("Recipe", "")
    pairs = parse_recipe_text(recipe_text)
    
    # 分离冰/碎冰/糖基底
    ice_base, crushed_ice_base, sugar_base = 0, 0, 0
    base_materials = []
    for name, gram in pairs:
        if name == "冰":
            ice_base = gram
        elif name == "碎冰":
            crushed_ice_base = gram
        elif name in ("果糖", "糖", "白糖"):
            sugar_base = gram
        else:
            base_materials.append((name, gram))
    
    recipe = {
        "recipe_id": recipe_id,
        "base_materials": build_recipe_text(base_materials),
        "ice_base": ice_base,
        "crushed_ice_base": crushed_ice_base,
        "ice_rule": {"少冰": 0.5, "正常冰": 1.0, "常温": 0.0},
        "sugar_base": sugar_base,
        "sugar_rule": {"三分糖": 0.3, "五分糖": 0.5, "常规": 1.0},
        "topping_rule": {}
    }
    
    return menu, recipe

def get_local_ip():
    """获取本机局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


class QRUploadDialog(QDialog):
    """二维码上传图片对话框"""
    image_received = pyqtSignal(str)  # 图片保存路径
    upload_success = pyqtSignal(str)  # 上传成功信号
    
    def __init__(self, drink_name, parent=None):
        super().__init__(parent)
        self.drink_name = drink_name
        self.server = None
        self.port = 8899
        self.setWindowTitle("扫码上传图片")
        self.setFixedSize(400, 480)
        self._init_ui()
        self._start_server()
        self.upload_success.connect(self._show_success)
    
    def _show_success(self, filename):
        self.status_label.setText(f"✓ 上传成功：{filename}")
        self.status_label.setStyleSheet("font-size:14px;color:#28a745;font-weight:bold;")
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 提示
        tip = QLabel(f"请用手机扫码上传【{self.drink_name}】的图片")
        tip.setStyleSheet("font-size:14px;color:#333;")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        
        # 二维码显示
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(300, 300)
        self.qr_label.setStyleSheet("border:1px solid #ddd;")
        layout.addWidget(self.qr_label, alignment=QtCore.Qt.AlignCenter)
        
        # 状态
        self.status_label = QLabel("等待上传...")
        self.status_label.setStyleSheet("font-size:13px;color:#666;")
        layout.addWidget(self.status_label, alignment=QtCore.Qt.AlignCenter)
        
        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.setFixedSize(100, 36)
        btn_close.setStyleSheet("QPushButton{background:#53CB31;color:white;border-radius:6px;}")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=QtCore.Qt.AlignCenter)
    
    def _start_server(self):
        ip = get_local_ip()
        url = f"http://{ip}:{self.port}/upload?name={urllib.parse.quote(self.drink_name)}"
        
        # 生成二维码
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转为QPixmap
        buf = BytesIO()
        img.save(buf, format='PNG')
        qimg = QImage.fromData(buf.getvalue())
        self.qr_label.setPixmap(QPixmap.fromImage(qimg).scaled(300, 300, QtCore.Qt.KeepAspectRatio))
        
        # 启动HTTP服务器
        self._run_server()
    
    def _run_server(self):
        dialog = self
        img_dir = _res_path("tee_image_xlsx")
        os.makedirs(img_dir, exist_ok=True)
        
        class UploadHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                name = params.get('name', ['image'])[0]
                
                html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
                <meta name="viewport" content="width=device-width,initial-scale=1">
                <title>上传图片</title>
                <style>body{{font-family:sans-serif;padding:20px;text-align:center}}
                .btn{{background:#53CB31;color:#fff;border:none;padding:12px 30px;border-radius:6px;font-size:16px;margin:10px}}
                input[type=file]{{display:none}}#status{{margin:15px;color:#666}}</style></head>
                <body><h2>上传【{name}】图片</h2>
                <input type="file" accept="image/*" id="fileInput">
                <button class="btn" onclick="document.getElementById('fileInput').click()">📷 拍照/选择图片</button>
                <div id="status"></div>
                <script>
                document.getElementById('fileInput').onchange=function(e){{
                    var file=e.target.files[0];if(!file)return;
                    document.getElementById('status').innerText='压缩中...';
                    var reader=new FileReader();
                    reader.onload=function(ev){{
                        var img=new Image();
                        img.onload=function(){{
                            var canvas=document.createElement('canvas');
                            var max=1200;var w=img.width,h=img.height;
                            if(w>max||h>max){{if(w>h){{h=h*max/w;w=max}}else{{w=w*max/h;h=max}}}}
                            canvas.width=w;canvas.height=h;
                            canvas.getContext('2d').drawImage(img,0,0,w,h);
                            canvas.toBlob(function(blob){{
                                document.getElementById('status').innerText='上传中...';
                                var fd=new FormData();fd.append('image',blob,'img.jpg');
                                fetch(location.href,{{method:'POST',body:fd}}).then(r=>r.text()).then(t=>{{
                                    document.body.innerHTML=t;
                                }});
                            }},'image/jpeg',0.8);
                        }};img.src=ev.target.result;
                    }};reader.readAsDataURL(file);
                }};
                </script></body></html>'''
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode())
            
            def do_POST(self):
                content_type = self.headers.get('Content-Type', '')
                if 'multipart/form-data' not in content_type:
                    self.send_response(400)
                    self.end_headers()
                    return
                
                # 解析boundary
                boundary = content_type.split('boundary=')[1].encode()
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len)
                
                # 提取图片数据
                parts = body.split(b'--' + boundary)
                for part in parts:
                    if b'filename=' in part and b'image' in part:
                        # 找到图片数据
                        header_end = part.find(b'\r\n\r\n')
                        if header_end > 0:
                            img_data = part[header_end+4:]
                            if img_data.endswith(b'\r\n'):
                                img_data = img_data[:-2]
                            
                            # 保存图片：旋转90度并裁剪到标准尺寸
                            filename = f"{dialog.drink_name}.png"
                            filepath = os.path.join(img_dir, filename)
                            from PIL import Image
                            pil_img = Image.open(BytesIO(img_data))
                            pil_img = pil_img.rotate(-90, expand=True)  # 顺时针90度
                            
                            # 裁剪为标准尺寸 2028x2680 (宽高比约0.757)
                            target_w, target_h = 2028, 2680
                            target_ratio = target_w / target_h
                            w, h = pil_img.size
                            img_ratio = w / h
                            
                            if img_ratio > target_ratio:
                                # 图片太宽，按高度缩放后裁剪宽度
                                new_h = h
                                new_w = int(h * target_ratio)
                                left = (w - new_w) // 2
                                pil_img = pil_img.crop((left, 0, left + new_w, new_h))
                            else:
                                # 图片太高，按宽度缩放后裁剪高度
                                new_w = w
                                new_h = int(w / target_ratio)
                                top = (h - new_h) // 2
                                pil_img = pil_img.crop((0, top, new_w, top + new_h))
                            
                            pil_img = pil_img.resize((target_w, target_h), Image.LANCZOS)
                            pil_img.save(filepath, 'PNG')
                            
                            dialog.image_received.emit(filename)
                            dialog.upload_success.emit(filename)
                            
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self.end_headers()
                            self.wfile.write(f'<html><body style="text-align:center;padding:50px;font-family:sans-serif"><h2>✓ 上传成功</h2><p>图片已保存为：{filename}</p></body></html>'.encode())
                            return
                
                self.send_response(400)
                self.end_headers()
        
        def run():
            try:
                self.server = http.server.HTTPServer(('0.0.0.0', self.port), UploadHandler)
                self.server.serve_forever()
            except: pass
        
        threading.Thread(target=run, daemon=True).start()
    
    def closeEvent(self, event):
        if self.server:
            self.server.shutdown()
        super().closeEvent(event)


def generate_final_materials(recipe, ice_opt, sugar_opt, toppings=None):
    """根据配方和选项生成最终克重表"""
    pairs = parse_recipe_text(recipe.get("base_materials", ""))
    
    # 冰量
    ice_mult = recipe.get("ice_rule", {}).get(ice_opt, 1.0)
    ice_base = recipe.get("ice_base", 0)
    crushed_ice_base = recipe.get("crushed_ice_base", 0)
    if ice_base > 0:
        pairs.append(("冰", int(ice_base * ice_mult)))
    if crushed_ice_base > 0:
        pairs.append(("碎冰", int(crushed_ice_base * ice_mult)))
    
    # 糖量
    sugar_mult = recipe.get("sugar_rule", {}).get(sugar_opt, 1.0)
    sugar_base = recipe.get("sugar_base", 0)
    if sugar_base > 0:
        pairs.append(("果糖", int(sugar_base * sugar_mult)))
    
    # 小料
    if toppings:
        topping_rule = recipe.get("topping_rule", {})
        for top in toppings:
            gram = topping_rule.get(top, 30)  # 默认30g
            pairs.append((top, gram))
    
    return build_recipe_text(pairs)


class MenuUpdateWidget(QWidget):
    """菜单更新三Tab界面"""
    menu_changed = pyqtSignal()  # 菜单变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.menus = []
        self.recipes = []
        self._init_font()
        self._init_ui()
        self._load_data()
    
    def _init_font(self):
        font_path = _res_path('fonts/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-65-Medium/AlibabaPuHuiTi-3-65-Medium.ttf')
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.app_font = QFont(family, 13)
        else:
            self.app_font = QFont("Microsoft YaHei", 13)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部返回按钮
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton("← 返回设置")
        self.btn_back.setFixedSize(160, 50)
        self.btn_back.setStyleSheet("QPushButton{background:#53CB31;color:white;border-radius:10px;font-size:20px;font-weight:bold;}")
        top_bar.addWidget(self.btn_back)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        
        # Tab控件
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane{border:1px solid #ddd;border-radius:8px;background:white;}
            QTabBar::tab{padding:15px 45px;font-size:20px;min-width:130px;min-height:25px;}
            QTabBar::tab:selected{background:#53CB31;color:white;border-radius:8px 8px 0 0;}
        """)
        
        # Tab A: 菜单管理
        self.tab_menu = self._create_menu_tab()
        self.tabs.addTab(self.tab_menu, "菜单管理")
        
        # Tab B: 配方管理
        self.tab_recipe = self._create_recipe_tab()
        self.tabs.addTab(self.tab_recipe, "配方管理")
        
        # Tab C: 导入/导出
        self.tab_io = self._create_io_tab()
        self.tabs.addTab(self.tab_io, "导入/导出")
        
        layout.addWidget(self.tabs)
        
        # 应用统一字体
        self.setFont(self.app_font)
    
    def _apply_table_style(self, table):
        """统一表格样式"""
        table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8faf8;
                gridline-color: #e0e0e0;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                font-size: 17px;
            }
            QTableWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #e8e8e8;
            }
            QTableWidget::item:selected {
                background-color: #d4edda;
                color: #155724;
            }
            QTableWidget::item:hover {
                background-color: #e8f5e9;
            }
            QHeaderView::section {
                background-color: #53CB31;
                color: white;
                font-weight: bold;
                font-size: 19px;
                padding: 15px 12px;
                border: none;
                border-right: 1px solid #45b028;
            }
            QTableCornerButton::section {
                background-color: #53CB31;
                border: none;
            }
        """)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(50)
        table.setShowGrid(True)
    
    def _create_menu_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_add_menu = QPushButton("+ 新增菜单")
        self.btn_del_menu = QPushButton("删除选中")
        self.btn_save_menu = QPushButton("保存")
        for btn in [self.btn_add_menu, self.btn_del_menu, self.btn_save_menu]:
            btn.setFixedHeight(55)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("QPushButton{background:#53CB31;color:white;border-radius:8px;padding:0 30px;font-size:20px;font-weight:bold;}")
        toolbar.addWidget(self.btn_add_menu)
        toolbar.addWidget(self.btn_del_menu)
        toolbar.addWidget(self.btn_save_menu)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 菜单表格
        self.menu_table = QTableWidget()
        self.menu_table.setColumnCount(8)
        self.menu_table.setHorizontalHeaderLabels(["ID", "名称", "价格", "图片", "杯型", "关联配方ID", "tips", "状态"])
        self.menu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.menu_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.menu_table.cellDoubleClicked.connect(self._on_menu_cell_double_clicked)
        self._apply_table_style(self.menu_table)
        layout.addWidget(self.menu_table)
        
        # 绑定事件
        self.btn_add_menu.clicked.connect(self._on_add_menu)
        self.btn_del_menu.clicked.connect(self._on_del_menu)
        self.btn_save_menu.clicked.connect(self._on_save_all)
        
        return w
    
    def _create_recipe_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_add_recipe = QPushButton("+ 新增配方")
        self.btn_del_recipe = QPushButton("删除选中")
        self.btn_save_recipe = QPushButton("保存")
        self.btn_view_mode = QPushButton("切换视图")
        for btn in [self.btn_add_recipe, self.btn_del_recipe, self.btn_save_recipe, self.btn_view_mode]:
            btn.setFixedHeight(55)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("QPushButton{background:#53CB31;color:white;border-radius:8px;padding:0 30px;font-size:20px;font-weight:bold;}")
        toolbar.addWidget(self.btn_add_recipe)
        toolbar.addWidget(self.btn_del_recipe)
        toolbar.addWidget(self.btn_save_recipe)
        toolbar.addWidget(self.btn_view_mode)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 配方表格
        self.recipe_table = QTableWidget()
        self.recipe_table.setColumnCount(7)
        self.recipe_table.setHorizontalHeaderLabels(["配方ID", "基础材料", "冰基底", "碎冰基底", "糖基底", "冰规则", "糖规则"])
        header = self.recipe_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 配方ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 基础材料
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 冰基底
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 碎冰基底
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 糖基底
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # 冰规则
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # 糖规则
        self.recipe_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._apply_table_style(self.recipe_table)
        layout.addWidget(self.recipe_table)
        
        # 文本视图（默认隐藏）
        self.recipe_text = QTextEdit()
        self.recipe_text.setPlaceholderText("配方JSON文本视图...")
        self.recipe_text.hide()
        layout.addWidget(self.recipe_text)
        
        self._is_table_view = True
        
        # 绑定事件
        self.btn_add_recipe.clicked.connect(self._on_add_recipe)
        self.btn_del_recipe.clicked.connect(self._on_del_recipe)
        self.btn_save_recipe.clicked.connect(self._on_save_all)
        self.btn_view_mode.clicked.connect(self._toggle_recipe_view)
        
        return w
    
    def _create_io_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # 导入/导出区（并排）
        io_box = QHBoxLayout()
        self.btn_import_json = QPushButton("导入菜单+配方包")
        self.btn_import_json.setFixedHeight(55)
        self.btn_import_json.setStyleSheet("QPushButton{background:#53CB31;color:white;border-radius:8px;padding:0 30px;font-size:20px;font-weight:bold;}")
        self.btn_export = QPushButton("导出菜单+配方包")
        self.btn_export.setFixedHeight(55)
        self.btn_export.setStyleSheet("QPushButton{background:#2196F3;color:white;border-radius:8px;padding:0 30px;font-size:20px;font-weight:bold;}")
        io_box.addWidget(self.btn_import_json)
        io_box.addWidget(self.btn_export)
        io_box.addStretch()
        layout.addLayout(io_box)
        
        # 版本/回滚区
        version_box = QHBoxLayout()
        self.lbl_version = QLabel("当前版本: v1")
        self.lbl_version.setStyleSheet("font-size:20px;font-weight:bold;")
        self.btn_rollback = QPushButton("回滚到上一版本")
        self.btn_rollback.setFixedHeight(55)
        self.btn_rollback.setStyleSheet("QPushButton{background:#FF9800;color:white;border-radius:8px;padding:0 30px;font-size:20px;font-weight:bold;}")
        version_box.addWidget(self.lbl_version)
        version_box.addWidget(self.btn_rollback)
        version_box.addStretch()
        layout.addLayout(version_box)
        
        # 日志区
        self.io_log = QTextEdit()
        self.io_log.setReadOnly(True)
        self.io_log.setPlaceholderText("操作日志...")
        self.io_log.setStyleSheet("font-size:18px;")
        self.io_log.setMaximumHeight(250)
        layout.addWidget(self.io_log)
        
        layout.addStretch()
        
        # 绑定事件
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_rollback.clicked.connect(self._on_rollback)
        
        return w
    
    def _on_menu_cell_double_clicked(self, row, col):
        """双击菜单表格单元格，图片列弹出文件选择"""
        if col != 3:  # 只处理图片列(第4列，索引3)
            return
        # 获取饮品名称
        name_item = self.menu_table.item(row, 1)
        drink_name = name_item.text() if name_item else f"饮品{row+1}"
        
        # 选择图片文件
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        # 复制并重命名为饮品名称
        import shutil
        ext = os.path.splitext(path)[1]
        new_filename = f"{drink_name}{ext}"
        dest_path = os.path.join(IMAGE_DIR, new_filename)
        shutil.copy(path, dest_path)
        self.menu_table.setItem(row, 3, QTableWidgetItem(new_filename))

    def _load_data(self):
        self.menus = load_json(MENUS_PATH)
        self.recipes = load_json(RECIPES_PATH)
        self._refresh_menu_table()
        self._refresh_recipe_table()
    
    def _refresh_menu_table(self):
        self.menu_table.setRowCount(len(self.menus))
        for i, m in enumerate(self.menus):
            self.menu_table.setItem(i, 0, QTableWidgetItem(m.get("menu_id", "")))
            self.menu_table.setItem(i, 1, QTableWidgetItem(m.get("name", "")))
            self.menu_table.setItem(i, 2, QTableWidgetItem(str(m.get("base_price", 0))))
            self.menu_table.setItem(i, 3, QTableWidgetItem(m.get("image", "")))
            self.menu_table.setItem(i, 4, QTableWidgetItem(m.get("cup", "")))
            self.menu_table.setItem(i, 5, QTableWidgetItem(m.get("base_recipe_id", "")))
            self.menu_table.setItem(i, 6, QTableWidgetItem(m.get("tips", "")))
            self.menu_table.setItem(i, 7, QTableWidgetItem("启用" if m.get("enabled", True) else "禁用"))
    
    def _refresh_recipe_table(self):
        self.recipe_table.setRowCount(len(self.recipes))
        for i, r in enumerate(self.recipes):
            self.recipe_table.setItem(i, 0, QTableWidgetItem(r.get("recipe_id", "")))
            self.recipe_table.setItem(i, 1, QTableWidgetItem(r.get("base_materials", "")))
            self.recipe_table.setItem(i, 2, QTableWidgetItem(str(r.get("ice_base", 0))))
            self.recipe_table.setItem(i, 3, QTableWidgetItem(str(r.get("crushed_ice_base", 0))))
            self.recipe_table.setItem(i, 4, QTableWidgetItem(str(r.get("sugar_base", 0))))
            self.recipe_table.setItem(i, 5, QTableWidgetItem(str(r.get("ice_rule", {}))))
            self.recipe_table.setItem(i, 6, QTableWidgetItem(str(r.get("sugar_rule", {}))))
    
    def _collect_menu_from_table(self):
        menus = []
        for i in range(self.menu_table.rowCount()):
            m = {
                "menu_id": self.menu_table.item(i, 0).text() if self.menu_table.item(i, 0) else "",
                "name": self.menu_table.item(i, 1).text() if self.menu_table.item(i, 1) else "",
                "base_price": int(self.menu_table.item(i, 2).text() or 0) if self.menu_table.item(i, 2) else 0,
                "image": self.menu_table.item(i, 3).text() if self.menu_table.item(i, 3) else "",
                "cup": self.menu_table.item(i, 4).text() if self.menu_table.item(i, 4) else "",
                "base_recipe_id": self.menu_table.item(i, 5).text() if self.menu_table.item(i, 5) else "",
                "tips": self.menu_table.item(i, 6).text() if self.menu_table.item(i, 6) else "",
                "enabled": (self.menu_table.item(i, 7).text() if self.menu_table.item(i, 7) else "") != "禁用"
            }
            if m["menu_id"]:
                menus.append(m)
        return menus
    
    def _collect_recipe_from_table(self):
        recipes = []
        for i in range(self.recipe_table.rowCount()):
            r = {
                "recipe_id": self.recipe_table.item(i, 0).text() if self.recipe_table.item(i, 0) else "",
                "base_materials": self.recipe_table.item(i, 1).text() if self.recipe_table.item(i, 1) else "",
                "ice_base": int(self.recipe_table.item(i, 2).text() or 0) if self.recipe_table.item(i, 2) else 0,
                "crushed_ice_base": int(self.recipe_table.item(i, 3).text() or 0) if self.recipe_table.item(i, 3) else 0,
                "sugar_base": int(self.recipe_table.item(i, 4).text() or 0) if self.recipe_table.item(i, 4) else 0,
                "ice_rule": {"少冰": 0.5, "正常冰": 1.0, "常温": 0.0},
                "sugar_rule": {"三分糖": 0.3, "五分糖": 0.5, "常规": 1.0}
            }
            if r["recipe_id"]:
                recipes.append(r)
        return recipes
    
    def _validate(self):
        """校验：唯一ID、recipe存在性"""
        errors = []
        menu_ids = [m.get("menu_id") for m in self.menus]
        recipe_ids = {r.get("recipe_id") for r in self.recipes}
        
        # 检查menu_id唯一
        if len(menu_ids) != len(set(menu_ids)):
            errors.append("菜单ID存在重复")
        
        # 检查recipe_id存在
        for m in self.menus:
            rid = m.get("base_recipe_id")
            if rid and rid not in recipe_ids:
                errors.append(f"菜单'{m.get('name')}'关联的配方ID'{rid}'不存在")
        
        return errors
    
    def _on_add_menu(self):
        row = self.menu_table.rowCount()
        self.menu_table.insertRow(row)
        new_id = f"{row+1:03d}"
        self.menu_table.setItem(row, 0, QTableWidgetItem(new_id))
        self.menu_table.setItem(row, 7, QTableWidgetItem("启用"))
    
    def _on_del_menu(self):
        rows = set(idx.row() for idx in self.menu_table.selectedIndexes())
        for row in sorted(rows, reverse=True):
            self.menu_table.removeRow(row)
    
    def _on_add_recipe(self):
        row = self.recipe_table.rowCount()
        self.recipe_table.insertRow(row)
        new_id = f"R{row+1:03d}"
        self.recipe_table.setItem(row, 0, QTableWidgetItem(new_id))
    
    def _on_del_recipe(self):
        rows = set(idx.row() for idx in self.recipe_table.selectedIndexes())
        for row in sorted(rows, reverse=True):
            self.recipe_table.removeRow(row)
    
    def _toggle_recipe_view(self):
        self._is_table_view = not self._is_table_view
        if self._is_table_view:
            # 从文本恢复到表格
            try:
                self.recipes = json.loads(self.recipe_text.toPlainText())
                self._refresh_recipe_table()
            except:
                pass
            self.recipe_table.show()
            self.recipe_text.hide()
        else:
            # 从表格到文本
            self.recipes = self._collect_recipe_from_table()
            self.recipe_text.setPlainText(json.dumps(self.recipes, ensure_ascii=False, indent=2))
            self.recipe_table.hide()
            self.recipe_text.show()
    
    def _on_save_all(self):
        self.menus = self._collect_menu_from_table()
        self.recipes = self._collect_recipe_from_table()
        
        errors = self._validate()
        if errors:
            QMessageBox.warning(self, "校验失败", "\n".join(errors))
            return
        
        # 备份
        self._backup()
        
        save_json(MENUS_PATH, self.menus)
        save_json(RECIPES_PATH, self.recipes)
        
        # 同步到旧格式 tea_drinks_menu.json
        self._sync_to_old_format()
        
        self.menu_changed.emit()
        QMessageBox.information(self, "成功", "菜单和配方已保存")
    
    def _sync_to_old_format(self):
        """将新格式同步到 tea_drinks_menu.json"""
        recipe_map = {r["recipe_id"]: r for r in self.recipes}
        old_list = []
        for m in self.menus:
            if not m.get("enabled", True):
                continue
            rid = m.get("base_recipe_id", "")
            r = recipe_map.get(rid, {})
            # 构建 Recipe 字符串
            recipe_str = f"冰{r.get('ice_base', 0)} 碎冰{r.get('crushed_ice_base', 0)} {r.get('base_materials', '')} 果糖{r.get('sugar_base', 0)}"
            old_list.append({
                "ID": m.get("menu_id", ""),
                "Name": m.get("name", ""),
                "Base Price": m.get("base_price", 0),
                "Sweetness Options": "常规,五分糖,三分糖",
                "Temperature Options": "少冰,正常冰,常温",
                "Size Options": "中杯,大杯",
                "Add-ons": "脆啵啵,芋圆,珍珠,椰果,果冻",
                "Price Calculation": "Final Price = Base Price * Size Factor + Add-ons Price",
                "cup": m.get("cup", "成品杯"),
                "Image": m.get("image", ""),
                "Recipe": recipe_str,
                "tips": m.get("tips", "")
            })
        old_path = _res_path("menu_xlsx/tea_drinks_menu.json")
        save_json(old_path, old_list)
    
    def _backup(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = _res_path(f"menu_xlsx/backup_{ts}")
        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists(MENUS_PATH):
            shutil.copy(MENUS_PATH, os.path.join(backup_dir, "menus_v1.json"))
        if os.path.exists(RECIPES_PATH):
            shutil.copy(RECIPES_PATH, os.path.join(backup_dir, "recipes_v1.json"))
    
    def _on_import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择JSON文件", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            data = load_json(path)
            if isinstance(data, dict) and "menus" in data and "recipes" in data:
                self.menus = data["menus"]
                self.recipes = data["recipes"]
            self._refresh_menu_table()
            self._refresh_recipe_table()
            self._log(f"已从 {path} 导入")
        except Exception as e:
            self._log(f"导入失败: {e}")
    
    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出", "menu_bundle.json", "JSON Files (*.json)")
        if not path:
            return
        bundle = {"menus": self.menus, "recipes": self.recipes, "version": "v1", "exported_at": datetime.now().isoformat()}
        save_json(path, bundle)
        self._log(f"已导出到 {path}")
    
    def _on_rollback(self):
        backup_dir = _res_path("menu_xlsx")
        backups = sorted([d for d in os.listdir(backup_dir) if d.startswith("backup_")], reverse=True)
        if not backups:
            self._log("没有可用的备份")
            return
        latest = backups[0]
        backup_path = os.path.join(backup_dir, latest)
        menu_bak = os.path.join(backup_path, "menus_v1.json")
        recipe_bak = os.path.join(backup_path, "recipes_v1.json")
        if os.path.exists(menu_bak):
            shutil.copy(menu_bak, MENUS_PATH)
        if os.path.exists(recipe_bak):
            shutil.copy(recipe_bak, RECIPES_PATH)
        self._load_data()
        self._log(f"已回滚到 {latest}")
    
    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.io_log.append(f"[{ts}] {msg}")


def get_recipe_by_id(recipe_id):
    """根据recipe_id获取配方"""
    recipes = load_json(RECIPES_PATH)
    for r in recipes:
        if r.get("recipe_id") == recipe_id:
            return r
    return None

def get_menu_by_id(menu_id):
    """根据menu_id获取菜单"""
    menus = load_json(MENUS_PATH)
    for m in menus:
        if m.get("menu_id") == menu_id:
            return m
    return None

def get_final_recipe_for_order(menu_id, ice_opt, sugar_opt, toppings=None):
    """为订单生成最终配方克重表"""
    menu = get_menu_by_id(menu_id)
    if not menu:
        return None
    recipe = get_recipe_by_id(menu.get("base_recipe_id"))
    if not recipe:
        return None
    return generate_final_materials(recipe, ice_opt, sugar_opt, toppings)
