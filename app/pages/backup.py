# -*- coding: utf-8 -*-
"""pages/backup.py - 备份与回滚：列出所有快照，一键恢复。"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget, QFileDialog, QMessageBox)

import backup
import widgets as W
from pages.base import Page, label

KIND_PILL = {
    "auto": ("plain", "自动"),
    "manual": ("brand", "手动"),
    "before-restore": ("green", "回滚前"),
    "daily": ("accent", "每日"),
    "zip": ("accent", "导出包"),
    "migrate": ("plain", "迁移"),
}


def _diff_text(cards: int, current: int) -> str:
    d = cards - current
    if d == 0:
        return "和现在一样多"
    return f"比现在{'多' if d > 0 else '少'} {abs(d)} 张"


class BackupDetailDialog(QDialog):
    """一份备份的详情：时间、卡片数、路径，以及恢复 / 删除。"""

    def __init__(self, it: dict, current_cards: int, parent=None):
        super().__init__(parent)
        self.action = None
        self.setWindowTitle("备份详情")
        self.resize(400, 330)
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)

        title = QLabel(backup.KIND_LABEL.get(it["kind"], "备份"))
        title.setStyleSheet(f"font-size:17px;font-weight:700;color:{W.T['ink']};")
        lay.addWidget(title)

        sub = QLabel(os.path.basename(it["path"]))
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        card = W.Card(flat=True)
        rows = [
            ("备份时间", backup.fmt_time(it["mtime"])),
            ("卡片 / 卡包", f"{it['cards']} 张 · {it['decks']} 个"),
            ("相对现在", _diff_text(it["cards"], current_cards)),
            ("文件大小", backup.fmt_size(it["size"])),
        ]
        for k, v in rows:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            kl = QLabel(k)
            kl.setObjectName("sub")
            vl = QLabel(v)
            vl.setStyleSheet(f"font-size:12.5px;font-weight:600;color:{W.T['ink']};")
            rl.addWidget(kl)
            rl.addStretch(1)
            rl.addWidget(vl)
            card.body.addWidget(row)
        lay.addWidget(card)

        warn = QLabel("恢复会用这份备份整份替换当前数据；"
                      "恢复前会自动存一份「回滚前快照」，可以再退回来。")
        warn.setWordWrap(True)
        warn.setStyleSheet(
            f"font-size:11.5px;color:{W.T['ink2']};background:{W.T['paper2']};"
            f"border-radius:10px;padding:10px 12px;")
        lay.addWidget(warn)
        lay.addStretch(1)

        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        bl.addStretch(1)
        delete = W.GhostButton("删除")
        delete.setMinimumHeight(40)
        delete.clicked.connect(lambda: self._pick("delete"))
        bl.addWidget(delete)
        restore = W.PrimaryButton("恢复到这份")
        restore.setMinimumHeight(40)
        restore.clicked.connect(lambda: self._pick("restore"))
        bl.addWidget(restore)
        lay.addWidget(btns)
        W.center_dialog(self, parent)

    def _pick(self, action: str):
        self.action = action
        self.accept()


class BackupPage(Page):
    def build(self):
        super().build()
        if not hasattr(self, "_select_mode"):
            self._select_mode = False
            self._selected: set[str] = set()
        self.appbar("备份与回滚", "数据", back=self.app.go_back)

        # ---------------- 当前数据 ----------------
        card = W.Card()
        card.body.addWidget(label("当前数据", "sub"))
        big = QLabel(f"{len(self.store.cards)} 张卡片")
        big.setStyleSheet(f"font-size:22px;font-weight:700;color:{W.T['ink']};")
        card.body.addWidget(big)
        card.body.addWidget(label(
            f"{len(self.store.decks)} 个卡包 · 最后修改 "
            f"{backup.fmt_time(self.store.updated_at())}", "sub"))
        make = W.PrimaryButton("立即备份")
        make.clicked.connect(self._create)
        card.body.addWidget(make)
        self.add(card)

        if self._select_mode:
            tip_text = "点一行选中它，选好后点「删除选中」。只会删备份文件，当前数据不受影响。"
        else:
            tip_text = ("恢复会把这台机器的卡片数据整份换成备份里的内容；"
                        "恢复前会自动留一份「回滚前快照」。同步的账号与密钥属于本机配置，不会被覆盖。")
        tip = QLabel(tip_text)
        tip.setWordWrap(True)
        tip.setStyleSheet(f"font-size:11.5px;color:{W.T['ink2']};padding:0 4px;")
        self.add(tip)

        # ---------------- 列表 ----------------
        items = backup.list_snapshots(self.store)
        live_paths = {it["path"] for it in items}
        self._selected &= live_paths                 # 已经删掉的不再算选中
        if not items:
            self._select_mode = False

        action = W.Chip("完成" if self._select_mode else "管理")
        action.clicked.connect(self._toggle_mode)
        self.section(f"可用备份（{len(items)}）", action)

        if self._select_mode:
            self.add(self._select_bar(items))

        if not items:
            empty = W.Card(flat=True)
            empty.body.addWidget(label("还没有备份。点上面的「立即备份」先存一份。", "sub", wrap=True))
            self.add(empty)
        for it in items:
            self.add(self._row(it))

        foot = QWidget()
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 6, 0, 0)
        fl.setSpacing(8)
        open_dir = W.GhostButton("打开备份文件夹")
        open_dir.clicked.connect(self._open_dir)
        fl.addWidget(open_dir, 1)
        pick = W.GhostButton("从文件恢复…")
        pick.clicked.connect(self._pick_file)
        fl.addWidget(pick, 1)
        self.add(foot)

        where = QLabel("备份目录：" + backup.backup_dir(self.store).replace(
            os.sep, os.sep + "\u200b"))          # 在分隔符后加零宽空格，长路径也能折行
        where.setWordWrap(True)
        where.setObjectName("sub")
        where.setToolTip(backup.backup_dir(self.store))
        self.add(where)
        self.stretch()

    # ---------------- 行 ----------------
    def _row(self, it: dict) -> QWidget:
        select = self._select_mode
        picked = it["path"] in self._selected
        frame = W.ClickFrame()
        frame.setObjectName("card")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(13, 11, 13, 11)
        lay.setSpacing(10)

        if select:                                   # 选择模式：左侧一个圆圈
            mark = QLabel("✓" if picked else "")
            mark.setFixedSize(22, 22)
            mark.setAlignment(Qt.AlignCenter)
            if picked:
                mark.setStyleSheet(
                    f"background:{W.T['brand']};color:#FFFFFF;border-radius:11px;"
                    f"font-size:12px;font-weight:700;border:none;")
            else:
                mark.setStyleSheet(
                    f"background:transparent;border:1.5px solid {W.T['ink3']};"
                    f"border-radius:11px;")
            lay.addWidget(mark, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(3)
        head = QHBoxLayout()
        head.setSpacing(8)
        kind, short = KIND_PILL.get(it["kind"], ("plain", "备份"))
        title = QLabel(backup.fmt_time(it["mtime"]))
        title.setObjectName("h3")
        head.addWidget(title, 0)
        head.addWidget(W.Pill(short, kind), 0)
        head.addStretch(1)
        col.addLayout(head)

        if it["ok"]:
            sub = (f"{it['cards']} 张卡 · {it['decks']} 个卡包 · "
                   f"{backup.fmt_size(it['size'])} · {_diff_text(it['cards'], len(self.store.cards))}")
        else:
            sub = it["error"] or "无法读取"
        sl = QLabel(sub)
        sl.setObjectName("sub")
        sl.setWordWrap(True)
        col.addWidget(sl)
        lay.addLayout(col, 1)

        if not select:
            chev = QLabel("›")
            chev.setStyleSheet(f"color:{W.T['ink3']};font-size:18px;")
            lay.addWidget(chev)
        frame.setToolTip(os.path.basename(it["path"]))

        if select:
            frame.clicked.connect(lambda it=it: self._toggle_pick(it["path"]))
        else:
            frame.clicked.connect(lambda it=it: self._open(it))
        return frame

    # ---------------- 批量选择 ----------------
    def _select_bar(self, items: list[dict]) -> QWidget:
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(2, 0, 2, 2)
        bl.setSpacing(8)
        n = len(self._selected)
        pick_all = W.GhostButton("全选")
        pick_all.setMinimumHeight(34)
        pick_all.clicked.connect(self._select_all)
        bl.addWidget(pick_all, 0)
        clear = W.GhostButton("清空")
        clear.setMinimumHeight(34)
        clear.setEnabled(bool(n))
        clear.clicked.connect(self._clear_selection)
        bl.addWidget(clear, 0)
        bl.addStretch(1)
        rm = W.PrimaryButton(f"删除选中（{n}）" if n else "删除选中")
        rm.setMinimumHeight(34)
        rm.setEnabled(bool(n))
        rm.setStyleSheet(
            f"QPushButton{{background:{W.T['red_soft']};color:{W.T['red']};border:none;"
            f"border-radius:10px;font-size:12px;font-weight:700;padding:0 14px;}}"
            f"QPushButton:disabled{{background:{W.T['paper2']};color:{W.T['ink3']};}}")
        rm.clicked.connect(self._delete_selected)
        bl.addWidget(rm, 0)
        return bar

    def _toggle_mode(self):
        self._select_mode = not self._select_mode
        self._selected.clear()
        self.build()

    def _toggle_pick(self, path: str):
        if path in self._selected:
            self._selected.discard(path)
        else:
            self._selected.add(path)
        self.build()

    def _select_all(self):
        self._selected = {it["path"] for it in backup.list_snapshots(self.store)}
        self.build()

    def _clear_selection(self):
        self._selected.clear()
        self.build()

    # ---------------- 动作 ----------------
    def _open(self, it: dict):
        if not it["ok"]:
            self.app.toast(it["error"] or "这份备份读不出来")
            return
        dlg = BackupDetailDialog(it, len(self.store.cards), self)
        dlg.exec()
        if dlg.action == "restore":
            self._restore(it["path"])
        elif dlg.action == "delete":
            self._delete(it["path"])

    def _create(self):
        try:
            path = backup.create_snapshot(self.store, "backup")
        except Exception as e:
            self.app.toast(f"备份失败：{e}")
            return
        self.app.toast(f"已备份：{os.path.basename(path)}")
        self.build()

    def _restore(self, path: str):
        ok, msg = backup.restore(self.store, path)
        self.app.toast(msg)
        if ok:
            self.build()

    def _delete(self, path: str):
        name = os.path.basename(path)
        if QMessageBox.question(self, "删除备份", f"删掉「{name}」？\n删除后无法找回。") != QMessageBox.Yes:
            return
        self._delete_paths([path])

    def _delete_selected(self):
        paths = sorted(self._selected)
        if not paths:
            self.app.toast("先选中要删除的备份")
            return
        head = "\n".join(os.path.basename(p) for p in paths[:3])
        tail = f"\n…等 {len(paths)} 份" if len(paths) > 3 else ""
        text = (f"删除选中的 {len(paths)} 份备份？\n{head}{tail}\n\n"
                f"删除后无法找回；当前数据不受影响。")
        if QMessageBox.question(self, "批量删除备份", text) != QMessageBox.Yes:
            return
        self._delete_paths(paths)

    def _delete_paths(self, paths: list[str]):
        done, failed = 0, []
        for p in paths:
            ok, msg = backup.delete_snapshot(self.store, p)
            if ok:
                done += 1
                self._selected.discard(p)
            else:
                failed.append(f"{os.path.basename(p)}：{msg}")
        if failed:
            QMessageBox.warning(self, "有些没删掉", "\n".join(failed[:6]))
        self.app.toast(f"已删除 {done} 份备份" if done else "没有删除")
        self.build()

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", backup.backup_dir(self.store),
            "浮卡备份 (*.zip *.json);;所有文件 (*.*)")
        if not path:
            return
        ok, msg = backup.restore(self.store, path)
        self.app.toast(msg)
        if ok:
            self.build()

    def _open_dir(self):
        d = backup.backup_dir(self.store)
        try:
            os.startfile(d)          # Windows
        except AttributeError:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        except Exception as e:
            self.app.toast(f"打开失败：{e}")
