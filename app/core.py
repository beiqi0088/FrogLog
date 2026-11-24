# -*- coding: utf-8 -*-
"""
core.py - 数据模型 / 调度算法 / JSON 存储 / 初始数据
调度算法移植自 APK 反编译结果（b4.v.T0）：SM-2 简化变体。
"""
from __future__ import annotations

import copy
import json
import math
import os
import time
import uuid
from typing import Any

DAY = 86_400_000

DEFAULT_DOMAINS = [
    {"id": "study", "name": "学习", "emoji": "📚"},
    {"id": "work", "name": "工作", "emoji": "💼"},
    {"id": "life", "name": "生活", "emoji": "🏠"},
]
LADDER = [1.0, 3.0, 7.0, 15.0, 30.0, 60.0]      # 前 6 次的固定阶梯
DEFAULT_EASE = 2.35

# Anki 卡组选项默认值（可按卡包覆盖）
DEFAULT_SCHED = {
    "learn_steps": [1, 10],
    "relearn_steps": [10],
    "graduating": 1.0,
    "easy": 4.0,
    "retention": 0.9,
    "new_per_day": 20,
    "review_per_day": 200,
    "max_interval": 36500.0,
    "fuzz": True,
    "easy_days": [1.0] * 7,     # 轻松日：周一..周日，1.0 正常 / 0.5 减少 / 0.0 最少
    "bury_new": False,          # 新卡作答后 bury 兄弟（Anki 26 默认关）
    "bury_reviews": False,      # 复习卡作答后 bury 兄弟（Anki 26 默认关）
    "load_balance": True,       # Load Balancer（Anki 26 默认开）
}
MIN_EASE, MAX_EASE = 1.3, 3.2


def uid(prefix: str = "") -> str:
    return (prefix + uuid.uuid4().hex[:10]) if prefix else uuid.uuid4().hex[:12]


def now_ms() -> int:
    return int(time.time() * 1000)


def _intersperse(one: list, two: list) -> list:
    """Anki queue/builder/intersperser.rs 的同款：按长度比例把 two 均匀插进 one。"""
    if not one:
        return list(two)
    if not two:
        return list(one)
    ratio = (len(one) + 1) / (len(two) + 1)
    out, i, j = [], 0, 0
    while i < len(one) and j < len(two):
        if (j + 1) * ratio < (i + 1):
            out.append(two[j])
            j += 1
        else:
            out.append(one[i])
            i += 1
    out.extend(one[i:])
    out.extend(two[j:])
    return out


def day_str(ts: int | None = None) -> str:
    """本地日期 YYYY-MM-DD（结算按本地 00:00 切日，不用 UTC）。"""
    t = time.localtime((ts if ts is not None else now_ms()) / 1000)
    return f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"


def prev_day_str(ts: int | None = None) -> str:
    t = time.localtime(((ts if ts is not None else now_ms()) / 1000) - 86400)
    return f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"



# ------------------------------------------------------------------ Anki 调度
ANKI = dict(
    learn_steps=(1, 10),        # 分钟
    relearn_steps=(10,),
    graduating_iv=1.0,          # 天
    easy_iv=4.0,
    start_ease=2.5,
    easy_bonus=1.30,
    hard_mult=1.20,
    lapse_mult=0.0,             # 0 = 遗忘后回到最小间隔
    interval_mod=1.0,
    min_iv=1.0,
    max_iv=36500.0,
    leech=8,
    fuzz_pct=0.05,
)

_DAY_MS = 86_400_000.0


def card_state(c: dict) -> str:
    st = c.get("state")
    if st:
        return st
    return "review" if c.get("reps") else "new"


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


def _fuzz(iv: float, pct: float) -> float:
    if iv < 3:
        return iv
    import random
    delta = max(1, int(round(iv * pct)))
    return max(1.0, iv + random.randint(-delta, delta))


def anki_schedule(card: dict, rating: int, now: int, fuzz: bool = True) -> dict:
    """Anki 的 SM-2 调度。rating: 0 重来 / 1 困难 / 2 记住 / 3 轻松。"""
    c = ANKI
    state = card_state(card)
    iv = float(card.get("interval") or 0.0)
    ease = float(card.get("ease") or c["start_ease"])
    reps = int(card.get("reps") or 0)
    lapses = int(card.get("lapses") or 0)
    step = int(card.get("step") or 0)
    minutes = 0.0
    steps = c["learn_steps"]

    if state == "new":
        if rating == 0:
            state, step, minutes = "learning", 0, steps[0]
        elif rating == 1:
            state, step, minutes = "learning", 0, steps[0]
        elif rating == 2:
            if len(steps) > 1:
                state, step, minutes = "learning", 1, steps[1]
            else:
                state, iv, ease = "review", c["graduating_iv"], c["start_ease"]
        else:
            state, iv, ease = "review", c["easy_iv"], c["start_ease"]

    elif state == "learning":
        if rating == 0:
            step, minutes = 0, steps[0]
        elif rating == 1:
            minutes = steps[min(step, len(steps) - 1)]
        elif rating == 2:
            step += 1
            if step >= len(steps):
                state, iv, ease = "review", c["graduating_iv"], c["start_ease"]
            else:
                minutes = steps[step]
        else:
            state, iv, ease = "review", c["easy_iv"], c["start_ease"]

    elif state == "relearning":
        if rating in (0, 1):
            minutes = c["relearn_steps"][0]
        else:
            state, iv = "review", max(c["min_iv"], iv)
            minutes = 0

    else:  # review
        if rating == 0:
            lapses += 1
            ease = max(1.3, ease - 0.20)
            iv = max(c["min_iv"], iv * c["lapse_mult"]) if c["lapse_mult"] else c["min_iv"]
            state, minutes = "relearning", c["relearn_steps"][0]
        elif rating == 1:
            iv = max(c["min_iv"], iv * c["hard_mult"])
            ease = max(1.3, ease - 0.15)
        elif rating == 2:
            iv = max(c["min_iv"], iv * ease)
        else:
            iv = max(c["min_iv"], iv * ease * c["easy_bonus"])
            ease = min(5.0, ease + 0.15)
        if state == "review":
            iv = min(c["max_iv"], iv * c["interval_mod"])
            if fuzz:
                iv = _fuzz(iv, c["fuzz_pct"])

    if minutes:
        interval = minutes / 1440.0
        due = now + int(minutes * 60_000)
    else:
        interval = max(c["min_iv"], iv)
        due = now + int(interval * _DAY_MS)

    return {
        "state": state,
        "step": step,
        "interval": round(interval, 4),
        "ease": round(ease, 4),
        "reps": reps + 1,
        "lapses": lapses,
        "due": int(due),
        "label": fmt_interval(interval),
        "leech": lapses >= c["leech"],
    }


def anki_preview(card: dict, now: int) -> dict:
    """四个按钮分别会变成什么间隔（不落库、不加模糊）。"""
    return {r: anki_schedule(card, r, now, fuzz=False)["label"] for r in range(4)}


# ---------------------------------------------------------------- 调度

def schedule(interval: float, reps: int, ease: float, lapses: int,
             rating: int, now: int) -> dict:
    """rating: 0 重来 / 1 困难 / 2 记住 / 3 轻松。返回新调度字段。"""
    prev = max(0.0, interval)
    e = ease if ease > 0 else DEFAULT_EASE

    if rating == 0:
        return {
            "interval": 60_000 / DAY,
            "reps": 0,
            "ease": max(MIN_EASE, e - 0.2),
            "lapses": lapses + 1,
            "due": now + 60_000,
            "label": "1 分钟",
        }
    if rating == 1:
        iv = max(1.0, prev * 1.2) if (reps > 0 and prev >= 1.0) else 1.0
        return {
            "interval": iv,
            "reps": max(1, reps),
            "ease": max(MIN_EASE, e - 0.15),
            "lapses": lapses,
            "due": now + int(DAY * iv),
            "label": interval_label(iv),
        }
    if rating == 2:
        iv = LADDER[max(0, reps)] if reps < 6 else max(1.0, prev * e)
        return {
            "interval": iv,
            "reps": reps + 1,
            "ease": e,
            "lapses": lapses,
            "due": now + int(DAY * iv),
            "label": interval_label(iv),
        }
    # rating == 3
    if reps <= 0:
        iv = 3.0
    elif reps < 6:
        iv = LADDER[reps] * 1.35
    else:
        iv = max(3.0, (e + 0.3) * prev)
    return {
        "interval": iv,
        "reps": reps + 1,
        "ease": min(MAX_EASE, e + 0.15),
        "lapses": lapses,
        "due": now + int(DAY * iv),
        "label": interval_label(iv),
    }


def interval_label(days: float) -> str:
    if days < 1 / 24:
        return f"{max(1, round(days * 1440))} 分钟"
    if days < 1:
        return f"{max(1, round(days * 24))} 小时"
    if days < 30:
        return f"{max(1, round(days))} 天"
    if days < 365:
        m = days / 30
        return "1 个月" if m < 2 else f"{m:.1f} 个月"
    return f"{days / 365:.1f} 年"


def retention(card: dict, now: int) -> float:
    """指数衰减，半衰期 = 当前间隔。"""
    last = card.get("last_review")
    if not last:
        return 0.35 if card.get("reps", 0) == 0 else 0.75
    elapsed = max(0, now - last) / DAY
    iv = max(1.0, card.get("interval", 1.0))
    return max(0.0, min(1.0, math.exp(-0.6931471805599453 * elapsed / iv)))


# ---------------------------------------------------------------- 存储

def data_path() -> str:
    if os.environ.get("ANDROID_PRIVATE"):          # 安卓：应用私有目录
        base = os.environ["ANDROID_PRIVATE"]
    else:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "FloCardLite")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "state.json")


def keep_device_sync_settings(old_state: dict, new_state: dict) -> None:
    """导入云端数据时，保住本机的同步配置。

    settings.sync 里放的是「这台设备」的账号与密钥（七牛 AK/SK、坚果云应用密码、
    局域网口令），它不该跟着卡片数据一起被别的设备覆盖：
    以前从云端拉一次数据，另一台设备上空着的 sync 就会把本机密钥冲掉，
    于是「上次还好好的，这次同步就失败了」。这里让本机配置永远优先，
    只有本机没配过（空）时才用云端带来的那份兜底。
    """
    old_sync = ((old_state or {}).get("settings") or {}).get("sync")
    if not old_sync:
        return
    new_state.setdefault("settings", {})["sync"] = copy.deepcopy(old_sync)


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or data_path()
        self.state: dict[str, Any] = {}
        self._idx_key = None
        self._card_idx: dict[str, dict] = {}
        self._deck_idx: dict[str, dict] = {}
        self._by_deck: dict[str, list[dict]] = {}
        self._dirty = False          # 高频操作先记脏，稍后再写盘
        self.load()

    def _ensure_indexes(self):
        """按需建立 id → 卡片/卡包 与卡包 → 卡片 的索引。

        Python 侧大量 O(n) 查找（card()/deck()/cards_of()）改成 O(1)；
        列表对象或长度变化时自动重建，不要求调用方手动维护。
        """
        cards, decks = self.cards, self.decks
        key = (id(cards), len(cards), id(decks), len(decks))
        if key == self._idx_key:
            return
        self._idx_key = key
        self._card_idx = {c["id"]: c for c in cards}
        self._deck_idx = {d["id"]: d for d in decks}
        by_deck: dict[str, list[dict]] = {}
        for c in cards:
            by_deck.setdefault(c["deck_id"], []).append(c)
        self._by_deck = by_deck

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception:
                self.state = {}
        if not self.state.get("cards"):
            self.state = seed()
            self.save()
        # 上次异常退出时可能留下「正在跑表」的标记：
        # 把关机前那一段补进 acc（最多补一个任务时长，避免把关机时间也算成学习）
        _q = self.state.get("quest")
        if isinstance(_q, dict) and _q.get("running_since"):
            _cap = int(_q.get("target_ms") or 15 * 60_000)
            _delta = max(0, now_ms() - int(_q["running_since"]))
            _q["acc_ms"] = int(_q.get("acc_ms") or 0) + min(_delta, _cap)
            _q["running_since"] = 0
        for _c in self.state.get("cards") or []:
            _c.setdefault("note_id", _c.get("id"))
        self.state.setdefault("domains", [dict(d) for d in DEFAULT_DOMAINS])
        self.state.setdefault("rounds", [])
        for d in self.state.get("decks", []):
            d.setdefault("parent_id", None)
            d.setdefault("created", now_ms())
        # 一次性统一：所有卡片默认用「天蓝薰衣」
        if not self.state.get("templates_unified"):
            for d in self.state.get("decks", []):
                d["template"] = "sky"
            self.state.setdefault("settings", {})["default_template"] = "sky"
            self.state["templates_unified"] = True
            self.save()

    def save_deferred(self):
        """高频操作（评分/计时）用：只标记脏，由主窗口的空闲定时器统一落盘。"""
        self._dirty = True

    def flush(self) -> None:
        """把延迟的写入补上（切页面/关窗/定时器都会调）。"""
        if getattr(self, "_dirty", False):
            self.save()

    def save(self, bump: bool = True) -> bool:
        """写盘：优先原子替换；文件被占用（另一实例开着）时重试并退化为直接写。"""
        self._dirty = False
        import time as _t
        if bump:
            self.state["updated_at"] = int(_t.time() * 1000)
        payload = json.dumps(self.state, ensure_ascii=False, separators=(",", ":"))
        tmp = self.path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(payload)
        except Exception:
            tmp = None
        if tmp:
            for _ in range(6):
                try:
                    os.replace(tmp, self.path)
                    return True
                except PermissionError:
                    _t.sleep(0.06)
                except Exception:
                    break
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(payload)
            return True
        except Exception:
            return False
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass

    # ---- 同步 ----
    def export_bytes(self, bump: bool = True) -> bytes:
        """导出整份状态。bump=False 用于应答局域网 GET：只读，不该改时间戳。"""
        if bump:
            import time as _t
            self.state["updated_at"] = int(_t.time() * 1000)
        return json.dumps(self.state, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")

    def updated_at(self) -> int:
        return int(self.state.get("updated_at") or 0)

    def import_bytes(self, data: bytes, force: bool = True) -> tuple[bool, str]:
        """导入远端数据。force=False 时只在远端更新时覆盖本地。"""
        try:
            remote = json.loads(data.decode("utf-8"))
        except Exception as e:
            return False, f"数据格式不对：{e}"
        if not isinstance(remote, dict) or not remote.get("cards"):
            return False, "远端数据缺少卡片，已忽略"
        r_at = int(remote.get("updated_at") or 0)
        if not force and r_at <= self.updated_at():
            return False, "云端不是更新的版本"
        # 备份本地
        try:
            if os.path.exists(self.path):
                import shutil
                shutil.copyfile(self.path, self.path + ".bak")
        except Exception:
            pass
        keep_device_sync_settings(self.state, remote)
        self.state = remote
        # 用远端的时间戳落盘：否则「刚上传完又被判成云端更新」，
        # 局域网同步会来回互相覆盖（上传完下一次又触发下载）。
        self.save(bump=not r_at)
        # 数据换了，选中/顺序等 UI 状态跟随
        return True, "已导入远端数据"

    # 便捷访问
    @property
    def decks(self) -> list[dict]:
        return self.state["decks"]

    @property
    def cards(self) -> list[dict]:
        return self.state["cards"]

    @property
    def reviews(self) -> list[dict]:
        return self.state.setdefault("reviews", [])

    @property
    def checkins(self) -> list[dict]:
        return self.state.setdefault("checkins", [])

    def add_checkin(self, minutes: int = 25) -> int:
        """记一次征途（学习任务完成），返回累计次数。"""
        self.checkins.append({"at": now_ms(), "mins": int(minutes)})
        self.save()
        return len(self.checkins)

    # ---------------------------------------------------------- 征途任务
    # 状态机：idle --claim--> active --(只在学习页跑表)--> 满时长 --> done
    QUEST_TARGETS = (15,)

    @property
    def quest(self) -> dict:
        q = self.state.setdefault("quest", {})
        q.setdefault("status", "idle")        # idle | active | done
        q.setdefault("mins", 25)
        q.setdefault("target_ms", int(q.get("mins") or 25) * 60_000)
        q.setdefault("acc_ms", 0)             # 已累计（已暂停的部分）
        q.setdefault("running_since", 0)      # 本轮开始跑表的时刻；0 = 暂停中
        q.setdefault("claimed_at", 0)
        q.setdefault("finished_at", 0)
        q.setdefault("reward", {})
        return q

    def quest_claim(self, mins: int = 15) -> dict:
        """领取任务：清空累计、进入 active（但先不跑表，等进学习页）。"""
        mins = max(1, int(mins))
        q = self.quest
        q.update({
            "status": "active", "mins": mins, "target_ms": mins * 60_000,
            "acc_ms": 0, "running_since": 0,
            "claimed_at": now_ms(), "finished_at": 0,
            "reward": {"xp": int(round(mins * 0.6)), "gold": int(round(mins * 0.4))},
        })
        self.save()
        return q

    def quest_elapsed(self) -> int:
        """已投入时长（含正在跑的这一段）。"""
        q = self.quest
        acc = int(q.get("acc_ms") or 0)
        since = int(q.get("running_since") or 0)
        if q.get("status") == "active" and since:
            acc += max(0, now_ms() - since)
        return acc

    def quest_left_ms(self) -> int:
        q = self.quest
        return max(0, int(q.get("target_ms") or 15 * 60_000) - self.quest_elapsed())

    def quest_running(self) -> bool:
        q = self.quest
        return q.get("status") == "active" and bool(q.get("running_since"))

    def quest_start_clock(self):
        """进学习页：开始跑表（幂等）。"""
        q = self.quest
        if q.get("status") != "active" or q.get("running_since"):
            return
        q["running_since"] = now_ms()
        self.save_deferred()          # 进学习页不阻塞，切页/关窗时会补写

    def quest_pause_clock(self):
        """离开学习页 / 窗口失焦：停下并结算掉这一段（幂等）。"""
        q = self.quest
        if not q.get("running_since"):
            return
        q["acc_ms"] = int(q.get("acc_ms") or 0) + max(0, now_ms() - int(q["running_since"]))
        q["running_since"] = 0
        self.save()

    def quest_complete(self) -> dict | None:
        """时长够了就地结算；返回任务字典（含 reward），没够返回 None。"""
        q = self.quest
        if q.get("status") != "active":
            return None
        # 先看时长：没学满就什么都不做（以前这里会先暂停，等于每秒把表停一次）
        if self.quest_elapsed() < int(q.get("target_ms") or 0):
            return None
        self.quest_pause_clock()
        q["status"] = "done"
        q["finished_at"] = now_ms()
        q["acc_ms"] = 0            # 这段已由下面这条 checkin 代表，别再算一次
        r = q.get("reward") or {}
        xp, gold = int(r.get("xp", 0)), int(r.get("gold", 0))
        # 记进 checkins，沿用现有「最近 7 天」与勋章统计
        before_frogs = self.frogs_eaten()
        self.checkins.append({"at": now_ms(), "mins": int(q.get("mins") or 15),
                              "quest": True, "xp": xp, "gold": gold})
        # 发奖 + 吃青蛙 + 连击 + 徽章（一只青蛙 = 累计 45 分钟）
        q["events"] = self.award(xp, gold, persist=False)
        kills = self.frogs_eaten() - before_frogs
        q["boss_kill"] = self._frog_eaten(kills) if kills > 0 else None
        self.sync_boss_hp()
        self.bump_streak()
        self.sync_badges()
        self.record("quest", f"专注 {int(q.get('mins') or 15)} 分钟", xp, gold,
                    mins=int(q.get("mins") or 15))
        self.save()
        return q

    def quest_reset(self):
        """回到可领取状态（放弃 / 领下一个）：没学满的进度和时长一起清零。"""
        q = self.quest
        q.update({"status": "idle", "acc_ms": 0, "running_since": 0,
                  "claimed_at": 0, "reward": {}})
        self.save()

    def quest_has_progress(self) -> bool:
        """有没有「领了但还没做完」的任务（暂停中也算）。"""
        q = self.quest
        return (q.get("status") != "done" and bool(q.get("claimed_at"))
                and int(q.get("target_ms") or 0) > 0)

    def quest_pause(self):
        """关开关：停表，但已用时间、时长、奖励全部保留。"""
        q = self.quest
        if q.get("status") != "active":
            return
        self.quest_pause_clock()
        q["status"] = "idle"
        self.save()

    def quest_resume(self) -> bool:
        """再开开关：接着上次的进度继续（不是重新领一个）。"""
        q = self.quest
        if q.get("status") == "active":
            return True
        if not self.quest_has_progress():
            return False
        q["status"] = "active"
        q["running_since"] = 0          # 回到学习页才继续跑表
        self.save()
        return True

    def quest_restart(self):
        """把计时清零（时长保留）；暂停中也能用。"""
        q = self.quest
        if not self.quest_has_progress():
            return
        q["acc_ms"] = 0
        q["running_since"] = 0
        self.save()

    # ---------------------------------------------------------- 征途 · 游戏
    XP_BASE, XP_STEP = 100, 40
    DIFF = {"easy": (8, 2, 1.0), "medium": (12, 4, 1.5), "hard": (18, 6, 2.2)}
    FROG_MINUTES = 15        # 吃掉一只青蛙需要累计专注 15 分钟
    BOSS_HP = FROG_MINUTES   # 兼容旧字段：现在血条 = 还差多少分钟
    ATTRS = (("str", "力量"), ("int", "智力"), ("con", "体质"), ("per", "感知"))

    def _game_seed(self) -> dict:
        return {
            "lv": 1, "xp": 0, "hp": 50, "hp_max": 50,
            "gold": 0, "gems": 0, "attr_points": 0,
            "attrs": {"str": 5, "int": 5, "con": 5, "per": 5},
            "streak": 0, "last_active": "", "last_day": day_str(),
            "day": {"date": day_str(), "xp": 0, "gold": 0},
            "records": [],
            "records_migrated": False,
            "habits": [],
            "dailies": [],
            "todos": [],
            "rewards": [
                {"id": "r-1", "title": "看一集剧", "price": 20, "tag": "娱乐", "redeemed": 0},
                {"id": "r-2", "title": "一杯奶茶", "price": 35, "tag": "犒赏", "redeemed": 0},
                {"id": "r-3", "title": "周末睡到自然醒", "price": 60, "tag": "休息", "redeemed": 0},
            ],
            "boss": {"name": "吃掉那只青蛙", "lv": 1, "hp": self.FROG_MINUTES,
                     "hp_max": self.FROG_MINUTES, "defeated": 0},
            "badges": ["novice"],
        }

    @property
    def game(self) -> dict:
        g = self.state.setdefault("game", {})
        seed = self._game_seed()
        for k, v in seed.items():
            if k not in g:
                g[k] = v
        for k, v in seed["attrs"].items():
            g["attrs"].setdefault(k, v)
        _boss = g.setdefault("boss", {})
        if _boss.get("name") in ("拖延巨兽", "拖延青蛙", ""):
            _boss["name"] = "吃掉那只青蛙"
        if int(_boss.get("hp_max") or 0) != self.FROG_MINUTES:
            prog = self.study_minutes() % self.FROG_MINUTES
            _boss["hp_max"] = self.FROG_MINUTES
            _boss["hp"] = self.FROG_MINUTES - prog if prog else self.FROG_MINUTES
        # 一次性：把老的「每日/习惯/待办」清掉，并用旧 checkins 补一份完成记录
        if not g.get("records_migrated"):
            if not g.get("records"):
                g["records"] = [
                    {"id": f"r{c.get('at')}", "at": c.get("at") or 0, "kind": "quest",
                     "title": f"专注 {int(c.get('mins') or 25)} 分钟",
                     "xp": int(c.get("xp") or 0), "gold": int(c.get("gold") or 0),
                     "mins": int(c.get("mins") or 25)}
                    for c in self.checkins if c.get("quest")]
                g["records"].sort(key=lambda r: r.get("at") or 0)
            g["dailies"] = []
            g["habits"] = []
            g["todos"] = []
            g["records_migrated"] = True
        return g

    # ---- 完成记录 ----
    def record(self, kind: str, title: str, xp: int = 0, gold: int = 0, **extra) -> dict:
        g = self.game
        recs = g.setdefault("records", [])
        item = {"id": f"r{uuid.uuid4().hex[:8]}", "at": now_ms(), "kind": kind,
                "title": (title or "").strip() or "完成", "xp": int(xp), "gold": int(gold)}
        item.update(extra)
        recs.append(item)
        del recs[:-400]          # 只留最近 400 条，别让 JSON 无限长
        return item

    def records_grouped(self) -> list[tuple[str, list[dict]]]:
        """按天分组、新的在前：[(YYYY-MM-DD, [记录...]), ...]。"""
        recs = sorted(self.game.get("records") or [], key=lambda r: -(r.get("at") or 0))
        groups: list[tuple[str, list[dict]]] = []
        for r in recs:
            d = day_str(r.get("at"))
            if not groups or groups[-1][0] != d:
                groups.append((d, []))
            groups[-1][1].append(r)
        return groups

    # ---- 数值 ----
    def xp_need(self, lv: int | None = None) -> int:
        lv = int(lv or self.game.get("lv") or 1)
        return self.XP_BASE + self.XP_STEP * (lv - 1)

    def award(self, xp: int = 0, gold: int = 0, persist: bool = True) -> list[dict]:
        """加经验/金币；够经验就连续升级。返回事件列表（供 UI 弹升级）。"""
        g = self.game
        events: list[dict] = []
        if xp or gold:
            today = day_str()
            d = g.setdefault("day", {"date": today, "xp": 0, "gold": 0})
            if d.get("date") != today:
                d.update({"date": today, "xp": 0, "gold": 0})
            d["xp"] = int(d.get("xp") or 0) + int(xp)
            d["gold"] = int(d.get("gold") or 0) + int(gold)
        if gold:
            g["gold"] = max(0, int(g.get("gold") or 0) + int(gold))
        if xp:
            g["xp"] = int(g.get("xp") or 0) + int(xp)
            guard = 0
            while g["xp"] >= self.xp_need(g["lv"]) and guard < 50:
                g["xp"] -= self.xp_need(g["lv"])
                g["lv"] = int(g["lv"]) + 1
                g["hp_max"] = int(g.get("hp_max") or 50) + 5
                g["hp"] = g["hp_max"]
                g["attr_points"] = int(g.get("attr_points") or 0) + 1
                events.append({"type": "levelup", "lv": g["lv"]})
                guard += 1
        if persist:
            self.save()
        return events

    def hurt(self, hp: int, persist: bool = True) -> bool:
        """扣血；血量归零 = 倒下（金币 -10%、回满、连击清零）。"""
        g = self.game
        g["hp"] = int(g.get("hp") or 0) - int(hp)
        down = g["hp"] <= 0
        if down:
            g["hp"] = int(g.get("hp_max") or 50)
            g["gold"] = int(int(g.get("gold") or 0) * 0.9)
            g["streak"] = 0
        if persist:
            self.save()
        return down

    def heal(self, hp: int = 1):
        g = self.game
        g["hp"] = min(int(g.get("hp_max") or 50), int(g.get("hp") or 0) + int(hp))
        self.save()

    def bump_streak(self):
        g = self.game
        today = day_str()
        if g.get("last_active") == today:
            return
        g["streak"] = (int(g.get("streak") or 0) + 1
                       if g.get("last_active") == prev_day_str() else 1)
        g["last_active"] = today

    def sync_badges(self) -> list[str]:
        from pages.journey_widgets import BADGES  # 阈值与 UI 同源
        total = self.frogs_eaten()
        unlocked = [k for k, _n, need, _e in BADGES if total >= need]
        self.game["badges"] = unlocked
        return unlocked

    def allocate_point(self, attr: str) -> bool:
        g = self.game
        if int(g.get("attr_points") or 0) <= 0 or attr not in g["attrs"]:
            return False
        g["attrs"][attr] = int(g["attrs"][attr]) + 1
        g["attr_points"] = int(g["attr_points"]) - 1
        self.save()
        return True

    # ---- 三类任务 ----
    def _find(self, bucket: str, tid: str) -> dict | None:
        return next((x for x in self.game.get(bucket) or [] if x.get("id") == tid), None)

    def score_daily(self, tid: str) -> dict:
        t = self._find("dailies", tid)
        today = day_str()
        if not t or t.get("last_done") == today:
            return {}
        t["streak"] = (int(t.get("streak") or 0) + 1
                       if t.get("last_done") == prev_day_str() else 1)
        t["last_done"] = today
        base_xp, base_gold, mult = self.DIFF.get(t.get("diff", "medium"), self.DIFF["medium"])
        sm = 1 + min(int(t["streak"]), 30) * 0.02
        xp = int(round(base_xp * mult * sm))
        gold = int(round(base_gold * mult * sm))
        events = self.award(xp, gold)
        self.bump_streak()
        self.sync_badges()
        self.record("daily", t.get("title") or "每日任务", xp, gold, streak=t["streak"])
        self.save()
        return {"xp": xp, "gold": gold, "streak": t["streak"], "events": events}

    def score_habit(self, tid: str, good: bool = True) -> dict:
        h = self._find("habits", tid)
        if not h:
            return {}
        if good:
            events = self.award(int(h.get("xp") or 0), int(h.get("gold") or 0))
            self.record("habit", h.get("title") or "习惯", int(h.get("xp") or 0),
                        int(h.get("gold") or 0))
            self.save()
            return {"xp": int(h.get("xp") or 0), "gold": int(h.get("gold") or 0),
                    "events": events}
        lost = int(h.get("hp") or 8)
        self.hurt(lost)
        return {"hp": -lost}

    def score_todo(self, tid: str) -> dict:
        t = self._find("todos", tid)
        if not t or t.get("done"):
            return {}
        t["done"] = True
        t["done_at"] = now_ms()
        events = self.award(int(t.get("xp") or 15), int(t.get("gold") or 5))
        self.bump_streak()
        self.sync_badges()
        self.record("todo", t.get("title") or "待办", int(t.get("xp") or 15),
                    int(t.get("gold") or 5))
        self.save()
        return {"xp": int(t.get("xp") or 15), "gold": int(t.get("gold") or 5),
                "events": events}

    def add_task(self, bucket: str, title: str, **kw) -> dict:
        tid = f"{bucket[:1]}-{uuid.uuid4().hex[:6]}"
        item = {"id": tid, "title": (title or "").strip() or "未命名"}
        if bucket == "dailies":
            item.update({"diff": kw.get("diff", "medium"), "streak": 0, "last_done": ""})
        elif bucket == "habits":
            item.update({"xp": int(kw.get("xp", 6)), "gold": int(kw.get("gold", 2))})
        elif bucket == "todos":
            item.update({"due": kw.get("due") or now_ms() + DAY,
                         "xp": int(kw.get("xp", 15)), "gold": int(kw.get("gold", 5)),
                         "done": False})
        self.game.setdefault(bucket, []).append(item)
        self.save()
        return item

    def remove_task(self, bucket: str, tid: str) -> bool:
        items = self.game.get(bucket) or []
        for i, x in enumerate(items):
            if x.get("id") == tid:
                del items[i]
                self.save()
                return True
        return False

    # ---- 奖励商店 ----
    def redeem_reward(self, rid: str) -> dict:
        r = next((x for x in self.game.get("rewards") or [] if x.get("id") == rid), None)
        if not r:
            return {"ok": False, "why": "missing"}
        price = int(r.get("price") or 0)
        if int(self.game.get("gold") or 0) < price:
            return {"ok": False, "why": "gold", "need": price - int(self.game.get("gold") or 0)}
        self.game["gold"] = int(self.game.get("gold") or 0) - price
        r["redeemed"] = int(r.get("redeemed") or 0) + 1
        self.save()
        return {"ok": True, "title": r.get("title"), "price": price}

    def add_reward(self, title: str, price: int, tag: str = "自定义") -> dict:
        item = {"id": f"r-{uuid.uuid4().hex[:6]}", "title": (title or "").strip() or "奖励",
                "price": max(1, int(price)), "tag": tag, "redeemed": 0}
        self.game.setdefault("rewards", []).append(item)
        self.save()
        return item

    # ---- 青蛙：按累计学习时长算 ----
    def banked_ms(self) -> int:
        """放弃 / 重置计时时存下来的零头（还没凑满一分钟任务的时长）。"""
        return sum(int(e.get("ms") or 0) for e in (self.state.get("study_banked") or []))

    def _live_ms(self) -> int:
        """当前这次任务已经学了多久（含正在跑的一段）。"""
        q = self.quest
        if q.get("status") not in ("active", "idle"):
            return 0
        if not q.get("claimed_at"):
            return 0
        return max(0, self.quest_elapsed())

    def study_minutes(self) -> int:
        """累计专注分钟：完成的任务 + 重置时存下的零头 + 当前进行中的时长。"""
        base = sum(int(c.get("mins") or 0) for c in self.checkins) * 60_000
        return int(base + self.banked_ms() + self._live_ms()) // 60_000

    def study_by_day(self) -> dict:
        """{YYYY-MM-DD: 分钟}：完成的任务 + 重置存下的零头 + 今天正在学的。"""
        out: dict = {}
        for c in self.checkins:
            k = day_str(int(c.get("at") or 0))
            out[k] = out.get(k, 0) + int(c.get("mins") or 0)
        for e in self.state.get("study_banked") or []:
            k = day_str(int(e.get("at") or 0))
            out[k] = out.get(k, 0) + int(e.get("ms") or 0) // 60_000
        live = self._live_ms()
        if live:
            k = day_str()
            out[k] = out.get(k, 0) + int(live) // 60_000
        return out

    def study_by_day(self) -> dict:
        """{YYYY-MM-DD: 分钟}：完成的任务 + 重置存下的零头 + 今天正在学的。"""
        out: dict = {}
        for c in self.checkins:
            k = day_str(int(c.get("at") or 0))
            out[k] = out.get(k, 0) + int(c.get("mins") or 0)
        for e in self.state.get("study_banked") or []:
            k = day_str(int(e.get("at") or 0))
            out[k] = out.get(k, 0) + int(e.get("ms") or 0) // 60_000
        live = self._live_ms()
        if live:
            k = day_str()
            out[k] = out.get(k, 0) + int(live) // 60_000
        return out

    def bank_quest_partial(self):
        """把当前任务已学、但还没算进统计的那段存起来（重置/放弃前调用）。"""
        q = self.quest
        left = max(0, self.quest_elapsed())
        if left <= 0:
            return
        arr = self.state.setdefault("study_banked", [])
        arr.append({"at": now_ms(), "ms": int(left)})
        q["acc_ms"] = 0
        q["running_since"] = 0

    def frogs_eaten(self) -> int:
        """累计吃掉了几只青蛙（每 45 分钟一只）。"""
        return self.study_minutes() // self.FROG_MINUTES

    def frog_left_minutes(self) -> int:
        """当前这只青蛙还差多少分钟。"""
        prog = self.study_minutes() % self.FROG_MINUTES
        return self.FROG_MINUTES - prog if prog else self.FROG_MINUTES

    def frog_events(self) -> list[dict]:
        """按时间顺序还原「每吃掉一只青蛙」的那一刻（最新在前）。"""
        items = [(int(c.get("at") or 0), int(c.get("mins") or 0) * 60_000,
                  int(c.get("mins") or 0)) for c in self.checkins]
        for e in self.state.get("study_banked") or []:
            ms = int(e.get("ms") or 0)
            items.append((int(e.get("at") or 0), ms, ms // 60_000))
        live = self._live_ms()
        if live > 0:
            items.append((now_ms(), live, live // 60_000))
        items.sort(key=lambda x: x[0])
        evts = []
        total_ms = 0
        for at, ms, mins in items:
            before = total_ms // (self.FROG_MINUTES * 60_000)
            total_ms += max(0, ms)
            after = total_ms // (self.FROG_MINUTES * 60_000)
            for n in range(before + 1, after + 1):
                evts.append({
                    "at": at,
                    "idx": n,
                    "mins": mins,
                    "total_min": n * self.FROG_MINUTES,
                })
        evts.reverse()
        return evts

    def reset_frog_data(self):
        """把「吃掉青蛙」的数据清零：吃蛙记录、勋章、累计学习时长、青蛙等级。

        只动征途的青蛙数据，卡片的复习进度、金币/宝石、待办等都不受影响。
        """
        self.checkins.clear()
        self.state["study_banked"] = []
        g = self.game
        g["boss"] = {"name": "吃掉那只青蛙", "lv": 1, "hp": self.FROG_MINUTES,
                     "hp_max": self.FROG_MINUTES, "defeated": 0}
        g["badges"] = ["novice"]
        g["streak"] = 0
        g["last_active"] = ""
        self.save()

    def frog_medal_times(self) -> dict:
        """{勋章门槛: 解锁时间}，由「第 N 只青蛙」那一刻反推。"""
        return {int(e["idx"]): int(e["at"]) for e in self.frog_events()}

    def sync_boss_hp(self):
        """把血条同步成「还差多少分钟」（满血 = 45 分钟）。"""
        b = self.game.setdefault("boss", {})
        b["hp_max"] = self.FROG_MINUTES
        b["hp"] = self.frog_left_minutes()

    def _frog_eaten(self, times: int = 1) -> dict:
        b = self.game["boss"]
        times = max(1, int(times))
        b["defeated"] = int(b.get("defeated") or 0) + times
        b["lv"] = int(b.get("lv") or 1) + times
        self.game["gems"] = int(self.game.get("gems") or 0) + times
        self.award(0, 40 * times, persist=False)
        self.sync_boss_hp()
        return {"gold": 40 * times, "gems": times, "boss_lv": b["lv"],
                "count": times}

    # ---- 每日结算 ----
    def run_daily_cron(self) -> dict | None:
        """跨天结算：漏做的每日扣血、断连击。返回摘要（没有跨天返回 None）。"""
        g = self.game
        today = day_str()
        if not g.get("last_day"):
            g["last_day"] = today
            self.save()
            return None
        if g["last_day"] == today:
            return None
        done = missed = 0
        for t in g.get("dailies") or []:
            if t.get("last_done") == today:
                done += 1
            else:
                missed += 1
                t["streak"] = 0
        hp_lost = missed * 3
        down = self.hurt(hp_lost, persist=False) if hp_lost else False
        # 昨天完成了多少（记录里按天汇总）
        yday = prev_day_str()
        recs = [r for r in g.get("records") or [] if day_str(r.get("at")) == yday]
        # 每天自然回 1 点生命（和结算弹层上的文案一致）
        g["hp"] = min(int(g.get("hp_max") or 50), int(g.get("hp") or 0) + 1)
        g["day"] = {"date": today, "xp": 0, "gold": 0}
        g["last_day"] = today
        # 今日任务跨天清零：没学满 15 分钟的进度和这段时间一起清零，
        # 但「0 点那一刻还在学习页计时」的情况不受影响（不清零，继续学）
        q = self.state.get("quest")
        if isinstance(q, dict) and not (q.get("status") == "active"
                                        and q.get("running_since")):
            if (q.get("status") != "idle" or q.get("claimed_at")
                    or int(q.get("acc_ms") or 0) > 0):
                q.update({"status": "idle", "acc_ms": 0, "running_since": 0,
                          "claimed_at": 0, "finished_at": 0, "reward": {}})
        self.save()
        return {"date": today, "done": done, "missed": missed, "hp_lost": hp_lost,
                "records": len(recs),
                "xp": sum(int(r.get("xp") or 0) for r in recs),
                "hp": g["hp"], "hp_max": g["hp_max"], "gold": g["gold"],
                "streak": g["streak"], "down": down}

    @property
    def settings(self) -> dict:
        return self.state["settings"]

    def deck(self, deck_id: str) -> dict | None:
        self._ensure_indexes()
        return self._deck_idx.get(deck_id)

    def card(self, card_id: str) -> dict | None:
        self._ensure_indexes()
        return self._card_idx.get(card_id)

    # ---- 归档（只针对卡包）----
    def archive_deck(self, deck_id: str, archived: bool = True) -> bool:
        d = self.deck(deck_id)
        if not d:
            return False
        d["archived"] = bool(archived)
        d["archived_at"] = now_ms() if archived else None
        if not archived:
            d["parent_id"] = None      # 取消归档 → 回到知识域根目录
        self.save()
        return True

    def archived_decks(self) -> list[dict]:
        return [d for d in self.decks if d.get("archived")]

    def active_cards(self) -> list[dict]:
        arch = {d["id"] for d in self.decks if d.get("archived")}
        return [c for c in self.cards
                if c["deck_id"] not in arch and not c.get("archived")]

    def live_cards(self) -> list[dict]:
        """真正还在学的卡：排除已完成卡包、存档/已完成卡组、暂停与已归档的卡。"""
        self._ensure_indexes()
        arch_decks = {d["id"] for d in self.decks if d.get("archived")}
        skip = {d["id"]: set(d.get("archived_groups") or [])
                | set(d.get("completed_groups") or [])
                for d in self.decks}
        out = []
        for c in self.cards:
            if c.get("archived") or c.get("suspended"):
                continue
            did = c["deck_id"]
            if did in arch_decks or c.get("group") in skip.get(did, ()):
                continue
            out.append(c)
        return out

    def live_reviews(self, cards: list[dict] | None = None) -> list[dict]:
        """只保留仍在学的卡片产生的复习记录。"""
        live = {c["id"] for c in (cards if cards is not None else self.live_cards())}
        return [r for r in self.reviews if r.get("card_id") in live]

    def cards_of(self, deck_id: str) -> list[dict]:
        self._ensure_indexes()
        return [c for c in self._by_deck.get(deck_id, ()) if not c.get("archived")]

    def practice_cards(self, deck_id: str | None = None,
                       group: str | None = None) -> list[dict]:
        self._ensure_indexes()
        arch_decks = {d["id"] for d in self.decks if d.get("archived")}
        source = self._by_deck.get(deck_id, ()) if deck_id else self.cards
        return [c for c in source
                if c.get("practice") and not c.get("archived")
                and not c.get("suspended") and c["deck_id"] not in arch_decks
                and (not group or c.get("group") == group)]

    def set_practice(self, ids, on: bool = True) -> int:
        ids = set(ids)
        n = 0
        for c in self.cards:
            if c["id"] in ids:
                c["practice"] = bool(on)
                n += 1
        self.save()
        return n

    # ------------------------------------------------------------ 回收站
    @property
    def trash(self) -> list:
        return self.state.setdefault("trash", [])

    def trash_count(self) -> int:
        return len(self.trash)

    def _trash_push(self, kind: str, title: str, sub: str, payload: dict) -> dict:
        e = {"id": f"t{now_ms()}{len(self.trash)}", "kind": kind, "at": now_ms(),
             "title": title, "sub": sub, "payload": payload}
        self.trash.append(e)
        return e

    def trash_restore(self, tid: str) -> tuple[bool, str]:
        e = next((x for x in self.trash if x.get("id") == tid), None)
        if not e:
            return False, "这条记录不在了"
        kind = e.get("kind")
        p = e.get("payload") or {}
        if kind == "cards":
            cards = [c for c in (p.get("cards") or []) if self.deck(c.get("deck_id"))]
            if not cards:
                return False, "原来的卡包已经删了，恢复不了这些卡片"
            have = {c["id"] for c in self.cards}
            self.state.setdefault("cards", []).extend(c for c in cards if c["id"] not in have)
            have_rev = {(r.get("card_id"), r.get("at")) for r in self.reviews}
            for r in p.get("reviews") or []:
                if (r.get("card_id"), r.get("at")) not in have_rev:
                    self.reviews.append(r)
        elif kind == "group":
            d = self.deck(p.get("deck_id") or "")
            if not d:
                return False, "原来的卡包已经删了，恢复不了这个卡组"
            g = p.get("group") or "未分组"
            if g not in (d.get("groups") or []):
                d.setdefault("groups", []).append(g)
            have = {c["id"] for c in self.cards}
            self.state.setdefault("cards", []).extend(
                c for c in (p.get("cards") or []) if c["id"] not in have)
        elif kind == "deck":
            d = p.get("deck") or {}
            if not d.get("id"):
                return False, "记录损坏，恢复不了"
            if self.deck(d["id"]) is None:
                if d.get("parent_id") and not any(r["id"] == d["parent_id"]
                                                  for r in self.rounds):
                    d["parent_id"] = None      # 上层的圆桌也没了 → 放回根目录
                self.state.setdefault("decks", []).append(d)
            have = {c["id"] for c in self.cards}
            self.state.setdefault("cards", []).extend(
                c for c in (p.get("cards") or []) if c["id"] not in have)
        self.trash.remove(e)
        self.save()
        return True, "已恢复"

    def trash_purge(self, tid: str) -> bool:
        n = len(self.trash)
        self.state["trash"] = [x for x in self.trash if x.get("id") != tid]
        if len(self.state["trash"]) != n:
            self.save()
            return True
        return False

    def trash_clear(self) -> int:
        n = len(self.trash)
        self.state["trash"] = []
        if n:
            self.save()
        return n

    def delete_cards(self, ids) -> int:
        ids = set(ids)
        if not ids:
            return 0
        gone = [c for c in self.cards if c["id"] in ids]
        if not gone:
            return 0
        revs = [r for r in self.reviews if r.get("card_id") in ids]
        self.state["cards"] = [c for c in self.cards if c["id"] not in ids]
        self.reviews[:] = [r for r in self.reviews if r.get("card_id") not in ids]
        names = {d["id"]: d.get("name") or "" for d in self.decks}
        where = ""
        if gone:
            d0 = gone[0].get("deck_id")
            where = names.get(d0, "") + (" · " + (gone[0].get("group") or "") if gone[0].get("group") else "")
        title = (gone[0].get("q") or "卡片")[:24] if len(gone) == 1 else f"{len(gone)} 张卡片"
        self._trash_push("cards", title, where.strip(" ·"),
                         {"cards": gone, "reviews": revs})
        self.save()
        return len(gone)

    def move_cards(self, ids, deck_id: str, group: str) -> int:
        ids = set(ids)
        d = self.deck(deck_id)
        if d is not None and group not in (d.get("groups") or []):
            d.setdefault("groups", []).append(group)
        n = 0
        for c in self.cards:
            if c["id"] in ids:
                c["group"] = group
                n += 1
        self.save()
        return n

    # ---- 圆桌/卡包排序 ----
    @staticmethod
    def _order_key(kind: str, domain: str, parent_id: str | None) -> str:
        return f"{kind}:{domain}:{parent_id or 'root'}"

    def ordered_ids(self, kind: str, domain: str, parent_id: str | None,
                    ids: list[str]) -> list[str]:
        saved = (self.state.get("orders") or {}).get(
            self._order_key(kind, domain, parent_id), [])
        return [i for i in saved if i in ids] + [i for i in ids if i not in saved]

    def set_order(self, kind: str, domain: str, parent_id: str | None, ids: list[str]):
        self.state.setdefault("orders", {})[
            self._order_key(kind, domain, parent_id)] = list(ids)
        self.save()

    # ---- 卡组顺序 / 选中 ----
    def ordered_groups(self, deck_id: str) -> list[str]:
        d = self.deck(deck_id) or {}
        present: list[str] = []
        for c in self.cards_of(deck_id):
            g = c.get("group", "未分组")
            if g not in present:
                present.append(g)
        # 新建但还没有卡片的卡组也要出现在列表里
        for g in (d.get("groups") or []):
            if g and g not in present:
                present.append(g)
        order = [g for g in (d.get("group_order") or []) if g in present]
        order += [g for g in present if g not in order]
        if order != (d.get("group_order") or []):
            d["group_order"] = order
            self.save()
        return order

    def create_group(self, deck_id: str, name: str) -> tuple[bool, str]:
        """新建一个空卡组；成功返回 (True, 名称)，失败返回 (False, 原因)。"""
        name = (name or "").strip()
        if not name:
            return False, "名称不能为空"
        if len(name) > 80:
            return False, "名称最长 80 个字符"
        d = self.deck(deck_id)
        if not d:
            return False, "卡包不存在"
        groups = d.setdefault("groups", [])
        if name in groups:
            return False, "已经有同名卡组了"
        groups.append(name)
        order = d.setdefault("group_order", [])
        if name not in order:
            order.append(name)
        for k in ("archived_groups", "completed_groups"):
            if name in (d.get(k) or []):
                d[k].remove(name)
        self.save()
        return True, name

    def set_group_order(self, deck_id: str, order: list[str]):
        d = self.deck(deck_id)
        if d:
            d["group_order"] = list(order)
            self.save()

    def selected_group(self, deck_id: str) -> str | None:
        sel = (self.state.get("settings") or {}).get("deck_selection") or {}
        return sel.get(deck_id)

    def save_selection(self, deck_id: str, group: str):
        sel = self.state.setdefault("settings", {}).setdefault("deck_selection", {})
        if sel.get(deck_id) == group:
            return
        sel[deck_id] = group
        self.save()

    # ---- 知识域 ----
    @property
    def domains(self) -> list[dict]:
        return self.state["domains"]

    def domain(self, domain_id: str) -> dict | None:
        return next((d for d in self.domains if d["id"] == domain_id), None)

    def add_domain(self, name: str) -> dict:
        d = {"id": uid("dom_"), "name": name.strip(), "emoji": "🗂"}
        self.domains.append(d)
        self.save()
        return d

    def rename_domain(self, domain_id: str, name: str):
        d = self.domain(domain_id)
        if d and name.strip():
            d["name"] = name.strip()
            self.save()

    def delete_domain(self, domain_id: str, move_to: str | None = None):
        """删除知识域：里面的圆桌与卡包移到 move_to（默认第一个域）。"""
        if len(self.domains) <= 1:
            return False
        rest = [d for d in self.domains if d["id"] != domain_id]
        target = move_to or (rest[0]["id"] if rest else None)
        for r in self.rounds:
            if r["domain"] == domain_id:
                r["domain"] = target
        for d in self.decks:
            if d["domain"] == domain_id:
                d["domain"] = target
        self.state["domains"] = rest
        self.save()
        return True

    # ---- 圆桌 ----
    @property
    def rounds(self) -> list[dict]:
        return self.state["rounds"]

    def rnd(self, round_id: str) -> dict | None:
        return next((r for r in self.rounds if r["id"] == round_id), None)

    def rounds_in(self, domain: str, parent_id: str | None) -> list[dict]:
        return [r for r in self.rounds
                if r["domain"] == domain and r.get("parent_id") == parent_id]

    def decks_in(self, domain: str, parent_id: str | None) -> list[dict]:
        return [d for d in self.decks
                if d["domain"] == domain and d.get("parent_id") == parent_id]

    def add_round(self, name: str, domain: str, parent_id: str | None) -> dict:
        r = {"id": uid("rnd_"), "name": name.strip(), "domain": domain,
             "parent_id": parent_id, "created": now_ms()}
        self.rounds.append(r)
        self.save()
        return r

    def add_deck(self, name: str, domain: str, parent_id: str | None,
                 template: str = "sky") -> dict:
        d = {"id": uid("dck_"), "name": name.strip(), "domain": domain,
             "parent_id": parent_id, "color": "#2F6A43", "template": template,
             "groups": [], "archived_groups": [], "completed_groups": [],
             "created": now_ms()}
        self.decks.append(d)
        self.save()
        return d

    def rename_round(self, round_id: str, name: str):
        r = self.rnd(round_id)
        if r:
            r["name"] = name.strip()
            self.save()

    def rename_deck(self, deck_id: str, name: str):
        d = self.deck(deck_id)
        if d:
            d["name"] = name.strip()
            self.save()

    def _is_descendant(self, round_id: str, ancestor_id: str) -> bool:
        cur = self.rnd(round_id)
        seen = set()
        while cur and cur.get("parent_id") and cur["parent_id"] not in seen:
            if cur["parent_id"] == ancestor_id:
                return True
            seen.add(cur["parent_id"])
            cur = self.rnd(cur["parent_id"])
        return False

    def move_round(self, round_id: str, domain: str, parent_id: str | None) -> bool:
        r = self.rnd(round_id)
        if not r:
            return False
        if parent_id == round_id or (parent_id and self._is_descendant(parent_id, round_id)):
            return False        # 不能移进自己或自己的子孙
        r["domain"] = domain
        r["parent_id"] = parent_id
        self.save()
        return True

    def move_deck(self, deck_id: str, domain: str, parent_id: str | None) -> bool:
        d = self.deck(deck_id)
        if not d:
            return False
        d["domain"] = domain
        d["parent_id"] = parent_id
        self.save()
        return True

    def delete_round(self, round_id: str):
        """删圆桌本身，里面的子圆桌与卡包上移到父级。"""
        r = self.rnd(round_id)
        if not r:
            return
        parent = r.get("parent_id")
        for x in self.rounds:
            if x.get("parent_id") == round_id:
                x["parent_id"] = parent
        for d in self.decks:
            if d.get("parent_id") == round_id:
                d["parent_id"] = parent
        self.rounds.remove(r)
        self.save()

    def delete_deck(self, deck_id: str):
        deck = self.deck(deck_id)
        if not deck:
            return
        cards = [c for c in self.cards if c["deck_id"] == deck_id]
        ids = {c["id"] for c in cards}
        revs = [r for r in self.reviews if r.get("card_id") in ids]
        self.state["cards"] = [c for c in self.cards if c["deck_id"] != deck_id]
        self.reviews[:] = [r for r in self.reviews if r.get("card_id") not in ids]
        self.state["decks"] = [d for d in self.decks if d["id"] != deck_id]
        self._trash_push("deck", deck.get("name") or "卡包",
                         f"{len(cards)} 张卡片",
                         {"deck": deck, "cards": cards, "reviews": revs})
        self.save()

    def subtree_counts(self, round_id: str) -> tuple[int, int, int]:
        """(卡包数, 卡片数, 子圆桌数) —— 含所有下层。"""
        decks_by_parent: dict[str, list[dict]] = {}
        for d in self.decks:
            decks_by_parent.setdefault(d.get("parent_id"), []).append(d)
        rounds_by_parent: dict[str, list[dict]] = {}
        for r in self.rounds:
            rounds_by_parent.setdefault(r.get("parent_id"), []).append(r)

        decks, cards, rounds = 0, 0, 0
        stack = [round_id]
        seen = set()
        while stack:
            rid = stack.pop()
            if rid in seen:
                continue
            seen.add(rid)
            for d in decks_by_parent.get(rid, ()):
                decks += 1
                cards += len(self.cards_of(d["id"]))
            for r in rounds_by_parent.get(rid, ()):
                rounds += 1
                stack.append(r["id"])
        return decks, cards, rounds

    # ---- 卡组归档 ----
    def archived_groups(self, deck_id: str) -> set[str]:
        d = self.deck(deck_id) or {}
        return set(d.get("archived_groups") or [])

    def completed_groups(self, deck_id: str) -> set[str]:
        d = self.deck(deck_id) or {}
        return set(d.get("completed_groups") or [])

    def toggle_group_complete(self, deck_id: str, group: str) -> bool:
        """标记「已完成」。返回 True 表示现在已完成。"""
        d = self.deck(deck_id)
        if not d:
            return False
        arr = d.setdefault("completed_groups", [])
        if group in arr:
            arr.remove(group)
            self.save()
            return False
        arr.append(group)
        arch = d.setdefault("archived_groups", [])
        if group in arch:
            arch.remove(group)
        self.save()
        return True

    def unarchive_group(self, deck_id: str, group: str):
        d = self.deck(deck_id)
        if d and group in (d.get("archived_groups") or []):
            d["archived_groups"].remove(group)
            self.save()

    # ---- 笔记 / 兄弟卡 ----
    def siblings(self, note_id: str | None, exclude_id: str | None = None) -> list[dict]:
        if not note_id:
            return []
        return [c for c in self.cards
                if c.get("note_id") == note_id and c.get("id") != exclude_id]

    def sibling_days(self, note_id: str | None, exclude_id: str | None = None,
                     horizon: int = 120) -> list[int]:
        """兄弟卡未来第几天到期（给 Load Balancer 用）。"""
        tm = time.localtime()
        day0 = time.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday, 0, 0, 0, 0, 0, -1)) * 1000
        out = set()
        for c in self.siblings(note_id, exclude_id):
            if c.get("suspended") or c.get("archived"):
                continue
            d = int((int(c.get("due") or 0) - day0) // DAY)
            if 0 <= d <= horizon:
                out.add(d)
        return sorted(out)

    def add_sibling(self, card_id: str) -> dict | None:
        """把一张卡复制成同笔记的兄弟卡（内容一样、独立调度）。"""
        src = self.card(card_id)
        if not src:
            return None
        note_id = src.get("note_id") or src["id"]
        src["note_id"] = note_id
        t = now_ms()
        copy = {k: v for k, v in src.items() if k not in ("id", "created", "due",
                                                          "interval", "reps", "ease",
                                                          "lapses", "last_review",
                                                          "state", "step",
                                                          "stability", "difficulty",
                                                          "suspended", "archived",
                                                          "buried_until", "done_at")}
        copy.update({
            "id": uid("c_"), "note_id": note_id, "created": t, "due": t,
            "interval": 0.0, "reps": 0, "ease": DEFAULT_EASE, "lapses": 0,
            "last_review": None, "state": "new", "step": 0,
            "suspended": False, "archived": False,
        })
        copy.pop("tags", None)
        copy["tags"] = list(src.get("tags") or [])
        self.cards.append(copy)
        self.save()
        return copy

    def bury_siblings(self, note_id: str | None, exclude_id: str | None = None,
                      persist: bool = True) -> list[str]:
        """把同笔记的其它卡搁置到今天结束（Anki 的 bury siblings）。"""
        out = []
        tm = time.localtime()
        tomorrow = time.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday + 1,
                                0, 0, 0, 0, 0, -1)) * 1000
        for c in self.siblings(note_id, exclude_id):
            if c.get("suspended"):
                continue
            c["buried_until"] = int(tomorrow)
            out.append(c["id"])
        if out and persist:
            self.save()
        return out

    def add_group_cards(self, deck_id: str, group: str, items: list[dict]) -> int:
        """把一批卡片写进指定卡组（卡组不存在则新建）。"""
        d = self.deck(deck_id)
        if d is not None:
            d.setdefault("groups", [])
            if group not in d["groups"]:
                d["groups"].append(group)
            for key in ("archived_groups", "completed_groups"):
                if group in (d.get(key) or []):
                    d[key].remove(group)
        t = now_ms()
        for it in items:
            self.cards.append({
                "id": uid("c_"), "note_id": it.get("note_id") or uid("n_"),
                "deck_id": deck_id, "group": group,
                "type": it["type"], "q": it["q"], "a": it.get("a", ""),
                "options": it.get("options", []), "answer": it.get("answer", []),
                "analysis": it.get("analysis", ""), "tags": [], "created": t,
                "due": t, "interval": 0.0, "reps": 0, "ease": DEFAULT_EASE,
                "lapses": 0, "last_review": None, "suspended": False,
                "archived": False,
            })
        self.save()
        return len(items)

    def rename_group(self, deck_id: str, old: str, new: str) -> int:
        new = (new or "").strip()
        if not new or new == old:
            return 0
        n = 0
        for c in self.cards:
            if c["deck_id"] == deck_id and c.get("group") == old:
                c["group"] = new
                n += 1
        d = self.deck(deck_id)
        if d:
            d["groups"] = [new if g == old else g for g in (d.get("groups") or [])]
            for key in ("archived_groups", "completed_groups"):
                if old in (d.get(key) or []):
                    d[key] = [new if g == old else g for g in d[key]]
            d["group_order"] = [new if g == old else g for g in (d.get("group_order") or [])]
        self.save()
        return n

    def delete_group(self, deck_id: str, group: str) -> int:
        """删除卡组：卡片和复习记录一起进回收站，可恢复。"""
        gone = [c for c in self.cards if c["deck_id"] == deck_id and c.get("group") == group]
        ids = {c["id"] for c in gone}
        self.state["cards"] = [c for c in self.cards if c["id"] not in ids]
        if ids:
            self.reviews[:] = [r for r in self.reviews if r["card_id"] not in ids]
        d = self.deck(deck_id)
        if d:
            d["groups"] = [g for g in (d.get("groups") or []) if g != group]
            for k in ("archived_groups", "completed_groups"):
                if group in (d.get(k) or []):
                    d[k].remove(group)
        self._trash_push("group", group or "未分组",
                         (d.get("name") if d else "") + f" · {len(gone)} 张卡片",
                         {"deck_id": deck_id, "group": group, "cards": gone})
        self.save()
        return len(gone)

    def toggle_group_archive(self, deck_id: str, group: str) -> bool:
        """返回 True 表示现在是「已归档」。卡片与复习记录一张都不动。"""
        d = self.deck(deck_id)
        if not d:
            return False
        arr = d.setdefault("archived_groups", [])
        if group in arr:
            arr.remove(group)
            self.save()
            return False
        arr.append(group)
        self.save()
        return True

    def due_cards(self, deck_id: str | None = None) -> list[dict]:
        t = now_ms()
        skip = {d["id"]: set(d.get("archived_groups") or [])
                | set(d.get("completed_groups") or [])
                for d in self.decks}
        arch_decks = {d["id"] for d in self.decks if d.get("archived")}
        out = []
        for c in self.cards:
            if c["due"] > t or c.get("suspended") or c.get("archived"):
                continue
            if int(c.get("buried_until") or 0) > t:
                continue
            did = c["deck_id"]
            if did in arch_decks or c.get("group") in skip.get(did, ()):
                continue
            if deck_id and did != deck_id:
                continue
            out.append(c)
        return sorted(out, key=lambda c: (c["due"], -c.get("lapses", 0)))

    def add_review(self, card: dict, rating: int, prev_iv: float, next_iv: float, dur: int):
        self.reviews.append({
            "card_id": card["id"], "at": now_ms(), "rating": rating,
            "prev": prev_iv, "next": next_iv, "duration_ms": dur,
        })

    def _reset_cards(self, cards) -> int:
        import time as _t
        now = int(_t.time() * 1000)
        for c in cards:
            c.update(due=now, interval=0.0, reps=0, ease=DEFAULT_EASE,
                     lapses=0, last_review=0, state="new", step=0,
                     stability=0, difficulty=0)
        self.save()
        return len(cards)

    def reset_group_progress(self, deck_id: str, group: str) -> int:
        cards = [c for c in self.cards_of(deck_id) if c.get("group") == group]
        return self._reset_cards(cards)

    def reset_deck_progress(self, deck_id: str) -> int:
        return self._reset_cards(self.cards_of(deck_id))

    # ---- 卡组选项（Anki deck options）----
    def deck_config(self, deck_id: str | None) -> dict:
        cfg = dict(DEFAULT_SCHED)
        cfg.update(self.state.get("settings", {}).get("sched") or {})
        d = self.deck(deck_id) if deck_id else None
        if d:
            cfg.update(d.get("config") or {})
        return cfg

    # Load Balancer 按「预设」聚合：卡组选项完全一样的一组卡包，共用一份负载曲线
    CFG_KEYS = ("learn_steps", "relearn_steps", "graduating", "easy", "retention",
                "new_per_day", "review_per_day", "max_interval", "fuzz",
                "bury_new", "bury_reviews", "easy_days", "load_balance")

    def _cfg_sig(self, cfg: dict) -> str:
        import json
        return json.dumps({k: cfg.get(k) for k in self.CFG_KEYS},
                          sort_keys=True, default=str)

    def preset_deck_ids(self, deck_id: str | None) -> list[str]:
        """和这个卡包共用同一套卡组选项的所有卡包。"""
        if not deck_id:
            return [d["id"] for d in self.decks]
        sig = self._cfg_sig(self.deck_config(deck_id))
        ids = [d["id"] for d in self.decks
               if self._cfg_sig(self.deck_config(d["id"])) == sig]
        return ids or [deck_id]

    def due_counts(self, deck_id: str | None = None, days: int = 100) -> list[int]:
        """未来 N 天每天有多少卡到期（Load Balancer 的数据来源，按预设聚合）。"""
        tm = time.localtime()
        day0 = time.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday, 0, 0, 0, 0, 0, -1)) * 1000
        counts = [0] * (days + 1)
        ids = set(self.preset_deck_ids(deck_id)) if deck_id else None
        for c in self.cards:
            if ids is not None and c.get("deck_id") not in ids:
                continue
            if c.get("suspended") or c.get("archived"):
                continue
            d = int((int(c.get("due") or 0) - day0) // DAY)
            if 0 <= d <= days:
                counts[d] += 1
        return counts

    def sched_cfg(self, deck_id: str | None = None,
                  note_id: str | None = None, card_id: str | None = None) -> dict:
        """调度用的配置：卡包选项 + 未来到期直方图 + 兄弟到期日（给 Load Balancer）。"""
        cfg = self.deck_config(deck_id)
        cfg["load_counts"] = self.due_counts(deck_id)
        cfg["sibling_days"] = self.sibling_days(note_id, card_id)
        cfg["easy_days"] = list(cfg.get("easy_days") or [1.0] * 7)
        cfg["weekday0"] = time.localtime().tm_wday      # 周一=0
        return cfg

    def set_deck_config(self, deck_id: str, **kw):
        d = self.deck(deck_id)
        if not d:
            return False
        d.setdefault("config", {}).update(kw)
        self.save()
        return True

    def set_global_sched(self, **kw):
        self.state.setdefault("settings", {}).setdefault("sched", {}).update(kw)
        self.save()

    # ---- 今日进度 / 限额 ----
    def deck_stats(self, deck_id: str | None) -> dict:
        """当天该卡包的新卡/复习计数（跨天自动归零）。"""
        d = self.deck(deck_id) if deck_id else None
        if not d:
            return {}
        st = d.setdefault("stats", {})
        today = day_str()
        if st.get("day") != today:
            if st.get("day") is None:
                # 老数据第一次升级：用今天的 review 日志补出来，别把当天已学清零
                n, r = self._count_today_from_reviews(deck_id)
                st.update({"day": today, "new": n, "rev": r})
            else:
                st.update({"day": today, "new": 0, "rev": 0})
        return st

    def _count_today_from_reviews(self, deck_id: str | None) -> tuple[int, int]:
        tm = time.localtime()
        today = (tm.tm_year, tm.tm_yday)
        new_n = rev_n = 0
        for r in self.reviews:
            lt = time.localtime(r["at"] / 1000)
            if (lt.tm_year, lt.tm_yday) != today:
                continue
            c = self.card(r["card_id"])
            if not c or (deck_id and c["deck_id"] != deck_id):
                continue
            if int(c.get("reps") or 0) <= 1:
                new_n += 1
            else:
                rev_n += 1
        return new_n, rev_n

    def bump_deck_stats(self, deck_id: str | None, was_new: bool,
                        was_review: bool, persist: bool = True):
        """评分时累加（Anki 的 new_today / review_today 是持久计数，不是回头数日志）。"""
        st = self.deck_stats(deck_id)
        if not st:
            return
        if was_new:
            st["new"] = int(st.get("new") or 0) + 1
        elif was_review:
            st["rev"] = int(st.get("rev") or 0) + 1
        if persist:
            self.save()

    def today_counts(self, deck_id: str | None = None) -> tuple[int, int]:
        """(今日新学数, 今日复习数)。优先用卡包里的持久计数。"""
        st = self.deck_stats(deck_id)
        if st:
            return int(st.get("new") or 0), int(st.get("rev") or 0)
        tm = time.localtime()
        today = (tm.tm_year, tm.tm_yday)
        new_n = rev_n = 0
        for r in self.reviews:
            lt = time.localtime(r["at"] / 1000)
            if (lt.tm_year, lt.tm_yday) != today:
                continue
            c = self.card(r["card_id"])
            if not c or (deck_id and c["deck_id"] != deck_id):
                continue
            if int(c.get("reps") or 0) <= 1:
                new_n += 1
            else:
                rev_n += 1
        return new_n, rev_n

    def study_queue(self, deck_id: str | None = None,
                    group: str | None = None) -> list[dict]:
        """按卡组选项的每日上限组队列：到期复习卡 + 新卡（各自受限额）。"""
        cfg = self.deck_config(deck_id)
        new_done, rev_done = self.today_counts(deck_id)
        new_left = max(0, int(cfg["new_per_day"]) - new_done)
        rev_left = max(0, int(cfg["review_per_day"]) - rev_done)
        # Anki：新卡也会吃掉复习额度（NewCardsIgnoreReviewLimit 默认关）
        new_left = min(new_left, max(0, rev_left - new_done))
        due = self.due_cards(deck_id)
        if group:
            due = [c for c in due if c.get("group") == group]
        # Anki 的「提前学习」：20 分钟内到期的学习卡也拿出来
        ahead = now_ms() + 20 * 60 * 1000
        seen = {c["id"] for c in due}
        extra = [c for c in self.cards
                 if c["id"] not in seen and c.get("state") in ("learning", "relearning")
                 and int(c.get("due") or 0) <= ahead and not c.get("suspended")
                 and not c.get("archived")
                 and int(c.get("buried_until") or 0) <= now_ms()
                 and (not deck_id or c["deck_id"] == deck_id)
                 and (not group or c.get("group") == group)]
        due = due + extra
        now = now_ms()
        learning = [c for c in due if c.get("state") in ("learning", "relearning")]
        learn_now = [c for c in learning if int(c.get("due") or 0) <= now]
        learn_ahead = [c for c in learning if int(c.get("due") or 0) > now]
        reviews = [c for c in due if int(c.get("reps") or 0) > 0
                   and c.get("state") not in ("learning", "relearning")]
        new = [c for c in due if int(c.get("reps") or 0) == 0]
        # Anki 的顺序：到点的学习卡 → 复习/新卡（按比例交错）→ 提前学习（learn ahead）
        main = _intersperse(reviews[:rev_left], new[:new_left])
        return learn_now + main + learn_ahead

    # ---- 搁置 / 暂停 ----
    def bury_card(self, card_id: str):
        """搁置到明天（当天 0 点前不再出现）。"""
        import time as _t
        c = self.card(card_id)
        if not c:
            return False
        tm = _t.localtime()
        tomorrow = _t.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday + 1, 0, 0, 0, 0, 0, -1))
        c["buried_until"] = int(tomorrow * 1000)
        self.save()
        return True

    def suspend_card(self, card_id: str, suspended: bool = True):
        c = self.card(card_id)
        if not c:
            return False
        c["suspended"] = bool(suspended)
        self.save()
        return True

    def reset_progress(self):
        t = now_ms()
        for c in self.cards:
            c.update(due=t, interval=0.0, reps=0, ease=DEFAULT_EASE,
                     lapses=0, last_review=None)
        self.reviews.clear()
        self.save()


# ---------------------------------------------------------------- 初始数据

SEED_CARDS = [
    # (deck_key, group, type, q, a, options, answer, analysis)
    ("renxing", "第一章 关于人性", "multi",
     "原文主张的期待管理方法包括哪些？",
     "社交初始不让别人对自己抱太高期待；施恩要自薄而厚，请客要前轻后重。",
     ["社交初期不抬高期待", "一开始就全力付出", "请客安排前轻后重", "施恩自薄而厚"],
     [0, 2, 3],
     "「一开始就全力付出」恰是原文反对的做法：它会把对方的期待抬到最高。"),
    ("renxing", "第一章 关于人性", "single",
     "以下哪一项最符合原文对「期待管理」的主张？",
     "先压低预期，后续超出预期才会有惊喜。",
     ["一开始就全力付出", "社交初期不抬高期待，施恩自薄而厚",
      "对所有人都保持同样的高期待", "完全不抱任何期待，随波逐流"],
     [1],
     "原文主张「施恩要自薄而厚」「请客要前轻后重」。"),
    ("renxing", "第一章 关于人性", "qa",
     "降低期待能带来哪些好处？",
     "事情落空的概率会减少很多。当进展超过预期，人生反而平添一些惊喜——这就是原文说的「幸福的秘诀」。放下高期待不是随波逐流，而是把能做的做好、把无法掌控的放下。",
     [], [], ""),
    ("renxing", "第一章 关于人性", "qa",
     "为什么「降低期待」不等于没有追求？",
     "它只是把能做的做好、把无法掌控的放下，仍然保有行动，只是不再把结果当成必须。",
     [], [], ""),
    ("renxing", "第二章 让人喜欢你", "qa",
     "让别人喜欢你的第一条原则是什么？",
     "真诚地关心别人。原文强调：对别人不感兴趣的人，一生中困难最多、对别人的伤害也最大。",
     [], [], ""),
    ("renxing", "第二章 让人喜欢你", "single",
     "以下哪种做法最能让人感到被重视？",
     "记住并使用对方的名字，会让对方感到被重视。",
     ["记住并使用对方的名字", "频繁打断对方说话",
      "只谈自己感兴趣的话题", "在对话中不断看手机"],
     [0], "名字对任何人来说，都是最甜美、最重要的声音。"),
    ("english", "雅思核心词", "qa",
     "ubiquitous 的准确含义？",
     "无处不在的、普遍存在的，常用于描述技术或现象广泛分布。",
     [], [], ""),
    ("english", "雅思核心词", "qa",
     "mitigate 的常用宾语？",
     "mitigate risk、damage、impact 或 effects，意为缓解、减轻。",
     [], [], ""),
    ("english", "雅思核心词", "single",
     "pragmatic 与 practical 的语感区别是？",
     "pragmatic 更强调务实和结果导向；practical 更强调实际可行。",
     ["pragmatic 更强调务实和结果导向", "两者完全同义",
      "practical 更强调理论", "pragmatic 只用于贬义"],
     [0], ""),
    ("english", "雅思核心词", "multi",
     "以下哪些词表示「普遍存在的」？",
     "ubiquitous / prevalent / widespread 都可表示普遍存在。",
     ["ubiquitous", "prevalent", "widespread", "ephemeral"],
     [0, 1, 2], "ephemeral 意为「短暂的」，意思相反。"),
    ("bio", "细胞结构", "qa",
     "线粒体的主要功能是什么？",
     "线粒体是细胞的能量工厂，主要通过有氧呼吸产生 ATP。",
     [], [], ""),
    ("bio", "细胞结构", "single",
     "植物细胞与动物细胞共有的细胞器是？",
     "线粒体、核糖体、内质网、高尔基体等为两者共有；叶绿体为植物特有。",
     ["叶绿体", "线粒体", "中心体", "细胞壁"],
     [1], "叶绿体是植物细胞特有；中心体见于动物细胞。"),
    ("bio", "细胞结构", "multi",
     "以下哪些属于细胞器？",
     "线粒体、核糖体、高尔基体都是细胞器；细胞膜是结构而非细胞器。",
     ["线粒体", "核糖体", "高尔基体", "细胞膜"],
     [0, 1, 2], "细胞膜是细胞的边界结构。"),
    ("product", "需求", "qa",
     "什么是「伪需求」？",
     "用户口头表达、但不愿为之付出成本的需求。判断标准是看行为，而不是听说法。",
     [], [], ""),
    ("product", "需求", "multi",
     "验证需求真伪的常用方法包括？",
     "看是否有人愿意付费、是否已有替代方案、使用频率是否足够。",
     ["看是否有人愿意付费", "看是否已有替代方案", "看使用频率", "看 PPT 写得好不好"],
     [0, 1, 2], ""),
    ("coffee", "手冲", "qa",
     "手冲咖啡的水温建议范围？",
     "浅烘 90–93°C，中烘 88–92°C，深烘 85–88°C。水温越高萃取越快，苦味也更明显。",
     [], [], ""),
]


def seed() -> dict:
    t = now_ms()
    rounds = [
        {"id": "r_exam", "name": "考试冲刺", "domain": "study", "parent_id": None,
         "created": t - 20 * DAY},
        {"id": "r_eng", "name": "英语", "domain": "study", "parent_id": "r_exam",
         "created": t - 18 * DAY},
        {"id": "r_work", "name": "工作方法", "domain": "work", "parent_id": None,
         "created": t - 12 * DAY},
    ]
    decks = [
        {"id": "renxing", "name": "有道暗记", "domain": "study", "color": "#2F6A43",
         "template": "sky", "parent_id": None, "created": t - 30 * DAY,
         "groups": ["第一章 关于人性", "第二章 让人喜欢你"],
         "archived_groups": [], "completed_groups": []},
        {"id": "english", "name": "英语 · 雅思核心词", "domain": "study", "color": "#426A80",
         "template": "sky", "parent_id": "r_eng", "created": t - 16 * DAY,
         "groups": ["雅思核心词"], "archived_groups": [], "completed_groups": []},
        {"id": "bio", "name": "细胞生物学", "domain": "study", "color": "#6D5F8E",
         "template": "sky", "parent_id": "r_exam", "created": t - 14 * DAY,
         "groups": ["细胞结构"], "archived_groups": [], "completed_groups": []},
        {"id": "product", "name": "产品方法论", "domain": "work", "color": "#426A80",
         "template": "sky", "parent_id": "r_work", "created": t - 10 * DAY,
         "groups": ["需求"], "archived_groups": [], "completed_groups": []},
        {"id": "coffee", "name": "咖啡笔记", "domain": "life", "color": "#B85D3C",
         "template": "sky", "parent_id": None, "created": t - 6 * DAY,
         "groups": ["手冲"], "archived_groups": [], "completed_groups": []},
    ]

    cards = []
    for i, (deck_id, group, typ, q, a, options, answer, analysis) in enumerate(SEED_CARDS):
        # 前 8 张已到期（今日有内容），其余分散到未来几天
        if i < 8:
            due = t - (i + 1) * 60_000
            reps, iv = (2, 3.0) if i % 3 == 0 else (0, 0.0)
        else:
            due = t + (i - 7) * DAY
            reps, iv = (4, 15.0) if i % 2 == 0 else (1, 3.0)
        cards.append({
            "id": uid("c_"), "note_id": uid("n_"),
            "deck_id": deck_id, "group": group, "type": typ,
            "q": q, "a": a, "options": options, "answer": answer,
            "analysis": analysis, "tags": [],
            "created": t - (len(SEED_CARDS) - i) * 120_000,
            "due": due, "interval": iv, "reps": reps, "ease": DEFAULT_EASE,
            "lapses": 1 if i in (3, 6) else 0,
            "last_review": (t - 3 * DAY) if i % 3 == 0 else None,
            "suspended": False, "archived": False,
        })

    # 造一批历史复习记录（示例数据，让洞察 / 连续天数有内容）
    import random
    random.seed(20261109)
    reviews = []
    for i in range(72):
        c = cards[i % len(cards)]
        at = t - random.randint(0, 13) * DAY - random.randint(0, 8) * 3_600_000
        rating = random.choices([0, 1, 2, 3], weights=[1, 2, 6, 2])[0]
        reviews.append({"card_id": c["id"], "at": at, "rating": rating,
                        "prev": 0.0, "next": 1.0,
                        "duration_ms": random.randint(4000, 15000)})
    reviews.sort(key=lambda r: r["at"])

    return {
        "version": 1,
        "domains": [dict(d) for d in DEFAULT_DOMAINS],
        "rounds": rounds,
        "decks": decks,
        "cards": cards,
        "reviews": reviews,
        "settings": {
            "dark": False,
            "daily_new_limit": 20,
            "goal": "每天保持 15 分钟",
            "default_template": "sky",
        },
    }
