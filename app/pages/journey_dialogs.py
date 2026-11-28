# -*- coding: utf-8 -*-
"""pages/journey_dialogs.py - 征途的三个弹层：每日结算 / 升级 / 加自定义奖励。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QSpinBox, QVBoxLayout, QWidget)

import widgets as W


def _dlg(owner, title: str, width: int = 380):
    d = QDialog(owner)
    d.setWindowTitle(title)
    d.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")
    d.setMinimumWidth(width)
    lay = QVBoxLayout(d)
    lay.setContentsMargins(20, 18, 20, 18)
    lay.setSpacing(12)
    return d, lay


def _title(lay, text: str):
    t = QLabel(text)
    t.setStyleSheet(f"font-size:19px;font-weight:700;color:{W.T['ink']};")
    lay.addWidget(t)


def _row(lay, k: str, v: str, color: str | None = None):
    row = QWidget()
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 0, 0, 0)
    a = QLabel(k)
    a.setStyleSheet(f"font-size:13.5px;color:{W.T['ink2']};")
    b = QLabel(v)
    b.setStyleSheet(f"font-size:13.5px;font-weight:700;color:{color or W.T['ink']};")
    rl.addWidget(a, 1)
    rl.addWidget(b, 0, Qt.AlignRight)
    lay.addWidget(row)


class SettleDialog(QDialog):
    """跨天结算摘要：完成 / 漏做 / 连击 / 金币，漏做会扣血。"""

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("今日结算")
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")
        self.setMinimumWidth(360)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        icon = QLabel("🌙")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:31px;")
        lay.addWidget(icon)

        t = QLabel("今日结算")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(f"font-size:21px;font-weight:700;color:{W.T['ink']};")
        lay.addWidget(t)

        sub = QLabel(f"{info.get('date', '')} · 24:00 自动结算")
        sub.setAlignment(Qt.AlignCenter)
        sub.setObjectName("sub")
        lay.addWidget(sub)

        card = W.Card(flat=True)
        card.body.setContentsMargins(16, 12, 16, 12)
        card.body.setSpacing(7)
        _row(card.body, "完成记录", f"{info.get('records', info.get('done', 0))} 次",
             W.T["brand"])
        if int(info.get("xp") or 0):
            _row(card.body, "经验", f"+{int(info['xp'])}", W.T["brand"])
        missed = int(info.get("missed", 0))
        if missed:
            _row(card.body, "漏做每日", f"{missed} 项 · −{info.get('hp_lost', 0)} 生命",
                 W.T["red"])
        _row(card.body, "连击", f"{info.get('streak', 0)} 天")
        _row(card.body, "金币", f"{info.get('gold', 0)} GP")
        lay.addWidget(card)

        tip = QLabel(f"生命 {info.get('hp', 0)} / {info.get('hp_max', 50)}"
                     + ("  ·  倒下：金币 −10%、连击清零" if info.get("down")
                        else "  ·  明早自动回 1 点"))
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet(f"font-size:13px;color:{W.T['red'] if info.get('down') else W.T['ink3']};")
        lay.addWidget(tip)

        btn = W.PrimaryButton("明天继续")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)


class LevelUpDialog(QDialog):
    """升级：展示涨了什么，并让用户把属性点分掉。"""

    def __init__(self, lv: int, points: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("升级")
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")
        self.setMinimumWidth(380)
        self.picked = None
        self.attr_points = int(points)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        icon = QLabel("🏆")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:31px;")
        lay.addWidget(icon)

        t = QLabel("升级！")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(f"font-size:22px;font-weight:700;color:{W.T['ink']};")
        lay.addWidget(t)

        sub = QLabel(f"Lv.{lv - 1} → Lv.{lv}")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size:18px;font-weight:700;color:{W.T['brand']};")
        lay.addWidget(sub)

        card = W.Card(flat=True)
        card.body.setContentsMargins(16, 12, 16, 12)
        card.body.setSpacing(7)
        _row(card.body, "生命上限", "+5")
        _row(card.body, "生命值", "回满", W.T["brand"])
        _row(card.body, "属性点", f"+{points} 可分配", W.T["accent"])
        lay.addWidget(card)

        tip = QLabel("点一个属性，把点数用掉")
        tip.setAlignment(Qt.AlignCenter)
        tip.setObjectName("sub")
        lay.addWidget(tip)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        for key, name in (("str", "力量"), ("int", "智力"), ("con", "体质"), ("per", "感知")):
            b = W.Chip(name)
            b.clicked.connect(lambda _, k=key: self._pick(k))
            rl.addWidget(b, 1)
        lay.addWidget(row)

        later = W.GhostButton("稍后再说")
        later.clicked.connect(self.accept)
        lay.addWidget(later)

    def _pick(self, key: str):
        self.picked = key
        self.accept()


class AddRewardDialog(QDialog):
    """加一条自定义奖励：名字 + 价格。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加奖励")
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")
        self.setMinimumWidth(360)
        self.result_title = ""
        self.result_price = 30

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)
        _title(lay, "添加奖励")

        sub = QLabel("金币只花在你自己的奖励上：看剧、奶茶、睡懒觉都行")
        sub.setWordWrap(True)
        sub.setObjectName("sub")
        lay.addWidget(sub)

        self.name = QLineEdit()
        self.name.setPlaceholderText("奖励名称，比如「看一集剧」")
        lay.addWidget(self.name)

        price_row = QWidget()
        pl = QHBoxLayout(price_row)
        pl.setContentsMargins(0, 0, 0, 0)
        cap = QLabel("需要金币")
        cap.setStyleSheet(f"color:{W.T['ink2']};font-size:13.5px;")
        self.price = QSpinBox()
        self.price.setRange(1, 9999)
        self.price.setValue(30)
        self.price.setSuffix(" GP")
        pl.addWidget(cap, 0)
        pl.addStretch(1)
        pl.addWidget(self.price, 0)
        lay.addWidget(price_row)

        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        cancel = W.GhostButton("取消")
        cancel.clicked.connect(self.reject)
        ok = W.PrimaryButton("添加")
        ok.clicked.connect(self._ok)
        bl.addWidget(cancel, 1)
        bl.addWidget(ok, 1)
        lay.addWidget(btns)

    def _ok(self):
        self.result_title = self.name.text().strip()
        self.result_price = int(self.price.value())
        if self.result_title:
            self.accept()
