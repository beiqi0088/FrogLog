# -*- coding: utf-8 -*-
"""pages/journey_panels.py - 征途的分段面板：总览（青蛙首领+勋章）/ 记录。

每个面板自己 build()，PlanPage 只负责页头 + 分段 + 挂载。
"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

import widgets as W

from core import day_str, prev_day_str
from pages.insights import activity_row
from pages.journey_widgets import (BADGES, CheckBtn, FROG_MEDAL_COLORS,
                                   FROG_MEDALS, MedalDot, Monster, ThinBar,
                                   ToggleSwitch, WeekBars, fmt_mmss,
                                   frog_medal)

# ---------------------------------------------------------------- 怪物吃青蛙
# 吃掉一只青蛙 = 累计学习 45 分钟；等级按累计吃掉数量解锁。
MONSTERS = [
    ("青泡泡", 0, "#6FAE7A"),
    ("蓝泡泡", 3, "#5B8FD4"),
    ("紫泡泡", 8, "#8A6BC0"),
    ("赤泡泡", 15, "#C4562E"),
    ("金泡泡", 25, "#C9A227"),
    ("蛙群之王", 40, "#B23A5B"),
    ("粉泡泡", 60, "#E27A9A"),
    ("雪泡泡", 85, "#7FB6C9"),
    ("墨泡泡", 115, "#5A6472"),
    ("虹泡泡", 150, "#C77FA8"),
    ("星泡泡", 190, "#6C8FD6"),
    ("泡泡之神", 240, "#8A6BC0"),
]


def monster_level(total: int):
    idx = 0
    for k, (_name, need, _color) in enumerate(MONSTERS):
        if total >= need:
            idx = k
    cur = MONSTERS[idx]
    nxt = MONSTERS[idx + 1] if idx + 1 < len(MONSTERS) else None
    return idx, cur, nxt


TITLES = ((20, "星辉旅人"), (10, "远征者"), (5, "行路人"), (1, "见习旅人"))
DIFF_NAME = {"easy": "简单", "medium": "中等", "hard": "困难"}


def title_for(lv: int) -> str:
    for need, name in TITLES:
        if lv >= need:
            return name
    return "见习旅人"


def small(text: str, size: float = 10.5, color: str | None = None, bold: bool = False):
    lb = QLabel(text)
    lb.setStyleSheet(
        f"font-size:{size}px;color:{color or W.T['ink3']};"
        f"font-weight:{700 if bold else 400};")
    return lb


def h3(text: str):
    lb = QLabel(text)
    lb.setStyleSheet(f"font-size:13px;font-weight:700;color:{W.T['ink']};")
    return lb


class _ElideLabel(QLabel):
    """单行超出用 … 截断，并允许布局把它收缩到任意窄，避免被屏幕裁掉。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full = text or ""
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(1)
        self._apply()

    def setText(self, text: str):
        self._full = text or ""
        self._apply()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply()

    def _apply(self):
        fm = QFontMetrics(self.font())
        QLabel.setText(self, fm.elidedText(self._full, Qt.ElideRight, max(1, self.width())))


def hline_msg(text: str):
    lb = QLabel(text)
    lb.setWordWrap(True)
    lb.setStyleSheet(f"font-size:10.5px;color:{W.T['ink3']};")
    return lb


class Panel(QWidget):
    """面板基类：0 边距的竖排容器。"""

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.app = page.app
        self.store = page.store
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(12)
        self.body.setAlignment(Qt.AlignTop)

    def rebuild(self):
        W.clear_layout(self.body)
        self.build()

    def build(self):
        raise NotImplementedError

    def on_show(self):
        pass


# ============================================================ 总览
def _fmt_total(minutes: int) -> str:
    """把累计分钟数写成人话：90 → 1 小时 30 分。"""
    m = max(0, int(minutes))
    if m <= 0:
        return "0 分钟"
    h, mm = divmod(m, 60)
    if h and mm:
        return f"{h} 小时 {mm} 分"
    if h:
        return f"{h} 小时"
    return f"{mm} 分钟"


class OverviewPanel(Panel):
    def build(self):
        self._q_status = None
        self._quest()
        self._medals()

    # ---- 任务卡 ----
    def _quest(self):
        q = self.store.quest
        status = q.get("status", "idle")
        self._q_status = status
        mins = int(q.get("mins") or 15)
        if mins not in self.store.QUEST_TARGETS and not self.store.quest_has_progress():
            mins = 15
        self._q_mins = mins

        card = W.Card()
        card.body.setContentsMargins(18, 15, 18, 15)
        card.body.setSpacing(9)

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(h3("今日任务"))
        hl.addStretch(1)
        self.q_reset = QPushButton("重置")
        self.q_reset.setFixedHeight(26)
        self.q_reset.setCursor(Qt.PointingHandCursor)
        self.q_reset.setToolTip("把这次任务清零：计时和这次学的时间都不算，回 15:00")
        self.q_reset.setStyleSheet(
            f"QPushButton{{background:{W.T['paper2']};border:none;color:{W.T['ink']};"
            f"border-radius:12px;font-size:10.5px;font-weight:700;padding:0 10px;}}"
            f"QPushButton:disabled{{color:{W.T['ink3']};}}")
        self.q_reset.clicked.connect(self.page.reset_quest)
        hl.addWidget(self.q_reset, 0, Qt.AlignVCenter)
        card.body.addWidget(head)

        self.q_time = QLabel("")
        self.q_time.setAlignment(Qt.AlignCenter)
        card.body.addWidget(self.q_time)

        self.q_hint = QLabel("")
        self.q_hint.setAlignment(Qt.AlignCenter)
        self.q_hint.setWordWrap(True)
        self.q_hint.setStyleSheet(f"font-size:10.5px;color:{W.T['ink3']};")
        card.body.addWidget(self.q_hint)

        # 今日吃掉青蛙数量：放进今日任务卡，不再单独用「吃掉那只青蛙」卡
        lt = time.localtime()
        today_key = (lt.tm_year, lt.tm_yday)
        today_frogs = 0
        for c in self.store.checkins:
            ct = time.localtime((c.get("at") or 0) / 1000)
            if (ct.tm_year, ct.tm_yday) == today_key:
                today_frogs += int(c.get("frogs") or 1)
        frog_row = QWidget()
        fr = QHBoxLayout(frog_row)
        fr.setContentsMargins(0, 2, 0, 0)
        fr.setSpacing(10)
        fr.addWidget(W.FrogMascot(34, "green"), 0, Qt.AlignVCenter)
        cap = QLabel("今日已吃")
        cap.setStyleSheet(f"font-size:11px;color:{W.T['ink3']};")
        fr.addWidget(cap)
        num = QLabel(f"{today_frogs}<span style='font-size:12px;color:{W.T['ink3']};'> 只</span>")
        num.setTextFormat(Qt.RichText)
        num.setStyleSheet(f"font-size:24px;font-weight:700;color:{W.T['brand']};")
        fr.addWidget(num, 1)
        card.body.addWidget(frog_row)

        self.body.addWidget(card)
        self.paint_quest()

    def paint_quest(self):
        q = self.store.quest
        status = q.get("status", "idle")
        mins = int(getattr(self, "_q_mins", 25))
        reward = q.get("reward") or {}

        # 开关跟数据走（色带右上角）；blockSignals 避免 setChecked 反过来再触发一次 toggle
        switch = getattr(self.page, "q_switch", None)
        if switch is not None:
            switch.blockSignals(True)
            switch.setChecked(status == "active")
            switch.blockSignals(False)

        if status == "active":
            self.q_time.setText(fmt_mmss(self.store.quest_left_ms()))
            self.q_time.setStyleSheet(
                f"font-size:42px;font-weight:700;color:{W.T['brand']};letter-spacing:1px;")
            running = self.store.quest_running()
            started = running or int(q.get("acc_ms") or 0) > 0
            if running:
                self.q_hint.setText(f"计时中 · 共 {mins} 分钟，离开学习页会自动暂停")
            elif started:
                self.q_hint.setText("已暂停 · 回到学习页继续计时")
            else:
                self.q_hint.setText("已开启 · 进学习页开始计时")
        elif status == "done":
            self.q_time.setText("00:00")
            self.q_time.setStyleSheet(
                f"font-size:42px;font-weight:700;color:{W.T['green']};letter-spacing:1px;")
            self.q_hint.setText(
                f"已完成 · 经验 +{reward.get('xp', 0)} · 金币 +{reward.get('gold', 0)}")
        elif self.store.quest_has_progress():
            # 暂停中：显示剩余时间，已用进度保留
            self.q_time.setText(fmt_mmss(self.store.quest_left_ms()))
            self.q_time.setStyleSheet(
                f"font-size:42px;font-weight:700;color:{W.T['ink']};letter-spacing:1px;")
            used = fmt_mmss(self.store.quest_elapsed())
            self.q_hint.setText(f"已暂停 · 已用 {used} / {mins} 分钟 · 进度保留")
        else:
            self.q_time.setText(f"{mins:02d}:00")
            self.q_time.setStyleSheet(
                f"font-size:42px;font-weight:700;color:{W.T['ink']};letter-spacing:1px;")
            self.q_hint.setText("打开开关后，进学习页才开始计时")

        if hasattr(self, "q_reset"):
            self.q_reset.setEnabled(self.store.quest_has_progress()
                                    and self.store.quest_elapsed() > 0)

    # ---- 首领 ----
    def _boss(self):
        # 只显示今日吃掉青蛙的数量
        lt = time.localtime()
        today_key = (lt.tm_year, lt.tm_yday)
        today_frogs = 0
        for c in self.store.checkins:
            ct = time.localtime((c.get("at") or 0) / 1000)
            if (ct.tm_year, ct.tm_yday) == today_key:
                today_frogs += int(c.get("frogs") or 1)

        card = W.Card()
        card.body.setContentsMargins(14, 12, 14, 12)
        card.body.setSpacing(8)

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(h3("吃掉那只青蛙"))
        hl.addStretch(1)
        card.body.addWidget(head)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)
        rl.addWidget(W.FrogMascot(44, "green"), 0, Qt.AlignVCenter)

        num_box = QWidget()
        nl = QVBoxLayout(num_box)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(0)
        cap = QLabel("今日已吃")
        cap.setStyleSheet(f"font-size:11px;color:{W.T['ink3']};")
        num = QLabel(f"{today_frogs}<span style='font-size:13px;color:{W.T['ink3']};'> 只</span>")
        num.setTextFormat(Qt.RichText)
        num.setStyleSheet(f"font-size:30px;font-weight:700;color:{W.T['brand']};")
        nl.addWidget(cap)
        nl.addWidget(num)
        rl.addWidget(num_box, 1)
        card.body.addWidget(row)

        self.body.addWidget(card)

    # ---- 青蛙勋章 ----
    def _medals(self):
        total = self.store.frogs_eaten()
        idx, cur, nxt = monster_level(total)

        card = W.Card()
        card.body.setContentsMargins(16, 13, 16, 15)
        card.body.setSpacing(8)

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        name = QLabel(cur[0])
        name.setStyleSheet(f"font-size:18px;font-weight:700;color:{W.T['ink']};")
        hl.addWidget(name)
        lv = QLabel(f"Lv.{idx + 1}")
        lv.setStyleSheet(f"background:{cur[2]};color:#FFFDF8;border-radius:9px;"
                         "font-size:10px;font-weight:700;padding:2px 8px;")
        hl.addWidget(lv)
        hl.addStretch(1)
        link = QPushButton("等级 ›")
        link.setCursor(Qt.PointingHandCursor)
        link.setToolTip("打开怪物图鉴：6 只怪物、吃青蛙数与学习时长")
        link.setStyleSheet(
            f"QPushButton{{background:{W.T['brand_soft']};border:none;color:{W.T['deep']};"
            f"border-radius:11px;font-size:11px;font-weight:700;padding:3px 10px;}}")
        link.clicked.connect(lambda: self.app.show_page("monsters"))
        hl.addWidget(link, 0, Qt.AlignVCenter)
        card.body.addWidget(head)

        mon = W.Monster(118, cur[2])
        card.body.addWidget(mon, 0, Qt.AlignHCenter)

        if nxt:
            span = max(1, nxt[1] - cur[1])
            pct = max(0.0, min(100.0, 100.0 * (total - cur[1]) / span))
            card.body.addWidget(ThinBar(pct, W.T["red"], W.T["paper2"], 8))
            hint = QLabel(f"已吃 {total} / {nxt[1]} 只 · 再吃 {nxt[1] - total} 只升级为「{nxt[0]}」")
        else:
            card.body.addWidget(ThinBar(100, W.T["red"], W.T["paper2"], 8))
            hint = QLabel("已吃到最高级「蛙群之王」")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"font-size:10.5px;color:{W.T['ink2']};")
        card.body.addWidget(hint)

        stats = QHBoxLayout()
        stats.setSpacing(0)
        for k, v in (("已吃青蛙", f"{total} 只"),
                     ("累计学习", f"{total * 45} 分钟"),
                     ("下一级", f"{nxt[1] - total if nxt else 0} 只")):
            box = QWidget()
            bx = QVBoxLayout(box)
            bx.setContentsMargins(0, 0, 0, 0)
            bx.setSpacing(0)
            vv = QLabel(v)
            vv.setStyleSheet(f"font-size:16px;font-weight:700;color:{W.T['ink']};")
            bx.addWidget(vv)
            kk = QLabel(k)
            kk.setStyleSheet(f"font-size:9.5px;color:{W.T['ink3']};")
            bx.addWidget(kk)
            stats.addWidget(box, 1)
        card.body.addLayout(stats)
        self.body.addWidget(card)

    def pick(self, mins: int):
        self._q_mins = int(mins)
        self.paint_quest()

    def refresh(self):
        status = self.store.quest.get("status", "idle")
        if status != self._q_status:
            self.rebuild()
            return
        self.paint_quest()

    def refresh_quest(self, full: bool = False):
        if full:
            self.rebuild()
            return
        self.refresh()


# ============================================================ 任务
class RecordsPanel(Panel):
    """记录页 = 最近 7 天柱状图（吃蛙时间线在「吃掉那只青蛙」里）。"""

    def build(self):
        self.body.addWidget(self._week_card())
        self.body.addWidget(activity_row(self.store, self.store.live_reviews()))
        self.body.addStretch(1)

    # ---- 最近 7 天 ----
    def _week_card(self):
        per_day = self.store.study_by_day()
        by_day: dict = {}
        for k, mins in per_day.items():
            t = time.strptime(k, "%Y-%m-%d")
            by_day[(t.tm_year, t.tm_mon, t.tm_mday)] = by_day.get(
                (t.tm_year, t.tm_mon, t.tm_mday), 0) + mins
        t = time.localtime()
        names = "一二三四五六日"
        days = []
        for i in range(6, -1, -1):
            d = time.localtime(time.mktime((t.tm_year, t.tm_mon, t.tm_mday - i,
                                            0, 0, 0, 0, 0, -1)))
            days.append(("今天" if i == 0 else names[d.tm_wday], by_day.get(d[:3], 0)))

        card = W.Card()
        card.body.setContentsMargins(16, 12, 16, 12)
        card.body.setSpacing(7)
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(h3("最近 7 天"))
        hl.addStretch(1)
        week_total = sum(m for _l, m in days)
        hl.addWidget(small(f"本周 {_fmt_total(week_total)}", 10.5))
        card.body.addWidget(head)

        self.week_bars = WeekBars(days)
        card.body.addWidget(self.week_bars)
        return card



class FrogTimelinePanel(Panel):
    """吃蛙时间线（按天分组、最新在上）。"""

    def __init__(self, page):
        super().__init__(page)
        self.show_header = True     # 独立页面已经有 appbar，就不再重复标题

    def build(self):
        evts = self.store.frog_events()
        total = self.store.frogs_eaten()

        if self.show_header:
            head = QWidget()
            hl = QHBoxLayout(head)
            hl.setContentsMargins(2, 0, 2, 0)
            hl.addWidget(h3("吃蛙记录"))
            hl.addStretch(1)
            hl.addWidget(small(f"共 {total} 只", 10.5))
            self.body.addWidget(head)

        if not evts:
            card = W.Card()
            card.body.setContentsMargins(18, 26, 18, 24)
            card.body.setSpacing(8)
            t = QLabel("还没有吃掉青蛙")
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet(f"font-size:14px;font-weight:700;color:{W.T['ink']};")
            card.body.addWidget(t)
            tip = QLabel("去总览领一个任务：每专注 15 分钟，就会吃掉一只")
            tip.setAlignment(Qt.AlignCenter)
            tip.setWordWrap(True)
            tip.setStyleSheet(f"font-size:11.5px;color:{W.T['ink3']};")
            card.body.addWidget(tip)
            self.body.addWidget(card)
            self.body.addStretch(1)
            return

        groups: list[tuple[str, list]] = []
        for ev in evts:
            date = day_str(ev["at"])
            if groups and groups[-1][0] == date:
                groups[-1][1].append(ev)
            else:
                groups.append((date, [ev]))
        for date, items in groups:
            self.body.addWidget(self._day_card(date, items))

        # 当前这只青蛙的进度
        left = self.store.frog_left_minutes()
        tip = QLabel(f"当前这只青蛙还差 {left} 分钟")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet(f"font-size:10.5px;color:{W.T['ink3']};")
        self.body.addWidget(tip)
        self.body.addStretch(1)

    @staticmethod
    def _date_label(date: str) -> str:
        if date == day_str():
            return "今天"
        if date == prev_day_str():
            return "昨天"
        try:
            t = time.strptime(date, "%Y-%m-%d")
            return f"{t.tm_mon:02d}-{t.tm_mday:02d} 周{'一二三四五六日'[t.tm_wday]}"
        except Exception:
            return date

    def _day_card(self, date: str, items: list) -> W.Card:
        card = W.Card()
        card.body.setContentsMargins(14, 11, 14, 6)
        card.body.setSpacing(0)

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(2, 0, 2, 2)
        hl.addWidget(h3(self._date_label(date)))
        hl.addStretch(1)
        hl.addWidget(small(f"{len(items)} 只", 10))
        card.body.addWidget(head)

        for ev in items:
            card.body.addWidget(self._row(ev))
        return card

    def _row(self, ev: dict) -> QWidget:
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 7, 0, 7)
        rl.setSpacing(9)

        when = QLabel(time.strftime("%H:%M", time.localtime((ev.get("at") or 0) / 1000)))
        when.setFixedWidth(38)
        when.setStyleSheet(f"font-size:10px;color:{W.T['ink3']};")
        when.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        rl.addWidget(when, 0, Qt.AlignTop)

        frog = QLabel("🐸")
        frog.setFixedWidth(20)
        frog.setStyleSheet("font-size:13px;")
        rl.addWidget(frog, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(2)
        title = QLabel(f"吃掉第 {int(ev.get('idx') or 0)} 只青蛙")
        title.setStyleSheet(f"font-size:12.5px;font-weight:700;color:{W.T['ink']};")
        title.setWordWrap(True)
        col.addWidget(title)

        bits = [f"专注 {int(ev.get('mins') or 0)} 分钟",
                f"累计 {_fmt_total(int(ev.get('total_min') or 0))}",
                "+40 金币", "+1 宝石"]
        sub = QLabel(" · ".join(bits))
        sub.setStyleSheet(f"font-size:10.5px;color:{W.T['ink3']};")
        sub.setWordWrap(True)
        col.addWidget(sub)
        rl.addLayout(col, 1)
        return row


class PartyPanel(Panel):
    def build(self):
        g = self.store.game
        b = g["boss"]
        card = W.Card()
        card.body.setContentsMargins(16, 15, 16, 14)
        card.body.setSpacing(6)
        card.body.setAlignment(Qt.AlignHCenter)

        mon = Monster()
        mon.set_scale(1.0)
        mon.set_palette("#8E76B8", "#5E4A7A")
        mon.set_state(int(b.get("lv") or 1), False)
        card.body.addWidget(mon, 0, Qt.AlignHCenter)

        name = QLabel("吃掉那只青蛙")
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"font-size:16px;font-weight:700;color:{W.T['ink']};")
        card.body.addWidget(name)
        card.body.addWidget(small(f"Lv.{b.get('lv', 1)} · 已损失 "
                                 f"{100 - int(int(b.get('hp') or 0) / max(1, int(b.get('hp_max') or 100)) * 100)}% 生命", 10.5))

        bar = ThinBar(int(b.get("hp") or 0) / max(1, int(b.get("hp_max") or 100)) * 100,
                      W.T["red"], W.T["paper2"], 10)
        card.body.addWidget(bar)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(small(f"{b.get('hp', 0)} / {b.get('hp_max', 100)}", 10.5))
        rl.addStretch(1)
        rl.addWidget(small(f"全队还需 {max(1, -(-int(b.get('hp') or 0) // 34))} 次", 10.5))
        card.body.addWidget(row)
        self.body.addWidget(card)

        # 队伍（本地单人）
        team = W.Card()
        team.body.setContentsMargins(16, 12, 16, 12)
        team.body.setSpacing(8)
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(h3("队伍"))
        hl.addStretch(1)
        hl.addWidget(small("伤害贡献", 10))
        team.body.addWidget(head)

        me = QWidget()
        ml = QHBoxLayout(me)
        ml.setContentsMargins(0, 2, 0, 2)
        ml.setSpacing(9)
        av = QLabel("你")
        av.setAlignment(Qt.AlignCenter)
        av.setFixedSize(30, 30)
        av.setStyleSheet(
            f"background:{W.T['brand']};color:#FFFFFF;border-radius:10px;"
            f"font-size:12px;font-weight:700;")
        ml.addWidget(av)
        col = QVBoxLayout()
        col.setSpacing(4)
        trow = QWidget()
        tl = QHBoxLayout(trow)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(small("你", 12.5, W.T["ink"], True))
        tl.addStretch(1)
        tl.addWidget(small("100%", 10.5))
        col.addWidget(trow)
        col.addWidget(ThinBar(100, W.T["brand"], W.T["paper2"], 6))
        ml.addLayout(col, 1)
        team.body.addWidget(me)
        team.body.addWidget(hline_msg(
            "多人队伍需要后端（或局域网同步）；现在按本地单人副本结算——每次完成征途造成 34 点伤害。"))
        self.body.addWidget(team)

        # 通关奖励
        rw = W.Card()
        rw.body.setContentsMargins(16, 12, 16, 12)
        rw.body.setSpacing(8)
        rhead = QWidget()
        rhl = QHBoxLayout(rhead)
        rhl.setContentsMargins(0, 0, 0, 0)
        rhl.addWidget(h3("通关奖励"))
        rhl.addStretch(1)
        rhl.addWidget(small("击败后自动开下一只", 10))
        rw.body.addWidget(rhead)
        pills = QWidget()
        pl = QHBoxLayout(pills)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        for text, kind in (("40 金币", "accent"), ("1 宝石", "brand"), ("限定徽章", "red")):
            pl.addWidget(W.Pill(text, kind))
        pl.addStretch(1)
        rw.body.addWidget(pills)
        self.body.addWidget(rw)

        btn = W.PrimaryButton("投入专注 · 去学习页计时")
        btn.clicked.connect(self.page.go_study)
        self.body.addWidget(btn)


# ============================================================ 奖励
class RewardsPanel(Panel):
    def build(self):
        g = self.store.game
        card = W.HeroCard()
        card.body.setContentsMargins(18, 14, 18, 14)
        card.body.setSpacing(2)
        hi = W.T.get("hero_ink") or W.T["brand_soft"]
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(small("可用金币", 10, hi, True))
        big = QLabel(f"{int(g.get('gold') or 0)} GP")
        big.setStyleSheet(f"font-size:28px;font-weight:700;color:{hi};")
        col.addWidget(big)
        rl.addLayout(col, 1)
        right = QVBoxLayout()
        right.setSpacing(1)
        cap = small("连击", 10, hi, True)
        cap.setAlignment(Qt.AlignRight)
        val = QLabel(f"{int(g.get('streak') or 0)} 天")
        val.setStyleSheet(f"font-size:15px;font-weight:700;color:{hi};")
        val.setAlignment(Qt.AlignRight)
        right.addWidget(cap)
        right.addWidget(val)
        rl.addLayout(right, 0)
        card.body.addWidget(row)
        self.body.addWidget(card)

        # 奖励列表
        shop = W.Card()
        shop.body.setContentsMargins(16, 13, 16, 12)
        shop.body.setSpacing(4)
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(h3("我的奖励"))
        hl.addStretch(1)
        hl.addWidget(small("点兑换即扣金币", 10))
        shop.body.addWidget(head)

        for r in g.get("rewards") or []:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 7, 0, 7)
            rl.setSpacing(8)
            rl.addWidget(W.Pill(str(r.get("tag") or "自定义"), "plain"))
            t = QLabel(str(r.get("title") or ""))
            t.setStyleSheet(f"font-size:13px;font-weight:700;color:{W.T['ink']};")
            rl.addWidget(t, 1)
            price = QLabel(f"◉ {int(r.get('price') or 0)}")
            price.setStyleSheet(
                f"font-size:12px;font-weight:700;color:{W.T['accent']};")
            rl.addWidget(price)
            buy = QPushButton("兑换")
            buy.setFixedHeight(28)
            buy.setCursor(Qt.PointingHandCursor)
            buy.setStyleSheet(
                f"QPushButton{{background:{W.T['brand_soft']};color:{W.T['brand']};"
                f"border:none;border-radius:9px;padding:0 10px;font-size:11px;"
                f"font-weight:700;}}")
            buy.clicked.connect(lambda _, rid=r["id"]: self.page.redeem(rid))
            rl.addWidget(buy)
            shop.body.addWidget(row)
        self.body.addWidget(shop)

        add = W.GhostButton("＋ 添加自定义奖励（花多少金币，你定）")
        add.setMinimumHeight(42)
        add.clicked.connect(self.page.add_reward)
        self.body.addWidget(add)

        # 徽章
        bcard = W.Card()
        bcard.body.setContentsMargins(16, 13, 16, 13)
        bcard.body.setSpacing(8)
        bh = QWidget()
        bl = QHBoxLayout(bh)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(h3("徽章"))
        bl.addStretch(1)
        unlocked = set(g.get("badges") or [])
        bl.addWidget(small(f"已解锁 {len(unlocked)} / {len(BADGES)}", 10))
        bcard.body.addWidget(bh)

        grid = QWidget()
        gl = QHBoxLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(5)
        for key, name, need, emoji in BADGES:
            on = key in unlocked
            cell = QVBoxLayout()
            cell.setSpacing(3)
            icon = QLabel(emoji)
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedHeight(36)
            icon.setStyleSheet(
                (f"background:{W.T['accent_soft']};border-radius:11px;font-size:16px;")
                if on else
                (f"background:{W.T['paper2']};border-radius:11px;font-size:16px;"
                 f"color:{W.T['ink3']};"))
            if not on:
                eff = QGraphicsOpacityEffect(icon)
                eff.setOpacity(0.32)
                icon.setGraphicsEffect(eff)
            cell.addWidget(icon)
            lb = QLabel(name)
            lb.setAlignment(Qt.AlignCenter)
            lb.setStyleSheet(f"font-size:9px;color:{W.T['ink3']};")
            cell.addWidget(lb)
            gl.addLayout(cell, 1)
        bcard.body.addWidget(grid)
        self.body.addWidget(bcard)

        # 金币来源
        src = W.Card()
        src.body.setContentsMargins(16, 12, 16, 12)
        src.body.setSpacing(6)
        sh = QWidget()
        sl = QHBoxLayout(sh)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(h3("金币怎么来"))
        sl.addStretch(1)
        sl.addWidget(small("做正事才有", 10))
        src.body.addWidget(sh)
        for label, val in (("专注 30 分钟", "+10"), ("完成一项每日", "+4"), ("清掉一件待办", "+5")):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 3, 0, 3)
            rl.addWidget(small(label, 12, W.T["ink2"]))
            rl.addStretch(1)
            rl.addWidget(small(val, 12, W.T["accent"], True))
            src.body.addWidget(row)
        self.body.addWidget(src)
