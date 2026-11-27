# -*- coding: utf-8 -*-
"""
theme.py - 设计令牌 + 全局 QSS
7 套「池塘纸感」平涂主题（极光/冰川/薄荷/香檟/丁香/珊瑚/潟湖），纯色、无渐变。
"""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter


LIGHT = {
    "paper":   "#FBF8F1",
    "paper2":  "#F2F1E7",
    "panel":   "#FFFFFF",
    "ink":     "#242721",
    "ink2":    "#73766F",
    "ink3":    "#A8A79E",
    "line":    "#E4E1D6",
    "brand":   "#2F6A43",
    "brand2":  "#245637",
    "brand_soft": "#E9EFE6",
    "accent":  "#BF5B38",
    "accent_soft": "#F4E7DF",
    "green":   "#2E9E67",
    "green_soft": "#EAF7F0",
    "red":     "#E8503A",
    "red_soft": "#FDEDEA",
    "blue":    "#426A80",
    "blue_soft": "#E4EDF4",
    "shadow":  "rgba(36,39,33,0.10)",
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

    /* 紧凑深色色带：标题区约 80–100px，内部文字反白 */
    QFrame#bandHeader, QWidget#bandHeader {{ background: transparent; border: none; }}
    QWidget#bandHeader QLabel#h1 {{ color: {cream}; font-size: 23px; font-weight: 700; }}
    QWidget#bandHeader QLabel#h2 {{ color: {cream}; font-size: 15px; font-weight: 700; }}
    QWidget#bandHeader QLabel#h3 {{ color: {cream}; font-size: 12px; font-weight: 600; }}
    QWidget#bandHeader QLabel#sub,
    QWidget#bandHeader QLabel#eyebrow {{ color: {band_sub}; font-size: 9px; }}
    QWidget#bandHeader QLabel {{ color: {cream}; }}
    QWidget#bandHeader QPushButton {{ color: {cream}; }}
    QWidget#bandHeader QPushButton#chip {{
        background: rgba(255,253,248,0.18);
        color: #FFFDF8;
        border: 1px solid rgba(255,253,248,0.35);
    }}
    QWidget#bandHeader QPushButton#ghost {{
        background: transparent; border: 1.5px solid rgba(255,253,248,0.55);
        color: {cream};
    }}

    QFrame#card {{
        background: {t['panel']};
        border: 1.5px solid {t['ink']};
        border-radius: 16px;
    }}
    QFrame#flatCard {{
        background: {t['panel']};
        border: 1.5px solid {t['ink']};
        border-radius: 16px;
    }}
    QFrame#hero {{
        border-radius: 24px;
        background: {t['brand']};
        border: 1.5px solid {t['ink']};
    }}
    QWidget#reviewTop {{ background: {t['deep']}; }}
    QWidget#reviewTop QLabel {{ color: #FFFDF8; }}
    QWidget#reviewTop QPushButton {{ color: #FFFDF8; }}
    QWidget#reviewTop QLabel#h2 {{ color: #FFFDF8; }}
    QWidget#reviewTop QFrame {{ background: transparent; }}
    QWidget#reviewTop QPushButton#iconBtn {{
        background: rgba(255,253,248,0.16);
        border: 1px solid rgba(255,253,248,0.35);
        border-radius: 15px;
        color: #FFFDF8;
    }}


    QFrame#navFrame {{
        background: {t['deep']};
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
        border: 1.5px solid {t['ink']};
    }}
    QPushButton#primary:hover {{ background: {t['brand2']}; }}
    QPushButton#ghost {{
        background: {t['panel']}; border: 1.5px solid {t['ink']};
        color: {t['ink']}; padding: 10px 16px; border-radius: 20px;
    }}
    QPushButton#ghost:hover {{ background: {t['butter_soft']}; }}
    QPushButton#chip {{
        background: {t['panel']}; border: 1.5px solid {t['line']};
        color: {t['ink2']}; padding: 7px 14px; border-radius: 15px; font-size: 12px;
    }}
    QPushButton#chip[on="true"] {{
        background: {t['brand']}; color: {cream}; border-color: {t['brand']};
    }}
    QPushButton#iconBtn {{
        background: {t['panel']}; border: 1.5px solid {t['ink']};
        border-radius: 20px; padding: 0px; font-size: 15px; color: {t['ink']};
    }}
    QPushButton#iconBtn:hover {{ background: {t['butter_soft']}; }}
    QPushButton#tab {{
        color: {t['ink2']}; font-size: 10px; padding: 6px 0 8px 0; border-radius: 0;
    }}
    QPushButton#tab[on="true"] {{ color: {t['brand']}; font-weight: 700; }}

    QLineEdit, QTextEdit {{
        background: {t['panel']}; border: 1.5px solid {t['ink']};
        border-radius: 14px; padding: 10px 12px; color: {t['ink']};
        selection-background-color: {t['brand']};
    }}
    QLineEdit:focus, QTextEdit:focus {{ border: 1.5px solid {t['brand']}; }}

    QComboBox {{
        background: {t['panel']}; border: 1.5px solid {t['ink']};
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
        border: 1.5px solid {t['ink']}; border-radius: 10px;
        padding: 7px 12px; font-size: 12px;
    }}
    """

# ---------------------------------------------------------------- 主题
# 「池塘纸感」7 套平涂主题：主题深色 + 浅纸色，全部纯色、无渐变。
_POND_BASE = {
    "panel": "#FFFDF8",
    "ink": "#211B1C", "ink2": "#6F5F60", "ink3": "#A08F90",
    "green": "#2F7A4F", "green_soft": "#DCEFE2",
    "red": "#C4562E", "red_soft": "#F8DCCF",
    "blue": "#2E5E8C", "blue_soft": "#DCE8F5",
    "accent": "#F2C14E", "accent_soft": "#FCEBC4",
    "butter": "#F2C14E", "butter_soft": "#FCEBC4",
    "shadow": "rgba(33,27,28,0.10)",
}

THEMES = {
    "anki-aurora": {
        "name": "极光", "dark": False, "deep": "#B23A5B", "page": "#F8E9E6",
        "tokens": {**_POND_BASE,
                   "paper": "#F8E9E6", "paper2": "#F3DADF", "line": "#E7CFD4",
                   "brand": "#B23A5B", "brand2": "#8E2946", "brand_soft": "#F3DADF",
                   "deep": "#B23A5B", "page": "#F8E9E6"},
    },
    "anki-ice": {
        "name": "冰川", "dark": False, "deep": "#2E5E8C", "page": "#EAF1F7",
        "tokens": {**_POND_BASE,
                   "paper": "#EAF1F7", "paper2": "#D9E6F3", "line": "#CFDDEB",
                   "brand": "#2E5E8C", "brand2": "#234A70", "brand_soft": "#D9E6F3",
                   "deep": "#2E5E8C", "page": "#EAF1F7"},
    },
    "anki-mint": {
        "name": "薄荷", "dark": False, "deep": "#2F7A4F", "page": "#EAF4EC",
        "tokens": {**_POND_BASE,
                   "paper": "#EAF4EC", "paper2": "#D8EEDD", "line": "#CFE4D5",
                   "brand": "#2F7A4F", "brand2": "#235F3D", "brand_soft": "#D8EEDD",
                   "deep": "#2F7A4F", "page": "#EAF4EC"},
    },
    "anki-champ": {
        "name": "香檟", "dark": False, "deep": "#A9761C", "page": "#F8F0E1",
        "tokens": {**_POND_BASE,
                   "paper": "#F8F0E1", "paper2": "#F1E2C4", "line": "#E8D7B5",
                   "brand": "#A9761C", "brand2": "#855A12", "brand_soft": "#F1E2C4",
                   "deep": "#A9761C", "page": "#F8F0E1"},
    },
    "anki-lilac": {
        "name": "丁香", "dark": False, "deep": "#6B4EA8", "page": "#F1ECF8",
        "tokens": {**_POND_BASE,
                   "paper": "#F1ECF8", "paper2": "#E4DAF5", "line": "#DCCFEF",
                   "brand": "#6B4EA8", "brand2": "#543B87", "brand_soft": "#E4DAF5",
                   "deep": "#6B4EA8", "page": "#F1ECF8"},
    },
    "anki-coral": {
        "name": "珊瑚", "dark": False, "deep": "#C4562E", "page": "#F9ECE4",
        "tokens": {**_POND_BASE,
                   "paper": "#F9ECE4", "paper2": "#F5DCCF", "line": "#EBCABC",
                   "brand": "#C4562E", "brand2": "#9E4423", "brand_soft": "#F5DCCF",
                   "deep": "#C4562E", "page": "#F9ECE4"},
    },
    "anki-lagoon": {
        "name": "潟湖", "dark": False, "deep": "#0F7C86", "page": "#E8F4F5",
        "tokens": {**_POND_BASE,
                   "paper": "#E8F4F5", "paper2": "#D3EBED", "line": "#C6E1E3",
                   "brand": "#0F7C86", "brand2": "#0A5F67", "brand_soft": "#D3EBED",
                   "deep": "#0F7C86", "page": "#E8F4F5"},
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
