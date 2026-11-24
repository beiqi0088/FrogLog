# 征途 · 设计稿（v3）

> 「打卡」改名为「征途」，并把 Habitica 的玩法融合进来。
> 单文件、零依赖：双击 `index.html` 就能看。

## 看什么

| 方式 | 说明 |
|---|---|
| 直接双击 | `index.html`，7 屏并排 |
| 单屏 | `?only=journey` / `quests` / `party` / `rewards` / `settle` / `levelup` / `study` |
| 任务卡三态 | `?only=journey&quest=active` / `&quest=paused` / `&quest=done`（默认未领取） |
| 学习页胶囊 | `?only=study&pill=paused` / `pill=idle` / `pill=done`（默认计时中） |
| 深色 | `?only=journey&theme=dark` |
| 高清 | `?only=journey&scale=2`，配 780×1900 窗口截 780×1688 |

已出图：`_shots/overview.png`（6 屏）、单屏 6 张、`journey-active.png`、`journey-done.png`、
`study-paused.png`、`study-idle.png`、`journey-dark.png`。

```
python capture.py          # 全部重出
python capture.py quests   # 只出一屏
```

> `capture.py` 走 `D:/re-tools/...` 这个 ASCII 联接取文件——Edge 命令行遇到中文路径会打不开。

## 七屏对应什么

| 屏 | 内容 | 对应旧界面 |
|---|---|---|
| 01 征途 · 总览 | 任务卡（开关 + 固定 15 分钟 + 重置，三态）、「吃掉那只青蛙」卡、青蛙勋章条、最近 7 天（角色卡已移除） | 「打卡」页 |
| 02 征途 · 数据 | 最近 7 天柱状图 + 31 天活跃热力图 + 准确率环；吃蛙时间线在「吃掉那只青蛙」右上角打开的独立页（每只青蛙一条，按天分组；空态只有一行提示） | 原「任务」页 |
| 03 征途 · 副本 | 队伍共斗 Boss、伤害榜、通关奖励 | 原「小怪」升级 |
| 04 征途 · 奖励 | 金币商店（自建奖励）、徽章墙、金币来源 | 原「勋章」升级 |
| 05 每日结算 | 24:00 自动结算：完成/漏做/连击/金币 | 无（新增） |
| 06 升级 | 生命上限/回满/属性点/解锁新副本 | 无（新增） |
| 07 学习页 · 顶栏计时 | 顶栏中间的倒计时胶囊：计时中=绿、暂停=灰、未领任务=整块留白 | 复习页顶栏空位 |

征途的 4 个子页共用同一条分段导航（总览 / 任务 / 副本 / 奖励），**不新增底部 tab**；
分段控件由 `segTabs()` 生成，落在页面标题与内容之间。

> 七屏已全部在 `app/` 里实现：`pages/journey_panels.py`（总览/任务/副本/奖励）、
> `pages/journey_dialogs.py`（结算/升级）、`pages/review.py::QuestPill`（学习页顶栏计时）。
> 真实界面截图见 `app/shots/70~77-journey-*.png`。

## 怎么改

- **配色**：`:root` 里 12 个变量；深色在 `html[data-theme="dark"]`。
  取值来自 APK 逆向（纸白 `#FBF8F1`、墨绿 `#2F6A43`、赭石 `#BF5B38`），与 `app/theme.py` 的 `LIGHT` 一致。
- **内容**：改 JS 里的 `D` 对象（`me` / `days` / `boss` / `habits` / `dailies` / `todos` / `party` / `rewards` / `badges`）。
- **结构**：每个屏一个函数（`screenJourney` 等），`SCREENS` 决定 `?only=` 的取值；
  总览的正文抽在 `journeyBody()`，升级弹层复用它做背景。
- **Boss 插画**：`bossSVG()`，与 `app/pages/plan.py` 里 `Monster.paintEvent` 的 QPainter 画法同构（圆身 + 犄角 + 眼睛），落地时可直接搬。

## 与真实 App 的关系

这是**设计稿**，不是可运行代码。落地步骤、数据模型、数值公式见
[`../../docs/JOURNEY-PLAN.md`](../../docs/JOURNEY-PLAN.md)。
