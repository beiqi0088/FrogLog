# -*- coding: utf-8 -*-
"""
docx_import.py - 导入 Word（.docx）生成卡组。

规则：
  · 文档第一行 = 卡组名称
  · 以「001、问题」这种序号行开新卡（支持 1. / 1、/ 001、）
  · 紧跟 A. / B. / C. … 选项 + 「答案：ABD」→ 单选/多选，解析取「解析：…」
  · 没有选项的 → 问答题，问号后的段落全部作为答案

只用标准库（zipfile + ElementTree）读 document.xml，不依赖 python-docx。
"""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

NUM_RE = re.compile(r"^\s*(\d{1,4})\s*[、.．]\s*(.+)$")
OPT_RE = re.compile(r"^\s*([A-Ga-g])\s*[、.．]\s*(.+)$")
ANS_RE = re.compile(r"^\s*答案\s*[:：]\s*([A-Ga-g][A-Ga-g、,，\s]*)$")
ANA_RE = re.compile(r"^\s*解析\s*[:：]\s*(.*)$")


def extract_paragraphs(path: str) -> list[str]:
    """按文档顺序取出所有非空段落文本。"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(f"{W}body")
    out: list[str] = []
    if body is None:
        return out
    for p in body.iter(f"{W}p"):
        parts = []
        for node in p.iter():
            if node.tag == f"{W}t":
                parts.append(node.text or "")
            elif node.tag == f"{W}tab":
                parts.append("\t")
            elif node.tag in (f"{W}br", f"{W}cr"):
                parts.append("\n")
        line = "".join(parts).strip()
        if line:
            out.append(line)
    return out


def _finish(cur: dict) -> dict:
    opts = [o.strip() for o in cur["options"] if o.strip()]
    ans = cur["answer"]
    text = [t for t in cur["text"] if t.strip()]
    analysis = " ".join(x for x in cur["analysis"] if x.strip()).strip()

    if opts and ans:
        typ = "single" if len(ans) == 1 else "multi"
        return {
            "type": typ,
            "q": cur["q"],
            "a": " ".join(text).strip(),
            "options": opts,
            "answer": sorted(set(ans)),
            "analysis": analysis,
        }
    # 问答：正文按段落保留（空行分隔），渲染时再转成 <br>
    body = "\n\n".join(t.strip() for t in text if t.strip())
    if analysis:
        body = (body + "\n" + analysis).strip() if body else analysis
    return {"type": "qa", "q": cur["q"], "a": body, "options": [], "answer": [],
            "analysis": ""}


def parse_docx(path: str) -> tuple[str, list[dict]]:
    """返回 (卡组名, 卡片列表)。"""
    lines = extract_paragraphs(path)
    if not lines:
        return "", []

    title = lines[0].strip()
    cards: list[dict] = []
    cur: dict | None = None

    for ln in lines[1:]:
        m = NUM_RE.match(ln)
        if m and (cur is None or cur["options"] or cur["text"] or cur["answer"] is not None):
            if cur:
                cards.append(_finish(cur))
            cur = {"q": m.group(2).strip(), "options": [], "answer": None,
                   "analysis": [], "text": []}
            continue
        if m and cur is not None and not cur["options"] and not cur["text"]:
            # 题干里的「1. xxx」被误判：并回题干
            cur["q"] += " " + m.group(2).strip()
            continue
        if cur is None:
            continue

        mo = OPT_RE.match(ln)
        if mo and cur["answer"] is None and len(cur["options"]) < 8:
            cur["options"].append(mo.group(2).strip())
            continue
        ma = ANS_RE.match(ln)
        if ma:
            cur["answer"] = [ord(ch.upper()) - 65 for ch in ma.group(1) if ch.isalpha()]
            continue
        mz = ANA_RE.match(ln)
        if mz:
            cur["analysis"].append(mz.group(1).strip())
            continue
        if cur["answer"] is not None:
            cur["analysis"].append(ln)          # 解析续行
        elif cur["options"]:
            cur["options"][-1] += ln            # 选项折行，并回上一项
        else:
            cur["text"].append(ln)

    if cur:
        cards.append(_finish(cur))
    cards = [c for c in cards if c["q"] and (c["a"] or c["options"])]
    return title, cards
