# -*- coding: utf-8 -*-
"""pages/review.py - 复习：卡片按浮卡模板渲染，底部评级条。"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, QEvent, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
                               QPushButton, QFrame)

import widgets as W
import card_render as CR
import formatting as F
import fsrs as FS
from core import now_ms
from pages.library import OneLineLabel

RATE_DEFS = [
    # idx, 名称, 主色, 浅底, 描边, 文字色
    # 四档走「红 → 橙 → 绿 → 青绿」递进，浅色底保持小清新、不压视线
    (0, "重来", "#C0392B", "#FBE9E6", "#F2C7C0", "#B23A2C"),
    (1, "困难", "#C77E1B", "#FBF0DC", "#F0D9B4", "#A96B10"),
    (2, "记住", "#2F7A4F", "#E7F2EA", "#C6DFCE", "#2A6C46"),
    (3, "轻松", "#0F9D6E", "#E2F4EC", "#BCE4D5", "#0B8A61"),
]


class BgArea(QWidget):
    """铺模板底色（浮卡 webview 的 page background）。"""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.color))


class MenuGlyph(QWidget):
    """菜单行的小线稿图标。"""

    def __init__(self, kind: str, size: int = 16, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        pen = QPen(QColor(W.T["ink2"]), 1.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        if self.kind == "practice":
            path = QPainterPath()
            path.moveTo(cx + 2.0, cy - 6.0)
            path.lineTo(cx - 4.0, cy + 0.8)
            path.lineTo(cx - 0.6, cy + 0.8)
            path.lineTo(cx - 1.4, cy + 6.0)
            path.lineTo(cx + 4.2, cy - 1.0)
            path.lineTo(cx + 0.8, cy - 1.0)
            path.closeSubpath()
            p.drawPath(path)
        elif self.kind == "edit":
            p.drawLine(QPointF(cx - 4.6, cy + 4.6), QPointF(cx + 3.6, cy - 3.6))
            p.drawLine(QPointF(cx - 4.6, cy + 4.6), QPointF(cx - 5.6, cy + 5.6))
            p.drawLine(QPointF(cx + 2.0, cy - 5.0), QPointF(cx + 5.4, cy - 1.6))
        elif self.kind == "pause":
            p.drawEllipse(QPointF(cx, cy), 6.0, 6.0)
            p.drawLine(QPointF(cx - 1.6, cy - 2.6), QPointF(cx - 1.6, cy + 2.6))
            p.drawLine(QPointF(cx + 1.6, cy - 2.6), QPointF(cx + 1.6, cy + 2.6))
        elif self.kind == "undo":
            p.drawArc(QRectF(cx - 6, cy - 6, 12, 12), 30 * 16, 260 * 16)
            p.drawLine(QPointF(cx + 5.6, cy - 2.4), QPointF(cx + 2.4, cy - 5.0))
            p.drawLine(QPointF(cx + 5.6, cy - 2.4), QPointF(cx + 2.0, cy - 0.6))
        else:  # later
            p.drawEllipse(QPointF(cx, cy), 6.0, 6.0)
            p.drawLine(QPointF(cx, cy), QPointF(cx, cy - 3.4))
            p.drawLine(QPointF(cx, cy), QPointF(cx + 2.8, cy + 1.2))


class MenuRow(QWidget):
    clicked = Signal(str)

    def __init__(self, key: str, kind: str, text: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("menuRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 14, 9)
        lay.setSpacing(10)
        lay.addWidget(MenuGlyph(kind, 16), 0, Qt.AlignVCenter)
        lb = QLabel(text)
        lb.setStyleSheet(f"font-size:12.5px;color:{W.T['ink']};")
        lay.addWidget(lb, 1)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(e)


class ReviewMenu(QFrame):
    """自绘弹出菜单（右上角/底部对齐都可用）。"""

    chose = Signal(str)

    def __init__(self, rows: list[tuple[str, str, str]], parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("reviewMenu")
        self.setStyleSheet(
            f"QFrame#reviewMenu{{background:{W.T['panel']};"
            f"border:1px solid {W.T['line']};border-radius:12px;}}"
            f"QWidget#menuRow:hover{{background:{W.T['paper2']};border-radius:8px;}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 5)
        lay.setSpacing(1)
        for key, kind, text in rows:
            row = MenuRow(key, kind, text)
            row.clicked.connect(self._pick)
            lay.addWidget(row)

    def _pick(self, key: str):
        self.chose.emit(key)
        self.close()

    def popup_at(self, anchor: QWidget):
        self.adjustSize()
        g = anchor.mapToGlobal(QPoint(0, 0))
        x = g.x() + anchor.width() - self.width()
        y = g.y() - self.height() - 6
        self.move(max(8, x), max(8, y))
        self.show()


def _svg_path(data: str) -> QPainterPath:
    """把 SVG path data（只用到 M/L/C/Z）转成 QPainterPath。"""
    tokens = re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?", data)
    path = QPainterPath()
    i, cmd = 0, None
    while i < len(tokens):
        t = tokens[i]
        if t in ("M", "L", "C", "Z"):
            cmd = t
            i += 1
            if cmd == "Z":
                path.closeSubpath()
                cmd = None
            continue
        if cmd == "M":
            path.moveTo(float(tokens[i]), float(tokens[i + 1]))
            i += 2
            cmd = "L"
        elif cmd == "L":
            path.lineTo(float(tokens[i]), float(tokens[i + 1]))
            i += 2
        elif cmd == "C":
            x1, y1, x2, y2, x, y = (float(v) for v in tokens[i:i + 6])
            path.cubicTo(x1, y1, x2, y2, x, y)
            i += 6
        else:
            i += 1
    return path


# 刻记 res/drawable/ic_buoy_60dp.xml 的两条路径（60×60 视图）
_BUOY_RING = _svg_path(
    "M8.701,49.185C1.707,41.517 -0.537,32.379 2.026,22.02C4.323,12.749 9.854,6.449 "
    "18.465,3.301C27.977,-0.179 37.398,-0.142 46.465,6.42C47.64,7.268 48.764,8.261 "
    "49.851,9.223L49.884,9.251C50.39,9.7 50.913,10.162 51.438,10.609C56.54,15.87 "
    "59.014,22.893 59,28.935C59.008,31.5 58.722,34.056 58.147,36.552C55.138,49.293 "
    "46.497,56.908 33.366,58.924C31.157,59.263 22.991,58.395 21.4,57.68C17.691,56.02 "
    "13.012,53.635 9.255,49.772C9.069,49.581 8.883,49.383 8.701,49.185Z"
    "M12.738,45.171C7.073,38.961 5.255,31.559 7.331,23.168C9.191,15.658 13.671,10.556 "
    "20.647,8.005C28.351,5.186 35.982,5.216 43.326,10.532C44.278,11.219 45.188,12.023 "
    "46.069,12.802L46.096,12.825C46.506,13.188 46.93,13.563 47.355,13.925C51.487,18.186 "
    "53.491,23.875 53.48,28.769C53.486,30.846 53.255,32.917 52.789,34.939C50.352,45.259 "
    "43.352,51.427 32.717,53.06C30.927,53.334 24.313,52.632 23.024,52.053C20.02,50.708 "
    "16.229,48.776 13.186,45.647C13.036,45.492 12.886,45.332 12.738,45.171Z")
_BUOY_CORE = _svg_path(
    "M11.765,24.39C10.104,31.103 11.558,37.024 16.091,41.993C16.209,42.121 16.329,42.249 "
    "16.449,42.373C18.884,44.876 21.916,46.422 24.319,47.498C25.35,47.961 30.642,48.523 "
    "32.074,48.304C40.582,46.997 46.181,42.063 48.131,33.807C48.504,32.189 48.689,30.533 "
    "48.684,28.871C48.693,24.956 47.09,20.404 43.784,16.996C43.444,16.706 43.105,16.406 "
    "42.777,16.116C42.065,15.487 41.33,14.836 40.561,14.281C34.686,10.029 28.581,10.005 "
    "22.417,12.26C16.837,14.3 13.253,18.382 11.765,24.39Z")
_BUOY_RING.setFillRule(Qt.OddEvenFill)
_BUOY_CORE.setFillRule(Qt.OddEvenFill)
_BUOY_ALL = _BUOY_RING.united(_BUOY_CORE)
_BUOY_ALL.setFillRule(Qt.OddEvenFill)

BUOY_COLOR = "#FFFFFF"      # 默认色（render 时会换成当前模板底色）
BUOY_ALPHA = 0.22           # 常态：很透，能看清下面的文字
BUOY_ALPHA_PRESSED = 0.55   # 按住/拖动：透明度降低一点（更实）


class HomeButton(QWidget):
    """刻记同款浮标：可点、可按住拖动。"""

    SIZE = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("点一下切换挖空显示；按住可拖动")
        self._on = False
        self._bg = QColor(BUOY_COLOR)
        self._fn = None
        self.on_drop = None
        self._pressed = False
        self._dragging = False
        self._press_global = None
        self._press_pos = None
        self._moved = 0

    def bind(self, fn):
        self._fn = fn

    def set_on(self, on: bool):
        self._on = bool(on)
        self.update()

    def set_bg(self, color):
        """填充色跟随卡片模板的整体底色。"""
        self._bg = QColor(color)
        self.update()

    # ---- 拖动 ----
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self._pressed = True
        self._dragging = False
        self._moved = 0
        self._press_global = e.globalPosition().toPoint()
        self._press_pos = self.pos()
        self.setCursor(Qt.ClosedHandCursor)
        self.update()

    def mouseMoveEvent(self, e):
        if not self._pressed:
            return
        delta = e.globalPosition().toPoint() - self._press_global
        self._moved = max(self._moved, abs(delta.x()) + abs(delta.y()))
        if self._moved <= 3 and not self._dragging:
            return
        self._dragging = True
        host = self.parentWidget()
        x = self._press_pos.x() + delta.x()
        y = self._press_pos.y() + delta.y()
        x = max(6, min(x, host.width() - self.width() - 6))
        y = max(6, min(y, host.height() - self.height() - 6))
        self.move(x, y)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self._pressed = False
        self.setCursor(Qt.OpenHandCursor)
        self.update()
        if not self._dragging and self._fn is not None:
            self._fn()
        if self._dragging and callable(self.on_drop):
            self.on_drop(self.pos())
        self._dragging = False

    # ---- 绘制 ----
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        scale = self.width() / 60.0
        p.scale(scale, scale)
        p.setPen(Qt.NoPen)
        # 很淡的投影，只是给个轮廓，透出下面的文字
        p.save()
        p.translate(0, 1.0)
        p.setOpacity(0.22 if self._pressed else 0.10)
        p.fillPath(_BUOY_ALL, QColor(0, 0, 0))   # 整块一起投影，内外深浅一致
        p.restore()
        alpha = BUOY_ALPHA_PRESSED if self._pressed else BUOY_ALPHA
        p.setOpacity(alpha)
        p.fillPath(_BUOY_RING, self._bg)
        p.fillPath(_BUOY_CORE, self._bg)


class PracticeBolt(QWidget):
    """主动练习状态：32×32 圆角方框里放一道闪电（未加入空心灰、已加入实心绿）。"""

    def __init__(self, on: bool = False, parent=None):
        super().__init__(parent)
        self._on = bool(on)
        self.setFixedSize(32, 32)
        self.setToolTip("已加入主动练习" if self._on else "未加入主动练习（右上角 ⋯ 里可加入）")

    @staticmethod
    def _bolt_path() -> QPainterPath:
        path = QPainterPath()
        path.moveTo(18.7, 6.3)
        path.lineTo(11.1, 17.4)
        path.lineTo(15.5, 17.4)
        path.lineTo(13.3, 25.7)
        path.lineTo(20.9, 14.6)
        path.lineTo(16.5, 14.6)
        path.closeSubpath()
        return path

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        # 只画边框（和右边 ⋯ 按钮同款），内部透明
        p.setPen(QPen(QColor(W.T["line"]), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, 31, 31), 10, 10)
        # 未加入练习时只留边框，不画闪电
        if self._on:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(W.T["brand"]))
            p.drawPath(self._bolt_path())


class QuestPill(QPushButton):
    """顶栏任务计时胶囊：只有停在学习页才跑表，暂停 / 未领取 / 完成各有状态。

    放在「卡组名」和右侧 ⋯ 之间，点一下跳回征途页。
    """

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setFixedHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.setToolTip("征途任务：只在学习页计时，点一下回到征途页")
        self.clicked.connect(lambda: self.app.show_page("plan"))
        self.sync()

    @staticmethod
    def _fmt(ms: int) -> str:
        s = max(0, int(round(ms / 1000)))
        return f"{s // 60:02d}:{s % 60:02d}"

    def sync(self):
        q = self.app.store.quest
        if q.get("status") != "active":
            # 没领任务（或已完成）：这个位置保持空白，只留点击进征途页
            self.setText("")
            self.setVisible(False)
            return
        self.setVisible(True)
        running = self.app.store.quest_running()
        self.setText(self._fmt(self.app.store.quest_left_ms()))
        bg = W.T["brand_soft"] if running else W.T["paper2"]
        fg = W.T["brand"] if running else W.T["ink2"]
        self.setStyleSheet(
            f"QPushButton{{background:{bg};color:{fg};border:none;border-radius:15px;"
            f"padding:0 12px;font-size:12.5px;font-weight:700;letter-spacing:0.6px;}}")
        self.setToolTip("倒计时中 · 离开学习页会暂停" if running else "已暂停 · 回到学习页继续")


class StatsChip(QWidget):
    """底部中间的小胶囊底：白底 + 细描边 + 大圆角（自绘，保证圆角一致）。"""

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor(W.T["line"]), 1))
        p.setBrush(QColor(W.T["panel"]))
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.drawRoundedRect(r, min(13.0, r.height() / 2), min(13.0, r.height() / 2))


class MaskModeButton(QPushButton):
    """挖空显示模式：逐个 = 方框里三横线 + L；全显 = 方框里 ALL。"""

    def __init__(self, mode: str = "hide", parent=None):
        super().__init__(parent)
        self._mode = mode
        self.setFixedSize(34, 34)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;border-radius:9px;}}"
            f"QPushButton:hover{{background:{W.T['paper2']};}}"
            f"QPushButton:pressed{{background:{W.T['brand_soft']};}}")

    def set_mode(self, mode: str):
        self._mode = mode
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(W.T["ink"]), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        box = QRectF(8, 7, 18, 20)
        p.drawRoundedRect(box, 3.2, 3.2)
        if self._mode == "hide":
            # 三横线 + 右侧 L
            for y in (12.2, 15.6, 19.0):
                p.drawLine(QPointF(11.4, y), QPointF(16.2, y))
            p.drawLine(QPointF(18.8, 11.6), QPointF(18.8, 19.8))
            p.drawLine(QPointF(18.8, 19.8), QPointF(22.4, 19.8))
        else:
            f = QFont("Microsoft YaHei UI")
            f.setPixelSize(7)
            f.setBold(True)
            p.setFont(f)
            p.drawText(box, Qt.AlignCenter, "ALL")


class ReviewPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.store = app.store
        self._last_w = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶栏（应用 chrome）：两行 —— 进度一行，卡组名一行
        self.top = QWidget()
        self.top.setObjectName("reviewTop")
        self.top.setAttribute(Qt.WA_StyledBackground, True)
        self.top.setFixedHeight(40)
        self.top_v = QVBoxLayout(self.top)
        self.top_v.setContentsMargins(16, 0, 16, 0)
        self.top_v.setSpacing(0)
        self.top_lay = QHBoxLayout()
        self.top_lay.setSpacing(8)
        self.top_v.addLayout(self.top_lay)
        self.top_meta = QHBoxLayout()
        self.top_meta.setSpacing(8)
        outer.addWidget(self.top)

        # 卡片区（模板底色）
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.area = BgArea("#B3E5FC")
        self.area_lay = QVBoxLayout(self.area)
        self.area_lay.setContentsMargins(16, 24, 16, 16)
        self.area_lay.setSpacing(0)
        self.scroll.setWidget(self.area)
        outer.addWidget(self.scroll, 1)

        # 底部操作条
        self.bottom = QWidget()
        self.bottom_lay = QVBoxLayout(self.bottom)
        # 底部只留手势条高度：纸面铺到底，提示文字不被手势条压住。
        self.bottom_lay.setContentsMargins(20, 8, 20, 10)
        self.bottom_lay.setSpacing(10)
        outer.addWidget(self.bottom)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.render)
        # 挖空开关：hide（逐个点开）/ all（全显）
        self.mask_mode = "hide"
        self._blank_all = False      # 全显模式下临时全部隐藏（home 键切换用）
        # 右下角 iOS 风格 home 键（和顶栏胶囊联动）
        self.home_btn = HomeButton(self.scroll.viewport())
        # 拖动过的位置记住：按视口比例存，窗口大小变了也不会跑丢
        saved = self.store.settings.get("home_pos")
        self._home_norm = None
        if isinstance(saved, (list, tuple)) and len(saved) == 2:
            try:
                self._home_norm = (float(saved[0]), float(saved[1]))
            except (TypeError, ValueError):
                self._home_norm = None
        self.home_btn.bind(self._home_click)
        self.home_btn.on_drop = self._home_dropped
        self.home_btn.hide()
        self.scroll.viewport().installEventFilter(self)

    # ------------------------------------------------------------ 生命周期
    def on_show(self):
        self._last_w = self.width()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.render()

    def eventFilter(self, obj, ev):
        if obj is self.scroll.viewport() and ev.type() == QEvent.Resize:
            self._place_home()
        return super().eventFilter(obj, ev)

    def _place_home(self):
        if getattr(self, "_waiting", False):
            self.home_btn.hide()
            return
        vp = self.scroll.viewport()
        b = self.home_btn
        if getattr(self, "_home_norm", None) is None:
            b.move(max(10, vp.width() - b.width() - 14),
                   max(10, vp.height() - b.height() - 14))
        else:
            nx, ny = self._home_norm
            x = int(nx * vp.width())
            y = int(ny * vp.height())
            x = max(6, min(x, vp.width() - b.width() - 6))
            y = max(6, min(y, vp.height() - b.height() - 6))
            b.move(x, y)
        b.raise_()
        b.show()

    def _home_dropped(self, pos):
        """拖完松手：记成视口比例，下次打开还在这儿。"""
        vp = self.scroll.viewport()
        w, h = max(1, vp.width()), max(1, vp.height())
        nx = max(0.0, min(1.0, pos.x() / w))
        ny = max(0.0, min(1.0, pos.y() / h))
        self._home_norm = (nx, ny)
        self.store.settings["home_pos"] = [round(nx, 4), round(ny, 4)]
        self.store.save()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if abs(self.width() - self._last_w) > 24:
            self._last_w = self.width()
            self._resize_timer.start(80)

    def _toggle_practice(self, card: dict):
        on = not card.get("practice")
        self.store.set_practice([card["id"]], on)
        self.app.toast("已加入练习" if on else "已移出练习")
        QTimer.singleShot(0, self.render)

    def _on_mask(self, key: str):
        """点一下挖空：只改这一处文字颜色，不重建页面。

        以前这里调 render()，会重建顶栏 + 整张卡 + 底部评分预览（要扫全库负载），
        挖空多的卡片点一下就是几百毫秒的卡顿。
        """
        visible = key not in self.masks
        if visible:
            self.masks.add(key)
        else:
            self.masks.discard(key)
        host = getattr(self, "_mask_host", None)
        if host is None:
            self.render()
            return
        for w in host.findChildren(CR.MaskText):
            w.set_shown(key, visible)

    def _card_mask_keys(self) -> list[str]:
        ses = self.app.session
        if not ses or ses["index"] >= len(ses["queue"]):
            return []
        card = ses["queue"][ses["index"]]
        return F.mask_keys(card.get("q") or "") + F.mask_keys(card.get("a") or "")

    def _shown_masks(self) -> set:
        """当前该显示的挖空：手点开的 + 模式带来的。"""
        if self.mask_mode == "all":
            if getattr(self, "_blank_all", False):
                return set()                 # 全显模式下的「全部不显示」
            return set(self.masks) | set(self._card_mask_keys())
        return set(self.masks)

    def _home_click(self):
        """home 键。

        逐个：每点一次露出下一个挖空；露完最后一个后再点，回到「全部隐藏」重新开始。
        全显：在「全部显示 ⇄ 全部不显示」之间切换。

        都在原位改挖空状态，不重建页面（以前每次点都 render()，挖空多就会卡）。
        """
        keys = self._card_mask_keys()
        if not keys:
            return
        if self.mask_mode != "all":
            revealed = set(self.masks)
            nxt = next((k for k in keys if k not in revealed), None)
            if nxt is None:
                self.masks.clear()          # 已经全露过 → 回到全部隐藏，重新开始
            else:
                self.masks.add(nxt)
        else:
            self._blank_all = not getattr(self, "_blank_all", False)
        self._sync_masks()

    def _sync_masks(self):
        """把当前该显示的挖空同步到已建好的卡片上（不重建页面）。"""
        host = getattr(self, "_mask_host", None)
        if host is None:
            self.render()
            return
        shown = self._shown_masks()
        for w in host.findChildren(CR.MaskText):
            w.apply_shown(shown)
        if hasattr(self, "home_btn"):
            self.home_btn.set_on(self.mask_mode == "all"
                                 and not getattr(self, "_blank_all", False))

    def _cycle_mask_mode(self):
        order = ["hide", "all"]
        if self.mask_mode not in order:
            self.mask_mode = "hide"
        self.mask_mode = order[(order.index(self.mask_mode) + 1) % len(order)]
        self._blank_all = False
        # 原位切换：只改模式图标和挖空状态，不重建整页
        if hasattr(self, "mode_btn"):
            self.mode_btn.set_mode(self.mask_mode)
        self._sync_masks()

    def render_summary(self):
        self._top_ready = False
        self._bottom_ready = False
        W.clear_layout(self.top_meta)
        ses = self.app.session
        reviewed = len(ses["ratings"])
        remembered = sum(1 for r in ses["ratings"] if r >= 2)
        weak = reviewed - remembered
        secs = max(1, int((now_ms() - ses["started"]) / 1000))
        pct = round(remembered / reviewed * 100) if reviewed else 0
        pal = CR.palette("sky")

        W.clear_layout(self.top_lay)
        back = W.BackButton(30)
        back.clicked.connect(self.app.exit_review)
        self.top_lay.addWidget(back)
        title = QLabel("这一轮完成了")
        title.setObjectName("h2")
        self.top_lay.addWidget(title, 1)

        # 居中卡片
        self.area.color = pal["page"]
        self.area.update()
        if hasattr(self, "home_btn"):
            self.home_btn.set_bg(pal["page"])
        W.clear_layout(self.area_lay)
        self.area_lay.addStretch(1)

        box = CR.CardBox(pal["front"], pal["shadow"])
        box.body.setSpacing(10)
        box.setMinimumHeight(300)
        box.body.addWidget(CR.Ribbon("小结", pal["label"]))

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(2)
        big = QLabel(f"{reviewed} 张卡片")
        big.setStyleSheet(f"color:{pal['fg']};font-size:28px;font-weight:700;")
        col.addWidget(big)
        sub = QLabel("这一轮复习完成")
        sub.setStyleSheet(f"color:{pal['fg']};font-size:12px;opacity:0.7;")
        col.addWidget(sub)
        hl.addLayout(col, 1)
        hl.addWidget(W.Ring(pct, 56, 6), 0, Qt.AlignVCenter)
        box.body.addWidget(head)

        # 三格统计
        stats = QWidget()
        sl = QHBoxLayout(stats)
        sl.setContentsMargins(0, 4, 0, 2)
        sl.setSpacing(0)
        for i, (val, name, color) in enumerate((
                (str(remembered), "记得", "#2E8B57"),
                (str(weak), "需加强", "#D9534F"),
                (f"{secs}s", "用时", "#73766F"))):
            if i:
                div = QFrame()
                div.setFixedWidth(1)
                div.setFixedHeight(26)
                div.setStyleSheet("background:rgba(0,0,0,0.08);border:none;")
                sl.addWidget(div)
            cell = QWidget()
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(1)
            v = QLabel(val)
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"color:{color};font-size:18px;font-weight:700;")
            n = QLabel(name)
            n.setAlignment(Qt.AlignCenter)
            n.setStyleSheet(f"color:{pal['fg']};font-size:10.5px;")
            cl.addWidget(v)
            cl.addWidget(n)
            sl.addWidget(cell, 1)
        box.body.addWidget(stats)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background:rgba(0,0,0,0.08);border:none;")
        box.body.addWidget(line)

        hint = QLabel("间隔已按 FSRS 自动调整，下次会正好卡在遗忘前")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{pal['fg']};font-size:11px;")
        box.body.addWidget(hint)

        self.area_lay.addWidget(box)
        self.area_lay.addStretch(1)

        # 底部：返回 / 下一组
        W.clear_layout(self.bottom_lay)
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        back = QPushButton("返回")
        back.setFixedHeight(46)
        back.setCursor(Qt.PointingHandCursor)
        back.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};color:{W.T['ink']};"
            f"border:none;border-radius:14px;font-size:14px;font-weight:600;}}")
        back.clicked.connect(self.app.exit_review)
        rl.addWidget(back, 1)

        nxt = QPushButton("下一组")
        nxt.setFixedHeight(46)
        nxt.setCursor(Qt.PointingHandCursor)
        nxt.setStyleSheet(
            f"QPushButton{{background:{W.T['brand']};color:#FFFFFF;border:none;"
            f"border-radius:14px;font-size:14px;font-weight:700;}}")
        nxt.clicked.connect(self._go_next_group)
        rl.addWidget(nxt, 1)
        self.bottom_lay.addWidget(row)

    # ---------- 下一组 ----------
    def _session_ctx(self):
        """(deck_id, 当前卡组, 是否练习模式)；混合队列 → 卡组为 None"""
        ses = self.app.session or {}
        q = ses.get("queue") or []
        deck_id = ses.get("deck_id") or (q[0]["deck_id"] if q else None)
        groups = {c.get("group") for c in q}
        cur = groups.pop() if len(groups) == 1 else None
        return deck_id, cur, bool(ses.get("practice"))

    def _next_group_candidates(self) -> list[str]:
        """按卡组列表的先后顺序，取当前卡组之后的、仍有卡片待练/待复习的组。"""
        deck_id, cur, practice = self._session_ctx()
        if not deck_id or cur is None:
            return []
        s = self.store
        cards = s.practice_cards(deck_id) if practice else s.due_cards(deck_id)
        have = {c.get("group") for c in cards}
        order = [g for g in s.ordered_groups(deck_id)
                 if g in have and g not in s.archived_groups(deck_id)
                 and g not in s.completed_groups(deck_id)]
        if cur in order:
            return order[order.index(cur) + 1:]
        return order

    def _go_next_group(self):
        cands = self._next_group_candidates()
        if not cands:
            self.app.toast("没有下一组了")
            self.app.exit_review()
            return
        deck_id, _, practice = self._session_ctx()
        nxt = cands[0]
        self.store.save_selection(deck_id, nxt)
        self.app.deck_selection[deck_id] = nxt
        self.app.start_review(deck_id, group=nxt, practice=practice)

    def _card_width(self) -> int:
        w = self.scroll.viewport().width() if self.scroll.viewport().width() > 100 else self.width()
        return max(280, w - 32)          # area_lay 左右各 16 的边距

    # ------------------------------------------------------------ 渲染
    def keyPressEvent(self, e):
        ses = self.app.session
        if not ses:
            return super().keyPressEvent(e)
        k = e.key()
        n = len(ses["queue"])
        idx = ses["index"]
        if k in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            if idx < n:
                card = ses["queue"][idx]
                if card["type"] == "qa" and not ses["revealed"]:
                    self._reveal()
                    return
                if card["type"] == "multi" and not ses["submitted"]:
                    self._submit()
                    return
            return
        if Qt.Key_1 <= k <= Qt.Key_4:
            if idx < n and ses["revealed"]:
                self._rate(k - Qt.Key_1)
            return
        if k == Qt.Key_U:
            self.app.undo()
            return
        if k == Qt.Key_E and idx < n:
            self.app.show_page("card_edit", card_id=ses["queue"][idx]["id"])
            return
        super().keyPressEvent(e)

    def render(self):
        if not self.app.session:
            # 常驻页面：退出复习后可能还有延迟的重绘请求，不能再把用户拽回首页
            return
        ses = self.app.session
        cards = ses["queue"]
        if ses["index"] >= len(cards):
            self.render_summary()
            return

        # Anki 的顺序：到点的学习卡优先。队列是按 due 排的，
        # 这里把「已经到点的学习卡」提到当前位，避免新卡把它压到后面。
        self._prefer_due_learning(ses, cards)

        card = cards[ses["index"]]
        # 还没到点的学习/重学卡：不提前弹，显示倒计时等它到点
        waiting = (card.get("state") in ("learning", "relearning")
                   and int(card.get("due") or 0) > now_ms())
        self._waiting = waiting
        deck = self.store.deck(card["deck_id"]) or {"name": "", "template": "sky"}
        if getattr(self, "_mask_card", None) != card.get("id"):
            self._mask_card = card.get("id")
            self.masks = set()
            self._blank_all = False

        # 顶栏：同一张卡只建一次（翻答案/选选项时不重建）
        self._render_top(card)

        if waiting:
            self._render_wait_body(card)
            return

        # 卡片区
        self._render_area(card, deck, ses)

        # 底部
        self._update_bottom(card, ses)

    def _render_area(self, card: dict, deck: dict, ses: dict):
        """卡片区：正/反面。翻答案、点选项时只重建这一块。"""
        pal = CR.palette(deck.get("template", "sky"))
        width = self._card_width()
        self.area.color = pal["page"]
        self.area.update()
        if hasattr(self, "home_btn"):
            self.home_btn.set_bg(pal["page"])
        W.clear_layout(self.area_lay)
        host = CR.build_cards(card, deck.get("template", "sky"),
                              bool(ses["revealed"]), ses.get("picked"), width,
                              on_pick=self._pick, mask_shown=self._shown_masks(),
                              on_mask=self._on_mask)
        self.area_lay.addWidget(host, 0, Qt.AlignHCenter)
        self._mask_host = host
        self.area_lay.addStretch(1)
        self.home_btn.set_on(self.mask_mode == "all"
                             and not getattr(self, "_blank_all", False))
        self._place_home()
        QTimer.singleShot(0, self._place_home)

    def _refresh_card_only(self):
        """只刷新卡片区和底部按钮状态（翻答案 / 选选项 / 提交），顶栏不动。"""
        ses = self.app.session
        if not ses:
            return
        if ses["index"] >= len(ses["queue"]):
            self.render_summary()
            return
        card = ses["queue"][ses["index"]]
        deck = self.store.deck(card["deck_id"]) or {"name": "", "template": "sky"}
        self._render_area(card, deck, ses)
        self._update_bottom(card, ses)

    def _render_top(self, card: dict):
        """顶栏只建一次；换卡只换卡组名（避免每张卡都重建一圈控件）。"""
        if not getattr(self, "_top_ready", False):
            W.clear_layout(self.top_lay)
            W.clear_layout(self.top_meta)

            back = W.BackButton(30)
            back.clicked.connect(self.app.exit_review)
            self.top_lay.addWidget(back)

            self._grp_label = OneLineLabel("")
            self._grp_label.setStyleSheet(
                f"color:{W.T['ink']};font-size:15px;font-weight:700;letter-spacing:0.2px;")
            self.top_lay.addWidget(self._grp_label, 1)

            # 任务计时胶囊：就在「卡组名」和右侧 ⋯ 之间那块空位
            self.q_pill = QuestPill(self.app)
            self.top_lay.addWidget(self.q_pill)

            mode_btn = MaskModeButton(self.mask_mode)
            mode_btn.setToolTip("挖空显示：逐个点开 ⇄ 全显（也可以点右下角的浮标）")
            mode_btn.clicked.connect(self._cycle_mask_mode)
            self.top_lay.addWidget(mode_btn)
            self.mode_btn = mode_btn
            self._top_ready = True
        self._grp_label.setText(card.get("group") or "未分组")
        if self.q_pill is not None:
            self.q_pill.sync()

    def refresh_quest(self, full: bool = False):
        """由 app 每秒回调：只刷顶栏那颗胶囊，不重建页面。"""
        pill = getattr(self, "q_pill", None)
        if pill is not None:
            pill.sync()

    @staticmethod
    def _prefer_due_learning(ses: dict, cards: list):
        """到点的学习/重学卡优先（Anki 的队列顺序），把它换到当前位。"""
        now = now_ms()
        i = ses["index"]
        for j in range(i, len(cards)):
            c = cards[j]
            if (c.get("state") in ("learning", "relearning")
                    and int(c.get("due") or 0) <= now):
                if j != i:
                    cards[i], cards[j] = cards[j], cards[i]
                return

    def _render_wait_body(self, card: dict):
        """学习卡还没到点：占位等着，到点自动回来（等同 Anki 的 steps 间隔）。"""
        left = max(0, int(card.get("due") or 0) - now_ms())
        secs = max(1, int(round(left / 1000)))
        W.clear_layout(self.area_lay)
        self.area.color = W.T["paper"]
        self.area.update()

        big = QLabel(f"{secs} 秒后继续")
        big.setAlignment(Qt.AlignCenter)
        big.setStyleSheet(f"font-size:16px;font-weight:700;color:{W.T['ink2']};")
        sub = QLabel("这张卡刚点过「重来」，等它到点会再出现")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size:11px;color:{W.T['ink3']};")

        self.area_lay.addStretch(1)
        self.area_lay.addWidget(big, 0, Qt.AlignHCenter)
        self.area_lay.addWidget(sub, 0, Qt.AlignHCenter)
        self.area_lay.addStretch(1)
        if hasattr(self, "home_btn"):
            self.home_btn.hide()

        W.clear_layout(self.bottom_lay)      # 等待期间不显示评分按钮
        self._bottom_ready = False           # 到点回来时重新建一次
        QTimer.singleShot(min(1000, max(200, left)), self.render)

    @staticmethod
    def _kind(c: dict) -> str:
        if int(c.get("reps") or 0) == 0:
            return "new"
        st = c.get("state") or "review"
        return "learn" if st in ("learning", "relearning") else "review"

    def _queue_stats(self, cards: list, card: dict) -> QWidget:
        """底部中间的小胶囊：新 / 学 / 复，各带一个彩色圆点，当前这一类高亮。"""
        counts = {"new": 0, "learn": 0, "review": 0}
        seen = set()
        for c in cards:
            cid = c.get("id")
            if cid in seen:          # 重学卡在队列里可能出现两次，只算一张
                continue
            seen.add(cid)
            counts[self._kind(c)] += 1
        cur = self._kind(card)

        wrap = StatsChip()
        hl = QHBoxLayout(wrap)
        hl.setContentsMargins(12, 4, 12, 4)
        hl.setSpacing(10)

        for i, (key, name) in enumerate((("new", "新"), ("learn", "学"), ("review", "复"))):
            active = key == cur
            if i:
                sep = QFrame()
                sep.setFixedSize(1, 10)
                sep.setStyleSheet(f"background:{W.T['line']};")
                hl.addWidget(sep, 0, Qt.AlignVCenter)

            lb = QLabel(f"{name} {counts[key]}")
            lb.setStyleSheet(
                f"font-size:12px;font-weight:700;letter-spacing:0.2px;"
                f"color:{W.T['brand'] if active else W.T['ink3']};")
            hl.addWidget(lb, 0, Qt.AlignVCenter)
        return wrap

    def _ensure_bottom(self):
        """底部操作条只建一次：主动练习 + 计数胶囊 + ⋯、显示答案/提交、4 个评分按钮。"""
        if getattr(self, "_bottom_ready", False):
            return
        W.clear_layout(self.bottom_lay)

        acts = QWidget()
        al = QHBoxLayout(acts)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(8)
        self._practice_bolt = PracticeBolt(False)
        al.addWidget(self._practice_bolt, 0, Qt.AlignVCenter)
        al.addStretch(1)
        self._stat_lbs = {}
        chip = StatsChip()
        cl = QHBoxLayout(chip)
        cl.setContentsMargins(12, 4, 12, 4)
        cl.setSpacing(10)
        for i, (key, name) in enumerate((("new", "新"), ("learn", "学"), ("review", "复"))):
            if i:
                sep = QFrame()
                sep.setFixedSize(1, 10)
                sep.setStyleSheet(f"background:{W.T['line']};")
                cl.addWidget(sep, 0, Qt.AlignVCenter)
            lb = QLabel(f"{name} 0")
            lb.setStyleSheet(f"font-size:12px;font-weight:700;letter-spacing:0.2px;"
                             f"color:{W.T['ink3']};")
            cl.addWidget(lb, 0, Qt.AlignVCenter)
            self._stat_lbs[key] = (name, lb)
        al.addWidget(chip, 0, Qt.AlignCenter)
        al.addStretch(1)
        self._more_btn = QPushButton("⋯")
        self._more_btn.setFixedSize(32, 32)
        self._more_btn.setCursor(Qt.PointingHandCursor)
        self._more_btn.setStyleSheet(
            f"QPushButton{{background:{W.T['paper']};border:1px solid {W.T['line']};"
            f"border-radius:10px;font-size:15px;font-weight:700;color:{W.T['ink2']};}}")
        self._more_btn.clicked.connect(
            lambda: self._open_menu(self._more_btn, self._current_card))
        al.addWidget(self._more_btn)
        self.bottom_lay.addWidget(acts)

        # 翻面/提交/评分三态共用一个固定高度容器：高度取三者最高（评分态），
        # 这样「显示答案」前后底部底色高度一致，卡片区不会跟着上下跳。
        self._bottom_swap = QWidget()
        sw = QVBoxLayout(self._bottom_swap)
        sw.setContentsMargins(0, 0, 0, 0)
        sw.setSpacing(8)

        # 问答：显示答案（去掉提示语，只留主按钮）
        self._reveal_box = QWidget()
        bl = QVBoxLayout(self._reveal_box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        btn = W.PrimaryButton("显示答案")
        btn.clicked.connect(self._reveal)
        bl.addWidget(btn)
        sw.addWidget(self._reveal_box)

        # 多选：提交答案
        self._submit_box = QWidget()
        sl = QVBoxLayout(self._submit_box)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(8)
        self._submit_btn = W.PrimaryButton("提交答案")
        self._submit_btn.clicked.connect(self._submit)
        sl.addWidget(self._submit_btn)
        hint2 = QLabel("可以多选，选完点提交")
        hint2.setObjectName("sub")
        hint2.setAlignment(Qt.AlignCenter)
        sl.addWidget(hint2)
        sw.addWidget(self._submit_box)

        grid = QWidget()
        gl = QHBoxLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(8)
        self._rate_btns = []
        for idx, name, _color, _bg, _edge, fg in RATE_DEFS:
            b = W.RatingButton(idx, name, "", fg=fg)
            b.clicked_rating.connect(self._rate)
            gl.addWidget(b, 1)
            self._rate_btns.append(b)
        # 4 个评分按钮：纯白卡片 + 轻阴影，四档只靠文字颜色区分
        group = QWidget()
        rgl = QVBoxLayout(group)
        rgl.setContentsMargins(0, 0, 0, 0)
        rgl.setSpacing(8)
        rgl.addWidget(grid)
        self._rate_box = group
        sw.addWidget(group)

        self.bottom_lay.addWidget(self._bottom_swap)
        self._bottom_ready = True
        self._equalize_bottom()

    def _equalize_bottom(self):
        """把底部变高区固定到三态里最高的高度，翻面前后底色不跳动。"""
        target = 0
        for w in (self._reveal_box, self._submit_box, self._rate_box):
            w.adjustSize()
            target = max(target, w.sizeHint().height())
        if target > 0:
            self._bottom_swap.setFixedHeight(target)

    def _update_bottom(self, card: dict, ses: dict):
        """换卡只更新文字/状态：练习星、计数、4 个间隔预览、按钮可见性。"""
        self._ensure_bottom()
        self._current_card = card

        bolt = self._practice_bolt
        bolt._on = bool(card.get("practice"))
        bolt.setToolTip("已加入主动练习" if bolt._on
                        else "未加入主动练习（右上角 ⋯ 里可加入）")
        bolt.update()

        counts = {"new": 0, "learn": 0, "review": 0}
        seen = set()
        for c in ses["queue"]:
            cid = c.get("id")
            if cid in seen:
                continue
            seen.add(cid)
            counts[self._kind(c)] += 1
        cur = self._kind(card)
        for key, (name, lb) in self._stat_lbs.items():
            lb.setText(f"{name} {counts[key]}")
            lb.setStyleSheet(
                f"font-size:12px;font-weight:700;letter-spacing:0.2px;"
                f"color:{W.T['brand'] if key == cur else W.T['ink3']};")

        previews = FS.preview(card, now_ms(),
                              cfg=self.store.sched_cfg(card.get("deck_id"),
                                                       note_id=card.get("note_id"),
                                                       card_id=card.get("id")))
        for idx, b in enumerate(self._rate_btns):
            b.set_hint(previews[idx])

        # 提前量：问答要翻面、多选要提交，才出现评分按钮
        typ = card.get("type")
        self._reveal_box.setVisible(typ == "qa" and not ses.get("revealed"))
        self._submit_box.setVisible(typ == "multi" and not ses.get("submitted"))
        self._submit_btn.setEnabled(bool(ses.get("picked")))
        self._rate_box.setVisible(
            not ((typ == "qa" and not ses.get("revealed"))
                 or (typ == "multi" and not ses.get("submitted"))))

    # ------------------------------------------------------------ 交互
    def _open_menu(self, anchor, card: dict):
        in_prac = bool(card.get("practice"))
        suspended = bool(card.get("suspended"))
        rows = [
            ("practice", "practice", "移出练习" if in_prac else "加入练习"),
            ("edit", "edit", "编辑卡片"),
            ("suspend", "pause", "恢复学习" if suspended else "暂停卡片"),
            ("bury", "later", "搁置到明天"),
            ("undo", "undo", "撤销上一步"),
        ]
        menu = ReviewMenu(rows, self)
        menu.chose.connect(lambda key: self._menu_action(key, card))
        menu.popup_at(anchor)

    def _menu_action(self, key: str, card: dict):
        if key == "practice":
            self._toggle_practice(card)
            return
        if key == "edit":
            self.app.show_page("card_edit", card_id=card["id"])
            return
        if key == "suspend":
            now_susp = not bool(card.get("suspended"))
            self.store.suspend_card(card["id"], now_susp)
            self.app.toast("已暂停" if now_susp else "已恢复学习")
            if now_susp:
                self._drop_current()
            else:
                self.render()
            return
        if key == "bury":
            self.store.bury_card(card["id"])
            self.app.toast("已搁置到明天")
            self._drop_current()
            return
        if key == "undo":
            self.app.undo()
            return
    def _drop_current(self):
        ses = self.app.session
        if not ses:
            return
        if ses["index"] < len(ses["queue"]):
            cid = ses["queue"][ses["index"]].get("id")
            # 暂停/搁置要把它在队列里的所有副本都清掉（重学卡可能有两条）
            old = list(ses["queue"])
            ses["queue"][:] = [c for c in old if c.get("id") != cid]
            gone_before = sum(1 for c in old[:ses["index"]] if c.get("id") == cid)
            ses["index"] = max(0, ses["index"] - gone_before)
        if ses["index"] >= len(ses["queue"]):
            self.render_summary()
        else:
            self.render()

    def _reveal(self):
        self.app.session["revealed"] = True
        self._refresh_card_only()

    def _pick(self, idx: int):
        ses = self.app.session
        card = ses["queue"][ses["index"]]
        if card["type"] == "single":
            ses["picked"] = idx
            ses["submitted"] = True
            ses["revealed"] = True
        else:
            picked = set(ses.get("picked") or [])
            picked.symmetric_difference_update({idx})
            ses["picked"] = picked
        self._refresh_card_only()

    def _submit(self):
        self.app.session["submitted"] = True
        self.app.session["revealed"] = True
        self._refresh_card_only()

    def _rate(self, idx: int):
        self.app.rate_card(idx)

