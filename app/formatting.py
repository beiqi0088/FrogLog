# -*- coding: utf-8 -*-
"""formatting.py - 富文本编辑（编辑器 ↔ 内联 HTML ↔ 卡片渲染）的公共工具。

移植自「浮卡」的 formatting.py：
- 卡片内容仍以「内联 HTML 字符串」存在 q / a 里，纯文本卡片完全不受影响；
- 挖空在编辑器里表现为浅绿高亮，存成 <span class="cloze">…</span>，
  渲染时按 reveal 决定「露出文字」还是「遮成空白」；
- 图片存到 <数据目录>/media/，卡片里只记 `media/文件名`，渲染时再转成绝对路径。

与浮卡的区别：浮卡用 QWebEngine + 模板 CSS 渲染，这里用 QLabel 的富文本子集，
所以下划线写成 <u>、颜色/背景写成内联 style，挖空遮罩用「同色文字 + 底色」实现。
"""
from __future__ import annotations

import hashlib
import html
import os
import re
import shutil

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QColorDialog

import core

# 挖空：编辑器里用不同浅色区分「第几组」；渲染时是「空白横线」，点开才露出原文
CLOZE_COLOR = "AAFFC7"
CLOZE_ON = "#D9F2DF"
CLOZE_PROP = QTextFormat.UserProperty + 1
CLOZE_PATTERN = re.compile(r"\{\{c\d+::(.*?)\}\}")

# 组号 → 编辑器下划线色（组 1 默认跟模板走，2/3 备用）
CLOZE_GROUP_COLORS = {1: "AAFFC7", 2: "FFE082", 3: "CFE3FF"}
# 编辑器里挖空改用「下划线」表示：载入时先打这个临时色，再按正/反面换成模板色
CLOZE_MARKER = "#1B7F5A"
CLOZE_INVISIBLE = QColor(0, 0, 0, 0)   # Qt 那条 1px 线画成透明，改由页面画 2px 主题色线
CLOZE_UNDERLINES: set[str] = set()   # 认得出的挖空下划线色（避免把普通下划线当挖空）
CLOZE_GROUP_NAMES = {1: "组1", 2: "组2", 3: "组3"}
# 渲染时的组配色：组 1 跟模板正/背面走，组 2 琥珀、组 3 靛蓝（横线, 露字）
GROUP_COLORS = {
    2: ("#E6A23C", "#B26A00"),
    3: ("#5C6BC0", "#283593"),
}
GROUP_OF_COLOR = {"#" + v.upper(): k for k, v in CLOZE_GROUP_COLORS.items()}

MASK_LINE = "#2E8B57"     # 挖空横线的默认颜色（背面海绿，正面由模板标签色覆盖）
MASK_BAR = "#E9E3D5"      # 挖空“空白块”的底色（文字同色，看不见）
MAX_GROUP = 3

FORMAT_SHORTCUTS = {
    "cloze": "Ctrl+D",
    "inkline": "Ctrl+Enter",   # 这里用 Ctrl+Enter 插 ---（保存是 Ctrl+S）
    "bold": "Ctrl+B",
    "color": "Ctrl+Shift+C",
    "bg": "Ctrl+Shift+H",
    "underline": "Ctrl+U",
    "clear": "Ctrl+Shift+0",
}

TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")

FONT_BASE_PT = 12.0   # 编辑器基准字号（≈16px），等于它就不写 font-size

MAX_IMG_W = 300      # 卡片里图片的最大显示宽度（窗口 430px 时的安全值）


# ---------------------------------------------------------------- 媒体
def media_dir() -> str:
    d = os.path.join(os.path.dirname(core.data_path()), "media")
    os.makedirs(d, exist_ok=True)
    return d


def import_media(src: str) -> str:
    """把图片复制进媒体目录，返回卡片里要存的相对路径 `media/<文件名>`。"""
    src = os.path.abspath(src)
    mdir = media_dir()
    if src.startswith(mdir + os.sep):
        return "media/" + os.path.basename(src)
    name = os.path.basename(src)
    stem, ext = os.path.splitext(name)
    dest = os.path.join(mdir, name)
    n = 2
    while os.path.exists(dest):
        try:
            if os.path.getsize(dest) == os.path.getsize(src):
                return "media/" + os.path.basename(dest)
        except OSError:
            pass
        dest = os.path.join(mdir, f"{stem}-{n}{ext}")
        n += 1
    shutil.copyfile(src, dest)
    return "media/" + os.path.basename(dest)


def _abs_src(src: str) -> str:
    if src.startswith("media/"):
        return os.path.join(os.path.dirname(core.data_path()), src.replace("/", os.sep))
    return src


def _rel_src(src: str) -> str:
    mdir = os.path.abspath(media_dir())
    p = os.path.abspath(src)
    if p.startswith(mdir + os.sep):
        return "media/" + os.path.basename(p)
    return src


def _expand_images(text: str) -> str:
    """存盘里的 media/xx.png → 绝对路径（编辑器/Qt 加载需要）。"""
    return re.sub(r'(<img[^>]*\bsrc=")([^"]+)(")',
                  lambda m: m.group(1) + _abs_src(m.group(2)) + m.group(3), text)


def _file_url(path: str) -> str:
    from PySide6.QtCore import QUrl
    return QUrl.fromLocalFile(os.path.abspath(path)).toString()


# ---------------------------------------------------------------- 编辑器 → 内联 HTML
def _group_of_format(cf) -> int:
    """认出挖空：自定义属性优先，其次看下划线色是否是「挖空色」。"""
    prop = cf.property(CLOZE_PROP)
    if isinstance(prop, int) and prop in CLOZE_GROUP_COLORS:
        return prop
    if cf.fontUnderline():
        c = cf.underlineColor()
        if c is not None and c.isValid() and c.name().upper() in CLOZE_UNDERLINES:
            return 1
    return 0


def _fragment_html(text: str, cf) -> str:
    if not text:
        return ""
    group = _group_of_format(cf)
    is_cloze = group > 0
    tags: list[str] = []
    if cf.fontWeight() >= QFont.Bold:
        tags.append("b")
    if cf.fontItalic():
        tags.append("i")
    if cf.fontUnderline() and not is_cloze:
        tags.append("u")
    styles = []
    if cf.hasProperty(QTextFormat.FontPointSize):
        pt = cf.fontPointSize()
        if pt > 0 and abs(pt - FONT_BASE_PT) > 0.01:
            styles.append(f"font-size:{pt:g}pt")
    if cf.hasProperty(QTextFormat.ForegroundBrush):
        c = cf.foreground().color()
        if c.isValid():
            styles.append("color:" + c.name())
    if not is_cloze and cf.hasProperty(QTextFormat.BackgroundBrush):
        c = cf.background().color()
        if c.isValid():
            styles.append("background-color:" + c.name())
    if styles:
        tags.append('span style="' + ";".join(styles) + '"')
    inner = html.escape(text)
    if tags:
        inner = "".join("<" + t + ">" for t in tags) + inner + \
                "".join("</" + t.split()[0] + ">" for t in reversed(tags))
    if is_cloze:
        cls = "cloze" if group == 1 else f"cloze g{group}"
        return f'<span class="{cls}">' + inner + "</span>"
    return inner


def _block_html(block) -> str:
    out = []
    it = block.begin()
    while not it.atEnd():
        frag = it.fragment()
        if frag.isValid():
            cf = frag.charFormat()
            if cf.isImageFormat():
                imgf = cf.toImageFormat()
                src = _rel_src(imgf.name()) if imgf.name() else ""
                if not src:
                    it += 1
                    continue
                w, h = int(imgf.width()), int(imgf.height())
                if w > 0 and h > 0:
                    out.append(f'<img src="{html.escape(src, quote=True)}" '
                               f'width="{w}" height="{h}">')
                else:
                    out.append(f'<img src="{html.escape(src, quote=True)}">')
            else:
                out.append(_fragment_html(frag.text().replace("\u2029", ""), cf))
        it += 1
    return "".join(out)


def editor_to_inline_html(editor) -> str:
    """QTextEdit 的富文本 → 内联 HTML；每个段落一行。"""
    doc = editor.document()
    lines = []
    b = doc.begin()
    while b.isValid():
        lines.append(_block_html(b))
        b = b.next()
    return "\n".join(lines)


def _looks_like_html(text: str) -> bool:
    return bool(TAG_RE.search(text or ""))


def _cloze_open(color: str = CLOZE_MARKER) -> str:
    """挖空的开标签：编辑器里用「下划线 + 指定颜色」表示。"""
    return (f'<span style="text-decoration:underline;'
            f'text-decoration-color:{color}">')


def _cloze_span(color: str, inner: str) -> str:
    return _cloze_open(color) + inner + "</span>"


def _recolor_clozes(editor, front: str, back: str):
    """把临时色下划线按正/反面换成模板色，并打上挖空属性。"""
    CLOZE_UNDERLINES.update({front.upper(), back.upper()})
    doc = editor.document()
    hits = []
    in_answer = False
    b = doc.begin()
    while b.isValid():
        if b.text().strip() == "---":
            in_answer = True
        color = back if in_answer else front
        it = b.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid():
                cf = frag.charFormat()
                if (cf.fontUnderline()
                        and cf.underlineColor().name().upper() == CLOZE_MARKER.upper()):
                    hits.append((frag.position(), frag.position() + frag.length(), color))
            it += 1
        b = b.next()
    for a, e, _color in hits:
        cur = QTextCursor(doc)
        cur.setPosition(a)
        cur.setPosition(e, QTextCursor.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setUnderlineColor(CLOZE_INVISIBLE)
        fmt.setProperty(CLOZE_PROP, 1)
        cur.mergeCharFormat(fmt)


def load_inline_html(editor, text: str, front: str | None = None,
                     back: str | None = None):
    """内联 HTML → QTextEdit：挖空显示成模板色下划线（不再是浅绿底）。"""
    editor.setAcceptRichText(True)
    text = (text or "").replace("<br><br>", "\n")
    if not _looks_like_html(text):
        text = "\n".join(html.escape(ln) for ln in text.split("\n"))
    text = CLOZE_PATTERN.sub(lambda m: _cloze_span(CLOZE_MARKER, m.group(1)), text)
    text = re.sub(r'<span class="cloze(?: g\d)?">', _cloze_open(CLOZE_MARKER), text)
    text = re.sub(r'<span class="([^"]*)\bmask\b[^"]*">', _cloze_open(CLOZE_MARKER), text)
    text = _expand_images(text)
    lines = text.split("\n")
    body = "".join("<p>" + ln + "</p>" if ln.strip() else "<p></p>" for ln in lines)
    editor.setHtml("<html><body>" + body + "</body></html>")
    _recolor_clozes(editor, front or MASK_LINE, back or MASK_LINE)
    cur = QTextCursor(editor.document())
    cur.setPosition(0)
    editor.setTextCursor(cur)


def split_front_back(text: str) -> tuple[str, str]:
    """按独占一行的 --- 拆正反（忽略格式标签）。"""
    text = (text or "").strip()
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if re.sub(r"<[^>]+>", "", ln).strip() == "---":
            return "\n".join(lines[:i]).strip(), "\n".join(lines[i + 1:]).strip()
    return "", text


# ---------------------------------------------------------------- 渲染
def _mask_key(inner: str) -> str:
    """用被挖空的原文算一个稳定 key：点一下只揭这一个空。"""
    return hashlib.md5(inner.encode("utf-8")).hexdigest()[:8]


def _img_html(tag: str) -> str:
    """<img> → 绝对 file:// 地址，并把尺寸夹到卡片宽度内（按原比例）。

    QLabel 的富文本对 width/height 属性就够用，不加 max-width（会被算成全宽而变形）。
    """
    m = re.search(r'\bsrc="([^"]+)"', tag)
    if not m:
        return tag
    path = _abs_src(m.group(1))
    if not os.path.isabs(path) or not os.path.exists(path):
        return tag
    url = _file_url(path)
    mw = re.search(r'\bwidth="(\d+)"', tag)
    mh = re.search(r'\bheight="(\d+)"', tag)
    if mw and mh and int(mw.group(1)) > 0 and int(mh.group(1)) > 0:
        w, h = int(mw.group(1)), int(mh.group(1))
    else:
        from PySide6.QtGui import QImage
        im = QImage(path)
        if im.isNull():
            return f'<img src="{url}">'
        w, h = im.width(), im.height()
    if w > MAX_IMG_W:
        h = max(1, round(h * MAX_IMG_W / w))
        w = MAX_IMG_W
    return f'<img src="{url}" width="{w}" height="{h}">'


def to_rich(text: str, shown=None, link: bool = False,
            mask_color: str = MASK_LINE, hovered: str | None = None,
            fg: str = "#2b3a3c", hidden: str | None = None,
            groups: dict | None = None) -> str:
    """卡片文本 → 富文本 HTML。

    挖空平时字看不见（颜色 = 卡片底色，横线由 MaskText 按组上色），
    鼠标移上去露出原文（hovered=那个 mask 的 key），点一下才固定显示（shown 集合）。
    groups: {组号: (横线色, 露字色)}，不传时组 1 用 mask_color/fg、组 2/3 用内置琥珀/靛蓝。
    `hidden` 不传时退化成浅色块（QLabel 路径用，没有点击交互）。
    """
    text = (text or "").replace("\r\n", "\n")
    if not text:
        return ""
    text = CLOZE_PATTERN.sub(lambda m: '<span class="cloze">' + m.group(1) + "</span>", text)
    text = re.sub(r'<span class="([^"]*)\bmask\b[^"]*">', '<span class="cloze">', text)
    shown = set(shown or ())

    def _colors(group: int) -> tuple[str, str]:
        if groups and group in groups:
            return groups[group]
        if group == 1:
            return mask_color, fg
        return GROUP_COLORS.get(group, (mask_color, fg))

    def _mask(m):
        inner = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
        group = int(m.group(1) or 1) if m.lastindex and m.lastindex >= 2 else 1
        line, hover = _colors(group)
        key = _mask_key(inner)
        # 挖空一律按「加粗」排版：露出/盖回只换颜色，字宽不变、不重排、不抖
        if key in shown or key == hovered:
            style = f"color:{hover};font-weight:700;text-decoration:none"
        elif hidden:
            style = f"color:{hidden};font-weight:700;text-decoration:none"
        else:
            style = f"background-color:{MASK_BAR};color:{MASK_BAR};font-weight:700;text-decoration:none"
        tag = "a" if link else "span"
        href = f' href="mask:{key}"' if link else ""
        return f'<{tag}{href} style="{style}">{inner}</{tag}>'

    text = re.sub(r'<span class="cloze(?: g(\d))?">(.*?)</span>', _mask, text, flags=re.S)

    out = []
    for part in re.split(r"(<[^>]+>)", text):
        if not part:
            continue
        if part.startswith("<"):
            low = part.lower()
            if low.startswith("<img"):
                out.append(_img_html(part))
            else:
                out.append(part)
        else:
            out.append(html.escape(part))
    return "".join(out)


def has_cloze(text: str) -> bool:
    t = text or ""
    return bool(re.search(r'class="cloze|class="[^"]*\bmask\b|{{c\d+::', t))


def _normalize_clozes(text: str) -> str:
    t = (text or "").replace("\r\n", "\n")
    t = CLOZE_PATTERN.sub(lambda m: '<span class="cloze">' + m.group(1) + "</span>", t)
    return re.sub(r'<span class="([^"]*)\bmask\b[^"]*">', '<span class="cloze">', t)


def mask_infos(text: str) -> list[tuple[str, str, int]]:
    """[(key, 原文, 组号)]：按出现顺序列出所有挖空。"""
    t = _normalize_clozes(text)
    out = []
    for m in re.finditer(r'<span class="cloze(?: g(\d))?">(.*?)</span>', t, re.S):
        inner = m.group(2)
        out.append((_mask_key(inner), inner, int(m.group(1) or 1)))
    return out


def mask_keys(text: str) -> list[str]:
    return [k for k, _, _ in mask_infos(text)]


def to_rich_blocks(text: str, shown=None, hovered: str | None = None, link: bool = True,
                   mask_color: str = MASK_LINE, fg: str = "#2b3a3c",
                   para_gap: int = 10, hidden: str | None = None,
                   groups: dict | None = None, line_px: int | None = None) -> str:
    """一行一段（<p> 带段间距和行高），给带挖空的卡片正文用。"""
    lines = [ln for ln in (text or "").replace("\r\n", "\n").split("\n") if ln.strip()]
    lh = f"line-height:{line_px}px;" if line_px else ""
    return "".join(
        f'<p style="margin:0 0 {para_gap}px 0;{lh}">'
        f'{to_rich(ln, shown=shown, link=link, mask_color=mask_color, hovered=hovered, fg=fg, hidden=hidden, groups=groups)}'
        f'</p>'
        for ln in lines)


def has_rich(text: str) -> bool:
    return _looks_like_html(text or "")


def to_plain(text: str) -> str:
    """卡片文本 → 纯文本（列表/搜索预览用）：去掉标签、图片变 [图片]、挖空露出原字。"""
    t = (text or "")
    t = CLOZE_PATTERN.sub(lambda m: m.group(1), t)
    t = re.sub(r'<span class="cloze">(.*?)</span>', r"\1", t, flags=re.S)
    t = re.sub(r"<img[^>]*>", "[图片]", t, flags=re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</p\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).strip()


# ---------------------------------------------------------------- 格式操作
def _merge_format(editor, fmt: QTextCharFormat):
    cursor = editor.textCursor()
    cursor.mergeCharFormat(fmt)
    editor.mergeCurrentCharFormat(fmt)


def _need_selection(editor, notify, msg: str) -> bool:
    if not editor.textCursor().hasSelection():
        if notify:
            notify(msg)
        return False
    return True


def apply_cloze(editor, notify=None, group: int = 1, line_color: str | None = None):
    """挖空：编辑器里显示成「模板色下划线」，存成 <span class="cloze">。"""
    if not _need_selection(editor, notify, "请先选中要挖空的文字"):
        return
    fmt = QTextCharFormat()
    fmt.setFontUnderline(True)
    fmt.setUnderlineColor(CLOZE_INVISIBLE)
    fmt.setProperty(CLOZE_PROP, 1)
    _merge_format(editor, fmt)
    if notify:
        notify("已挖空 ✓")


def apply_bold(editor, notify=None):
    fmt = QTextCharFormat()
    fmt.setFontWeight(QFont.Bold if editor.fontWeight() != QFont.Bold else QFont.Normal)
    _merge_format(editor, fmt)


def apply_underline(editor, notify=None):
    fmt = QTextCharFormat()
    fmt.setFontUnderline(not editor.fontUnderline())
    _merge_format(editor, fmt)


def apply_italic(editor, notify=None):
    fmt = QTextCharFormat()
    fmt.setFontItalic(not editor.fontItalic())
    _merge_format(editor, fmt)


def apply_color(editor, notify=None):
    if not _need_selection(editor, notify, "请先选中要上色的文字"):
        return
    color = QColorDialog.getColor(QColor("#26211A"), editor, "选择字体颜色")
    if color.isValid():
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        _merge_format(editor, fmt)


def apply_bg(editor, notify=None):
    if not _need_selection(editor, notify, "请先选中要加背景的文字"):
        return
    color = QColorDialog.getColor(QColor("#FDEDE2"), editor, "选择文字背景色")
    if color.isValid():
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        _merge_format(editor, fmt)


def apply_clear(editor, notify=None):
    """清除选中文字的全部格式（图片保留）。"""
    if not _need_selection(editor, notify, "请先选中要清除格式的文字"):
        return
    cursor = editor.textCursor()
    doc = editor.document()
    start, end = cursor.selectionStart(), cursor.selectionEnd()
    ranges = []
    block = doc.findBlock(start)
    while block.isValid() and block.position() < end:
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid() and not frag.charFormat().isImageFormat():
                fstart, fend = frag.position(), frag.position() + frag.length()
                if fstart < end and fend > start:
                    ranges.append((max(fstart, start), min(fend, end)))
            it += 1
        block = block.next()
    for a, b in ranges:
        c = QTextCursor(doc)
        c.setPosition(a)
        c.setPosition(b, QTextCursor.KeepAnchor)
        c.setCharFormat(QTextCharFormat())
    editor.setTextCursor(cursor)
    if notify:
        notify("已清除格式 ✓")
