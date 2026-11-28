# -*- coding: utf-8 -*-
"""
card_render.py - 严格按「浮卡」的卡片样式渲染（取值自 templates_data.json / card_render.py）

天蓝薰衣模板原始值：
  page  #B3E5FC   front #FFF0F5   back #F0FAE6
  label #E91E63   answer label #2E8B57   text #2b3a3c
  card  radius 16  padding 14/16/16  shadow 0 10 15 -3 rgba(233,30,99,.10)
  bookmark: 13px/800, padding 4x14, radius 0 4 4 0, 左侧 8x16 三角, 左侧 2px 处 4px 白点
选择题（card_render.CHOICE_CSS）：
  选项 1px #E5DFD3 / radius 9 / 白底 / padding 7x11 / margin 6 0
  正确 #2E9E67 + #E3F4EC + 绿字 + "  ✓"；错选 #D9534F + #FDECEA + 红字 + "  ✗"
"""
from __future__ import annotations

import html

from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import (QColor, QPainter, QPainterPath, QPen, QBrush, QFont,
                           QFontMetrics, QTextDocument, QTextOption,
                           QTextCharFormat)
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
                               QSizePolicy, QTextBrowser)

import formatting as F
import theme

# ---------------------------------------------------------------- 调色板

TEMPLATES = {
    "sky": {
        "name": "天蓝薰衣", "page": "#B3E5FC", "front": "#FFF0F5", "back": "#F0FAE6",
        "label": "#E91E63", "alabel": "#2E8B57", "fg": "#2b3a3c",
        # 挖空露字时的颜色（浮卡 CSS: 正面 #C2185B / 背面 #1B5E20）
        "hlabel": "#C2185B", "halabel": "#1B5E20",
        "shadow": (233, 30, 99), "ashadow": (46, 139, 87),
    },
    "bean": {
        "name": "豆沙绿语", "page": "#C7EDCC", "front": "#FFFDF9", "back": "#FFFDF9",
        "label": "#4F8F9D", "alabel": "#4F8F9D", "fg": "#2D4B4B",
        "hlabel": "#2d4b4b", "halabel": "#2d4b4b",
        "shadow": (79, 143, 157), "ashadow": (79, 143, 157),
    },
    "mint": {
        "name": "青柠薄荷", "page": "#C7ECEE", "front": "#E0F2F1", "back": "#E0F2F1",
        "label": "#079992", "alabel": "#38ADA9", "fg": "#263238",
        "hlabel": "#004D40", "halabel": "#004D40",
        "shadow": (7, 153, 146), "ashadow": (56, 173, 169),
    },
    "lime": {
        "name": "绿韵黄调", "page": "#D1F2EB", "front": "#FFFFF0", "back": "#FFFFF0",
        "label": "#43A047", "alabel": "#43A047", "fg": "#263238",
        "hlabel": "#2E7D32", "halabel": "#2E7D32",
        "shadow": (67, 160, 71), "ashadow": (67, 160, 71),
    },
    "pink": {
        "name": "淡粉紫橙", "page": "#FFE5F1", "front": "#F5F5FF", "back": "#FFF8F0",
        "label": "#5C6BC0", "alabel": "#E65100", "fg": "#263238",
        "hlabel": "#283593", "halabel": "#BF360C",
        "shadow": (92, 107, 192), "ashadow": (230, 81, 0),
    },
    "candy": {
        "name": "粉彩撞色", "page": "#FFF0F8", "front": "#FFFFFF", "back": "#FFFFFF",
        "label": "#FF69B4", "alabel": "#4FD1C5", "fg": "#8A0051",
        "hlabel": "#8a0051", "halabel": "#8a0051",
        "amask": "#FF69B4",
        "shadow": (255, 105, 180), "ashadow": (79, 209, 197),
    },
    "glass": {
        "name": "弥散雾影", "page": "#F0EEF8", "front": "#FFFFFF", "back": "#FFFFFF",
        "label": "#5C6BC0", "alabel": "#E65100", "fg": "#333333",
        "hlabel": "#283593", "halabel": "#BF360C",
        "shadow": (92, 107, 192), "ashadow": (230, 81, 0),
    },
}

ALIAS = {"sunset": "pink", "tpl-sky": "sky"}


def palette(key: str) -> dict:
    key = ALIAS.get(key, key)
    return TEMPLATES.get(key, TEMPLATES["sky"])


def mask_colors(pal, side: str = "back") -> dict:
    """{组号: (横线色, 露字色)}。

    组 1 用模板自己的标签色（正面玫瑰、背面海绿），露字色是它的深色版；
    组 2/3 用固定的琥珀 / 靛蓝，保证多组挖空一眼能分开。
    """
    if not isinstance(pal, dict):
        pal = palette(pal)
    if side == "front":
        line = pal.get("mask") or pal["label"]
        hover = pal.get("hlabel") or QColor(line).darker(135).name()
    else:
        line = pal.get("amask") or pal["alabel"]
        hover = pal.get("halabel") or QColor(line).darker(135).name()
    out = {1: (line, hover)}
    out.update(F.GROUP_COLORS)
    return out


def _as_set(picked) -> set:
    if picked is None:
        return set()
    if isinstance(picked, int):
        return {picked}
    try:
        return set(picked)
    except TypeError:
        return set()


def _q(color: str, alpha: int | None = None) -> QColor:
    c = QColor(color)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


# ---------------------------------------------------------------- 文本量高

def text_height(text: str, px: int, width: int, bold=False, line=1.7, color="#2b3a3c") -> int:
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setDefaultFont(_font(px, bold))
    opt = QTextOption()
    opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
    doc.setDefaultTextOption(opt)
    lh = max(1, round(px * line))
    doc.setHtml(f'<div style="color:{color};font-size:{px}px;line-height:{lh}px">{text}</div>')
    doc.setTextWidth(max(40, width))
    return int(doc.size().height()) + 4


def _font(px: int, bold=False) -> QFont:
    f = QFont(theme.FONT)
    f.setPixelSize(px)
    f.setBold(bold)
    return f


# ---------------------------------------------------------------- 书签

class Ribbon(QWidget):
    """浮卡的书签：左侧 8×16 三角 + 0/4/4/0 圆角 + 白点 + 投影。"""

    def __init__(self, text: str, color: str, parent=None):
        super().__init__(parent)
        self.text = text
        self.color = color
        f = _font(13, True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 0.4)
        self._f = f
        self._tw = QFontMetrics(f).horizontalAdvance(text)
        self.setFixedSize(self._tw + 34, 24)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = _q(self.color)
        h = self.height()
        x0 = 8.0
        w = self.width() - x0

        # 投影（只画在主体上，够近似 box-shadow: 2px 2px 4px rgba(0,0,0,.15)）
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 34))
        p.drawRoundedRect(QRectF(x0 + 2, 2, w, h - 2), 4, 4)

        path = QPainterPath()
        path.moveTo(x0, 0)
        path.lineTo(x0 + w - 4, 0)
        path.quadTo(x0 + w, 0, x0 + w, 4)
        path.lineTo(x0 + w, h - 4)
        path.quadTo(x0 + w, h, x0 + w - 4, h)
        path.lineTo(x0, h)
        path.closeSubpath()

        # 左侧三角
        tri = QPainterPath()
        tri.moveTo(x0, 0)
        tri.lineTo(0, h / 2)
        tri.lineTo(x0, h)
        tri.closeSubpath()

        p.setBrush(QBrush(c))
        p.setPen(Qt.NoPen)
        p.drawPath(tri)
        p.drawPath(path)

        # 白点
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(x0 + 6, h / 2), 2.2, 2.2)

        # 文字
        p.setPen(QColor("#FFFFFF"))
        p.setFont(self._f)
        p.drawText(QRectF(x0 + 12, 0, w - 12, h), Qt.AlignLeft | Qt.AlignVCenter, self.text)


# ---------------------------------------------------------------- 卡片

class CardBox(QWidget):
    """一张卡：圆角底 + 投影，内容放 self.body。"""

    def __init__(self, bg: str, shadow_rgb, radius=16, parent=None):
        super().__init__(parent)
        self.bg = bg
        self.radius = radius
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 16)
        self.body.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._shadow_rgb = shadow_rgb

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        p.setPen(Qt.NoPen)
        p.setBrush(_q(self.bg))
        p.drawRoundedRect(r, self.radius, self.radius)


class CheckBox(QWidget):
    """多选的勾选框：16×16 圆角方块，选中填充并画勾/叉。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.setFixedSize(18, 18)

    def set_state(self, state: str):
        self.state = state
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)

        if self.state in ("picked", "right", "wrong"):
            fill = {"picked": "#F25F1C", "right": "#2E9E67", "wrong": "#D9534F"}[self.state]
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(fill))
            p.drawRoundedRect(r, 5, 5)
            p.setPen(QPen(QColor("#FFFFFF"), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            c = r.center()
            if self.state == "wrong":
                p.drawLine(QPointF(c.x() - 3.4, c.y() - 3.4), QPointF(c.x() + 3.4, c.y() + 3.4))
                p.drawLine(QPointF(c.x() + 3.4, c.y() - 3.4), QPointF(c.x() - 3.4, c.y() + 3.4))
            else:
                path = QPainterPath()
                path.moveTo(c.x() - 3.6, c.y() + 0.2)
                path.lineTo(c.x() - 1.0, c.y() + 3.0)
                path.lineTo(c.x() + 3.8, c.y() - 3.0)
                p.drawPath(path)
        else:
            p.setPen(QPen(QColor("#C9C4B8"), 1.6))
            p.setBrush(QColor("#FFFFFF"))
            p.drawRoundedRect(r, 5, 5)


class OptionPill(QFrame):
    """选项行：单选是白底胶囊；多选前面多一个勾选框。"""

    clicked = Signal(int)

    def __init__(self, index: int, letter: str, text: str, state="idle",
                 multi=False, width=300, parent=None):
        super().__init__(parent)
        self.index = index
        self.state = state
        self.multi = multi
        self._hover = False
        self.letter = letter
        self.raw = text
        self.setObjectName("optRow")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 7, 11, 7)
        lay.setSpacing(9)
        self.box = None
        if multi:
            self.box = CheckBox()
            self.box.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lay.addWidget(self.box, 0, Qt.AlignVCenter)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label.setStyleSheet("background:transparent;border:none;")
        self.label.setMinimumHeight(text_height(f"{letter}. {text}", 16, max(60, width), False, 1.5))
        lay.addWidget(self.label, 1)
        self._apply()

    # ---- 状态 ----
    def set_state(self, state: str):
        self.state = state
        self._apply()

    # 状态 → (底色, 边框, 文字色, 字重)
    STYLES = {
        "idle":   ("#FFFFFF", "#E5DFD3", "#26211A", 400),
        "picked": ("#FDEDE2", "#F25F1C", "#26211A", 700),
        "right":  ("#E3F4EC", "#2E9E67", "#1F6B45", 700),
        "wrong":  ("#FDECEA", "#D9534F", "#A0322E", 400),
    }

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(self._border), 1))
        p.setBrush(QColor(self._bg))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
                          9, 9)

    def _apply(self, restyle: bool = True):
        suffix = ""
        if not self.multi and self.state == "right":
            suffix = "  ✓"
        elif not self.multi and self.state == "wrong":
            suffix = "  ×"
        self.label.setText(f"{self.letter}. {self.raw}{suffix}")

        bg, border, fg, weight = self.STYLES[self.state]
        if self._hover and self.state in ("idle", "picked"):
            border = "#F25F1C"
        self._bg, self._border = bg, border
        if restyle:
            # 只在状态真的变化时改文字样式；悬停只重绘，不碰样式表
            self.label.setStyleSheet(
                f"background:transparent;border:none;color:{fg};"
                f"font-size:16px;font-weight:{weight};")
        if self.box is not None:
            self.box.set_state(self.state)
        self.update()

    # ---- 交互 ----
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.state in ("idle", "picked"):
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(e)

    def enterEvent(self, e):
        self._hover = True
        self._apply(restyle=False)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._apply(restyle=False)
        super().leaveEvent(e)


# ---------------------------------------------------------------- 组装

def _label_html(text: str, px: int, color: str, bold=False, line=1.7) -> str:
    lh = max(1, round(px * line))          # 用 px，避免 Qt 把 % 算错基准
    return (f'<div style="color:{color};font-size:{px}px;'
            f'font-weight:{"700" if bold else "400"};'
            f'line-height:{lh}px">{text}</div>')


PARA_GAP = 18  # 段间距（px）——对齐浮卡 fmt_html 的 margin:0 0 18px 0

_PARA_RE = __import__("re").compile(r"\n+")   # 每个换行 = 一段（浮卡也是按行拆 <p>）


def _rich(text: str, px: int, color: str, bold=False, line=1.7, width=330,
          on_mask=None) -> QLabel:
    """单段文本：段内换行用 <br>，行高统一。挖空是 <a href="mask:key">，点了就回调。"""
    body = text.replace("\r\n", "\n").replace("\n", "<br>")
    lb = QLabel()
    lb.setTextFormat(Qt.RichText)
    lb.setWordWrap(True)
    lb.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    lb.setIndent(0)
    lb.setText(_label_html(body, px, color, bold, line))
    if on_mask is not None and "mask:" in text:
        lb.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        lb.setOpenExternalLinks(False)
        lb.linkActivated.connect(lambda href: on_mask(href.split(":", 1)[-1]))
    # 高度用 QLabel 自己在固定宽度下的换行结果，避免「量的宽度 ≠ 画的宽度」导致虚高
    lb.setFixedWidth(max(40, width))
    h = lb.heightForWidth(max(40, width))
    lb.setFixedHeight(max(24, int(h)))
    return lb


def _paras(text: str, px: int, color: str, bold=False, line=1.7, width=330,
           gap: int | None = None, on_mask=None) -> QWidget:
    """多段文本：每段一个 QLabel，段间用布局 spacing —— 行距、段距都精确可控。"""
    text = (text or "").replace("\r\n", "\n")
    paras = [x.strip() for x in _PARA_RE.split(text) if x.strip()]
    if len(paras) <= 1:
        return _rich(text, px, color, bold, line, width, on_mask=on_mask)
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(PARA_GAP if gap is None else gap)
    for para in paras:
        lay.addWidget(_rich(para, px, color, bold, line, width, on_mask=on_mask))
    return box


class MaskText(QWidget):
    """带挖空的正文（对应浮卡的 .mask:hover / .shown）。

    自己管一个 QTextDocument 并直接画，避免 QTextBrowser 的滚动/焦点副作用。
    - 平时：文字颜色 = 卡片底色（看不见），下面画一条 2px 横线（同浮卡的 border-bottom）；
    - 鼠标移入：该空露出原文（只改字符格式，不重排，所以不闪也不裁切）；
    - 移出：盖回去；
    - 点一下：页面把 key 记进 mask_shown（固定显示、加粗），再点收回。
    """

    def __init__(self, raw, pal, shown, on_mask, px, bold, line, width, side="back",
                 parent=None):
        super().__init__(parent)
        self._raw = raw
        self._shown = set(shown or ())
        self._on_mask = on_mask
        self._hover = None
        self._px, self._bold, self._line = px, bold, line
        self._width = max(40, width)
        self._colors = mask_colors(pal, side)      # {组号: (横线色, 露字色)}
        self._fg = pal["fg"]
        self._bg = pal["front"] if side == "front" else pal["back"]
        self._clozes = {k: (inner, g) for k, inner, g in F.mask_infos(raw)}  # key → (原文, 组)
        self._doc = QTextDocument(self)
        self._doc.setDocumentMargin(0)
        self._doc.setUndoRedoEnabled(False)
        self._rects: dict = {}          # 挖空横线矩形缓存：换文本/宽度时才失效
        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)
        self._apply()

    # ---------- 渲染 ----------
    def _wrap(self, inner: str) -> str:
        lh = max(1, round(self._px * self._line))
        return (f'<div style="color:{self._fg};font-size:{self._px}px;'
                f'font-weight:{700 if self._bold else 400};'
                f'line-height:{lh}px">{inner}</div>')

    def _html(self) -> str:
        line, hover = self._colors.get(1, next(iter(self._colors.values())))
        return F.to_rich_blocks(self._raw, shown=self._shown, hovered=None,
                                link=self._on_mask is not None,
                                mask_color=line, fg=hover,
                                hidden=self._bg, groups=self._colors,
                                para_gap=PARA_GAP,
                                line_px=max(1, round(self._px * self._line)))

    def _apply(self):
        self._doc.setHtml(self._wrap(self._html()))
        self._doc.setTextWidth(self._width)
        h = self._doc.documentLayout().documentSize().height()
        self.setFixedWidth(self._width)
        self.setFixedHeight(max(24, int(h) + 2))
        self._rects.clear()             # 排版变了，横线位置要重算

    # ---------- 挖空横线 ----------
    def _range_rects(self, start: int, end: int):
        """把 [start,end) 这段文字按行拆成若干横线矩形（处理换行）。"""
        doc = self._doc
        layout = doc.documentLayout()
        out = []
        block = doc.findBlock(start)
        while block.isValid() and block.position() < end:
            bpos = block.position()
            blk = block.layout()
            top = layout.blockBoundingRect(block).top()
            for i in range(blk.lineCount()):
                line = blk.lineAt(i)
                lstart = bpos + line.textStart()
                lend = lstart + line.textLength()
                a, b = max(start, lstart), min(end, lend)
                if b <= a:
                    continue
                x1 = line.cursorToX(a - bpos)
                x2 = line.cursorToX(b - bpos)
                x1 = x1[0] if isinstance(x1, tuple) else x1
                x2 = x2[0] if isinstance(x2, tuple) else x2
                y = top + line.y() + line.height() - 1
                out.append(QRectF(min(x1, x2), y, abs(x2 - x1), 2))
            block = block.next()
        return out

    def _mask_rects(self, inner: str):
        cached = self._rects.get(inner)
        if cached is not None:
            return cached
        doc = self._doc
        rects = []
        pos = 0
        while True:
            cur = doc.find(inner, pos)
            if cur.isNull():
                break
            rects += self._range_rects(cur.selectionStart(), cur.selectionEnd())
            pos = cur.selectionEnd()
        self._rects[inner] = rects
        return rects

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        # 只画露出来的那一块：长答案卡（十几段）整篇重绘会明显卡
        clip = QRectF(e.rect())
        self._doc.drawContents(p, clip)
        # 横线永远画（浮卡的 border-bottom 两种状态都在）
        p.setPen(Qt.NoPen)
        for inner, group in self._clozes.values():
            p.setBrush(QColor(self._colors.get(group, self._colors[1])[0]))
            for r in self._mask_rects(inner):
                if clip.intersects(r):
                    p.drawRect(r)

    # ---------- 交互 ----------
    def _anchor_at(self, pos) -> str:
        return self._doc.documentLayout().anchorAt(QPointF(pos))

    @staticmethod
    def _key(anchor: str) -> str | None:
        return anchor.split(":", 1)[1] if anchor.startswith("mask:") else None

    def _paint(self, key: str | None, visible: bool):
        """只换颜色：可见 = 正文色，隐藏 = 卡片底色。

        字重始终是加粗（排版按加粗算好），所以这里不会触发重排/改高度。
        """
        item = self._clozes.get(key or "")
        if not item:
            return
        inner, group = item
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self._colors.get(group, self._colors[1])[1] if visible else self._bg))
        fmt.setBackground(QColor(0, 0, 0, 0))       # 不要底色，只要横线
        doc = self._doc
        pos = 0
        while True:
            cur = doc.find(inner, pos)
            if cur.isNull():
                break
            cur.mergeCharFormat(fmt)
            pos = cur.selectionEnd()
        self.update()


    def set_shown(self, key: str, visible: bool):
        """外部（复习页点挖空）直接切换显示，不重建整个页面。"""
        if visible:
            self._shown.add(key)
        else:
            self._shown.discard(key)
        self._paint(key, visible)

    def apply_shown(self, shown) -> None:
        """把「该显示哪些空」整体同步过来（home 键逐个/全显用），只重画变了的。"""
        want = set(shown or ())
        changed = [k for k in self._clozes
                   if (k in want) != (k in self._shown)]
        self._shown = {k for k in self._clozes if k in want}
        for k in changed:
            self._paint(k, k in want)

    def mouseMoveEvent(self, ev):
        key = self._key(self._anchor_at(ev.position()))
        if key != self._hover:
            prev, self._hover = self._hover, key
            if prev and prev not in self._shown:
                self._paint(prev, False)
            if key:
                self._paint(key, True)
            self.setCursor(Qt.PointingHandCursor if key else Qt.ArrowCursor)
        super().mouseMoveEvent(ev)

    def leaveEvent(self, ev):
        if self._hover:
            prev, self._hover = self._hover, None
            if prev not in self._shown:
                self._paint(prev, False)
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(ev)

    def mousePressEvent(self, ev):
        key = self._key(self._anchor_at(ev.position()))
        if key and self._on_mask:
            self._on_mask(key)
        super().mousePressEvent(ev)


def _body(text: str, pal: dict, width: int, side: str = "front", px: int = 18,
          bold: bool = False, line: float = 1.65, on_mask=None, mask_shown=()) -> QWidget:
    """一段卡片正文：有挖空用 MaskText（悬停/点击），否则走原来的 QLabel 排版。"""
    if F.has_cloze(text):
        return MaskText(text, pal, mask_shown, on_mask, px, bold, line, width, side)
    color = pal["label"] if side == "front" else pal["alabel"]
    html = F.to_rich(text, shown=mask_shown, mask_color=color, fg=pal["fg"],
                     groups=mask_colors(pal, side))
    return _paras(html, px, pal["fg"], bold, line, width)


def build_front(card: dict, pal: dict, revealed=False, picked=None, multi=False, width=330,
                on_pick=None, mask_shown=(), on_mask=None) -> QWidget:
    """正面卡：问答只放问题；选择题放题干 + 选项。"""
    box = CardBox(pal["front"], pal["shadow"])
    box.setFixedWidth(width)
    box.body.addWidget(Ribbon("问题", pal["label"]))
    box.body.addSpacing(10)

    def q_html(text):
        return F.to_rich(text, shown=mask_shown, link=on_mask is not None,
                         mask_color=pal["label"])

    if card["type"] == "qa":
        box.body.addWidget(_body(card["q"], pal, width - 32, "front", 16, False, 1.6,
                                 on_mask, mask_shown))
        return box

    q = _body(card["q"], pal, width - 32, "front", 16, True, 1.55, on_mask, mask_shown)
    box.body.addWidget(q)
    box.body.addSpacing(10)

    answers = set(card.get("answer") or [])
    picks = _as_set(picked)
    for i, opt in enumerate(card.get("options") or []):
        if revealed:
            state = "right" if i in answers else ("wrong" if i in picks else "idle")
        else:
            state = "picked" if i in picks else "idle"
        pill = OptionPill(i, "ABCDEFG"[i], F.to_rich(str(opt), shown=mask_shown,
                                                    mask_color=pal["label"]), state,
                          multi=(card["type"] == "multi"), width=width - 60)
        if on_pick is not None and not revealed:
            pill.clicked.connect(on_pick)
        box.body.addWidget(pill)
        box.body.addSpacing(6)
    return box


def build_back(card: dict, pal: dict, picked=None, width=330,
               mask_shown=(), on_mask=None) -> QWidget:
    """背面卡：问答放答案；选择题放「你选了… · 正确答案… · 答对了」+ 解析。"""
    box = CardBox(pal["back"], pal["ashadow"])
    box.setFixedWidth(width)
    box.body.addWidget(Ribbon("回答", pal["alabel"]))
    box.body.addSpacing(10)

    if card["type"] == "qa":
        box.body.addWidget(_body(card["a"] or "（无答案）", pal, width - 32, "back",
                                 16, False, 1.6, on_mask, mask_shown))
        return box

    answers = sorted(set(card.get("answer") or []))
    picks = sorted(_as_set(picked))
    letters = lambda idx: "、".join("ABCDEFG"[i] for i in idx) or "—"
    ok = bool(answers) and picks == answers

    # 回答卡结果水印：低透明度、压在文字下面
    wm = QLabel("✓" if ok else "✗", box)
    wm.setStyleSheet(
        "background:transparent;font-size:70px;font-weight:400;"
        + (f"color:rgba(46,158,103,0.16);" if ok else "color:rgba(217,83,79,0.16);")
    )
    wm.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    wm.move(width - 88, -2)
    wm.lower()

    if not picks:
        verdict, color = "（没有作答）", "#A0322E"
    elif ok:
        verdict, color = "答对了", "#1F6B45"
    else:
        verdict, color = "答错了", "#A0322E"

    # 结果行：只留「你选了… · 正确答案…」，对错由正面右上角水印表达
    row = QWidget()
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 0, 0, 8)
    rl.setSpacing(6)
    head = QLabel(f'<span style="color:{color};font-weight:700;font-size:15px">'
                  f'你选了 {letters(picks)} · 正确答案 {letters(answers)}</span>')
    head.setTextFormat(Qt.RichText)
    rl.addWidget(head)
    rl.addStretch(1)
    box.body.addWidget(row)

    if card.get("analysis"):
        box.body.addWidget(_body(card["analysis"], pal, width - 32, "back", 17, False, 1.65,
                                 on_mask, mask_shown))
    return box


def build_cards(card: dict, tpl_key: str, revealed: bool, picked=None,
                width=330, on_pick=None, mask_shown=(), on_mask=None) -> QWidget:
    """整块：正面卡 + 16px 间隔 + （已揭示时）背面卡。"""
    pal = palette(tpl_key)
    host = QWidget()
    host.setFixedWidth(width)
    lay = QVBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(build_front(card, pal, revealed, picked, width=width, on_pick=on_pick,
                              mask_shown=mask_shown, on_mask=on_mask))
    if revealed:
        lay.addSpacing(16)
        lay.addWidget(build_back(card, pal, picked, width=width,
                                 mask_shown=mask_shown, on_mask=on_mask))
    lay.addStretch(1)
    return host
