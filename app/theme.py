# -*- coding: utf-8 -*-
"""
theme.py - 设计令牌 + 全局 QSS
沿用浮卡的做法：LIGHT / DARK 两套 dict，build_qss() 统一出样式表。
配色来自「艾宾浩斯记忆曲线」APK 反编译（纸白 + 墨绿 + 赭石）。
"""

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
    return f"""
    QWidget {{
        font-family: "{FONT}", "Microsoft YaHei UI", "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 13px;
        color: {t['ink']};
    }}
    QMainWindow, #root {{ background: {t['paper']}; }}
    #phoneColumn {{ background: {t['paper']}; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ width: 0px; background: transparent; }}

    QFrame#card {{
        background: {t['panel']};
        border: 1px solid {t['line']};
        border-radius: 18px;
    }}
    QFrame#flatCard {{
        background: {t['paper2']};
        border: none;
        border-radius: 16px;
    }}
    QFrame#hero {{
        border-radius: 26px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {t.get('hero_a', t['brand2'])}, stop:1 {t.get('hero_b', t['brand'])});
    }}

    QLabel {{ background: transparent; }}
    QLabel#h1 {{ font-size: 27px; font-weight: 700; color: {t['ink']}; }}
    QLabel#h2 {{ font-size: 16px; font-weight: 700; color: {t['ink']}; }}
    QLabel#h3 {{ font-size: 13px; font-weight: 600; color: {t['ink']}; }}
    QLabel#sub {{ color: {t['ink2']}; font-size: 11px; }}
    QLabel#eyebrow {{ color: {t['ink2']}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
    QLabel#big {{ font-size: 46px; font-weight: 600; color: {t['brand_soft']}; }}
    QLabel#heroCap {{ color: {t['brand_soft']}; font-size: 12px; }}

    QPushButton {{
        border: none; background: transparent; color: {t['ink']};
        padding: 8px 12px; border-radius: 999px;
    }}
    QPushButton#primary {{
        background: {t['brand']}; color: {t['brand_soft']};
        font-weight: 600; padding: 11px 18px; border-radius: 22px;
    }}
    QPushButton#primary:hover {{ background: {t['brand2']}; }}
    QPushButton#ghost {{
        background: {t['panel']}; border: 1px solid {t['line']};
        color: {t['ink']}; padding: 10px 16px; border-radius: 20px;
    }}
    QPushButton#ghost:hover {{ background: {t['paper2']}; }}
    QPushButton#chip {{
        background: {t['panel']}; border: 1px solid {t['line']};
        color: {t['ink2']}; padding: 7px 14px; border-radius: 15px; font-size: 12px;
    }}
    QPushButton#chip[on="true"] {{
        background: {t['brand2']}; color: #FFFFFF; border-color: {t['brand2']};
    }}
    QPushButton#iconBtn {{
        background: {t['paper2']}; border-radius: 20px; padding: 0px;
        font-size: 15px; color: {t['ink']};
    }}
    QPushButton#iconBtn:hover {{ background: {t['line']}; }}
    QPushButton#tab {{
        color: {t['ink2']}; font-size: 10px; padding: 6px 0 8px 0; border-radius: 0;
    }}
    QPushButton#tab[on="true"] {{ color: {t['brand']}; font-weight: 700; }}

    QLineEdit, QTextEdit {{
        background: {t['paper2']}; border: 1px solid {t['line']};
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
THEMES = {
    "paper": {"name": "宣纸墨绿", "dark": False, "tokens": LIGHT},
    "mist": {"name": "晨雾靛蓝", "dark": False, "tokens": {
        "paper": "#F2F5F8", "paper2": "#E7EDF3", "panel": "#FFFFFF",
        "ink": "#1F2A33", "ink2": "#5C6B77", "ink3": "#93A1AC",
        "line": "#DCE4EA", "brand": "#2F5D8A", "brand2": "#22456A",
        "brand_soft": "#E1ECF7", "accent": "#C2703D", "accent_soft": "#FAE9DE",
        "green": "#2E7D5B", "green_soft": "#E1F2EA", "red": "#C0443A",
        "red_soft": "#FBE7E4", "blue": "#2F5D8A", "blue_soft": "#E1ECF7",
        "shadow": "rgba(36,58,80,0.10)",
    }},
    "cream": {"name": "奶油陶土", "dark": False, "tokens": {
        "paper": "#FDF6EC", "paper2": "#F6EADB", "panel": "#FFFDF9",
        "ink": "#3A2E27", "ink2": "#7A6A5D", "ink3": "#B3A292",
        "line": "#EADCCB", "brand": "#B45F3F", "brand2": "#8E4527",
        "brand_soft": "#F8E4D8", "accent": "#D98E4B", "accent_soft": "#FBEDDD",
        "green": "#4E7A50", "green_soft": "#E7F0E3", "red": "#C24B3F",
        "red_soft": "#FBE6E2", "blue": "#4A6C8C", "blue_soft": "#E6EDF5",
        "shadow": "rgba(90,60,40,0.10)",
    }},
    "ink": {"name": "石墨黑白", "dark": False, "tokens": {
        "paper": "#F5F5F4", "paper2": "#EAEAE8", "panel": "#FFFFFF",
        "ink": "#18191A", "ink2": "#5F6163", "ink3": "#9A9C9E",
        "line": "#DADAD8", "brand": "#2B2D2F", "brand2": "#101112",
        "brand_soft": "#E8E8E6", "accent": "#A85B33", "accent_soft": "#F3E7DF",
        "green": "#2E7D5B", "green_soft": "#E4F1EA", "red": "#C0392B",
        "red_soft": "#FBE6E3", "blue": "#3F5F7A", "blue_soft": "#E6EDF3",
        "shadow": "rgba(20,20,20,0.12)",
    }},
    "celadon": {"name": "青瓷", "dark": False, "tokens": {
        "paper": "#EFF6F4", "paper2": "#E2EEEA", "panel": "#FAFFFD",
        "ink": "#1E3330", "ink2": "#5A736E", "ink3": "#93A8A3",
        "line": "#D3E4DF", "brand": "#2E6F63", "brand2": "#1F5049",
        "brand_soft": "#DDEDE8", "accent": "#B07A45", "accent_soft": "#F4E9DC",
        "green": "#2E7D5B", "green_soft": "#E1F3EC", "red": "#BF4A3F",
        "red_soft": "#FAE6E3", "blue": "#3D6B86", "blue_soft": "#E2EEF5",
        "shadow": "rgba(30,70,60,0.10)",
    }},
    "sunset": {"name": "落日粉橙", "dark": False, "tokens": {
        "paper": "#FFF4F0", "paper2": "#FCE7DF", "panel": "#FFFDFC",
        "ink": "#3B2A26", "ink2": "#7C625B", "ink3": "#B79F97",
        "line": "#F0D8CF", "brand": "#C0563F", "brand2": "#9A3E2A",
        "brand_soft": "#FBE3DB", "accent": "#E08A3C", "accent_soft": "#FCEBDA",
        "green": "#4F7A52", "green_soft": "#E8F1E4", "red": "#C5453C",
        "red_soft": "#FCE4E0", "blue": "#4A6683", "blue_soft": "#E8EDF4",
        "shadow": "rgba(120,60,40,0.10)",
    }},
    "night": {"name": "暗夜青", "dark": True, "tokens": {
        "paper": "#12161A", "paper2": "#1B2127", "panel": "#161C22",
        "ink": "#E8EDF1", "ink2": "#A9B6C0", "ink3": "#74828D",
        "line": "#2A343D", "brand": "#4FB3A5", "brand2": "#2E7C72",
        "brand_soft": "#17312F", "accent": "#E0A15C", "accent_soft": "#3A2A18",
        "green": "#62C29A", "green_soft": "#1B3329", "red": "#F0857A",
        "red_soft": "#3A211E", "blue": "#6FA8D0", "blue_soft": "#1E2E3A",
        "shadow": "rgba(0,0,0,0.45)",
        "hero_a": "#1B2A24", "hero_b": "#2A4A3F", "hero_ink": "#EAF3F0",
    }},
    "dusk": {"name": "暮紫", "dark": True, "tokens": {
        "paper": "#17141C", "paper2": "#211C29", "panel": "#1C1823",
        "ink": "#ECE8F2", "ink2": "#B2ABC0", "ink3": "#7E7790",
        "line": "#332C3F", "brand": "#A48BE0", "brand2": "#7A63B8",
        "brand_soft": "#2A2340", "accent": "#E0A15C", "accent_soft": "#3A2A18",
        "green": "#7FC9A6", "green_soft": "#1E3329", "red": "#F0877C",
        "red_soft": "#3A211E", "blue": "#8FB0D8", "blue_soft": "#212C3A",
        "shadow": "rgba(0,0,0,0.45)",
        "hero_a": "#201A2B", "hero_b": "#3A3055", "hero_ink": "#EFEAF6",
    }},
}


def theme_ids() -> list[str]:
    return list(THEMES.keys())


def theme_info(tid: str) -> dict:
    return THEMES.get(tid) or THEMES["paper"]


def theme_tokens(tid: str) -> dict:
    return theme_info(tid)["tokens"]


def theme_is_dark(tid: str) -> bool:
    return bool(theme_info(tid)["dark"])

