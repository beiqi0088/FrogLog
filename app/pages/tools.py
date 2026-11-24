# -*- coding: utf-8 -*-
"""pages/tools.py - 浮墨记录 / 批量拆卡 / 卡片模板。"""
from __future__ import annotations

import re

from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget,
                               QTextEdit, QComboBox)

import widgets as W
import card_render as CR
from core import uid, now_ms, DEFAULT_EASE
from pages.base import Page, label


# ---------------------------------------------------------------- 浮墨

class MemoPage(Page):
    def build(self):
        super().build()
        s = self.store
        self.appbar("浮墨记录", "一个框，--- 拆正反", back=self.app.go_back)

        self.text = QTextEdit()
        self.text.setPlaceholderText("记录点什么…\n\n用 --- 分隔问题与答案")
        self.text.setPlainText("降低期待的三个具体做法\n---\n1. 社交初期不抬高期待；\n2. 施恩要自薄而厚，请客要前轻后重；\n3. 把「必须」换成「希望」。")
        self.text.setMinimumHeight(170)
        self.add(self.text)

        hint = label("有 --- → 问答题；没有 → 单面笔记卡", "sub")
        self.add(hint)

        picker = QWidget()
        pl = QHBoxLayout(picker)
        pl.setContentsMargins(0, 2, 0, 0)
        pl.setSpacing(8)
        self.deck_box = QComboBox()
        for d in s.decks:
            self.deck_box.addItem(d["name"], d["id"])
        pl.addWidget(self.deck_box, 1)
        self.add(picker)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 4, 0, 0)
        rl.setSpacing(8)
        ai = W.GhostButton("✨ AI 拆题")
        ai.clicked.connect(self._ai)
        save = W.PrimaryButton("保存为卡片")
        save.clicked.connect(self._save)
        rl.addWidget(ai, 1)
        rl.addWidget(save, 2)
        self.add(row)
        self.stretch()

    def _ai(self):
        raw = self.text.toPlainText().strip()
        if "---" in raw:
            self.app.toast("已经是问答结构了")
            return
        lines = [l for l in raw.splitlines() if l.strip()]
        if len(lines) < 2:
            self.app.toast("内容太短，先多写两句")
            return
        q = lines[0].rstrip("？?")
        body = "\n".join(lines[1:])
        self.text.setPlainText(f"{q}？\n---\n{body}")
        self.app.toast("已拆成正反面（示例规则）")

    def _save(self):
        raw = self.text.toPlainText().strip()
        if not raw:
            self.app.toast("先写点内容")
            return
        if "---" in raw:
            q, a = raw.split("---", 1)
            q, a = q.strip(), a.strip()
            typ = "qa"
        else:
            q, a, typ = raw.splitlines()[0].strip(), "", "qa"
        deck_id = self.deck_box.currentData()
        deck = self.store.deck(deck_id) or {}
        groups = deck.get("groups") or ["未分组"]
        self.store.cards.append({
            "id": uid("c_"), "deck_id": deck_id, "group": groups[0], "type": typ,
            "q": q, "a": a, "options": [], "answer": [], "analysis": "",
            "tags": [], "created": now_ms(), "due": now_ms(),
            "interval": 0.0, "reps": 0, "ease": DEFAULT_EASE, "lapses": 0,
            "last_review": None, "suspended": False, "archived": False,
        })
        self.store.save()
        self.app.toast("已保存 1 张卡片")
        self.app.show_page("today")


# ---------------------------------------------------------------- 拆卡

def parse_split(text: str) -> list[dict]:
    """把粘贴文本拆成卡片：序号行 = 正面；A-D 选项 + 答案 = 选择题。"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    out = []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        lines[0] = re.sub(r"^\d+\s*[\.、\)]\s*", "", lines[0])
        q, options, answer, rest = None, [], None, []
        for l in lines:
            m = re.match(r"^([A-D])[\.、\)]\s*(.+)$", l)
            if m:
                options.append(m.group(2).strip())
                continue
            m2 = re.match(r"^答案[:：]\s*([A-D]+)", l)
            if m2:
                answer = [ord(ch) - 65 for ch in m2.group(1)]
                continue
            if l.startswith("---"):
                rest.append(l[3:].strip())
                continue
            if q is None:
                q = l
            else:
                rest.append(l)
        if not q:
            continue
        if options and answer:
            typ = "single" if len(answer) == 1 else "multi"
            out.append({"type": typ, "q": q, "a": " ".join(rest), "options": options,
                        "answer": answer, "analysis": " ".join(rest)})
        else:
            out.append({"type": "qa", "q": q, "a": " ".join(rest), "options": [],
                        "answer": [], "analysis": ""})
    return out


class SplitPage(Page):
    def build(self):
        super().build()
        self.appbar("批量拆卡", "粘贴 → 解析 → 导入", back=self.app.go_back)

        self.text = QTextEdit()
        self.text.setMinimumHeight(190)
        self.text.setPlaceholderText("1. 问题\nA. 选项\nB. 选项\n答案：AB\n\n2. 问题\n--- 答案")
        self.text.setPlainText(
            "1. 降低期待能带来哪些好处？\nA. 事情落空的概率减少\nB. 超出预期时收获惊喜\n"
            "C. 人生从此毫无欲望\nD. 更能专注可做之事\n答案：ABD\n\n"
            "2. 原文主张的期待管理方法包括哪些？\nA. 社交初期不抬高期待\nB. 一开始就全力付出\n"
            "C. 请客安排前轻后重\nD. 施恩自薄而厚\n答案：ACD\n\n"
            "3. 为什么「降低期待」不等于没有追求？\n--- 它只是把能做的做好、把无法掌控的放下。")
        self.add(self.text)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 2, 0, 0)
        rl.setSpacing(8)
        parse = W.GhostButton("解析")
        parse.clicked.connect(self._parse)
        self.import_btn = W.PrimaryButton("导入")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._import)
        rl.addWidget(parse, 1)
        rl.addWidget(self.import_btn, 1)
        self.add(row)

        self.preview = QWidget()
        self.pl = QVBoxLayout(self.preview)
        self.pl.setContentsMargins(0, 6, 0, 0)
        self.pl.setSpacing(8)
        self.add(self.preview)
        self._parsed = []
        self.stretch()

    def _parse(self):
        W.clear_layout(self.pl)
        self._parsed = parse_split(self.text.toPlainText())
        self.import_btn.setEnabled(bool(self._parsed))
        self.import_btn.setText(f"导入 {len(self._parsed)} 张")
        if not self._parsed:
            self.pl.addWidget(label("没识别到卡片，检查一下序号和「答案：」", "sub"))
            return
        for c in self._parsed:
            badge = {"qa": ("问", "qa"), "single": ("单", "single"), "multi": ("多", "multi")}[c["type"]]
            row = W.ListRow(*badge, c["q"][:34], (c["a"] or "（无答案）")[:40])
            self.pl.addWidget(row)

    def _import(self):
        s = self.store
        deck = s.decks[0]
        t = now_ms()
        for c in self._parsed:
            s.cards.append({
                "id": uid("c_"), "deck_id": deck["id"],
                "group": (deck.get("groups") or ["未分组"])[0],
                "type": c["type"], "q": c["q"], "a": c["a"],
                "options": c["options"], "answer": c["answer"],
                "analysis": c["analysis"], "tags": [], "created": t, "due": t,
                "interval": 0.0, "reps": 0, "ease": DEFAULT_EASE, "lapses": 0,
                "last_review": None, "suspended": False, "archived": False,
            })
        s.save()
        self.app.toast(f"已导入 {len(self._parsed)} 张卡片")
        self.app.show_page("today")


# ---------------------------------------------------------------- 模板

class _PreviewArea(QWidget):
    """预览区：铺模板页面底色。"""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.color))


SAMPLE = {
    "type": "qa",
    "q": "降低期待能带来哪些好处？",
    "a": "事情落空的概率会减少很多。当进展超过预期，人生反而平添一些惊喜。",
    "options": [], "answer": [], "analysis": "",
}


class TemplatesPage(Page):
    def __init__(self, app, deck_id: str | None = None):
        self.deck_id = deck_id
        self.scope = "deck" if deck_id else "all"
        self.current = None
        super().__init__(app)

    def build(self):
        super().build()
        s = self.store
        deck = s.deck(self.deck_id) if self.deck_id else None
        if self.current is None:
            self.current = (deck or {}).get("template") or s.settings.get("default_template", "sky")

        where = "全部卡包" if self.scope == "all" else f"「{deck['name']}」" if deck else "全部卡包"
        self.appbar("卡片模板", f"7 套 · 应用到{where}", back=self.app.go_back)

        # 范围
        if deck:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(7)
            for key, text in (("deck", "仅此卡包"), ("all", "全部卡包")):
                chip = W.Chip(text, on=(self.scope == key))
                chip.clicked.connect(lambda _, k=key: self._set_scope(k))
                rl.addWidget(chip)
            rl.addStretch(1)
            self.add(row)

        # 大预览
        pal = CR.palette(self.current)
        area = _PreviewArea(pal["page"])
        al = QVBoxLayout(area)
        al.setContentsMargins(14, 14, 14, 14)
        al.addWidget(CR.build_cards(SAMPLE, self.current, True, None,
                                    width=max(260, (self.width() or 430) - 68)))
        self.add(area)

        cap = label(f"预览：{pal['name']}", "sub")
        self.add(cap)

        # 模板网格
        grid_wrap = QWidget()
        outer = QVBoxLayout(grid_wrap)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(9)
        keys = list(CR.TEMPLATES.keys())
        for r in range(3):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(9)
            for c in range(3):
                i = r * 3 + c
                if i < len(keys):
                    k = keys[i]
                    tile = W.TemplateTile(k, CR.palette(k), selected=(k == self.current))
                    tile.clicked_tpl.connect(self._pick)
                    rl.addWidget(tile, 1)
                else:
                    rl.addWidget(QWidget(), 1)
            outer.addWidget(row)
        self.add(grid_wrap)

        note = label("选中即生效，复习卡片会同步换肤。", "sub")
        note.setWordWrap(True)
        self.add(note)
        self.stretch()

    def _set_scope(self, scope: str):
        self.scope = scope
        self.build()

    def _pick(self, key: str):
        s = self.store
        if self.scope == "deck" and self.deck_id:
            d = s.deck(self.deck_id)
            if d:
                d["template"] = key
        else:
            s.settings["default_template"] = key
            for d in s.decks:
                d["template"] = key
        s.save()
        self.current = key
        self.app.toast(f"已应用「{CR.palette(key)['name']}」")
        self.build()
