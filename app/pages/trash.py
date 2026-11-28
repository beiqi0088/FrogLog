# -*- coding: utf-8 -*-
"""pages/trash.py - 回收站：删掉的卡片 / 卡组 / 卡包，可恢复或彻底删除。"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

import widgets as W
from pages.base import Page, label

KIND_NAME = {"cards": "卡片", "group": "卡组", "deck": "卡包"}


def _when(ms: int) -> str:
    if not ms:
        return ""
    t = time.localtime(ms / 1000)
    now = time.localtime()
    if (t.tm_year, t.tm_yday) == (now.tm_year, now.tm_yday):
        return time.strftime("今天 %H:%M", t)
    return time.strftime("%m-%d %H:%M", t)


class TrashPage(Page):
    def build(self):
        super().build()
        s = self.store
        items = list(s.trash)
        self.appbar("回收站", f"{len(items)} 项", back=self.app.go_back)

        tip = QLabel("删掉的卡片、卡组、卡包会先放这里，可以恢复；彻底删除后就找不回来了。")
        tip.setObjectName("sub")
        tip.setWordWrap(True)
        self.add(tip)

        if not items:
            card = W.Card(flat=True)
            card.body.setContentsMargins(18, 26, 18, 26)
            t = QLabel("回收站是空的")
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet(f"font-size:15px;font-weight:700;color:{W.T['ink']};")
            card.body.addWidget(t)
            hint = QLabel("在「记忆」里删除卡片、卡组或卡包，都会先到这里")
            hint.setAlignment(Qt.AlignCenter)
            hint.setObjectName("sub")
            hint.setWordWrap(True)
            card.body.addWidget(hint)
            self.add(card)
            self.stretch()
            return

        groups = {k: [x for x in items if x.get("kind") == k]
                  for k in ("cards", "group", "deck")}
        for kind, rows in groups.items():
            if not rows:
                continue
            self.section(KIND_NAME[kind], label(f"{len(rows)} 项", "sub"))
            for e in rows:
                self.body.addWidget(self._row(e))

        clear = QPushButton("清空回收站")
        clear.setCursor(Qt.PointingHandCursor)
        clear.setFixedHeight(40)
        clear.setStyleSheet(
            f"QPushButton{{background:transparent;border:1px solid {W.T['line']};"
            f"border-radius:12px;font-size:13.5px;font-weight:600;color:{W.T['red']};}}"
            f"QPushButton:hover{{background:{W.T['panel']};}}")
        clear.clicked.connect(self._clear)
        self.body.addSpacing(6)
        self.body.addWidget(clear)
        self.stretch()

    # ---------------- 一行 ----------------
    def _row(self, e: dict) -> QWidget:
        card = W.Card()
        card.body.setContentsMargins(15, 10, 12, 10)
        card.body.setSpacing(6)
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        t = QLabel(e.get("title") or "—")
        t.setStyleSheet(f"font-size:14.5px;font-weight:700;color:{W.T['ink']};")
        hl.addWidget(t, 1)
        stamp = QLabel(_when(int(e.get("at") or 0)))
        stamp.setObjectName("sub")
        hl.addWidget(stamp, 0, Qt.AlignVCenter)
        card.body.addWidget(head)

        sub = QLabel((e.get("sub") or "").strip(" ·"))
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        card.body.addWidget(sub)

        acts = QWidget()
        al = QHBoxLayout(acts)
        al.setContentsMargins(0, 2, 0, 0)
        al.setSpacing(8)
        al.addStretch(1)
        back = QPushButton("恢复")
        back.setCursor(Qt.PointingHandCursor)
        back.setFixedHeight(30)
        back.setStyleSheet(
            f"QPushButton{{background:{W.T['brand_soft']};border:none;border-radius:9px;"
            f"padding:0 14px;font-size:13px;font-weight:700;color:{W.T['brand']};}}"
            f"QPushButton:hover{{background:{W.T['brand']};color:#FFFFFF;}}")
        back.clicked.connect(lambda _, tid=e["id"]: self._restore(tid))
        al.addWidget(back)
        gone = QPushButton("彻底删除")
        gone.setCursor(Qt.PointingHandCursor)
        gone.setFixedHeight(30)
        gone.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;padding:0 8px;"
            f"font-size:13px;font-weight:600;color:{W.T['ink3']};}}"
            f"QPushButton:hover{{color:{W.T['red']};}}")
        gone.clicked.connect(lambda _, tid=e["id"], ti=e.get("title"): self._purge(tid, ti))
        al.addWidget(gone)
        card.body.addWidget(acts)
        return card

    # ---------------- 动作 ----------------
    def _restore(self, tid: str):
        good, msg = self.store.trash_restore(tid)
        self.app.toast(msg)
        if good:
            self.build()

    def _purge(self, tid: str, title: str):
        ok = QMessageBox.question(self, "彻底删除", f"「{title}」将无法恢复，确定删除？")
        if ok != QMessageBox.Yes:
            return
        if self.store.trash_purge(tid):
            self.app.toast("已彻底删除")
            self.build()

    def _clear(self):
        n = self.store.trash_count()
        if not n:
            return
        ok = QMessageBox.question(self, "清空回收站", f"回收站里 {n} 项都会永久删除，继续？")
        if ok != QMessageBox.Yes:
            return
        self.store.trash_clear()
        self.app.toast("回收站已清空")
        self.build()
