# -*- coding: utf-8 -*-
"""pages/monsters.py - 怪物图鉴：6 只怪物、所需青蛙数与学习时长、吃青蛙记录。"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

import widgets as W
from pages.base import Page
from pages.journey_panels import MONSTERS, monster_level


class MonstersPage(Page):
    def build(self):
        total = self.store.frogs_eaten()
        idx, cur, nxt = monster_level(total)
        self.appbar("怪物图鉴", f"已解锁 {idx + 1} / {len(MONSTERS)}", back=self.app.go_back)

        # ---- 当前出战 ----
        card = W.Card()
        card.body.setContentsMargins(14, 12, 14, 12)
        card.body.setSpacing(6)
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        name = QLabel(cur[0])
        name.setStyleSheet(f"font-size:18px;font-weight:700;color:{W.T['ink']};")
        hl.addWidget(name)
        lv = QLabel(f"Lv.{idx + 1}")
        lv.setStyleSheet(f"background:{cur[2]};color:#FFFDF8;border-radius:9px;"
                         "font-size:11.5px;font-weight:700;padding:2px 8px;")
        hl.addWidget(lv)
        hl.addStretch(1)
        now = QLabel("出战中")
        now.setStyleSheet(f"background:{W.T['deep']};color:#FFFDF8;border-radius:9px;"
                          "font-size:10.5px;font-weight:700;padding:2px 8px;")
        hl.addWidget(now)
        card.body.addWidget(head)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        rl.addWidget(W.Monster(92, cur[2]), 0, Qt.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(4)
        rows = [("已吃青蛙", f"{total} 只"),
                ("累计学习", f"{total * 45} 分钟")]
        if nxt:
            rows += [("下一级", f"Lv.{idx + 2} {nxt[0]}"),
                     ("还差", f"{nxt[1] - total} 只 / 约 {(nxt[1] - total) * 45} 分钟")]
        for k, v in rows:
            lb = QLabel(f"{k}  {v}")
            lb.setStyleSheet(f"font-size:12.5px;color:{W.T['ink2']};")
            info.addWidget(lb)
        info.addStretch(1)
        rl.addLayout(info, 1)
        card.body.addWidget(row)
        self.add(card)

        # ---- 怪物图鉴：12 只铺满整页 ----
        for r in range(4):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            for j in range(3):
                k = r * 3 + j
                if k >= len(MONSTERS):
                    break
                mname, need, color = MONSTERS[k]
                box = W.Card(flat=True)
                box.body.setContentsMargins(8, 8, 8, 8)
                box.body.setSpacing(2)
                top = QWidget()
                tl = QHBoxLayout(top)
                tl.setContentsMargins(0, 0, 0, 0)
                tl.setSpacing(4)
                nm = QLabel(mname)
                nm.setStyleSheet(f"font-size:12.5px;font-weight:700;"
                                 f"color:{W.T['ink'] if k <= idx else W.T['ink3']};")
                tl.addWidget(nm)
                tl.addStretch(1)
                if k < idx:
                    tag = "已解锁"
                    tag_color = "#6FAE7A"
                elif k == idx:
                    tag = "当前"
                    tag_color = color
                else:
                    tag = "未解锁"
                    tag_color = W.T["line"]
                tag_fg = "#FFFDF8" if k <= idx else W.T["ink3"]
                tg = QLabel(tag)
                tg.setStyleSheet(f"background:{tag_color};color:{tag_fg};border-radius:8px;"
                                 "font-size:10px;font-weight:700;padding:1px 5px;")
                tl.addWidget(tg)
                box.body.addWidget(top)
                box.body.addWidget(W.Monster(40, color, "sleep" if k > idx else "happy"),
                                   0, Qt.AlignHCenter)
                cost = QLabel(f"需要 {need} 只 · 约 {need * 45 // 60} 小时")
                cost.setAlignment(Qt.AlignCenter)
                cost.setStyleSheet(f"font-size:10px;color:{W.T['ink3']};")
                box.body.addWidget(cost)
                rl.addWidget(box, 1)
            self.add(row)

        self.stretch()
