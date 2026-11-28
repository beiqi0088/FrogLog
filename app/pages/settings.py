# -*- coding: utf-8 -*-
"""pages/settings.py - 设置：模板 / 外观 / 数据 / 关于。"""
from __future__ import annotations

import json
import os
import time
import zipfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, QWidget,
                               QGridLayout,
                               QFileDialog, QMessageBox)

import widgets as W
import brand
from theme import TEMPLATES
import theme as theme_mod
from pages.base import Page, label


class SettingsPage(Page):
    def build(self):
        super().build()
        s = self.store
        self.appbar("设置", "外观 · 7 套完整纸感主题", back=self.app.go_back)

        self.group("卡片与模板")
        tpl_name = TEMPLATES.get(s.settings.get("default_template", "bean"), {}).get("name", "豆沙绿语")
        self.row("卡片模板", "7 套皮肤，按卡包覆盖", value=tpl_name,
                 on_click=lambda: self.app.show_page("templates"))

        self.group("外观")
        cur_name = theme_mod.theme_info(
            getattr(self.app, "theme_id", theme_mod.DEFAULT_THEME))["name"]
        self.row("主题与外观", "7 套完整纸感主题，点进去切换",
                 value=cur_name,
                 on_click=lambda: self.app.show_page("appearance"))

        self.group("每日节奏")
        self.row("学习调度", "学习步骤 / 间隔 / 每日上限 / 保持率",
                 on_click=lambda: self.app.show_page("sched"))
        new_left, rev_left = self.store.today_counts()
        cfg = self.store.deck_config(None)
        self.row("今日进度", f"新卡 {new_left}/{cfg['new_per_day']} · "
                            f"复习 {rev_left}/{cfg['review_per_day']}",
                 value="")

        self.group("数据与同步")
        self.row("同步", "局域网 / WebDAV / S3", on_click=lambda: self.app.show_page("sync"))
        self.row("导出备份", "生成 .zip 备份，可再导入", on_click=self._export)
        self.row("导入备份", "从 .zip 恢复（兼容 JSON）", on_click=self._import)
        self.row("清零青蛙记录",
                 "青蛙数、勋章、累计学习时长归零",
                 on_click=self._reset_frogs, danger=True)

        self.group("关于")
        self.row("版本", "", value="2.0.0")
        self.row("数据位置", "", value=os.path.basename(self.store.path))
        self.stretch()

    # ---------------------------------------------------------------- 布局件
    def group(self, title: str):
        row = QWidget()
        gl = QHBoxLayout(row)
        gl.setContentsMargins(2, 0, 2, 0)
        gl.setSpacing(7)
        gl.addWidget(W.AccentBar(11, 3), 0, Qt.AlignVCenter)
        lb = QLabel(title)
        lb.setObjectName("sub")
        lb.setStyleSheet(f"color:{W.T['ink2']};font-size:12px;font-weight:700;letter-spacing:1.2px;")
        gl.addWidget(lb, 1)
        self.body.addSpacing(6)
        self.body.addWidget(row)

    def row(self, title: str, desc: str = "", value: str | None = None,
            widget: QWidget | None = None, on_click=None, danger=False):
        if on_click:
            box = W.ClickFrame()
            box.setObjectName("card")
            lay = QHBoxLayout(box)
        else:
            box = W.Card()
            lay = box.body
        lay.setContentsMargins(15, 11, 15, 11)
        lay.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = W.ElideLabel(title)
        t.setStyleSheet(f"font-size:14px;font-weight:600;color:{W.T['red'] if danger else W.T['ink']};")
        col.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setObjectName("sub")
            d.setWordWrap(True)
            col.addWidget(d)
        lay.addLayout(col, 1)
        if widget is not None:
            lay.addWidget(widget)
        if value:
            v = W.ElideLabel(value)
            v.setObjectName("sub")
            lay.addWidget(v)
        if on_click:
            chev = QLabel("›")
            chev.setStyleSheet(f"color:{W.T['ink3']};")
            lay.addWidget(chev)
            box.clicked.connect(on_click)
        self.body.addWidget(box)
        return box

    # ---------------------------------------------------------------- 动作
    def _set_limit(self, v: int):
        self.store.settings["daily_new_limit"] = v
        self.store.save()

    def _export(self):
        default = time.strftime(f"{brand.NAME_EN}-backup-%Y%m%d.zip")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出备份", default, f"{brand.NAME_EN} 备份 (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        data = self.store.export_bytes()
        manifest = {
            "app": brand.NAME,
            "version": "2.0.0",
            "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cards": len(self.store.cards),
            "decks": len(self.store.decks),
            "file": "state.json",
        }
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("state.json", data)
                z.writestr("manifest.json",
                           json.dumps(manifest, ensure_ascii=False, indent=1))
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
            return
        self.app.toast(f"已导出备份：{len(self.store.cards)} 张卡片")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入备份", "", f"{brand.NAME_EN} 备份 (*.zip *.json);;所有文件 (*.*)")
        if not path:
            return
        try:
            if path.lower().endswith(".zip"):
                with zipfile.ZipFile(path) as z:
                    names = z.namelist()
                    inner = "state.json" if "state.json" in names else (
                        next((n for n in names if n.lower().endswith(".json")
                              and "manifest" not in n.lower()), None))
                    if not inner:
                        raise ValueError("压缩包里没有 state.json")
                    raw = z.read(inner)
                data = json.loads(raw.decode("utf-8"))
            else:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            if "cards" not in data or "decks" not in data:
                raise ValueError("格式不对")
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))
            return
        if QMessageBox.question(
                self, "导入备份",
                f"用这份备份覆盖当前数据？\n（{len(data.get('cards') or [])} 张卡片，"
                f"当前 {len(self.store.cards)} 张）") != QMessageBox.Yes:
            return
        from core import keep_device_sync_settings
        keep_device_sync_settings(self.store.state, data)   # 本机同步配置不被备份覆盖
        self.store.state = data
        self.store.save()                                    # 算一次本地改动，下次同步会传上去
        self.app.toast("导入完成")
        self.build()

    def _reset_frogs(self):
        n = self.store.frogs_eaten()
        if n <= 0 and not self.store.checkins:
            self.app.toast("还没有青蛙记录")
            return
        if QMessageBox.question(
                self, "清零青蛙记录",
                f"会把 {n} 只青蛙、勋章和累计学习时长全部归零。\n"
                f"卡片的复习进度不受影响。继续？") != QMessageBox.Yes:
            return
        self.store.reset_frog_data()
        # 征途页如果开着，刷新一下
        self.app.toast("青蛙记录已清零")
        self.build()

    def _reset(self):
        ok = QMessageBox.question(self, "重置全部学习进度",
                                  "所有卡片会立即重新到期，复习历史会清除。继续？")
        if ok == QMessageBox.Yes:
            self.store.reset_progress()
            self.app.toast("学习进度已重置")
            self.build()


class AppearancePage(Page):
    """外观：7 套主题切换（从「设置 → 主题与外观」点进来）。"""

    def build(self):
        super().build()
        self.appbar("外观", back=self.app.go_back)
        cur = getattr(self.app, "theme_id", theme_mod.DEFAULT_THEME)
        tip = QLabel("点一张主题卡立刻生效：整页纸底、卡片、文字和底栏会一起换色。")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{W.T['ink2']};font-size:12.5px;")
        self.add(tip)

        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for i, (tid, info) in enumerate(theme_mod.THEMES.items()):
            card = W.ThemeCard(tid, info, selected=(tid == cur))
            card.clicked.connect(lambda t=tid: self.app.set_theme(t))
            grid.addWidget(card, i // 2, i % 2)
        for c in range(2):
            grid.setColumnStretch(c, 1)
        self.add(grid_host)

        foot = QLabel("7 套完整纸感主题；每套都有独立背景、卡片、文字、边框与点缀配色。")
        foot.setWordWrap(True)
        foot.setStyleSheet(f"color:{W.T['ink3']};font-size:11px;")
        self.add(foot)
        self.stretch()
