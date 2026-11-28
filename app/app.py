# -*- coding: utf-8 -*-
"""
app.py - 主窗口：手机竖屏单列 + 底部导航 + 页面栈 + Toast
结构对齐浮卡：窗口只做导航装配，页面各自成模块（pages/*.py）。
"""
from __future__ import annotations

import os
import sys
import threading

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QStackedWidget, QFrame, QLabel, QApplication,
                               QButtonGroup, QDialog, QSizePolicy)

import widgets as W
import brand
import theme
import fsrs as FS
from core import Store, now_ms, day_str
from pages.today import TodayPage, AllGroupsPage
from pages.sync import SyncPage
from pages.archive import ArchivePage
from pages.cards import CardsPage
from pages.card_edit import CardEditPage
from pages.sched import SchedPage
from pages.stats import StatsPage
from pages.library import LibraryPage, DeckPage
from pages.review import ReviewPage
from pages.plan import PlanPage
from pages.insights import InsightsPage
from pages.settings import SettingsPage, AppearancePage
from pages.backup import BackupPage
from pages.tools import MemoPage, SplitPage, TemplatesPage

_FAMILY_CACHE: str | None = None
_IS_ANDROID = sys.platform == "android"   # 安卓窗口由系统铺满，不能再 move()


def _write_bar_color_file(hex_str: str | None):
    """把页面底色写进应用私有目录，供 Java 侧读取。

    安卓 15+ 上 setStatusBarColor/setNavigationBarColor 已经不起作用，安全区
    那一条只能靠 Activity 窗口背景来填；而窗口背景必须在 Java 里设置才稳，
    Java 又要知道当前主题色 —— 用文件做一次最简单的桥接，不依赖 jnius 是否可用。
    """
    if not hex_str:
        return
    try:
        d = os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_APP_PATH")
        if not d:
            return
        with open(os.path.join(d, "froglog_bar_color.txt"), "w") as f:
            f.write(hex_str)
    except Exception:
        pass


def _android_edge_to_edge(bg_hex: str | None = None, nav_hex: str | None = None):
    """安卓：内容铺到系统栏后面，状态栏与手势条都透出页面底色。

    Qt 在窗口首次显示、切换主题（setStyleSheet）时都可能把系统栏重设，
    所以启动和每次换主题之后都要重放。bg_hex 是页面纯色底，用来给状态栏
    和 Activity 窗口底色兜底；nav_hex 是手势条颜色（默认与页面同色）。
    """
    _write_bar_color_file(bg_hex)
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread
    except Exception:
        return

    def _argb(hex_str):
        c = QColor(hex_str) if hex_str else QColor()
        if not c.isValid():
            return 0                    # Color.TRANSPARENT
        v = (255 << 24) | (c.red() << 16) | (c.green() << 8) | c.blue()
        if v >= 1 << 31:
            v -= 1 << 32                # Java 的 int 是有符号的
        return v

    color = _argb(bg_hex)
    nav_color = _argb(nav_hex) if nav_hex else color

    @run_on_ui_thread
    def _apply():
        try:
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            if activity is None:
                return
            window = activity.getWindow()
            Build = autoclass("android.os.Build$VERSION")
            # 状态栏和手势条都必须露出来（时间/电量/手势条），不能被全屏标志藏掉
            window.clearFlags(1024)          # FLAG_FULLSCREEN
            window.setStatusBarColor(color)
            window.setNavigationBarColor(nav_color)
            if bg_hex:
                try:
                    ColorDrawable = autoclass("android.graphics.drawable.ColorDrawable")
                    window.setBackgroundDrawable(ColorDrawable(color))
                except Exception:
                    pass
            if Build.SDK_INT >= 29:
                window.setStatusBarContrastEnforced(False)
                window.setNavigationBarContrastEnforced(False)
            if Build.SDK_INT >= 30:
                window.setDecorFitsSystemWindows(False)
                ctrl = window.getInsetsController()
                if ctrl is not None:
                    # 状态栏 / 手势条都是浅色纸底 → 都用深色系统图标与手势条
                    ctrl.setSystemBarsAppearance(8 | 16, 8 | 16)
                    try:
                        # 确保时间、电量、手势条都显示（透明栏也不隐藏）
                        ctrl.show(autoclass("android.view.WindowInsets$Type").systemBars())
                    except Exception:
                        pass
            else:
                window.getDecorView().setSystemUiVisibility(
                    0x0100 | 0x0200 | 0x0400 | 0x0010 | 0x2000)
            try:
                bars = autoclass("org.kivy.android.FrogLogSystemBars")
                bars.barColor = color
                bars.navBarColor = nav_color
            except Exception:
                pass
        except Exception:
            pass

    try:
        _apply()
    except Exception:
        pass


def _android_edge_to_edge_safe(bg_hex: str | None = None, nav_hex: str | None = None):
    try:
        _android_edge_to_edge(bg_hex, nav_hex)
    except Exception:
        pass


def resolve_family() -> str:
    """挑一个系统里真实存在的字体（offscreen 截图时也能出字）。

    QFontDatabase.families() 在 Windows 上要枚举全部字体（几百毫秒），
    以前每次切主题都调一遍，导致主题切换要卡 0.6~0.8 秒。这里缓存一次。
    """
    global _FAMILY_CACHE
    if _FAMILY_CACHE:
        return _FAMILY_CACHE
    fams = set(QFontDatabase.families())
    for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Alibaba PuHuiTi 2.0",
                 "SimHei", "PingFang SC", "Noto Sans CJK SC"):
        if name in fams:
            _FAMILY_CACHE = name
            return name
    _FAMILY_CACHE = "Sans Serif"
    return _FAMILY_CACHE


MAIN_TABS = [("today", "今日"), ("library", "记忆"), ("plan", "征途"),
             ("insights", "战果")]
NO_NAV = {"review", "settings", "appearance", "memo", "split", "templates", "deck", "groups", "sync", "archive", "cards", "card_edit", "sched", "stats", "backup", "frog_records", "medals", "trash"}


class BgLayer(QWidget):
    """整页渐变底：7 套 Anki 主题的径向/线性底色都画在这里。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        win = self.window()
        tid = getattr(win, "theme_id", None)
        # 整页奶白：系统栏区域也透出奶白，与参考图一致；不再单独刷深色条。
        theme.paint_page_bg(p, self.rect(), tid)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = Store()
        self.session = None
        self._review_page = None
        self.deck_scroll: dict = {}      # 卡包浏览列表的滚动位置（按 卡包/档位/卡组 记）
        self.deck_selection = {}
        self.library_domain = None
        self.lan_server = None
        self._history: list[tuple[str, dict]] = []
        self._undo: list[dict] = []
        self._nav_back = False
        # 征途任务：只在「学习页（review）」跑表；切页面/失焦/最小化/关窗都会暂停
        self.quest_timer = QTimer(self)
        self.quest_timer.setInterval(1000)
        self.quest_timer.timeout.connect(self._quest_tick)
        self.setWindowTitle(brand.NAME)
        # Qt 6.9+：内容铺到状态栏和手势条后面，渐变背景才能覆盖整块屏幕。
        # 没这个提示时 Qt 会把窗口退回安全区内，系统栏区域会露出主题白底。
        if hasattr(Qt, "ExpandedClientAreaHint"):
            self.setWindowFlag(Qt.ExpandedClientAreaHint, True)
        if _IS_ANDROID:
            # 安卓必须让窗口铺满整块屏幕。固定 resize()/maximumWidth() 会让窗口
            # 比屏幕小一圈，右侧和底部就会露出 Activity 的白底。
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            scr = QApplication.primaryScreen()
            if scr is not None:
                self.resize(scr.size())
        else:
            self.setMinimumSize(380, 700)
            self.resize(430, 880)
            self.setMaximumWidth(560)
        _default = theme.theme_tokens(theme.DEFAULT_THEME)
        self.setStyleSheet(f"QMainWindow{{background:{_default['paper']};}}")
        # 安卓系统返回键会作为 Qt.Key_Back 送到应用里，这里全局接住
        QApplication.instance().installEventFilter(self)

        root = QWidget()
        root.setObjectName("root")
        self.root = root
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.root_layout = outer

        self.column = QWidget()
        self.column.setObjectName("phoneColumn")
        col = QVBoxLayout(self.column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self.stack = QStackedWidget()
        col.addWidget(self.stack, 1)

        self.nav = QFrame()
        self.nav.setFixedHeight(44)
        self.nav.setObjectName("navFrame")
        nav_outer = QHBoxLayout(self.nav)
        nav_outer.setContentsMargins(12, 0, 12, 0)
        nav_outer.setSpacing(0)
        self.nav_bar = QFrame()
        self.nav_bar.setObjectName("navBar")
        self.nav_bar.setStyleSheet("QFrame#navBar{background:transparent;border:none;}")
        nav_lay = QHBoxLayout(self.nav_bar)
        nav_lay.setContentsMargins(4, 0, 4, 0)
        nav_lay.setSpacing(4)
        nav_lay.setAlignment(Qt.AlignCenter)
        nav_outer.addWidget(self.nav_bar)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        for key, name in MAIN_TABS:
            b = W.NavButton(key, name)
            self.nav_group.addButton(b)
            b.clicked.connect(lambda _, k=key: self.show_page(k))
            nav_lay.addWidget(b, 1)
            self.nav_buttons[key] = b
        col.addWidget(self.nav)

        outer.addWidget(self.column, 1)

        self.toast_label = QLabel("", root)
        self.toast_label.hide()
        self.toast_label.setStyleSheet(
            "background:rgba(36,39,33,0.92);color:#FBF8F1;border-radius:14px;"
            "padding:9px 16px;font-size:12px;")
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self.toast_label.hide)

        # 渐变底：放在 root 最底层，column / 页面 / 底栏都透明，渐变能透出来
        self.bg = BgLayer(root)
        self.bg.setGeometry(root.rect())
        self.bg.lower()

        self.apply_theme()
        self.show_page("today")
        self.quest_timer.start()
        self._flush_timer = QTimer(self)      # 空闲落盘：最多 0.7s 写一次
        self._flush_timer.timeout.connect(self.store.flush)
        self._flush_timer.start(700)
        QTimer.singleShot(400, self.maybe_settle)
        # 空闲时预热一张复习页：第一次进学习页不用现场加载字体/样式/文本排版
        QTimer.singleShot(800, self._prewarm_review)   # 启动后尽快预热，第一次点卡组就是热的

    def _prewarm_review(self):
        """在后台把复习页的字体、样式、文本排版缓存热一遍（用完即删，不显示）。"""
        try:
            cards = self.store.live_cards()
            if not cards:
                return
            card = cards[0]
            old = self.session
            self.session = {
                "queue": [card], "index": 0, "revealed": False,
                "picked": None, "submitted": False, "ratings": [],
                "started": now_ms(), "card_start": now_ms(),
                "practice": True, "deck_id": card.get("deck_id"),
            }
            if self._review_page is None:
                self._review_page = ReviewPage(self)
            page = self._review_page
            page.resize(430, 880)
            page.render()
            page.grab()                 # 逼出一次真正的排版 + 绘制
            page.setParent(None)        # 先挂空，等真正进复习页再放进栈里
        except Exception:
            pass
        finally:
            try:
                self.session = old
            except Exception:
                self.session = None

    # ------------------------------------------------------------ 主题
    def apply_theme(self):
        tid = self.store.settings.get("theme")
        if not tid:
            tid = theme.DEFAULT_THEME
        self.theme_id = tid if tid in theme.THEMES else theme.DEFAULT_THEME
        t = theme.theme_tokens(self.theme_id)
        theme.set_font(resolve_family())
        W.set_tokens(t)
        app = QApplication.instance()
        app.setFont(QFont(theme.FONT, 9))
        app.setStyleSheet(theme.build_qss(t))
        # 窗口自身底色就是状态栏安全区那一条的颜色：必须用页面纯色底。
        # 这行是控件级样式，优先级高于全局表，之前写死 paper 就是顶部色差的根源。
        page_bg = theme.page_bg_color(self.theme_id).name()
        self.setStyleSheet(f"QMainWindow{{background:{page_bg};}}")
        # 底部 dock 不再铺深色：和页面同底，选中项用浅色胶囊 + 主题色图标
        self.nav.setStyleSheet(
            "QFrame#navFrame{background:transparent;border:none;}"
        )
        self.nav_bar.setStyleSheet("QFrame#navBar{background:transparent;border:none;}")
        for b in self.nav_buttons.values():
            b.update()
        if hasattr(self, "bg"):
            self.bg.update()
        self._apply_android_bars()

    def _apply_android_bars(self):
        """状态栏 / 手势条铺和页面完全一致的纯色底 + 深色系统图标（换主题后 Qt 可能重置）。"""
        if not _IS_ANDROID:
            return
        paper = theme.theme_tokens(self.theme_id).get("paper", "#F3EEDF")
        # 页面现在是纯色底：状态栏、Activity 窗口底、手势条统一取这块底色，
        # 顶部就不会再出现一条比页面浅/深、还把时间电量藏起来的色差条。
        page_bg = theme.page_bg_color(self.theme_id).name()
        write_log = getattr(sys, "froglog_log", None)
        if callable(write_log):
            try:
                scr = self.screen().geometry() if self.screen() else None
                write_log(f"系统栏底色 page={page_bg} paper={paper} "
                          f"窗口={self.width()}x{self.height()} "
                          f"屏幕={scr.width() if scr else 0}x{scr.height() if scr else 0} "
                          f"insets={getattr(self, '_sys_top', 0)}/{getattr(self, '_sys_bottom', 0)}")
            except Exception:
                pass
        for ms in (0, 300, 1200, 3000):
            QTimer.singleShot(ms, lambda c=page_bg, d=page_bg: _android_edge_to_edge_safe(c, d))

    def _sync_bg(self):
        # 背景层铺满整个 central widget。安卓上窗口已被拉到全屏，
        # root.rect() 就是整块屏幕（含状态栏/手势条区域）。
        if hasattr(self, "bg") and hasattr(self, "root"):
            self.bg.setGeometry(self.root.rect())
            self.bg.lower()

    def _sync_system_insets(self):
        """内容避开状态栏/手势条，背景层仍铺满整块屏幕。"""
        wh = self.windowHandle()
        top = bottom = 0
        if wh is not None:
            if getattr(self, "_insets_window", None) is not wh:
                self._insets_window = wh
                if hasattr(wh, "safeAreaMarginsChanged"):
                    wh.safeAreaMarginsChanged.connect(
                        lambda *_: self._sync_system_insets())
            if hasattr(wh, "safeAreaMargins"):
                margins = wh.safeAreaMargins()
                top = max(0, margins.top())
                bottom = max(0, margins.bottom())
        self._sys_top = top
        self._sys_bottom = bottom
        # dock 只有 44 高、图标垂直居中；下方手势区与页面同色，
        # 所以整条底栏延伸到内容区最底部。
        if hasattr(self, "nav"):
            pad = min(bottom, 26)
            if _IS_ANDROID and pad <= 0:
                # 部分机型边到边后 safeArea 返回 0，但手势条其实压着内容，
                # 这里兜底 24dp，保证底栏一直铺到屏幕最底部。
                pad = 24
            self.nav.setFixedHeight(44 + pad)
            outer = self.nav.layout()
            if outer is not None:
                # 底部不再留白：图标在「dock + 手势区」整块里垂直居中
                outer.setContentsMargins(12, 0, 12, 0)
        # 顶部不再留任何空白：安卓窗口内容本来就从状态栏下方开始，
        # 再叠一次 safeArea 就会多出一条空带。页面顶栏贴住内容区顶部即可。
        if hasattr(self, "root_layout"):
            self.root_layout.setContentsMargins(0, 0, 0, 0)
        if hasattr(self, "bg"):
            self.bg.update()
        if top + bottom > 0 and not getattr(self, "_insets_logged", False):
            self._insets_logged = True
            write_log = getattr(sys, "froglog_log", None)
            if callable(write_log):
                try:
                    scr = self.screen().geometry()
                    write_log(f"系统栏适配: 窗口 {self.width()}x{self.height()} "
                              f"屏幕 {scr.width()}x{scr.height()} "
                              f"insets={top}/{bottom} "
                              f"flags=0x{int(self.windowFlags()):x}")
                except Exception:
                    pass

    def _drop_review_cache(self):
        """换主题后让常驻的复习页重建，顶栏/底栏用新主题色。"""
        if getattr(self, "_review_page", None) is not None:
            try:
                self._review_page.deleteLater()
            except Exception:
                pass
            self._review_page = None

    def set_theme(self, tid: str):
        self.store.settings["theme"] = tid
        self.store.settings["dark"] = theme.theme_is_dark(tid)
        self.store.save()
        self.apply_theme()
        self._drop_review_cache()
        cur = self.stack.currentWidget()
        if cur and hasattr(cur, "build"):
            cur.build()

    def set_dark(self, dark: bool):
        self.store.settings["dark"] = bool(dark)
        self.store.save()
        self.apply_theme()
        self._drop_review_cache()
        cur = self.stack.currentWidget()
        if cur and hasattr(cur, "build"):
            cur.build()

    # ------------------------------------------------------------ 导航
    def showEvent(self, e):
        super().showEvent(e)
        self._sync_bg()
        self._sync_system_insets()
        QTimer.singleShot(0, self._sync_bg)
        QTimer.singleShot(0, self._sync_system_insets)
        QTimer.singleShot(120, self._sync_system_insets)
        if _IS_ANDROID:
            self._fit_screen()
            QTimer.singleShot(200, self._fit_screen)
            QTimer.singleShot(800, self._fit_screen)
            self._apply_android_bars()
            QTimer.singleShot(6000, self._apply_android_bars)
        if not getattr(self, "_centered", False):
            self._centered = True
            if not _IS_ANDROID:
                W.center_on_screen(self)

    def _fit_screen(self):
        """安卓：把窗口拉到整块屏幕，避免右侧/底部露出白边。"""
        try:
            scr = self.screen()
            if scr is not None:
                g = scr.geometry()
                if self.geometry() != g:
                    self.setGeometry(g)
        except Exception:
            pass
        self._sync_bg()
        self._sync_system_insets()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 窗口尺寸（含系统栏适配后的全屏尺寸）变化时重新铺满渐变，避免上下露出底色。
        self._sync_bg()

    def show_page(self, key: str, **kw):
        prev = getattr(self, "_cur_spec", None)
        # 计时只认学习页：离开就自动暂停，进来就接着跑（开关只负责武装任务）
        if prev is not None and prev[0] == "review" and key != "review":
            self.store.quest_pause_clock()
        if key == "review":
            self.store.quest_start_clock()
        if prev is not None and not self._nav_back and prev != (key, dict(kw)):
            self._history.append(prev)
            if len(self._history) > 40:
                self._history.pop(0)
        self._cur_prev = prev
        self._cur_spec = (key, dict(kw))
        self.store.flush()
        old = self.stack.currentWidget()
        if key == "review":
            # 学习页常驻：切走时不销毁，下次进来直接换 current（省掉整页重建）
            page = self._review_page
            if page is None:
                from pages.review import ReviewPage as _RP
                page = self._review_page = _RP(self)
            if self.stack.indexOf(page) < 0:
                self.stack.addWidget(page)
            self.stack.setCurrentWidget(page)
        else:
            page = self._make(key, **kw)
            if page is None:
                return
            self.stack.addWidget(page)
            self.stack.setCurrentWidget(page)
            if old is not None and old is not page and old is not self._review_page:
                self.stack.removeWidget(old)
                old.deleteLater()
        if hasattr(page, "on_show"):
            page.on_show()
        # 安卓没有滚轮：页面里的 QScrollArea 必须装 QScroller 才能手指拖动
        W.enable_touch_scroll_deep(page)
        self.nav.setVisible(key not in NO_NAV)
        if key in self.nav_buttons:
            self.nav_buttons[key].setChecked(True)

    # ---------- 征途：领取任务 / 学习页跑表 ----------
    def claim_quest(self, mins: int = 25):
        self.store.quest_claim(mins)
        self.toast(f"已领取 {mins} 分钟任务 · 去学习页开始计时")

    def abandon_quest(self):
        self.store.quest_reset()
        self.toast("已放弃本次任务")
        self._refresh_quest_ui(True)

    def _quest_tick(self):
        """每秒：够了就结算、跨过 0 点就把昨天的任务清零，然后刷新计时显示。"""
        # 跨天：正在学习时先不打断，等离开学习页再清零
        if (day_str() != (self.store.game.get("last_day") or "")
                and not self.store.quest_running()):
            self.maybe_settle()
            self._refresh_quest_ui(True)
            return
        if self.store.quest.get("status") == "active":
            done = self.store.quest_complete()
            if done:
                r = done.get("reward") or {}
                self.toast(f"征途完成 · 经验 +{r.get('xp', 0)} · 金币 +{r.get('gold', 0)}")
                self._refresh_quest_ui(True)
                return
        self._refresh_quest_ui()

    def _refresh_quest_ui(self, full: bool = False):
        cur = self.stack.currentWidget()
        fn = getattr(cur, "refresh_quest", None) if cur is not None else None
        if fn is None:
            return
        try:
            fn(full)
        except TypeError:
            fn()

    # ---------- 征途：数值反馈 / 升级 / 跨天结算 ----------
    def game_feedback(self, res: dict):
        """一次得分后的 Toast 与升级弹层。"""
        parts = []
        if res.get("xp"):
            parts.append(f"+{res['xp']} 经验")
        if res.get("gold"):
            parts.append(f"+{res['gold']} 金币")
        if res.get("hp"):
            parts.append(f"{res['hp']} 生命")
        if res.get("streak"):
            parts.append(f"连击 {res['streak']}")
        if parts:
            self.toast(" · ".join(parts))
        for ev in res.get("events") or []:
            if ev.get("type") == "levelup":
                lv = int(ev.get("lv") or 1)
                QTimer.singleShot(0, lambda v=lv: self.show_levelup(v))

    def show_levelup(self, lv: int):
        from pages.journey_dialogs import LevelUpDialog
        pts = int(self.store.game.get("attr_points") or 0)
        dlg = LevelUpDialog(lv, pts, self)
        dlg.exec()
        if dlg.picked:
            self.store.allocate_point(dlg.picked)
            self.toast("属性点已分配")
        self._refresh_quest_ui(True)

    def maybe_settle(self):
        """跨天时弹一次结算摘要（幂等：同一天只会有摘要一次）。"""
        info = self.store.run_daily_cron()
        if not info:
            return
        # 昨天什么都没干就别弹窗了（回血/清零已经由 run_daily_cron 做掉）
        if not info.get("records") and not info.get("missed"):
            return
        from pages.journey_dialogs import SettleDialog
        SettleDialog(info, self).exec()
        self._refresh_quest_ui(True)

    def _make(self, key, **kw):
        if key == "today":
            return TodayPage(self)
        if key == "library":
            return LibraryPage(self, kw.get("domain"), kw.get("round_id"))
        if key == "trash":
            from pages.trash import TrashPage
            return TrashPage(self)
        if key == "stats":
            return StatsPage(self)
        if key == "sched":
            return SchedPage(self, kw.get("deck_id"))
        if key == "card_edit":
            return CardEditPage(self, kw.get("card_id"),
                                kw.get("deck_id"), kw.get("group"))
        if key == "cards":
            return CardsPage(self, kw.get("kind", "due"))
        if key == "archive":
            return ArchivePage(self, kw.get("domain_id"))
        if key == "sync":
            return SyncPage(self)
        if key == "groups":
            return AllGroupsPage(self)
        if key == "plan":
            return PlanPage(self)
        if key == "insights":
            return InsightsPage(self)
        if key == "settings":
            return SettingsPage(self)
        if key == "appearance":
            return AppearancePage(self)
        if key == "backup":
            return BackupPage(self)
        if key == "deck":
            return DeckPage(self, kw.get("deck_id", ""))
        if key == "medals":
            from pages.medals import MedalsPage
            return MedalsPage(self)
        if key == "frog_records":
            from pages.frog_records import FrogRecordsPage
            return FrogRecordsPage(self)
        if key == "review":
            return ReviewPage(self)
        if key == "memo":
            return MemoPage(self)
        if key == "split":
            return SplitPage(self)
        if key == "templates":
            return TemplatesPage(self, kw.get("deck_id"))
        self.toast(f"未知页面：{key}")
        return None

    # ------------------------------------------------------------ 复习
    def start_review(self, deck_id=None, single=None, group=None, practice=False):
        s = self.store
        if single:
            card = s.card(single)
            queue = [card] if card else []
        elif practice:
            queue = s.practice_cards(deck_id)
        else:
            # 卡组必须参与限额计算：先按整卡包取前 N 张再按卡组过滤，
            # 会把「今天的新卡额度」先花在别的卡组上，这个组就一张不剩了。
            queue = s.study_queue(deck_id, group=group)
        if group and (practice or single):
            queue = [c for c in queue if c.get("group") == group]
        if not queue:
            # 区分「真没有到期的卡」和「今天的新卡/复习额度用完了」
            due = s.due_cards(deck_id)
            if group:
                due = [c for c in due if c.get("group") == group]
            self.toast("今天的额度用完了，明天再来" if due else "没有可复习的卡片")
            return
        self.review_back = getattr(self, "_cur_spec", None)
        self.session = {
            "queue": queue, "index": 0, "revealed": False,
            "picked": None, "submitted": False, "ratings": [],
            "started": now_ms(), "card_start": now_ms(),
            "practice": bool(practice) or bool(single),
            "deck_id": deck_id,
        }
        self.show_page("review")

    def start_review_cards(self, cards, title: str = "回顾"):
        """用一组指定卡片开一次复习（每日回顾用）。"""
        cards = [c for c in cards if not c.get("archived")]
        if not cards:
            self.toast("没有可复习的卡片")
            return
        self.review_back = getattr(self, "_cur_spec", None)
        self.session = {
            "queue": list(cards), "index": 0, "revealed": False,
            "picked": None, "submitted": False, "ratings": [],
            "started": now_ms(), "card_start": now_ms(),
            "practice": False, "deck_id": None, "title": title,
        }
        self.show_page("review")

    UNDO_FIELDS = ("due", "interval", "reps", "ease", "lapses", "last_review",
                   "state", "step", "stability", "difficulty")

    def _snapshot(self, card: dict) -> dict:
        return {"id": card["id"],
                "fields": {k: card.get(k) for k in self.UNDO_FIELDS},
                "reviews": len(self.store.reviews)}

    def undo(self) -> bool:
        """撤销上一次评分（Anki 的 Undo）。"""
        if not self._undo:
            self.toast("没有可撤销的操作")
            return False
        snap = self._undo.pop()
        card = self.store.card(snap["id"])
        if not card:
            return False
        for k, v in snap["fields"].items():
            if v is None:
                card.pop(k, None)
            else:
                card[k] = v
        del self.store.reviews[snap["reviews"]:]
        self.store.save()
        if self.session:
            self.session["index"] = max(0, self.session["index"] - 1)
            # 上一次评分如果把这卡放回了学习队列，撤销时要把那一条也去掉
            ids = self.session.get("requeued") or []
            if ids:
                cid = ids.pop()
                q = self.session["queue"]
                for k in range(len(q) - 1, self.session["index"], -1):
                    if q[k].get("id") == cid:
                        q.pop(k)
                        break
            if self.session["ratings"]:
                self.session["ratings"].pop()
            self.session["revealed"] = False
            self.session["picked"] = None
            self.session["submitted"] = False
            cur = self.stack.currentWidget()
            if hasattr(cur, "render"):
                cur.render()
        self.toast("已撤销")
        return True

    def _requeue_learning(self, ses: dict, card: dict, due: int):
        """把刚进学习/重学步骤的卡按到期时间放回队尾（20 分钟内才算）。"""
        if due > now_ms() + 20 * 60 * 1000:
            return
        q = ses["queue"]
        pos = ses["index"] + 1
        while pos < len(q) and int(q[pos].get("due") or 0) <= due:
            pos += 1
        q.insert(pos, card)
        ses.setdefault("requeued", []).append(card["id"])

    @staticmethod
    def _drop_from_queue(ses: dict, ids: set):
        """把某些卡从会话队列里摘掉（bury 兄弟时用），顺带修正 index。"""
        if not ids or not ses:
            return
        q = ses["queue"]
        old = list(q)
        q[:] = [c for c in old if c.get("id") not in ids]
        gone_before = sum(1 for c in old[:ses["index"]] if c.get("id") in ids)
        ses["index"] = max(0, ses["index"] - gone_before)

    def rate_card(self, rating: int):
        ses = self.session
        if not ses:
            return
        if ses["index"] >= len(ses["queue"]):
            return
        card = ses["queue"][ses["index"]]
        prev_iv = card["interval"]
        if not ses["practice"]:
            pre_state = card.get("state") or ("review" if int(card.get("reps") or 0) else "new")
            self._undo.append(self._snapshot(card))
            if len(self._undo) > 50:
                self._undo.pop(0)
            cfg = self.store.sched_cfg(card.get("deck_id"),
                                       note_id=card.get("note_id"),
                                       card_id=card.get("id"))
            res = FS.step(card, rating, now_ms(), cfg=cfg)
            card.update(
                interval=res["interval"], reps=res["reps"], ease=card.get("ease", 2.5),
                lapses=res["lapses"], due=res["due"], last_review=now_ms(),
                state=res["state"], step=res["step"],
                stability=res["stability"], difficulty=res["difficulty"],
            )
            self.store.add_review(card, rating, prev_iv, res["interval"],
                                  now_ms() - ses["card_start"])
            if res.get("leech") and rating == 0:
                tags = set(card.get("tags") or [])
                if "leech" not in tags:
                    card["tags"] = list(tags) + ["leech"]
                    self.toast("这张卡累计遗忘 8 次，已标记 leech")
            # 每日计数：按「作答前」的状态记（Anki 的 new_today / review_today）
            self.store.bump_deck_stats(card.get("deck_id"),
                                       was_new=(pre_state == "new"),
                                       was_review=(pre_state == "review"),
                                       persist=False)
            # bury 兄弟卡（Anki 的 BuryMode，默认关，可在卡组选项里开）
            if ((pre_state == "new" and cfg.get("bury_new"))
                    or (pre_state == "review" and cfg.get("bury_reviews"))):
                buried = self.store.bury_siblings(card.get("note_id"), card.get("id"),
                                                  persist=False)
                if buried:
                    self._drop_from_queue(ses, set(buried))
            # Anki 的行为：点了「重来」进学习/重学步骤后，到点要再出现一次（同一会话内）
            if res["state"] in ("learning", "relearning"):
                self._requeue_learning(ses, card, int(res["due"]))
            self.store.save_deferred()  # 先记脏，空闲时统一落盘
        ses["ratings"].append(rating)
        ses["index"] += 1
        ses["revealed"] = False
        ses["submitted"] = False
        ses["picked"] = None
        ses["card_start"] = now_ms()
        cur = self.stack.currentWidget()
        if isinstance(cur, ReviewPage):
            cur.render()

    def sync_now(self, mode: str = "auto") -> str:
        """按 Anki 的方式同步：自动判方向，冲突时让用户选上传还是下载。

        网络请求放到后台线程，避免点一下「同步」整个窗口卡住（超时可达 20 秒）。
        """
        if getattr(self, "_sync_job", None) and self._sync_job.is_alive():
            return ""
        import sync as S
        from pages.sync import sync_cfg
        if mode == "auto":
            self._sync_cfg = dict(sync_cfg(self.store))
        cfg = getattr(self, "_sync_cfg", None) or dict(sync_cfg(self.store))
        store = self.store
        self._sync_result = None

        def work():
            try:
                self._sync_result = ("ok", S.do_sync(store, cfg, mode), None)
            except Exception as e:
                self._sync_result = ("err", str(e), e)

        self._sync_job = threading.Thread(target=work, daemon=True)
        self._sync_job.start()
        QTimer.singleShot(150, self._poll_sync)
        return ""

    def _poll_sync(self):
        if self._sync_job and self._sync_job.is_alive():
            QTimer.singleShot(150, self._poll_sync)
            return
        kind, msg, exc = self._sync_result or ("err", "未知错误", None)
        import sync as S
        if kind == "ok":
            self.toast(msg)
            cur = self.stack.currentWidget()
            if cur and hasattr(cur, "build"):
                cur.build()
            return
        if isinstance(exc, S.SyncConflict):
            choice = self._ask_sync_conflict(exc)
            if not choice:
                self.toast("已取消同步")
                return
            self.sync_now(choice)
            return
        self.toast(f"同步失败：{msg}")

    def _ask_sync_conflict(self, e) -> str | None:
        from pages.sync import SyncConflictDialog
        dlg = SyncConflictDialog(e.local_at, e.remote_at,
                                 getattr(e, 'local_cards', 0),
                                 getattr(e, 'remote_cards', 0), self)
        dlg.exec()
        return dlg.choice

    def go_back(self):
        """返回上一个操作的页面（统一入口）。"""
        while self._history:
            key, kw = self._history.pop()
            cur = getattr(self, "_cur_spec", None)
            if key == "review" and cur and cur[0] == "review":
                continue        # 从复习页退出时，跳过复习页本身
            self._nav_back = True
            try:
                self.show_page(key, **kw)
            finally:
                self._nav_back = False
            return
        self.show_page("today")

    # ------------------------------------------------- 系统返回键（安卓）
    def handle_back(self) -> bool:
        """返回键：先退出学习页，再退回上一页；已在首页则交给系统（退出应用）。"""
        cur = getattr(self, "_cur_spec", None)
        if cur is not None and cur[0] == "review":
            self.exit_review()
            return True
        if self._history:
            self.go_back()
            return True
        return False

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress and ev.key() == Qt.Key_Back:
            modal = QApplication.activeModalWidget()
            if isinstance(modal, QDialog):
                modal.reject()          # 有弹窗时，返回键先关弹窗
                return True
            if modal is not None:
                return False
            return self.handle_back()
        return super().eventFilter(obj, ev)

    def exit_review(self):
        self.session = None
        page = getattr(self, "_review_page", None)
        if page is not None:
            page._resize_timer.stop()      # 别让延迟重绘在退出后再触发
            page._waiting = False
        self.go_back()

    # ------------------------------------------------------------ Toast
    def toast(self, text: str):
        self.toast_label.setText(text)
        self.toast_label.adjustSize()
        w = self.toast_label.width()
        self.toast_label.move((self.width() - w) // 2, self.height() - 120)
        self.toast_label.raise_()
        self.toast_label.show()
        self._toast_timer.start(1800)

    # ------------------------------------------------- 只认「学习页」的计时
    # 注意：只按「页面 / 最小化 / 关窗」暂停，不按窗口失焦暂停。
    # 失焦是很常见的（截图、切去看资料），一失焦就把倒计时冻住反而像坏了。
    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() != QEvent.WindowStateChange:
            return
        if self.isMinimized():
            self.store.quest_pause_clock()
        else:
            # 从最小化恢复：如果当前还在学习页，接着跑表
            cur = getattr(self, "_cur_spec", None)
            if cur and cur[0] == "review":
                self.store.quest_start_clock()
        self._refresh_quest_ui()

    def closeEvent(self, e):
        self.store.quest_pause_clock()
        self.store.flush()
        super().closeEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._sync_bg()
        if self.toast_label.isVisible():
            w = self.toast_label.width()
            self.toast_label.move((self.width() - w) // 2, self.height() - 120)
