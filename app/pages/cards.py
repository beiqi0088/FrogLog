# -*- coding: utf-8 -*-
"""pages/cards.py - 指标明细：点今日的四宫格可以看到具体卡片。"""
from __future__ import annotations

import re
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

import widgets as W
from pages.base import Page, label
from pages.library import LinesLabel

KINDS = {
    "due": ("待复习卡片", "到期但还没复习的卡片"),
    "today": ("今日已学", "今天复习过的卡片"),
    "new": ("待学新卡", "还没开始学的卡片"),
    "overdue": ("已到期", "已经过了到期时间的卡片"),
}


def _plain(s: str) -> str:
    s = s or ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def _day0() -> int:
    return int(time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1)) * 1000)


class CardsPage(Page):
    CHUNK = 24

    def __init__(self, app, kind: str = "due"):
        self.kind = kind if kind in KINDS else "due"
        self._items: list[dict] = []
        self._pos = 0
        self._rows_lay = None
        self._scroll_connected = False
        super().__init__(app)
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._load_chunk)

    def build(self):
        super().build()
        s = self.store
        title, desc = KINDS[self.kind]
        self._today_counts = {}
        if self.kind == "today":
            for r in s.reviews:
                if self._is_today(r["at"]):
                    cid = r["card_id"]
                    self._today_counts[cid] = self._today_counts.get(cid, 0) + 1
        cards = self._cards()
        self.appbar(title, "今日", back=self.app.go_back)
        self.add(label(f"{len(cards)} 张 · {desc}", "sub"))

        if not cards:
            self.add(self._empty())
            self.stretch()
            return

        # 分块加载：卡片很多时先建前 24 行，滚动到底附近再继续。
        self._items = cards
        self._pos = 0
        host = QWidget()
        self._rows_lay = QVBoxLayout(host)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(12)
        self.add(host)
        self._load_chunk()
        self.stretch()

        if not self._scroll_connected:
            self._scroll_connected = True
            self.scroll.verticalScrollBar().valueChanged.connect(self._maybe_load)

    def _load_chunk(self):
        if self._rows_lay is None:
            return
        end = min(len(self._items), self._pos + self.CHUNK)
        for c in self._items[self._pos:end]:
            self._rows_lay.addWidget(self._row(c))
        self._pos = end

    def _maybe_load(self, value: int):
        bar = self.scroll.verticalScrollBar()
        if self._pos < len(self._items) and value >= bar.maximum() - 320:
            if not self._load_timer.isActive():
                self._load_timer.start(0)

    # ---------- 数据 ----------
    def _cards(self) -> list[dict]:
        s = self.store
        if self.kind == "today":
            live_ids = {c["id"] for c in s.live_cards()}
            seen: set[str] = set()
            ids = []
            for r in s.reviews:
                cid = r["card_id"]
                if cid in seen or cid not in live_ids or not self._is_today(r["at"]):
                    continue
                seen.add(cid)
                ids.append(cid)
            return [c for c in (s.card(i) for i in ids) if c]
        if self.kind == "new":
            return sorted([c for c in s.live_cards() if c["reps"] == 0],
                          key=lambda c: c.get("created") or 0)
        due = s.due_cards()
        if self.kind == "overdue":
            d0 = _day0()
            return sorted([c for c in due if c["due"] < d0], key=lambda c: c["due"])
        return sorted([c for c in due if c["reps"] > 0], key=lambda c: c["due"])

    # ---------- 行 ----------
    def _row(self, c: dict) -> QWidget:
        s = self.store
        box = W.ClickFrame()
        box.setObjectName("card")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(14, 11, 14, 11)
        bl.setSpacing(5)

        t = LinesLabel(_plain(c.get("q")) or _plain(c.get("a")) or "（无内容）",
                       13.5, 2, True, W.T["ink"])
        bl.addWidget(t)

        deck = s.deck(c.get("deck_id")) or {}
        meta = f"{deck.get('name', '—')} · {c.get('group') or '未分组'} · {self._state(c)}"
        m = QLabel(meta)
        m.setObjectName("sub")
        bl.addWidget(m)

        box.clicked.connect(lambda cc=c: self._open(cc))
        return box

    def _state(self, c: dict) -> str:
        now = int(time.time() * 1000)
        if self.kind == "today":
            n = self._today_counts.get(c["id"], 0)
            return f"今天复习 {n} 次"
        if c["reps"] == 0:
            return "新卡"
        days = (c["due"] - now) / 86400000
        if days <= -1:
            return f"逾期 {round(abs(days))} 天"
        if days < 1:
            return "今天到期"
        return f"{round(days)} 天后到期"

    def _open(self, c: dict):
        s = self.store
        s.save_selection(c["deck_id"], c.get("group") or "")
        self.app.deck_selection[c["deck_id"]] = c.get("group") or ""
        self.app.show_page("deck", deck_id=c["deck_id"])

    def _empty(self) -> QWidget:
        box = W.Card(flat=True)
        box.body.setContentsMargins(18, 30, 18, 30)
        t = QLabel("这里没有卡片")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:14px;font-weight:600;")
        s2 = QLabel("换个指标看看，或先去「记忆」里加卡片")
        s2.setObjectName("sub")
        s2.setAlignment(Qt.AlignCenter)
        box.body.addWidget(t)
        box.body.addWidget(s2)
        return box

    @staticmethod
    def _is_today(ms: int) -> bool:
        a = time.localtime(ms / 1000)
        b = time.localtime()
        return (a.tm_year, a.tm_yday) == (b.tm_year, b.tm_yday)
