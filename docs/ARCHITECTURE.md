# 架构与数据流

## 1. 分层

```
MainActivity (com.luoyu.aibinhaosi)
 └─ b.j.a(activity, content)                 ComposeView 挂进 decorView
    └─ y2.h / c3.d0.a(...)                   根 Composable：主题 + 导航 + 合规门禁
       ├─ f3.a.a(themeMode, content)         Material3 主题（AppColors / 字体 / 形状）
       ├─ 未同意 → s2.k（privacy_consent_screen）
       └─ 已同意 → c3.x（NavHost，7 个 route）
          ├─ "today"        → c3.j → b4.v.z   （today_screen）
          ├─ "library"      → c3.o → t2.d.l   （library_screen）
          ├─ "deck/{id}"    → c3.w → s2.k.b   （deck_detail_screen）
          ├─ "plan"         → c3.p → b4.v.r   （plan_screen）
          ├─ "insights"     → c3.q → e3.g0.b
          ├─ "review"       → c3.p → t2.d.q   （review_screen）
          └─ "settings"     → c3.r → s3.g.s   （settings_screen）

状态：y2.a0 (ViewModel) 持有 MutableStateFlow<y2.i>
       y2.i = MemoryUiState（13 字段，不可变）
数据：z2.q (Repository) → z2.a (SQLiteOpenHelper) + z2.s (SharedPreferences)
       z2.b…z2.p 是 20+ 个「一个意图一个协程类」的写操作
```

**单向数据流**：UI 事件 → `y2.a0` 的 action（或 `y2.j…z` 的协程类）→ `z2.q` →
重新查库 → `MutableStateFlow.update { copy(...) }` → Compose 重组。
没有 LiveData，没有 Paging，没有依赖注入框架（`y2.a0` 自己 `new z2.q(application)`）。

**一个反直觉的逆向点**：整屏 Composable 被 R8 合并进了 `b4.v` / `t2.d` / `s3.g` / `s2.k`
这四个「库大桶」，`e3` 里只剩叶子组件。定位页面靠的是保留下来的 `testTag`。

## 2. 主状态 `y2.i`（`MemoryUiState`）

> 字段名来自 `toString()`（`y2/i.java:128`），**不是猜测**。

| 字段 | 类型 | 含义 |
|---|---|---|
| `f8178a` | `Boolean` | `isLoading`，首次加载完成前为 true |
| `f8179b` | `List<Deck>` | 全部记忆库 + 统计（卡片数/到期数/已掌握数） |
| `f8180c` | `List<MemoryCard>` | 当前筛选下的卡片（搜索 + 记忆库过滤） |
| `f8181d` | `List<MemoryCard>` | 今日到期队列（复习队列） |
| `f8182e` | `List<ForecastDay>` | 今天 + 未来 14 天负荷预测 |
| `f8183f` | `InsightSnapshot` | 洞察页全部数据（17 字段） |
| `f8184g` | `Int` | **`todayReviewed`**：本地零点起已复习次数 |
| `f8185h` | `AppSettings` | 设置快照 |
| `f8186i` | `String` | `searchQuery` 搜索关键词 |
| `f8187j` | `Long?` | `activeDeckId` 当前记忆库（null = 全部） |
| `f8188k` | `ReviewSessionState?` | 复习会话（null = 不在复习中） |
| `f8189l` | `String?` | **`snackMessage`** 一次性提示 |
| `f8190m` | `String?` | **`errorMessage`** 错误提示 |

`ReviewSessionState`（`y2.b0`）：

| 字段 | 含义 |
|---|---|
| `queue: List<MemoryCard>` | 本轮待复习队列（快照） |
| `index: Int` | 当前第几张 |
| `revealed: Boolean` | 是否已翻面 |
| `startedAt: Long` | 本轮开始时间（算总用时） |
| `shownAt: Long` | 当前卡展示时间（算单卡用时 → `reviews.duration_ms`） |
| `ratings: List<Rating>` | 本轮已打的评级（算 SessionSummary） |
| `current: MemoryCard?` | 当前卡 |

## 3. 页面结构

> **重要**：R8 的 class-merging 把整屏 Composable 融合进了 stdlib 大桶，
> 所以页面**不在 `e3`**。每个页面都保留了自己的 `testTag`，用它可以精确定位。
> `e3` 里只剩叶子组件（卡片、行、图标、枚举）。

| testTag | 位置 | 页面 |
|---|---|---|
| `today_screen` | `b4/v.java:5491` | 今日（body 是 `e3.i1`） |
| `plan_screen` | `b4/v.java:4828` | 计划（body 是 `e3.v0`） |
| `library_screen` | `t2/d.java:1803` | 记忆库列表（body `t2.m0`） |
| `review_screen` | `t2/d.java:2878` | 复习会话 |
| `deck_detail_screen` | `s2/k.java:1197` | 记忆库详情 |
| `settings_screen` | `s3/g.java:3917` | 设置 |
| `onboarding_screen` | `s3/g.java:3650` | 引导 |
| `privacy_consent_screen` | `s2/k.java:1583` | 首次启动同意页 |

### 今日（`today_screen`）
- 头部（`e3.x`）：问候语（`e3.h0` 时段枚举）+ 日期 `M月d日 EEEE`
- 内容体（`e3.i1`）：今日卡片列表（`e3.u0` 标题块）、
  「明天 · N 张」（`e3.h1`）、负荷预测（`e3.s0`/`e3.t0`）、
  保持率评语（`e3.a0`）
- 主按钮：「开始今日复习」
- 全部完成时：「今天已全部完成 / 记忆正在巩固中，明天会在合适的时间再次出现。」
- 右上角设置入口（testTag `open_settings`）

### 记忆库（`library_screen`）
- 顶部搜索（`d3.i`，带防抖）
- 记忆库行（`d3.r.b/e`）：名称、卡片数、到期数、已掌握数、颜色条
- 空状态（`e3.r`）：「这里还没有记忆库」/「新建记忆库」
- 记忆库详情（`deck_detail_screen`）：头卡（`e3.o`）、
  筛选 chips（`e3.h0`：全部/今日/新卡/已掌握）、卡片列表
- 记忆库操作面板（`c3.b0`）：新建/重命名/删除/设为示例
- 卡片编辑器（`d3.g` sheet + `d3.h` 记忆库选择器）

### 计划（`plan_screen`）
- 时间轴（`e3.g1`）：「晨间复习」「已完成/待开始」
- 本周节奏（`e3.r0`）
- 负荷预测：`e3.s0`（复习负荷 / 预测总量）、`e3.t0`（日均负荷 / 峰值 / 今日待复习）
- 「每日新卡上限」滑块（5–100，默认 20）
- 「学习目标」三选一：每天保持 10 分钟 / 15 分钟 / 每天完成到期内容

### 洞察（`e3.g0`）
- 「六维健康指数」雷达（`e3.d0` 入口 + `e3.g0` 主体）
- 「28 天活跃趋势」热力图（`e3.b0`）+「30 天准确率」
- 「回答质量分布」（重来/困难/记住/轻松）
- 「学习阶段结构」（新卡/学习中/巩固中/已掌握）
- 「记忆风险分层」（临界 <50% / 渐淡 50–69% / 稳定 70–84% / 牢固 ≥85%）
- 「复习间隔结构」（即时 <1天 / 短期 1–7 / 中期 8–29 / 长期 ≥30）
- 「时段表现分析」（`e3.y` 双线图：粗线复习量、细线准确率；`e3.s0` 给评价）
- 「记忆库对比」（`b3.d` DeckAnalytics 表）
- 难卡列表（`lapses` 最高 8 张）或「目前没有明显难卡」
- 底部免责声明：「全部分析由本机复习记录计算……不代表医学测量结果。」

### 复习会话（`review_screen`）
- 签名：`q(session, hapticsEnabled, showAnswerHint, onBack, onReveal, onRate, onFinish, modifier)`
- 正面：问题 + 「先在心里完整回答，再查看答案」
- 翻面后：答案 + 四个评级（重来/困难/记住/轻松，来自 `b3.n`）
- 评级 → `b4.v.T0()` 调度 → `z2.l` 写库 → 下一张
- 计时：`now - cardStartedAt` 记进 `reviews.duration_ms`
- 结束：`b3.p` SessionSummary `(reviewed, remembered, needsWork, durationMillis, nextDueAt)`

### 设置（`settings_screen`）
- 每日节奏（`e3.g` 分区）：每日新卡上限、学习目标
- 显示与反馈：主题（system/light/dark）、触感反馈、显示答案提示
- 示例与模板：加载模板内容、清除示例内容（`e3.i0`）
- 数据与备份：批量导入、导出备份、清除复习记录、重置全部进度（`e3.q`）
- 关于与支持：用户协议、隐私政策、意见反馈（`e3.a1`）

### 合规门禁（`privacy_consent_screen`）
- 「在开始建立长期记忆前，请阅读并理解用户协议与隐私政策。」
- 「同意并继续」/「不同意并退出」
- 同意后写 `privacy_consent.accepted_policy_version`

## 4. 关键流程

### 首次启动
```
MainActivity.onCreate
  → 读 privacy_consent.accepted_policy_version
  → 与 "yingwenzitie-2026-08-06-v2" 比较
  → 不等 / 为空 → c3.d0.a 渲染 e3.g（合规门禁）
      ├─ 同意 → 写 version + accepted_at → 状态置 true → 进主界面
      └─ 不同意 → finishAffinity()
```

### 复习一张卡
```
点击评级
 → y2.a0 记录 duration = now - shownAt
 → b4.v.T0(card, rating, now) 算 ScheduleResult
 → z2.l: UPDATE cards + INSERT reviews（同一事务）
 → 队列 index+1；队列空 → 生成 SessionSummary → 回今日页
```

### 外部导入（`content://`）
```
MainActivity.j(intent) 解析 ACTION_VIEW / ACTION_SEND 的 Uri
 → y2.h 的 LaunchedEffect(uri) 触发
 → z2.i 读流 → 解析 CSV → 事务内建库+插卡
 → ImportSummary(imported, skipped, createdDecks, "已导入 N 张卡片")
```

### 数据刷新
`y2.a0.d()` 一次性并发拉：decks / cards / dueCards / forecast / insights / settings，
然后一次 `state.update {}` 落地，避免多次重组。

## 5. 值得注意的工程选择

1. **不用 Room**：手写 SQLite 让 SQL 完全可控（尤其是那些 `SUM(CASE WHEN ...)` 统计），
   代价是 800 行 helper 和手写 cursor 映射。
2. **不用 Hilt/Koin**：`y2.a0` 直接 `new z2.q(application)`，依赖关系简单到不需要 DI。
3. **不用 Navigation-Compose 的 safe-args**：route 就是 4 个字符串常量，
   底部导航状态用 `rememberSaveable` 存。
4. **统计全部实时算**：没有预聚合表，每次进洞察页都全表扫描 `cards` + `reviews`。
   卡片量小（个人使用，几百到几千张）时完全够用。
5. **示例数据是「活的」**：`is_example` 标记让「清除示例」能精确删除，
   不会误伤用户内容；`loadTemplates()` 可重复生成而不覆盖用户数据。
