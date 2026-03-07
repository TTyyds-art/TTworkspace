# import cv2
# import time
# import numpy
# from pyzbar import pyzbar
# from PyQt5.QtCore import QThread, pyqtSignal


# class CameraThread(QThread):
#     result_image = pyqtSignal(numpy.ndarray)  # 信号：传递处理后的帧
#     result_clear = pyqtSignal()
#     close_thread_signal = pyqtSignal()  # 信号：用于接收外部线程关闭请求

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.is_running = True

#     def run(self):
#         # 打开摄像头
#         cap = cv2.VideoCapture(0)
#         if not cap.isOpened():
#             print('无法打开摄像头')
#             self.result_clear.emit()
#             return

#         print('摄像头已打开，开始扫码')
#         code_scanned = False
#         try:
#             while self.is_running and not code_scanned:
#                 ret, frame = cap.read()
#                 if not ret:
#                     print('无法读取摄像头帧')
#                     break

#                 # 获取原始帧尺寸
#                 original_height, original_width = frame.shape[:2]

#                 # 目标尺寸
#                 target_width = 640
#                 target_height = 237

#                 # 计算裁剪区域
#                 crop_x = (original_width - target_width) // 2  # 水平居中裁剪
#                 crop_y = (original_height - target_height) // 2  # 垂直居中裁剪

#                 # 确保裁剪区域合法
#                 crop_x = max(crop_x, 0)
#                 crop_y = max(crop_y, 0)

#                 # 裁剪图像
#                 cropped_frame = frame[crop_y:crop_y + target_height, crop_x:crop_x + target_width]

#                 # 检查裁剪结果
#                 if cropped_frame.shape[0] != target_height or cropped_frame.shape[1] != target_width:
#                     print(f"裁剪失败：目标尺寸不匹配 {cropped_frame.shape}")
#                     break

#                 # 发送裁剪后的帧
#                 self.result_image.emit(cropped_frame)

#                 # 解码二维码
#                 barcodes = pyzbar.decode(frame)
#                 for barcode in barcodes:
#                     # 提取二维码数据
#                     barcode_data = barcode.data.decode('utf-8')
#                     print(f'扫码成功：{barcode_data}')

#                     # 获取二维码位置
#                     (x, y, w, h) = barcode.rect

#                     # 在裁剪后的图像上绘制矩形框
#                     x, y, w, h = x - crop_x, y - crop_y, w, h  # 更新坐标到裁剪后的范围
#                     if 0 <= x < target_width and 0 <= y < target_height:
#                         cv2.rectangle(cropped_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

#                 # 发送处理后的帧
#                 self.result_image.emit(cropped_frame)
#         finally:
#             # 关闭摄像头
#             cap.release()
#             cv2.destroyAllWindows()
#             print('摄像头已关闭')

#         self.result_clear.emit()

#     def close_thread(self):
#         """关闭线程"""
#         self.is_running = False
#         self.quit()
#         self.wait()


import cv2
import numpy
from pyzbar import pyzbar
from PyQt5.QtCore import QThread, pyqtSignal


class CameraThread(QThread):
    result_image = pyqtSignal(numpy.ndarray)  # 信号：传递处理后的帧
    result_clear = pyqtSignal()
    close_thread_signal = pyqtSignal()  # 信号：用于接收外部线程关闭请求

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True

    def create_rounded_mask(self, width, height, radius):
        """创建一个完全白色且具有圆角的遮罩"""
        mask = numpy.ones((height, width, 3), dtype=numpy.uint8) * 255

        # 创建一个黑色背景，用于定义圆角区域
        black_background = numpy.zeros((height, width), dtype=numpy.uint8)

        # 绘制中间的矩形部分
        cv2.rectangle(black_background, (radius, 0), (width - radius, height), 255, -1)
        cv2.rectangle(black_background, (0, radius), (width, height - radius), 255, -1)

        # 绘制四个圆角
        cv2.circle(black_background, (radius, radius), radius, 255, -1)
        cv2.circle(black_background, (width - radius, radius), radius, 255, -1)
        cv2.circle(black_background, (radius, height - radius), radius, 255, -1)
        cv2.circle(black_background, (width - radius, height - radius), radius, 255, -1)

        # 使用圆角定义的黑色背景创建白色遮罩
        for i in range(3):
            mask[:, :, i] = cv2.bitwise_and(mask[:, :, i], black_background)

        return mask

    def apply_rounded_corners(self, frame, mask):
        """将圆角遮罩应用到图像上，使遮罩部分完全变成白色"""
        white_background = numpy.ones_like(frame) * 255  # 创建全白背景
        frame_with_mask = cv2.bitwise_and(frame, mask)  # 将原始图像应用遮罩
        inverted_mask = cv2.bitwise_not(mask[:, :, 0])  # 创建反向遮罩
        white_corners = cv2.bitwise_and(white_background, white_background, mask=inverted_mask)  # 白色圆角区域
        result = cv2.add(frame_with_mask, white_corners)  # 合并图像和白色圆角
        return result

    def run(self):
        # 打开摄像头
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print('无法打开摄像头')
            return

        print('摄像头已打开，开始扫码')
        code_scanned = False
        try:
            while self.is_running and not code_scanned:
                ret, frame = cap.read()
                if not ret:
                    print('无法读取摄像头帧')
                    break

                # 获取原始帧尺寸
                original_height, original_width = frame.shape[:2]

                # 目标尺寸
                target_width = 640
                target_height = 237
                radius = 15 #圆角半径

                # 计算裁剪区域
                crop_x = (original_width - target_width) // 2  # 水平居中裁剪
                crop_y = (original_height - target_height) // 2  # 垂直居中裁剪

                # 确保裁剪区域合法
                crop_x = max(crop_x, 0)
                crop_y = max(crop_y, 0)

                # 裁剪图像
                cropped_frame = frame[crop_y:crop_y + target_height, crop_x:crop_x + target_width]

                # 检查裁剪结果
                if cropped_frame.shape[0] != target_height or cropped_frame.shape[1] != target_width:
                    print(f"裁剪失败：目标尺寸不匹配 {cropped_frame.shape}")
                    break

                # 创建圆角遮罩
                mask = self.create_rounded_mask(target_width, target_height, radius)

                # 应用圆角遮罩
                rounded_frame = self.apply_rounded_corners(cropped_frame, mask)

                # 解码二维码
                barcodes = pyzbar.decode(frame)
                for barcode in barcodes:
                    # 提取二维码数据
                    barcode_data = barcode.data.decode('utf-8')
                    print(f'扫码成功：{barcode_data}')

                    # 获取二维码位置
                    (x, y, w, h) = barcode.rect

                    # 在裁剪后的图像上绘制矩形框
                    x, y, w, h = x - crop_x, y - crop_y, w, h  # 更新坐标到裁剪后的范围
                    if 0 <= x < target_width and 0 <= y < target_height:
                        cv2.rectangle(rounded_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # 发送处理后的帧
                self.result_image.emit(rounded_frame)
        finally:
            # 关闭摄像头
            cap.release()
            cv2.destroyAllWindows()
            print('摄像头已关闭')

        self.result_clear.emit()

    def close_thread(self):
        """关闭线程"""
        self.is_running = False
        self.quit()
        self.wait()
