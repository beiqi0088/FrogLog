# 调度算法与 Anki 26.08 的逐条对照（含两轮修复）

> 对照对象：`D:\我的下载\WorkBuddy库\闪卡制作\浮卡 FloCard\anki-26.08.1\rslib\src\scheduler\`
> 我们这边：`app/fsrs.py`（评分状态机）、`app/core.py`（队列 / 限额 / 存储）、`app/pages/review.py`（会话与重学卡回队列）
> 结论：**学习步骤、四档评分、限额、fuzz、Load Balancer、复习/新卡交错、多步撤销都已对齐**；
> 剩下的差异是「需要 notes/easy-days 元数据」和「RNG 实现不同」两类，不影响算法结构。

---

## 1. 你问的那个场景：重来（1 分钟）后会不会再出现？

**修复前：不会。** 会话队列在开始复习时一次性建好，点「重来」只把卡片写成 `state=learning, due=now+1min`，
队列里没有第二条 → 本场再也不会出现。

**修复后：会。** 与 Anki 的 `CardQueues.intraday_learning` 对齐：

1. 评分后若进入 `learning` / `relearning` 且 `due` 在 20 分钟内 → 按 due 插回队列（`app._requeue_learning`）；
2. 到点前不提前弹：显示「N 秒后继续」，到点自动渲染回来（`review._render_wait_body`）；
3. 队列里若有**已经到点**的学习卡，会把它提到当前位（`review._prefer_due_learning`）；
4. 撤销时把那一条重复的队列项收回；
5. 暂停/搁置时清掉该卡的所有队列副本。

实测：`_scratch/test_steps.py` 13 项全 PASS。

---

## 2. 逐条对照（Anki 26.08 源码 → 我们）

| 规则 | Anki 26.08（源码依据） | 我们 | 状态 |
|---|---|---|---|
| 学习步骤默认 | `learn=[1,10]`、`relearn=[10]`（`deckconfig/mod.rs`） | 同 | ✅ |
| 学习卡 Again / Hard / Good / Easy | 回第 1 步 1m / 第一步 5.5m、其余步不变 / 前进一步、末步毕业 1 天 / 直接毕业 4 天（`states/learning.rs`、`steps.rs`） | 同 | ✅ |
| 复习卡 Again | lapses+1、进 relearning 10m、ease −0.2（`states/review.rs`） | lapses+1、relearning 10m（不用 ease，见 §4） | ✅ |
| 复习卡 Hard/Good/Easy | FSRS 开启时用 FSRS 间隔（`passing_fsrs_review_intervals`） | FSRS 间隔 | ✅ |
| 重学毕业间隔 | FSRS：用新算的 good 间隔（`states/relearning.rs`） | 已从"写死 1 天"改为 FSRS 间隔 | ✅ 已修 |
| 学习步骤 fuzz | 最多 +25%、不超过 +300s（`answering/learning.rs`） | 已实现，同一 seed | ✅ 新增 |
| 间隔取整 | Rust `round()`（.5 向上） | `_round()` | ✅ 已修 |
| 间隔上下限 | 最小 1 天、上限 36500 天 | 同 | ✅ |
| 复习 fuzz | 确定性种子 `card.id + reps`；2.5–7 ±15%、7–20 ±10%、20+ ±5%（`states/fuzz.rs`） | 同 | ✅ 已修 |
| **Load Balancer** | 默认开；≤90 天时在 fuzz 区间内按 `(1/当日到期数)^2.15 × (1/间隔)^3` 加权选日；负载按**预设**聚合（`states/load_balancer.rs`） | **已实现**：`due_counts()` 按「同一套卡组选项」聚合 + 同款权重 + 确定性采样 | ✅ 新增 |
| **Easy Days（轻松日）** | 7 天各配 正常/减少/最少；LB 权重按 `calculate_easy_days_modifiers`（最少=0.0001，减少=0.5 或按负载转最少）（`load_balancer.rs`） | **已实现**：卡组选项 7 个下拉 + `_easy_days_weights()` 同款算法 | ✅ 新增 |
| 按钮预览 | 与实评共用 next states（含 fuzz/LB），显示=落库 | 同（`preview` 用同一 cfg） | ✅ 已修 |
| 提前学习 | 默认 1200s；主队列空后才提前取（`config/mod.rs`） | 20 分钟窗口，进队时统计，学习卡排在两头 | ✅ |
| **复习/新卡交错** | `Intersperser`：`ratio=(n1+1)/(n2+1)`，按比例均匀穿插（`queue/builder/intersperser.rs`） | **已实现** `_intersperse()` | ✅ 新增 |
| Leech | `lapses>=8 && (lapses-8)%4==0`（`states/review.rs:leech_threshold_met`） | 同 | ✅ 已修 |
| 每日限额 | 新卡吃复习额度；持久计数在评分时累加（`decks/limits.rs`、`answering/mod.rs`） | 卡包内持久计数 + 额度联动 | ✅ 已修 |
| 学习卡与限额 | intraday learning 不占限额 | 同 | ✅ |
| 笔记 / 兄弟卡 | 卡属于 note，同 note 可有多张卡（`card.note_id`） | 每张卡都有 `note_id`；编辑器右上「兄弟卡」可复制出同笔记的卡；老数据自动迁移（note_id=card.id） | ✅ 新增 |
| 自动 bury 兄弟 | `bury_new` / `bury_reviews` 默认 false（`deckconfig/mod.rs`） | 卡组选项两个开关（默认关），开启后作答即 bury 兄弟，并从当前会话队列移除 | ✅ 新增 |
| LB 的兄弟修饰 | 兄弟到期日 ±5 天按 `[1, .8, .6, .4, .2, 1e-6, .2, .4, .6, .8, 1]` 衰减（`load_balancer.rs`） | 已实现：`sched_cfg` 带 `sibling_days`，权重按同款系数衰减 | ✅ 新增 |
| 手动 bury / suspend | 只改队列，不改 due；日切解封 | 写 `buried_until` / `suspended` | ✅（等价） |
| **撤销** | 多层 undo | 快照栈，实测可连续回退 3 步（`test_undo.py`） | ✅ |
| 队列顺序 | 到点学习 → 复习/新卡交错 → 提前学习 | 同 | ✅ |

四档评分按钮、快捷键 1–4、预览、暂停/搁置/编辑/撤销菜单、leech 打标签都在。

---

## 3. 两轮修复清单（文件级）

| 文件 | 改动 |
|---|---|
| `app/app.py` | 学习/重学卡按 due 回队列；撤销收回重复项；按作答前状态累加每日计数；`start_review` 卡组参与限额 |
| `app/pages/review.py` | 到点学习卡优先、未到点显示倒计时、计数去重、暂停/搁置清副本；预览改用 `sched_cfg` |
| `app/fsrs.py` | 去重；`_round`；确定性 fuzz；**学习卡 +25% fuzz**；**Load Balancer 加权选日**；重学毕业用 FSRS 间隔；leech 打点；预览=实评 |
| `app/core.py` | 持久每日计数（含迁移）；新卡占复习额度；队列顺序；`due_counts` / `sched_cfg`；`_intersperse` 交错；**`note_id` + `siblings` / `add_sibling` / `bury_siblings` / `sibling_days`** |
| `app/pages/card_edit.py` | 顶栏新增「兄弟卡」（复制成同笔记的卡） |
| `app/pages/sched.py` | 卡组选项新增两个 bury 开关 + 轻松日 7 个下拉（正常/减少/最少） |

---

## 4. 仍然不同（都有理由，不影响算法结构）

1. **RNG 实现**：Anki 用 `StdRng`（ChaCha12），我们用 `random.Random`。种子相同、分布相同，
   但**同一天抽到的具体天数不一定和 Anki 逐位相同**；统计行为一致。
2. **ease 字段**：我们用 FSRS 的 stability/difficulty 算间隔，`ease` 只是历史字段；
   Anki 在 FSRS 模式下同样不用 ease 算间隔。
3. **学习卡跨天转 DayLearn**：Anki 会把跨天的学习延迟转成日期队列（`maybe_as_days`）；
   我们的学习步骤最多 10 分钟，实际不会跨天，未实现。
4. **到期日计算**：Anki 用 `interval - (due - today)` 算已过天数，我们用 `last_review` 到现在的实际天数。
   晚点复习时两者略有差别（我们的更贴近真实间隔）。

---

## 5. 验证脚本

| 脚本 | 覆盖 | 结果 |
|---|---|---|
| `_scratch/test_scheduler.py` | 四按钮 × 新卡/学习/复习/重学、leech、fuzz 确定性、预览=实评 | 21 项 ALL PASS |
| `_scratch/test_lb.py` | 学习卡 fuzz 区间、Load Balancer 避开高峰日、>90 天不启用、交错比例 | 11 项 ALL PASS |
| `_scratch/test_steps.py` | 重来→回队列、等待页、到点复现、第二步、撤销 | 13 项 ALL PASS |
| `_scratch/test_undo.py` | 连续撤销 3 步、状态回滚、无操作提示 | 9 项 ALL PASS |
| `_scratch/test_siblings.py` | 兄弟卡创建、bury 开关（默认关 / 开启后生效）、LB 避开兄弟日 | 12 项 ALL PASS |
| `_scratch/test_note_migrate.py` | 老数据 143 张卡全部补上 note_id | PASS |
| `_scratch/test_easy_days.py` | 全正常不变、避开「最少」日、「减少」+尖峰、全最少仍可排 | 8 项 ALL PASS |
| `_scratch/shot_easy_ui.py` | 卡组选项 7 个下拉保存/读回 | 7 项 ALL PASS |
| `_scratch/test_preset_scope.py` | 共用配置的卡包合并算负载、改配置后分开 | 6 项 ALL PASS |
| `_scratch/test_group_queue.py` | 卡组限额顺序、额度提示 | 7 项 ALL PASS |
| `_scratch/test_real_group.py` | 真实数据副本点四个卡组 | 4 组均可进复习 |
| `_scratch/test_quest.py` / `_scratch/shot_journey.py` | 征途计时与数值 | ALL PASS |
| `app/smoke.py` | 开窗自检 | SMOKE OK |
