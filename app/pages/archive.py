# -*- coding: utf-8 -*-
"""pages/archive.py - 完成页（只作用于卡包，不参与学习与复习）。"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel, QHBoxLayout, QWidget,
                               QPushButton, QMessageBox, QFrame)

import widgets as W
from pages.base import Page, label
from pages.library import OneLineLabel


def _date_text(ms) -> str:
    if not ms:
        return "—"
    return time.strftime("%Y-%m-%d", time.localtime(int(ms) / 1000))


class ArchivePage(Page):
    def __init__(self, app, domain_id: str | None = None):
        self.domain_id = domain_id
        super().__init__(app)

    def build(self):
        super().build()
        s = self.store
        decks = s.archived_decks()
        if self.domain_id:
            decks = [d for d in decks if d.get("domain") == self.domain_id]
        dom = s.domain(self.domain_id) if self.domain_id else None

        # 大标题 = 知识域；「归档」弱化成眉标
        if dom:
            self.appbar(dom.get("name", "完成"), "完成", back=self.app.go_back)
        else:
            self.appbar("完成", None, back=self.app.go_back)
        self.add(label(f"{len(decks)} 个卡包 · 已学完，不再参与学习与复习", "sub"))

        if not decks:
            self.add(self._empty())
            self.stretch()
            return

        for d in decks:
            self.add(self._card(d, show_domain=not dom))
        self.stretch()

    # ---------- 卡片 ----------
    def _card(self, d: dict, show_domain: bool = True) -> QWidget:
        s = self.store
        box = W.Card()
        box.body.setContentsMargins(15, 12, 15, 12)
        box.body.setSpacing(6)

        # 知识域：醒目的品牌色标签（单域页面不需要，标题已经写明）
        if show_domain:
            dom = s.domain(d.get("domain")) or {}
            dtag = QLabel(dom.get("name", "未分组"))
            dtag.setStyleSheet(
                f"font-size:12.5px;font-weight:700;color:{W.T['brand']};"
                f"background:{W.T['brand_soft']};border-radius:8px;padding:3px 9px;")
            top = QWidget()
            tl = QHBoxLayout(top)
            tl.setContentsMargins(0, 0, 0, 0)
            tl.setSpacing(0)
            tl.addWidget(dtag)
            tl.addStretch(1)
            box.body.addWidget(top)

        t = OneLineLabel(d["name"])
        t.setStyleSheet(f"font-size:16.5px;font-weight:700;color:{W.T['ink']};")
        box.body.addWidget(t)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{W.T['line']};border:none;")
        box.body.addWidget(sep)

        meta = QLabel(f"{len(s.cards_of(d['id']))} 张卡片 · 完成于 "
                      f"{_date_text(d.get('archived_at'))}")
        meta.setStyleSheet(f"font-size:12.5px;color:{W.T['ink2']};")
        box.body.addWidget(meta)

        acts = QWidget()
        al = QHBoxLayout(acts)
        al.setContentsMargins(0, 4, 0, 0)
        al.setSpacing(8)

        back = QPushButton("取消完成")
        back.setFixedHeight(34)
        back.setCursor(Qt.PointingHandCursor)
        back.setStyleSheet(
            f"QPushButton{{background:{W.T['brand']};color:#FFFFFF;border:none;"
            f"border-radius:11px;font-size:13.5px;font-weight:600;}}")
        back.clicked.connect(lambda: self._unarchive(d))
        al.addWidget(back, 1)

        dele = QPushButton("删除")
        dele.setFixedHeight(34)
        dele.setCursor(Qt.PointingHandCursor)
        dele.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};color:{W.T['red']};border:none;"
            f"border-radius:11px;font-size:13.5px;font-weight:600;}}")
        dele.clicked.connect(lambda: self._delete(d))
        al.addWidget(dele, 1)
        box.body.addWidget(acts)
        return box

    def _empty(self) -> QWidget:
        box = W.Card(flat=True)
        box.body.setContentsMargins(18, 30, 18, 30)
        t = QLabel("还没有完成的卡包")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:14px;font-weight:600;")
        s2 = QLabel("在「记忆」里对卡包点 ⋯ → 完成")
        s2.setObjectName("sub")
        s2.setAlignment(Qt.AlignCenter)
        box.body.addWidget(t)
        box.body.addWidget(s2)
        return box

    # ---------- 操作 ----------
    def _unarchive(self, d: dict):
        if QMessageBox.question(
                self, "取消完成",
                f"恢复「{d['name']}」的学习？\n会放回知识域根目录，复习进度保留。"
        ) != QMessageBox.Yes:
            return
        self.store.archive_deck(d["id"], False)
        self.app.toast(f"「{d['name']}」已恢复学习")
        self.build()

    def _delete(self, d: dict):
        n = len(self.store.cards_of(d["id"]))
        if QMessageBox.question(
                self, "删除卡包",
                f"永久删除「{d['name']}」及 {n} 张卡片？\n无法恢复。"
        ) != QMessageBox.Yes:
            return
        self.store.delete_deck(d["id"])
        self.app.toast("已删除")
        self.build()
