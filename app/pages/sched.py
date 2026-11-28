# -*- coding: utf-8 -*-
"""pages/sched.py - 学习调度（Anki 卡组选项）：步骤 / 间隔 / 限额 / 保持率。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel, QHBoxLayout, QWidget, QCheckBox,
                               QComboBox, QGridLayout, QLineEdit, QSpinBox,
                               QDoubleSpinBox)

import widgets as W
from pages.base import Page, label


def _steps_text(steps) -> str:
    return ", ".join(str(int(s)) if float(s).is_integer() else str(s)
                     for s in (steps or []))


def _parse_steps(text: str) -> list[int]:
    out = []
    for part in (text or "").replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(max(1, int(float(part))))
        except ValueError:
            pass
    return out or [1, 10]


class SchedPage(Page):
    def __init__(self, app, deck_id: str | None = None):
        self.deck_id = deck_id
        super().__init__(app)

    def build(self):
        super().build()
        s = self.store
        deck = s.deck(self.deck_id) if self.deck_id else None
        self.cfg = s.deck_config(self.deck_id)
        title = "学习调度"
        eyebrow = deck["name"] if deck else "全局默认"
        self.appbar(title, eyebrow, back=self.app.go_back)
        self.add(label("学习步骤与间隔；改了立刻生效（新评分按新设置算）", "sub"))

        card = W.Card()
        body = card.body

        self.steps = self._line(body, "学习步骤（分钟，逗号分隔）",
                                _steps_text(self.cfg["learn_steps"]))
        self.relearn = self._line(body, "重学步骤（分钟）",
                                  _steps_text(self.cfg["relearn_steps"]))
        self.grad = self._spin(body, "毕业间隔（天）", self.cfg["graduating"], 1, 365)
        self.easy = self._spin(body, "简单间隔（天）", self.cfg["easy"], 1, 365)
        self.ret = self._spin(body, "目标保持率（%）",
                              float(self.cfg["retention"]) * 100, 70, 99, double=True)
        self.newday = self._spin(body, "每日新卡上限", self.cfg["new_per_day"], 0, 999)
        self.revday = self._spin(body, "每日复习上限", self.cfg["review_per_day"], 0, 9999)
        self.maxiv = self._spin(body, "最大间隔（天）", self.cfg["max_interval"], 1, 36500)

        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 4, 0, 2)
        tip = QLabel("模糊随机性")
        tip.setObjectName("sub")
        hl.addWidget(tip, 1)
        self.fuzz = QCheckBox()
        self.fuzz.setChecked(bool(self.cfg.get("fuzz", True)))
        hl.addWidget(self.fuzz)
        body.addWidget(row)

        self.bury_new = self._check(body, "新卡作答后搁置兄弟卡",
                                    bool(self.cfg.get("bury_new", False)))
        self.bury_reviews = self._check(body, "复习卡作答后搁置兄弟卡",
                                        bool(self.cfg.get("bury_reviews", False)))

        # 轻松日：周一到周日各自的排卡强度（Anki 的 Easy Days）
        t = QLabel("轻松日（这些天少排卡）")
        t.setObjectName("sub")
        body.addWidget(t)
        grid = QWidget()
        gl = QGridLayout(grid)
        gl.setContentsMargins(0, 0, 0, 2)
        gl.setHorizontalSpacing(4)
        gl.setVerticalSpacing(3)
        names = "一二三四五六日"
        cur = list(self.cfg.get("easy_days") or [1.0] * 7)
        while len(cur) < 7:
            cur.append(1.0)
        self.easy_boxes = []
        for i in range(7):
            lb = QLabel(names[i])
            lb.setAlignment(Qt.AlignCenter)
            lb.setStyleSheet(f"font-size:11.5px;color:{W.T['ink3']};")
            cb = QComboBox()
            cb.addItems(["正常", "减少", "最少"])
            v = round(float(cur[i]), 2)
            cb.setCurrentIndex(0 if v >= 0.99 else (1 if v > 0.01 else 2))
            cb.setFixedWidth(48)
            cb.setStyleSheet("QComboBox{font-size:12.5px;padding:4px 6px;}")
            gl.addWidget(lb, 0, i)
            gl.addWidget(cb, 1, i)
            self.easy_boxes.append(cb)
        body.addWidget(grid)

        hint = QLabel("兄弟卡 = 同一笔记下内容相同的多张卡（编辑器右上「兄弟卡」可创建）")
        hint.setWordWrap(True)
        hint.setObjectName("sub")
        body.addWidget(hint)
        self.add(card)

        save = W.PrimaryButton("保存")
        save.clicked.connect(self._save)
        self.add(save)
        self.stretch()

    # ---------- 控件 ----------
    def _line(self, body, title: str, value: str) -> QLineEdit:
        t = QLabel(title)
        t.setObjectName("sub")
        body.addWidget(t)
        e = QLineEdit(value)
        e.setPlaceholderText("如 1, 10")
        body.addWidget(e)
        return e

    def _spin(self, body, title: str, value, lo: int, hi: int, double=False):
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 2, 0, 2)
        t = QLabel(title)
        t.setObjectName("sub")
        hl.addWidget(t, 1)
        w = QDoubleSpinBox() if double else QSpinBox()
        w.setRange(lo, hi)
        w.setValue(float(value) if double else int(value))
        if double:
            w.setDecimals(0)
            w.setSuffix(" %")
        w.setFixedWidth(110)
        w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(w)
        body.addWidget(row)
        return w

    def _check(self, body, title: str, value: bool) -> QCheckBox:
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 4, 0, 2)
        t = QLabel(title)
        t.setObjectName("sub")
        hl.addWidget(t, 1)
        box = QCheckBox()
        box.setChecked(bool(value))
        hl.addWidget(box)
        body.addWidget(row)
        return box

    # ---------- 保存 ----------
    def _save(self):
        cfg = {
            "learn_steps": _parse_steps(self.steps.text()),
            "relearn_steps": _parse_steps(self.relearn.text()),
            "graduating": float(self.grad.value()),
            "easy": float(self.easy.value()),
            "retention": round(self.ret.value() / 100.0, 2),
            "new_per_day": int(self.newday.value()),
            "review_per_day": int(self.revday.value()),
            "max_interval": float(self.maxiv.value()),
            "fuzz": bool(self.fuzz.isChecked()),
            "easy_days": [1.0 if b.currentIndex() == 0 else
                          (0.5 if b.currentIndex() == 1 else 0.0)
                          for b in self.easy_boxes],
            "bury_new": bool(self.bury_new.isChecked()),
            "bury_reviews": bool(self.bury_reviews.isChecked()),
        }
        if self.deck_id:
            self.store.set_deck_config(self.deck_id, **cfg)
            self.app.toast("已保存到本卡包")
        else:
            self.store.set_global_sched(**cfg)
            self.app.toast("已保存为全局默认")
