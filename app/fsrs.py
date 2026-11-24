# -*- coding: utf-8 -*-
"""
fsrs.py - FSRS-6（Anki 26 默认参数）。

公式与常量取自 fsrs-rs 6.6.1：
  · 默认参数 21 个（inference.rs DEFAULT_PARAMETERS）
  · 遗忘曲线 R(t,S) = (1 + t/S * factor) ** (-decay)，decay = w[20]
  · 稳定性更新：初始 / 同日 / 遗忘 / 成功 四支
  · 难度更新：线性阻尼 + 均值回归（w[6]/w[7]）
  · 间隔 = S / factor * (retention ** (-1/decay) - 1)
"""
from __future__ import annotations

import math
import random

# fsrs 6.6.1 默认参数（Anki 26 新卡片默认使用）
PARAMS = [
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
    1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
    1.8729, 0.5425, 0.0912, 0.0658, 0.1542,
]

DESIRED_RETENTION = 0.9
S_MIN, S_MAX = 0.001, 36500.0
D_MIN, D_MAX = 1.0, 10.0
DAY_MS = 86_400_000.0

LEARN_STEPS = (1, 10)      # 分钟（Anki 默认）
RELEARN_STEPS = (10,)      # 分钟
LEECH_THRESHOLD = 8        # Anki 默认：累计遗忘 8 次算 leech
GRADUATING_IV = 1.0        # 毕业间隔（天）
EASY_IV = 4.0              # 轻松间隔（天）


def _constants(w):
    decay = -w[20]
    factor = math.exp(math.log(0.9) / decay) - 1.0
    return decay, factor


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def retrievability(t_days: float, s: float, w=PARAMS) -> float:
    if s <= 0:
        return 0.0
    decay, factor = _constants(w)
    return (1.0 + t_days / s * factor) ** decay


def next_interval(stability: float, desired: float = DESIRED_RETENTION, w=PARAMS) -> float:
    decay, factor = _constants(w)
    if factor <= 0:
        return max(1.0, stability)
    val = stability / factor * (desired ** (1.0 / decay) - 1.0)
    return _clamp(val, S_MIN, S_MAX)


def init_state(rating: int, w=PARAMS):
    """首次评分：rating 1..4。"""
    s = max(S_MIN, w[rating - 1])
    d = w[4] - math.exp(w[5] * (rating - 1)) + 1.0
    return s, _clamp(d, D_MIN, D_MAX)


def _short_term(s: float, rating: int, w=PARAMS) -> float:
    raw = math.exp(w[17] * (rating - 3.0 + w[18])) * (s ** -w[19])
    if rating >= 2:
        return s * max(raw, 1.0)
    return s * raw


def _next_difficulty(d: float, rating: int, w=PARAMS) -> float:
    delta_d = -w[6] * (rating - 3.0)
    nd = d + (10.0 - d) * delta_d / 9.0
    easy_d = w[4] - math.exp(3.0 * w[5]) + 1.0
    mean_d = w[7] * (easy_d - nd) + nd
    return _clamp(mean_d, D_MIN, D_MAX)


def _next_stability(s: float, d: float, r: float, rating: int,
                    delta_days: float, w=PARAMS) -> float:
    if delta_days <= 0.0:
        return _clamp(_short_term(s, rating, w), S_MIN, S_MAX)
    if rating == 1:
        raw = (w[11] * (d ** -w[12]) * ((s + 1.0) ** w[13] - 1.0)
               * math.exp((1.0 - r) * w[14]))
        floor = s / math.exp(w[17] * w[18])
        return _clamp(min(raw, floor), S_MIN, S_MAX)
    hard = w[15] if rating == 2 else 1.0
    easy = w[16] if rating == 4 else 1.0
    inc = (math.exp(w[8]) * (11.0 - d) * (s ** -w[9])
           * (math.exp((1.0 - r) * w[10]) - 1.0) * hard * easy)
    return _clamp(s * (1.0 + inc), S_MIN, S_MAX)


def fmt_interval(days: float) -> str:
    if days <= 0:
        return "0 分钟"
    mins = days * 1440
    if mins < 60:
        return f"{max(1, round(mins))} 分钟"
    if mins < 1440:
        return f"{round(mins / 60)} 小时"
    if days < 30:
        return f"{round(days)} 天"
    if days < 365:
        return f"{round(days / 30)} 个月"
    return f"{days / 365:.1f} 年"


def _hard_delay(steps, idx: int) -> float:
    """Anki 的 Hard 延迟：第一步取 (step0+step1)/2，其余步骤取当前步骤。"""
    idx = min(idx, len(steps) - 1)
    cur = steps[idx]
    if idx == 0:
        if len(steps) > 1:
            return (steps[0] + steps[1]) / 2.0
        return min(cur * 1.5, cur + 1440)   # 只有一步时 1.5 倍，最多 +1 天
    return cur


def _round(x: float) -> int:
    """Anki/Rust 的 round 语义：.5 一律向上（Python 内建 round 是银行家舍入）。"""
    return int(math.floor(float(x) + 0.5))


def _constrained_bounds(interval: float, minimum: int, maximum: int) -> tuple[int, int]:
    """Anki states/fuzz.rs:constrained_fuzz_bounds 的同款实现。"""
    minimum = min(minimum, maximum)
    interval = min(max(float(interval), float(minimum)), float(maximum))
    delta = _fuzz_delta(interval)
    lower = _round(interval - delta)
    upper = _round(interval + delta)
    lower = min(max(lower, minimum), maximum)
    upper = min(max(upper, minimum), maximum)
    if upper == lower and upper > 2 and upper < maximum:
        upper = lower + 1
    return lower, upper


def _learning_fuzz(secs: int, seed: int) -> int:
    """Anki answering/learning.rs:learning_ivl_with_fuzz（+25%，最多 +300 秒）。"""
    if secs <= 0:
        return secs
    upper = secs + int(min(secs * 0.25, 300.0))
    if upper <= secs:
        return secs
    return random.Random(seed).randrange(secs, upper)


SIBLING_MODIFIER_RANGE = (1.0, 0.8, 0.6, 0.4, 0.2, 0.000001, 0.2, 0.4, 0.6, 0.8, 1.0)


def _easy_days_weights(easy_days, weekday0: int, lo: int, hi: int,
                       counts: list | None) -> dict:
    """Anki load_balancer.rs:calculate_easy_days_modifiers 的同款实现。"""
    if not easy_days:
        return {}
    vals = list(easy_days)[:7]
    while len(vals) < 7:
        vals.append(1.0)
    if all(abs(float(v) - 1.0) < 1e-9 for v in vals):
        return {}                       # 全正常：不改变任何权重
    days = list(range(lo, hi + 1))
    review_counts = [(counts[d] if counts and 0 <= d < len(counts) else 0) for d in days]
    weekdays = [(weekday0 + d) % 7 for d in days]
    load = {0.0: 0.0001, 0.5: 0.5, 1.0: 1.0}
    percents = [load.get(round(float(vals[wd]), 2), 1.0) for wd in weekdays]
    total_count = sum(review_counts)
    total_pct = sum(percents)
    out = {}
    for i, d in enumerate(days):
        v = round(float(vals[weekdays[i]]), 2)
        if v == 0.5:
            other_count = total_count - review_counts[i]
            other_pct = total_pct - 0.5
            threshold = (other_count / other_pct) if other_pct > 0 else 0.0
            normalized = review_counts[i] / 0.5
            out[d] = 0.0001 if normalized > threshold else 1.0
        else:
            out[d] = 0.0001 if v == 0.0 else 1.0
    return out


def _review_interval(interval: float, minimum: float, maximum: float,
                     seed: int, counts: list | None = None,
                     sibling_days: list | None = None,
                     easy_days=None, weekday0: int = 0) -> float:
    """Anki 的 with_review_fuzz：有 Load Balancer 数据就加权选日，否则退化为普通 fuzz。"""
    lo, hi = _constrained_bounds(interval, int(minimum), int(maximum))
    rng = random.Random(seed)
    if counts and interval <= 90 and minimum <= 90:
        weights = []
        for d in range(lo, hi + 1):
            cnt = counts[d] if 0 <= d < len(counts) else 0
            if cnt <= 0:
                # 这天没有卡：给满权重（Anki: review_count == 0 → 1.0）
                w = 1.0
            else:
                w = (1.0 / cnt) ** 2.15 * (1.0 / max(1, d)) ** 3
            weights.append((d, w))
        # 轻松日：某些星期几少排卡（Anki Easy Days）
        esay = _easy_days_weights(easy_days, weekday0, lo, hi, counts)
        if esay:
            for i, (d, w) in enumerate(weights):
                weights[i] = (d, w * esay.get(d, 1.0))
        # 兄弟卡：同笔记的卡不要挤在同一天（±5 天按 Anki 的系数衰减）
        if sibling_days:
            for i, (d, w) in enumerate(weights):
                mod = 1.0
                for sday in sibling_days:
                    step = d - int(sday)
                    if -5 <= step <= 5:
                        mod *= SIBLING_MODIFIER_RANGE[step + 5]
                weights[i] = (d, w * mod)
        total = sum(w for _d, w in weights)
        if total > 0:
            pick = rng.random() * total
            acc = 0.0
            for d, w in weights:
                acc += w
                if pick <= acc:
                    return float(d)
            return float(weights[-1][0])
    factor = rng.random()
    return float(lo + int(factor * (1 + hi - lo)))


FUZZ_RANGES = ((2.5, 7.0, 0.15), (7.0, 20.0, 0.10), (20.0, float("inf"), 0.05))


def _fuzz_delta(interval: float) -> float:
    if interval < 2.5:
        return 0.0
    d = 1.0
    for lo, hi, factor in FUZZ_RANGES:
        d += factor * max(min(interval, hi) - lo, 0.0)
    return d


def _seed(card_id, reps: int) -> int:
    """Anki 的 get_fuzz_seed：card_id + reps（u64 回绕）。我们的 id 是字符串，先做稳定哈希。"""
    if isinstance(card_id, int):
        base = card_id
    else:
        import hashlib
        base = int.from_bytes(
            hashlib.sha1(str(card_id).encode("utf-8")).digest()[:8], "big")
    return (base + int(reps)) & 0xFFFFFFFFFFFFFFFF


def fuzz_factor(card_id, reps: int) -> float:
    """同一张卡、同一轮复习永远得到同一个模糊因子（0~1）。"""
    return random.Random(_seed(card_id, reps)).random()


def _fuzz(interval: float, max_iv: float, min_iv: float = 1.0,
          floor_iv: float = 0.0, factor: float | None = None) -> float:
    """Anki states/fuzz.rs 的 with_review_fuzz（含 minimum_review_fuzz_interval）。"""
    if interval < 2.5:
        return float(_round(interval))
    delta = _fuzz_delta(interval)
    lower = _round(interval - delta)
    upper = _round(interval + delta)
    lo = max(min_iv, min(lower, max_iv))
    hi = max(min_iv, min(upper, max_iv))
    if hi == lo and hi > 2 and hi < max_iv:
        hi += 1
    if floor_iv:
        lo = max(lo, int(floor_iv))
        hi = max(hi, lo)
    f = random.random() if factor is None else max(0.0, min(0.999999, factor))
    return float(lo + int(f * (1 + hi - lo)))


def _is_leech(lapses: int, threshold: int = LEECH_THRESHOLD) -> bool:
    """Anki states/review.rs:leech_threshold_met 的同款判定。"""
    if threshold <= 0:
        return False
    return lapses >= threshold and (lapses - threshold) % max(1, math.ceil(threshold / 2)) == 0


def _cfg(cfg: dict | None) -> dict:
    base = {
        "learn_steps": list(LEARN_STEPS),
        "relearn_steps": list(RELEARN_STEPS),
        "graduating": GRADUATING_IV,
        "easy": EASY_IV,
        "retention": DESIRED_RETENTION,
        "max_interval": S_MAX,
        "fuzz": True,
    }
    if cfg:
        base.update({k: v for k, v in cfg.items() if v is not None})
    return base


def step(card: dict, rating: int, now: int, fuzz: bool = True,
         cfg: dict | None = None) -> dict:
    """rating: 0 重来 / 1 困难 / 2 记住 / 3 轻松（对应 FSRS 1..4）。"""
    c = _cfg(cfg)
    LEARN_STEPS = tuple(c["learn_steps"]) or (1,)
    RELEARN_STEPS = tuple(c["relearn_steps"]) or (10,)
    GRADUATING_IV = float(c["graduating"])
    EASY_IV = float(c["easy"])
    MAX_IV = float(c["max_interval"])
    RETENTION = min(0.99, max(0.70, float(c["retention"])))
    w = PARAMS
    r = int(rating) + 1
    # Anki 的 fuzz 种子：card_id + reps（确定性）
    seed = _seed(card.get("id") or "", int(card.get("reps") or 0))
    load_counts = c.get("load_counts") if c.get("load_balance", True) else None
    sibling_days = c.get("sibling_days") or []
    easy_days = c.get("easy_days")
    weekday0 = int(c.get("weekday0") or 0)
    s = float(card.get("stability") or 0.0)
    d = float(card.get("difficulty") or 0.0)
    state = card.get("state") or ("review" if card.get("reps") else "new")
    step_i = int(card.get("step") or 0)
    lapses = int(card.get("lapses") or 0)
    reps = int(card.get("reps") or 0)
    last = int(card.get("last_review") or 0)
    delta = 0 if not last else int(max(0, now - last) // DAY_MS)
    if s <= 0.0 or d <= 0.0:
        # 老数据/迁移数据可能没有记忆状态，按本次评分初始化
        s0, d0 = init_state(r, w)
        s = s if s > 0.0 else s0
        d = d if d > 0.0 else d0
    minutes = 0.0
    interval = 0.0

    def graduate(easy: bool = False):
        # 新卡毕业走"毕业/轻松间隔"；重学毕业走重学后新算的 FSRS 间隔
        nonlocal state, step_i, interval, minutes
        was_relearn = (state == "relearning")
        state, step_i, minutes = "review", 0, 0.0
        if was_relearn:
            interval = max(1.0, next_interval(s, desired=RETENTION, w=w))
            if fuzz and c.get("fuzz", True):
                interval = _review_interval(interval, max(1.0, 1.0), MAX_IV,
                                            seed, load_counts, sibling_days,
                                            easy_days, weekday0)
            interval = _clamp(float(interval), 1.0, MAX_IV)
        else:
            interval = EASY_IV if easy else GRADUATING_IV

    if state == "new":
        s, d = init_state(r, w)
        if r == 1:
            state, step_i, minutes = "learning", 0, LEARN_STEPS[0]
        elif r == 2:
            state, step_i = "learning", 0
            minutes = _hard_delay(LEARN_STEPS, 0)
        elif r == 3:
            if len(LEARN_STEPS) > 1:
                state, step_i, minutes = "learning", 1, LEARN_STEPS[1]
            else:
                graduate()
        else:
            graduate(easy=True)

    elif state in ("learning", "relearning"):
        if s > 0:
            s = _next_stability(s, d, retrievability(0.0, s, w), r, 0.0, w)
        steps = LEARN_STEPS if state == "learning" else RELEARN_STEPS
        if r == 1:
            step_i = 0
            minutes = steps[0]
        elif r == 2:
            minutes = _hard_delay(steps, step_i)
        elif r == 3:
            if step_i + 1 < len(steps):
                step_i += 1
                minutes = steps[step_i]
            else:
                graduate()
        else:
            graduate(easy=True)
        if r >= 2:
            d = _next_difficulty(d, r, w)

    else:  # review
        r_ret = retrievability(delta, s, w)
        s = _next_stability(s, d, r_ret, r, delta, w)
        d = _next_difficulty(d, r, w)
        if r == 1:
            lapses += 1
            state, step_i = "relearning", 0
            minutes = RELEARN_STEPS[0]
        else:
            state, step_i = "review", 0
            interval = max(1.0, next_interval(s, desired=RETENTION, w=w))
            prev_iv = float(card.get("interval") or 0.0)
            raw_round = round(interval)
            floor_iv = 0.0
            if prev_iv:
                if raw_round > prev_iv:
                    floor_iv = prev_iv + 1
                elif prev_iv <= interval + _fuzz_delta(interval):
                    floor_iv = prev_iv
            if fuzz and c.get("fuzz", True):
                interval = _review_interval(interval, max(1.0, floor_iv), MAX_IV,
                                            seed, load_counts, sibling_days,
                                            easy_days, weekday0)
            else:
                interval = float(_round(interval))
                if floor_iv:
                    interval = max(interval, floor_iv)
            interval = _clamp(float(interval), 1.0, MAX_IV)

    if minutes:
        secs = int(round(minutes * 60))
        if fuzz and c.get("fuzz", True):
            secs = _learning_fuzz(secs, seed)
        interval = secs / 86400.0
        due = now + secs * 1000
    else:
        interval = max(1.0, interval)
        # Anki：跨天的间隔按「天」对齐，到期日是当天 0 点 + N 天
        import time as _t
        tm = _t.localtime(now / 1000)
        day0 = _t.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday,
                          0, 0, 0, 0, 0, -1)) * 1000
        due = int(day0 + _round(interval) * DAY_MS)

    return {
        "state": state,
        "step": step_i,
        "stability": round(s, 6),
        "difficulty": round(d, 6),
        "interval": round(interval, 6),
        "reps": reps + 1,
        "lapses": lapses,
        "due": int(due),
        "label": fmt_interval(interval),
        "leech": _is_leech(lapses),
    }


def preview(card: dict, now: int, cfg: dict | None = None) -> dict:
    """四个按钮分别会变成什么间隔（和实评同一套确定性 fuzz，所以显示=落库）。"""
    return {r: step(card, r, now, fuzz=True, cfg=cfg)["label"]
            for r in range(4)}
