# -*- coding: utf-8 -*-
"""把关键截图拼成一张总览图。"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "shots")
OUT = os.path.join(SHOTS, "overview.png")

ITEMS = [
    ("01-today.png", "今日"),
    ("02-library.png", "记忆"),
    ("03-deck.png", "卡包详情"),
    ("13-review-single-judged.png", "复习 · 单选判定"),
    ("15-review-multi-judged.png", "复习 · 多选判定"),
    ("16-dark-today.png", "深色模式"),
]

CW, CH = 430, 880
GAP, PAD, TOP = 24, 40, 104
COLS, ROWS = 3, 2
W = PAD * 2 + COLS * CW + (COLS - 1) * GAP
H = TOP + ROWS * (CH + 40) + PAD

sheet = Image.new("RGB", (W, H), "#F3F0E8")
d = ImageDraw.Draw(sheet)
try:
    f_title = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 28)
    f_sub = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 14)
    f_cell = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 15)
except Exception:
    f_title = f_sub = f_cell = ImageFont.load_default()

d.text((PAD, 18), "FrogLog · 蛙记  —  PySide6 桌面版", font=f_title, fill="#242721")
d.text((PAD, 60), "同一套竖屏界面，手机与电脑一致；界面用浮卡的方式搭（app.py / theme.py / widgets.py / pages）",
       font=f_sub, fill="#73766F")

for i, (name, label) in enumerate(ITEMS):
    r, c = divmod(i, COLS)
    x = PAD + c * (CW + GAP)
    y = TOP + r * (CH + 40)
    img = Image.open(os.path.join(SHOTS, name)).convert("RGB").resize((CW, CH))
    mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, CW - 1, CH - 1], radius=18, fill=255)
    sheet.paste(img, (x, y), mask)
    d.rounded_rectangle([x, y, x + CW - 1, y + CH - 1], radius=18, outline="#D8D4C6", width=2)
    d.text((x + 2, y - 24), label, font=f_cell, fill="#3B3F39")

sheet.save(OUT, quality=92)
print("saved", OUT, sheet.size)
