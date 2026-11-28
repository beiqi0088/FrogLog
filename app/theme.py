# -*- coding: utf-8 -*-
"""
theme.py - 设计令牌 + 全局 QSS
7 套奶白纸感主题（极光/冰川/薄荷/香檟/丁香/珊瑚/潟湖）：全站奶白背景 + 细墨字，
主题色只用作按钮 / 选中态 / 徽章点缀。纯色、无渐变、无深色顶带 / 底栏。
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
    return f"""
    QWidget {{
        font-family: "{FONT}", "Microsoft YaHei UI", "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 13px;
        color: {t['ink']};
    }}
    QMainWindow, #root {{ background: {t['paper']}; }}
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
    QWidget#reviewTop {{ background: {t['paper']}; }}
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
        background: {t['paper2']};
        border: none;
    }}
    QFrame#navBar {{ background: transparent; border: none; }}

    QLabel {{ background: transparent; }}
    QLabel#h1 {{ font-size: 27px; font-weight: 700; color: {t['ink']}; }}
    QLabel#h2 {{ font-size: 16px; font-weight: 700; color: {t['ink']}; }}
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
# 奶白纸感：全站奶白背景 + 细墨字；每套主题只保留一个强调色（deep/brand），
# 用作选中态、主按钮、徽章等点缀。纯色、无渐变、无深色顶带 / 底栏。
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
        "name": "冰川", "dark": False, "deep": "#2E5E8C", "page": _CREAM["page"],
        "tokens": {**_CREAM,
                   "brand": "#2E5E8C", "brand2": "#234A70", "brand_soft": "#DCE6F3",
                   "deep": "#2E5E8C"},
    },
    "anki-mint": {
        "name": "薄荷", "dark": False, "deep": "#2F7A4F", "page": _CREAM["page"],
        "tokens": {**_CREAM,
                   "brand": "#2F7A4F", "brand2": "#235F3D", "brand_soft": "#DCEFE2",
                   "deep": "#2F7A4F"},
    },
    "anki-champ": {
        "name": "香檟", "dark": False, "deep": "#A9761C", "page": _CREAM["page"],
        "tokens": {**_CREAM,
                   "brand": "#A9761C", "brand2": "#855A12", "brand_soft": "#F3E7CC",
                   "deep": "#A9761C"},
    },
    "anki-lilac": {
        "name": "丁香", "dark": False, "deep": "#6B4EA8", "page": _CREAM["page"],
        "tokens": {**_CREAM,
                   "brand": "#6B4EA8", "brand2": "#543B87", "brand_soft": "#E7DEF3",
                   "deep": "#6B4EA8"},
    },
    "anki-coral": {
        "name": "珊瑚", "dark": False, "deep": "#C4562E", "page": _CREAM["page"],
        "tokens": {**_CREAM,
                   "brand": "#C4562E", "brand2": "#9E4423", "brand_soft": "#F5E1D3",
                   "deep": "#C4562E"},
    },
    "anki-lagoon": {
        "name": "潟湖", "dark": False, "deep": "#0F7C86", "page": _CREAM["page"],
        "tokens": {**_CREAM,
                   "brand": "#0F7C86", "brand2": "#0A5F67", "brand_soft": "#D4EAEC",
                   "deep": "#0F7C86"},
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


def paint_page_bg(p: QPainter, rect, tid: str | None):
    """平涂纸底：整页只铺主题浅纸色，不再画任何渐变。"""
    info = theme_info(tid or DEFAULT_THEME)
    p.fillRect(QRectF(rect), QColor(info["page"]))
