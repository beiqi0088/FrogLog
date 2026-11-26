# -*- coding: utf-8 -*-
"""生成 FrogLog 安卓图标（扁平矢量风，参考「砚卡」的奶油色可爱吉祥物）。
运行：python3 scripts/make_icon.py  ->  assets/icon.png (1024x1024)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

S = 4                      # 超采样倍数
W = H = 1024 * S
OUT = Path(__file__).resolve().parent.parent / "assets" / "icon.png"

BG = (246, 241, 227)
BODY = (234, 223, 203)
BODY_DARK = (223, 210, 187)
BODY_LIGHT = (243, 234, 218)
EYE = (43, 47, 68)
CHEEK = (240, 180, 174)
MOUTH = (122, 74, 72)
TONGUE = (214, 128, 124)
GREEN = (111, 158, 107)
GREEN_DARK = (90, 134, 87)
CARD = (255, 255, 255)
CARD_LINE = (214, 199, 174)
SHADOW = (231, 222, 205)


def sc(*vals):
    return [int(v * S) for v in vals]


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")

    # 地面软阴影
    d.ellipse(sc(250, 780, 774, 900), fill=SHADOW)

    # 耳朵/小角（在身体后面）
    d.ellipse(sc(286, 268, 400, 382), fill=BODY_DARK)
    d.ellipse(sc(624, 268, 738, 382), fill=BODY_DARK)

    # 头顶嫩芽
    d.line(sc(512, 300, 512, 214), fill=GREEN_DARK, width=int(16 * S))
    d.ellipse(sc(470, 186, 522, 232), fill=GREEN)
    d.ellipse(sc(500, 176, 558, 228), fill=GREEN)

    # 身体
    d.ellipse(sc(206, 300, 818, 892), fill=BODY)
    d.ellipse(sc(238, 318, 786, 620), fill=BODY_LIGHT)

    # 眼睛
    for cx in (424, 600):
        d.ellipse(sc(cx - 60, 452, cx + 60, 592), fill=EYE)
        d.ellipse(sc(cx - 40, 470, cx - 8, 512), fill=(255, 255, 255))
        d.ellipse(sc(cx - 4, 528, cx + 12, 546), fill=(255, 255, 255))

    # 腮红
    d.ellipse(sc(330, 596, 438, 652), fill=CHEEK + (110,))
    d.ellipse(sc(586, 596, 694, 652), fill=CHEEK + (110,))

    # 嘴（张小口 + 小尖牙）
    d.pieslice(sc(462, 596, 562, 672), start=0, end=180, fill=MOUTH)
    d.ellipse(sc(492, 646, 532, 668), fill=TONGUE)
    d.polygon([tuple(sc(470, 604)), tuple(sc(492, 604)), tuple(sc(481, 632))],
              fill=(255, 255, 255))
    d.polygon([tuple(sc(532, 604)), tuple(sc(554, 604)), tuple(sc(543, 632))],
              fill=(255, 255, 255))

    # 脚
    d.ellipse(sc(330, 806, 482, 886), fill=BODY_DARK)
    d.ellipse(sc(542, 806, 694, 886), fill=BODY_DARK)

    # 怀里的卡片
    d.rounded_rectangle(sc(352, 700, 672, 862), radius=int(26 * S), fill=CARD,
                        outline=(231, 223, 208), width=int(4 * S))
    d.rounded_rectangle(sc(410, 780, 614, 800), radius=int(10 * S), fill=CARD_LINE)

    # 抱卡片的手臂
    d.ellipse(sc(300, 726, 396, 834), fill=BODY)
    d.ellipse(sc(628, 726, 724, 834), fill=BODY)
    d.arc(sc(300, 726, 396, 834), start=300, end=120, fill=BODY_DARK, width=int(6 * S))
    d.arc(sc(628, 726, 724, 834), start=60, end=240, fill=BODY_DARK, width=int(6 * S))

    img = img.resize((1024, 1024), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    print("saved", OUT, img.size)


if __name__ == "__main__":
    main()
