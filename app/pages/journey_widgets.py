# -*- coding: utf-8 -*-
"""pages/journey_widgets.py - 征途共用的自绘件（小怪 / 血条 / 勋章）。

从 plan.py 抽出来：总览页与副本页都要用，避免循环 import。
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton, QWidget

import widgets as W

HP_PER_MONSTER = 3

MONSTERS = [
    ("绿团子", "#7FB069", "#5C8A46"),
    ("蓝泡泡", "#6FA8DC", "#4A7FB0"),
    ("紫布丁", "#B39DDB", "#8E75C4"),
    ("橙果冻", "#F0A868", "#C97F3E"),
    ("粉云朵", "#F2A0B5", "#C9738B"),
    ("金元宝", "#E6C34A", "#B99722"),
]

MEDALS = [
    (0, "见习徽章", "#A8A79E"),
    (5, "青铜勋章", "#C77B3C"),
    (15, "白银勋章", "#9AA5B1"),
    (30, "黄金勋章", "#E0B341"),
    (60, "铂金勋章", "#7FB3C8"),
    (120, "钻石勋章", "#6FA8DC"),
]

# 青蛙勋章：吃掉一只青蛙 = 完成一次征途（一次专注结算）
# 阶梯按「先密后疏」设计：第 1 只立刻有反馈，之后 5 / 15 / 30 / 60 / 100 / 200 / 365
FROG_MEDALS = [
    ("tadpole",    "蝌蚪",     0,   "🐸"),
    ("first",      "初尝蛙味",  1,   "🐸"),
    ("apprentice", "蛙群学徒",  5,   "🥉"),
    ("hunter",     "蛙群克星",  15,  "🥈"),
    ("iron",       "铁胃猎手",  30,  "🥇"),
    ("feast",      "蛙宴大师",  60,  "💠"),
    ("century",    "百蛙斩",    100, "💎"),
    ("king",       "蛙王",      200, "👑"),
    ("god",        "蛙神",      365, "🌟"),
    ("emperor",    "蛙皇",      500, "👑"),
    ("overlord",   "蛙帝",      1000, "🔥"),
    ("immortal",   "蛙仙",      2000, "✨"),
    ("saint",      "蛙圣",      5000, "🏆"),
]
# 每枚勋章的主色（和 FROG_MEDALS 一一对应）
FROG_MEDAL_COLORS = ["#B9B4A6", "#9CCC65", "#CD7F32", "#BFC4C9", "#FFD24A",
                     "#7FE0C3", "#8FD0FF", "#C9A6FF", "#F06292",
                     "#FF8A65", "#B39DDB", "#4FC3F7", "#FFD54F"]

BADGES = FROG_MEDALS          # 兼容旧引用（徽章墙 / sync_badges）


def frog_medal(total: int):
    """按吃掉的总数返回 (当前勋章, 下一枚)，已满级时下一枚为 None。"""
    total = max(0, int(total))
    cur, nxt = FROG_MEDALS[0], None
    for m in FROG_MEDALS:
        if total >= m[2]:
            cur = m
        else:
            nxt = m
            break
    return cur, nxt


def _shape_path(shape: int) -> QPainterPath:
    """在 0..100 的虚拟坐标里画 12 种不同形状的勋章轮廓（按索引取）。"""
    path = QPainterPath()
    s = int(shape) % 12
    if s == 0:                                  # 圆章
        path.addEllipse(QRectF(10, 10, 80, 80))
    elif s == 1:                                # 六边形
        pts = [(50 + 42 * math.cos(math.radians(a)),
                 50 + 42 * math.sin(math.radians(a)))
               for a in (90, 150, 210, 270, 330, 30)]
        path.moveTo(*pts[0])
        for x, y in pts[1:]:
            path.lineTo(x, y)
        path.closeSubpath()
    elif s == 2:                                # 菱形
        for x, y in ((50, 8), (92, 50), (50, 92), (8, 50)):
            path.lineTo(x, y) if path.elementCount() else path.moveTo(x, y)
        path.closeSubpath()
    elif s == 3:                                # 盾牌
        path.moveTo(22, 16)
        path.lineTo(78, 16)
        path.lineTo(78, 50)
        path.cubicTo(78, 72, 64, 86, 50, 92)
        path.cubicTo(36, 86, 22, 72, 22, 50)
        path.closeSubpath()
    elif s == 4:                                # 五角星
        pts = []
        for i in range(10):
            ang = math.radians(-90 + i * 36)
            r = 42 if i % 2 == 0 else 18
            pts.append((50 + r * math.cos(ang), 50 + r * math.sin(ang)))
        path.moveTo(*pts[0])
        for x, y in pts[1:]:
            path.lineTo(x, y)
        path.closeSubpath()
    elif s == 5:                                # 八边形
        pts = [(50 + 44 * math.cos(math.radians(a)),
                 50 + 44 * math.sin(math.radians(a)))
               for a in (22.5 + 45 * k for k in range(8))]
        path.moveTo(*pts[0])
        for x, y in pts[1:]:
            path.lineTo(x, y)
        path.closeSubpath()
    elif s == 6:                                # 圆环
        path.setFillRule(Qt.OddEvenFill)
        path.addEllipse(QRectF(10, 10, 80, 80))
        path.addEllipse(QRectF(32, 32, 36, 36))
    elif s == 7:                                # 爱心
        path.moveTo(50, 86)
        path.cubicTo(18, 62, 18, 26, 34, 22)
        path.cubicTo(44, 20, 50, 30, 50, 36)
        path.cubicTo(50, 30, 56, 20, 66, 22)
        path.cubicTo(82, 26, 82, 62, 50, 86)
        path.closeSubpath()
    elif s == 8:                                # 三叶草
        path.addEllipse(QRectF(22, 22, 32, 32))
        path.addEllipse(QRectF(46, 22, 32, 32))
        path.addEllipse(QRectF(34, 44, 32, 32))
        path.addRoundedRect(QRectF(47, 62, 6, 24), 3, 3)
    elif s == 9:                                # 火焰
        path.moveTo(50, 14)
        path.cubicTo(72, 34, 74, 52, 50, 88)
        path.cubicTo(26, 52, 28, 34, 50, 14)
        path.closeSubpath()
    elif s == 10:                               # 皇冠
        path.moveTo(18, 78)
        path.lineTo(22, 40)
        path.lineTo(34, 58)
        path.lineTo(50, 26)
        path.lineTo(66, 58)
        path.lineTo(78, 40)
        path.lineTo(82, 78)
        path.closeSubpath()
        path.addRect(18, 72, 64, 9)
    else:                                       # 奖杯
        path.moveTo(32, 20)
        path.lineTo(68, 20)
        path.lineTo(62, 52)
        path.lineTo(38, 52)
        path.closeSubpath()
        path.addRect(45, 52, 10, 14)
        path.addRoundedRect(QRectF(30, 66, 40, 9), 4, 4)
    return path


class MedalDot(QWidget):
    """勋章：按 shape 画不同形状；解锁=彩色+内圈高光，未解锁=灰底描边。"""

    def __init__(self, earned: bool = False, color: str = "#C9A227",
                 shape: int = 0, size: int = 22, parent=None):
        super().__init__(parent)
        self.earned = bool(earned)
        self.color = color
        self.shape = int(shape)
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = float(self.width())
        p.save()
        p.scale(s / 100.0, s / 100.0)            # 统一在 0..100 坐标里画
        path = _shape_path(self.shape)

        if self.earned:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.color))
            p.drawPath(path)
            # 内圈高光：同形状缩小到 70%，用更亮的同色
            p.save()
            p.translate(50, 50)
            p.scale(0.68, 0.68)
            p.translate(-50, -50)
            p.setBrush(QColor(self.color).lighter(138))
            p.drawPath(path)
            p.restore()
        else:
            p.setPen(QPen(QColor(W.T["line"]), 2.4))
            p.setBrush(QColor(W.T["paper2"]))
            p.drawPath(path)
        p.restore()



def fmt_mmss(ms: int) -> str:
    s = max(0, int(round(ms / 1000)))
    return f"{s // 60:02d}:{s % 60:02d}"


class Monster(QWidget):
    """青蛙（《吃掉那只青蛙》）：圆身体 + 两只大眼睛 + 嘴，被打败时变灰、眼睛打叉。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 1
        self.defeated = False
        self._scale = 1.0
        self._override = None
        self.setFixedSize(150, 132)

    def set_scale(self, k: float):
        """整体缩放（内部按 150×132 画的，缩小时不能只改尺寸，否则会裁掉）。"""
        self._scale = max(0.3, float(k))
        self.setFixedSize(max(40, int(150 * self._scale)),
                          max(36, int(132 * self._scale)))
        self.update()

    def set_state(self, level: int, defeated: bool):
        self.level = max(1, level)
        self.defeated = defeated
        self.update()

    def set_palette(self, body: str, dark: str):
        """允许外部指定配色（普通青蛙默认草绿）。"""
        self._override = (body, dark)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = getattr(self, "_scale", 1.0)
        if k != 1.0:
            p.scale(k, k)
        body, dark = "#7CB342", "#4E7A2E"
        if getattr(self, "_override", None):
            body, dark = self._override
        if self.defeated:
            body, dark = "#C9C6BB", "#A8A79E"
        cx, base = 75.0, 122.0

        # 地面阴影
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 26))
        p.drawEllipse(QRectF(cx - 44, base - 9, 88, 14))

        # 后腿（深色，压在身体后面）
        p.setBrush(QColor(dark))
        p.drawEllipse(QRectF(cx - 54, base - 28, 28, 17))
        p.drawEllipse(QRectF(cx + 26, base - 28, 28, 17))

        # 眼睛的外凸（身体色，略深描边）
        p.setBrush(QColor(body))
        p.setPen(QPen(QColor(dark), 2))
        p.drawEllipse(QRectF(cx - 44, base - 82, 38, 38))
        p.drawEllipse(QRectF(cx + 6, base - 82, 38, 38))

        # 身体
        p.setBrush(QColor(body))
        p.setPen(QPen(QColor(dark), 2))
        p.drawEllipse(QRectF(cx - 47, base - 58, 94, 56))

        # 肚皮
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(body).lighter(120))
        p.drawEllipse(QRectF(cx - 31, base - 46, 62, 38))

        # 眼睛
        eye_y = base - 63
        if self.defeated:
            p.setPen(QPen(QColor("#6E7266"), 3.2, Qt.SolidLine, Qt.RoundCap))
            for dx in (-25, 25):
                p.drawLine(QPointF(cx + dx - 6, eye_y - 6), QPointF(cx + dx + 6, eye_y + 6))
                p.drawLine(QPointF(cx + dx - 6, eye_y + 6), QPointF(cx + dx + 6, eye_y - 6))
        else:
            p.setPen(Qt.NoPen)
            for dx in (-25, 25):
                p.setBrush(QColor("#FFFFFF"))
                p.drawEllipse(QRectF(cx + dx - 12, eye_y - 12, 24, 24))
                p.setBrush(QColor("#2B2B26"))
                p.drawEllipse(QRectF(cx + dx - 4.8, eye_y - 4.8, 9.6, 9.6))
                p.setBrush(QColor(255, 255, 255, 210))
                p.drawEllipse(QRectF(cx + dx - 2.6, eye_y - 7.0, 3.8, 3.8))

        # 鼻孔
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(dark))
        p.drawEllipse(QRectF(cx - 10, base - 50, 3.2, 3.2))
        p.drawEllipse(QRectF(cx + 6.8, base - 50, 3.2, 3.2))

        # 嘴：宽宽的一道弧
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(dark), 2.4, Qt.SolidLine, Qt.RoundCap))
        if self.defeated:
            p.drawLine(QPointF(cx - 14, base - 36), QPointF(cx + 14, base - 36))
        else:
            p.drawArc(QRectF(cx - 22, base - 44, 44, 18), 200 * 16, 140 * 16)

        # 前脚
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(dark))
        p.drawEllipse(QRectF(cx - 40, base - 16, 18, 8))
        p.drawEllipse(QRectF(cx + 22, base - 16, 18, 8))


class HpBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.done = 0
        self.need = HP_PER_MONSTER
        self.setFixedHeight(10)

    def set_state(self, done: int, need: int):
        self.done = done
        self.need = max(1, need)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        n = max(1, self.need)
        gap = 3
        seg = (self.width() - gap * (n - 1)) / n
        for i in range(n):
            x = i * (seg + gap)
            filled = i < self.done
            p.setBrush(QColor(W.T["red"] if filled and self.done < self.need
                              else (W.T["brand"] if filled else W.T["paper2"])))
            p.drawRoundedRect(QRectF(x, 0, seg, 10), 5, 5)


class Medal(QWidget):
    """勋章：圆形底 + 缎带 + 星星。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = MEDALS[0][2]
        self.setFixedSize(46, 46)

    def set_color(self, color: str):
        self.color = color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.color).darker(118))
        p.drawRoundedRect(QRectF(15, 26, 7, 16), 2, 2)
        p.drawRoundedRect(QRectF(24, 26, 7, 16), 2, 2)
        p.setBrush(QColor(self.color))
        p.drawEllipse(QRectF(5, 3, 36, 36))
        p.setBrush(QColor(255, 255, 255, 60))
        p.drawEllipse(QRectF(9, 7, 28, 28))
        path = QPainterPath()
        cx, cy = 23, 21
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            r = 8.0 if i % 2 == 0 else 3.6
            pt = QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath()
        p.setBrush(QColor("#FFFFFF"))
        p.drawPath(path)


def medal_for(total: int):
    """按累计次数返回 (当前勋章, 下一档或 None)。"""
    cur, nxt = MEDALS[0], None
    for i, m in enumerate(MEDALS):
        if total >= m[0]:
            cur = m
            nxt = MEDALS[i + 1] if i + 1 < len(MEDALS) else None
    return cur, nxt


class CheckBtn(QPushButton):
    """24×24 的勾选方块（自绘，避免字体里没有 ✓ 时变成空白）。"""

    def __init__(self, done: bool, on_click=None, parent=None):
        super().__init__("", parent)
        self.done = bool(done)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        if on_click is not None:
            self.clicked.connect(on_click)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        if self.done:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(W.T["brand"]))
            p.drawRoundedRect(r, 8, 8)
            pen = QPen(QColor("#FFFFFF"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawLine(QPointF(6.6, 12.4), QPointF(10.4, 16.2))
            p.drawLine(QPointF(10.4, 16.2), QPointF(17.4, 8.4))
        else:
            p.setPen(QPen(QColor(W.T["line"]), 1.7))
            p.setBrush(QColor(W.T["panel"]))
            p.drawRoundedRect(r, 8, 8)


class ToggleSwitch(QPushButton):
    """iOS 风格开关：开=品牌色 + 滑块靠右，关=灰底 + 滑块靠左。"""

    def __init__(self, on: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(bool(on))
        self.setFixedSize(50, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        on = self.isChecked()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(W.T["brand"] if on else W.T["line"]))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        d = h - 6
        x = (w - d - 3) if on else 3
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 3, d, d))


class WeekBars(QWidget):
    """最近 7 天的学习时长柱状图：一根柱子 = 一天，高度 = 分钟数。"""

    def __init__(self, days, parent=None):
        super().__init__(parent)
        self.days = list(days)          # [(标签, 分钟)]
        self.setFixedHeight(118)

    def bar_heights(self) -> list[float]:
        """各柱子的像素高度（测试/复用用）。"""
        n = max(1, len(self.days))
        base, top = self.height() - 22, 16
        mx = max([m for _l, m in self.days] + [1])
        return [0.0 if m <= 0 else max(4.0, (base - top) * m / mx)
                for _l, m in self.days]

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = max(1, len(self.days))
        slot = self.width() / n
        bar_w = max(10.0, min(24.0, slot * 0.5))
        base = self.height() - 22
        heights = self.bar_heights()
        for i, (label, mins) in enumerate(self.days):
            cx = slot * (i + 0.5)
            today = (i == n - 1)
            h = heights[i]

            # 底槽（没数据的日子也留一条淡淡的底座）
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(W.T["paper2"]))
            p.drawRoundedRect(QRectF(cx - bar_w / 2, base - 4, bar_w, 4),
                              bar_w * 0.4, bar_w * 0.4)
            if h > 0:
                p.setBrush(QColor(W.T["brand"] if today else W.T["brand_soft"]))
                p.drawRoundedRect(QRectF(cx - bar_w / 2, base - h, bar_w, h),
                                  bar_w * 0.35, bar_w * 0.35)
                f = QFont()
                f.setPixelSize(9)
                p.setFont(f)
                p.setPen(QColor(W.T["brand"] if today else W.T["ink3"]))
                p.drawText(QRectF(cx - 24, base - h - 14, 48, 12),
                           Qt.AlignCenter, str(int(mins)))

            # 星期标签
            f2 = QFont()
            f2.setPixelSize(9)
            f2.setBold(today)
            p.setFont(f2)
            p.setPen(QColor(W.T["brand"] if today else W.T["ink3"]))
            p.drawText(QRectF(cx - slot / 2, base + 4, slot, 14),
                       Qt.AlignCenter, label)


class ThinBar(QWidget):
    """可指定 track / fill 的细条（HeroCard 深色底上也能看清）。"""

    def __init__(self, pct: float = 0, fill: str = "#7FD3A6",
                 track: str = "rgba(255,255,255,0.22)", height: int = 8, parent=None):
        super().__init__(parent)
        self.pct = max(0.0, min(100.0, float(pct)))
        self.fill = fill
        self.track = track
        self.setFixedHeight(height)

    @staticmethod
    def _color(spec) -> QColor:
        if isinstance(spec, QColor):
            return spec
        s = str(spec).strip()
        if s.startswith("rgba(") and s.endswith(")"):
            try:
                parts = [p.strip() for p in s[5:-1].split(",")]
                r, g, b = (int(float(x)) for x in parts[:3])
                a = float(parts[3]) if len(parts) > 3 else 1.0
                return QColor(r, g, b, int(round(a * 255)))
            except Exception:
                return QColor(0, 0, 0, 0)
        return QColor(s)

    def set_pct(self, pct: float):
        self.pct = max(0.0, min(100.0, float(pct)))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.height() / 2
        p.setPen(Qt.NoPen)
        p.setBrush(self._color(self.track))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), r, r)
        if self.pct > 0:
            p.setBrush(self._color(self.fill))
            p.drawRoundedRect(QRectF(0, 0, self.width() * self.pct / 100.0, self.height()), r, r)

