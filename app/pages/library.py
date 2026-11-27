# -*- coding: utf-8 -*-
"""pages/library.py - 知识域 → 圆桌（可嵌套）→ 卡包 → 卡组。"""
from __future__ import annotations

import time

from PySide6.QtCore import QSize, Qt, QPoint, QRectF, QTimer, Signal
from PySide6.QtGui import (QColor, QPainter, QPainterPath, QPen, QFont,
                           QFontMetrics, QTextLayout)
from PySide6.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, QWidget, QLineEdit,
                               QMessageBox, QMenu, QInputDialog, QDialog, QFileDialog,
                               QSizePolicy,
                               QDialogButtonBox, QPushButton, QScrollArea, QFrame, QListWidget, QListWidgetItem,
                               QTextEdit)

import formatting as F
import widgets as W
import theme
from pages.base import Page, label


def _date_text(ms: float) -> str:
    lt = time.localtime((ms or 0) / 1000)
    return f"{lt.tm_year}年{lt.tm_mon:02d}月{lt.tm_mday:02d}日"


class IconTile(QWidget):
    """左侧 48×48 图标块：圆桌=文件夹，卡包=清单纸。"""

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(48, 48)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QFrame().rect()
        p.setPen(Qt.NoPen)
        bg = "#F6EFDC" if self.kind == "round" else "#F1EFE8"
        p.setBrush(QColor(bg))
        p.drawRoundedRect(0, 0, 48, 48, 14, 14)

        if self.kind == "round":
            # 文件夹：背板 + 左上标签 + 内页
            pen = QPen(QColor("#E2B94F"), 1)
            p.setPen(pen)
            p.setBrush(QColor("#F5D97E"))
            p.drawRoundedRect(QRectF(9, 14, 30, 22), 4, 4)      # 背板
            p.drawRoundedRect(QRectF(9, 11, 14, 9), 2.5, 2.5)   # 标签
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FFEDB0"))
            p.drawRoundedRect(QRectF(12, 19.5, 24, 13), 3, 3)   # 内页
        else:
            # 清单纸 + 右上角橙点
            p.setBrush(QColor("#FFFFFF"))
            p.setPen(QPen(QColor("#E0DBCC"), 1))
            p.drawRoundedRect(13, 11, 22, 27, 4, 4)
            p.setPen(QPen(QColor("#CFC9BA"), 1.6, Qt.SolidLine, Qt.RoundCap))
            for i in range(4):
                y = 19 + i * 4.5
                p.drawLine(17, y, 31 if i % 2 == 0 else 28, y)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#F0A32E"))
            p.drawEllipse(QPoint(33, 14), 2.2, 2.2)


class EntityRow(W.ClickFrame):
    """圆桌 / 卡包 的列表行：图标 + 标题 + 日期统计 + ⋯；长按可拖动排序。"""

    drag_started = Signal()
    drag_moved = Signal(float)
    drag_finished = Signal()

    def __init__(self, kind: str, title: str, sub: str, on_more, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setObjectName("card")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(12)
        lay.addWidget(IconTile(kind), 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(4)
        # 单行截断：文案再长也不会把右侧 ⋯ 挤出屏幕
        t = OneLineLabel(title)
        t.setStyleSheet("font-size:14.5px;font-weight:700;")
        s = OneLineLabel(sub)
        s.setObjectName("sub")
        col.addWidget(t)
        col.addWidget(s)
        lay.addLayout(col, 1)

        more = W.MoreButton(32)
        more.setStyleSheet("background:transparent;border:none;color:#B5B0A4;font-size:16px;")
        more.setCursor(Qt.PointingHandCursor)
        more.clicked.connect(lambda: on_more(more))
        lay.addWidget(more, 0, Qt.AlignVCenter)
        self.more = more

        # 子控件不吃鼠标，保证按下事件落在整行上
        for w in self.findChildren(QWidget):
            if w is not more:
                w.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._press = None
        self._dragging = False
        self._lp = QTimer(self)
        self._lp.setSingleShot(True)
        self._lp.setInterval(320)
        self._lp.timeout.connect(self._enter_drag)

    # ---- 长按拖动 ----
    def _enter_drag(self):
        if self._press is None:
            return
        self._dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        self.drag_started.emit()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.position()
            self._lp.start()
            e.accept()              # 成为鼠标抓取者，后续 move/release 才会到这一行
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging:
            self.drag_moved.emit(e.globalPosition().y())
            e.accept()
            return
        if self._press is not None and (e.position() - self._press).manhattanLength() > 8:
            self._lp.stop()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._lp.stop()
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.PointingHandCursor)
            self.drag_finished.emit()
            self._press = None
            e.accept()
            return
        if (self._press is not None and e.button() == Qt.LeftButton
                and self.rect().contains(e.position().toPoint())):
            self.clicked.emit()
        self._press = None
        e.accept()


class DomainDialog(QDialog):
    """知识域管理：新增 / 删除。"""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("管理知识域")
        self.setMinimumSize(360, 300)
        self.resize(380, 430)
        self.setMinimumWidth(340)
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(6)
        holder = QWidget()
        holder.setLayout(self.list_box)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(holder)
        self.scroll.setFixedHeight(220)
        lay.addWidget(self.scroll)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("新知识域名称")
        add = QPushButton("添加")
        add.setObjectName("primary")
        add.clicked.connect(self._add)
        rl.addWidget(self.input, 1)
        rl.addWidget(add)
        lay.addWidget(row)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.button(QDialogButtonBox.Close).setText("关闭")
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._fill()
        W.center_dialog(self, parent)

    def _fill(self):
        W.clear_layout(self.list_box)
        for d in self.store.domains:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 6, 6, 6)
            rl.setSpacing(8)
            name = QLabel(d["name"])
            name.setStyleSheet("font-size:13px;font-weight:600;")
            rl.addWidget(name, 1)
            cnt = sum(1 for x in self.store.decks if x["domain"] == d["id"])
            info = QLabel(f"{cnt} 个卡包")
            info.setObjectName("sub")
            rl.addWidget(info)
            rb = QPushButton("重命名")
            rb.setStyleSheet(f"color:{W.T['ink2']};font-size:12px;")
            rb.setCursor(Qt.PointingHandCursor)
            rb.clicked.connect(lambda _, did=d["id"]: self._rename(did))
            rl.addWidget(rb)
            if len(self.store.domains) > 1:
                b = QPushButton("删除")
                b.setStyleSheet("color:#D9534F;font-size:12px;")
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _, did=d["id"]: self._del(did))
                rl.addWidget(b)
            row.setStyleSheet(f"background:{W.T['paper2']};border-radius:10px;")
            self.list_box.addWidget(row)
        self.list_box.addStretch(1)

    def _rename(self, did: str):
        d = self.store.domain(did)
        if not d:
            return
        name, ok = QInputDialog.getText(self, "重命名知识域", "名称", text=d["name"])
        if ok and name.strip():
            self.store.rename_domain(did, name.strip())
            self._fill()

    def _add(self):
        name = self.input.text().strip()
        if not name:
            return
        self.store.add_domain(name)
        self.input.clear()
        self._fill()

    def _del(self, did: str):
        target = next((d for d in self.store.domains if d["id"] != did), None)
        ok = QMessageBox.question(
            self, "删除知识域",
            f"删除「{self.store.domain(did)['name']}」？里面的圆桌与卡包会移到"
            f"「{target['name'] if target else '—'}」。")
        if ok == QMessageBox.Yes:
            self.store.delete_domain(did)
            self._fill()




def _line_count(text: str, font: QFont, width: int, limit: int = 0) -> int:
    """文本在给定宽度下排几行；limit > 0 时超过 limit 行立即返回。

    只创建前 limit + 1 行，避免对长文本做无谓的整段排版。
    """
    lay = QTextLayout(text, font)
    lay.beginLayout()
    n = 0
    try:
        while True:
            line = lay.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            n += 1
            if limit and n > limit:
                break
    finally:
        lay.endLayout()
    return n


def elide_lines(text: str, font: QFont, width: int, max_lines: int = 2) -> str:
    """最多 max_lines 行，超出用 … 结尾。

    对长文本用二分查找定位截断点。每次排版只算到 max_lines + 1 行，
    因此复杂度从 O(n²) 降到 O(log n)。结果与逐字符回退一致。
    """
    if not text:
        return text
    if _line_count(text, font, width, max_lines) <= max_lines:
        return text

    # text 本身已经超行，因此 text + … 必然也超行；0 个字符（只剩 …）一定能放下。
    lo, hi = 0, len(text) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        cand = text[:mid].rstrip() + "…"
        if _line_count(cand, font, width, max_lines) <= max_lines:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "…"


class PlusIcon(QWidget):
    """细线加号：两条 1.6px 圆头灰线，比字体加号更细更干净。"""

    def __init__(self, size: int = 18, color: str | None = None, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color or W.T["ink3"]

    def paintEvent(self, e):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(self._color), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2, self.height() / 2
        r = 5.6
        p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))


class GearButton(QPushButton):
    """自绘齿轮（避免 emoji 彩色字形）。"""

    def __init__(self, size: int = 32, color: str | None = None, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._color = color
        self.setStyleSheet("background:transparent;border:none;")

    def paintEvent(self, e):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        col = QColor(self._color or W.T["ink2"])
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        for i in range(8):
            a = math.radians(i * 45)
            x = cx + math.cos(a) * 6.2
            y = cy + math.sin(a) * 6.2
            p.save()
            p.translate(x, y)
            p.rotate(i * 45)
            p.drawRoundedRect(QRectF(-2.0, -2.0, 4.0, 4.0), 1.2, 1.2)
            p.restore()
        p.drawEllipse(QRectF(cx - 6.0, cy - 6.0, 12.0, 12.0))
        p.setBrush(QColor(W.T["paper2"]))
        p.drawEllipse(QRectF(cx - 2.6, cy - 2.6, 5.2, 5.2))


class PracticeIcon(QWidget):
    """练习图标：圆角块 + 闪电。"""

    def __init__(self, size: int = 42, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(W.T["brand_soft"]))
        p.drawRoundedRect(r, 12, 12)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.moveTo(w * 0.56, h * 0.22)
        path.lineTo(w * 0.36, h * 0.54)
        path.lineTo(w * 0.50, h * 0.54)
        path.lineTo(w * 0.44, h * 0.78)
        path.lineTo(w * 0.66, h * 0.46)
        path.lineTo(w * 0.51, h * 0.46)
        path.closeSubpath()
        p.setBrush(QColor(W.T["brand"]))
        p.drawPath(path)


class OneLineLabel(QLabel):
    """单行：超出用 … 截断。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full = text or ""
        self._last_width = -1
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setMinimumWidth(20)
        QLabel.setText(self, self._full)

    def setText(self, text: str):
        self._full = text or ""
        self._last_width = -1
        self._apply()

    def fullText(self) -> str:
        return self._full

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply()

    def _apply(self):
        w = max(20, self.width())
        if w == self._last_width:
            return
        self._last_width = w
        fm = self.fontMetrics()
        QLabel.setText(self, fm.elidedText(self._full, Qt.ElideRight, w))


_ELIDE_CACHE: dict = {}


def _elide_cached(text: str, font, width: int, lines: int) -> str:
    key = (text, width, lines, font.pixelSize(), font.bold())
    hit = _ELIDE_CACHE.get(key)
    if hit is not None:
        return hit
    out = elide_lines(text, font, width, lines)
    if len(_ELIDE_CACHE) > 3000:
        _ELIDE_CACHE.clear()
    _ELIDE_CACHE[key] = out
    return out


class LinesLabel(QLabel):
    """固定行数：不足也占满，超出用 … 截断。"""

    def __init__(self, text: str = "", px: int = 19, lines: int = 2,
                 bold: bool = True, color: str | None = None, parent=None):
        super().__init__(parent)
        self._full = text or ""
        self._lines = lines
        self._last_size = None
        f = QFont(theme.FONT)
        f.setPixelSize(px)
        f.setBold(bold)
        self.setFont(f)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # 全局 QSS 给 QWidget 定了 13px，这里必须用同等优先级覆盖字号。
        style = f"font-size:{px}px;font-weight:{700 if bold else 400};"
        if color:
            style += f"color:{color};"
        self.setStyleSheet(style)
        self.setFixedHeight(lines * QFontMetrics(f).lineSpacing())
        self._refresh()

    def setText(self, text: str):
        self._full = text or ""
        self._last_size = None
        self._refresh()

    def fullText(self) -> str:
        return self._full

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh()

    def _refresh(self):
        w = max(60, self.width())
        key = (self._full, w)
        if key == self._last_size:
            return
        self._last_size = key
        QLabel.setText(self, _elide_cached(self._full, self.font(), w, self._lines))


TwoLineLabel = LinesLabel


class MoveDialog(QDialog):
    """选目标位置：根目录或某个圆桌。"""

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("移动到…")
        self.resize(360, 400)
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        tip = QLabel("选择目标位置")
        tip.setObjectName("sub")
        lay.addWidget(tip)

        self.list = QListWidget()
        self.list.addItems(labels)
        self.list.setCurrentRow(0)
        self.list.setStyleSheet(
            f"QListWidget{{background:{W.T['panel']};border:1px solid {W.T['line']};"
            f"border-radius:10px;padding:4px;font-size:12.5px;}}"
            f"QListWidget::item{{padding:7px 8px;border-radius:7px;}}"
            f"QListWidget::item:selected{{background:{W.T['brand_soft']};"
            f"color:{W.T['brand']};}}")
        lay.addWidget(self.list, 1)

        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        cancel = QPushButton("取消")
        cancel.setFixedHeight(38)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};color:{W.T['ink']};border:none;"
            f"border-radius:12px;font-size:13px;font-weight:600;}}")
        cancel.clicked.connect(self.reject)
        bl.addWidget(cancel, 1)
        ok = QPushButton("移动到这里")
        ok.setFixedHeight(38)
        ok.setCursor(Qt.PointingHandCursor)
        ok.setStyleSheet(
            f"QPushButton{{background:{W.T['brand']};color:#FFFFFF;border:none;"
            f"border-radius:12px;font-size:13px;font-weight:600;}}")
        ok.clicked.connect(self.accept)
        bl.addWidget(ok, 1)
        lay.addWidget(btns)
        W.center_dialog(self, parent)

    def selected(self) -> str | None:
        item = self.list.currentItem()
        return item.text() if item else None


class MoveCardsDialog(QDialog):
    """批量移动卡片：列出卡组与卡片数，点选目标。"""

    def __init__(self, rows: list[dict], count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("移动卡片")
        self.setMinimumSize(380, 360)
        self.resize(400, min(520, 210 + 58 * max(1, len(rows))))
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")
        self._choice = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(12)

        title = QLabel("移动卡片")
        title.setStyleSheet(f"font-size:18px;font-weight:700;color:{W.T['ink']};")
        lay.addWidget(title)
        sub = QLabel(f"已选 {count} 张卡片 · 点选目标卡组")
        sub.setObjectName("sub")
        lay.addWidget(sub)

        self.list = QListWidget()
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setSpacing(6)
        self.list.setStyleSheet(
            f"QListWidget{{background:transparent;border:none;outline:none;}}"
            f"QListWidget::item{{background:{W.T['panel']};border:1px solid {W.T['line']};"
            f"border-radius:12px;padding:12px 14px;color:{W.T['ink']};font-size:13.5px;}}"
            f"QListWidget::item:selected{{background:{W.T['brand_soft']};"
            f"border:1px solid {W.T['brand']};color:{W.T['brand']};font-weight:600;}}")
        for row in rows:
            item = QListWidgetItem(f"{row['name']}")
            item.setSizeHint(QSize(0, 52))
            item.setData(Qt.UserRole, row["name"])
            self.list.addItem(item)
        if rows:
            self.list.setCurrentRow(0)
        lay.addWidget(self.list, 1)

        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(10)
        cancel = QPushButton("取消")
        cancel.setFixedHeight(42)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};color:{W.T['ink']};border:none;"
            f"border-radius:13px;font-size:13px;font-weight:600;}}")
        cancel.clicked.connect(self.reject)
        bl.addWidget(cancel, 1)
        ok = QPushButton("移动到这里")
        ok.setFixedHeight(42)
        ok.setCursor(Qt.PointingHandCursor)
        ok.setStyleSheet(
            f"QPushButton{{background:{W.T['brand']};color:#FFFFFF;border:none;"
            f"border-radius:13px;font-size:13px;font-weight:600;}}")
        ok.clicked.connect(self.accept)
        bl.addWidget(ok, 1)
        lay.addWidget(btns)
        W.center_dialog(self, parent)

    def selected(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None


class NewGroupDialog(QDialog):
    """新建卡组：一个输入框 + 取消/创建，回车即创建。"""

    def __init__(self, taken: set[str], deck_name: str = "", parent=None):
        super().__init__(parent)
        self.name = ""
        self._taken = {(t or "").strip() for t in taken}
        self.setWindowTitle("新建卡组")
        self.setFixedWidth(360)
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(8)

        title = QLabel("新建卡组")
        title.setStyleSheet(f"font-size:17px;font-weight:700;color:{W.T['ink']};")
        lay.addWidget(title)

        sub = QLabel(f"在「{deck_name}」里新建一个空卡组" if deck_name else "新建一个空卡组")
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        lay.addSpacing(6)

        self.input = QLineEdit()
        self.input.setPlaceholderText("给卡组起个名字")
        self.input.setMaxLength(80)
        self.input.setStyleSheet(
            f"QLineEdit{{background:{W.T['paper2']};color:{W.T['ink']};"
            f"border:1px solid {W.T['line']};border-radius:12px;"
            f"padding:10px 12px;font-size:14px;}}"
            f"QLineEdit:focus{{border:1px solid {W.T['brand']};"
            f"background:{W.T['panel']};}}")
        self.input.textChanged.connect(self._validate)
        self.input.returnPressed.connect(self._submit)
        lay.addWidget(self.input)

        self.hint = QLabel("")
        self.hint.setStyleSheet(f"color:{W.T['red']};font-size:11.5px;padding-left:2px;")
        self.hint.hide()
        lay.addWidget(self.hint)
        lay.addSpacing(8)

        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        bl.addStretch(1)
        cancel = QPushButton("取消")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setFixedHeight(40)
        cancel.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{W.T['ink2']};"
            f"font-size:13px;padding:0 14px;}}")
        cancel.clicked.connect(self.reject)
        bl.addWidget(cancel)
        self.ok_btn = W.PrimaryButton("创建")
        self.ok_btn.setFixedHeight(40)
        self.ok_btn.setMinimumWidth(96)
        self.ok_btn.setStyleSheet(
            f"QPushButton#primary{{background:{W.T['brand']};color:#FFFFFF;border:none;"
            f"border-radius:12px;font-size:13.5px;font-weight:700;padding:0 18px;}}"
            f"QPushButton#primary:hover{{background:{W.T['brand2']};}}"
            f"QPushButton#primary:disabled{{background:{W.T['paper2']};"
            f"color:{W.T['ink3']};}}")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self._submit)
        bl.addWidget(self.ok_btn)
        lay.addWidget(btns)

        self.input.setFocus()
        W.center_dialog(self, parent)

    def _validate(self, text: str):
        name = (text or "").strip()
        if not name:
            self.hint.hide()
            self.ok_btn.setEnabled(False)
            return
        if name in self._taken:
            self.hint.setText("已经有同名卡组了")
            self.hint.show()
            self.ok_btn.setEnabled(False)
            return
        self.hint.hide()
        self.ok_btn.setEnabled(True)

    def _submit(self):
        name = self.input.text().strip()
        if not name or name in self._taken:
            return
        self.name = name
        self.accept()


class LibraryPage(Page):
    def __init__(self, app, domain: str | None = None, round_id: str | None = None):
        self.domain = domain or getattr(app, "library_domain", None) or app.store.domains[0]["id"]
        self.round_id = round_id
        self.query = ""
        self._rows = []
        self._drag = None
        self._indicator = None
        super().__init__(app)

    def build(self):
        super().build()
        s = self.store
        self.app.library_domain = self.domain
        rnd = s.rnd(self.round_id) if self.round_id else None
        dom = s.domain(self.domain) or {"name": "—", "emoji": "✦"}

        if rnd:
            self.appbar(rnd["name"], None,
                        back=self.app.go_back,
                        right=self._actions_group(False))
        else:
            total_decks = len([d for d in s.decks if d["domain"] == self.domain])
            total_cards = sum(len(s.cards_of(d["id"]))
                              for d in s.decks if d["domain"] == self.domain)
            self.hero(
                "记忆",
                f"{len(s.domains)} 个知识域 · {total_decks} 个文件 · {total_cards} 张卡片",
                right=self._actions_group(True))

        # 知识域只在最上层显示
        if not rnd:
            self.add(self._domain_bar())

        # 搜索（当前层）
        search = QLineEdit()
        search.setPlaceholderText("搜索圆桌、文件或卡片")
        search.addAction(self._search_icon(), QLineEdit.LeadingPosition)
        search.setText(self.query)
        search.textChanged.connect(self._on_search)
        self.add(search)

        self.list_host = QWidget()
        self.list_lay = QVBoxLayout(self.list_host)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(10)
        self.add(self.list_host)
        self._render_list()
        self.stretch()

    @staticmethod
    def _search_icon():
        from PySide6.QtCore import QRectF, QPointF
        from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
        pm = QPixmap(32, 32)
        pm.setDevicePixelRatio(2)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(W.T["ink3"]), 1.7, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(7.2, 7.2), 4.6, 4.6)
        p.drawLine(QPointF(10.7, 10.7), QPointF(13.6, 13.6))
        p.end()
        return QIcon(pm)

    def _actions_group(self, with_manage: bool):
        """右上角只留一个细线加号：新建 / 管理知识域都收进它的菜单里。"""
        actions = QWidget()
        al = QHBoxLayout(actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(0)

        btn = W.ClickFrame()
        btn.setObjectName("plusIcon")
        btn.setFixedSize(32, 32)
        btn.setAttribute(Qt.WA_Hover, True)
        btn.setToolTip("新建圆桌 / 卡包，或管理知识域")
        btn.setStyleSheet(
            f"QFrame#plusIcon{{background:#FFF3D6;border:1.5px solid {W.T['ink']};"
            f"border-radius:16px;}}"
            f"QFrame#plusIcon:hover{{background:#FFE9BD;}}")
        lay = QHBoxLayout(btn)
        lay.setContentsMargins(0, 0, 0, 0)
        icon = PlusIcon(18, W.T["deep"])
        icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(icon, 0, Qt.AlignCenter)
        btn.clicked.connect(lambda: self._add_menu(btn, with_manage))
        al.addWidget(btn)
        return actions

    # ---------------- 知识域条 ----------------
    def _domain_bar(self) -> QWidget:
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(7)
        for d in self.store.domains:
            chip = W.Chip(d["name"], on=(d["id"] == self.domain))
            chip.clicked.connect(lambda _, did=d["id"]: self._set_domain(did))
            lay.addWidget(chip)
        lay.addStretch(1)
        return wrap

    def _set_domain(self, did: str):
        self.domain = did
        self.round_id = None
        self.build()

    def _add_domain(self):
        name, ok = QInputDialog.getText(self, "新建知识域", "名称")
        if ok and name.strip():
            d = self.store.add_domain(name.strip())
            self.domain = d["id"]
            self.round_id = None
            self.build()

    def _manage_domains(self):
        dlg = DomainDialog(self.store, self)
        dlg.exec()
        if not self.store.domain(self.domain):
            self.domain = self.store.domains[0]["id"]
        self.build()

    # ---------------- 列表 ----------------
    def _on_search(self, text: str):
        self.query = text
        self._render_list()

    @staticmethod
    def _parse_search(q: str):
        """支持 tag:xxx / is:new|due|suspended|learning|practice / deck:名称。"""
        text, tags, states, deck_name = [], [], [], None
        for tok in (q or "").split():
            low = tok.lower()
            if low.startswith("tag:") and len(tok) > 4:
                tags.append(tok[4:].lower())
            elif low.startswith("is:") and len(tok) > 3:
                states.append(low[3:])
            elif low.startswith("deck:") and len(tok) > 5:
                deck_name = tok[5:].lower()
            else:
                text.append(tok)
        return " ".join(text).lower(), tags, states, deck_name

    def _card_matches(self, c: dict, tags, states) -> bool:
        import time as _t
        if tags:
            have = {str(t).lower() for t in (c.get("tags") or [])}
            if not all(t in have for t in tags):
                return False
        now = int(_t.time() * 1000)
        for st in states:
            if st == "new" and int(c.get("reps") or 0) != 0:
                return False
            if st == "due" and not (c.get("due", 0) <= now
                                    and not c.get("suspended")
                                    and int(c.get("buried_until") or 0) <= now):
                return False
            if st == "suspended" and not c.get("suspended"):
                return False
            if st == "learning" and c.get("state") not in ("learning", "relearning"):
                return False
            if st == "practice" and not c.get("practice"):
                return False
        return True

    def _render_list(self):
        W.clear_layout(self.list_lay)
        s = self.store
        q = (self.query or "").strip().lower()
        text_q, tag_f, state_f, deck_f = self._parse_search(q)

        rounds = s.rounds_in(self.domain, self.round_id)
        decks = [d for d in s.decks_in(self.domain, self.round_id)
                 if not d.get("archived")]
        if q:
            rounds = [r for r in rounds if not text_q or text_q in r["name"].lower()]
            kept = []
            for d in decks:
                if deck_f and deck_f not in d["name"].lower():
                    continue
                if text_q and text_q not in d["name"].lower():
                    cards = [c for c in s.cards_of(d["id"])
                             if text_q in (c.get("q") or "").lower()]
                else:
                    cards = s.cards_of(d["id"])
                if tag_f or state_f:
                    cards = [c for c in cards if self._card_matches(c, tag_f, state_f)]
                    if not cards:
                        continue
                elif text_q and text_q not in d["name"].lower() and not cards:
                    continue
                kept.append(d)
            decks = kept

        # 顺序：保存的自定义顺序优先；圆桌永远排在卡包上面
        if not q:
            r_ids = [r["id"] for r in rounds]
            d_ids = [d["id"] for d in decks]
            r_ids = s.ordered_ids("round", self.domain, self.round_id, r_ids)
            d_ids = s.ordered_ids("deck", self.domain, self.round_id, d_ids)
            by_r = {r["id"]: r for r in rounds}
            by_d = {d["id"]: d for d in decks}
            rounds = [by_r[i] for i in r_ids]
            decks = [by_d[i] for i in d_ids]
        else:
            rounds = sorted(rounds, key=lambda r: r.get("created", 0))
            decks = sorted(decks, key=lambda d: d.get("created", 0))

        self._rows = []

        for r in rounds:
            # 圆桌只显示「时间 · 多少个卡包」，其余统计省略，避免手机上被截断
            dcount, _ccount, _rcount = s.subtree_counts(r["id"])
            sub = f"{_date_text(r.get('created'))} · {dcount} 个文件"
            row = EntityRow("round", r["name"], sub,
                            on_more=lambda btn, rr=r: self._round_menu(btn, rr))
            row.clicked.connect(lambda rr=r: self.app.show_page(
                "library", domain=self.domain, round_id=rr["id"]))
            self._wire_drag(row, "round", r["id"])
            self._rows.append(("round", r["id"], row))
            self.list_lay.addWidget(row)

        for d in decks:
            cards = s.cards_of(d["id"])
            # 卡包只显示「时间 · 多少张卡片」，不在行内展示到期数
            sub = f"{_date_text(d.get('created'))} · {len(cards)} 张卡片"
            row = EntityRow("deck", d["name"], sub,
                            on_more=lambda btn, dd=d: self._deck_menu(btn, dd))
            row.clicked.connect(lambda dd=d: self.app.show_page("deck", deck_id=dd["id"]))
            self._wire_drag(row, "deck", d["id"])
            self._rows.append(("deck", d["id"], row))
            self.list_lay.addWidget(row)

        if not rounds and not decks:
            box = W.Card(flat=True)
            box.body.setContentsMargins(18, 26, 18, 26)
            t = QLabel("这里还是空的" if not q else "没有匹配项")
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet("font-size:13px;font-weight:600;")
            tip = QLabel("点右上角 ＋ 新建圆桌或卡包" if not q else "换个关键词试试")
            tip.setObjectName("sub")
            tip.setAlignment(Qt.AlignCenter)
            box.body.addWidget(t)
            box.body.addWidget(tip)
            self.list_lay.addWidget(box)

    # ---------------- 移动到… ----------------
    def _collect_dests(self, domain, parent, prefix, kind, obj, labels, targets):
        s = self.store
        for r in s.rounds_in(domain, parent):
            if kind == "round" and (r["id"] == obj["id"]
                                    or s._is_descendant(r["id"], obj["id"])):
                continue
            labels.append(f"{prefix}{r['name']}")
            targets.append((domain, r["id"]))
            self._collect_dests(domain, r["id"], f"{prefix}{r['name']} / ",
                                kind, obj, labels, targets)

    def _move_node(self, kind: str, obj: dict):
        s = self.store
        labels, targets = [], []
        for d in s.domains:
            labels.append(f"{d['name']}（根目录）")
            targets.append((d["id"], None))
            self._collect_dests(d["id"], None, f"{d['name']} / ",
                                kind, obj, labels, targets)
        if not labels:
            return
        dlg = MoveDialog(labels, self)
        if dlg.exec() != QDialog.Accepted:
            return
        label = dlg.selected()
        if not label or label not in labels:
            return
        domain, parent = targets[labels.index(label)]
        if kind == "round":
            if not s.move_round(obj["id"], domain, parent):
                self.app.toast("不能移动到它自己的子圆桌里")
                return
        else:
            s.move_deck(obj["id"], domain, parent)
        self.app.toast(f"已移动到「{label}」")
        self.build()

    # ---------------- 拖动排序 ----------------
    def _wire_drag(self, row, kind: str, oid: str):
        row.drag_started.connect(lambda r=row, k=kind, i=oid: self._drag_begin(r, k, i))
        row.drag_moved.connect(lambda gy, r=row: self._drag_move(r, gy))
        row.drag_finished.connect(lambda r=row: self._drag_end(r))

    def _drag_begin(self, row, kind: str, oid: str):
        self._drag = {"kind": kind, "id": oid, "row": row, "target": 0}
        self._indicator = QFrame(self.list_host)
        self._indicator.setFixedHeight(3)
        self._indicator.setStyleSheet(f"background:{W.T['brand']};border-radius:2px;")
        self.list_lay.insertWidget(self.list_lay.indexOf(row), self._indicator)

    def _drag_move(self, row, global_y: float):
        if not getattr(self, "_drag", None) or self._drag["row"] is not row:
            return
        y = self.list_host.mapFromGlobal(QPoint(0, int(global_y))).y()
        n_round = sum(1 for k, _, _ in self._rows if k == "round")
        target = len(self._rows)
        for i, (kind, oid, r) in enumerate(self._rows):
            if y < r.y() + r.height() / 2:
                target = i
                break
        # 圆桌永远在上：圆桌最多插到卡包之前，卡包最少插在圆桌之后
        if self._drag["kind"] == "round":
            target = min(target, n_round)
        else:
            target = max(target, n_round)
        self._drag["target"] = target
        self.list_lay.removeWidget(self._indicator)
        if target < len(self._rows):
            self.list_lay.insertWidget(self.list_lay.indexOf(self._rows[target][2]),
                                       self._indicator)
        else:
            self.list_lay.insertWidget(
                self.list_lay.indexOf(self._rows[-1][2]) + 1, self._indicator)
        self._indicator.show()

    def _drag_end(self, row):
        d = getattr(self, "_drag", None)
        self._drag = None
        if self._indicator is not None:
            self._indicator.deleteLater()
            self._indicator = None
        if not d or d["row"] is not row:
            self.build()
            return
        kind, oid, target = d["kind"], d["id"], d["target"]
        same = [i for k, i, _ in self._rows if k == kind]
        if oid not in same:
            self.build()
            return
        old = same.index(oid)
        rest = [i for i in same if i != oid]
        pos = target - (1 if old < target else 0)
        if kind == "deck":
            pos -= sum(1 for k, _, _ in self._rows if k == "round")
        pos = max(0, min(len(rest), pos))
        rest.insert(pos, oid)
        self.store.set_order(kind, self.domain, self.round_id, rest)
        self.build()

    # ---------------- 新建 ----------------
    def _build_add_menu(self, with_manage: bool = False) -> QMenu:
        """新建菜单：圆桌 / 卡包 / 知识域；最上层还会带「管理知识域」。"""
        m = QMenu(self)
        m.addAction("新建圆桌", self._new_round)
        m.addAction("新建卡包", self._new_deck)
        if self.round_id is None:
            m.addSeparator()
            m.addAction("新建知识域", self._add_domain)
            if with_manage:
                m.addAction("管理知识域", self._manage_domains)
        return m

    def _add_menu(self, anchor: QWidget, with_manage: bool = False):
        m = self._build_add_menu(with_manage)
        m.exec(anchor.mapToGlobal(QPoint(0, anchor.height() + 4)))

    def _new_round(self):
        name, ok = QInputDialog.getText(self, "新建圆桌", "名称")
        if ok and name.strip():
            self.store.add_round(name.strip(), self.domain, self.round_id)
            self.build()

    def _new_deck(self):
        name, ok = QInputDialog.getText(self, "新建卡包", "名称")
        if ok and name.strip():
            self.store.add_deck(name.strip(), self.domain, self.round_id)
            self.build()

    # ---------------- 行菜单 ----------------
    def _round_menu(self, anchor: QWidget, r: dict):
        m = QMenu(self)
        m.addAction("打开", lambda: self.app.show_page(
            "library", domain=self.domain, round_id=r["id"]))
        m.addAction("新建子圆桌", lambda: self._new_sub_round(r["id"]))
        m.addAction("新建卡包", lambda: self._new_sub_deck(r["id"]))
        m.addSeparator()
        m.addAction("移动到…", lambda: self._move_node("round", r))
        m.addAction("重命名", lambda: self._rename_round(r))
        m.addAction("删除", lambda: self._delete_round(r))
        m.exec(anchor.mapToGlobal(QPoint(0, anchor.height())))

    def _deck_menu(self, anchor: QWidget, d: dict):
        m = QMenu(self)
        m.addAction("打开", lambda: self.app.show_page("deck", deck_id=d["id"]))
        m.addAction("卡组选项", lambda: self.app.show_page(
            "sched", deck_id=d["id"]))
        m.addAction("移动到…", lambda: self._move_node("deck", d))
        m.addAction("重命名", lambda: self._rename_deck(d))
        m.addSeparator()
        m.addAction("完成", lambda: self._archive_deck(d))
        m.addAction("删除", lambda: self._delete_deck(d))
        m.exec(anchor.mapToGlobal(QPoint(0, anchor.height())))

    def _archive_deck(self, d: dict):
        n = len(self.store.cards_of(d["id"]))
        if QMessageBox.question(
                self, "完成",
                f"把「{d['name']}」标记为完成？\n{n} 张卡片不再参与学习与复习，进度保留。") != QMessageBox.Yes:
            return
        self.store.archive_deck(d["id"], True)
        self.app.toast(f"「{d['name']}」已完成")
        self.build()

    def _new_sub_round(self, rid: str):
        name, ok = QInputDialog.getText(self, "新建子圆桌", "名称")
        if ok and name.strip():
            self.store.add_round(name.strip(), self.domain, rid)
            self.build()

    def _new_sub_deck(self, rid: str):
        name, ok = QInputDialog.getText(self, "新建卡包", "名称")
        if ok and name.strip():
            self.store.add_deck(name.strip(), self.domain, rid)
            self.build()

    def _rename_round(self, r: dict):
        name, ok = QInputDialog.getText(self, "重命名圆桌", "名称", text=r["name"])
        if ok and name.strip():
            self.store.rename_round(r["id"], name)
            self.build()

    def _rename_deck(self, d: dict):
        name, ok = QInputDialog.getText(self, "重命名卡包", "名称", text=d["name"])
        if ok and name.strip():
            self.store.rename_deck(d["id"], name)
            self.build()

    def _delete_round(self, r: dict):
        ok = QMessageBox.question(
            self, "删除圆桌",
            f"删除「{r['name']}」？\n里面的子圆桌与卡包会移到上一层，不会丢。")
        if ok == QMessageBox.Yes:
            self.store.delete_round(r["id"])
            self.build()

    def _delete_deck(self, d: dict):
        n = len(self.store.cards_of(d["id"]))
        ok = QMessageBox.question(
            self, "删除卡包",
            f"删除「{d['name']}」及其 {n} 张卡片？\n会放进回收站（细数 → ⋯ → 回收站），可以恢复。")
        if ok == QMessageBox.Yes:
            self.store.delete_deck(d["id"])
            self.build()


class PracticeMark(QWidget):
    """练习标记：闪电，加入练习时用品牌色。"""

    def __init__(self, active: bool = False, size: int = 15, parent=None):
        super().__init__(parent)
        self.active = active
        self.setFixedSize(size, size)

    def set_active(self, active: bool):
        if active != self.active:
            self.active = active
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        col = QColor(W.T["brand"] if self.active else W.T["ink3"])
        path = QPainterPath()
        path.moveTo(w * 0.58, 0)
        path.lineTo(w * 0.18, h * 0.56)
        path.lineTo(w * 0.45, h * 0.56)
        path.lineTo(w * 0.38, h)
        path.lineTo(w * 0.82, h * 0.42)
        path.lineTo(w * 0.54, h * 0.42)
        path.closeSubpath()
        if self.active:
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawPath(path)
        else:
            pen = QPen(col, 1.2)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)


class CardEditDialog(QDialog):
    """编辑一张卡片：类型 / 问题 / 答案 / 选项 / 解析。"""

    def __init__(self, card: dict, parent=None):
        super().__init__(parent)
        self.card = card
        self.ctype = card.get("type", "qa")
        self.setWindowTitle("编辑卡片")
        self.resize(400, 560)
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        # 类型
        seg = QWidget()
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(6)
        self.type_chips = {}
        for key, name in (("qa", "问答"), ("single", "单选"), ("multi", "多选")):
            chip = W.Chip(name, on=(self.ctype == key))
            chip.clicked.connect(lambda _, k=key: self._set_type(k))
            sl.addWidget(chip)
            self.type_chips[key] = chip
        sl.addStretch(1)
        lay.addWidget(seg)

        lay.addWidget(self._cap("问题"))
        self.q = QTextEdit()
        self.q.setPlainText(card.get("q", ""))
        self.q.setFixedHeight(84)
        lay.addWidget(self.q)

        self.a_cap = self._cap("答案")
        self.a = QTextEdit()
        self.a.setPlainText(card.get("a", ""))
        self.a.setFixedHeight(84)
        lay.addWidget(self.a_cap)
        lay.addWidget(self.a)

        self.opt_cap = self._cap("选项（每行一个）")
        self.opts = QTextEdit()
        self.opts.setPlainText("\n".join(card.get("options") or []))
        self.opts.setFixedHeight(96)
        lay.addWidget(self.opt_cap)
        lay.addWidget(self.opts)

        self.ans_cap = self._cap("正确答案（字母，如 ACD）")
        self.ans = QLineEdit("".join(
            "ABCDEF"[i] for i in sorted(card.get("answer") or [])))
        lay.addWidget(self.ans_cap)
        lay.addWidget(self.ans)

        lay.addWidget(self._cap("解析"))
        self.analysis = QTextEdit()
        self.analysis.setPlainText(card.get("analysis", ""))
        self.analysis.setFixedHeight(70)
        lay.addWidget(self.analysis)

        lay.addStretch(1)
        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        cancel = QPushButton("取消")
        cancel.setFixedHeight(38)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};color:{W.T['ink']};border:none;"
            f"border-radius:12px;font-size:13px;font-weight:600;}}")
        cancel.clicked.connect(self.reject)
        bl.addWidget(cancel, 1)
        save = QPushButton("保存")
        save.setFixedHeight(38)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(
            f"QPushButton{{background:{W.T['brand']};color:#FFFFFF;border:none;"
            f"border-radius:12px;font-size:13px;font-weight:700;}}")
        save.clicked.connect(self.accept)
        bl.addWidget(save, 1)
        lay.addWidget(btns)

        self._sync_visibility()

    def _cap(self, text: str) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("sub")
        return lb

    def _set_type(self, key: str):
        self.ctype = key
        for k, chip in self.type_chips.items():
            chip.set_on(k == key)
        self._sync_visibility()

    def _sync_visibility(self):
        is_qa = self.ctype == "qa"
        for w in (self.a_cap, self.a):
            w.setVisible(is_qa)
        for w in (self.opt_cap, self.opts, self.ans_cap, self.ans):
            w.setVisible(not is_qa)

    def accept(self):
        c = self.card
        c["type"] = self.ctype
        c["q"] = self.q.toPlainText().strip()
        c["analysis"] = self.analysis.toPlainText().strip()
        if self.ctype == "qa":
            c["a"] = self.a.toPlainText().strip()
            c["options"] = []
            c["answer"] = []
        else:
            opts = [ln.strip() for ln in self.opts.toPlainText().splitlines()
                    if ln.strip()]
            c["options"] = opts
            c["a"] = ""
            letters = self.ans.text().strip().upper()
            idx = sorted({ord(ch) - 65 for ch in letters
                          if "A" <= ch <= "F" and ord(ch) - 65 < len(opts)})
            c["answer"] = idx
        super().accept()


class BrowseCard(W.ClickFrame):
    """浏览网格卡片：问题 + 摘要 + 状态；批量模式下右上角可勾选。

    控件结构只建一次，滚动时通过 update_card() 复用，避免反复创建 QLabel。
    """

    HEIGHT = 178
    _STAGE_KIND = {"新卡": "plain", "遗忘复习": "accent", "学习中": "brand"}
    _TYPE_BADGE = {"qa": ("问", "qa"), "single": ("单", "single"),
                   "multi": ("多", "multi")}

    def __init__(self, card: dict, stage: str, width: int, batch=False,
                 checked=False, parent=None):
        super().__init__(parent)
        self.setObjectName("browseCard")
        self._selected = checked
        self._batch = batch
        self.card_id = card["id"]
        self.setFixedWidth(width)
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.PointingHandCursor)

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(13, 12, 13, 10)
        self._lay.setSpacing(7)

        self.q = LinesLabel("", 13, lines=3, bold=True, color=W.T["ink"])
        self.a = LinesLabel("", 11, lines=3, bold=False, color=W.T["ink2"])
        self._lay.addWidget(self.q)
        self._lay.addWidget(self.a)
        self._lay.addStretch(1)

        foot = QWidget()
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(6)
        self.pill = W.Pill(stage, self._STAGE_KIND.get(stage, "plain"))
        self.badge = W.TypeBadge("问", "qa")
        fl.addWidget(self.pill)
        fl.addWidget(self.badge)
        fl.addStretch(1)
        self.mark = PracticeMark(False, 15)
        self.tag = QLabel("练习")
        self.tag.setStyleSheet(f"color:{W.T['brand']};font-size:10px;font-weight:600;")
        fl.addWidget(self.mark)
        fl.addWidget(self.tag)
        self._lay.addWidget(foot)

        self.box = W.SelectBox(checked=checked, parent=self)
        self.box.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.box.setVisible(batch)
        self.box.move(width - 30, 10)
        self.box.raise_()
        self.box.move(self.width() - 30, 6)
        self.box.raise_()
        self.box.move(self.width() - 30, 6)
        self.box.raise_()
        self._border = None
        self.update_card(card, stage, batch, checked)

    def update_card(self, card: dict, stage: str, batch: bool, checked: bool):
        self.card_id = card["id"]
        self.q.setText(F.to_plain(card.get("q") or ""))
        preview = card.get("a") or card.get("analysis") or "（无答案）"
        self.a.setText(F.to_plain(preview))
        self.pill.setText(stage)
        self.pill.set_kind(self._STAGE_KIND.get(stage, "plain"))
        tchar, tkind = self._TYPE_BADGE.get(card.get("type") or "qa", ("问", "qa"))
        self.badge.set_kind(tchar, tkind)
        in_prac = bool(card.get("practice"))
        self.mark.set_active(in_prac)
        self.tag.setVisible(in_prac)
        if batch != self._batch:
            self.set_batch(batch)
        if checked != self._selected:
            self.set_selected(checked)
        self._style()

    def _style(self):
        border = W.T["brand"] if (self._batch and self._selected) else W.T["line"]
        if border == self._border:
            return
        self._border = border
        self.setStyleSheet(
            f"QFrame#browseCard{{background:{W.T['panel']};border:1px solid {border};"
            f"border-radius:14px;}}")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "box", None) is not None:
            self.box.move(self.width() - 30, 10)

    def set_batch(self, on: bool):
        if on == self._batch:
            return
        self._batch = on
        self._lay.setContentsMargins(13, 12, 34 if on else 13, 10)
        self.box.setVisible(on)
        self._style()

    def set_selected(self, on: bool):
        if on == self._selected:
            return
        self._selected = on
        self.box.setChecked(on)
        self._style()


class BrowseListRow(W.ClickFrame):
    """一行：勾选框槽位 + 标题/摘要 + 底部（题型 / 练习 / 状态）。"""

    HEIGHT = 110
    _STAGE_KIND = {"新卡": "plain", "遗忘复习": "accent", "学习中": "brand"}
    _TYPE_BADGE = {"qa": ("问", "qa"), "single": ("单", "single"),
                   "multi": ("多", "multi")}

    def __init__(self, card: dict, stage: str, batch=False, checked=False,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._selected = checked
        self._batch = batch
        self.card_id = card["id"]
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        # 勾选框：右上角浮层，不占布局、不挤压文字（和网格一致）
        self.box = W.SelectBox(checked=checked, parent=self)
        self.box.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.box.setVisible(batch)

        right = QVBoxLayout()
        right.setSpacing(5)
        self.q = LinesLabel("", 13, lines=2, bold=True, color=W.T["ink"])
        self.a = LinesLabel("", 11, lines=1, bold=False, color=W.T["ink2"])
        right.addWidget(self.q)
        right.addWidget(self.a)

        foot = QWidget()
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(6)
        self.badge = W.TypeBadge("问", "qa")
        fl.addWidget(self.badge, 0, Qt.AlignVCenter)
        self.mark = PracticeMark(False, 14)
        fl.addWidget(self.mark, 0, Qt.AlignVCenter)
        self.tag = QLabel("练习")
        self.tag.setStyleSheet(
            f"color:{W.T['brand']};font-size:10px;font-weight:600;")
        self.tag.setVisible(False)
        fl.addWidget(self.tag, 0, Qt.AlignVCenter)
        fl.addStretch(1)
        self.pill = W.Pill(stage, "plain")
        fl.addWidget(self.pill, 0, Qt.AlignVCenter)
        right.addWidget(foot)
        lay.addLayout(right, 1)

        self.box.move(self.width() - 30, 6)
        self.box.raise_()
        self._border = None
        self.update_card(card, stage, batch, checked)

    def update_card(self, card: dict, stage: str, batch: bool, checked: bool):
        self.card_id = card["id"]
        self.q.setText(F.to_plain(card.get("q") or ""))
        preview = card.get("a") or card.get("analysis") or "（无答案）"
        self.a.setText(F.to_plain(preview))
        tchar, tkind = self._TYPE_BADGE.get(card.get("type") or "qa", ("问", "qa"))
        self.badge.set_kind(tchar, tkind)
        self.pill.setText(stage)
        self.pill.set_kind(self._STAGE_KIND.get(stage, "plain"))
        in_prac = bool(card.get("practice"))
        self.mark.set_active(in_prac)
        self.tag.setVisible(in_prac)
        if batch != self._batch:
            self.set_batch(batch)
        if checked != self._selected:
            self.set_selected(checked)
        self._style()

    def _style(self):
        border = W.T["brand"] if (self._batch and self._selected) else W.T["line"]
        if border == self._border:
            return
        self._border = border
        self.setStyleSheet(
            f"QFrame#card{{background:{W.T['panel']};border:1px solid {border};"
            f"border-radius:14px;}}")

    def set_batch(self, on: bool):
        if on == self._batch:
            return
        self._batch = on
        self.box.setVisible(on)
        self.box.move(self.width() - 30, 6)
        self.box.raise_()
        self._style()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.box.move(self.width() - 30, 6)
        self.box.raise_()

    def set_selected(self, on: bool):
        if on == self._selected:
            return
        self._selected = on
        self.box.setChecked(on)
        self._style()


class VirtualCardList(QWidget):
    """浏览卡片列表的虚拟化容器。

    只给视口附近的行创建控件，滚动时复用；卡片有几百上千张时，
    创建/布局开销基本恒定，不会一次性建出成千上万个 QLabel。
    """

    GAP = 10
    TOP = 8
    BOTTOM = 8
    RIGHT = 6

    def __init__(self, cards: list, view: str, batch: bool, picked: set,
                 width: int, stage_fn, on_click, scroll: QScrollArea,
                 parent=None):
        super().__init__(parent)
        self.cards = cards
        self.view = view
        self._batch = batch
        self.picked = picked
        self._stage_fn = stage_fn
        self._on_click = on_click
        self._scroll = scroll
        self._cols = 2 if view == "grid" else 1
        self._item_h = BrowseCard.HEIGHT if view == "grid" else BrowseListRow.HEIGHT
        self._pool: list[QWidget] = []
        self._live: dict[int, QWidget] = {}
        self._syncing = False
        self._last_span = None
        self._bound_width = 0
        self._fallback_width = width
        self.setStyleSheet("background:transparent;")
        self.setMinimumHeight(self._content_height(width))
        scroll.verticalScrollBar().valueChanged.connect(self.sync)
        scroll.verticalScrollBar().rangeChanged.connect(self.sync)
        # 等 QScrollArea 把宿主调整到真实视口宽度后再建控件，避免先用错误宽度排版。
        self._init_timer = QTimer(self)
        self._init_timer.setSingleShot(True)
        self._init_timer.timeout.connect(self.sync)
        self._init_timer.start(0)

    # ---- 几何 ----
    def _host_width(self) -> int:
        w = self.width()
        return w if w >= 200 else max(280, self._fallback_width - 40)

    def _card_width(self, width: int) -> int:
        avail = max(120, int(width) - self.RIGHT)
        if self._cols == 2:
            return max(110, (avail - self.GAP) // 2)
        return avail

    def _content_height(self, width: int) -> int:
        n = len(self.cards)
        rows = max(1, (n + self._cols - 1) // self._cols)
        return self.TOP + rows * self._item_h + max(0, rows - 1) * self.GAP + self.BOTTOM

    def resizeEvent(self, e):
        super().resizeEvent(e)
        h = self._content_height(self._host_width())
        if h != self.minimumHeight():
            self.setMinimumHeight(h)
        self.sync()

    # ---- 滚动复用 ----
    def _new_widget(self, card: dict) -> QWidget:
        cw = self._card_width(self._host_width())
        checked = card["id"] in self.picked
        if self.view == "grid":
            w = BrowseCard(card, self._stage_fn(card), cw, self._batch, checked, self)
        else:
            w = BrowseListRow(card, self._stage_fn(card), self._batch, checked, self)
        w.clicked.connect(lambda _=None, w=w: self._on_click(w.card_id))
        return w

    def sync(self, *_, force: bool = False):
        if self._syncing:
            return
        self._syncing = True
        try:
            vp = self._scroll.viewport().height() if self._scroll else 700
            vp = max(160, vp)
            sb = self._scroll.verticalScrollBar().value() if self._scroll else 0
            row_h = self._item_h + self.GAP
            # 上下各留一行缓冲，快速滚动时不会露白
            first_row = max(0, (sb - row_h) // row_h)
            last_row = (sb + vp) // row_h + 2
            first = first_row * self._cols
            last = min(len(self.cards), last_row * self._cols)
            cw = self._card_width(self._host_width())
            if cw != self._bound_width:
                force = True
                self._bound_width = cw
            # 同一段可见区间不重复搬运控件（滚动条信号会连发两次）
            span = (first, last, cw)
            if not force and self._last_span == span:
                return
            self._last_span = span

            for idx in [i for i in self._live if i < first or i >= last]:
                w = self._live.pop(idx)
                w.hide()
                self._pool.append(w)

            for idx in range(first, last):
                w = self._live.get(idx)
                if w is None:
                    if self._pool:
                        card = self.cards[idx]
                        w = self._pool.pop()
                        w.update_card(card, self._stage_fn(card), self._batch,
                                      card["id"] in self.picked)
                    else:
                        w = self._new_widget(self.cards[idx])
                    self._live[idx] = w
                elif force:
                    w.update_card(self.cards[idx], self._stage_fn(self.cards[idx]),
                                  self._batch, self.cards[idx]["id"] in self.picked)
                if self._cols == 2:
                    x = (idx % 2) * (cw + self.GAP)
                    y = self.TOP + (idx // 2) * row_h
                else:
                    x = 0
                    y = self.TOP + idx * row_h
                w.setFixedWidth(cw)
                w.setGeometry(x, y, cw, self._item_h)
                w.show()
        finally:
            self._syncing = False

    # ---- 批量选择 ----
    def set_selected(self, card_id: str, on: bool):
        for w in self._live.values():
            if w.card_id == card_id:
                w.set_selected(on)
                break

    def refresh_selection(self):
        for w in self._live.values():
            w.set_selected(w.card_id in self.picked)


class DeckPage(Page):
    def __init__(self, app, deck_id: str):
        self.deck_id = deck_id
        self.mode = getattr(app, "deck_mode", "learn")
        self._swipes = []
        self._rows = []
        self._active_order = []
        self._indicator = None
        self._drag_row = None
        self._drag_target = None
        self.selected_group = (app.deck_selection.get(deck_id)
                               or app.store.selected_group(deck_id))
        self.list_content = None
        self.list_lay = None
        self.browse_view = getattr(app, "browse_view", "grid")
        self.batch = False
        self.picked = set()
        self._virtual = None
        self._bar = None
        super().__init__(app)

    def _clear_root(self):
        lay = self.layout()
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def build(self):
        # 不用 Page 的整页滚动：改成「固定头部 + 下方内部滚动框」
        self._clear_root()
        self._swipes = []
        self._rows = []
        self._indicator = None
        s = self.store
        d = s.deck(self.deck_id) or {"name": "—", "color": "#888", "template": "sky", "groups": []}
        cards = s.cards_of(self.deck_id)
        due = s.due_cards(self.deck_id)
        order = s.ordered_groups(self.deck_id)
        archived = s.archived_groups(self.deck_id)
        completed = s.completed_groups(self.deck_id)
        active = [g for g in order if g not in archived]
        stored = [g for g in order if g in archived]
        # 一次分组，后面按卡组取卡片不再反复扫全量。
        by_group: dict[str, list] = {}
        for c in cards:
            by_group.setdefault(c.get("group", "未分组"), []).append(c)

        # 永远有选中：上次的 → 第一个
        sel = self.selected_group
        if sel not in active:
            sel = active[0] if active else None
        self.selected_group = sel
        if sel:
            s.save_selection(self.deck_id, sel)
            self.app.deck_selection[self.deck_id] = sel
        self._active_order = active

        sel_cards = by_group.get(sel, []) if sel else cards
        prac_all = s.practice_cards(self.deck_id)
        n_prac = len([c for c in prac_all if c.get("group") == sel]) if sel else 0
        n_prac_all = len(prac_all)
        n_prac_groups = len({c.get("group") for c in prac_all})
        sel_due = sum(1 for c in due if c.get("group") == sel)
        done = sum(1 for c in sel_cards if c["reps"] > 0)
        pct = round(done / len(sel_cards) * 100) if sel_cards else 0

        # 顶部固定区（注意：别用 top 这个名字，下面概览卡也用了 top）
        head_holder = QWidget()
        self._head_holder = head_holder
        self.top_lay = QVBoxLayout(head_holder)
        self.top_lay.setContentsMargins(0, 0, 0, 8)
        self.top_lay.setSpacing(0)

        imp = W.Chip("导入")
        imp.clicked.connect(self._import_word)
        # 固定在头部的 appbar：返回 / 卡包名 / 导入，不会被下方列表滚走
        band = W.BandHeader()
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(8)
        back = W.BackButton(30)
        back.set_light(True)
        back.clicked.connect(self.app.go_back)
        bl.addWidget(back, 0, Qt.AlignVCenter)
        title = QLabel(d["name"])
        title.setObjectName("h1")
        bl.addWidget(title, 1)
        bl.addWidget(imp, 0, Qt.AlignVCenter)
        band.lay.addWidget(bar)
        self.top_lay.addWidget(band)

        # 色带下方内容：左右 20px 边距（色带本身铺满整宽）
        content = QWidget()
        self._head_content = content
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(20, 16, 20, 0)
        self.body.setSpacing(12)
        self.top_lay.addWidget(content)

        # 三档
        seg = QWidget()
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(3)
        seg.setObjectName("segWrap")
        seg.setStyleSheet(
            f"QWidget#segWrap{{background:{W.T['paper2']};border-radius:18px;}}")
        for key, name in (("practice", "刷题练习"), ("learn", "学习记忆"), ("browse", "浏览卡片")):
            b = W.Chip(name, on=(self.mode == key))
            b.clicked.connect(lambda _, k=key: self._set_mode(k))
            sl.addWidget(b, 1)
        self.add(seg)

        # 概览：环形 = 当前选中卡组
        card = W.Card()
        if self.mode in ("learn", "browse"):
            card.body.setContentsMargins(16, 12, 16, 11)
            card.body.setSpacing(0)
        top = QWidget()
        tl = QHBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        col = QVBoxLayout()
        col.setSpacing(2)
        meta = QLabel(f"{len(cards)} 张 · {len(order)} 个卡组")
        meta.setStyleSheet(
            f"background:{W.T['paper2']};color:{W.T['ink2']};border-radius:9px;"
            f"font-size:10.5px;font-weight:600;padding:3px 9px;")
        meta.setFixedHeight(20)
        erow = QWidget()
        el = QHBoxLayout(erow)
        el.setContentsMargins(0, 0, 0, 0)
        el.addWidget(meta, 0, Qt.AlignLeft)
        el.addStretch(1)
        col.addWidget(erow)
        if self.mode != "practice":
            col.addWidget(TwoLineLabel(sel or d["name"]))
        if self.mode in ("learn", "browse"):
            now = time.time() * 1000
            n_rev = sum(1 for c in sel_cards
                        if not c.get("suspended") and int(c.get("reps") or 0) > 0
                        and (c.get("due") or 0) <= now)
            n_new = sum(1 for c in sel_cards
                        if not c.get("suspended") and int(c.get("reps") or 0) == 0)
            dot = f'<span style="color:{W.T["line"]};">&nbsp;&nbsp;·&nbsp;&nbsp;</span>'
            strip = QLabel(
                f'<span style="color:{W.T["ink"]};font-size:16px;font-weight:700;">{len(sel_cards)}</span>'
                f'<span style="color:{W.T["ink3"]};font-size:11px;"> 卡片</span>' + dot +
                f'<span style="color:{W.T["brand"]};font-size:16px;font-weight:700;">{n_rev}</span>'
                f'<span style="color:{W.T["ink3"]};font-size:11px;"> 待复习</span>' + dot +
                f'<span style="color:#B8792A;font-size:16px;font-weight:700;">{n_new}</span>'
                f'<span style="color:{W.T["ink3"]};font-size:11px;"> 待新学</span>')
            strip.setTextFormat(Qt.RichText)
            strip.setFixedHeight(20)
            col.addSpacing(4)
            col.addWidget(strip)



        tl.addLayout(col, 1)
        if self.mode == "learn":
            tl.addWidget(W.Ring(pct, 54, 6, track=W.T["brand_soft"]), 0, Qt.AlignVCenter)
        elif self.mode == "browse" and n_prac:
            chip = QLabel(f"{n_prac} 张在练")
            chip.setStyleSheet(
                f"background:{W.T['brand_soft']};color:{W.T['brand']};border-radius:11px;"
                f"font-size:11px;font-weight:700;padding:4px 10px;")
            chip.setFixedHeight(22)
            tl.addWidget(chip, 0, Qt.AlignVCenter)
        card.body.addWidget(top)

        if self.mode == "practice":
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background:{W.T['line']};")
            card.body.addWidget(line)
            mastered = sum(1 for c in prac_all if c.get("interval", 0) >= 21)
            stats = QWidget()
            sl = QHBoxLayout(stats)
            sl.setContentsMargins(0, 2, 0, 0)
            sl.setSpacing(0)
            for i, (num, cap) in enumerate(((n_prac_all, "在练卡片"),
                                            (n_prac_groups, "覆盖卡组"),
                                            (mastered, "已掌握"))):
                if i:
                    div = QFrame()
                    div.setFixedWidth(1)
                    div.setStyleSheet(f"background:{W.T['line']};")
                    sl.addWidget(div)
                c2 = QVBoxLayout()
                c2.setSpacing(1)
                n2 = QLabel(str(num))
                n2.setAlignment(Qt.AlignCenter)
                n2.setStyleSheet(f"font-size:20px;font-weight:700;color:{W.T['brand']};")
                l2 = QLabel(cap)
                l2.setObjectName("sub")
                l2.setAlignment(Qt.AlignCenter)
                c2.addWidget(n2)
                c2.addWidget(l2)
                sl.addLayout(c2, 1)
            card.body.addWidget(stats)

        card.setMinimumHeight(122)      # 三种模式概览卡等高
        self.add(card)

        # 「卡组」标题固定在滚动区上方
        if self.mode == "learn":
            self.body = self.top_lay
            new_group = W.IconButton("＋", 32)
            new_group.setToolTip("新建卡组")
            new_group.clicked.connect(self._new_group)
            self.section("卡组", new_group)
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background:{W.T['line']};")
            self.body.addWidget(sep)
        elif self.mode == "browse":
            self.body = self.top_lay
            self._browse_controls()

        # ---- 以下内容装进可滚动区（无边框） ----
        # 只做滚动容器，不加背景和边框（保持页面通透）
        box = QWidget()
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(0, 0, 0, 0)

        self.list_content = QWidget()
        self.list_content.setObjectName("listBody")
        self.list_content.setStyleSheet("QWidget#listBody{background:transparent;}")
        self.list_lay = QVBoxLayout(self.list_content)
        self.list_lay.setContentsMargins(0, 8, 6, 0)
        self.list_lay.setSpacing(10)
        self.list_lay.setAlignment(Qt.AlignTop)

        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_scroll.setFrameShape(QFrame.NoFrame)
        self.list_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.list_scroll.setWidget(self.list_content)
        box_lay.addWidget(self.list_scroll)
        self.body = self.list_lay

        root = self.layout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        box_wrap = QWidget()
        wl = QVBoxLayout(box_wrap)
        wl.setContentsMargins(20, 0, 20, 12)
        wl.addWidget(box)
        root.addWidget(head_holder, 0)
        root.addWidget(box_wrap, 1)

        if self.mode == "browse" and self.batch:
            bar = QWidget()
            bar.setObjectName("batchBar")
            bar.setStyleSheet(
                f"QWidget#batchBar{{background:{W.T['paper']};"
                f"border-top:1px solid {W.T['line']};}}")
            bl = QHBoxLayout(bar)
            bl.setContentsMargins(20, 10, 20, 12)
            bl.setSpacing(7)
            self._bar = QLabel(f"已选 {len(self.picked)} 张")
            self._bar.setObjectName("sub")
            bl.addWidget(self._bar)
            bl.addStretch(1)
            for text, fn in (("全选", self._pick_all),
                             ("取消", self._clear_picks),
                             ("移动", self._move_picked),
                             ("删除", self._delete_picked)):
                chip = W.Chip(text)
                chip.clicked.connect(lambda _, f=fn: f())
                bl.addWidget(chip)
            root.addWidget(bar, 0)

        # 刷题练习：只刷加入练习的卡
        if self.mode == "practice":
            self._build_practice(s)
            self.stretch()
            return

        # 浏览：当前卡组的卡片网格（虚拟列表，自己管理滚动内容）
        if self.mode == "browse":
            self._build_browse(sel_cards)
            return

        # 卡组列表
        if not active:
            self.add(self._hint("没有进行中的卡组", "存档里的卡组可以左滑「恢复」。"))
        for gname in active:
            items = by_group.get(gname, [])
            row = self._group_row(gname, items, archived=False,
                                  completed=gname in completed)
            self._rows.append(row)
            self.add(row)

        if stored:
            self.section("存档", label(f"{len(stored)} 个", "sub"))
            for gname in stored:
                items = by_group.get(gname, [])
                self.add(self._group_row(gname, items, archived=True, completed=False))

        self.stretch()

    # ---------------- 浏览网格 ----------------
    def _build_practice(self, s):
        """刷题练习：一张卡一个卡组，右侧直接开练。"""
        prac = s.practice_cards(self.deck_id)
        if not prac:
            box = W.Card(flat=True)
            box.body.setContentsMargins(18, 30, 18, 30)
            icon = PracticeIcon(46)
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(10)
            wl.addWidget(icon, 0, Qt.AlignHCenter)
            t = QLabel("还没有加入练习的卡片")
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet("font-size:14px;font-weight:700;")
            tip = QLabel("在「学习记忆」复习时点顶部的「加入练习」，"
                         "或在「浏览卡片」里选中卡片后加入。")
            tip.setObjectName("sub")
            tip.setAlignment(Qt.AlignCenter)
            tip.setWordWrap(True)
            wl.addWidget(t)
            wl.addWidget(tip)
            box.body.addWidget(wrap)
            self.add(box)
            return

        groups: dict[str, list] = {}
        for c in prac:
            groups.setdefault(c.get("group", "未分组"), []).append(c)

        for gname, items in groups.items():
            row = W.ClickFrame()
            row.setObjectName("pracRow")
            row.setStyleSheet(
                f"QFrame#pracRow{{background:{W.T['panel']};"
                f"border:1px solid {W.T['line']};border-radius:14px;}}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 12, 12, 12)
            rl.setSpacing(12)
            rl.addWidget(PracticeIcon(42), 0, Qt.AlignVCenter)

            col = QVBoxLayout()
            col.setSpacing(4)
            t = OneLineLabel(gname)
            t.setStyleSheet(f"font-size:15px;font-weight:700;color:{W.T['ink']};")
            sub = QLabel(f"{len(items)} 张卡片 · 不计入复习")
            sub.setObjectName("sub")
            col.addWidget(t)
            col.addWidget(sub)
            rl.addLayout(col, 1)

            go = QPushButton("开始练习")
            go.setCursor(Qt.PointingHandCursor)
            go.setFixedHeight(34)
            go.setStyleSheet(
                "QPushButton{background:%s;color:#FFFFFF;border:none;"
                "border-radius:17px;font-size:12.5px;font-weight:600;padding:0 16px;}"
                % W.T["brand"])
            go.clicked.connect(lambda _, g=gname: self.app.start_review(
                self.deck_id, group=g, practice=True))
            rl.addWidget(go, 0, Qt.AlignVCenter)

            row.clicked.connect(lambda g=gname: self.app.start_review(
                self.deck_id, group=g, practice=True))
            self.add(row)

    def _browse_controls(self):
        """浏览模式的工具栏（固定在头部，不随卡片滚动）。"""
        ctrl = QWidget()
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(7)
        for key, name in (("list", "列表"), ("grid", "网格")):
            chip = W.Chip(name, on=(self.browse_view == key))
            chip.clicked.connect(lambda _, k=key: self._set_browse_view(k))
            cl.addWidget(chip)
        cl.addStretch(1)
        add = W.Chip("新建")
        add.setToolTip("在当前卡组新建一张卡片")
        add.clicked.connect(self._add_card)
        cl.addWidget(add)
        b = W.Chip("批量中" if self.batch else "批量", on=self.batch)
        b.clicked.connect(self._toggle_batch)
        cl.addWidget(b)
        self.add(ctrl)

        self._bar = None

    def _add_card(self):
        """在浏览档位新建卡片：带上当前卡包与卡组。"""
        self.app.show_page("card_edit", deck_id=self.deck_id,
                           group=self.selected_group)

    def _build_browse(self, cards: list):
        self._browse_cards = cards

        if not cards:
            self._virtual = None
            self.add(self._hint("这一组还没有卡片", "换一个卡组试试。"))
            create = W.PrimaryButton("＋ 在这里新建卡片")
            create.clicked.connect(self._add_card)
            self.add(create)
            return

        # 虚拟列表：只渲染视口附近的卡片，滚动时复用控件。
        # 旧列表控件直接丢弃，后面的 self.body（list_lay）不再使用。
        old = self.list_scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self._virtual = VirtualCardList(
            cards, self.browse_view, self.batch, self.picked,
            self.width() or 430, self._stage, self._on_card_click,
            self.list_scroll,
        )
        self.list_scroll.setWidget(self._virtual)
        sb = self.list_scroll.verticalScrollBar()
        self._scroll_key = self._scroll_key_now()
        self._pending_scroll = getattr(self.app, "deck_scroll", {}).get(self._scroll_key, 0)
        self._scroll_ready = False
        # 只在换了一根滚动条时连一次，别 disconnect（会把虚拟列表的 sync 也断掉）
        if getattr(self, "_scroll_sb", None) is not sb:
            self._scroll_sb = sb
            sb.valueChanged.connect(self._remember_scroll)
            sb.rangeChanged.connect(lambda *_: self._try_restore_scroll())
        sb.setValue(0)
        QTimer.singleShot(0, self._try_restore_scroll)
        QTimer.singleShot(80, self._try_restore_scroll)

    def _scroll_key_now(self):
        return (self.deck_id, self.mode, self.selected_group)

    def _try_restore_scroll(self):
        """等列表高度算出来（maximum 够大）再恢复，只恢复一次。"""
        pending = getattr(self, "_pending_scroll", None)
        if not pending:
            self._scroll_ready = True
            return
        sb = self.list_scroll.verticalScrollBar()
        if sb.maximum() < pending:
            return
        sb.setValue(pending)
        self._pending_scroll = None
        self._scroll_ready = True

    def _save_scroll_now(self):
        try:
            sb = self.list_scroll.verticalScrollBar()
            self.app.deck_scroll[self._scroll_key_now()] = sb.value()
        except Exception:
            pass

    def _remember_scroll(self, v: int):
        if not getattr(self, "_scroll_ready", False):
            return
        try:
            self.app.deck_scroll[self._scroll_key] = v
        except Exception:
            pass

    def _on_card_click(self, cid: str):
        self._save_scroll_now()
        if self.batch:
            if cid in self.picked:
                self.picked.discard(cid)
            else:
                self.picked.add(cid)
            if self._virtual is not None:
                self._virtual.set_selected(cid, cid in self.picked)
            if self._bar:
                self._bar.setText(f"已选 {len(self.picked)} 张")
            return
        self.app.show_page("card_edit", card_id=cid)

    def _set_browse_view(self, view: str):
        self.browse_view = view
        self.app.browse_view = view
        self.build()

    def _toggle_batch(self):
        self.batch = not self.batch
        self.picked.clear()
        self.build()

    def _pick_all(self):
        self.picked.clear()
        self.picked.update(c["id"] for c in getattr(self, "_browse_cards", []))
        if self._virtual is not None:
            self._virtual.refresh_selection()
        if self._bar:
            self._bar.setText(f"已选 {len(self.picked)} 张")

    def _clear_picks(self):
        self.picked.clear()
        if self._virtual is not None:
            self._virtual.refresh_selection()
        if self._bar:
            self._bar.setText("已选 0 张")

    def _move_picked(self):
        if not self.picked:
            self.app.toast("先选卡片")
            return
        groups = self.store.ordered_groups(self.deck_id)
        rows = [{"name": g,
                 "n": sum(1 for c in self.store.cards
                          if c.get("deck_id") == self.deck_id and c.get("group") == g)}
                for g in groups]
        dlg = MoveCardsDialog(rows, len(self.picked), self)
        if not dlg.exec():
            return
        name = dlg.selected()
        if not name:
            return
        n = self.store.move_cards(self.picked, self.deck_id, name)
        self.app.toast(f"已移动 {n} 张到「{name}」")
        self.batch = False
        self.picked.clear()
        self.build()

    def _delete_picked(self):
        if not self.picked:
            self.app.toast("先选卡片")
            return
        n = len(self.picked)
        ok = QMessageBox.question(self, "删除卡片",
                                  f"删除选中的 {n} 张卡片？\n会放进回收站，之后可以恢复。")
        if ok != QMessageBox.Yes:
            return
        self.store.delete_cards(self.picked)
        self.app.toast(f"已删除 {n} 张卡片")
        self.batch = False
        self.picked.clear()
        self.build()

    # ---------------- 卡组行 ----------------
    def _group_row(self, gname: str, items: list, archived: bool, completed: bool):
        gdue = 0 if (archived or completed) else sum(
            1 for c in items if c["due"] <= time.time() * 1000)
        selected = (self.selected_group == gname) and not archived

        body = QWidget()
        body.setObjectName("swipeBody")
        bg = W.T["paper2"] if archived else (W.T["brand_soft"] if selected else W.T["panel"])
        border = W.T["brand"] if selected else W.T["line"]
        body.setStyleSheet(
            f"QWidget#swipeBody{{background:{bg};border:1px solid {border};"
            f"border-radius:12px;}}")
        lay = QHBoxLayout(body)
        lay.setContentsMargins(16, 10, 12, 10)
        lay.setSpacing(9)

        left = QVBoxLayout()
        left.setSpacing(4)
        t = OneLineLabel(gname)
        t.setStyleSheet(f"font-size:13.5px;font-weight:600;"
                        f"color:{W.T['ink3'] if archived else W.T['ink']};")
        types = sorted({ {"qa": "问答", "single": "单选", "multi": "多选"}[c["type"]] for c in items })
        sub = QLabel(f"{len(items)} 张 · " + " / ".join(types) if types else "0 张 · 还没有卡片")
        sub.setObjectName("sub")
        left.addWidget(t)
        left.addWidget(sub)
        lay.addLayout(left, 1)

        if archived:
            pill = W.Pill("已存档", "plain")
        elif completed:
            pill = W.Pill("已完成", "brand")
        elif gdue:
            pill = W.Pill(f"{gdue} 到期", "accent")
        else:
            pill = W.Pill("未开始", "plain")
        lay.addWidget(pill)

        if archived:
            actions = [("rename", "重命名", "#8A7F6E"),
                       ("restore", "恢复", "#2F6A43"),
                       ("delete", "删除", "#D9534F")]
        elif completed:
            actions = [("rename", "重命名", "#8A7F6E"),
                       ("uncomplete", "取消", "#8A7F6E"),
                       ("delete", "删除", "#D9534F")]
        else:
            actions = [("rename", "重命名", "#8A7F6E"),
                       ("reset", "重置", "#8A7F6E"),
                       ("archive", "存档", "#8A7F6E"),
                       ("delete", "删除", "#D9534F")]

        row = W.SwipeRow(body, actions, height=70)
        row.setProperty("group", gname)
        row.clicked.connect(lambda g=gname, a=archived: self._open_group(g, a))
        row.action.connect(lambda key, g=gname: self._on_action(g, key))
        row.drag_started.connect(lambda r=row: self._drag_begin(r))
        row.drag_moved.connect(lambda gy, r=row: self._drag_move(r, gy))
        row.drag_finished.connect(lambda r=row: self._drag_end(r))
        self._swipes.append(row)
        return row

    # ---------------- 移动到… ----------------
    def _collect_dests(self, domain, parent, prefix, kind, obj, labels, targets):
        s = self.store
        for r in s.rounds_in(domain, parent):
            if kind == "round" and (r["id"] == obj["id"]
                                    or s._is_descendant(r["id"], obj["id"])):
                continue
            labels.append(f"{prefix}{r['name']}")
            targets.append((domain, r["id"]))
            self._collect_dests(domain, r["id"], f"{prefix}{r['name']} / ",
                                kind, obj, labels, targets)

    def _move_node(self, kind: str, obj: dict):
        s = self.store
        labels, targets = [], []
        for d in s.domains:
            labels.append(f"{d['name']}（根目录）")
            targets.append((d["id"], None))
            self._collect_dests(d["id"], None, f"{d['name']} / ",
                                kind, obj, labels, targets)
        if not labels:
            return
        dlg = MoveDialog(labels, self)
        if dlg.exec() != QDialog.Accepted:
            return
        label = dlg.selected()
        if not label or label not in labels:
            return
        domain, parent = targets[labels.index(label)]
        if kind == "round":
            if not s.move_round(obj["id"], domain, parent):
                self.app.toast("不能移动到它自己的子圆桌里")
                return
        else:
            s.move_deck(obj["id"], domain, parent)
        self.app.toast(f"已移动到「{label}」")
        self.build()

    # ---------------- 拖动排序 ----------------
    def _drag_begin(self, row):
        if row not in self._rows:
            return
        self._drag_row = row
        self._drag_target = self._rows.index(row)
        self._indicator = QFrame(self.list_content)
        self._indicator.setFixedHeight(3)
        self._indicator.setStyleSheet(
            f"background:{W.T['brand']};border-radius:2px;")
        self.list_lay.insertWidget(self.list_lay.indexOf(row), self._indicator)

    def _drag_move(self, row, global_y: float):
        if self._drag_row is not row or self._indicator is None:
            return
        y = self.list_content.mapFromGlobal(QPoint(0, int(global_y))).y()
        target = len(self._rows)
        for i, r in enumerate(self._rows):
            top = r.mapTo(self.list_content, QPoint(0, 0)).y()
            if y < top + r.height() / 2:
                target = i
                break
        self._drag_target = target
        self.list_lay.removeWidget(self._indicator)
        if target < len(self._rows):
            self.list_lay.insertWidget(self.list_lay.indexOf(self._rows[target]),
                                       self._indicator)
        else:
            self.list_lay.insertWidget(self.list_lay.indexOf(self._rows[-1]) + 1,
                                       self._indicator)
        self._indicator.show()

    def _drag_end(self, row):
        if self._indicator is not None:
            self._indicator.deleteLater()
            self._indicator = None
        dragged = row.property("group")
        target = self._drag_target
        self._drag_row = None
        self._drag_target = None
        if not dragged or target is None or dragged not in self._active_order:
            self.build()
            return
        order = list(self._active_order)
        old = order.index(dragged)
        items = [g for g in order if g != dragged]
        pos = target - (1 if old < target else 0)
        pos = max(0, min(len(items), pos))
        items.insert(pos, dragged)
        self.store.set_group_order(self.deck_id, items)
        self.build()

    def _hint(self, title: str, sub: str):
        box = W.Card(flat=True)
        box.body.setContentsMargins(18, 22, 18, 22)
        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:13px;font-weight:600;")
        s2 = QLabel(sub)
        s2.setObjectName("sub")
        s2.setAlignment(Qt.AlignCenter)
        s2.setWordWrap(True)
        box.body.addWidget(t)
        box.body.addWidget(s2)
        return box

    # ---------------- 动作 ----------------
    def _close_others(self, keep=None):
        for r in self._swipes:
            if r is not keep:
                r.close()

    def _open_group(self, group: str, archived: bool):
        """点卡组：学习模式直接开始这一组；其它模式只做选中。

        没有可复习的卡片时也要保留选中态，所以先把选中画出来再尝试开复习。
        """
        if archived:
            self.app.toast("这个卡组在「存档」里，左滑「恢复」后可继续学习")
            return
        self.selected_group = group
        self.app.deck_selection[self.deck_id] = group
        self.store.save_selection(self.deck_id, group)
        if self.mode == "learn":
            # 直接开复习：不需要先把整页重建一遍（马上就被学习页替换掉了，白花 20ms+）
            before = getattr(self.app, "_cur_spec", None)
            self.app.start_review(self.deck_id, group=group)
            if getattr(self.app, "_cur_spec", None) == before:
                self.build()        # 没开起来（没卡/额度用完）→ 留在本页，补画选中态
            return
        self.build()

    def _toggle_group(self, group: str, archived: bool):
        if archived:
            self.app.toast("这个卡组在「存档」里，左滑「恢复」后可继续学习")
            return
        if self.selected_group == group:
            return                      # 已是选中，不取消
        self._select_group(group, True)

    def _select_group(self, group: str, checked: bool):
        if not checked:
            self.build()                # 不允许「没有选中」：重建以恢复勾选
            return
        self._close_others()
        self.selected_group = group
        self.app.deck_selection[self.deck_id] = group
        self.store.save_selection(self.deck_id, group)
        self.build()

    def _start_study(self):
        self.app.start_review(self.deck_id, group=self.selected_group,
                              practice=(self.mode == "practice"))

    def _import_word(self):
        from docx_import import parse_docx
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 Word 文档", "", "Word 文档 (*.docx)")
        if not path:
            return
        try:
            title, items = parse_docx(path)
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"读不了这个文档：\n{e}")
            return
        if not title or not items:
            QMessageBox.warning(self, "导入失败",
                                "没识别到卡片。需要「001、问题」这样的序号行。")
            return
        existed = title in (self.store.deck(self.deck_id) or {}).get("groups", [])
        n = self.store.add_group_cards(self.deck_id, title, items)
        self.app.toast(f"已导入 {n} 张卡片到「{title}」" + ("（追加到已有卡组）" if existed else ""))
        self._select_group(title, True)

    def _on_action(self, group: str, key: str):
        self._close_others()
        s = self.store
        if key == "reset":
            n = sum(1 for c in s.cards_of(self.deck_id) if c.get("group") == group)
            ok = QMessageBox.question(
                self, "重置进度",
                f"把「{group}」的 {n} 张卡片进度清零？\n卡片内容保留，调度回到新卡。")
            if ok != QMessageBox.Yes:
                return
            n = s.reset_group_progress(self.deck_id, group)
            self.app.toast(f"「{group}」已重置（{n} 张）")
            self.build()
            return
        if key == "archive":
            s.toggle_group_archive(self.deck_id, group)
            self.app.toast(f"「{group}」已存档，不再安排复习")
        elif key == "restore":
            s.unarchive_group(self.deck_id, group)
            self.app.toast(f"「{group}」已恢复")
        elif key == "rename":
            name, ok = QInputDialog.getText(self, "重命名卡组", "名称", text=group)
            if not ok or not name.strip() or name.strip() == group:
                return
            new = name.strip()
            n = s.rename_group(self.deck_id, group, new)
            if self.selected_group == group:
                self.selected_group = new
                s.save_selection(self.deck_id, new)
                self.app.deck_selection[self.deck_id] = new
            self.app.toast(f"已重命名为「{new}」（{n} 张卡片）")
            self.build()
            return
        elif key == "uncomplete":
            s.toggle_group_complete(self.deck_id, group)
            self.app.toast(f"「{group}」已取消完成")
        elif key == "delete":
            n = sum(1 for c in s.cards_of(self.deck_id) if c.get("group") == group)
            ok = QMessageBox.question(
                self, "删除卡组",
                f"删除「{group}」及其 {n} 张卡片？\n会放进回收站，之后可以恢复。")
            if ok != QMessageBox.Yes:
                return
            s.delete_group(self.deck_id, group)
            if self.selected_group == group:
                self.selected_group = None
            self.app.toast(f"「{group}」已删除")
        self.build()

    def _new_group(self):
        """新建空卡组（「卡组」标题右侧的 ＋）。"""
        d = self.store.deck(self.deck_id) or {}
        dlg = NewGroupDialog(set(self.store.ordered_groups(self.deck_id)),
                             d.get("name", ""), self)
        dlg.exec()
        if not dlg.name:
            return
        done, msg = self.store.create_group(self.deck_id, dlg.name)
        if not done:
            self.app.toast(msg)
            return
        self.selected_group = msg
        self.store.save_selection(self.deck_id, msg)
        self.app.deck_selection[self.deck_id] = msg
        self.build()

    def _set_mode(self, key: str):
        if key != self.mode:
            self.batch = False
            self.picked.clear()
        self.mode = key
        self.app.deck_mode = key
        self.build()

    @staticmethod
    def _stage(c: dict) -> str:
        if c["reps"] == 0:
            return "新卡"
        if c.get("lapses"):
            return "遗忘复习"
        if c["interval"] >= 21:
            return "已完成"
        return "学习中"
