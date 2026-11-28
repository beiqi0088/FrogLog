# -*- coding: utf-8 -*-
"""pages/card_edit.py - 编辑卡片：富文本工具栏 + 实时预览（移植自浮卡的浮墨编辑）。

一个框，`---` 拆正反；工具栏支持 挖空 / 墨线 / 加粗 / 颜色 / 背景 / 下划线 / 图片 / 清除格式，
下方按复习页同一套 card_render 实时预览，可切换「含答案 / 仅题面」。
"""
from __future__ import annotations

import math
import re

from PySide6.QtCore import Qt, QTimer, QEvent, QPointF, QRectF, QSize
from PySide6.QtGui import (QColor, QFont, QIcon, QImage, QKeySequence, QPainter,
                           QPainterPath, QPen, QPixmap, QShortcut, QTextImageFormat,
                           QTextBlockFormat, QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import (QColorDialog, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QTextEdit, QVBoxLayout, QWidget)

import card_render as CR
import formatting as F
import widgets as W
from core import DEFAULT_EASE, now_ms, uid
from pages.base import Page, label

OPT_RE = re.compile(r"^([A-Fa-f])[.、．)）]\s*(.+)$")
ANS_RE = re.compile(r"^(?:正确答案|答案)\s*[:：]\s*([A-Fa-f]+)$")


def _bar_icon(kind: str, color: str | None = None) -> QIcon:
    """功能条的矢量小图标：18×18 逻辑像素，2 倍图，线条风格。"""
    color = color or W.T["ink2"]
    s = 18
    pm = QPixmap(s * 2, s * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    def text(t, px=12, bold=True):
        f = QFont("Microsoft YaHei UI")
        f.setPixelSize(px)
        f.setBold(bold)
        p.setFont(f)
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, t)

    if kind == "image":
        p.drawRoundedRect(QRectF(2.6, 3.8, 12.8, 10.4), 2.0, 2.0)
        p.setBrush(QColor(color))
        p.drawEllipse(QRectF(5.2, 6.0, 2.4, 2.4))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(3.6, 13.2)
        path.lineTo(7.4, 8.8)
        path.lineTo(10.0, 11.8)
        path.lineTo(12.0, 9.8)
        path.lineTo(14.6, 13.2)
        p.drawPath(path)
    elif kind == "line":
        p.setPen(QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap))
        for x0 in (3.0, 8.0, 13.0):
            p.drawLine(QPointF(x0, 9.0), QPointF(x0 + 2.4, 9.0))
    elif kind == "bold":
        text("B", 13, True)
    elif kind == "size":
        text("Aa", 11, False)
    elif kind == "cloze":
        # 括号里放一个实心长方形（填空位）：整体放大到占满图标格
        p.save()
        p.translate(9.0, 9.0)
        p.scale(1.45, 1.45)
        p.translate(-9.0, -9.0)
        p.setPen(QPen(QColor(color), 1.3, Qt.SolidLine, Qt.RoundCap))
        left = QPainterPath()
        left.moveTo(4.9, 6.2)
        left.cubicTo(3.6, 7.4, 3.6, 10.6, 4.9, 11.8)
        p.drawPath(left)
        right = QPainterPath()
        right.moveTo(13.1, 6.2)
        right.cubicTo(14.4, 7.4, 14.4, 10.6, 13.1, 11.8)
        p.drawPath(right)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(5.6, 7.3, 6.8, 3.4), 0.9, 0.9)
        p.setBrush(Qt.NoBrush)
        p.restore()
    elif kind == "multi":
        # 虚线选区框（划选）
        pen = QPen(QColor(color), 1.3, Qt.DashLine, Qt.RoundCap)
        pen.setDashPattern([2.2, 1.8])
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(3.2, 4.4, 11.6, 9.2), 1.6, 1.6)
        p.setPen(QPen(QColor(color), 1.4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(6.4, 9.0), QPointF(11.6, 9.0))
    elif kind == "more":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        for cx in (4.6, 9.0, 13.4):
            p.drawEllipse(QRectF(cx - 1.25, 7.75, 2.5, 2.5))
    elif kind == "clear":
        # 橡皮擦：斜放的圆角块 + 分色带 + 擦痕
        p.save()
        p.translate(9.0, 8.6)
        p.rotate(-38)
        p.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap))
        p.drawRoundedRect(QRectF(-5.0, -2.9, 10.0, 5.8), 1.6, 1.6)
        p.drawLine(QPointF(-1.4, -2.9), QPointF(-1.4, 2.9))
        p.restore()
        p.setPen(QPen(QColor(color), 1.3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(3.4, 15.0), QPointF(14.6, 15.0))
    elif kind in ("undo", "redo"):
        p.save()
        if kind == "redo":
            p.translate(s, 0)
            p.scale(-1, 1)
        path = QPainterPath()
        path.moveTo(8.0, 6.4)
        path.lineTo(12.6, 6.4)
        path.cubicTo(15.4, 6.6, 15.4, 11.4, 12.2, 12.6)
        p.drawPath(path)
        tri = QPainterPath()
        tri.moveTo(3.8, 6.4)
        tri.lineTo(8.0, 3.8)
        tri.lineTo(8.0, 9.0)
        tri.closeSubpath()
        p.fillPath(tri, QColor(color))
        p.restore()
    p.end()
    return QIcon(pm)


class _SelOverlay(QWidget):
    """挖空下划线 + 划选虚线框：画在正文之上，透明、不吃鼠标。"""

    CLOZE_LINE = "#FF4D1A"     # 醒目的橘红（不再跟主题/模板）
    SELECT_BLUE = "#12A5FF"    # 醒目的天蓝

    def __init__(self, editor, page):
        super().__init__(editor.viewport())
        self._page = page
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setGeometry(0, 0, editor.viewport().width(), editor.viewport().height())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        # 1) 挖空：2px 橘红下划线
        clozes = self._page._cloze_rects()
        if clozes:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.CLOZE_LINE))
            for x, y, w, h in clozes:
                p.drawRect(QRectF(x, y + h - 2.0, w, 2.0))
        # 2) 划选：天蓝底色（不再画虚线框）
        rects = self._page._multi_rects()
        if not rects:
            return
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 165, 255, 58))
        for x, y, w, h in rects:
            p.drawRect(QRectF(x, y + 1.0, w, h - 1.0))


class CardEditPage(Page):
    def __init__(self, app, card_id: str | None = None, deck_id: str | None = None,
                 group: str | None = None):
        self.card_id = card_id
        self.deck_id = deck_id
        self.group = group
        self.is_new = not card_id
        self._origin_new = not card_id      # 从「新建」进来的页面，返回一律回卡包
        super().__init__(app)

    # ------------------------------------------------------------ 构建
    def build(self):
        super().build()
        if self.is_new:
            self.card = self._blank_card()
        else:
            self.card = self.store.card(self.card_id)
            if not self.card:
                self.app.toast("卡片不存在")
                self.app.go_back()
                return
        if not hasattr(self, "_mode"):
            self._mode = "edit"
        if not hasattr(self, "_shown_masks"):
            self._shown_masks = set()
        self._multi_sel: list[tuple[int, int]] = []   # 划选收进来的范围
        self._multi_hist: list[list] = []             # 划选范围的撤销栈
        if not hasattr(self, "_saved_new"):
            self._saved_new = False                   # 新建卡保存后：按钮变「继续新建」
        self._multi_future: list[list] = []           # 划选范围的重做栈
        self.multi_mode = False
        self._reveal = True
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._refresh_preview)

        # ---------------- 顶栏 ----------------
        self.text = QTextEdit()
        self.text.setAcceptRichText(True)
        self.text.setPlaceholderText("写问题…\n---\n写答案…\n\n选中文字后上方会浮出格式栏")
        pal = self._pal()
        F.load_inline_html(self.text, self._compose(self.card),
                           front=pal.get("mask") or pal["label"],
                           back=pal.get("amask") or pal["alabel"])
        self._apply_line_spacing(124)
        # 载入本身不进撤销栈：打开卡片时撤销/重做都是灰的
        self.text.document().clearUndoRedoStacks()
        self.text.setMinimumHeight(240)
        self.text.setStyleSheet(
            f"QTextEdit{{font-size:17px;line-height:170%;padding:8px 4px;"
            f"background:{W.T['panel']};border:none;border-radius:12px;}}")
        self.text.textChanged.connect(lambda: self._preview_timer.start(250))

        self.add(self._topbar())

        # ---------------- 编辑区 ----------------
        self.edit_area = QWidget()
        el = QVBoxLayout(self.edit_area)
        el.setContentsMargins(20, 8, 20, 24)
        el.setSpacing(6)
        el.addWidget(self.text, 1)

        self.bottom_bar = self._bottom_tools()
        self.bottom_bar.hide()                 # 光标进到正文才出来（像手机的小键盘）
        el.addWidget(self.bottom_bar)
        self.add(self.edit_area)
        if hasattr(self, "body"):
            self.body.setContentsMargins(0, 4, 0, 0)

        # 划选的框线画在正文之上（透明、不吃鼠标）
        self._sel_overlay = _SelOverlay(self.text, self)
        self._sel_overlay.raise_()
        self._make_sel_bar()
        self.text.installEventFilter(self)
        self.text.viewport().installEventFilter(self)
        self.text.verticalScrollBar().valueChanged.connect(self._refresh_overlay)
        self.text.textChanged.connect(self._refresh_overlay)

        # ---------------- 预览区 ----------------
        self.preview_area = QWidget()
        pl = QVBoxLayout(self.preview_area)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)
        self.preview_host = QWidget()                 # 不再套一层卡片（去掉外面的边框）
        self.preview_body = QVBoxLayout(self.preview_host)
        self.preview_body.setContentsMargins(0, 0, 0, 0)
        self.preview_body.setSpacing(0)
        pl.addWidget(self.preview_host, 1)
        self.add(self.preview_area)
        self._refresh_preview()

        self._install_shortcuts()
        self._apply_mode()

    def _apply_line_spacing(self, pct: int = 124):
        """行间距：默认 100% 偏挤，稍微放大一点（不影响存盘）。"""
        doc = self.text.document()
        cur = QTextCursor(doc)
        cur.select(QTextCursor.Document)
        bf = QTextBlockFormat()
        bf.setLineHeight(float(pct), 1)   # 1 = ProportionalHeight
        cur.mergeBlockFormat(bf)

    # ------------------------------------------------------------ 顶栏
    def _topbar(self) -> QWidget:
        """← 编辑/预览 ↶ ↷ ⋯ 保存 —— 对齐浮卡编辑器顶栏。"""
        row = QWidget()
        self.top_row = row
        lay = QHBoxLayout(row)
        lay.setContentsMargins(20, 4, 20, 2)
        lay.setSpacing(4)

        back = W.BackButton(34)
        back.clicked.connect(self._back)
        lay.addWidget(back)
        lay.addWidget(self._mode_segment(compact=True))

        lay.addStretch(1)

        self.tpl_btn = QPushButton("更换模板")
        self.tpl_btn.setCursor(Qt.PointingHandCursor)
        self.tpl_btn.setFixedHeight(28)
        self.tpl_btn.setToolTip("换一套卡片皮肤（应用到当前卡包）")
        self.tpl_btn.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};color:{W.T['ink']};border:none;"
            f"border-radius:14px;font-size:13px;padding:0 12px;}}"
            f"QPushButton:hover{{background:{W.T['brand_soft']};color:{W.T['brand']};}}")
        self.tpl_btn.clicked.connect(self._open_templates)
        lay.addWidget(self.tpl_btn)
        self.tpl_btn.setVisible(False)

        sibling = QPushButton("兄弟卡")
        sibling.setCursor(Qt.PointingHandCursor)
        sibling.setFixedHeight(28)
        sibling.setToolTip("复制成同一笔记的另一张卡（独立调度，可开「bury 兄弟」避免同天出现）")
        sibling.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{W.T['ink2']};"
            f"font-size:13.5px;font-weight:600;padding:0 6px;}}"
            f"QPushButton:hover{{color:{W.T['brand']};}}")
        sibling.clicked.connect(self._add_sibling)
        lay.addWidget(sibling)

        save = QPushButton("保存")
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{W.T['brand']};"
            f"font-size:14.5px;font-weight:700;padding:0 4px;}}"
            f"QPushButton:hover{{color:{W.T['brand2']};}}")
        save.clicked.connect(self._save_clicked)
        lay.addWidget(save)
        self.save_btn = save

        return row

    def _paste_plain(self):
        from PySide6.QtGui import QGuiApplication
        t = QGuiApplication.clipboard().text()
        if t:
            self.text.insertPlainText(t)

    def _add_sibling(self):
        """把当前卡复制成同一笔记的兄弟卡，并打开新卡继续编辑。"""
        if not self._has_content():
            self.app.toast("先写点内容")
            return
        if not self._persist():
            self.app.toast("保存失败")
            return
        card = self.card or {}
        sib = self.store.add_sibling(card.get("id"))
        if not sib:
            self.app.toast("先保存这张卡")
            return
        self.app.toast("已创建兄弟卡（同一笔记，独立调度）")
        # 用「替换」而不是「入栈」：否则返回会先回到刚编辑的那张原卡，要按两次
        self.app._nav_back = True
        try:
            self.app.show_page("card_edit", card_id=sib["id"])
        finally:
            self.app._nav_back = False

    def _open_templates(self):
        """更换模板：先静默保存草稿，再跳到模板页面（点一下即时换肤）。"""
        deck_id = (self.card or {}).get("deck_id")
        if not deck_id:
            return
        self._persist()
        # 让「返回」回到这张卡（新建的卡也算），而不是又开一张空卡
        self.app._cur_spec = ("card_edit", {"card_id": self.card.get("id"),
                                            "deck_id": deck_id,
                                            "group": self.group})
        self.app.show_page("templates", deck_id=deck_id)

    # ------------------------------------------------------------ 底部工具栏
    def _bottom_tools(self) -> QWidget:
        """紧凑图标条（对齐浮卡键盘上方的附件栏）：点正文才出现。"""
        bar = QFrame()
        bar.setObjectName("bottomTools")
        bar.setFixedHeight(40)
        bar.setStyleSheet(
            f"QFrame#bottomTools{{background:{W.T['panel']};"
            f"border:1px solid {W.T['line']};border-radius:10px;}}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)
        items = [
            ("multi", "划选：连续选中多处文字，统一加格式；再点一次退出", self._toggle_multi),
            ("cloze", f"挖空（{F.FORMAT_SHORTCUTS['cloze']}）", self._fmt_cloze),
            ("line", "插入墨线 ---", self._fmt_inkline),
            ("bold", f"加粗（{F.FORMAT_SHORTCUTS['bold']}）", self._fmt_bold),
            ("image", "插入图片", self._fmt_image),
            ("clear", f"清除格式（{F.FORMAT_SHORTCUTS['clear']}）", self._fmt_clear),
        ]
        for i, (kind, tip, fn) in enumerate(items):
            b = self._icon_btn(kind, tip, fn)
            if kind == "multi":
                b.setCheckable(True)
                self.multi_btn = b
            lay.addWidget(b, 1)
        # 撤销 / 重做（原来在顶栏）
        self.undo_btn = self._icon_btn("undo", "撤销", self._undo)
        self.redo_btn = self._icon_btn("redo", "重做", self._redo)
        self.text.undoAvailable.connect(lambda _=False: self._refresh_undo_btns())
        self.text.redoAvailable.connect(lambda _=False: self._refresh_undo_btns())
        self._refresh_undo_btns()
        lay.addWidget(self._vsep())
        lay.addWidget(self.undo_btn, 1)
        lay.addWidget(self.redo_btn, 1)
        return bar

    @staticmethod
    def _vsep() -> QFrame:
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(18)
        sep.setStyleSheet(f"background:{W.T['line']};border:none;")
        return sep

    def _icon_btn(self, kind: str, tip: str, fn) -> QPushButton:
        b = QPushButton()
        b.setIcon(_bar_icon(kind))
        b.setIconSize(QSize(20, 20))
        b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus)
        b.setFixedHeight(30)
        b.setToolTip(tip)
        b.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;padding:0;}}"
            f"QPushButton:hover{{background:{W.T['paper2']};border-radius:7px;}}"
            f"QPushButton:checked{{background:{W.T['brand_soft']};border-radius:7px;}}")
        b.clicked.connect(lambda _=False, f=fn: self._bar_action(f))
        return b

    def _bar_action(self, fn):
        """底部条按钮：执行完把焦点还给正文，别让划选/光标被打断。"""
        fn()
        if self._mode == "edit":
            self.text.setFocus()
            self._show_bottom(True)
            self._refresh_overlay()

    # ------------------------------------------------------------ 模式切换
    def _mode_segment(self, compact: bool = False) -> QWidget:
        seg = QWidget()
        seg.setObjectName("segMode")
        seg.setStyleSheet(
            f"QWidget#segMode{{background:{W.T['paper2']};border-radius:15px;}}"
            f"QPushButton#chip{{background:transparent;color:{W.T['ink2']};border:none;"
            f"font-size:13px;border-radius:12px;padding:0 14px;}}"
            f"QPushButton#chip:hover{{color:{W.T['brand']};}}"
            f"QPushButton#chip[on=\"true\"]{{background:{W.T['panel']};"
            f"color:{W.T['brand']};font-weight:700;}}")
        lay = QHBoxLayout(seg)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.mode_chips = {}
        for key, name in (("edit", "编辑"), ("preview", "预览")):
            chip = W.Chip(name, on=(self._mode == key))
            if compact:
                chip.setFixedHeight(26)
            chip.clicked.connect(lambda _, k=key: self._set_mode(k))
            lay.addWidget(chip)
            self.mode_chips[key] = chip
        return seg

    def _set_mode(self, key: str):
        if key == self._mode:
            return
        self._mode = key
        if key == "edit" and getattr(self, "_saved_new", False):
            self._saved_new = False
            if hasattr(self, "save_btn"):
                self.save_btn.setText("保存")
        for k, chip in self.mode_chips.items():
            chip.set_on(k == key)
        self._apply_mode()
        if key == "preview":
            self._refresh_preview()

    def _apply_mode(self):
        editing = self._mode == "edit"
        if hasattr(self, "tpl_btn"):
            self.tpl_btn.setVisible(not editing)
        if hasattr(self, "edit_area"):
            self.edit_area.setVisible(editing)
        if hasattr(self, "preview_area"):
            self.preview_area.setVisible(not editing)
        if not editing:
            if hasattr(self, "bottom_bar"):
                self.bottom_bar.hide()
            if hasattr(self, "_sel_bar"):
                self._sel_bar.hide()

    # ------------------------------------------------------------ 划选 / 事件
    def eventFilter(self, obj, ev):
        text = getattr(self, "text", None)
        if obj is text:
            if ev.type() == QEvent.FocusIn:
                self._show_bottom(True)
            elif ev.type() == QEvent.FocusOut:
                self._show_bottom(False)
                bar = getattr(self, "_sel_bar", None)
                if bar is not None:
                    bar.hide()
        elif text is not None and obj is text.viewport():
            if ev.type() == QEvent.MouseButtonRelease and self.multi_mode:
                self._collect_multi()
            elif ev.type() == QEvent.Resize:
                self._refresh_overlay()
        return super().eventFilter(obj, ev)

    def _show_bottom(self, on: bool):
        """底部图标条跟着光标出现/收起（像手机键盘上方的附件栏）。"""
        bar = getattr(self, "bottom_bar", None)
        if bar is None:
            return
        if self._mode != "edit":
            bar.hide()
            return
        if on:
            bar.show()
            self._refresh_overlay()
        else:
            QTimer.singleShot(0, self._hide_bottom_if_unfocused)

    def _hide_bottom_if_unfocused(self):
        bar = getattr(self, "bottom_bar", None)
        if bar is not None and not self.text.hasFocus():
            bar.hide()

    def _undo(self):
        """撤销：优先撤销最近一次划选范围的增删，其次撤销正文编辑。"""
        if self.multi_mode and self._multi_hist:
            self._multi_future.append(list(self._multi_sel))
            self._multi_sel = self._multi_hist.pop()
            self._paint_multi()
            self._refresh_undo_btns()
            return
        self.text.undo()

    def _redo(self):
        if self.multi_mode and self._multi_future:
            self._multi_hist.append(list(self._multi_sel))
            self._multi_sel = self._multi_future.pop()
            self._paint_multi()
            self._refresh_undo_btns()
            return
        self.text.redo()

    def _refresh_undo_btns(self):
        u = getattr(self, "undo_btn", None)
        r = getattr(self, "redo_btn", None)
        if u is None or r is None:
            return
        doc = self.text.document()
        u.setEnabled(bool(self._multi_hist) or doc.isUndoAvailable())
        r.setEnabled(bool(self._multi_future) or doc.isRedoAvailable())

    def _toggle_multi(self):
        self.multi_mode = not self.multi_mode
        btn = getattr(self, "multi_btn", None)
        if btn is not None:
            btn.setChecked(self.multi_mode)
        if not self.multi_mode:
            self._multi_sel.clear()
            self._multi_hist.clear()
            self._multi_future.clear()
            self._paint_multi()
            self._refresh_undo_btns()
            self.app.toast("已退出划选")
        else:
            self.app.toast("划选：拖选多处文字，再点格式")
        if self._mode == "edit":
            self.text.setFocus()
            self._show_bottom(True)

    def _collect_multi(self, toggle: bool = True):
        """划选一段：新范围若和已有框重叠就取消它们，否则加进来。"""
        cur = self.text.textCursor()
        if not cur.hasSelection():
            return
        s, e = cur.selectionStart(), cur.selectionEnd()
        self._multi_hist.append(list(self._multi_sel))
        self._multi_future.clear()
        hit = [r for r in self._multi_sel if r[0] < e and s < r[1]]
        if toggle and hit:
            # 再划一次同一段 = 取消这些框
            self._multi_sel = [r for r in self._multi_sel if r not in hit]
            self._paint_multi()
            self._sink_cursor(e)
            self._refresh_undo_btns()
            self.app.toast("已取消这句的划选")
            return
        rs = sorted(self._multi_sel + [(s, e)])
        merged: list[tuple[int, int]] = []
        for a, b in rs:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        self._multi_sel = merged
        self._sink_cursor(e)
        self._paint_multi()
        self._refresh_undo_btns()

    def _sink_cursor(self, pos: int):
        """收掉当前选区，让下一笔重新选。"""
        c = QTextCursor(self.text.document())
        c.setPosition(pos)
        self.text.setTextCursor(c)

    def _paint_multi(self):
        """划选的范围用虚线框圈出来（画在正文上方的透明层里）。"""
        self._refresh_overlay()

    def _rects_for(self, ranges) -> list:
        """把若干字符范围按行拆成矩形（视口坐标）。"""
        out = []
        doc = self.text.document()
        for a, b in ranges:
            block = doc.findBlock(a)
            while block.isValid() and block.position() < b:
                bpos = block.position()
                blk = block.layout()
                for i in range(blk.lineCount()):
                    line = blk.lineAt(i)
                    ls = bpos + line.textStart()
                    le = ls + line.textLength()
                    s, e = max(a, ls), min(b, le)
                    if e <= s:
                        continue
                    c = QTextCursor(doc)
                    c.setPosition(s)
                    r1 = self.text.cursorRect(c)
                    c.setPosition(e)
                    r2 = self.text.cursorRect(c)
                    left = min(r1.left(), r2.left())
                    right = max(r1.left(), r2.left())
                    out.append((left, r1.top(), max(2.0, right - left), r1.height()))
                block = block.next()
        return out

    def _multi_rects(self) -> list:
        return self._rects_for(self._multi_sel)

    def _cloze_ranges(self) -> list:
        """文档里所有挖空片段的字符范围。"""
        doc = self.text.document()
        out = []
        b = doc.begin()
        while b.isValid():
            it = b.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    cf = frag.charFormat()
                    if cf.property(F.CLOZE_PROP):
                        out.append((frag.position(), frag.position() + frag.length()))
                it += 1
            b = b.next()
        return out

    def _cloze_rects(self) -> list:
        return self._rects_for(self._cloze_ranges())

    def _refresh_overlay(self):
        ov = getattr(self, "_sel_overlay", None)
        if ov is None:
            return
        ov.setGeometry(0, 0, self.text.viewport().width(), self.text.viewport().height())
        ov.update()

    def _ranges(self) -> list[tuple[int, int]]:
        """划选范围 + 当前选区（重叠合并）。"""
        cur = self.text.textCursor()
        rs = list(self._multi_sel)
        if cur.hasSelection():
            rs.append((cur.selectionStart(), cur.selectionEnd()))
        rs.sort()
        out: list[tuple[int, int]] = []
        for a, b in rs:
            if out and a <= out[-1][1]:
                out[-1] = (out[-1][0], max(out[-1][1], b))
            else:
                out.append((a, b))
        return out

    def _sync_multi(self):
        """划选模式下，当前选区先收进框里，再统一处理。"""
        if self.multi_mode:
            cur = self.text.textCursor()
            if cur.hasSelection():
                self._collect_multi(toggle=False)

    def _each_range(self, fn):
        """对每一段（划选或普通选区）执行一次 fn(editor)。"""
        self._sync_multi()
        rs = self._ranges()
        if not rs:
            fn(self.text)
            return
        keep = self.text.textCursor()
        for a, b in rs:
            c = QTextCursor(self.text.document())
            c.setPosition(a)
            c.setPosition(b, QTextCursor.KeepAnchor)
            self.text.setTextCursor(c)
            fn(self.text)
        self.text.setTextCursor(keep)
        self._paint_multi()

    def _apply_fmt_all(self, fmt: QTextCharFormat):
        self._sync_multi()
        rs = self._ranges()
        if not rs:
            self.app.toast("请先选中文字")
            return
        for a, b in rs:
            c = QTextCursor(self.text.document())
            c.setPosition(a)
            c.setPosition(b, QTextCursor.KeepAnchor)
            c.mergeCharFormat(fmt)
        self._paint_multi()

    # ------------------------------------------------------------ 预览
    def _template_key(self) -> str:
        deck = self.store.deck(self.card.get("deck_id")) or {}
        key = deck.get("template") or self.store.settings.get("default_template") or "sky"
        return key if key in CR.TEMPLATES else "sky"

    def _preview_header(self) -> QWidget:
        """预览顶部：左侧「更换模板」，右侧当前模板名。"""
        host = QWidget()
        lay = QHBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 10)
        lay.setSpacing(8)

        change = QPushButton("更换模板")
        change.setCursor(Qt.PointingHandCursor)
        change.setFixedHeight(28)
        change.setToolTip("换一套卡片皮肤（应用到当前卡包）")
        change.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};color:{W.T['ink']};border:none;"
            f"border-radius:14px;font-size:13px;padding:0 14px;}}"
            f"QPushButton:hover{{background:{W.T['brand_soft']};color:{W.T['brand']};}}")
        change.clicked.connect(self._open_templates)
        lay.addWidget(change)
        lay.addStretch(1)

        self.tpl_name_label = QLabel(CR.TEMPLATES[self._template_key()]["name"])
        self.tpl_name_label.setObjectName("sub")
        lay.addWidget(self.tpl_name_label)
        return host

    def _refresh_preview(self):
        if not hasattr(self, "preview_host"):
            return
        W.clear_layout(self.preview_body)
        parsed = self._parse()
        front, back = parsed["q"], parsed["a"]
        if not (front or back):
            tip = QLabel("在左侧写点内容，这里实时预览")
            tip.setObjectName("sub")
            tip.setAlignment(Qt.AlignCenter)
            tip.setMinimumHeight(90)
            self.preview_body.addWidget(tip)
            return
        card = dict(self.card)
        card.update(q=front, a=back, type=parsed["type"],
                    options=parsed["options"], answer=parsed["answer"])
        width = max(280, (self.width() or 430) - 32)
        widget = CR.build_cards(card, self._template_key(), self._reveal, width=width,
                                mask_shown=self._shown_masks, on_mask=self._on_mask)
        # 预览铺模板自己的页面底色（和复习页/浮卡一致：蓝底 + 粉/绿卡）
        page = CR.palette(self._template_key())["page"]
        frame = QFrame()
        frame.setObjectName("previewPage")
        frame.setStyleSheet(
            f"QFrame#previewPage{{background:{page};border-radius:0;}}")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 8, 16, 16)
        fl.setSpacing(6)
        fl.addWidget(widget, 0, Qt.AlignTop | Qt.AlignHCenter)
        fl.addStretch(1)
        self.preview_body.addWidget(frame, 1)

    def _on_mask(self, key: str):
        """预览里点一下挖空：揭开 / 盖回去。"""
        if key in self._shown_masks:
            self._shown_masks.discard(key)
        else:
            self._shown_masks.add(key)
        self._refresh_preview()

    # ------------------------------------------------------------ 格式动作
    def _fmt_cloze(self):
        """挖空：把所有划选的框一起挖掉，然后退出划选模式。"""
        was_multi = self.multi_mode
        self._each_range(lambda ed: F.apply_cloze(ed, notify=None))
        if was_multi:
            self._toggle_multi()          # 收起划选（清框、开关关掉）
            self.app.toast("已挖空，已退出划选")

    # ------------------------------------------------------------ 选中浮条
    def _make_sel_bar(self):
        """选中文字时浮出来的小工具条：复制 / 粘贴 / 全选 / 挖空。"""
        bar = QFrame(self.text.viewport())
        bar.setObjectName("selBar")
        bar.setStyleSheet(
            f"QFrame#selBar{{background:{W.T['panel']};"
            f"border:1px solid {W.T['line']};border-radius:12px;}}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        for text, tip, fn in (
            ("复制", "复制选中的文字", self._sel_copy),
            ("粘贴", "粘贴为纯文本", self._paste_plain),
            ("全选", "选中全部文字", self.text.selectAll),
            ("挖空", "把选中的文字挖成填空", self._sel_cloze),
        ):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setFixedHeight(28)
            b.setToolTip(tip)
            b.setStyleSheet(
                f"QPushButton{{background:{W.T['paper2']};color:{W.T['ink2']};border:none;"
                f"border-radius:8px;font-size:13px;padding:0 9px;}}"
                f"QPushButton:hover{{background:{W.T['brand_soft']};color:{W.T['brand']};}}")
            b.clicked.connect(lambda _=False, f=fn: self._sel_bar_action(f))
            lay.addWidget(b)
        bar.hide()
        self._sel_bar = bar
        self.text.selectionChanged.connect(self._sync_sel_bar)
        self.text.verticalScrollBar().valueChanged.connect(lambda _=0: bar.hide())

    def _sel_bar_action(self, fn):
        fn()
        self.text.setFocus()
        self._sync_sel_bar()

    def _sel_copy(self):
        self.text.copy()

    def _sel_cloze(self):
        self._fmt_cloze()

    def _sync_sel_bar(self):
        bar = getattr(self, "_sel_bar", None)
        if bar is None:
            return
        if self._mode != "edit" or not self.text.hasFocus() or not self.text.textCursor().hasSelection():
            bar.hide()
            return
        bar.adjustSize()
        cur = self.text.textCursor()
        c1 = QTextCursor(cur)
        c1.setPosition(cur.selectionStart())
        c2 = QTextCursor(cur)
        c2.setPosition(cur.selectionEnd())
        r1 = self.text.cursorRect(c1)
        r2 = self.text.cursorRect(c2)
        vp = self.text.viewport()
        w, h = bar.width(), bar.height()
        x = max(4, min(r1.left() - 8, vp.width() - w - 4))
        y = r1.top() - h - 6          # 优先放在选区上方
        if y < 2:
            y = r2.bottom() + 8       # 上面放不下就放到选区末尾下方
        bar.move(x, max(2, y))
        bar.show()
        bar.raise_()

    def _pal(self) -> dict:
        deck = self.store.deck((self.card or {}).get("deck_id")) or {}
        key = deck.get("template") or self.store.settings.get("default_template") or "sky"
        return CR.palette(key if key in CR.TEMPLATES else "sky")

    def _fmt_inkline(self):
        cur = self.text.textCursor()
        cur.insertText("\n---\n")
        self.text.setTextCursor(cur)
        self.text.setFocus()

    def _fmt_bold(self):
        self._each_range(lambda ed: F.apply_bold(ed))

    def _fmt_underline(self):
        self._each_range(lambda ed: F.apply_underline(ed))

    def _fmt_size(self):
        """字号：弹出 小/标准/大/特大，作用到选中（或划选的）文字。"""
        from PySide6.QtWidgets import QMenu
        self._sync_multi()
        if not self._ranges():
            self.app.toast("请先选中要改字号的文字")
            return
        m = QMenu(self)
        m.setStyleSheet(
            f"QMenu{{background:{W.T['panel']};border:1px solid {W.T['line']};"
            f"border-radius:10px;padding:4px;}}"
            f"QMenu::item{{padding:7px 22px;border-radius:7px;font-size:13.5px;}}"
            f"QMenu::item:selected{{background:{W.T['brand_soft']};color:{W.T['brand']};}}")
        for label, pt in (("小", 10.0), ("标准", F.FONT_BASE_PT),
                          ("大", 16.0), ("特大", 20.0)):
            act = m.addAction(label)
            act.triggered.connect(lambda _=False, p=pt: self._set_size(p))
        m.exec(self.bottom_bar.mapToGlobal(self.bottom_bar.rect().topLeft()))

    def _set_size(self, pt: float):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(pt)
        self._apply_fmt_all(fmt)

    def _fmt_color(self):
        rs = self._ranges()
        if not rs:
            self.app.toast("请先选中要上色的文字")
            return
        color = QColorDialog.getColor(self.text.textColor(), self, "选择字体颜色")
        if not color.isValid():
            return
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        self._apply_fmt_all(fmt)

    def _fmt_bg(self):
        rs = self._ranges()
        if not rs:
            self.app.toast("请先选中要加背景的文字")
            return
        color = QColorDialog.getColor(QColor("#FDEDE2"), self, "选择文字背景色")
        if not color.isValid():
            return
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        if color.name().upper() == "#" + F.CLOZE_COLOR:
            fmt.setProperty(F.CLOZE_PROP, 1)
        self._apply_fmt_all(fmt)

    def _fmt_clear(self):
        self._each_range(lambda ed: F.apply_clear(ed))

    def _fmt_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "插入图片", "", "图片 (*.png *.jpg *.jpeg *.gif *.bmp)")
        if not path:
            return
        rel = F.import_media(path)          # 复制进 <数据目录>/media/
        abs_path = F._abs_src(rel)
        fmt = QTextImageFormat()
        fmt.setName(abs_path)
        im = QImage(abs_path)
        if not im.isNull() and im.width() > 0:
            max_w = min(max(120, self.text.viewport().width() - 48), 360)
            scale = min(1.0, max_w / im.width())
            if scale < 1.0:
                fmt.setWidth(max(1, int(im.width() * scale)))
                fmt.setHeight(max(1, int(im.height() * scale)))
        self.text.textCursor().insertImage(fmt)
        self.text.setFocus()
        self.app.toast("已插入图片")

    # ------------------------------------------------------------ 组装 / 解析
    @staticmethod
    def _compose(c: dict) -> str:
        q = c.get("q") or ""
        if c.get("type") == "qa":
            back = c.get("a") or ""
            return f"{q}\n---\n{back}" if back else q
        lines = [q, "---"]
        for i, opt in enumerate(c.get("options") or []):
            lines.append(f"{'ABCDEF'[i]}. {opt}")
        ans = "".join("ABCDEF"[i] for i in sorted(c.get("answer") or []))
        if ans:
            lines.append(f"答案：{ans}")
        if c.get("analysis"):
            lines.append(str(c["analysis"]))
        return "\n".join(lines)

    def _parse(self) -> dict:
        """编辑器 → 卡片字段。结构按纯文本判断，内容保留富文本。"""
        hlines = F.editor_to_inline_html(self.text).split("\n")
        plines = self.text.toPlainText().split("\n")
        n = min(len(hlines), len(plines))
        hlines, plines = hlines[:n], plines[:n]

        sep = next((i for i, p in enumerate(plines) if p.strip() == "---"), None)
        if sep is None:
            front = "\n".join(hlines).strip()
            back_lines, plain_back = [], []
        else:
            front = "\n".join(hlines[:sep]).strip()
            back_lines = hlines[sep + 1:]
            plain_back = plines[sep + 1:]

        opts, answers, analysis = [], [], []
        for hl, pl in zip(back_lines, plain_back):
            s = pl.strip()
            m_opt = OPT_RE.match(s)
            m_ans = ANS_RE.match(s)
            if m_opt:
                body_html = re.sub(r"^\s*[A-Fa-f][.、．)）]\s*", "", hl, count=1)
                opts.append(body_html.strip())
            elif m_ans:
                answers = [ord(ch.upper()) - 65 for ch in m_ans.group(1)]
            elif s:
                analysis.append(hl.strip())

        if opts and answers:
            valid = [i for i in answers if 0 <= i < len(opts)]
            return {"q": front, "a": "",
                    "type": "single" if len(valid) <= 1 else "multi",
                    "options": opts, "answer": sorted(set(valid)),
                    "analysis": "\n".join(analysis).strip()}
        return {"q": front, "a": "\n".join(back_lines).strip(),
                "type": "qa", "options": [], "answer": [],
                "analysis": ""}

    # ------------------------------------------------------------ 保存
    def _blank_card(self) -> dict:
        """新建卡片时用的空壳（还没进 store，保存时才插入）。"""
        deck = self.store.deck(self.deck_id) if self.deck_id else None
        deck = deck or (self.store.decks[0] if self.store.decks else {})
        t = now_ms()
        return {
            "id": uid("c_"),
            "deck_id": deck.get("id") or self.deck_id,
            "group": self.group or (deck.get("groups") or ["未分组"])[0],
            "type": "qa", "q": "", "a": "", "options": [], "answer": [],
            "analysis": "", "tags": [], "created": t, "due": t,
            "interval": 0.0, "reps": 0, "ease": DEFAULT_EASE, "lapses": 0,
            "last_review": None, "suspended": False, "archived": False,
        }

    def _has_content(self) -> bool:
        try:
            p = self._parse()
        except Exception:
            return True
        return bool(p["q"] or p["a"] or p["options"])

    def _back(self):
        """左上角返回。

        从「新建」进来的页面（含保存后的预览、继续新建）：保存后直接回卡包页，
        编辑/预览的切换不算一次导航，所以不会停在上一张卡。
        """
        if getattr(self, "_origin_new", False):
            if self._has_content():
                self._persist()
            deck_id = (self.card or {}).get("deck_id") or self.deck_id
            self.app._nav_back = True
            try:
                if deck_id:
                    self.app.show_page("deck", deck_id=deck_id)
                else:
                    self.app.go_back()
            finally:
                self.app._nav_back = False
            return
        if self.is_new and not self._has_content():
            self.app.go_back()
            return
        self._save_and_back()

    def _persist(self) -> bool:
        """把编辑区内容写回 store（新建时插入），成功返回 True。"""
        try:
            parsed = self._parse()
            c = self.card
            c["q"] = parsed["q"]
            c["a"] = parsed["a"]
            c["type"] = parsed["type"]
            c["options"] = parsed["options"]
            c["answer"] = parsed["answer"]
            c["analysis"] = parsed["analysis"]
            if self.is_new:
                if not (c["q"] or c["a"] or c["options"]):
                    return False
                self.store.cards.append(c)
                d = self.store.deck(c["deck_id"])
                if d is not None:
                    groups = d.setdefault("groups", [])
                    if c["group"] not in groups:
                        groups.append(c["group"])
                    order = d.setdefault("group_order", [])
                    if c["group"] not in order:
                        order.append(c["group"])
                self.store.save()
                self.is_new = False
                self.card_id = c["id"]
                return True
            # 标签不在这个页面改，保留原值
            self.store.save()
            return True
        except Exception as e:
            self.app.toast(f"保存失败：{e}")
            return False

    def _save_clicked(self):
        """顶部「保存」：新建卡保存后停在预览，按钮变「继续新建」。"""
        if getattr(self, "_saved_new", False):
            self._continue_new()
            return
        was_new = self.is_new
        if not self._persist():
            if was_new:
                self.app.toast("写点内容再保存吧")
            return
        if not was_new:
            self.app.go_back()
            return
        # 新建卡保存成功 → 直接看预览
        self._saved_new = True
        if hasattr(self, "save_btn"):
            self.save_btn.setText("继续新建")
        self.app._cur_spec = ("card_edit", {"card_id": self.card.get("id"),
                                            "deck_id": self.card.get("deck_id"),
                                            "group": self.group})
        self._set_mode("preview")
        self.app.toast("已保存，可以继续新建下一张")

    def _continue_new(self):
        """再开一张同卡包/卡组的新卡。"""
        deck_id = self.card.get("deck_id")
        self.app._cur_spec = ("card_edit", {"card_id": self.card.get("id"),
                                            "deck_id": deck_id,
                                            "group": self.group})
        self.app.show_page("card_edit", deck_id=deck_id, group=self.group)

    def _save_and_back(self):
        if not self._persist():
            if self.is_new:
                self.app.toast("写点内容再保存吧")
            return
        self.app.go_back()

    # ------------------------------------------------------------ 快捷键
    def _install_shortcuts(self):
        pairs = [
            ("Ctrl+S", self._save_clicked),
            (F.FORMAT_SHORTCUTS["bold"], self._fmt_bold),
            ("Ctrl+U", self._fmt_underline),
            ("Ctrl+D", self._fmt_cloze),
            ("Ctrl+Shift+C", self._fmt_color),
            ("Ctrl+Shift+H", self._fmt_bg),
            ("Ctrl+Shift+0", self._fmt_clear),
            ("Ctrl+Return", self._fmt_inkline),
        ]
        for keys, fn in pairs:
            sc = QShortcut(QKeySequence(keys), self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)
