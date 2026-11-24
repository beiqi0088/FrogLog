# -*- coding: utf-8 -*-
"""pages/sync.py - 同步（Anki 风格：状态 + 一个大同步按钮 + 强制上传/下载）。"""
from __future__ import annotations

import copy
import threading
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, QWidget, QDialog,
                               QLineEdit, QPushButton, QProgressBar)

import widgets as W
import sync as S
from pages.base import Page, label


def sync_cfg(store) -> dict:
    settings = store.state.setdefault("settings", {})
    cfg = settings.setdefault("sync", {})
    cfg.setdefault("provider", "lan")
    cfg.setdefault("lan", {"url": "", "token": ""})
    cfg.setdefault("webdav", {"url": "", "user": "", "password": ""})
    cfg.setdefault("s3", {"endpoint": "", "region": "us-east-1", "bucket": "",
                          "key": "flocard/state.json", "access": "", "secret": "",
                          "path_style": True})
    return cfg


class SyncBadge(QWidget):
    """圆形同步图标。"""

    def __init__(self, size: int = 52, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(W.T["brand_soft"]))
        p.drawEllipse(0, 0, w, h)
        pen = QPen(QColor(W.T["brand"]), 2.2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        r = w * 0.24
        cx, cy = w / 2, h / 2
        from PySide6.QtCore import QRectF as _R
        box = _R(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(box, 40 * 16, 140 * 16)
        p.drawArc(box, 220 * 16, 140 * 16)
        # 箭头
        p.setBrush(QColor(W.T["brand"]))
        path = QPainterPath()
        ax, ay = cx + r * 0.86, cy - r * 0.55
        path.moveTo(ax, ay - 4)
        path.lineTo(ax + 5, ay + 1)
        path.lineTo(ax - 4, ay + 3)
        path.closeSubpath()
        p.drawPath(path)


class SyncConflictDialog(QDialog):
    """本地与云端都有改动时，让用户选同步方向。"""

    def __init__(self, local_at: int, remote_at: int,
                 local_cards: int = 0, remote_cards: int = 0, parent=None):
        super().__init__(parent)
        self.choice = None
        self.setWindowTitle("同步冲突")
        self.resize(400, 320)
        self.setStyleSheet(f"QDialog{{background:{W.T['paper']};}}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        t = QLabel("同步冲突")
        t.setStyleSheet(f"font-size:17px;font-weight:700;color:{W.T['ink']};")
        lay.addWidget(t)
        sub = QLabel("本地和云端都有新的修改，选一个方向同步")
        sub.setObjectName("sub")
        lay.addWidget(sub)

        # 两张卡
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        for name, at, n, side in (("本地", local_at, local_cards, "local"),
                                  ("云端", remote_at, remote_cards, "cloud")):
            card = W.Card(flat=True)
            card.body.setContentsMargins(14, 12, 14, 12)
            card.body.setSpacing(3)
            cap = QLabel(name)
            cap.setObjectName("sub")
            card.body.addWidget(cap)
            big = QLabel(S.fmt_ts(at))
            big.setStyleSheet(f"font-size:16px;font-weight:700;color:{W.T['ink']};")
            card.body.addWidget(big)
            ago = QLabel((f"{n} 张卡片 · " if n else "") + self._ago(at))
            ago.setStyleSheet(f"font-size:11px;color:{W.T['ink3']};")
            card.body.addWidget(ago)
            rl.addWidget(card, 1)
        lay.addWidget(row)

        # 提醒
        tip = QLabel("选择后另一边会被覆盖；被覆盖的一方会先备份到 state.json.bak")
        tip.setWordWrap(True)
        tip.setStyleSheet(
            f"font-size:11.5px;color:{W.T['ink2']};background:{W.T['paper2']};"
            f"border-radius:10px;padding:10px 12px;")
        lay.addWidget(tip)
        lay.addStretch(1)

        # 按钮
        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        cancel = QPushButton("取消")
        cancel.setFixedHeight(40)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(
            f"QPushButton{{background:transparent;color:{W.T['ink2']};border:none;"
            f"font-size:12.5px;}}")
        cancel.clicked.connect(self.reject)
        bl.addWidget(cancel)
        bl.addStretch(1)

        down = QPushButton("下载云端")
        down.setFixedHeight(40)
        down.setCursor(Qt.PointingHandCursor)
        down.setStyleSheet(
            f"QPushButton{{background:{W.T['brand_soft']};color:{W.T['brand']};border:none;"
            f"border-radius:12px;font-size:12.5px;font-weight:600;padding:0 16px;}}")
        down.clicked.connect(lambda: self._pick("pull"))
        bl.addWidget(down)

        up = QPushButton("上传本地")
        up.setFixedHeight(40)
        up.setCursor(Qt.PointingHandCursor)
        up.setStyleSheet(
            f"QPushButton{{background:{W.T['brand_soft']};color:{W.T['brand']};border:none;"
            f"border-radius:12px;font-size:12.5px;font-weight:600;padding:0 16px;}}")
        up.clicked.connect(lambda: self._pick("push"))
        bl.addWidget(up)
        lay.addWidget(btns)
        W.center_dialog(self, parent)

    def _pick(self, mode: str):
        self.choice = mode
        self.accept()

    @staticmethod
    def _ago(ms: int) -> str:
        if not ms:
            return "—"
        mins = max(0, int((time.time() * 1000 - ms) / 60000))
        if mins < 1:
            return "刚刚修改"
        if mins < 60:
            return f"{mins} 分钟前修改"
        if mins < 1440:
            return f"{mins // 60} 小时前修改"
        return f"{mins // 1440} 天前修改"


class SyncPage(Page):
    def build(self):
        super().build()
        self.cfg = sync_cfg(self.store)
        self._job = None
        self._job_result = None
        self._test_job = None
        self._test_result = None
        self._alt_buttons = []
        self.appbar("同步", None, back=self.app.go_back)

        # ---------------- 状态区 ----------------
        card = W.Card()
        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(0, 6, 0, 2)
        hl.setSpacing(8)
        hl.addWidget(SyncBadge(54), 0, Qt.AlignHCenter)

        self.status = QLabel(self._status_text())
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(f"font-size:16px;font-weight:700;color:{W.T['ink']};")
        hl.addWidget(self.status)

        sub = QLabel(self._sub_text())
        sub.setAlignment(Qt.AlignCenter)
        sub.setObjectName("sub")
        hl.addWidget(sub)
        card.body.addWidget(head)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        self.bar.setStyleSheet(
            f"QProgressBar{{background:{W.T['paper2']};border:none;border-radius:2px;}}"
            f"QProgressBar::chunk{{background:{W.T['brand']};border-radius:2px;}}")
        self.bar.hide()
        card.body.addWidget(self.bar)

        self.primary = QPushButton("同步")
        self.primary.setFixedHeight(44)
        self.primary.setCursor(Qt.PointingHandCursor)
        self.primary.setStyleSheet(
            f"QPushButton{{background:{W.T['brand']};color:#FFFFFF;border:none;"
            f"border-radius:14px;font-size:14px;font-weight:700;}}")
        self.primary.clicked.connect(lambda: self._run("auto"))
        card.body.addWidget(self.primary)

        alt = QWidget()
        al = QHBoxLayout(alt)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(18)
        for text, mode in (("上传到远端", "push"), ("从远端下载", "pull")):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:transparent;border:none;font-size:11.5px;"
                f"color:{W.T['ink2']};}}")
            b.clicked.connect(lambda _, m=mode: self._run(m))
            al.addWidget(b, 1)
            self._alt_buttons.append(b)
        card.body.addWidget(alt)
        self.add(card)

        # ---------------- 通道 ----------------
        seg = QWidget()
        seg.setObjectName("segSync")
        seg.setStyleSheet(f"QWidget#segSync{{background:{W.T['paper2']};border-radius:16px;}}")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(3)
        for key, name in (("lan", "局域网"), ("webdav", "WebDAV"), ("s3", "S3 存储")):
            b = W.Chip(name, on=(self.cfg["provider"] == key))
            b.clicked.connect(lambda _, k=key: self._set_provider(k))
            sl.addWidget(b, 1)
        self.add(seg)

        prov = self.cfg["provider"]
        form = W.Card()
        if prov == "lan":
            self._form_lan(form)
        elif prov == "webdav":
            self._form_webdav(form)
        else:
            self._form_s3(form)
        self.add(form)

        test = W.GhostButton("测试连接")
        test.clicked.connect(self._test)
        self.add(test)

        self.result_lbl = QLabel("")
        self.result_lbl.setObjectName("sub")
        self.result_lbl.setWordWrap(True)
        self.result_lbl.setAlignment(Qt.AlignCenter)
        self.result_lbl.hide()
        self.add(self.result_lbl)

        if prov == "lan":
            self.add(self._share_card())
        self.stretch()

    # ---------------- 文案 ----------------
    def _last_sync(self) -> int:
        return int(((self.store.state.get("settings") or {}).get("last_sync") or 0))

    def _status_text(self) -> str:
        last = self._last_sync()
        st = self.store.state.get("settings") or {}
        done_prov = st.get("last_sync_provider") or ""
        cur_prov = (self.cfg or {}).get("provider") or "lan"
        if last and done_prov and done_prov != cur_prov:
            return "当前通道还没同步过"      # 别把别的通道的同步结果显示在这里
        if not last:
            return "尚未同步"
        mins = max(0, int((time.time() * 1000 - last) / 60000))
        if mins < 1:
            return "刚刚同步过"
        if mins < 60:
            return f"{mins} 分钟前同步"
        if mins < 1440:
            return f"{mins // 60} 小时前同步"
        return f"{mins // 1440} 天前同步"

    def _sub_text(self) -> str:
        return f"本地版本 {S.fmt_ts(self.store.updated_at())}"

    # ---------------- 执行 ----------------
    def _run(self, mode: str):
        if self._job and self._job.is_alive():
            return
        mode = "auto" if mode in ("", "both", "sync") else mode
        self.primary.setEnabled(False)
        self.primary.setText("同步中…")
        for b in self._alt_buttons:
            b.setEnabled(False)
        self.bar.show()
        self.status.setText("正在同步")
        self._job_result = None
        cfg = copy.deepcopy(self.cfg)      # 快照：线程里用，主线程同时改也不影响
        store = self.store

        def work():
            try:
                msg = S.do_sync(store, cfg, mode)
                self._job_result = ("ok", msg, None)
            except Exception as e:
                self._job_result = ("err", str(e), e)

        self._job = threading.Thread(target=work, daemon=True)
        self._job.start()
        QTimer.singleShot(150, self._poll)

    def _reset_buttons(self):
        self.bar.hide()
        self.primary.setEnabled(True)
        self.primary.setText("同步")
        for b in self._alt_buttons:
            b.setEnabled(True)

    def _poll(self):
        if self._job and self._job.is_alive():
            QTimer.singleShot(150, self._poll)
            return
        kind, msg, exc = self._job_result or ("err", "未知错误", None)
        self._reset_buttons()
        if kind == "ok":
            self.app.toast(msg)
            self.build()
            return
        # 两边都有改动：走和「设置 → 同步」一样的冲突弹窗
        if isinstance(exc, S.SyncConflict):
            choice = self.app._ask_sync_conflict(exc)
            if not choice:
                self.app.toast("已取消同步")
                return
            self._run(choice)
            return
        self.status.setText("同步失败")
        self._show_result(False, f"同步失败：{msg}")
        self.app.toast(f"同步失败：{msg}")
        QTimer.singleShot(1200, self.build)

    def _test(self):
        if self._test_job and self._test_job.is_alive():
            return
        self._test_result = None
        cfg = copy.deepcopy(self.cfg)

        def work():
            try:
                self._test_result = ("ok", S.client_from(cfg).test())
            except Exception as e:
                self._test_result = ("err", str(e))

        self._test_job = threading.Thread(target=work, daemon=True)
        self._test_job.start()
        QTimer.singleShot(150, self._poll_test)

    def _poll_test(self):
        if self._test_job and self._test_job.is_alive():
            QTimer.singleShot(150, self._poll_test)
            return
        kind, msg = self._test_result or ("err", "未知错误")
        self._show_result(kind == "ok", msg if kind == "ok" else f"连接失败：{msg}")
        self.app.toast(msg if kind == "ok" else f"连接失败：{msg}")

    def _show_result(self, good: bool, text: str):
        """把结果写进页面（toast 一闪而过，排障时看不全）。"""
        lbl = getattr(self, "result_lbl", None)
        if lbl is None:
            return
        lbl.setText(text)
        lbl.setStyleSheet(
            f"color:{W.T['brand'] if good else W.T['red']};"
            f"font-size:11.5px;font-weight:600;")
        lbl.show()

    # ---------------- 表单 ----------------
    SECRET_FIELDS = ("access", "secret")
    QINIU_KEY_LEN = 40

    def _field(self, parent, title, holder, key, placeholder="", password=False):
        t = QLabel(title)
        t.setObjectName("sub")
        parent.addWidget(t)
        box = QLineEdit()
        box.setPlaceholderText(placeholder)
        box.setText(str(holder.get(key) or ""))
        if password:
            box.setEchoMode(QLineEdit.Password)

        def commit():
            raw = box.text()
            if key in self.SECRET_FIELDS:
                # 清掉粘贴带进来的空白/零宽字符/引号，并把结果回显
                val = S.clean_cred(raw)
                if val != raw:
                    box.setText(val)
            else:
                val = raw.strip()
            holder[key] = val
            self.store.save()
            self._warn_key(key, val)

        box.editingFinished.connect(commit)
        parent.addWidget(box)
        return box

    def _warn_key(self, key: str, val: str):
        """七牛密钥固定 40 位，长度不对基本就是没复制全，当场提示。"""
        if key not in self.SECRET_FIELDS or not val:
            return
        s3 = self.cfg.get("s3") or {}
        if "qiniucs.com" not in str(s3.get("endpoint") or ""):
            return
        if len(val) != self.QINIU_KEY_LEN:
            name = "Access Key" if key == "access" else "Secret Key"
            self.app.toast(f"{name} 只有 {len(val)} 位，七牛是 "
                           f"{self.QINIU_KEY_LEN} 位，多半没复制完整 → "
                           f"到「密钥管理」重新复制整行")

    def _form_lan(self, card):
        col = card.body
        self._field(col, "对方设备地址", self.cfg["lan"], "url",
                    "http://192.168.3.140:8765")
        self._field(col, "同步口令", self.cfg["lan"], "token", "两台设备要一致")

    def _form_webdav(self, card):
        col = card.body
        self._field(col, "地址（目录或完整文件路径）", self.cfg["webdav"], "url",
                    "https://dav.jianguoyun.com/dav/")
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        left = QVBoxLayout()
        self._field(left, "账号", self.cfg["webdav"], "user")
        right = QVBoxLayout()
        self._field(right, "密码", self.cfg["webdav"], "password", password=True)
        rl.addLayout(left, 1)
        rl.addLayout(right, 1)
        col.addWidget(row)
        tip = QLabel("坚果云：地址填 https://dav.jianguoyun.com/dav/ 即可，"
                     "会自动创建 flocard/state.json；密码用「应用密码」，不是登录密码。")
        tip.setObjectName("sub")
        tip.setWordWrap(True)
        col.addWidget(tip)

    def _form_s3(self, card):
        col = card.body
        self._field(col, "Endpoint", self.cfg["s3"], "endpoint",
                    "https://s3.cn-east-1.qiniucs.com")
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        a = QVBoxLayout()
        self._field(a, "Region", self.cfg["s3"], "region",
                    "cn-east-1（留空则按 Endpoint 自动识别）")
        b = QVBoxLayout()
        self._field(b, "Bucket", self.cfg["s3"], "bucket", "my-bucket")
        rl.addLayout(a, 1)
        rl.addLayout(b, 1)
        col.addWidget(row)
        self._field(col, "对象 Key", self.cfg["s3"], "key", "flocard/state.json")
        row2 = QWidget()
        rl2 = QHBoxLayout(row2)
        rl2.setContentsMargins(0, 0, 0, 0)
        rl2.setSpacing(8)
        c = QVBoxLayout()
        self._field(c, "Access Key", self.cfg["s3"], "access")
        d = QVBoxLayout()
        self._field(d, "Secret Key", self.cfg["s3"], "secret", password=True)
        rl2.addLayout(c, 1)
        rl2.addLayout(d, 1)
        col.addWidget(row2)
        tip = QLabel("七牛云：Endpoint 填 s3.<区域>.qiniucs.com（如 s3.cn-south-1.qiniucs.com），"
                     "Bucket 填空间名，对象 Key 只写 state.json 就行。"
                     "Access Key / Secret Key 在「七牛控制台 → 密钥管理」，两个都是 40 位，"
                     "复制时要选全整行。")
        tip.setObjectName("sub")
        tip.setWordWrap(True)
        col.addWidget(tip)

    def _set_provider(self, key: str):
        self.cfg["provider"] = key
        self.store.save()
        self.build()

    # ---------------- 局域网共享 ----------------
    def _share_card(self):
        card = W.Card()
        card.body.addWidget(label("本机共享（让另一台设备连过来）", "sub"))
        token = self.cfg["lan"].get("token") or ""
        box = QLineEdit()
        box.setPlaceholderText("同步口令（建议点右侧生成）")
        box.setText(token)

        def commit():
            self.cfg["lan"]["token"] = box.text().strip()
            self.store.save()

        box.editingFinished.connect(commit)
        card.body.addWidget(box)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        gen = W.GhostButton("生成口令")
        gen.clicked.connect(lambda: self._gen_token(box))
        rl.addWidget(gen, 1)
        started = getattr(self.app, "lan_server", None) is not None
        toggle = W.PrimaryButton("停止共享" if started else "开启共享")
        toggle.clicked.connect(self._toggle_share)
        rl.addWidget(toggle, 1)
        card.body.addWidget(row)

        if started:
            url = self.app.lan_server.url()
            show = QLineEdit(url)
            show.setReadOnly(True)
            card.body.addWidget(show)
            tip = QLabel(f"在另一台设备的「局域网」里填：{url}")
            tip.setObjectName("sub")
            tip.setWordWrap(True)
            card.body.addWidget(tip)
        return card

    def _gen_token(self, box: QLineEdit):
        import secrets
        tok = secrets.token_hex(4)
        box.setText(tok)
        self.cfg["lan"]["token"] = tok
        self.store.save()

    def _toggle_share(self):
        srv = getattr(self.app, "lan_server", None)
        if srv:
            srv.stop()
            self.app.lan_server = None
            self.app.toast("已停止共享")
            self.build()
            return
        import secrets
        token = self.cfg["lan"].get("token") or secrets.token_hex(4)
        self.cfg["lan"]["token"] = token
        self.store.save()
        srv = S.LanServer(self.store, token, 8765)
        try:
            url = srv.start()
        except OSError as e:
            self.app.toast(f"端口 8765 被占用：{e}")
            return
        self.app.lan_server = srv
        self.app.toast(f"已开启共享：{url}")
        self.build()
