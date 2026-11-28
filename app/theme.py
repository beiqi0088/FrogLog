# -*- coding: utf-8 -*-
"""
theme.py - 设计令牌 + 全局 QSS
7 套纸感主题（极光/冰川/薄荷/香檟/丁香/珊瑚/潟湖）：每套都有独立的浅纸底、
卡片、文字、边框和点缀配色。纯色、无渐变、无深色顶带 / 底栏。
"""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter


LIGHT = {
    "paper":   "#F3EEDF",
    "paper2":  "#E9E1CB",
    "page":    "#F3EEDF",
    "panel":   "#FBF6EA",
    "ink":     "#2A2519",
    "ink2":    "#8A8066",
    "ink3":    "#B7AD94",
    "line":    "#E0D6BE",
    "brand":   "#B23A5B",
    "brand2":  "#8E2946",
    "brand_soft": "#F3DDE4",
    "deep":    "#B23A5B",
    "accent":  "#D9A441",
    "accent_soft": "#F6E8C5",
    "butter":  "#D9A441",
    "butter_soft": "#F6E8C5",
    "green":   "#3E7A52",
    "green_soft": "#DDEBDF",
    "red":     "#B85A3A",
    "red_soft": "#F5DECF",
    "blue":    "#3E6482",
    "blue_soft": "#DCE6F0",
    "shadow":  "rgba(42,37,25,0.10)",
}

DARK = {
    "paper":   "#161A17",
    "paper2":  "#20251F",
    "panel":   "#1E241F",
    "ink":     "#F0F1EA",
    "ink2":    "#B7BDB5",
    "ink3":    "#7C857D",
    "line":    "#333B34",
    "brand":   "#91C89C",
    "brand2":  "#274B31",
    "brand_soft": "#22301F",
    "accent":  "#F2A17F",
    "accent_soft": "#3A241A",
    "green":   "#7FD3A6",
    "green_soft": "#1C3327",
    "red":     "#FF8A75",
    "red_soft": "#3A211E",
    "blue":    "#8FB6CE",
    "blue_soft": "#22303A",
    "shadow":  "rgba(0,0,0,0.45)",
}

# 7 套卡片皮肤（来自浮卡 templates_data.json 的主色）
TEMPLATES = {
    "sky":    {"name": "天蓝薰衣", "note": "天蓝底 · 薰衣草粉", "bg": "#B3E5FC", "fg": "#263238", "label": "#E91E63"},
    "glass":  {"name": "弥散雾影", "note": "渐变底 · 毛玻璃",   "bg": "#F0EEF8", "fg": "#333333", "label": "#5C6BC0"},
    "sunset": {"name": "淡粉紫橙", "note": "淡粉底 · 靛蓝橙",   "bg": "#FFE5F1", "fg": "#263238", "label": "#E65100"},
    "candy":  {"name": "粉彩撞色", "note": "粉丝带 · 薄荷绿",   "bg": "#FFF0F8", "fg": "#8A0051", "label": "#FF69B4"},
    "lime":   {"name": "绿韵黄调", "note": "薄荷青 · 极淡黄",   "bg": "#D1F2EB", "fg": "#263238", "label": "#43A047"},
    "bean":   {"name": "豆沙绿语", "note": "豆沙绿 · 书签蓝",   "bg": "#C7EDCC", "fg": "#2D4B4B", "label": "#4F8F9D"},
    "mint":   {"name": "青柠薄荷", "note": "青柠底 · 青绿字",   "bg": "#C7ECEE", "fg": "#263238", "label": "#079992"},
}

FONT = "Microsoft YaHei UI"


def set_font(name: str):
    global FONT
    FONT = name


DOMAINS = {
    "study": {"name": "学习", "emoji": "📚", "color": "#2F6A43"},
    "work":  {"name": "工作", "emoji": "💼", "color": "#426A80"},
    "life":  {"name": "生活", "emoji": "🏠", "color": "#B85D3C"},
}


def tokens(dark: bool) -> dict:
    return DARK if dark else LIGHT


def build_qss(t: dict) -> str:
    cream = "#FFFDF8"
    band_sub = "#FFE9BD"
    # 窗口自身底色：Qt 在状态栏安全区那一条会用它填（页面内容从安全区下方开始）。
    # 必须和页面纯色底一致，否则顶部永远留一条比页面浅的色差带。
    page_bg = _mix(t["brand"], t["page"], 0.92).name()
    return f"""
    QWidget {{
        font-family: "{FONT}", "Microsoft YaHei UI", "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 13px;
        color: {t['ink']};
    }}
    QMainWindow, #root {{ background: {page_bg}; }}
    #phoneColumn {{ background: transparent; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ width: 0px; background: transparent; }}

    /* 顶部：奶白底 + 墨色标题（无深色色带、无波浪） */
    QFrame#bandHeader, QWidget#bandHeader {{ background: transparent; border: none; }}
    QWidget#bandHeader QLabel#h1 {{ color: {t['ink']}; font-size: 24px; font-weight: 700; }}
    QWidget#bandHeader QLabel#h2 {{ color: {t['ink']}; font-size: 16px; font-weight: 700; }}
    QWidget#bandHeader QLabel#h3 {{ color: {t['ink']}; font-size: 13px; font-weight: 600; }}
    QWidget#bandHeader QLabel#sub,
    QWidget#bandHeader QLabel#eyebrow {{ color: {t['ink2']}; font-size: 10px; }}
    QWidget#bandHeader QLabel {{ color: {t['ink']}; }}
    QWidget#bandHeader QPushButton {{ color: {t['ink']}; }}
    QWidget#bandHeader QPushButton#chip {{
        background: {t['panel']}; color: {t['ink2']};
        border: 1px solid {t['line']};
    }}
    QWidget#bandHeader QPushButton#ghost {{
        background: transparent; border: 1.2px solid {t['line']};
        color: {t['ink']};
    }}

    QFrame#card {{
        background: {t['panel']};
        border: 1px solid {t['line']};
        border-radius: 18px;
    }}
    QFrame#flatCard {{
        background: {t['panel']};
        border: 1px solid {t['line']};
        border-radius: 18px;
    }}
    QFrame#hero {{
        border-radius: 22px;
        background: {t['brand']};
        border: 1px solid {t['line']};
    }}

    QWidget#bandHeader QLabel {{ color: #FFFDF8; }}
    QWidget#bandHeader QLabel#h1 {{ color: #FFFDF8; }}
    QWidget#bandHeader QPushButton {{ color: #FFFDF8; }}
    QWidget#reviewTop {{ background: {page_bg}; }}
    QWidget#reviewTop QLabel {{ color: {t['ink']}; }}
    QWidget#reviewTop QPushButton {{ color: {t['ink']}; }}
    QWidget#reviewTop QLabel#h2 {{ color: {t['ink']}; }}
    QWidget#reviewTop QFrame {{ background: transparent; }}
    QWidget#reviewTop QPushButton#iconBtn {{
        background: {t['panel']};
        border: 1px solid {t['line']};
        border-radius: 15px;
        color: {t['ink']};
    }}


    QFrame#navFrame {{
        background: transparent;
        border: none;
    }}
    QFrame#navBar {{ background: transparent; border: none; }}

    QLabel {{ background: transparent; }}
    QLabel#h1 {{ font-family: "KaiTi"; font-size: 27px; font-weight: 700; color: {t['ink']}; }}
    QLabel#h2 {{ font-family: "KaiTi"; font-size: 16px; font-weight: 700; color: {t['ink']}; }}
    QLabel#h3 {{ font-size: 13px; font-weight: 600; color: {t['ink']}; }}
    QLabel#sub {{ color: {t['ink2']}; font-size: 11px; }}
    QLabel#eyebrow {{ color: {t['ink2']}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
    QLabel#big {{ font-size: 46px; font-weight: 700; color: {t['butter']}; }}
    QLabel#heroCap {{ color: {cream}; font-size: 12px; }}

    QPushButton {{
        border: none; background: transparent; color: {t['ink']};
        padding: 8px 12px; border-radius: 999px;
    }}
    QPushButton#primary {{
        background: {t['brand']}; color: {cream};
        font-weight: 700; padding: 11px 18px; border-radius: 22px;
        border: none;
    }}
    QPushButton#primary:hover {{ background: {t['brand2']}; }}
    QPushButton#ghost {{
        background: {t['panel']}; border: 1px solid {t['line']};
        color: {t['ink']}; padding: 10px 16px; border-radius: 20px;
    }}
    QPushButton#ghost:hover {{ background: {t['butter_soft']}; }}
    QPushButton#chip {{
        background: {t['panel']}; border: 1px solid {t['line']};
        color: {t['ink2']}; padding: 7px 14px; border-radius: 15px; font-size: 12px;
    }}
    QPushButton#chip[on="true"] {{
        background: {t['brand']}; color: {cream}; border-color: {t['brand']};
    }}
    QPushButton#iconBtn {{
        background: {t['panel']}; border: 1px solid {t['line']};
        border-radius: 20px; padding: 0px; font-size: 15px; color: {t['ink']};
    }}
    QPushButton#iconBtn:hover {{ background: {t['butter_soft']}; }}
    QPushButton#tab {{
        color: {t['ink2']}; font-size: 10px; padding: 6px 0 8px 0; border-radius: 0;
    }}
    QPushButton#tab[on="true"] {{ color: {t['brand']}; font-weight: 700; }}

    QLineEdit, QTextEdit {{
        background: {t['panel']}; border: 1px solid {t['line']};
        border-radius: 14px; padding: 10px 12px; color: {t['ink']};
        selection-background-color: {t['brand']};
    }}
    QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {t['brand']}; }}

    QComboBox {{
        background: {t['panel']}; border: 1px solid {t['line']};
        border-radius: 12px; padding: 8px 12px; color: {t['ink']};
    }}
    QComboBox QAbstractItemView {{
        background: {t['panel']}; color: {t['ink']};
        selection-background-color: {t['brand_soft']};
    }}

    QFrame#line {{ background: {t['line']}; max-height: 1px; min-height: 1px; border: none; }}
    QFrame#grabber {{ background: {t['line']}; border-radius: 2px; }}
    QToolTip {{
        background: {t['panel']}; color: {t['ink']};
        border: 1px solid {t['line']}; border-radius: 10px;
        padding: 7px 12px; font-size: 12px;
    }}
    """

# ---------------------------------------------------------------- 主题
# 纸感主题：每套都有完整的背景 / 卡片 / 文字 / 边框 / 点缀配色。
# 共享令牌只负责成功、警告等语义色；中性色由各主题自行覆盖。
_CREAM = {
    "paper":   "#F3EEDF",
    "paper2":  "#E9E1CB",
    "page":    "#F3EEDF",
    "panel":   "#FBF6EA",
    "ink":     "#2A2519",
    "ink2":    "#8A8066",
    "ink3":    "#B7AD94",
    "line":    "#E0D6BE",
    "green":   "#3E7A52", "green_soft": "#DDEBDF",
    "red":     "#B85A3A", "red_soft":   "#F5DECF",
    "blue":    "#3E6482", "blue_soft":  "#DCE6F0",
    "accent":  "#D9A441", "accent_soft":"#F6E8C5",
    "butter":  "#D9A441", "butter_soft":"#F6E8C5",
    "shadow":  "rgba(42,37,25,0.10)",
}

THEMES = {
    "anki-aurora": {
        "name": "极光", "dark": False, "deep": "#B23A5B", "page": _CREAM["page"],
        "tokens": {**_CREAM,
                   "brand": "#B23A5B", "brand2": "#8E2946", "brand_soft": "#F3DDE4",
                   "deep": "#B23A5B"},
    },
    "anki-ice": {
        "name": "冰川", "dark": False, "deep": "#2E5E8C", "page": "#EDF3F7",
        "tokens": {**_CREAM,
                   "paper": "#EDF3F7", "paper2": "#DDE8EF", "page": "#EDF3F7",
                   "panel": "#F8FBFD", "ink": "#22303A", "ink2": "#647C8C",
                   "ink3": "#9CB0BC", "line": "#CFDDE6",
                   "brand": "#2E5E8C", "brand2": "#234A70", "brand_soft": "#D6E5F0",
                   "deep": "#2E5E8C", "accent": "#4B7FA3", "accent_soft": "#DCE8F1",
                   "butter": "#4B7FA3", "butter_soft": "#DCE8F1"},
    },
    "anki-mint": {
        "name": "薄荷", "dark": False, "deep": "#2F7A4F", "page": "#EDF4EC",
        "tokens": {**_CREAM,
                   "paper": "#EDF4EC", "paper2": "#DDE9DA", "page": "#EDF4EC",
                   "panel": "#F9FCF6", "ink": "#243329", "ink2": "#687E6D",
                   "ink3": "#9DB2A0", "line": "#D0DFCE",
                   "brand": "#2F7A4F", "brand2": "#235F3D", "brand_soft": "#D8EBDD",
                   "deep": "#2F7A4F", "accent": "#6E9847", "accent_soft": "#E1EBD4",
                   "butter": "#6E9847", "butter_soft": "#E1EBD4"},
    },
    "anki-champ": {
        "name": "香檟", "dark": False, "deep": "#A9761C", "page": "#F7F0DF",
        "tokens": {**_CREAM,
                   "paper": "#F7F0DF", "paper2": "#EDE0C2", "page": "#F7F0DF",
                   "panel": "#FFFAEE", "ink": "#3A2E18", "ink2": "#907A4E",
                   "ink3": "#BEAB7C", "line": "#E4D5AF",
                   "brand": "#A9761C", "brand2": "#855A12", "brand_soft": "#F1E2BC",
                   "deep": "#A9761C", "accent": "#B88425", "accent_soft": "#F3E5C3",
                   "butter": "#B88425", "butter_soft": "#F3E5C3"},
    },
    "anki-lilac": {
        "name": "丁香", "dark": False, "deep": "#6B4EA8", "page": "#F2EFF7",
        "tokens": {**_CREAM,
                   "paper": "#F2EFF7", "paper2": "#E4DEEE", "page": "#F2EFF7",
                   "panel": "#FBF9FD", "ink": "#30283D", "ink2": "#7D718E",
                   "ink3": "#AFA4BE", "line": "#DCD3E7",
                   "brand": "#6B4EA8", "brand2": "#543B87", "brand_soft": "#E4DBF0",
                   "deep": "#6B4EA8", "accent": "#8A68B4", "accent_soft": "#E8DFF2",
                   "butter": "#8A68B4", "butter_soft": "#E8DFF2"},
    },
    "anki-coral": {
        "name": "珊瑚", "dark": False, "deep": "#C4562E", "page": "#F9EFE7",
        "tokens": {**_CREAM,
                   "paper": "#F9EFE7", "paper2": "#F0DED1", "page": "#F9EFE7",
                   "panel": "#FFF9F3", "ink": "#3C2921", "ink2": "#937264",
                   "ink3": "#C1A092", "line": "#E8D1C2",
                   "brand": "#C4562E", "brand2": "#9E4423", "brand_soft": "#F3D9CC",
                   "deep": "#C4562E", "accent": "#C8793C", "accent_soft": "#F3E0CE",
                   "butter": "#C8793C", "butter_soft": "#F3E0CE"},
    },
    "anki-lagoon": {
        "name": "潟湖", "dark": False, "deep": "#0F7C86", "page": "#EAF4F2",
        "tokens": {**_CREAM,
                   "paper": "#EAF4F2", "paper2": "#D8E8E5", "page": "#EAF4F2",
                   "panel": "#F7FCFA", "ink": "#203534", "ink2": "#617F7D",
                   "ink3": "#9AB3B0", "line": "#CBDDD9",
                   "brand": "#0F7C86", "brand2": "#0A5F67", "brand_soft": "#D2E9E8",
                   "deep": "#0F7C86", "accent": "#3A9188", "accent_soft": "#D8EAE6",
                   "butter": "#3A9188", "butter_soft": "#D8EAE6"},
    },
}

DEFAULT_THEME = "anki-aurora"

def theme_ids() -> list[str]:
    return list(THEMES.keys())


def theme_info(tid: str) -> dict:
    return THEMES.get(tid) or THEMES[DEFAULT_THEME]


def theme_tokens(tid: str) -> dict:
    return theme_info(tid)["tokens"]


def theme_is_dark(tid: str) -> bool:
    return bool(theme_info(tid)["dark"])


def _mix(a: str, b: str, t: float) -> QColor:
    """把 a 按比例 t 混到 b 里（t=1 表示完全取 b）。"""
    ca, cb = QColor(a), QColor(b)
    return QColor(
        round(ca.red() * (1 - t) + cb.red() * t),
        round(ca.green() * (1 - t) + cb.green() * t),
        round(ca.blue() * (1 - t) + cb.blue() * t),
    )


def page_bg_color(tid: str | None = None) -> QColor:
    """页面纯色底：主题纸色掺一点主色。界面绘制和系统栏取色都用它，保证同色。"""
    pal = theme_info(tid or DEFAULT_THEME)["tokens"]
    return _mix(pal["brand"], pal["page"], 0.92)


def chrome_bg_color(tid: str | None = None) -> QColor:
    """系统栏（状态栏 / 手势条）底色：取主题深色，和顶栏色带、底部 dock 连成一片。

    安卓上这两条安全区由 Activity 窗口背景填（Qt 窗口本身不覆盖），所以颜色必须
    和顶栏/底栏同色；用页面浅色底会在深色顶栏上方露出浅一截的色带（「奶白条」）。
    """
    pal = theme_info(tid or DEFAULT_THEME)["tokens"]
    return QColor(pal["deep"])


def chrome_is_light(hex_str: str | None) -> bool:
    """系统栏底色是否偏浅：决定状态栏/手势条用深色图标还是白色图标。"""
    c = QColor(hex_str) if hex_str else QColor()
    if not c.isValid():
        return False
    lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
    return lum > 0.58


def paint_page_bg(p: QPainter, rect, tid: str | None):
    """页面底色：纯色，主题纸色里掺一点主色，整页统一，不用渐变。"""
    p.fillRect(QRectF(rect), page_bg_color(tid))
