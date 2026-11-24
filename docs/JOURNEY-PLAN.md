# 征途 · 打卡改名 × Habitica 玩法融合 —— 落地实施方案

> 设计稿：`design/journey/index.html`（5 屏 + 深色）
> 效果图：`design/journey/_shots/overview.png`、`journey.png`、`quests.png`、`party.png`、`rewards.png`、`levelup.png`、`journey-dark.png`
> 目标工程：`app/`（PySide6 桌面端「浮卡」）

---

## 0. 一句话方案

**界面层把「打卡」这个词全部换成「征途」；把原本"番茄专注 → 打小怪 → 勋章"的单线，升级成 Habitica 的五件事：角色状态（等级/生命/经验/金币）、三类任务（习惯·每日·待办）、每日结算与连击、队伍副本、奖励商店。** 番茄专注保留为"行动入口"——专注结束 = 记一次征途 = 造成 1 点伤害。

---

## 1. 改名清单（纯文案，不动内部 API）

| # | 文件:行 | 现在 | 改成 |
|---|---|---|---|
| 1 | `app/app.py:45` | `("plan", "打卡")` | `("plan", "征途")` |
| 2 | `app/app.py:193` | `# ---------- 打卡：番茄计时 ----------` | `# ---------- 征途：番茄计时 ----------` |
| 3 | `app/app.py:197` | `开始专注 {mins} 分钟，结束后自动打卡` | `开始专注 {mins} 分钟，结束后自动记一次征途` |
| 4 | `app/app.py:220` | `打卡成功！累计 {n} 次` | `征途 +1 · 累计 {n} 次` |
| 5 | `app/pages/plan.py:2` | docstring `打卡：番茄专注 → 打卡 → …` | `征途：番茄专注 → 记一次征途 → …` |
| 6 | `app/pages/plan.py:182` | docstring `打卡页：…` | `征途页：…` |
| 7 | `app/pages/plan.py:204` | `self.hero("打卡", …)` | `self.hero("征途", …)` |
| 8 | `app/pages/plan.py:277` | `再打卡 {left} 次击败它` | `再专注 {left} 次击败它` |
| 9 | `app/pages/plan.py:299` | `再打卡 {n} 次升级为{medal}` | `再专注 {n} 次升级为{medal}` |
| 10 | `app/pages/plan.py:329` | `最近 7 天打卡` | `最近 7 天征途` |
| 11 | `app/pages/plan.py:399/406` | `结束后自动打卡` / `专注结束后自动打卡` | `结束后自动记一次征途` |
| 12 | `app/core.py:436` | docstring `记一次打卡（番茄结束）` | `记一次征途（番茄结束）` |
| 13 | `app/README.md:229` | 功能表「打卡」 | 「征途」 |

**故意不改的：**

- `Store.checkins` / `Store.add_checkin()` / JSON 键 `"checkins"` —— 这是**同步协议的一部分**（`sync.py`、`backup.py`、局域网/WebDAV/S3 都按这个键读写）。改名会让旧备份对不上。
- `MAIN_TABS` 的 key `"plan"` —— 大量 `if key == "plan"` 与 `scripts/patch_*.py` 依赖它。
- 想彻底改名的话，做成**别名迁移**：新增 `add_journey()`（内部调 `add_checkin`），UI 只调新名字；`checkins` 键保留并加 `"_migrated": true` 标记。

---

## 2. 数据模型：`state["game"]`

全部塞进现有 `store.state`（一个 JSON，`save()` 原子写盘），不改同步格式的顶层结构：

```jsonc
"game": {
  "lv": 12, "xp": 320, "hp": 42, "hp_max": 50,
  "gold": 128, "gems": 4,
  "attrs": {"str": 12, "int": 9, "con": 11, "per": 8},
  "streak": 12, "last_day": "2026-11-22",

  "habits": [
    {"id": "h1", "title": "晨间拉伸 10 分钟", "dir": "both", "xp": 6,  "gold": 2},
    {"id": "h2", "title": "刷手机超过 1 小时", "dir": "both", "xp": -8, "gold": 0}
  ],
  "dailies": [
    {"id": "d1", "title": "复习到期卡片", "diff": "medium", "streak": 12,
     "last_done": "2026-11-21", "history": {"2026-11-20": 1, "2026-11-21": 1}}
  ],
  "todos": [
    {"id": "t1", "title": "整理「细胞结构」错题", "due": 1763856000000,
     "xp": 15, "gold": 5, "done": false}
  ],
  "rewards": [
    {"id": "r1", "title": "看一集剧", "price": 20, "tag": "娱乐", "redeemed": 3}
  ],
  "boss": {"key": "procrastination", "hp": 68, "hp_max": 100,
           "ends_at": 1764200000000, "damage": {"me": 38, "a": 27}},
  "badges": ["novice", "bronze", "silver"]
}
```

`load()` 里补一段 `self.state.setdefault("game", default_game())`，老用户无损升级。

---

## 3. 数值规则（可调，先定一版）

| 事件 | 经验 XP | 金币 GP | 生命 HP |
|---|---|---|---|
| 专注 15 分钟 | +9 | +6 | — |
| 完成每日（简单/中等/困难） | +8 / +12 / +18 | +2 / +4 / +6 | — |
| 每日到 24:00 未完成 | — | — | −3 |
| 完成待办 | 按登记值（默认 +15~25） | +5~10 | — |
| 好习惯点「+」 | +6 | +2 | — |
| 坏习惯点「−」 | — | — | −8 |

派生公式：

```
xp_need(lv)  = 100 + 40 * (lv - 1)        # Lv.12 → 560，正好对上设计稿
level_up     : hp_max += 5, hp = hp_max, attrs_point += 1, 解锁下一档徽章
streak_mult  = 1 + min(streak, 30) * 0.02 # 连击加成，上限 +60%
gain         = base * diff_mult * streak_mult
diff_mult    = easy 1.0 / medium 1.5 / hard 2.2
down         : gold = gold * 0.9 (取整), hp = hp_max, streak = 0
```

**每日结算（cron）**：`last_day != today` 时执行一次，遍历 `dailies`，`last_done != today` 的扣血并把 `streak` 归零；然后 `last_day = today`。用本地日期（00:00 而不是 UTC），避免跨时区"提前扣血"。

---

## 4. 界面结构：把 `plan.py` 拆成 1 + 3

设计稿对应到代码（**前两行已落地**，见 §4.1）：

| 设计稿 | 代码落点 | 复用 |
|---|---|---|
| 01 征途 · 总览 | ✅ `pages/journey_panels.py::OverviewPanel` | 任务卡（含「重置」）、青蛙 `Monster`、青蛙勋章 `MedalDot`（角色卡已移除；副本/奖励分段已删） |
| 02 征途 · 数据 | ✅ `RecordsPanel`（最近 7 天 + 活跃热力 + 准确率）+ `FrogRecordsPage`（吃蛙时间线） | `W.Card`、`WeekBars` |
| 03 征途 · 副本 | ✅ `PartyPanel` | `Monster`、`ThinBar`、`W.Pill` |
| 04 征途 · 奖励 | ✅ `RewardsPanel` + `AddRewardDialog` | `W.HeroCard`、`W.GhostButton`、`ThinBar` |
| 05 每日结算 | ✅ `journey_dialogs.py::SettleDialog` | `W.Card`、`W.PrimaryButton` |
| 06 升级弹层 | ✅ `journey_dialogs.py::LevelUpDialog` | `W.Chip` 分配属性点 |
| 07 学习页 · 顶栏计时 | ✅ `pages/review.py::QuestPill` | 顶栏 `top_lay` 空位 |

页面骨架：`pages/plan.py::PlanPage` = 页头 + 四段控件 + 面板（`TABS` / `PANELS` 两张表决定顺序）。

总览页自上而下的组件顺序（与设计稿一一对应）：

```
Page.hero("征途", "今日 3 次专注 · 连续 12 天")
└─ Card(今日任务)          ← 任务卡三态：未领取 / 进行中 / 已完成
└─ Card(吃掉那只青蛙)      青蛙(QPainter) + 两个大数字（吃了多少只 / 累计时长）+ 勋章
└─ Card(最近 7 天)         每天学习时长柱状图
```

`Monster` 的 `paintEvent` 已经是"圆滚滚 + 犄角 + 眼睛"，Boss 只是换配色/放大到 132px，可复用同一套 QPainter 路径。

### 4.1 任务卡状态机（已实现）

```
idle ──开关打开（武装 N 分钟）──▶ active ──学习页累计满 N 分钟──▶ done
  ▲                                  │  ↑                          │
  └──────────── 开关关闭 ────────────┘  └── 进/出学习页 自动跑表/暂停 ──┘
```

任务卡是一个**开关**：打开 = 武装任务（时长固定 15 分钟），关闭 = 取消任务。开关只决定「这个任务算不算数」，**计时仍然只认学习页**：进复习页自动接着跑，离开自动暂停，不需要手动点暂停。

- 状态存在 `store.state["quest"]`：`status / mins / target_ms / acc_ms / running_since / reward`。
- 奖励：`xp = round(mins × 0.6)`、`gold = round(mins × 0.4)` → 15 分钟 = **+9 经验 +6 金币**。
- 完成时**同时**往 `checkins` 记一条（所以「最近 7 天」「小怪」「勋章」照旧往前走，一次任务 = 原来的一次打卡）。
- 代码：`core.py` 的 `quest / quest_claim / quest_start_clock / quest_pause_clock / quest_elapsed / quest_complete / quest_reset`；
  `app.py` 的 `claim_quest / abandon_quest / _quest_tick / _refresh_quest_ui`；`plan.py` 的 `_paint_quest / refresh_quest`。

### 4.2 计时只认学习页（已实现）

| 事件 | 行为 |
|---|---|
| 进学习页 | `quest_start_clock()` 自动接着跑表 |
| 离开学习页 | `quest_pause_clock()` 自动暂停，累计保留 |
| 最小化 / 关闭 | 暂停（`WindowStateChange` / `closeEvent`） |
| 窗口失焦 | **不暂停**：截图、切去看资料都很常见，一失焦就冻住会像坏掉 |
| 开关关闭 | 取消任务（回到 idle，进度清零；已完成则关掉后可直接领下一个） |
| 回到 review | 续上，不清零 |
| 异常退出（`running_since` 残留） | 加载时清零标记，**不把关机时间算成学习时长** |
| 累计 ≥ `target_ms` | 每秒的 `_quest_tick` 自动结算、发奖、Toast、卡片转「已完成」 |

学习页顶栏中间（原来的空位）放了一颗 `QuestPill`：

| 状态 | 显示 | 说明 |
|---|---|---|
| 未领取 | **空白** | 整个胶囊隐藏，这块只留空白 |
| 计时中 | `14:58`（绿底绿字） | 倒计时，无图标 |
| 暂停 | `14:58`（灰底灰字） | 切走页面 / 最小化后停住 |
| 已完成 | **空白** | 任务结束后同样隐藏 |

回归脚本：`_scratch/test_quest.py`（15 项断言全通过）；截图：`app/shots/60~64-quest-*.png`。

### 4.3 征途内部的分段导航（不新增底部 tab）

底部仍是 4 个 tab（今日 / 记忆 / 征途 / 细数）。「征途」页头下面放一条 4 段控件：

```
总览 │ 任务 │ 副本 │ 奖励
```

- 用现有 `W.Chip` 或自绘的 `SegControl`（`QWidget` + `QHBoxLayout` + 两个圆角背景）；
- 切换时**不重建整页**：`PlanPage` 里用一个 `QStackedWidget` 装 4 个 `QWidget` 子面板，
  切 tab 只 `setCurrentIndex`，避免每次都跑 `build()`（任务列表可有几十行）；
- 当前分段记在 `store.settings["journey_tab"]`，下次进来回到上次的分段。

### 4.4 三个新页面的实现映射

**数据页（`RecordsPanel`）**——最近 7 天柱状图 + 31 天活跃 + 准确率

| 设计稿元素 | 实现 | 数据 |
|---|---|---|
| 按天分组（今天 / 昨天 / MM-DD） | `records_grouped()` 分组，每组一张卡 | `game.records[]` |
| 完成行：✓ + 划线标题 + 时间/奖励 | `CheckBtn(True)` + 删除线字体 + 一行小字 | `at / title / xp / gold` |
| 空状态 | 「还没有完成记录」+「去总览领取任务」 | — |
| 写入时机 | 征途完成 / 每日 / 待办 / 习惯 各自 `store.record(...)` | — |

~~**任务页（`pages/quests.py`）**~~（已被数据页取代）

| 设计稿元素 | 实现 | 数据 |
|---|---|---|
| 每日行：勾选框 + streak 火苗 + 难度 | `W.ListRow` + 自绘 `Check`（复用） + `QLabel("🔥12")` | `game.dailies[]` |
| 习惯行：＋ / − 两个按钮 | `HabBtn`（QPushButton，绿/红描边） | `game.habits[]` |
| 待办行：勾选 + 到期 + 金币 | `W.ListRow` + 右侧 `W.Pill` | `game.todos[]` |
| 今日战报 | `W.Card` + 3 个 `Pill` | 当日聚合 |
| 勾选动作 | `store.score_daily(id)` / `score_todo(id)` / `score_habit(id, ±1)` → 发 XP/金币、改 streak、`save()` | — |

**副本页（`pages/party.py`）**

| 设计稿元素 | 实现 |
|---|---|
| Boss 立绘 | 复用 `plan.py` 的 `Monster`，构造参数改 `size=132`，配色换紫 |
| Boss 血条 | `W.Bar`（现有），绑定 `game.boss.hp / hp_max` |
| 队伍伤害榜 | 4 行 `W.ListRow`，每行一个 `W.Bar` 细条 |
| 投入专注 CTA | `app.show_page("plan")` 并自动展开任务卡（或直接 `start_review()`） |
| 结算 | Boss 血量为 0 时，按 `damage` 占比发 `gold / gems / badge`，然后生成下一只 |

**奖励页（`pages/rewards.py`）**

| 设计稿元素 | 实现 |
|---|---|
| 金币大卡 | `W.Card` + 大字号（沿用 hero 渐变） |
| 奖励行 | `W.ListRow`，右侧「兑换」`W.PrimaryButton`（窄） |
| 添加自定义奖励 | 复用 `pages/tools.py` 的输入弹窗写法 |
| 徽章墙 | 复用 `Medal`，6 个一排，未解锁用 `setEnabled(False)` + 灰度 |
| 兑换 | `store.redeem_reward(id)`：`gold -= price`，记一条 `redemptions[]` |

**每日结算 / 升级弹层**

- 结算：`app._quest_tick` 旁边加一个「跨天检查」（`last_day != today` 才跑一次），
  弹 `SettleDialog`，内容 = 完成/漏做/连击/金币四项；确认按钮只做 `hide()`。
- 升级：`store.add_xp()` 里检测 `xp >= xp_need(lv)` → 发信号 → `MainWindow` 弹 `LevelUpDialog`。

---

## 5. Habitica 功能取舍

| Habitica 能力 | 采用 | 说明 |
|---|---|---|
| 习惯 / 每日 / 待办 三类型 | ✅ | 核心；替换现在只有"打卡次数"的单指标 |
| 等级 / HP / XP / 金币 | ✅ | 设计稿角色卡 |
| 难度（简单/中等/困难） | ✅ | 影响奖励倍率 |
| 连击 streak + 火苗 | ✅ | 每日连续完成 |
| 每日 24:00 结算（cron） | ✅ | 未完成扣血 |
| 队伍副本 / Boss 伤害榜 | ✅ 本地版 | 队友先用"本地虚构/多用户档"；真实多人需要后端 |
| 奖励商店（金币换自定义奖励） | ✅ | 这是最能提升留存的一环 |
| 徽章 / 成就 | ✅ | 复用现有勋章等级 |
| 装备 / 宠物 / 职业 / 技能 | ⏸ 暂缓 | 玩法重、和"背单词"关系弱 |
| 宝石内购、Google 内购 | ❌ | 桌面端无意义 |
| Habitica 账号绑定 | ⏸ 可选 | 见 §6 |

---

## 6. 可选：与 Habitica 账号同步

我们刚从 `habitica.apk` 逆向出完整接口（见 `../habitica-analysis/api-endpoints.md`），同步是可行的：

```
POST https://habitica.com/api/v4/user/auth/local/login         {username,password} → {id, apiToken}
GET  /api/v4/tasks/user                                         → 三类任务
POST /api/v4/tasks/{id}/score/{up|down}                         → 打分
GET  /api/v4/user/                                              → stats/hp/exp/gp/lvl
```

请求头只要三件（来自 `ApiClientImpl` 拦截器）：

```
x-api-user: <userId>
x-api-key:  <apiToken>
x-client:   habitica-android
```

注意两点：

1. **不要**照抄 APK 里的 `Authorization: Basic YWRtaW46…`（那是它自己的 staging 头，见逆向报告 §9.3a），我们不该带；
2. 冲突策略建议**本地为准、单向推送**：本地打分 → 推 Habitica；不拉取覆盖，避免两边数值打架。

---

## 7. 落地状态

| 里程碑 | 内容 | 状态 |
|---|---|---|
| **M1** | 改名 + 角色卡（等级/HP/XP/金币/属性） | ✅ 界面已改；角色卡后按需求从总览页移除（2026-11-22） |
| **M2** | 三类任务页 + 每日结算 + 连击 | ✅ `TasksPanel` + `SettleDialog` + `run_daily_cron` |
| **M3** | Boss 副本（本地单人、伤害结算） | ✅ `PartyPanel` + `damage_boss`（多人队伍留待后端） |
| **M4** | 奖励商店 + 徽章墙 + 升级弹层 | ✅ `RewardsPanel` + `LevelUpDialog` + 属性点分配 |
| **M5**（可选） | Habitica 账号同步 | ⏸ 未做（端点与请求头已在 §6 备好） |

验证：`_scratch/shot_journey.py` 的 22 项断言全通过（打分/连击/扣血/升级/兑换/Boss/跨天结算），
`_scratch/test_quest.py` 的 15 项计时断言仍全通过，`app/smoke.py` 开窗自检 `SMOKE OK`。
截图：`app/shots/70~77-journey-*.png`。

代码分布：

| 文件 | 职责 |
|---|---|
| `core.py` | `game` 数值模型、三类任务打分、奖励商店、Boss、`run_daily_cron`、升级 |
| `pages/plan.py` | 征途页骨架（页头 + 四段 + 面板桩） |
| `pages/journey_panels.py` | 总览 / 任务 / 副本 / 奖励 四个面板 |
| `pages/journey_widgets.py` | 小怪、勾选方块、细条、勋章（自绘件） |
| `pages/journey_dialogs.py` | 每日结算 / 升级 / 加奖励 三个弹层 |
| `pages/review.py` | 学习页顶栏计时胶囊 `QuestPill` |

---

## 8. 风险与注意

1. **同步兼容**：`state` 里加 `"game"` 键，老版本客户端读到会忽略，但**旧客户端写回时会丢掉它** —— 多人/多端同步场景要升 `state["schema"]`，或在 `sync.py` 做 merge 时保留未知键。
2. **改名 vs patch 脚本**：`scripts/patch_*.py` 里有 2 处锚定 `pages/plan.py`（`W.IconButton("⚙", 38)`、`cards = [c for c in s.active_cards()…]`），锚的是**代码片段而不是"打卡"文案**，所以单纯改名不受影响；但只要按 §4 把 `plan.py` 拆页/重构，这些补丁就会失配——建议把它们标记为"已并入主干"再删，避免以后重复执行。
3. **日期边界**：结算用本地 00:00；用户改系统时间会导致重复结算，用 `last_day` 单调保护。
4. **数值平衡**：Lv.12 需要 560 XP ≈ 63 次 15 分钟专注，大约 2~3 周，节奏合适；偏快就调 `40` 这个系数。
5. **性能**：`game` 与 `checkins` 同在一个 JSON，`save()` 是全量写盘；任务历史 `history` 只保留最近 60 天，避免文件无限膨胀。

---

## 9. 设计稿怎么改

`design/journey/index.html` 单文件、零依赖：

- 配色：改 `:root` 的 12 个变量（深色在 `html[data-theme="dark"]`）；
- 内容：改 `D` 对象（`me`/`days`/`boss`/`habits`/`dailies`/`todos`/`party`/`rewards`/`badges`）；
- 出图：`python design/journey/capture.py`（Edge 无头，390×844@2x，自动拼 `_shots/overview.png`）。

---

## 10. 青蛙勋章的阶梯（2026-11-22）

**一只青蛙 = 一次 15 分钟专注**（完成一次征途就吃掉一只）；
「吃掉那只青蛙」卡里是两个大数字：**已吃青蛙 N 只**、**累计学习 X 小时 Y 分**，一眼能看清。
勋章看累计吃掉的数量，**先密后疏**：

| 勋章 | 需要青蛙 | 大致节奏 |
|---|---|---|
| 蝌蚪 | 0 | 起点 |
| 初尝蛙味 | 1 | 第一天 |
| 蛙群学徒 | 5 | 一周内 |
| 蛙群克星 | 15 | 半个月 |
| 铁胃猎手 | 30 | 一个月 |
| 蛙宴大师 | 60 | 两个月 |
| 百蛙斩 | 100 | 三个多月 |
| 蛙王 | 200 | 半年多 |
| 蛙神 | 365 | 一年（每天一只） |
| 蛙皇 | 500 | 一年半 |
| 蛙帝 | 1000 | 三年 |
| 蛙仙 | 2000 | 五年多 |
| 蛙圣 | 5000 | 长期目标 |

- 总览页底部是一张独立的「青蛙勋章」卡：8 枚小圆点 + 到下一枚的进度条；
- 右上角「已解锁 N / 8 ›」可点，进入**勋章页**：每一枚的门槛、解锁时间（第几只青蛙、哪一刻）、还差几只；，已解锁是彩底白星，未解锁是灰底灰星；
- 文案：两个大数字（已吃 N 只 / 累计 X 小时）+ 当前「X」· 下一枚「Y」还差 Z 只；
- 数据来源：journey_widgets.FROG_MEDALS 与 rog_medal()，sync_badges() 用同一份阈值，避免两处不同步。


## 学习时长怎么算（零头不丢）

- **跨天清零**：新的一天任务回到 15:00、开关关闭；昨天没学满 15 分钟的那段计时**和这段时间一起清掉**（累计学习不保留）；唯一例外是「0 点那一刻还在学习页计时」——不清零、时间照算；
- `study_minutes()` = 已完成任务的 checkins + 当前这次任务已跑的时间（未完成时实时显示，被重置/跨天清零时一起清掉）；`study_banked` 只用于兼容旧版本存下的零头；
- 进行中就计入「累计学习」，跨天不清零，`frogs_eaten()` 按总分钟数每 15 分钟一只；
- 「重置」把这一次任务的计时和这段时间一起清掉，回到 15:00；
- 异常退出（`running_since` 残留）重开时，把那一小段补回 `acc_ms`（最多补一个任务时长）；
- 吃蛙时间线（`frog_events`）同时消费 checkins、`study_banked` 和当前进行中的时长，保证「累计几只」和「吃蛙记录」对得上。
