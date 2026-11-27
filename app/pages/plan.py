# -*- coding: utf-8 -*-
"""pages/plan.py - 征途：页头 + 两个分段（总览 / 记录）。

真正的面板在 pages/journey_panels.py；这里只做装配与动作转发，
任务计时（只认学习页）的状态机在 core.Store.quest_* 里。
"""
from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import widgets as W
from pages.base import Page
from pages.journey_widgets import ToggleSwitch, fmt_mmss

from pages.journey_panels import (OverviewPanel, PartyPanel, RecordsPanel,
                                  RewardsPanel)

TABS = (("overview", "总览"), ("tasks", "数据"))
PANELS = {"overview": OverviewPanel, "tasks": RecordsPanel}


class PlanPage(Page):
    """征途页：一个页头 + 一条分段 + 一个面板。"""

    def build(self):
        super().build()
        self.tab = self.store.settings.get("journey_tab") or "overview"
        if self.tab not in PANELS:
            self.tab = "overview"
        self._mins = int(self.store.quest.get("mins") or 15)
        if self._mins not in self.store.QUEST_TARGETS:
            self._mins = 15
        # 任务开关默认打开：第一次进征途就领任务（进学习页开始计时）
        if self.store.quest.get("status", "idle") == "idle":
            self.store.quest_claim(self._mins)

        g = self.store.game
        total = len(self.store.checkins)
        today_n = sum(1 for c in self.store.checkins
                      if time.localtime((c.get("at") or 0) / 1000)[:3]
                      == time.localtime()[:3])
        self.hero("征途", f"今日 {today_n} 次 · 累计 {total} 次 · Lv.{g.get('lv', 1)}",
                  right=self._band_quest())

        self._build_seg()
        self.host = QWidget()
        self.host_lay = QVBoxLayout(self.host)
        self.host_lay.setContentsMargins(0, 0, 0, 0)
        self.host_lay.setSpacing(0)
        self.body.addWidget(self.host)
        self._mount()

        # 跨天结算：不在 build 里直接 exec（会重入），推到事件循环下一拍
        QTimer.singleShot(0, self.app.maybe_settle)

    def _band_quest(self):
        """色带右上角：奶油胶囊里放「专注」+ 任务开关；重置放回今日任务卡。"""
        self.q_switch = ToggleSwitch(self.store.quest.get("status") == "active")
        self.q_switch.setToolTip("打开后进学习页才计时；离开学习页自动暂停")
        self.q_switch.toggled.connect(self.toggle_quest)
        wrap = QFrame()
        wrap.setObjectName("bandQuest")
        wrap.setStyleSheet(
            "QFrame#bandQuest{background:#FFF3D6;border:none;border-radius:16px;}")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(10, 3, 5, 3)
        lay.setSpacing(6)
        lab = QLabel("专注")
        lab.setStyleSheet(f"color:{W.T['ink']};font-size:10.5px;font-weight:700;")
        lay.addWidget(lab, 0, Qt.AlignVCenter)
        lay.addWidget(self.q_switch, 0, Qt.AlignVCenter)
        return wrap

    # ---------------- 分段 ----------------
    def _build_seg(self):
        wrap = QFrame()
        wrap.setStyleSheet(f"QFrame{{background:{W.T['paper2']};border:none;border-radius:14px;}}")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(0)
        self.tab_btns = {}
        for key, name in TABS:
            b = QPushButton(name)
            b.setCheckable(True)
            b.setFixedHeight(36)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, k=key: self.set_tab(k))
            lay.addWidget(b, 1)
            self.tab_btns[key] = b
        self.body.addWidget(wrap)
        self._paint_seg()

    def _paint_seg(self):
        for key, b in self.tab_btns.items():
            on = (key == self.tab)
            b.setStyleSheet(
                (f"QPushButton{{background:{W.T['panel']};color:{W.T['ink']};"
                 f"border:none;border-radius:11px;font-size:12px;font-weight:700;}}")
                if on else
                (f"QPushButton{{background:transparent;color:{W.T['ink2']};"
                 f"border:none;border-radius:11px;font-size:12px;font-weight:700;}}"))

    def set_tab(self, key: str):
        if key == self.tab:
            return
        self.tab = key
        self.store.settings["journey_tab"] = key
        self.store.save()
        self._paint_seg()
        self._mount()

    # ---------------- 面板 ----------------
    def _mount(self):
        W.clear_layout(self.host_lay)
        self.panel = PANELS[self.tab](self)
        self.host_lay.addWidget(self.panel)
        if hasattr(self.panel, "build"):
            self.panel.build()

    def refresh_quest(self, full: bool = False):
        panel = getattr(self, "panel", None)
        fn = getattr(panel, "refresh_quest", None)
        if fn:
            fn(full)

    # ---------------- 任务卡动作 ----------------
    def primary_qss(self) -> str:
        return (f"QPushButton{{background:{W.T['brand2']};color:#FFFFFF;border:none;"
                f"border-radius:14px;font-size:13px;font-weight:700;}}"
                f"QPushButton:hover{{background:{W.T['brand']};}}")

    def pick_mins(self, mins: int):
        # 已完成 / 暂停中改时长 = 开始一个新任务
        if (self.store.quest.get("status") == "done"
                or self.store.quest_has_progress()):
            self.store.quest_reset()
        self._mins = int(mins)
        panel = getattr(self, "panel", None)
        if hasattr(panel, "pick"):
            panel.pick(self._mins)
        else:
            self.build()

    def reset_quest(self):
        """今日任务：把这次计时清零（时长保留），开关状态不变。"""
        if not self.store.quest_has_progress():
            self.app.toast("任务没在计时")
            return
        self.store.quest_restart()
        self.app.toast(f"计时已清零 · 回到 {fmt_mmss(self.store.quest_left_ms())}")
        self.build()

    def toggle_quest(self, on: bool):
        """任务开关：开 = 开始/继续；关 = 暂停（已用时间保留）。只有「重置」才清零。"""
        status = self.store.quest.get("status", "idle")
        if on:
            if status != "active":
                if status == "done":
                    self.store.quest_reset()
                    self.store.quest_claim(self._mins)
                    self.app.toast(f"任务已开启 · {self._mins} 分钟 · 进学习页开始计时")
                elif self.store.quest_resume():
                    self.app.toast(
                        f"已继续 · 还剩 {fmt_mmss(self.store.quest_left_ms())}")
                else:
                    self.store.quest_claim(self._mins)
                    self.app.toast(f"任务已开启 · {self._mins} 分钟 · 进学习页开始计时")
            self.build()
        else:
            if status == "active":
                self.store.quest_pause()
                self.app.toast("已暂停 · 已用时间保留")
            self.build()

    def go_study(self):
        if self.app.session:
            self.app.show_page("review")
        else:
            self.app.start_review()

    # ---------------- 奖励动作 ----------------
    def redeem(self, rid: str):
        res = self.store.redeem_reward(rid)
        if res.get("ok"):
            self.app.toast(f"已兑换「{res['title']}」· -{res['price']} 金币")
        else:
            self.app.toast(f"金币不够，还差 {res.get('need', 0)}")
        self.build()

    def add_reward(self):
        from pages.journey_dialogs import AddRewardDialog
        dlg = AddRewardDialog(self)
        if dlg.exec() and dlg.result_title:
            self.store.add_reward(dlg.result_title, dlg.result_price)
            self.app.toast("奖励已添加")
            self.build()
