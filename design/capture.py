# -*- coding: utf-8 -*-
"""Batch capture all design screens with Edge headless, then crop to 390x844@2x."""
import subprocess, time, os, sys
from PIL import Image, ImageDraw, ImageFont

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"D:\我的下载\WorkBuddy库\逆向分析\ebbinghaus\design\_shots"
BASE = "http://127.0.0.1:8765/index.html"
RAW_W, RAW_H = 780, 1900
CROP = (0, 0, 780, 1688)

SCREENS = ["consent", "today", "review", "library", "deck", "plan", "insights", "settings"]

def shot(name, query, profile):
    raw = os.path.join(OUT, f"_raw_{name}.png")
    url = f"{BASE}?{query}&scale=2"
    cmd = [
        EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check",
        f"--user-data-dir={profile}",
        f"--window-size={RAW_W},{RAW_H}",
        "--virtual-time-budget=4000",
        f"--screenshot={raw}", url,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)
    if not os.path.exists(raw):
        print(f"FAIL {name}")
        return None
    im = Image.open(raw).convert("RGB").crop(CROP)
    dst = os.path.join(OUT, f"{name}.png")
    im.save(dst)
    os.remove(raw)
    print(f"OK {name} {im.size}")
    return dst

os.makedirs(OUT, exist_ok=True)
profile = os.path.join(os.environ.get("TEMP", "."), "edge-batch-profile")
made = {}
for s in SCREENS:
    made[s] = shot(s, f"only={s}", profile)

# 深色版：今日 / 洞察 / 复习
for s in ["today", "insights", "review"]:
    made[f"{s}-dark"] = shot(f"{s}-dark", f"only={s}&theme=dark", profile)

# ---------- 拼一张总览图（4 列 × 2 行，含标题） ----------
if all(made.get(s) for s in SCREENS):
    cell_w, cell_h = 390, 844
    pad_x, pad_y, gap_x, gap_y = 40, 76, 28, 34
    cols, rows = 4, 2
    W = pad_x * 2 + cols * cell_w + (cols - 1) * gap_x
    H = pad_y + 40 + rows * (cell_h + gap_y) + 20
    sheet = Image.new("RGB", (W, H), "#F3F0E8")
    d = ImageDraw.Draw(sheet)
    try:
        font_title = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 26)
        font_sub = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 15)
    except Exception:
        font_title = font_sub = ImageFont.load_default()

    d.text((pad_x, 24), "艾宾浩斯记忆曲线 · UI 设计稿", font=font_title, fill="#242721")
    d.text((pad_x, 58), "配色 / 文案 / 页面结构均来自 APK 1.0.2 逆向还原", font=font_sub, fill="#73766F")

    labels = {
        "consent": "00 合规门禁", "today": "01 今日", "review": "02 复习会话",
        "library": "03 记忆库", "deck": "04 记忆库详情", "plan": "05 计划",
        "insights": "06 洞察", "settings": "07 设置",
    }
    for i, s in enumerate(SCREENS):
        r, c = divmod(i, cols)
        x = pad_x + c * (cell_w + gap_x)
        y = pad_y + 40 + r * (cell_h + gap_y)
        im = Image.open(made[s]).resize((cell_w, cell_h), Image.LANCZOS)
        # 圆角遮罩
        mask = Image.new("L", (cell_w, cell_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, cell_w - 1, cell_h - 1], radius=22, fill=255)
        sheet.paste(im, (x, y), mask)
        d.rounded_rectangle([x, y, x + cell_w - 1, y + cell_h - 1], radius=22, outline="#D8D4C6", width=2)
        d.text((x + 4, y - 26), labels[s], font=font_sub, fill="#3B3F39")

    overview = os.path.join(OUT, "overview.png")
    sheet.save(overview)
    print("overview:", overview, sheet.size)
