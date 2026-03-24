# -*- coding: utf-8 -*-
import math
import re
import time
import serial
from serial import SerialException

from PyQt5.QtCore import QThread, pyqtSignal, QTimer


class ConduitSerialThread(QThread):
    """
    ESP32 串口通信线程

    接收：
      - wD:1, 2, 3          -> weights_info(list[int])
      - mA:0, 1, 0          -> mA_info(list[int])
      - a..x                 -> material_detected(code, material_name)
      - 1..5: value          -> material_detail_detected(dict)  (凑齐1~5后一次发)

    发送：
      - send_data("...\\n")
      - prepare_once_send("...")  // 兼容旧工程：设置一次性发送，run 内发

    兼容旧工程控制接口（供主程序 connect）：
      - conduit_serial_out(operation_name, select_conduit_bean, context)
      - conduit_serial_one(operation_name, select_conduit_bean)
      - conduit_serial_all(operation_name, conduit_beans)
      - conduit_serial_clean_begin(conduit_beans, T)
      - conduit_serial_clean_stop()
      - conduit_serial_clean_pause(is_continue)
      - conduit_serial_clean_time(minutes, seconds)
    """

    # 你工程里已有的信号（保持命名不变）
    auto_clear_close = pyqtSignal()
    auto_calibration_close = pyqtSignal()
    auto_material_close = pyqtSignal()
    mA_info = pyqtSignal(list)
    weights_info = pyqtSignal(list)
    temp_changed = pyqtSignal(float)   # 新增：温度信号
    temp_finished = pyqtSignal()          # 新增：加热完成

    # 新增：材料识别信号
    material_detected = pyqtSignal(str, str)      # code, material_name
    material_detail_detected = pyqtSignal(dict)   # {code, material_name, prod_date, expiry_date, origin, sku}

     # 出冰模块状态信号
    ice_locking = pyqtSignal(str)   # 正在尝试自动摆脱
    ice_locked = pyqtSignal()       # 自动摆脱失败，已锁死
    ice_unlock_finished = pyqtSignal()  # 自动摆脱完成

    # 字母码 -> 材料名（按需扩充）
    MATERIAL_MAP = {
        "a": "茉莉绿茶",
        "b": "蜂蜜",
        "c": "四季春茶",
        "d": "柠檬果蜜",
        "e": "啵啵",
        "f": "草莓果酱",
        "g": "蔗糖",
        "h": "橙柚果酱",
        "i": "奇异果汁",
        "j": "水蜜桃酱",
        "k": "草莓酱",
        "l": "黑糖浆",
        "m": "黄桃果酱",
        "n": "葡萄汁",
        "o": "波波",
        "p": "椰果",
        "q": "奶浆",
        "r": "冰块",
        "s": "寒天晶球",
        "t": "珍珠",
        "u": "椰果粒",
        "v": "红豆",
        "w": "奶盖",
        "x": "芝士酱",
    }

    # —— 旧工程里存在的字段（保持）——
    one_value = 50
    all_value = [999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999]
    thous_value = [10000, 20000, 30000]
    is_clean = False
    conduit_work_number = 0
    conduit_clean_l_date = 0
    dynamic_vars = {}
    is_dynamic = True
    k = 0
    command_three_groups = []
    device_name_found = pyqtSignal(str)

    def request_device_name(self):
        """
        主线程在未获得设备名时调用；为了兼容不同固件，这里连发几种常见写法。
        ESP32 收到任意一种后，回传 'device_name:XXX' 即可。
        """
        self.send_data("device_name?")
    # ========== 兼容老工程的字符串转换工具 ==========
    def convert_to_commands(self, input_str: str) -> str:
        """
        把 "1#2#3#" 这种变成 "ABC"
        """
        parts = input_str.split('#')
        res, base = "", 64  # 'A' = 65
        for i in range(len(parts) - 1):  # 最后一段通常是空
            p = parts[i].strip()
            if p.isdigit():
                res += chr(int(p) + base)
        res += parts[-1]  # 如果最后一段不是空，拼上
        return res

    def conversion_command_str(self, conduit_name_list):
        """
        将 ['1#','2#'] 或带 get_shield/get_conduit 的对象列表 -> 'AB...'
        """
        s = ""
        if not conduit_name_list:
            return s
        if all(hasattr(x, 'get_shield') and hasattr(x, 'get_conduit') for x in conduit_name_list):
            for it in conduit_name_list:
                if str(it.get_shield()) != "2":  # 2=屏蔽
                    s += self.convert_to_commands(str(it.get_conduit()))
        elif all(isinstance(x, str) for x in conduit_name_list):
            for it in conduit_name_list:
                s += self.convert_to_commands(it)
        return s

    def conversion_command_str_num(self, conduit_name_list, value=None):
        """
        将 ['1#','2#'] -> 'A050B050'（value 左补零3位）
        """
        s = ""
        v3 = str(0 if value is None else int(value)).zfill(3)
        if not conduit_name_list:
            return s
        if all(hasattr(x, 'get_shield') and hasattr(x, 'get_conduit') for x in conduit_name_list):
            for it in conduit_name_list:
                if str(it.get_shield()) != "2":
                    s += self.convert_to_commands(str(it.get_conduit())) + v3
        elif all(isinstance(x, str) for x in conduit_name_list):
            for it in conduit_name_list:
                s += self.convert_to_commands(it) + v3
        return s

    def map_values_to_conduits(self, letters: str) -> str:
        """把 'AB' -> 'A050B100'，数值来自 all_value 下标"""
        res = []
        for ch in letters:
            idx = ord(ch) - ord('A')
            if 0 <= idx < len(self.all_value):
                res.append(f"{ch}{int(self.all_value[idx]):03d}")
        return ''.join(res)

    def split_conduit_str(self, conduit_str: str, group_size: int, size: int):
        """按 size=4（形如 A050）分组，每组 group_size 个"""
        groups, cur, cnt = [], "", 0
        for i in range(0, len(conduit_str), size):
            cur += conduit_str[i:i + size]
            cnt += 1
            if cnt == group_size:
                groups.append(cur)
                cur, cnt = "", 0
        if cur:
            groups.append(cur)
        return groups

    def send_in_command(self, conduit_groups, interval: float):
        """分组间隔发送"""
        def _send_next():
            if conduit_groups:
                g = conduit_groups.pop(0)
                self.send_data(g)
                QTimer.singleShot(int(interval * 1000), _send_next)
        _send_next()

    # ========== 兼容主程序调用的“出/退/满管/一键满管/清洗”接口 ==========
    def conduit_serial_out(self, operation_name, select_conduit_bean, context):
        """
        operation_name: '出料' / '退料'
        select_conduit_bean: ['1#','2#'] 或对象数组(需有 get_shield/get_conduit)
        context: 数值（克）
        """
        cmd = self.conversion_command_str_num(select_conduit_bean, context)
        if not cmd:
            print("[compat] 空命令，忽略")
            return
        if str(operation_name) == '退料':
            cmd = '-' + cmd
        self.prepare_once_send(cmd)

    def conduit_serial_one(self, operation_name, select_conduit_bean):
        if str(operation_name) != '单管满管':
            return
        letters = self.conversion_command_str(select_conduit_bean)  # 'AB...'
        cmd = self.map_values_to_conduits(letters)                   # 'A050B050...'
        if cmd:
            self.prepare_once_send(cmd)

    def conduit_serial_all(self, operation_name, conduit_beans):
        if str(operation_name) != '一键满管':
            return
        letters = self.conversion_command_str(conduit_beans)
        cmd = self.map_values_to_conduits(letters)
        if not cmd:
            return
        groups = self.split_conduit_str(cmd, group_size=3, size=4)
        self.send_in_command(groups, interval=5)

    def conduit_serial_clean_begin(self, conduit_beans, T):
        self.is_clean = True
        letters = self.conversion_command_str(conduit_beans)
        self.conduit_work_number = max(0, len(letters))
        print(f"[clean] begin: work_number={self.conduit_work_number}, T={T}")

    def conduit_serial_clean_stop(self):
        self.is_clean = False
        self.dynamic_vars.clear()
        self.is_dynamic = True
        self.k = 0
        self.send_data('stop')
        print("[clean] stop")

    def conduit_serial_clean_pause(self, is_continue):
        self.is_clean = bool(is_continue)
        if not self.is_clean:
            self.send_data('stop')
        print(f"[clean] {'resume' if self.is_clean else 'pause'}")

    def conduit_serial_clean_time(self, minutes, seconds):
        try:
            self.conduit_clean_l_date = int(minutes) * 60 + int(seconds)
        except Exception:
            self.conduit_clean_l_date = 0
        print(f"[clean] set time {minutes}:{seconds}")

    # ========== 线程 & 串口 ==========
    def __init__(self, port, parent=None):
        super().__init__(parent)
        self.port = port
        self.serial = None
        self.running = False

        # 连接与重连控制
        self._last_rx_ts = time.time()
        self._last_tx_ts = 0.0
        self._rx_timeout_sec = 6.0
        self._reopen_delay = 0.5

        # 一次性发送兼容标记
        self.is_open = False
        self.execute_once = False
        self.new_conduit_str_num = ""
        self.new_conduit_str = ""
         # ★ 新增：制作开关（主程序会调用 make_tee_open/stop 来控制）
        self.make_running = False

        # 缓存
        self._matpkt = {}      # 资料包缓存：{1:...,2:...,3:...,4:...,5:...}

    def prepare_once_send(self, msg: str):
        """兼容旧流程：设置一次性发送，下一个循环发送"""
        self.new_conduit_str_num = str(msg)
        self.is_open = True
        self.execute_once = True

    def send_data(self, data):
        if self.serial and self.serial.is_open:
            try:
                s = f"{data}\n" if not str(data).endswith("\n") else str(data)
                print("输出配方：")
                print(f"[Serial=>] {s.strip()}")
                self.serial.write(s.encode("utf-8"))
                self._last_tx_ts = time.time()
            except Exception as e:
                print(f"[Serial] write error: {e}")
                self._close_serial()

    def _open_serial(self) -> bool:
        try:
            self.serial = serial.Serial(self.port, 9600, timeout=1)
            print(f"[Serial] Connected to {self.port}")

            # 复位/唤醒设备（应对休眠/拔插后不响应）
            try:
                self.serial.dtr = False
                self.serial.rts = False
                time.sleep(0.05)
                self.serial.dtr = True
                self.serial.rts = True
            except Exception:
                pass

            self._last_rx_ts = time.time()
            return True
        except Exception as e:
            print(f"[Serial] open error: {e}")
            self.serial = None
            return False

    def _close_serial(self):
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception:
                pass
        self.serial = None

    def run(self):
        self.running = True
        while self.running:
            try:
                # 打开串口
                if self.serial is None or not self.serial.is_open:
                    if not self._open_serial():
                        time.sleep(self._reopen_delay)
                        continue

                # 兼容一次性发送
                if self.is_open and self.execute_once:
                    self.is_open = False
                    self.execute_once = False
                    self.send_data(self.new_conduit_str_num)

                line = ""
                if self.serial.is_open:
                    try:
                        line = self.serial.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            print(f"[Serial<=] {line}")
                            self._last_rx_ts = time.time()
                    except Exception as e:
                        print(f"[Serial] decode err: {e}")
                        line = ""
                        self._close_serial()

                if line:

                    m = re.match(r'^\s*device_name\s*[:=]\s*(.+)\s*$', line, re.IGNORECASE)
                    if m:
                        name = m.group(1).strip()
                        self.device_name_found.emit(name)   # 通知主线程
                        time.sleep(0.01)
                        continue

                    # 0) 温度：temp:xx.xx 或 temp = xx.xx
                    m = re.match(r'^(?:temp)\s*[:=]\s*(-?\d+(?:\.\d+)?)$', line, re.IGNORECASE)
                    if m:
                        try:
                            self.temp_changed.emit(float(m.group(1)))
                        except Exception:
                            pass
                        time.sleep(0.01)
                        continue
                    if re.match(r'^\s*temp[_\s-]*finish\s*$', line, re.IGNORECASE):
                        self.temp_finished.emit()
                        time.sleep(0.01)
                        continue

                    # 出冰/碎冰模块卡冰状态：
                    #   crushed_ice_locking  -> 碎冰模块堵
                    #   ice_out_locking      -> 出冰模块堵
                    #   locking              -> 两个模块都堵（兼容旧协议）
                    low = line.strip().lower()

                    if low in ("crushed_ice_locking", "ice_out_locking", "locking"):
                        if low == "crushed_ice_locking":
                            kind = "crushed"
                        elif low == "ice_out_locking":
                            kind = "ice_out"
                        else:
                            # 兼容老固件的 "locking"：默认两个模块都堵
                            kind = "both"

                        try:
                            self.ice_locking.emit(kind)
                        except Exception:
                            pass
                        time.sleep(0.01)
                        continue

                    if low == "locked":
                        # 出冰模块被冰卡住，自动摆脱失败
                        try:
                            self.ice_locked.emit()
                        except Exception:
                            pass
                        time.sleep(0.01)
                        continue

                    if low == "unlock_finish":
                        # 出冰模块自动摆脱完成
                        try:
                            self.ice_unlock_finished.emit()
                        except Exception:
                            pass
                        time.sleep(0.01)
                        continue


                    # 1) 资料包行：1..5: value
                    if self._handle_material_packet_line(line):
                        time.sleep(0.01)
                        continue

                    # 2) 单字母材料码
                    if len(line) == 1 and line.isalpha():
                        code = line.lower()
                        if code in self.MATERIAL_MAP:
                            name = self.MATERIAL_MAP[code]
                            self.material_detected.emit(code, name)
                            time.sleep(0.01)
                            continue

                    # 3) wD/mA 列表
                    self._handle_wd_ma_line(line)
                 
                # 读取到一行 line 之后：



                # 无数据超时 -> 触发重连（应对休眠/拔插后设备不响应）
                if (time.time() - self._last_rx_ts) > self._rx_timeout_sec:
                    print("[Serial] no data timeout, reopen serial")
                    self._close_serial()
                    time.sleep(self._reopen_delay)
                else:
                    time.sleep(0.01)

            except (SerialException, PermissionError) as e:
                print(f"[Serial] error: {e}")
                self._close_serial()
                time.sleep(self._reopen_delay)

        # 退出清理
        self._close_serial()
        print("[Serial] closed")

    # ========== 解析工具 ==========
    def _handle_material_packet_line(self, line: str) -> bool:
        """
        解析形如：
            1:a
            2:2025.8.21
            3:2026.8.21
            4:GuangDong,China
            5:626565524
        返回 True 表示此行属于资料包并已处理
        """
        m = re.match(r'^(\d+)\s*[:\.：]\s*(.+)$', line)
        if not m:
            return False

        idx = int(m.group(1))
        val = m.group(2).strip()
        if 1 <= idx <= 5:
            self._matpkt[idx] = val

            if all(k in self._matpkt for k in (1, 2, 3, 4, 5)):
                code = (self._matpkt[1] or "").lower()
                material_name = self.MATERIAL_MAP.get(code, code)
                pkt = {
                    "code": code,
                    "material_name": material_name,
                    "prod_date": self._matpkt[2],
                    "expiry_date": self._matpkt[3],
                    "origin": self._matpkt[4],
                    "sku": self._matpkt[5],
                }
                self.material_detail_detected.emit(pkt)
                self._matpkt.clear()
        return True

    def _handle_wd_ma_line(self, line: str):
        """
        解析 wD / mA 两种列表格式：
          wD:1, 2, 3
          mA:0, 1, 0
        """
        if not re.match(r'^(wD|mA)\s*:\s*-?\d+(?:\s*,\s*-?\d+)*$', line):
            return
        prefix, vals = line.split(':', 1)
        nums = []
        for v in vals.split(','):
            v = v.strip()
            try:
                nums.append(int(v))
            except Exception:
                pass
        if prefix == 'wD':
            self.weights_info.emit(nums)
        elif prefix == 'mA':
            self.mA_info.emit(nums)

    # ========== 线程控制 ==========
    def stop(self):
        self.running = False
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception:
                pass
    def make_tee_open(self):
        """开始制作：打开制作开关（主程序 notice_thread_tee_begin 会连到这）"""
        self.make_running = True
        print("[make] start")

    def make_tee_stop(self):
        """停止制作：关闭制作开关并向下位机发送 stop（主程序 notice_thread_tee_stop 会连到这）"""
        self.make_running = False
        self.send_data('stop')
        print("[make] stop")
