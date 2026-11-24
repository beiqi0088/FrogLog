# -*- coding: utf-8 -*-
"""pages/stats.py - 统计：复习量 / 到期预测 / 间隔分布 / 卡片状态。"""
from __future__ import annotations

import time
from collections import Counter, defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget

import widgets as W
from pages.base import Page, label

DAYS = 31
FORECAST_DAYS = 31


def _day_key(ts_ms: int) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts_ms / 1000))


class StatsPage(Page):
    def build(self):
        super().build()
        s = self.store
        cards = s.live_cards()
        reviews = s.live_reviews(cards)
        self.appbar("统计", f"近 {DAYS} 天 · {len(reviews)} 次复习",
                    back=self.app.go_back)

        # ---------- 关键指标 ----------
        tiles = W.Card()
        grid = QHBoxLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        mastered = sum(1 for c in cards if c.get("reps", 0) >= 4
                       and c.get("interval", 0) >= 21)
        learned = [c for c in cards if c.get("reps", 0) > 0]
        avg_iv = (sum(c.get("interval", 0) for c in learned) / len(learned)) if learned else 0
        keep = self._retention(reviews)
        for i, (val, name) in enumerate((
                (str(len(cards)), "总卡片"),
                (str(mastered), "已掌握"),
                (f"{avg_iv:.0f}天", "平均间隔"),
                (f"{keep}%", "留存率"))):
            if i:
                div = QWidget()
                div.setFixedWidth(1)
                div.setStyleSheet(f"background:{W.T['line']};")
                grid.addWidget(div)
            cell = QWidget()
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(0, 2, 0, 2)
            cl.setSpacing(1)
            v = QLabel(val)
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"font-size:18px;font-weight:700;color:{W.T['ink']};")
            n = QLabel(name)
            n.setAlignment(Qt.AlignCenter)
            n.setObjectName("sub")
            cl.addWidget(v)
            cl.addWidget(n)
            grid.addWidget(cell, 1)
        tiles.body.addLayout(grid)
        self.add(tiles)

        # ---------- 复习量 ----------
        self.section("复习量", label(f"近 {DAYS} 天", "sub"))
        labels, new_series, rev_series = self._daily_reviews(reviews)
        box = W.Card()
        box.body.addWidget(W.StackBars(labels, [new_series, rev_series],
                                       [W.T["accent"], W.T["brand"]], 150))
        box.body.addWidget(self._legend([("新学", W.T["accent"]),
                                         ("复习", W.T["brand"])]))
        self.add(box)

        # ---------- 到期预测 ----------
        self.section("到期预测", label(f"未来 {FORECAST_DAYS} 天", "sub"))
        flabels, fvals = self._forecast(cards)
        box2 = W.Card()
        box2.body.addWidget(W.StackBars(flabels, [fvals], [W.T["accent"]], 140))
        self.add(box2)

        # ---------- 间隔分布 ----------
        self.section("间隔分布", label(f"{len(learned)} 张已学", "sub"))
        ilabels, ivals = self._intervals(learned)
        box3 = W.Card()
        box3.body.addWidget(W.StackBars(ilabels, [ivals], [W.T["blue"]], 140))
        self.add(box3)

        # ---------- 卡片状态 ----------
        parts, total = self._status(cards)
        self.section("卡片状态", label(f"{total} 张", "sub"))
        box4 = W.Card()
        box4.body.addWidget(W.StackBar(parts, 16))
        box4.body.addWidget(self._legend([(n, c) for n, v, c in parts if v]))
        self.add(box4)
        self.stretch()

    # ---------- 组件 ----------
    def _legend(self, items, per_row: int = 3) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 2, 0, 0)
        outer.setSpacing(3)
        for start in range(0, len(items), per_row):
            row = QHBoxLayout()
            row.setSpacing(10)
            for name, color in items[start:start + per_row]:
                dot = QLabel("●")
                dot.setStyleSheet(f"color:{color};font-size:10px;")
                row.addWidget(dot)
                lb = QLabel(name)
                lb.setObjectName("sub")
                row.addWidget(lb)
            row.addStretch(1)
            outer.addLayout(row)
        return w

    # ---------- 数据 ----------
    def _retention(self, reviews) -> int:
        if not reviews:
            return 0
        return round(sum(1 for r in reviews if r.get("rating", 0) >= 2) / len(reviews) * 100)

    def _daily_reviews(self, reviews):
        days = [time.strftime("%m-%d", time.localtime(
            time.time() - (DAYS - 1 - i) * 86400)) for i in range(DAYS)]
        keys = [time.strftime("%Y-%m-%d", time.localtime(
            time.time() - (DAYS - 1 - i) * 86400)) for i in range(DAYS)]
        first_seen = set()
        new_c, rev_c = defaultdict(int), defaultdict(int)
        for r in sorted(reviews, key=lambda x: x["at"]):
            k = _day_key(r["at"])
            if r["card_id"] in first_seen:
                rev_c[k] += 1
            else:
                first_seen.add(r["card_id"])
                new_c[k] += 1
        return days, [new_c.get(k, 0) for k in keys], [rev_c.get(k, 0) for k in keys]

    def _forecast(self, cards):
        tm = time.localtime()
        base = int(time.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday, 0, 0, 0, 0, 0, -1)) * 1000)
        labels, vals = [], []
        # 先按天分桶，避免每一天都把全部卡片扫一遍。
        buckets = Counter()
        for c in cards:
            due = int(c.get("due") or 0)
            if c.get("suspended") or c.get("archived"):
                continue
            day = (due - base) // 86400_000
            if 0 <= day < FORECAST_DAYS:
                buckets[int(day)] += 1
        for i in range(FORECAST_DAYS):
            labels.append(time.strftime("%m-%d", time.localtime((base + i * 86400_000) / 1000)))
            vals.append(buckets.get(i, 0))
        return labels, vals

    def _intervals(self, learned):
        buckets = [("1-3", 0), ("4-7", 0), ("8-14", 0), ("15-30", 0),
                   ("31-90", 0), ("90+", 0)]
        out = [0] * len(buckets)
        for c in learned:
            iv = float(c.get("interval") or 0)
            if iv <= 3:
                i = 0
            elif iv <= 7:
                i = 1
            elif iv <= 14:
                i = 2
            elif iv <= 30:
                i = 3
            elif iv <= 90:
                i = 4
            else:
                i = 5
            out[i] += 1
        return [b[0] for b in buckets], out

    def _status(self, cards):
        new = sum(1 for c in cards if int(c.get("reps") or 0) == 0
                  and not c.get("suspended"))
        suspended = sum(1 for c in cards if c.get("suspended"))
        buried = sum(1 for c in cards if int(c.get("buried_until") or 0) > int(time.time() * 1000)
                     and not c.get("suspended"))
        learning = sum(1 for c in cards if c.get("state") in ("learning", "relearning")
                       and not c.get("suspended"))
        review = max(0, len(cards) - new - suspended - buried - learning)
        parts = [
            ("新卡", new, W.T["ink3"]),
            ("学习中", learning, W.T["accent"]),
            ("复习中", review, W.T["brand"]),
            ("暂停", suspended, W.T["red"]),
            ("搁置", buried, W.T["blue"]),
        ]
        return parts, len(cards)
