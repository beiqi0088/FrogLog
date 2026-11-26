# -*- coding: utf-8 -*-
"""
theme.py - 设计令牌 + 全局 QSS
7 套 Anki card-anki 模板配色（极光/冰川/薄荷/香槟/丁香/珊瑚/潟湖）+ 渐变页面底色。
"""

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient


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
    #phoneColumn {{ background: transparent; }}

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
# 只保留 apkg 里 card-anki 模板的 7 个 ColorClass 配色；原来的 8 套已删除。
_ANKI_BASE = {
    "panel": "#FFFFFF",
    "ink": "#1E293B", "ink2": "#64748B", "ink3": "#94A3B8",
    "green": "#2E9E67", "green_soft": "#EAF7F0",
    "red": "#E8503A", "red_soft": "#FDEDEA",
    "blue": "#426A80", "blue_soft": "#E4EDF4",
    "shadow": "rgba(30,41,59,0.10)",
}

THEMES = {
    "anki-aurora": {
        "name": "极光", "dark": False, "anki": True,
        "dot": ("#FB923C", "#DB2777"),
        "bg": {"linear": ("#FFF7F3", "#FEF1F6", "#F6F2FF"),
               "r1": "#FFCEAA", "r2": "#FFBACE", "solid": "#FBEEE6"},
        "tokens": {**_ANKI_BASE,
                   "paper": "#FCF6F4", "paper2": "#F9EBEF", "line": "#F3DEE6",
                   "brand": "#DB2777", "brand2": "#9D174D",
                   "brand_soft": "#FCE7F3", "accent": "#F59E0B",
                   "accent_soft": "#FEF3C7"},
    },
    "anki-ice": {
        "name": "冰川", "dark": False, "anki": True,
        "dot": ("#38BDF8", "#4F46E5"),
        "bg": {"linear": ("#F3F8FF", "#EEF5FE", "#F2F3FF"),
               "r1": "#AADCFA", "r2": "#BAAFFA", "solid": "#E9F1FB"},
        "tokens": {**_ANKI_BASE,
                   "paper": "#F5F8FF", "paper2": "#E9F2FE", "line": "#DEE7F8",
                   "brand": "#4F46E5", "brand2": "#3730A3",
                   "brand_soft": "#E0E7FF", "accent": "#38BDF8",
                   "accent_soft": "#E0F2FE"},
    },
    "anki-mint": {
        "name": "薄荷", "dark": False, "anki": True,
        "dot": ("#10B981", "#0EA5E9"),
        "bg": {"linear": ("#F4FDF8", "#EEFAF4", "#F0F9FF"),
               "r1": "#96EBC4", "r2": "#B2E4F6", "solid": "#E7F7F0"},
        "tokens": {**_ANKI_BASE,
                   "paper": "#F4FCF9", "paper2": "#E6F8F0", "line": "#D8EEE5",
                   "brand": "#0E9F6E", "brand2": "#047857",
                   "brand_soft": "#D1FAE5", "accent": "#0EA5E9",
                   "accent_soft": "#E0F2FE"},
    },
    "anki-champ": {
        "name": "香槟", "dark": False, "anki": True,
        "dot": ("#F59E0B", "#EC4899"),
        "bg": {"linear": ("#FFFCF2", "#FDF6E9", "#FDF1EE"),
               "r1": "#FADE8C", "r2": "#FFC4C4", "solid": "#FBF3E2"},
        "tokens": {**_ANKI_BASE,
                   "paper": "#FEFAF1", "paper2": "#FDF3DF", "line": "#F1E3C4",
                   "brand": "#D97706", "brand2": "#92400E",
                   "brand_soft": "#FEF3C7", "accent": "#EC4899",
                   "accent_soft": "#FCE7F3"},
    },
    "anki-lilac": {
        "name": "丁香", "dark": False, "anki": True,
        "dot": ("#A78BFA", "#6366F1"),
        "bg": {"linear": ("#FAF7FF", "#F5F2FF", "#F1F5FF"),
               "r1": "#CEB4FC", "r2": "#B2D0FA", "solid": "#F1EBFD"},
        "tokens": {**_ANKI_BASE,
                   "paper": "#F9F5FF", "paper2": "#F1ECFE", "line": "#E6DDF8",
                   "brand": "#7C3AED", "brand2": "#5B21B6",
                   "brand_soft": "#EDE9FE", "accent": "#6366F1",
                   "accent_soft": "#E0E7FF"},
    },
    "anki-coral": {
        "name": "珊瑚", "dark": False, "anki": True,
        "dot": ("#F97316", "#DB2777"),
        "bg": {"linear": ("#FFF8F4", "#FEF3EC", "#FDF9F0"),
               "r1": "#FFB09E", "r2": "#FCD698", "solid": "#FDECE4"},
        "tokens": {**_ANKI_BASE,
                   "paper": "#FFF7F2", "paper2": "#FDECE6", "line": "#F6DFD3",
                   "brand": "#EA580C", "brand2": "#9A3412",
                   "brand_soft": "#FFEDD5", "accent": "#DB2777",
                   "accent_soft": "#FCE7F3"},
    },
    "anki-lagoon": {
        "name": "潟湖", "dark": False, "anki": True,
        "dot": ("#06B6D4", "#6366F1"),
        "bg": {"linear": ("#F4FDFD", "#EEFAFB", "#F1F6FF"),
               "r1": "#8AE4E4", "r2": "#A6C4FA", "solid": "#E6F6F7"},
        "tokens": {**_ANKI_BASE,
                   "paper": "#F3FBFC", "paper2": "#E5F8F9", "line": "#D8EEF1",
                   "brand": "#0891B2", "brand2": "#155E75",
                   "brand_soft": "#CFFAFE", "accent": "#6366F1",
                   "accent_soft": "#E0E7FF"},
    },
}

DEFAULT_THEME = "anki-mint"


def theme_ids() -> list[str]:
    return list(THEMES.keys())


def theme_info(tid: str) -> dict:
    return THEMES.get(tid) or THEMES[DEFAULT_THEME]


def theme_tokens(tid: str) -> dict:
    return theme_info(tid)["tokens"]


def theme_is_dark(tid: str) -> bool:
    return bool(theme_info(tid)["dark"])


def theme_gradient(tid: str | None) -> dict | None:
    return theme_info(tid or DEFAULT_THEME).get("bg")


def paint_page_bg(p: QPainter, rect, tid: str | None):
    """把当前 Anki 主题的渐变底色铺满 rect（页面底层 / 设置页 / 复习 chrome）。"""
    info = theme_info(tid or DEFAULT_THEME)
    bg = info.get("bg")
    r = QRectF(rect)
    if not bg:
        p.fillRect(r, QColor(info["tokens"]["paper"]))
        return
    p.setRenderHint(QPainter.Antialiasing, True)
    l0, l1, l2 = bg["linear"]
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0.0, QColor(l0))
    g.setColorAt(0.52, QColor(l1))
    g.setColorAt(1.0, QColor(l2))
    p.fillRect(r, g)

    for (px, py), col, rad in (((0.88, 0.08), bg["r1"], 0.56),
                               ((0.06, 0.92), bg["r2"], 0.58)):
        rg = QRadialGradient(QPointF(r.left() + r.width() * px,
                                     r.top() + r.height() * py),
                             max(r.width(), r.height()) * rad)
        c = QColor(col)
        c.setAlphaF(0.92)
        c0 = QColor(col)
        c0.setAlpha(0)
        rg.setColorAt(0, c)
        rg.setColorAt(1, c0)
        p.fillRect(r, rg)

