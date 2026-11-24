# 艾宾浩斯记忆曲线 1.0.2 — 逆向分析报告

| 项 | 值 |
|---|---|
| APK 文件 | `艾宾浩斯记忆曲线 1.0.2.apk` |
| SHA-256 | `171726F47AF35E1EC5C159E37E4A2A47DE3FFEE2EE83DD504B207C1F98F68C48` |
| 大小 | 2,100,855 字节（解压后 3,276,187） |
| 包名 | `com.luoyu.aibinhaosi` |
| versionName / Code | `1.0.2` / `3` |
| minSdk / targetSdk / compileSdk | 26 / 35 / 35 |
| 构建链 | Gradle 8.0 · Kotlin 1.8.22 · JDK 17 · Compose Compiler 1.4.8 |
| DEX | 单 `classes.dex`，1,739 个类，10,419 个字符串 |
| 代码混淆 | R8 全量混淆（包名压成 `a0`…`z3`，字段名压成 `f819a` 之类） |
| 第三方 SDK | **无**（只有 AndroidX + Kotlin + Compose） |
| 网络 | **无 INTERNET 权限**，DEX 中无任何 `java.net`/OkHttp/统计 SDK 引用 |

---

## 1. 一句话结论

**源码可以还原，但无法「一字不差」地还原成原始 Kotlin 工程。** 这个 APP 只有
一个 2.2 MB 的 DEX，被 R8 全量混淆：包名、类名、字段名、局部变量全是 `a`/`b`/`f819a`
这样的符号，Kotlin 的内联、`inline`、扩展函数、Compose 编译器生成的状态读取也都被打平。

- **逻辑层可 100% 还原**：算法、SQL、状态机、CSV 规则、公式都能从字节码精确读出来，
  并且已经用等价的 Python oracle + 测试向量交叉验证（见 §5）。
- **命名层只能靠推断**：`b3.k` 实际是 `MemoryCard`，`b4.v.T0` 实际是 `schedule()`，
  这类映射是我根据字段顺序、方法签名、SQL 列名、中文文案反推的。
- **UI 层是「结构性还原」**：Compose 的 `@Composable` 在字节码里变成
  `static void a(state, modifier, Composer, int)` 这样的巨型函数，jadx 输出的是
  带 `xVar.Z()`/`xVar.r()` 的槽位操作代码，**不能直接编译**，只能读懂结构后用 Compose 重写。
- **页面位置反直觉**：R8 的 class-merging 把整屏 Composable 合并进了
  `b4.v` / `t2.d` / `s3.g` / `s2.k` 四个「库大桶」，`e3` 里只剩叶子组件。
  定位靠的是残留的 `testTag`（`today_screen`、`settings_screen` 等），
  详见 [`DECOMPILE-MAP.md`](DECOMPILE-MAP.md) §5。

因此我交付的不是「假装能编译的反编译产物」，而是三类东西：

1. `decompiled/` —— jadx 原始反编译结果（2,742 个 Java 文件，供逐行比对）；
2. `project/` —— 可重新编译的 Gradle 工程骨架（清单 + 176 个资源文件 + 依赖声明）；
3. `project/.../recovered/` —— **我按原始字节码逐行重写、可编译、带注释的可读 Kotlin**
   （调度算法、数据库、CSV、设置、调色板、洞察公式）。

---

## 2. 还原产物清单

```
ebbinghaus/
├─ README.md                    ← 总索引（先看这个）
├─ docs/
│  ├─ REVERSE-ENGINEERING.md   ← 本文件
│  ├─ DECOMPILE-MAP.md         ← 混淆名 → 语义名映射表（核心成果）
│  ├─ SCHEDULER.md             ← 调度算法逐分支说明 + 验证
│  └─ ARCHITECTURE.md          ← 架构、数据流、页面结构
├─ decompiled/                 ← jadx 全量输出（2,742 个 .java，未经修改）
├─ apktool/                    ← apktool 还原结果（AndroidManifest.xml、res/、assets/）
├─ project/                    ← 可编译工程骨架
│  ├─ settings.gradle.kts / app/build.gradle.kts / gradle.properties
│  ├─ _compilecheck/           ← 编译验证：Android 桩 + Verify.kt + VERIFICATION.md
│  └─ app/src/main/
│     ├─ AndroidManifest.xml   ← 已还原（可直接用）
│     ├─ res/                  ← 176 个文件，91 个 values 语言目录
│     ├─ assets/json/          ← 用户协议 / 隐私政策 / 意见反馈 HTML
│     └─ java/com/luoyu/aibinhaosi/recovered/
│        ├─ scheduler/EbbinghausScheduler.kt
│        ├─ data/MemoryDbHelper.kt · SettingsStore.kt
│        ├─ analytics/Retention.kt
│        ├─ io/CsvCardCodec.kt
│        └─ ui/AppColors.kt
├─ strings-all.txt / strings-zh.txt      ← DEX 字符串池（全部 / 仅中文）
├─ scheduler-vectors.txt                  ← 16 组调度测试向量
└─ validation.txt                         ← CSV + 调度不变量扫描结果
```

---

## 3. APP 到底是个什么东西

一个**完全离线**的间隔重复（SRS）背记工具，界面全中文，四个底部页签：

| 页签 | route | 内容 |
|---|---|---|
| 今日 | `today` | 今日到期队列、开始复习、完成度 |
| 记忆库 | `library` | 记忆库列表 → 卡片列表 → 卡片编辑 |
| 计划 | `plan` | 未来 14 天负荷、每日新卡上限、学习目标 |
| 洞察 | `insights` | 六维雷达、保持率、热力图、时段表现、难卡 |

外加：复习会话页、批量导入/导出、设置、用户协议/隐私政策/意见反馈（本地 HTML）。

**技术选型很有意思**：没有用 Room，而是手写 `SQLiteOpenHelper` + `ContentValues`
+ 原生 `Cursor`（`z2.a`，800 多行）；状态用 `MutableStateFlow` + 不可变 data class
（`y2.i`，13 个字段）；UI 全 Compose + Material3，没有 XML 布局文件。

---

## 4. 数据层还原

数据库 `memory_curve.db`（v2，WAL，外键级联）：

```sql
CREATE TABLE decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    color_index INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    is_example INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    due_at INTEGER NOT NULL,
    interval_days REAL NOT NULL DEFAULT 0,
    repetitions INTEGER NOT NULL DEFAULT 0,
    ease_factor REAL NOT NULL DEFAULT 2.35,
    lapses INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at INTEGER,
    suspended INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
);
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    reviewed_at INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    previous_interval REAL NOT NULL,
    next_interval REAL NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
);
CREATE INDEX idx_cards_due ON cards(due_at, suspended, archived);
CREATE INDEX idx_cards_deck ON cards(deck_id);
CREATE INDEX idx_reviews_time ON reviews(reviewed_at);
```

几个**只在逆向里才能发现的业务定义**：

- 「已掌握」= `repetitions >= 4 AND interval_days >= 30`（不是 SM-2 原版的 `reps>=8`）。
- 「到期」= `due_at <= now AND suspended = 0 AND archived = 0`。
- 卡片软删除用 `archived`，暂停用 `suspended`，都有索引覆盖。
- 迁移 v1→v2 只加了一个 `is_example` 列，并用**中文记忆库名**回填示例数据
  （`生物 · 细胞结构` / `英语 · 雅思核心词` / `历史 · 世界近代史` / `计算机 · 数据结构`）。

---

## 5. 调度算法（本报告最硬的部分）

入口 `b4.v.T0(MemoryCard, Rating, long)`。这是 **SM-2 的简化变体**，不是标准 SM-2：

```
难度因子 ease ∈ [1.3, 3.2]，初值 2.35
固定阶梯 [1, 3, 7, 15, 30, 60] 天

AGAIN(重来)  interval = 1 分钟, repetitions = 0, lapses+1, ease -= 0.2
HARD (困难)  interval = max(1, prev*1.2)（新卡固定 1 天）, reps=max(1,reps), ease -= 0.15
GOOD (记住)  interval = 阶梯[reps]（reps<6）否则 prev*ease, reps+1, ease 不变
EASY (轻松)  interval = 3（新卡）| 阶梯[reps]*1.35（reps<6）| max(3,(ease+0.3)*prev）, reps+1, ease += 0.15

最终 dueAt = max(now + 60s, now + interval 天)
```

`project/.../recovered/scheduler/EbbinghausScheduler.kt` 是逐行重写版。
为了证明等价，我把原 Java **逐语句镜像**成 Python oracle（`scripts/scheduler_oracle.py`），
生成 16 组边界向量（`scheduler-vectors.txt`），覆盖：

- 新卡的四种评级；
- 阶梯第 1→6 次与第 7 次的切换点；
- `ease` 撞上下限 1.3（连续重来）和上限 3.2（连续轻松）；
- 非法输入（`interval<0`、`ease<=0`）的兜底；
- 标签分档边界（`<1 小时` / `<1 天` / `30 天→「1 个月」` / `>365 天→年`）。

关键边界值（`now = 1700000000000`）：

| 输入 (interval, reps, ease, lapses, rating) | intervalDays | reps | ease | lapses | label |
|---|---|---|---|---|---|
| (0, 0, 2.35, 0, AGAIN) | 0.0007 | 0 | 2.15 | 1 | 1 分钟 |
| (0, 0, 2.35, 0, GOOD) | 1.0 | 1 | 2.35 | 0 | 1 天 |
| (1, 1, 2.35, 0, GOOD) | 3.0 | 2 | 2.35 | 0 | 3 天 |
| (15, 4, 2.35, 0, GOOD) | 30.0 | 5 | 2.35 | 0 | **1 个月** |
| (60, 6, 2.35, 0, GOOD) | 141.0 | 7 | 2.35 | 0 | 4.7 个月 |
| (3, 2, 2.0, 0, HARD) | 3.6 | 2 | 1.85 | 0 | 4 天 |
| (5, 9, 1.5, 3, AGAIN) | 0.0007 | 0 | **1.30** | 4 | 1 分钟 |
| (100, 12, 3.2, 4, EASY) | 350.0 | 13 | **3.20** | 4 | 11.7 个月 |

> 注意第 4 行：`intervalDays = 30` 但标签显示「1 个月」，因为原 `i0()` 在
> `30 <= d < 365` 且 `d/30 < 2` 时**固定返回「1 个月」**。这种细节只有逐行读才拿得到。

### 保持率公式

`b4.v.e0(card, now)` 用的是**指数衰减，半衰期 = 当前间隔**：

```
R(t) = exp( -ln2 * t / max(interval, 1) )      t = 距上次复习的天数
```

- 未复习过：新卡 `0.35`，有学习记录 `0.75`；
- 这个公式就是「艾宾浩斯曲线：1 天后剩 ~50%」的代码化（`interval=1` 时 `R(1)=0.5`）。

### 六维健康指数

`e3.g0.b(...)` 第 97 行，六个维度的真实公式：

| 维度 | 公式 |
|---|---|
| 保持 | `avg(单卡保持率) * 100` |
| 准确 | `remembered / reviews * 100`（rating>=2 记为记得） |
| 掌握 | `masteredCards / totalCards * 100` |
| 坚持 | `clamp(streakDays*5 + active28*3, 0, 100)` |
| 均衡 | `clamp(100 - (max-min)/mean*10, 0, 100)`，按日负荷分布 |
| 稳定 | `clamp((avgEase - 1.3)/1.7*100, 0, 100)` |

---

## 6. 导入/导出格式（可直接对接）

**导出**（`x0.c.p0`）：

```
deck,question,answer,tags
"英语 · 雅思核心词","ubiquitous 的准确含义？","无处不在的……","英语,词汇"
```

- UTF-8 **带 BOM**，`\n` 换行；
- 字段含 `,` `"` `\n` `\r` 才加引号，内部 `"` → `""`；
- 文件名 `艾宾浩斯记忆曲线-yyyyMMdd.csv`。

**导入**（`z2.i`）：

- 去 BOM，**按首行**在 `tab` / `;` / `,` 中选出现次数最多的作分隔符（平票选 `,`）；
- 首行含 `question/front/问题/正面` 等关键字 → 视为表头，按别名映射列；
- 否则按位置 `deck, question, answer, tags`；
- 表头别名：`deck|deckname|记忆库|卡组`、`question|front|问题|正面`、
  `answer|back|答案|背面`、`tags|tag|标签`；
- 问题或答案为空 → 跳过；记忆库为空 → 落到 `导入卡片`；
- 记忆库不存在则**自动创建**，`color_index = 已有库数 % 4`。

---

## 7. 隐私与安全审计结果

APP 自己在隐私页写「卡片、复习记录与偏好仅保存在本机。应用不含账号、广告或数据追踪。」
**字节码层面完全支持这个声明**：

| 检查项 | 结果 |
|---|---|
| `AndroidManifest.xml` 权限 | 只有一条 signature 级自定义权限 + `DUMP`（AndroidX profileinstaller 用），**无 INTERNET** |
| `java.net` / OkHttp / Retrofit / Volley | 0 处引用 |
| Firebase / Crashlytics / 友盟 / AppsFlyer / AdMob / Sentry | 0 处引用 |
| `com.*` 第三方包 | 只有 `com.luoyu.aibinhaosi` 自己 |
| 硬编码密钥/Token | 未发现（DEX 中 `token`/`secret` 仅作为通用词出现） |
| 数据落盘 | `memory_curve.db` + `memory_preferences` + `privacy_consent`，均私有目录 |
| 备份 | `allowBackup=true`，且提供 `backup_rules` / `data_extraction_rules` |
| 合规门禁 | 首次启动强制阅读《用户协议》《隐私政策》，同意前不进主界面 |

唯一值得提的：`allowBackup="true"` 意味着 **adb backup / 云备份可能带走学习数据**，
如果这是你的 APP 且在意隐私，建议改成 `false` 或收紧 `data_extraction_rules`。

---

## 8. 还原的完整度与已知损失

### 8.0 验证：这些代码是真的能编译、能跑的

不是「看起来像代码」的伪代码。用仓库内 `tools/kotlin/kotlinc`（1.9.24）+
5 个最小 Android 桩做了**真实编译**，并用编译产物跑了运行时对拍：

```
编译 exit = 0（4 个数据/算法文件 + AppColors）
运行 FAILS = 0（12 条调度向量 + CSV 往返 + 2 条保持率）
```

编译过程**真实抓出并修复了 2 个 bug**（`SettingsStore` 双 companion object、
`ContentValues.put` 重载歧义），这也说明这套验证不是走过场。
细节见 [`../project/_compilecheck/VERIFICATION.md`](../project/_compilecheck/VERIFICATION.md)。

| 部分 | 完整度 | 说明 |
|---|---|---|
| 调度算法 | ★★★★★ | 逐语句还原，12 条向量编译后运行验证 |
| 数据库 schema / SQL | ★★★★★ | 全部 SQL 原文可读 |
| 导入导出 | ★★★★★ | 状态机逐字符还原，往返测试通过 |
| 设置项 / 默认值 | ★★★★★ | 键名、类型、默认值、clamp 区间齐全 |
| 洞察公式 | ★★★★★ | 六个维度公式全部拿到 |
| 领域模型 | ★★★★☆ | 字段与顺序确定（`toString()` 为证），类名/属性名为推断 |
| 页面结构 | ★★★☆☆ | 靠 `testTag` 定位，需重写才能编译 |
| UI 像素级还原 | ★★☆☆☆ | 间距、圆角、动画曲线在 Compose 字节码里，未逐一提取 |
| 原始 Kotlin 语法 | ★☆☆☆☆ | `inline`/扩展函数/属性委托被 R8 与 Compose 编译器打平，不可逆 |

**无法恢复的东西**（诚实说明）：

1. 原始文件/类/变量名（R8 已丢弃，除非有 mapping.txt）；
2. 原始源码的注释、Kotlin 语法糖、`when` 表达式结构；
3. Compose 的 `@Composable` 源码形态（只能得到槽位式字节码）；
4. 原始的 `build.gradle` 精确版本（只能从 `META-INF/*.version` 与
   `kotlin-tooling-metadata.json` 反推到大版本）；
5. 签名私钥（这是理所当然的，也意味着**不能**用这份工程直接发布更新）。

---

## 9. 复现命令

```powershell
$JAVA = "D:\我的下载\WorkBuddy库\逆向分析\tools\jdk21\bin\java.exe"
$APK  = "D:\我的下载\WorkBuddy库\逆向分析\艾宾浩斯记忆曲线 1.0.2.apk"

# 资源 + 清单
& $JAVA -jar tools\android\apktool_2.12.0.jar d -f --no-src -o ebbinghaus\apktool $APK

# Java 反编译
$env:JAVA_HOME = "D:\我的下载\WorkBuddy库\逆向分析\tools\jdk21"
tools\android\jadx\bin\jadx.bat --no-res --show-bad-code -d ebbinghaus\decompiled $APK

# 字符串池
python scripts\dex_strings.py ebbinghaus\apktool\classes.dex > ebbinghaus\strings-all.txt

# 调度向量
python scripts\scheduler_oracle.py
```

---

## 10. 法律与使用边界

这份产物是**互操作性分析 / 学习研究**用途。代码与资源的著作权归原作者
（`com.luoyu.aibinhaosi`）所有。请勿用于：

- 重新打包分发（二次打包、去广告版、破解版）；
- 商业使用或上架应用商店；
- 绕过付费/授权（本 APP 本身免费且无内购，不涉及）。

如果你就是作者本人，想拿回工程继续维护，那 `decompiled/` + 本文档的映射表
足够你重建一个等价工程；`project/` 的骨架可以直接作为起点。
