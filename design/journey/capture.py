# -*- coding: utf-8 -*-
"""征途设计稿批量出图：Edge 无头 780x1900 → 裁 780x1688（390x844 @2x）→ 拼总览。

用法：
    python capture.py                # 出全部 7 屏 + 状态图 + 总览
    python capture.py journey        # 只出一屏
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_shots")
# 走 ASCII 联接，避免中文路径进入 Edge 命令行
BASE = "file:///D:/re-tools/ebbinghaus/design/journey/index.html"
RAW_W, RAW_H = 780, 1900
CROP = (0, 0, 780, 1688)

SCREENS = [
    ("journey", "01 征途 · 总览"),
    ("quests",  "02 征途 · 任务"),
    ("party",   "03 征途 · 副本"),
    ("rewards", "04 征途 · 奖励"),
    ("settle",  "05 每日结算"),
    ("levelup", "06 升级弹层"),
    ("study",   "07 学习页 · 顶栏计时"),
]

# 额外出的状态图（不进总览）
EXTRA = [
    ("journey-active", "only=journey&quest=active"),
    ("journey-paused", "only=journey&quest=paused"),
    ("journey-done",   "only=journey&quest=done"),
    ("study-paused",   "only=study&pill=paused"),
    ("study-idle",     "only=study&pill=idle"),
]

INFO = [
    ("总览", "任务卡三态 + 首领 + 最近 7 天"),
    ("记录", "完成记录，按天分组（滴答清单式）"),
    ("副本", "队伍共斗，按伤害分红"),
    ("奖励", "金币商店（自建）+ 徽章墙"),
    ("结算", "24:00 自动结算，漏做扣血"),
    ("升级", "生命上限/回满/属性点"),
    ("学习页", "顶栏胶囊：只在学习页计时"),
    ("入口", "征途页内四个分段，不新增底部 tab"),
]


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
    print(f"OK   {name:14s} {im.size[0]}x{im.size[1]}")
    return dst


def font(size, bold=False):
    for p in (r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
              r"C:\Windows\Fonts\msyh.ttc"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build_sheet(made):
    cell_w, cell_h = 390, 844
    pad_x, pad_y = 54, 128
    gap_x, gap_y = 26, 42
    cols, rows = 4, 2
    W = pad_x * 2 + cols * cell_w + (cols - 1) * gap_x
    H = pad_y + rows * (cell_h + gap_y) + 26
    sheet = Image.new("RGB", (W, H), "#F3F0E8")
    d = ImageDraw.Draw(sheet)

    f_title, f_sub = font(30, True), font(13)
    f_cap, f_h, f_k, f_v = font(13, True), font(16, True), font(12, True), font(12)

    d.text((pad_x, 22), "征途 · Habitica 玩法融合（任务 / 副本 / 奖励 / 结算）", font=f_title, fill="#242721")
    d.text((pad_x, 64), "纸白 + 墨绿 + 赭石沿用 APK 逆向配色；HP·XP·金币、习惯/每日/待办、连击、每日结算、副本、奖励商店来自 Habitica",
           font=f_sub, fill="#73766F")

    for i, (key, cap) in enumerate(SCREENS):
        r, c = divmod(i, cols)
        x = pad_x + c * (cell_w + gap_x)
        y = pad_y + r * (cell_h + gap_y)
        im = Image.open(made[key]).resize((cell_w, cell_h), Image.LANCZOS)
        mask = Image.new("L", (cell_w, cell_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, cell_w - 1, cell_h - 1], radius=22, fill=255)
        sheet.paste(im, (x, y), mask)
        d.rounded_rectangle([x, y, x + cell_w - 1, y + cell_h - 1], radius=22, outline="#D8D4C6", width=2)
        d.text((x + 4, y - 26), cap, font=f_cap, fill="#3B3F39")

    # 最后一格：说明
    idx = len(SCREENS)
    r, c = divmod(idx, cols)
    x = pad_x + c * (cell_w + gap_x)
    y = pad_y + r * (cell_h + gap_y)
    d.rounded_rectangle([x, y, x + cell_w - 1, y + cell_h - 1], radius=22,
                        fill="#FFFFFF", outline="#D8D4C6", width=2)
    tx, ty = x + 26, y + 34
    d.text((tx, ty), "这一版补齐了什么", font=f_h, fill="#242721")
    ty += 42
    for k, v in INFO:
        d.text((tx, ty), k, font=f_k, fill="#2F6A43")
        d.text((tx + 62, ty), v, font=f_v, fill="#3B3F39")
        ty += 32
    d.text((tx, ty + 8), "配色/圆角/字号沿用 PySide6 主题；", font=font(11.5), fill="#73766F")
    d.text((tx, ty + 28), "数值与状态机见 docs/JOURNEY-PLAN.md。", font=font(11.5), fill="#73766F")

    dst = os.path.join(OUT, "overview.png")
    sheet.save(dst)
    print("overview:", dst, sheet.size)


def main():
    os.makedirs(OUT, exist_ok=True)
    profile = os.path.join(os.environ.get("TEMP", "."), "edge-journey-profile")
    want = sys.argv[1:] or [s for s, _ in SCREENS]
    made = {}
    for key, _ in SCREENS:
        if key in want:
            p = shot(key, f"only={key}", profile)
            if p:
                made[key] = p
    if all(k in made for k, _ in SCREENS):
        build_sheet(made)
    if not sys.argv[1:]:
        for name, query in EXTRA:
            shot(name, query, profile)
        shot("journey-dark", "only=journey&theme=dark", profile)


if __name__ == "__main__":
    main()
