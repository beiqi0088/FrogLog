# -*- coding: utf-8 -*-
"""pages/today.py - 今日：同步状态 + 四宫格指标 + 继续学习。"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, QWidget,
                               QPushButton, QGridLayout, QSizePolicy)

import theme

import widgets as W
from pages.base import Page, label
from pages.library import OneLineLabel


class StatIcon(QWidget):
    """四宫格图标：淡色圆角底座 + 线稿图标。"""

    def __init__(self, kind: str, size: int = 26, color: str | None = None,
                 bg: str | None = None, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.color = color or W.T["ink2"]
        self.bg = bg or W.T["paper2"]
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.bg))
        p.drawRoundedRect(r, 9, 9)

        pen = QPen(QColor(self.color), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        inset = 6.5
        x0, y0 = inset, inset
        w = self.width() - inset * 2
        h = self.height() - inset * 2
        if self.kind == "clock":
            p.drawEllipse(QRectF(x0, y0, w, h))
            p.drawLine(QPointF(x0 + w / 2, y0 + h / 2), QPointF(x0 + w / 2, y0 + h * 0.22))
            p.drawLine(QPointF(x0 + w / 2, y0 + h / 2), QPointF(x0 + w * 0.82, y0 + h * 0.62))
        elif self.kind == "book":
            p.drawRoundedRect(QRectF(x0, y0 + 0.5, w, h - 1), 2.4, 2.4)
            p.drawLine(QPointF(x0 + 2.5, y0 + h * 0.38), QPointF(x0 + w - 2.5, y0 + h * 0.38))
            p.drawLine(QPointF(x0 + 2.5, y0 + h * 0.66), QPointF(x0 + w - 2.5, y0 + h * 0.66))
        elif self.kind == "sheet":
            p.drawRoundedRect(QRectF(x0 + 2.0, y0, w - 4.0, h), 2.4, 2.4)
            p.drawRoundedRect(QRectF(x0, y0 + 2.4, w - 4.0, h - 2.4), 2.4, 2.4)
        elif self.kind == "calendar":
            p.drawRoundedRect(QRectF(x0, y0 + 1.6, w, h - 1.6), 2.4, 2.4)
            p.drawLine(QPointF(x0 + 0.6, y0 + h * 0.42), QPointF(x0 + w - 0.6, y0 + h * 0.42))
            p.drawLine(QPointF(x0 + w * 0.28, y0), QPointF(x0 + w * 0.28, y0 + 3.2))
            p.drawLine(QPointF(x0 + w * 0.72, y0), QPointF(x0 + w * 0.72, y0 + 3.2))
        elif self.kind == "check":
            path = QPainterPath()
            path.moveTo(x0 + 0.6, y0 + h * 0.52)
            path.lineTo(x0 + w * 0.38, y0 + h - 1.2)
            path.lineTo(x0 + w - 0.4, y0 + 1.2)
            p.drawPath(path)


class StatTile(W.Card):
    """一格指标：淡色图标底座 + 标签 + 大数字；可点击查看明细。"""

    from PySide6.QtCore import Signal as _Signal
    clicked = _Signal()

    def __init__(self, kind: str, name: str, value: str, unit: str = "张",
                 accent: str | None = None, tint: str | None = None,
                 number: str | None = None, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.body.setContentsMargins(14, 12, 12, 12)
        self.body.setSpacing(4)

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        hl.addWidget(StatIcon(kind, 26, accent or W.T["ink2"], tint), 0, Qt.AlignVCenter)
        cap = QLabel(name)
        cap.setStyleSheet(f"font-size:11.5px;color:{W.T['ink2']};font-weight:600;")
        hl.addWidget(cap)
        hl.addStretch(1)
        chev = QLabel("›")
        chev.setStyleSheet(f"color:{W.T['ink3']};font-size:14px;")
        hl.addWidget(chev)
        self.body.addWidget(head)

        num = QLabel(
            f"<span style='font-size:29px;font-weight:700;color:{number or W.T['ink']};'>{value}</span>"
            f"<span style='font-size:11.5px;color:{W.T['ink3']};'> {unit}</span>")
        num.setTextFormat(Qt.RichText)
        self.body.addWidget(num)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class SyncButton(QPushButton):
    """同步图标：闭合圆环 + 切线箭头；有未同步修改时右上角一个红点。"""

    def __init__(self, dirty: bool = False, parent=None):
        super().__init__(parent)
        self.dirty = dirty
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background:transparent;border:none;")

    def set_dirty(self, dirty: bool):
        self.dirty = dirty
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        cx = cy = w / 2
        r = 9.0
        col = QColor(W.T["brand"] if self.dirty else W.T["ink2"])

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(W.T["paper2"]))
        p.drawEllipse(QPointF(cx, cy), w / 2 - 1, w / 2 - 1)

        pen = QPen(col, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        if self.dirty:
            p.setPen(QPen(QColor(W.T["paper"]), 2.0))
            p.setBrush(QColor(W.T["red"]))
            p.drawEllipse(QPointF(w - 8.0, 8.0), 3.6, 3.6)


class LearnCard(W.Card):
    """可点的卡组卡：点空白处进入学习。"""

    from PySide6.QtCore import Signal as _Signal
    clicked = _Signal()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


def learn_card(app, g: dict) -> QWidget:
    """一张「继续学习」卡：标题主导 + 右上「查看卡组」，整卡点击进入学习。"""
    box = LearnCard()
    box.setCursor(Qt.PointingHandCursor)
    box.clicked.connect(lambda: app.start_review(g["deck"]["id"], group=g["group"]))
    box.body.setContentsMargins(16, 13, 16, 13)
    box.body.setSpacing(5)

    head = QWidget()
    hl = QHBoxLayout(head)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    t = OneLineLabel(g["group"])
    t.setStyleSheet(f"font-size:17px;font-weight:700;color:{W.T['ink']};")
    hl.addWidget(t, 1)
    view = QPushButton("查看卡组 ›")
    view.setCursor(Qt.PointingHandCursor)
    view.setStyleSheet(
        f"QPushButton{{background:transparent;border:none;font-size:11px;"
        f"color:{W.T['ink2']};padding:0;}}"
        f"QPushButton:hover{{color:{W.T['brand']};}}")
    view.clicked.connect(lambda: open_deck(app, g))
    hl.addWidget(view, 0, Qt.AlignVCenter)
    box.body.addWidget(head)

    sub = QLabel(f"到期复习 {g['due']} · 待学新卡 {g['new']} · 学习中 {g['learning']}")
    sub.setStyleSheet(f"font-size:11px;color:{W.T['ink2']};")
    box.body.addWidget(sub)
    return box


def open_deck(app, g: dict):
    app.store.save_selection(g["deck"]["id"], g["group"])
    app.deck_selection[g["deck"]["id"]] = g["group"]
    app.show_page("deck", deck_id=g["deck"]["id"])


def collect_groups(store, due_all) -> list[dict]:
    # 一次分桶：原先每个卡组都重新扫一遍全部卡片和到期列表，卡多时是 O(组数×卡片数)。
    by_key: dict[tuple[str, str], list] = {}
    for c in store.cards:
        if c.get("archived"):
            continue
        by_key.setdefault((c["deck_id"], c.get("group", "未分组")), []).append(c)
    due_count: dict[tuple[str, str], int] = {}
    for c in due_all:
        key = (c["deck_id"], c.get("group", "未分组"))
        due_count[key] = due_count.get(key, 0) + 1

    out = []
    for d in store.decks:
        if d.get("archived"):
            continue
        did = d["id"]
        skip = store.archived_groups(did) | store.completed_groups(did)
        for g in store.ordered_groups(did):
            if g in skip:
                continue
            items = by_key.get((did, g))
            if not items:
                continue
            last = max((c.get("last_review") or 0) for c in items)
            due = due_count.get((did, g), 0)
            new = sum(1 for c in items if c["reps"] == 0)
            learning = sum(1 for c in items if c["reps"] > 0)
            out.append({"group": g, "deck": d, "items": items, "last": last,
                        "due": due, "new": new, "learning": learning})
    out.sort(key=lambda x: (-x["last"], x["group"]))
    return out


def _empty_box(title: str, sub: str) -> QWidget:
    box = W.Card(flat=True)
    box.body.setContentsMargins(18, 26, 18, 26)
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


class AllGroupsPage(Page):
    """查看全部：所有卡组的继续学习列表。"""

    def build(self):
        super().build()
        self.appbar("继续学习", None, back=self.app.go_back)
        groups = collect_groups(self.store, self.store.due_cards())
        self.add(label(f"{len(groups)} 个卡组 · 按最近学习", "sub"))
        if not groups:
            self.add(_empty_box("还没有卡组", "导入一份 Word，或在记忆里新建卡包。"))
        else:
            for g in groups:
                self.add(learn_card(self.app, g))
        self.stretch()


class TodayPage(Page):
    def build(self):
        super().build()
        s = self.store
        due_all = s.due_cards()
        live = s.live_cards()
        live_ids = {c["id"] for c in live}
        today_reviews = [r for r in s.reviews
                         if self._is_today(r["at"]) and r["card_id"] in live_ids]
        new_cards = [c for c in live if c["reps"] == 0]
        review_due = [c for c in due_all if c["reps"] > 0]
        overdue = [c for c in due_all if c["due"] < self._day0()]

        # ---------- 顶栏 ----------
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 10, 0, 2)
        hl.setSpacing(10)

        col = QVBoxLayout()
        col.setSpacing(3)
        dirty = self._dirty()

        # 同步状态：浅底胶囊
        chip = QWidget()
        chip.setAttribute(Qt.WA_StyledBackground, True)
        chip.setFixedHeight(22)
        chip.setStyleSheet(
            f"background:{W.T['red_soft'] if dirty else W.T['brand_soft']};border-radius:11px;")
        chl = QHBoxLayout(chip)
        chl.setContentsMargins(9, 0, 11, 0)
        chl.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(
            f"background:{W.T['red'] if dirty else W.T['green']};border-radius:3px;")
        chl.addWidget(dot, 0, Qt.AlignVCenter)
        st = QLabel("有未同步的修改" if dirty else self._sync_text().replace("● ", ""))
        st.setStyleSheet(
            f"font-size:10.5px;font-weight:700;"
            f"color:{W.T['red'] if dirty else W.T['brand']};background:transparent;")
        chl.addWidget(st)
        chl.addStretch(1)
        crow = QWidget()
        crl = QHBoxLayout(crow)
        crl.setContentsMargins(0, 0, 0, 0)
        crl.addWidget(chip, 0, Qt.AlignLeft)
        crl.addStretch(1)
        col.addWidget(crow)

        title = QLabel("今日")
        title.setObjectName("h1")
        col.addWidget(title)

        # 日期 + 还差多少
        today = time.localtime()
        left = len(due_all)
        sub = QLabel(f"{today.tm_mon} 月 {today.tm_mday} 日 · 今天还差 {left} 张")
        sub.setStyleSheet(f"font-size:11.5px;color:{W.T['ink2']};")
        col.addWidget(sub)
        hl.addLayout(col, 1)

        sync = SyncButton(dirty)
        sync.clicked.connect(self._do_sync)
        hl.addWidget(sync, 0, Qt.AlignTop)
        self.add(head)

        # ---------- 四宫格 ----------
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        AMBER, AMBER_SOFT = "#B8792A", "#FBF0E1"
        tiles = [
            ("clock", "待复习卡片", str(len(review_due)), W.T["blue"], W.T["blue_soft"], None),
            ("check", "今日已学", str(len(today_reviews)), W.T["brand"], W.T["brand_soft"], None),
            ("sheet", "待学新卡", str(len(new_cards)), AMBER, AMBER_SOFT, None),
            ("calendar", "已到期", str(len(overdue)), W.T["red"], W.T["red_soft"],
             W.T["red"] if overdue else None),
        ]
        keys = ("due", "today", "new", "overdue")
        for i, (kind, name, val, accent, tint, num_color) in enumerate(tiles):
            tile = StatTile(kind, name, val, accent=accent, tint=tint, number=num_color)
            tile.clicked.connect(
                lambda k=keys[i]: self.app.show_page("cards", kind=k))
            grid.addWidget(tile, i // 2, i % 2)
        self.add(grid_host)

        # ---------- 继续学习 ----------
        groups = collect_groups(s, due_all)
        sec = QWidget()
        sl = QHBoxLayout(sec)
        sl.setContentsMargins(2, 8, 2, 0)
        sl.setSpacing(8)
        t = QLabel("继续学习")
        t.setObjectName("h2")
        sl.addWidget(t, 1)
        more = QPushButton("查看全部 ›")
        more.setCursor(Qt.PointingHandCursor)
        more.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;font-size:11px;"
            f"color:{W.T['ink2']};}}")
        more.clicked.connect(lambda: self.app.show_page("groups"))
        sl.addWidget(more)
        self.add(sec)

        if not groups:
            self.add(_empty_box("还没有卡组", "导入一份 Word，或在记忆里新建卡包。"))
        else:
            for g in groups[:3]:
                self.add(learn_card(self.app, g))
        self.stretch()

    # ---------- 同步 ----------
    def _last_sync(self) -> int:
        return int(((self.store.state.get("settings") or {}).get("last_sync") or 0))

    def _dirty(self) -> bool:
        last = self._last_sync()
        return self.store.updated_at() > last + 1000

    def _sync_text(self) -> str:
        last = self._last_sync()
        if not last:
            return "● 未同步"
        mins = max(0, int((time.time() * 1000 - last) / 60000))
        if mins < 1:
            when = "刚刚"
        elif mins < 60:
            when = f"{mins} 分钟前"
        else:
            when = f"{mins // 60} 小时前"
        return f"● 已同步 · {when}"

    def _do_sync(self):
        from pages.sync import sync_cfg
        cfg = sync_cfg(self.store)
        c = cfg.get(cfg.get("provider")) or {}
        if not (c.get("url") or c.get("endpoint")):
            self.app.show_page("sync")
            return
        self.app.sync_now()

    # ---------- 工具 ----------
    @staticmethod
    def _day0() -> int:
        return int(time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1)) * 1000)

    def _is_today(self, ms: int) -> bool:
        a = time.localtime(ms / 1000)
        b = time.localtime()
        return (a.tm_year, a.tm_yday) == (b.tm_year, b.tm_yday)
