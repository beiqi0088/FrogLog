# -*- coding: utf-8 -*-
"""pages/insights.py - 细数：六维雷达 + 题型统计。"""
from __future__ import annotations

import time
from collections import Counter

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, QWidget,
                               QMenu, QPushButton)

import widgets as W
import theme
from core import retention
from pages.base import Page, label


def _heat_days(store, reviews, days: int = 31):
    counts = Counter()
    for r in (reviews if reviews is not None else store.live_reviews()):
        counts[time.strftime("%Y-%m-%d", time.localtime(r["at"] / 1000))] += 1
    out = []
    for i in range(days - 1, -1, -1):
        key = time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400))
        out.append(counts.get(key, 0))
    return out


def _accuracy_pct(reviews) -> int:
    if not reviews:
        return 0
    return round(sum(1 for r in reviews if r["rating"] >= 2) / len(reviews) * 100)


def _streak_days(reviews) -> int:
    days = {time.strftime("%Y-%m-%d", time.localtime(r["at"] / 1000)) for r in reviews}
    n, cur = 0, time.time()
    while time.strftime("%Y-%m-%d", time.localtime(cur)) in days:
        n += 1
        cur -= 86400
    return n


def activity_row(store, reviews) -> QWidget:
    """31 天活跃热力图 + 准确率（征途数据页用）。"""
    row = QWidget()
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 0, 0, 0)
    rl.setSpacing(10)

    left = W.Card()
    left.body.setContentsMargins(6, 10, 6, 10)
    left.body.setSpacing(4)
    lh = QWidget()
    lhl = QHBoxLayout(lh)
    lhl.setContentsMargins(0, 0, 0, 0)
    lhl.addWidget(label("31 天活跃", "h3"), 1)
    lhl.addWidget(label("连续 %d 天" % _streak_days(reviews), "sub"))
    left.body.addWidget(lh)
    left.body.addWidget(W.Heat(_heat_days(store, reviews, 31), cols=8), 1)
    rl.addWidget(left, 7)

    right = W.Card()
    right.body.setContentsMargins(14, 10, 14, 10)
    right.body.addWidget(label("准确率", "h3"))
    acc = _accuracy_pct(reviews)
    wrap = QWidget()
    wl = QHBoxLayout(wrap)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.addStretch(1)
    wl.addWidget(W.Ring(acc, 96, 9))
    wl.addStretch(1)
    right.body.addWidget(wrap)
    cap = label(f"近 31 天共 {len(reviews)} 次复习", "sub")
    cap.setAlignment(Qt.AlignHCenter)
    right.body.addWidget(cap)
    rl.addWidget(right, 5)
    return row


class ArchiveIcon(QWidget):
    """完成卡前面的小箱子图标。"""

    def __init__(self, size: int = 18, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        from PySide6.QtCore import QRectF, QPointF
        from PySide6.QtGui import QColor, QPainter, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(W.T["ink2"]), 1.5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        w, h = self.width(), self.height()
        p.drawRoundedRect(QRectF(2, 6.5, w - 4, h - 8), 2, 2)
        p.drawLine(QPointF(1.5, 3.5), QPointF(w - 1.5, 3.5))
        p.drawLine(QPointF(w / 2 - 3, 10), QPointF(w / 2 + 3, 10))


class FolderIcon(QWidget):
    """知识域文件夹：一个带标签页的文件夹。"""

    def __init__(self, size: int = 17, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        from PySide6.QtCore import QRectF, QPointF
        from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        col = QColor(W.T["ink2"])
        p.setPen(QPen(col, 1.4))
        p.setBrush(Qt.NoBrush)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.moveTo(2, 6)
        path.lineTo(2, 4.5)
        path.quadTo(2, 3.5, 3, 3.5)
        path.lineTo(w * 0.42, 3.5)
        path.lineTo(w * 0.52, 5)
        path.lineTo(w - 3, 5)
        path.quadTo(w - 2, 5, w - 2, 6)
        path.lineTo(w - 2, h - 4)
        path.quadTo(w - 2, h - 3, w - 3, h - 3)
        path.lineTo(3, h - 3)
        path.quadTo(2, h - 3, 2, h - 4)
        path.closeSubpath()
        p.drawPath(path)


class InsightsPage(Page):
    def build(self):
        super().build()
        s = self.store
        now = int(time.time() * 1000)
        cards = s.live_cards()
        reviews = s.live_reviews(cards)
        right = QWidget()
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        more = W.MoreButton(32)
        more.clicked.connect(lambda: self._more_menu(more))
        rl.addWidget(more)
        self.appbar("细数", f"近 31 天 · {len(reviews)} 次复习", right=right)

        self.add(self._radar_card(now, cards, reviews))

        # 活跃 + 准确率已搬到征途「记录」页

        self._archive_section()
        self.stretch()

    def _archive_section(self):
        s = self.store
        decks = s.archived_decks()
        self.section("完成", label(f"{len(decks)} 个卡包", "sub"))

        if not decks:
            box = W.Card(flat=True)
            box.body.setContentsMargins(18, 22, 18, 22)
            t = QLabel("还没有完成的卡包")
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet("font-size:13px;font-weight:600;")
            s2 = QLabel("在「记忆」里对卡包点 ⋯ → 完成，表示这一包已经学完")
            s2.setObjectName("sub")
            s2.setAlignment(Qt.AlignCenter)
            s2.setWordWrap(True)
            box.body.addWidget(t)
            box.body.addWidget(s2)
            self.add(box)
            return

        by_domain: dict[str, int] = {}
        for d in decks:
            by_domain[d.get("domain")] = by_domain.get(d.get("domain"), 0) + 1
        for did, n in by_domain.items():
            dom = s.domain(did) or {"name": "未分组"}
            box = W.ClickFrame()
            box.setObjectName("card")
            bl = QHBoxLayout(box)
            bl.setContentsMargins(15, 13, 14, 13)
            bl.setSpacing(10)

            col = QVBoxLayout()
            col.setSpacing(3)
            t = QLabel(dom.get("name", "未分组"))
            t.setStyleSheet(f"font-size:14.5px;font-weight:700;color:{W.T['ink']};")
            sub = QLabel(f"{n} 个卡包已完成")
            sub.setObjectName("sub")
            col.addWidget(t)
            col.addWidget(sub)
            bl.addLayout(col, 1)

            bl.addWidget(W.Pill(f"{n} 个", "brand"))
            arrow = QLabel("›")
            arrow.setStyleSheet(f"color:{W.T['ink3']};font-size:15px;")
            bl.addWidget(arrow)

            box.clicked.connect(
                lambda d_id=did: self.app.show_page("archive", domain_id=d_id))
            self.add(box)

    # ---------- 六维雷达卡 ----------
    def _build_more_menu(self) -> QMenu:
        """细数右上角 ⋯：设置 + 回收站。"""
        m = QMenu(self)
        m.addAction("设置", lambda: self.app.show_page("settings"))
        n = self.store.trash_count()
        m.addAction(f"回收站（{n}）" if n else "回收站",
                    lambda: self.app.show_page("trash"))
        return m

    def _more_menu(self, anchor: W.MoreButton):
        m = self._build_more_menu()
        m.exec(anchor.mapToGlobal(QPoint(0, anchor.height() + 4)))

    def _radar_card(self, now: int, cards: list, reviews: list) -> QWidget:
        radar = self._radar_data(now, cards, reviews)
        card = W.Card()
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        hl.addWidget(label("六维健康指数", "h2"), 1)
        all_zero = all(v == 0 for _k, v in radar)
        hl.addWidget(W.Pill("暂无数据" if all_zero else
                            ("状态很好" if radar[0][1] >= 70 else "待加强"),
                            "brand"))
        more = QPushButton("详情 ›")
        more.setCursor(Qt.PointingHandCursor)
        more.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;font-size:11.5px;"
            f"color:{W.T['ink2']};}}")
        more.clicked.connect(lambda: self.app.show_page("stats"))
        hl.addWidget(more)
        card.body.addWidget(head)
        holder = QWidget()
        hh = QHBoxLayout(holder)
        hh.setContentsMargins(0, 0, 0, 0)
        hh.addStretch(1)
        hh.addWidget(W.Radar(radar, 220))
        hh.addStretch(1)
        card.body.addWidget(holder)
        tip = label("综合保持、准确、掌握、坚持、均衡与稳定性", "sub")
        tip.setAlignment(Qt.AlignHCenter)
        card.body.addWidget(tip)
        return card

    # ---------- 学习统计卡（保留，当前未使用）----------
    def _stats_card(self) -> QWidget:
        s = self.store
        cards = s.cards
        box = W.Card()
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        hl.addWidget(label("学习统计", "h2"), 1)
        hl.addWidget(label("近 31 天", "sub"))
        more = QPushButton("详情 ›")
        more.setCursor(Qt.PointingHandCursor)
        more.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;font-size:11.5px;"
            f"color:{W.T['ink2']};}}")
        more.clicked.connect(lambda: self.app.show_page("stats"))
        hl.addWidget(more)
        box.body.addWidget(head)

        # 三个指标
        mastered = sum(1 for c in cards if c.get("reps", 0) >= 4
                       and c.get("interval", 0) >= 21)
        learned = [c for c in cards if c.get("reps", 0) > 0]
        avg_iv = (sum(c.get("interval", 0) for c in learned) / len(learned)) if learned else 0
        keep = self._accuracy()
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 2, 0, 2)
        rl.setSpacing(0)
        for i, (val, name) in enumerate(((str(mastered), "已掌握"),
                                         (f"{avg_iv:.0f} 天", "平均间隔"),
                                         (f"{keep}%", "留存率"))):
            if i:
                div = QWidget()
                div.setFixedWidth(1)
                div.setStyleSheet(f"background:{W.T['line']};")
                rl.addWidget(div)
            cell = QWidget()
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(1)
            v = QLabel(val)
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"font-size:17px;font-weight:700;color:{W.T['ink']};")
            n = QLabel(name)
            n.setAlignment(Qt.AlignCenter)
            n.setObjectName("sub")
            cl.addWidget(v)
            cl.addWidget(n)
            rl.addWidget(cell, 1)
        box.body.addWidget(row)

        # 迷你复习量
        labels, new_s, rev_s = self._daily(14)
        box.body.addWidget(W.SparkBars([new_s, rev_s],
                                       [W.T["accent"], W.T["brand"]], 86))
        foot = QWidget()
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(12)
        for name, color, val in (("新学", W.T["accent"], sum(new_s)),
                                 ("复习", W.T["brand"], sum(rev_s))):
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color};font-size:10px;")
            fl.addWidget(dot)
            fl.addWidget(label(f"{name} {val}", "sub"))
        fl.addStretch(1)
        box.body.addWidget(foot)
        return box

    def _daily(self, days: int):
        s = self.store
        keys = [time.strftime("%Y-%m-%d", time.localtime(
            time.time() - (days - 1 - i) * 86400)) for i in range(days)]
        first = set()
        new_c, rev_c = {}, {}
        for r in sorted(s.reviews, key=lambda x: x["at"]):
            k = time.strftime("%Y-%m-%d", time.localtime(r["at"] / 1000))
            if k not in keys:
                continue
            if r["card_id"] in first:
                rev_c[k] = rev_c.get(k, 0) + 1
            else:
                first.add(r["card_id"])
                new_c[k] = new_c.get(k, 0) + 1
        return keys, [new_c.get(k, 0) for k in keys], [rev_c.get(k, 0) for k in keys]

    # ---------- 计算 ----------
    def _radar_data(self, now: int, cards: list, reviews: list):
        """六个维度；没有卡片也没有复习记录时一律 0（不能凭空给出分数）。"""
        empty = [("保持", 0), ("准确", 0), ("掌握", 0),
                 ("坚持", 0), ("均衡", 0), ("稳定", 0)]
        if not cards and not reviews:
            return empty
        total = max(1, len(cards))
        mastered = sum(1 for c in cards if c["reps"] >= 4 and c["interval"] >= 30)
        # 保持：只算真正学过（有 last_review）的卡，新卡没有记忆状态，不拉低也不用默认值凑
        reviewed = [c for c in cards if c.get("last_review")]
        keep = (round(sum(retention(c, now) for c in reviewed) / len(reviewed) * 100)
                if reviewed else 0)
        remembered = sum(1 for r in reviews if r["rating"] >= 2)
        accuracy = round(remembered / len(reviews) * 100) if reviews else 0
        streak = self._streak(reviews)
        active_days = len({time.strftime("%Y-%m-%d", time.localtime(r["at"] / 1000))
                           for r in reviews})
        consistency = min(100, streak * 5 + active_days * 3) if reviews else 0
        # 均衡：未来 30 天每天的到期量，越平均越接近 100（全挤在一天会很低）
        today0 = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1)) * 1000
        buckets: Counter = Counter()
        for c in cards:
            d = int((int(c.get("due") or 0) - today0) // 86_400_000)
            if 0 <= d < 30:
                buckets[d] += 1
        counts = [buckets.get(i, 0) for i in range(30)]
        mean = sum(counts) / len(counts)
        peak = max(counts)
        if peak <= 0:
            balance = 100          # 30 天内没有到期卡，负荷完全平坦
        else:
            balance = max(0, min(100, round(100 * (1 - (peak - mean) / peak))))
        # 稳定：真正学过的卡的平均 ease（新卡的默认 ease 不算）
        studied = [c for c in cards if c.get("reps", 0) > 0]
        stability = 0
        if studied:
            ease = sum(float(c.get("ease") or 2.5) for c in studied) / len(studied)
            stability = max(0, min(100, round((ease - 1.3) / 1.7 * 100)))
        return [("保持", keep), ("准确", accuracy),
                ("掌握", round(mastered / total * 100) if cards else 0),
                ("坚持", consistency), ("均衡", balance), ("稳定", stability)]

    def _heat(self, days: int = 30, reviews: list | None = None):
        return _heat_days(self.store, reviews, days)

    def _accuracy(self, reviews: list | None = None) -> int:
        rs = reviews if reviews is not None else self.store.live_reviews()
        return _accuracy_pct(rs)

    def _by_type(self):
        s = self.store
        agg = {}
        for r in s.reviews:
            c = s.card(r["card_id"])
            if not c:
                continue
            agg.setdefault(c["type"], [0, 0])
            agg[c["type"]][0] += 1
            if r["rating"] >= 2:
                agg[c["type"]][1] += 1
        names = {"qa": "问答题", "single": "单选题", "multi": "多选题"}
        out = []
        for k in ("qa", "single", "multi"):
            n, ok = agg.get(k, [0, 0])
            out.append((names[k], round(ok / n * 100) if n else 0))
        return out

    def _streak(self, reviews: list | None = None) -> int:
        rs = reviews if reviews is not None else self.store.live_reviews()
        return _streak_days(rs)
