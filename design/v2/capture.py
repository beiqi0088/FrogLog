# -*- coding: utf-8 -*-
"""Capture all v2 screens and compose a single overview sheet."""
import subprocess, os
from PIL import Image, ImageDraw, ImageFont

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"D:\我的下载\WorkBuddy库\逆向分析\ebbinghaus\design\v2\_shots"
BASE = "http://127.0.0.1:8765/v2/index.html"
RAW_W, RAW_H = 780, 1900
CROP = (0, 0, 780, 1688)

SCREENS = [
    ("consent", "00 合规门禁"),
    ("today", "01 今日"),
    ("memo", "02 浮墨记录"),
    ("split", "03 批量拆卡"),
    ("library", "04 记忆库"),
    ("deck", "05 卡包详情"),
    ("reviewqa", "06 复习 · 问答"),
    ("reviewsingle", "07 复习 · 单选"),
    ("reviewmulti", "08 复习 · 多选"),
    ("templates", "09 卡片模板"),
    ("plan", "10 计划"),
    ("insights", "11 洞察"),
    ("settings", "12 设置"),
]

def shot(key, name, profile):
    raw = os.path.join(OUT, f"_raw_{key}.png")
    url = f"{BASE}?only={key}&scale=2"
    subprocess.run([
        EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        f"--user-data-dir={profile}", f"--window-size={RAW_W},{RAW_H}",
        "--virtual-time-budget=5000", f"--screenshot={raw}", url,
    ], capture_output=True, timeout=120)
    if not os.path.exists(raw):
        print("FAIL", key); return None
    im = Image.open(raw).convert("RGB").crop(CROP)
    dst = os.path.join(OUT, f"{key}.png")
    im.save(dst); os.remove(raw)
    print("OK", key)
    return dst

os.makedirs(OUT, exist_ok=True)
profile = os.path.join(os.environ.get("TEMP", "."), "edge-v2-batch")
made = {k: shot(k, n, profile) for k, n in SCREENS}

# ---------------- overview ----------------
COLS, ROWS = 5, 3
CW, CH = 330, 714
PAD_X, PAD_Y, GX, GY, TOP = 44, 44, 22, 30, 96
W = PAD_X * 2 + COLS * CW + (COLS - 1) * GX
H = TOP + ROWS * (CH + GY) + PAD_Y

sheet = Image.new("RGB", (W, H), "#F3F0E8")
d = ImageDraw.Draw(sheet)
F = lambda n, s: ImageFont.truetype(rf"C:\Windows\Fonts\{n}", s)
f_title, f_sub, f_cell, f_small, f_tiny = F("msyhbd.ttc", 30), F("msyh.ttc", 15), F("msyhbd.ttc", 17), F("msyh.ttc", 13), F("msyh.ttc", 11)

d.text((PAD_X, 26), "浮卡 × 艾宾浩斯 · UI 设计 v2", font=f_title, fill="#242721")
d.text((PAD_X, 66), "外壳沿用 v1 的纸感；卡片皮肤 / 题型 / 浮墨 / 拆卡 来自桌面版「浮卡」", font=f_sub, fill="#73766F")

def tile(img, x, y, label):
    im = img.resize((CW, CH), Image.LANCZOS)
    mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, CW - 1, CH - 1], radius=20, fill=255)
    sheet.paste(im, (x, y), mask)
    d.rounded_rectangle([x, y, x + CW - 1, y + CH - 1], radius=20, outline="#D8D4C6", width=2)
    d.text((x + 2, y - 24), label, font=f_cell, fill="#3B3F39")

for i, (key, label) in enumerate(SCREENS):
    r, c = divmod(i, COLS)
    x = PAD_X + c * (CW + GX)
    y = TOP + 10 + r * (CH + GY)
    tile(Image.open(made[key]), x, y, label)

# 两张说明卡填满最后一行
INFO = [
    ("合并映射", [
        ("7 套卡片模板", "→ 卡片皮肤 .tpl-*"),
        ("问答 / 单选 / 多选", "→ 三种复习卡"),
        ("浮墨记录 + AI 拆题", "→ 速记弹层"),
        ("批量拆卡（序号行）", "→ 粘贴→预览→导入"),
        ("知识域 学习/工作/生活", "→ 记忆库首层筛选"),
        ("圆桌→铁盒→卡包→卡组", "→ 压成 卡包→卡组"),
    ]),
    ("设计变量", [
        ("--bg", "#FBF8F1", "#FBF8F1"),
        ("--primary", "#2F6A43", "#2F6A43"),
        ("--accent", "#BF5B38", "#BF5B38"),
        ("学习 / 工作 / 生活", "#2F6A43 #426A80 #B85D3C", None),
        ("卡片皮肤", "7 套，独立于外壳", None),
    ]),
]

for j, (title, rows) in enumerate(INFO):
    c = 3 + j
    x = PAD_X + c * (CW + GX)
    y = TOP + 10 + 2 * (CH + GY)
    d.rounded_rectangle([x, y, x + CW - 1, y + CH - 1], radius=20, fill="#FFFFFF", outline="#D8D4C6", width=2)
    d.text((x + 2, y - 24), title, font=f_cell, fill="#3B3F39")
    d.text((x + 20, y + 22), title, font=f_cell, fill="#242721")
    yy = y + 56
    for row in rows:
        if len(row) == 3 and row[2]:
            d.rounded_rectangle([x + 20, yy, x + 40, yy + 14], radius=4, fill=row[2], outline="#E4E1D6")
            d.text((x + 48, yy - 1), row[0], font=f_small, fill="#73766F")
            d.text((x + 48, yy + 17), row[1], font=f_tiny, fill="#242721")
            yy += 44
        elif len(row) == 3:
            d.text((x + 20, yy), row[0], font=f_small, fill="#73776F")
            d.text((x + 20, yy + 18), row[1], font=f_tiny, fill="#242721")
            yy += 44
        else:
            d.text((x + 20, yy), row[0], font=f_small, fill="#73766F")
            d.text((x + 20, yy + 18), row[1], font=f_tiny, fill="#242721")
            yy += 46

overview = os.path.join(OUT, "overview.png")
sheet.save(overview)
print("overview", sheet.size)
