from PyQt5 import QtWidgets
def clear_layout(layout):
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        if not item:
            break
        w = item.widget()
        if w:
            w.setParent(None)
            try: w.deleteLater()
            except: pass
        sub = item.layout()
        if sub:
            clear_layout(sub)

def clear_layout_hard(layout: QtWidgets.QLayout):
    """彻底清空：递归清除子布局、控件；同时移除 QSpacerItem。"""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        w = item.widget()
        child_layout = item.layout()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif child_layout is not None:
            clear_layout_hard(child_layout)
            # 子布局本身也要删除，否则会残留占位
            del child_layout
        else:
            # QSpacerItem / QLayoutItem
            # 只要被 takeAt() 掉就不会再占位，显式 del 一下更稳
            del item
    layout.invalidate()