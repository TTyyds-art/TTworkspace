# import sys
# import serial
# import time
# from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
# from PyQt5.QtCore import QObject, pyqtSignal, QThread
# from serial import SerialException



# class SerialThread(QThread):
#     data_received = pyqtSignal(str)
#     result_info = pyqtSignal(list)

#     def __init__(self, port):
#         super().__init__()
#         self.port = port
#         self.serial = None
#         self.running = False

#     def run(self):
#         self.running = True
#         while self.running:
#             try:
#                 if self.serial is None or not self.serial.is_open:
#                     self.serial = serial.Serial(self.port, 115200)
#                     print(f"Connected to {self.port}")

#                 if self.serial.in_waiting > 0:
#                     data = self.serial.read(self.serial.in_waiting)
#                     # print(f"Received data: {data}")
#                     try:
#                         chinese_str = data.decode('utf-8')
#                         print(f'chinese_str: {chinese_str}')
#                     except UnicodeDecodeError:
#                         chinese_str = data.decode('utf-8', errors='ignore')
#                     if chinese_str:
#                         self.data_received.emit(chinese_str)

#                 time.sleep(0.1)
#             except (SerialException, PermissionError) as e:
#                 print(f"Serial error: {e}")
#                 self.running = False  # 停止线程
#         if self.serial and self.serial.is_open:
#             self.serial.close()
#             print("Serial port closed")
        
#     def send_data(self, data):
#         if self.serial and self.serial.is_open:
#             self.serial.write(f"{data}\n".encode('utf-8'))

#     def stop(self):
#         self.running = False

#         # 尝试关闭串口
#         if self.serial and self.serial.is_open:
#             try:
#                 self.serial.close()
#                 print("串口已成功关闭")
#             except Exception as e:
#                 print(f"关闭串口时出现异常: {e}")

#         # 退出线程的事件循环
#         self.quit()

#         # 等待线程终止，但设置一个超时时间以防止卡死
#         if not self.wait(5000):  # 等待最多5秒
#             print("线程未能在规定时间内终止")

import sys
import serial
import time
import re
import json
from PyQt5.QtCore import pyqtSignal, QThread
from serial import SerialException

                    # data_to_send = [
                    #     {
                    #         "product_name": "草莓奶昔",
                    #         "product_sugar": "常规",
                    #         "product_quantity": "中杯",
                    #         "product_ice": "少冰",
                    #         "product_simp": "脆啵啵,芋圆",
                    #         "unit_price": "18.0",
                    #         "recipe": "C200D50"
                    #     }
                    # ]
class SerialThread(QThread):
    data_received = pyqtSignal(str)
    camera_info = pyqtSignal(str) #用于监听扫码数据

    def __init__(self, port):   
        super().__init__()
        self.port = port
        self.serial = None
        self.running = False
        self._retry_delay = 0.5
        
    def run(self):
        self.running = True
        while self.running:
            try:
                if self.serial is None or not self.serial.is_open:
                    self.serial = serial.Serial(self.port, 9600, timeout=0.2)
                    print(f"Connected to {self.port}")

                # if self.serial.in_waiting > 0:
                #     data = self.serial.read(self.serial.in_waiting)
                #     print(f"Received data: {data}")

                #     response = json.dumps(data, ensure_ascii=False)  #转为json字符串
                #     # print(f"Received data: {data}")
                #     try:
                #         response = data.decode('utf-8', errors='ignore')
                #         print(f'response:{response}')
                #     except UnicodeDecodeError:
                #         print(f"解码失败: {e}")
                #     pattern = re.compile(r'^\[.*\]$') #判断是否是字典数据
                #     if re.match(pattern, response):
                #         self.camera_info.emit(response)
                #     if response:
                #         self.data_received.emit(response)
                try:
                    waiting = self.serial.in_waiting
                except (SerialException, PermissionError, OSError) as e:
                    print(f"Serial read error(in_waiting): {e}")
                    try:
                        if self.serial and self.serial.is_open:
                            self.serial.close()
                            print("Serial port closed")
                    except Exception as close_e:
                        print(f"关闭串口时出现异常: {close_e}")
                    self.serial = None
                    time.sleep(self._retry_delay)
                    continue

                if waiting > 0:
                    # 从串口读取数据
                    try:
                        data = self.serial.read(waiting)
                    except (SerialException, PermissionError, OSError) as e:
                        print(f"Serial read error(read): {e}")
                        try:
                            if self.serial and self.serial.is_open:
                                self.serial.close()
                                print("Serial port closed")
                        except Exception as close_e:
                            print(f"关闭串口时出现异常: {close_e}")
                        self.serial = None
                        time.sleep(self._retry_delay)
                        continue
                    # print(f"Received raw data: {data}")

                    try:
                        # 尝试将 bytes 数据解码为字符串
                        response = data.decode('utf-8', errors='ignore').strip()  # 去除多余的空格和换行符
                        # print(f"Decoded response: {response}")

                        # 尝试将字符串解析为 JSON 对象
                        try:
                            json_data = json.loads(response)  # 将字符串解析为 JSON
                            print(f"Parsed JSON data: {json_data}")
                            # 如果需要将 JSON 数据发送到其他部分
                            # self.data_received.emit(json_data)
                        except json.JSONDecodeError as e:
                            print(f"JSON 解析失败: {e}")
                            # 如果数据不是合法的 JSON，直接发送原始字符串
                            self.data_received.emit(response)

                        # 判断是否是字典数据（假设字典数据用 {} 包裹）
                        pattern = re.compile(r'^\{.*\}$')  # 匹配 JSON 对象格式
                        if re.match(pattern, response):
                            self.camera_info.emit(response)

                    except UnicodeDecodeError as e:
                        print(f"解码失败: {e}")
                    
                time.sleep(0.1)
            except (SerialException, PermissionError, OSError) as e:
                print(f"Serial error: {e}")
                try:
                    if self.serial and self.serial.is_open:
                        self.serial.close()
                        print("Serial port closed")
                except Exception as close_e:
                    print(f"关闭串口时出现异常: {close_e}")
                self.serial = None
                time.sleep(self._retry_delay)
                continue
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Serial port closed")

    def send_data(self, data):
        # print("data")
        if self.serial and self.serial.is_open:
            print(f'data:{data}')
            self.serial.write(f"{data}\n".encode('utf-8'))
            
    def stop(self):
        self.running = False

        # 尝试关闭串口
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                print("串口已成功关闭")
            except Exception as e:
                print(f"关闭串口时出现异常: {e}")

        # 退出线程的事件循环
        self.quit()

        # 等待线程终止，但设置一个超时时间以防止卡死
        if not self.wait(5000):  # 等待最多5秒
            print("线程未能在规定时间内终止")

