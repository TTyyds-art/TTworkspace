from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QPainterPath, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QLabel
import sys
import os

def resource_path(relative_path):
    """ 获取资源的绝对路径 """
    if hasattr(sys, '_MEIPASS'):
        # 打包后的运行环境
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class QBarPainter(QWidget):
    def __init__(self, margin, max_value, y_value, r_value, is_shield, conduit_id=None, parent=None):
        super().__init__(parent)
        self.margin = margin
        self.setStyleSheet("border-radius: 16px;")
        self.max_value = max_value
        self.y_value = y_value
        self.r_value = r_value
        self.is_shield = is_shield
        self.conduit_id = conduit_id  # 通道ID，用于判断是否为冰/碎冰通道
        self.icon_label = QLabel(self)
        # self.icon = QPixmap(r'drawable\icon_conduit_bar_shield.png')  # 替换为你的图标路径
        self.icon = QPixmap(resource_path(r'drawable\icon_conduit_bar_shield.png'))
        self.icon_label.setPixmap(self.icon)
        self.icon_label.setFixedSize(self.icon.size())
        self.icon_label.setHidden(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if int(self.margin) >= 0:
            p_value = int((int(self.margin) / int(self.max_value)) * 100)
        else:
            p_value = 0

        # 设置条形柱的动态参数
        margin_top = 8  # 距顶部的固定距离
        margin_bottom = 8  # 距底部的固定距离
        margin_side = 0  # 距左右两侧的固定距离

        bar_width = self.width() - 2 * margin_side  # 条形柱宽度
        bar_height = self.height() - margin_top - margin_bottom  # 条形柱高度
        bar_value = int(p_value)  # 条形柱的值（0-100）
        green_color = QColor("#53CB31")  # 条形柱的颜色
        orange_color = QColor("#FF9A18")
        red_color = QColor("#FF534A")

        # 条形柱的左上角坐标
        left = margin_side
        step = bar_value * bar_height / 100  # 根据值计算实际条形高度

        # 冰/碎冰通道(1#/2#)始终显示余量，不显示屏蔽图标
        is_ice_channel = self.conduit_id in ('1#', '2#')
        show_bar = (self.is_shield == '1') or is_ice_channel

        if show_bar:
            # 绘制条形柱
            if self.margin > self.y_value:
                # 绿
                self.drawBar_green(left, margin_top, bar_width, bar_height, step, green_color, painter)
            elif self.r_value < self.margin <= self.y_value:
                # 橙色
                self.drawBar_orange(left, margin_top, bar_width, bar_height, step, orange_color, painter)
            elif 0 <= self.margin <= self.r_value:
                # 红
                self.drawBar_red(left, margin_top, bar_width, bar_height, step, red_color, painter)
            else:
                # 红
                self.drawBar_red(left, margin_top, bar_width, bar_height, step, red_color, painter)
        else:
            self.icon_label.setHidden(False)
            self.drawBar(left, margin_top, bar_width, bar_height, step, red_color, painter)
            self.icon_label.move(int(self.geometry().width() / 2) - 10, int(self.geometry().height() / 2) - 10)

    def drawBar(self, left, margin_top, bar_width, bar_height, step, red_color, painter):
        # 绘制背景矩形，四个角为圆角
        painter.save()
        # 创建圆角矩形路径
        radius = 8  # 圆角半径
        rounded_rect_path = QPainterPath()
        bg_rect = QRectF(left, margin_top, bar_width, bar_height)
        rounded_rect_path.addRoundedRect(bg_rect, radius, radius)  # 添加圆角矩形路径
        bg_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0.5, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        painter.fillPath(rounded_rect_path, bg_linear_gradient)
        painter.restore()

    def drawBar_green(self, left, margin_top, bar_width, bar_height, step, color, painter):
        # 绘制底部椭圆
        painter.save()
        bottom_rect = QRectF(left, margin_top + bar_height - 10, bar_width, 15)
        bottom_linear = QLinearGradient(left, 0, left + bar_width, 0)  # 水平方向渐变
        bottom_linear.setColorAt(0, color)
        bottom_linear.setColorAt(0.5, QColor("#75F152"))
        bottom_linear.setColorAt(1, color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bottom_linear)
        painter.drawEllipse(bottom_rect)
        painter.restore()

        # 绘制背景矩形，四个角为圆角
        painter.save()
        # 创建圆角矩形路径
        radius = 8  # 圆角半径
        rounded_rect_path = QPainterPath()
        bg_rect = QRectF(left, margin_top, bar_width, bar_height)
        rounded_rect_path.addRoundedRect(bg_rect, radius, radius)  # 添加圆角矩形路径
        bg_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0.5, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        painter.fillPath(rounded_rect_path, bg_linear_gradient)
        painter.restore()

        # # 绘制中间部分矩形
        painter.save()
        mid_rect = QRectF(left, margin_top + bar_height - step, bar_width, step)
        mid_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)  # 水平方向渐变
        mid_linear_gradient.setColorAt(0, color)
        mid_linear_gradient.setColorAt(0.5, QColor("#75F152"))
        mid_linear_gradient.setColorAt(1, color)
        painter.fillRect(mid_rect, mid_linear_gradient)
        painter.restore()

        # 绘制中间部分矩形，底部左右角圆角半径16
        painter.save()
        # 中间矩形的矩形区域
        mid_rect = QRectF(left, margin_top + bar_height - step, bar_width, step)
        # 使用 QPainterPath 来绘制带圆角的矩形
        path = QPainterPath()
        radius = 8  # 圆角半径
        # 为中间矩形的左右角添加圆角
        path.addRoundedRect(mid_rect, radius, radius)  # 只为矩形的左右角添加圆角
        # 设置水平方向的渐变色
        mid_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)  # 水平方向渐变
        mid_linear_gradient.setColorAt(0, color)
        mid_linear_gradient.setColorAt(0.5, QColor("#75F152"))
        mid_linear_gradient.setColorAt(1, color)
        # 填充渐变色
        painter.setPen(Qt.NoPen)
        painter.setBrush(mid_linear_gradient)
        painter.fillPath(path, mid_linear_gradient)  # 使用路径填充渐变色
        painter.restore()


        # 绘制中间顶部椭圆
        painter.save()
        mid_top_rect = QRectF(left, margin_top + bar_height - step - 9, bar_width, 14)
        # 设置由上到下的线性渐变
        mid_top_linear = QLinearGradient(mid_top_rect.topLeft(), mid_top_rect.bottomLeft())
        mid_top_linear.setColorAt(0, QColor("#54CC32"))  # 渐变起始颜色
        mid_top_linear.setColorAt(1, QColor("#74EF51"))  # 渐变结束颜色
        painter.setPen(Qt.NoPen)
        painter.setBrush(mid_top_linear)
        painter.drawEllipse(mid_top_rect)
        painter.restore()



    def drawBar_orange(self, left, margin_top, bar_width, bar_height, step, color, painter):
        # 绘制底部椭圆
        painter.save()
        bottom_rect = QRectF(left, margin_top + bar_height - 10, bar_width, 15)
        bottom_linear = QLinearGradient(left, 0, left + bar_width, 0)  # 水平方向渐变
        bottom_linear.setColorAt(0, color)
        bottom_linear.setColorAt(0.5, QColor("#FFC57A"))
        bottom_linear.setColorAt(1, color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bottom_linear)
        painter.drawEllipse(bottom_rect)
        painter.restore()

        # 绘制背景矩形，四个角为圆角
        painter.save()
        # 创建圆角矩形路径
        radius = 8  # 圆角半径
        rounded_rect_path = QPainterPath()
        bg_rect = QRectF(left, margin_top, bar_width, bar_height)
        rounded_rect_path.addRoundedRect(bg_rect, radius, radius)  # 添加圆角矩形路径
        bg_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0.5, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        painter.fillPath(rounded_rect_path, bg_linear_gradient)
        painter.restore()

        # 绘制中间部分矩形
        painter.save()
        mid_rect = QRectF(left, margin_top + bar_height - step, bar_width, step)
        mid_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)  # 水平方向渐变
        mid_linear_gradient.setColorAt(0, color)
        mid_linear_gradient.setColorAt(0.5, QColor("#FFC57A"))
        mid_linear_gradient.setColorAt(1, color)
        painter.fillRect(mid_rect, mid_linear_gradient)
        painter.restore()

        # 绘制中间顶部椭圆
        painter.save()
        mid_top_rect = QRectF(left, margin_top + bar_height - step - 9, bar_width, 14)
        # 设置由上到下的线性渐变
        mid_top_linear = QLinearGradient(mid_top_rect.topLeft(), mid_top_rect.bottomLeft())
        mid_top_linear.setColorAt(0, QColor("#FF9A18"))  # 渐变起始颜色
        mid_top_linear.setColorAt(1, QColor("#FFC57A"))  # 渐变结束颜色
        painter.setPen(Qt.NoPen)
        painter.setBrush(mid_top_linear)
        painter.drawEllipse(mid_top_rect)
        painter.restore()


    def drawBar_red(self, left, margin_top, bar_width, bar_height, step, color, painter):
        # 绘制底部椭圆
        painter.save()
        bottom_rect = QRectF(left, margin_top + bar_height - 10, bar_width, 15)
        bottom_linear = QLinearGradient(left, 0, left + bar_width, 0)  # 水平方向渐变
        bottom_linear.setColorAt(0, color)
        bottom_linear.setColorAt(0.5, QColor("#FF8D87"))
        bottom_linear.setColorAt(1, color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bottom_linear)
        painter.drawEllipse(bottom_rect)
        painter.restore()

        # 绘制背景矩形，四个角为圆角
        painter.save()
        # 创建圆角矩形路径
        radius = 8  # 圆角半径
        rounded_rect_path = QPainterPath()
        bg_rect = QRectF(left, margin_top, bar_width, bar_height)
        rounded_rect_path.addRoundedRect(bg_rect, radius, radius)  # 添加圆角矩形路径
        bg_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0.5, QColor('#D9D9D9'))
        bg_linear_gradient.setColorAt(0, QColor('#D9D9D9'))
        painter.fillPath(rounded_rect_path, bg_linear_gradient)
        painter.restore()

        # 绘制中间部分矩形
        painter.save()
        mid_rect = QRectF(left, margin_top + bar_height - step, bar_width, step)
        mid_linear_gradient = QLinearGradient(left, 0, left + bar_width, 0)  # 水平方向渐变
        mid_linear_gradient.setColorAt(0, color)
        mid_linear_gradient.setColorAt(0.5, QColor("#FF8D87"))
        mid_linear_gradient.setColorAt(1, color)
        painter.fillRect(mid_rect, mid_linear_gradient)
        painter.restore()

        # 绘制中间顶部椭圆
        painter.save()
        mid_top_rect = QRectF(left, margin_top + bar_height - step - 9, bar_width, 14)
        # 设置由上到下的线性渐变
        mid_top_linear = QLinearGradient(mid_top_rect.topLeft(), mid_top_rect.bottomLeft())
        mid_top_linear.setColorAt(0, QColor("#FF534A"))  # 渐变起始颜色
        mid_top_linear.setColorAt(1, QColor("#FF8D87"))  # 渐变结束颜色
        painter.setPen(Qt.NoPen)
        painter.setBrush(mid_top_linear)
        painter.drawEllipse(mid_top_rect)
        painter.restore()



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = QBarPainter()
    window.show()
    sys.exit(app.exec_())
