# 混淆名 → 语义名 映射表

R8 把包名压成 `a0`…`z3`，类名压成 `a`…`z`，字段压成 `f1234a`。
下表是我**逐文件读字节码**反推出的语义映射，按「可信度」分级：

- **A**：证据确凿（SQL 列名、字符串常量、`toString()` 里的字段名、方法签名直接对应）
- **B**：强推断（字段类型 + 使用位置 + 上下文一致）
- **C**：猜测（仅结构相似，命名可能不同）

> 原类名后面括号里的 `f819a` 之类是字段名，可用于对照 `decompiled/` 里的原始代码。

---

## 1. 应用自有包（不是 AndroidX/Kotlin）

| 混淆包 | 语义 | 文件数 | 可信度 |
|---|---|---|---|
| `y2` | **UI 状态 + 主 ViewModel + Activity 入口** | 29 | A |
| `c3` | **应用外壳 / 导航 / 页面胶水** | 27 | A |
| `e3` | **Compose 页面与组件**（54 个类） | 54 | A |
| `d3` | **领域辅助类型 + 图表数据 + 设置 UI** | 19 | B |
| `b3` | **领域模型（MemoryCard / Deck / Rating / …）** | 19 | A |
| `z2` | **数据层（SQLite / 偏好 / CSV / Repository）** | 19 | A |
| `b4` | **Kotlin 标准库 + Compose 扩展被内联的巨型桶**（含调度器） | 74 | A |
| `f3` | **Material3 主题（配色 + 字体 + 形状）** | 2 | A |
| `a4` | 字符串/文本工具（`x1`=trim，`o1`=isBlank，`s1`=replace） | 8 | B |
| `x0` | **Compose 运行时门面 + CSV 导出格式化** | 5 | B |
| `t2` | Compose 运行时 + **协程启动器**（`d.h0`/`d.j`/`d.O0`） | 14 | B |
| `s2` | Kotlin 标准库门面（`k.B`=checkNotNull，`k.A`=checkNotNullExpression） | 12 | A |
| `s3` | Compose UI 扩展（`g.Y`=closeQuietly，`g.X0`=roundToInt，`g.C0`=mutableStateOf） | 95 | B |
| `w1` | **Compose 主题 token**（`k` 里是 colorScheme/typography 的 composition local） | 13 | B |
| `y` | **调色板原始 Long 常量**（`m.java` 是 Material3 baseline 色板） | 22 | A |
| `z2.a` | **`MemoryDbHelper`（SQLiteOpenHelper，800+ 行）** | — | A |
| `z2.i` | **CSV/TXT 导入器** | — | A |
| `z2.g` | **CSV 导出器**（`BufferedWriter` + `x0.c.p0`） | — | A |
| `z2.j` | **主页/计划页数据聚合**（回顾队列 + 14 天预测 + 洞察 + 设置） | — | A |
| `z2.q` | **Repository 门面**（持有 `z2.a` + `z2.s`） | — | A |
| `z2.s` | **`SettingsStore`（SharedPreferences `memory_preferences`）** | — | A |
| `z2.c` | 重置学习进度 / 清理示例 / 删除数据 | — | A |
| `z2.l` | 写复习记录（cards 更新 + reviews 插入） | — | A |

## 2. 领域模型（`b3`）

| 混淆类 | 语义 | 字段 | 可信度 |
|---|---|---|---|
| `b3.k` | **`MemoryCard`** | `id, deckId, deckName, question, answer, tags, createdAt, updatedAt, dueAt, intervalDays, repetitions, easeFactor, lapses, lastReviewedAt, suspended, archived` | **A**（`toString()` 直接给出全部名字） |
| `b3.o` | **`ScheduleResult`** | `dueAt, intervalDays, repetitions, easeFactor, lapses, label` | **A** |
| `b3.n` | **`Rating`** enum | `AGAIN("重来") / HARD("困难") / GOOD("记住") / EASY("轻松")` | **A** |
| `b3.c` | `Deck` | `id, name, colorIndex, createdAt, isExample, cardCount, dueCount, masteredCount` | **A** |
| `b3.i` | **`InsightSnapshot`** | 17 个字段，见 §4 | **A**（`toString()` 全字段） |
| `b3.b` | `DayActivity` | `date, reviewCount, rememberedCount` | A |
| `b3.e` | `ForecastDay` | `date, dueCount` | A |
| `b3.f` | `HourlyPerformance` | `label, reviewCount, rememberedCount` | A |
| `b3.g` | **`ImportCard`**（CSV 一行） | `deckName, question, answer, tags` | **A**（`toString()`） |
| `b3.h` | **`ImportSummary`** | `imported, skipped, createdDecks, message` | **A**（`toString()`） |
| `b3.a` | **`AppSettings`** | `onboardingCompleted, themeMode, dailyNewLimit, hapticsEnabled, showAnswerHint, learningGoal` | **A**（与 `z2.s.a()` 一一对应） |
| `b3.r` | **`ThemeMode`** enum | `SYSTEM("system") / LIGHT("light") / DARK("dark")` | A |
| `b3.l` | `RatingDistribution` | `again, hard, good, easy` | A |
| `b3.q` | `StageDistribution` | `newCards, learning, consolidating, mastered` | A（对应「新卡/学习中/巩固中/已掌握」） |
| `b3.m` | `RetentionDistribution` | `critical, fading, stable, solid` | A（对应 <50/50–69/70–84/≥85） |
| `b3.j` | `IntervalDistribution` | `immediate, short, mid, long` | A（<1天 / 1–7 / 8–29 / ≥30） |
| `b3.d` | **`DeckAnalytics`** | `deckId, name, colorIndex, cardCount, reviewCount, accuracy, averageRetention, masteryRate, dueCount` | **A**（`toString()`） |
| `b3.p` | **`SessionSummary`** | `reviewed, remembered, needsWork, durationMillis, nextDueAt` | **A**（`toString()`） |

## 3. UI 状态（`y2`）

| 混淆类 | 语义 | 关键证据 |
|---|---|---|
| `y2.i` | **`MemoryUiState`**（13 字段不可变 data class） | `toString()` 给出全部字段名：`isLoading/decks/cards/dueCards/forecast/insights/todayReviewed/settings/searchQuery/activeDeckId/reviewSession/snackMessage/errorMessage` | **A** |
| `y2.a0` | **`MainViewModel`**（`extends androidx.lifecycle.a`） | 持有 `z2.q` repository + `MutableStateFlow<MemoryUiState>` | A |
| `y2.b0` | **`ReviewSessionState`** | `queue, index, answerVisible, sessionStartedAt, cardStartedAt, ratings, summary` |
| `y2.a` | 两个 `staticCompositionLocalOf`（主题令牌，被 `y2.e` 等以 `f8141a`/`f8142b` 引用） | `w1.k.f6598p` / `z.y.f8540o` 两个 CompositionLocal key | B |
| `y2.f` | **`LegalDocument`** enum | `PRIVACY("privacy","隐私政策","json/yinsi.html")` / `AGREEMENT` / `FEEDBACK` |
| `y2.c0` | `WebViewClient`（渲染 assets 里的 HTML） | `extends WebViewClient` |
| `y2.h` | `MainActivity` 的根 Composable lambda | 引用 `MainActivity` |
| `y2.e` | 一组 `onOpen*` 回调 lambda | 引用 `d3.e.*` / `e3.a/c/j` |
| `y2.j` … `y2.z` | **每个用户意图一个协程 lambda 类**（R8 把 20+ 个意图全内联成独立类） | 见下表 |

`y2.a0`（MainViewModel）只留下 6 个未被内联的方法：

| 方法 | 语义 | 证据 |
|---|---|---|
| `d()` | 清空 `reviewSession`（`copy` 掩码 7167，只替换第 11 位） | `a0.java:47-54` |
| `e(uri)`（static） | 外部 `content://` 导入 → `new p(uri, …)` | `a0.java:40-45` |
| `f(boolean)` | 重新加载但**保留**会话（掩码 6912） | `a0.java:56-58` |
| `g(String)` | 更新 `searchQuery` + **180ms 防抖**（先 cancel 旧 Job 再起 `new w(...)`） | `a0.java:60-73` |
| `h(Long)` | 选记忆库 + **清空搜索**（掩码 7423） | `a0.java:75-83` |
| `i(AppSettings)` | 保存设置 + 重载（掩码 8063） | `a0.java:85-94` |

其余 20+ 个意图在 `y2` 包里各是一个 `n3.h implements r3.e` 的协程类：

| 混淆类 | 意图 | 落到 `z2.*` |
|---|---|---|
| `y2.j` | 清除示例内容 | `z2.b`（「示例内容已清除，用户内容已保留」） |
| `y2.q` | 重新生成模板 | `z2.k`（「模板内容已加载」） |
| `y2.k` | 清除复习记录 / 重置进度 | `z2.c` |
| `y2.l` | 新建记忆库 | `z2.d`（「记忆库已创建」/「名称已存在」） |
| `y2.u` | 重命名记忆库 | `z2.m` |
| `y2.n` | 删除记忆库 | `z2.f` |
| `y2.m` | 删除卡片 | `z2.e` |
| `y2.v` | 新增/编辑卡片 | `z2.n`（「卡片已更新」/「保存失败」） |
| `y2.y` | 暂停/恢复卡片 | `z2.o` |
| `y2.x` | 构建今日队列 + 初始化会话 | `z2.h`（「当前没有到期卡片，稍后再来看看」） |
| `y2.r` | 记录一次复习 | `z2.l`（「保存复习结果失败」） |
| `y2.s` | 全量重载 | `z2.j`（「数据加载失败」） |
| `y2.t` | 重载但保留会话 | `z2.j` |
| `y2.w` | 搜索防抖 | `z2.d` |
| `y2.z` | 保存设置 | `z2.p` |
| `y2.o` | 导出 CSV | `z2.g`（「已导出 N 张卡片」） |
| `y2.p` | 导入 CSV | `z2.i` |

> `y2.b.java:26/30/33` 里残留的反射字符串 `clearExamples` / `loadTemplates` /
> `revealAnswer`，以及 `s/m1.java:24` 的 `completeOnboarding(I)V`，
> 是原始 Kotlin 方法名的**唯一直接证据**。

## 4. `InsightSnapshot`（`b3.i`）字段全表

| 字段 | 语义 | 计算位置 |
|---|---|---|
| `a` | `totalCards` | `z2.a.g()` |
| `b` | `masteredCards`（reps>=4 && interval>=30） | 同上 |
| `c` | `reviewCount`（近 30 天） | `SELECT COUNT(*) FROM reviews WHERE reviewed_at >= ?` |
| `d` | `rememberedCount`（近 30 天 rating>=2） | 同上 + `AND rating >= 2` |
| `e` | `streakDays` | ViewModel 层另行计算 |
| `f` | `estimatedRetention`（0–100） | `round(avg(Retention.of(card)))` |
| `g` | `activity`：`List<DayActivity>`（28 天） | `z2.a.c(LocalDate.now()-27)` |
| `h` | `ratingDistribution` | `SELECT rating,COUNT(*) … GROUP BY rating` |
| `i` | `stageDistribution` | 遍历卡片按 reps/interval 分桶 |
| `j` | `retentionDistribution` | 按每卡保持率分四档 |
| `k` | `intervalDistribution` | 按 interval 分四档 |
| `l` | `hourlyPerformance` | 按 `strftime('%H')` 分时段 |
| `m` | `deckAnalytics` | 每个记忆库一行 |
| `n` | `averageIntervalDays` | `AVG(interval_days)` |
| `o` | `averageEaseFactor` | `AVG(ease_factor)`，用于「稳定」维度 |
| `p` | `averageReviewSeconds` | `AVG(duration_ms)/1000` |
| `q` | `difficultCards` | lapses DESC, ease ASC 取 8 张 |

## 5. Compose 页面（**被 R8 合并进库大桶**，不在 `e3` 里）

> **这是本次分析最重要的发现。** 直觉上「页面应该在 `e3` 包」，但 R8 的
> class-merging 把整屏 Composable 融合进了 stdlib 桶：`e3` 里只剩**叶子组件**
> （卡片、行、图标、枚举）。真正的页面在 `b4.v` / `t2.d` / `s3.g` / `s2.k` 里，
> 但保留了自己的 `testTag`，成为定位的锚点。
>
> `e3` 里每个 `class X extends s3.h implements r3.f` 是 `@Composable` 的函数体：
> `r3.f`=Function3、`r3.e`=Function2、`r3.a`=Function0、`r3.c`=Function1。

### 5.1 真正的页面（按 `testTag` 定位，可信度 A）

| testTag | 所在文件:行 | 函数签名 | 页面 |
|---|---|---|---|
| `today_screen` | `b4/v.java:5491` | `z(state, onAddCard, onStartReview, onOpenPlan, onOpenSettings, modifier)` | **今日** |
| `plan_screen` | `b4/v.java:4828` | `r(state, onStartReview, onOpenSettings, modifier)` | **计划** |
| `library_screen` | `t2/d.java:1803` | `l(state, onSearch, onAddCard, onAddDeck, onOpenDeck, onEditCard, onDeleteCard, onToggleSuspend, onImport, onExport, modifier)` | **记忆库列表** |
| `review_screen` | `t2/d.java:2878` | `q(session, haptics, showHint, onBack, onReveal, onRate, onFinish, modifier)` | **复习会话** |
| `onboarding_screen` | `s3/g.java:3650` | 多段 onboarding / 引导 | **引导** |
| `settings_screen` | `s3/g.java:3917` | `s(settings, onBack, onUpdate, onImport, onExport, onClearHistory, onClearExamples, onLoadTemplates, onOpenPrivacy, onOpenAgreement, onOpenFeedback, modifier)` | **设置** |
| `deck_detail_screen` | `s2/k.java:1197` | `b(deck, cards, query, 9 callbacks, modifier)` | **记忆库详情** |
| `privacy_consent_screen` | `s2/k.java:1583` | 合规门禁（同意/退出） | **首次启动同意页** |

> 另有 `s3/g.java:3732`、`s3/g.java:4074`、`s2/k.java:1677` 三个 tag，
> 分别对应 onboarding 子步骤、设置子页、同意页变体。

### 5.2 `e3` 的真实角色：叶子组件

| 混淆类 | 语义 | 判定依据 | 可信度 |
|---|---|---|---|
| `e3.g0` | **洞察页**（唯一留在 `e3` 的整屏） | 被 `o.h0`/`o.i` 以 `e3.g0.a/b/d/e/f` 直接调用；含雷达六维 | A |
| `e3.i1` | **今日页内容体**（`today_screen` 的 body） | 在 `b4/v.java:5491` 作为 `new e3.i1(...)` 传入 | A |
| `e3.v0` | **计划页内容体** | 在 `b4/v.java:4828` 作为 `new e3.v0(...)` | A |
| `e3.j0` | 今日卡片列表区 | 「今天已全部完成」「还有 N 张，预计 M 分钟」 | A |
| `e3.x` | 今日页头部（日期 + 问候） | `M月d日 EEEE`、被 `i1` 调用 | B |
| `e3.b` | 通用 UI 字符串/文案桶（跨页复用） | 含「新建记忆库」「搜索」「退出复习」「目前没有明显难卡」 | B |
| `e3.g` | onboarding 条目 + 设置分区标签（15 个变体） | `s3/g.java:3650` 的 `new e3.g(...)` 15 次；含「欢迎使用」「每日节奏」 | A |
| `e3.i0` | 设置页「数据与备份」条目组 | 「批量导入」「导出备份」「加载模板内容」「清除示例内容」 | A |
| `e3.q` | 设置页底部操作面板 | 「从文件导入」「导出完整备份」「清除复习记录」「重置全部进度」 | A |
| `e3.a1` | 关于与支持条目组 | 「隐私政策」「用户协议」「意见反馈」 | A |
| `e3.r` | 记忆库空状态 | 「还没有卡片」「从一个你真正想记住的问题开始。」「添加第一张」 | A |
| `e3.o` | 记忆库详情头卡 | 「N 张卡片」「今日 N 张 · 已掌握 N 张」「开始复习」 | A |
| `e3.h0` | 卡片筛选 enum | 全部/今日/新卡/已掌握（`e3/h0.java:5-11`） | A |
| `e3.g1` | 计划页时间轴 | 「晨间复习」「已完成/待开始」「开始今日复习/继续复习」 | A |
| `e3.r0` | 本周节奏卡 | 「本周节奏」「今日完成」 | A |
| `e3.y` | 洞察双线图 | 「粗线：复习量」「细线：准确率」「轻/中/高」 | A |
| `e3.w` | 统计小卡 | 「张到期」「准确率」「掌握率」「保持率」 | A |
| `e3.c0` | 统计块 | 「次回答」「全部卡片」「平均保持」「平均天数」 | A |
| `e3.b0` | 热力图 + 连续天数 | 「活跃 / 28 天」「连续天数」「30 天准确率」 | A |
| `e3.d0` | 六维指数入口卡 | 「六维健康指数」「智能排序」 | A |
| `e3.s0` | 负荷状态卡 | 「复习负荷」「预测总量」「平稳/很轻松/有明显高峰」 | A |
| `e3.t0` | 负荷指标块 | 「日均负荷」「峰值」「今日待复习」 | A |
| `e3.u0` | 「今日卡片」标题块 | 「今日卡片」 | A |
| `e3.h1` | 「明天 · N 张」条 | 被 `e3.i1` 调用 | B |
| `e3.a0` | 保持率评语卡 | 「预计记忆保持率」「状态很好，继续按当前节奏复习即可」 | A |
| `e3.k0` | 图标/装饰常量 | `r3.c` 回调 | C |
| `e3.l` | 时段枚举 | 图表时间范围 | C |
| `e3.a`/`c`/`d`/`e`/`f`/`i`/`j`/`k`/`m`/`n`/`p`/`v`/`z` | 按钮/对话框/回调的**函数引用常量**（静态字段） | 均为 `b4.v.n(...)`/`a1.n(...)` 的尾参 | A |

### 5.3 导航图（`c3`）

| route | 文件 | 渲染 |
|---|---|---|
| `today` | `c3.j` | `b4.v.z(...)`（today_screen） |
| `library` | `c3.o` | `t2.d.l(...)`（library_screen） |
| `plan` | `c3.p` | `b4.v.r(...)`（plan_screen） |
| `insights` | `c3.q` | `e3.g0.b(...)` |
| `settings` | `c3.r` | `s3.g.s(...)`（settings_screen） |
| `deck/{deckId}` | `c3.w` | `s2.k.b(...)`（deck_detail_screen） |
| `review` | `c3.p`（case 1） | `t2.d.q(...)`（review_screen） |

底部四页签定义在 `c3.d0.java:58-61`：`today`/`library`/`plan`/`insights`。

## 6. 关键函数（`b4.v` 里的内联体）

`b4.v` 有 5,000+ 行，是被内联的 Kotlin 标准库 + Compose 扩展的垃圾场。
真正的应用逻辑混在里面，按方法名找：

| 方法 | 语义 | 行号（`decompiled/b4/v.java`） |
|---|---|---|
| `T0(MemoryCard, Rating, long)` | **调度算法**（核心） | ~1175 |
| `i0(double)` | 间隔 → 中文标签 | ~2400 |
| `e0(MemoryCard, long)` | **单卡保持率**（指数衰减） | ~2450 |
| `E0(...)` | `listOf(...)` | 多处 |
| `X0()` | `throw new IndexOutOfBoundsException` | — |
| `W0()` | `NoWhenBranchMatchedException` | — |
| `n(...)` | `Surface`/`Card` 组合封装 | — |
| `l(...)` | `DropdownMenuItem` 封装 | — |

## 7. 工具方法与 Kotlin 标准库对照

| 混淆 | 真实语义 |
|---|---|
| `s2.k.B(x, msg)` | `requireNotNull` / `checkNotNull` |
| `s2.k.A(x, msg)` | `checkNotNullExpressionValue` |
| `s2.k.p(a,b)` | `Intrinsics.areEqual`（`==`） |
| `s2.k.L0(a,b)` | `SemanticsPropertyReceiver.testTag` / `Modifier.testTag` |
| `s3.g.Y(c, t)` | `closeFinally`（`use {}` 的 finally） |
| `s3.g.X0(d)` | `Math.round(d)` → `roundToInt` |
| `s3.g.C0(v)` | `mutableStateOf(v)` |
| `s3.g.i1(o)` | `COROUTINE_SUSPENDED` 检查 / `ResultKt.throwOnFailure` |
| `x0.c.b0(v,lo,hi)` | `coerceIn` |
| `x0.c.Z(v,lo,hi)` | `coerceIn`（double 版） |
| `x0.c.h0(lambda, …)` | `composableLambda(...)` |
| `x0.c.g0(composer, key, lambda)` | `startRestartGroup` / `remember` 块 |
| `a4.h.x1(s)` | `String.trim()` |
| `a4.h.o1(s)` | `String.isBlank()` |
| `a4.h.s1(s,a,b)` | `String.replace(a,b)` |
| `a4.h.p1(s)` | `String.trimIndent()` / `trim()` |
| `t2.d.L0(s)` | `String.trimIndent()` |
| `t2.d.h0(scope,…)` | `CoroutineScope.launch` |
| `t2.d.O0(dispatcher,…)` | `withContext` |
| `t2.d.j(uri,…)` | `LaunchedEffect(uri)` |
| `i3.o.m1(list)` | `Iterable.average()` |
| `i3.o.z1(list)` | `Iterable.maxOrNull()` |
| `i3.o.A1(list)` | `Iterable.minOrNull()` |
| `i3.o.I1(list)` | `List.toList()` |
| `i3.l.d1(coll)` | `Collection.size` |
| `b4.v.E0(a,b,…)` | `listOf(a,b,…)` |

---

## 8. 怎么用这张表

想找某个功能：

1. 先看本文档的「页面」表定位到 `e3` 的类；
2. 打开 `decompiled/e3/<类>.java`，里面的中文串就是文案；
3. 顺着它调用的 `y2.a0` 方法找到 ViewModel 动作；
4. 再顺着 `z2.*` 找到 SQL；
5. 算法类的东西去 `b4.v` 里搜方法名。

想重建 UI：

- Compose 的 `@Composable` 无法从字节码恢复成源码，但**结构**很清楚：
  `Column/Row/Box/Surface/LazyColumn/…` 的嵌套、每个 `Text(...)` 的文案、
  每个 `Icon(...)` 的 `ImageVector` 都在字节码里。可以照着 `e3` 的类逐个重写。
- 文案 100% 可提取（`strings-zh.txt` 有全部 376 条中文串）。
- 配色 100% 可提取（见 `project/.../ui/AppColors.kt`）。
