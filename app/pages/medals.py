# -*- coding: utf-8 -*-
"""pages/medals.py - 青蛙勋章：每一枚怎么达到的、什么时候解锁的。"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

import widgets as W
from pages.base import Page
from pages.journey_widgets import FROG_MEDAL_COLORS, FROG_MEDALS, MedalDot


class MedalsPage(Page):
    """勋章清单：门槛、进度、解锁时间。"""

    def build(self):
        super().build()
        s = self.store
        total = s.frogs_eaten()
        medals = FROG_MEDALS[1:]
        unlocked = sum(1 for m in medals if total >= m[2])
        self.appbar("青蛙勋章", f"已解锁 {unlocked} / {len(medals)}",
                    back=self.app.go_back)

        evts = s.frog_medal_times()
        intro = QLabel(f"累计吃掉 {total} 只青蛙 · 每吃一只都会推进勋章")
        intro.setObjectName("sub")
        self.add(intro)

        card = W.Card()
        card.body.setContentsMargins(14, 4, 14, 4)
        card.body.setSpacing(0)
        for i, (key, name, need, _emoji) in enumerate(medals):
            card.body.addWidget(self._row(i, name, need, total, evts.get(need)))
        self.add(card)
        self.stretch()

    def _row(self, idx: int, name: str, need: int, total: int, at) -> QWidget:
        got = total >= need
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(2, 8, 2, 8)
        rl.setSpacing(10)

        dot = MedalDot(got, FROG_MEDAL_COLORS[idx + 1], shape=idx, size=34)
        rl.addWidget(dot, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(name)
        color = W.T["ink"] if got else W.T["ink3"]
        t.setStyleSheet(f"font-size:13px;font-weight:700;color:{color};")
        col.addWidget(t)

        if got and at:
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(at) / 1000))
            sub_text = f"累计吃掉 {need} 只青蛙 · 第 {need} 只于 {when} 解锁"
        elif got:
            sub_text = f"累计吃掉 {need} 只青蛙 · 已解锁"
        else:
            sub_text = f"累计吃掉 {need} 只青蛙 · 还差 {need - total} 只"
        sub = QLabel(sub_text)
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        col.addWidget(sub)
        rl.addLayout(col, 1)

        tag = QLabel("已解锁" if got else f"{total} / {need}")
        tag.setStyleSheet(
            f"font-size:11px;font-weight:700;"
            f"color:{W.T['brand'] if got else W.T['ink3']};")
        rl.addWidget(tag, 0, Qt.AlignVCenter)
        return row
