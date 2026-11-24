# 艾宾浩斯记忆曲线 1.0.2 — 逆向还原总索引

> 目标 APK：`艾宾浩斯记忆曲线 1.0.2.apk`（`com.luoyu.aibinhaosi`，2.1 MB）
> SHA-256：`171726F47AF35E1EC5C159E37E4A2A47DE3FFEE2EE83DD504B207C1F98F68C48`

## 先读这一页

这个 APP 是 **Kotlin + Jetpack Compose 原生应用**，被 R8 全量混淆。
「源码能不能逆向出来」的诚实答案是：

- **业务逻辑：几乎 100% 还原了，而且验证过能编译、能运行。**
  调度算法、数据库 schema/SQL、CSV 规则、设置项、六维健康公式，全部从字节码
  逐句读出，并写成可读 Kotlin。
- **原始工程的命名与语法：不可能恢复。** 包名、类名、字段名都被压成
  `a`/`b`/`f819a`；`inline`、扩展函数、Compose 槽位代码都不可逆。
- **UI：结构性还原。** 页面在字节码里能读懂，但 Compose 的 `@Composable`
  无法反编译回源码形态，必须重写。

## 从哪里开始

| 你想… | 打开 |
|---|---|
| **看 UI 设计稿（8 个页面）** | **[`design/index.html`](design/index.html)** |
| **看 PC 桌面版效果图** | [`pc/README.md`](pc/README.md) |
| 看整体结论与产物清单 | [`docs/REVERSE-ENGINEERING.md`](docs/REVERSE-ENGINEERING.md) |
| 找某个混淆类对应什么 | [`docs/DECOMPILE-MAP.md`](docs/DECOMPILE-MAP.md) |
| 搞懂复习间隔怎么算 | [`docs/SCHEDULER.md`](docs/SCHEDULER.md) |
| 看架构、页面、数据流 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| 直接读可编译的还原代码 | [`project/app/src/main/java/com/luoyu/aibinhaosi/recovered/`](project/app/src/main/java/com/luoyu/aibinhaosi/recovered/) |
| 看编译/运行验证结果 | [`project/_compilecheck/VERIFICATION.md`](project/_compilecheck/VERIFICATION.md) |
| 逐行比对原始反编译输出 | [`decompiled/`](decompiled/) |
| 拿资源 / 清单 / 协议 HTML | [`apktool/`](apktool/) |

## UI 设计稿

`design/index.html` —— 单文件、零依赖，双击即开。含 8 个页面：
合规门禁 / 今日 / 复习会话 / 记忆库 / 记忆库详情 / 计划 / 洞察 / 设置。

- 支持**浅色 / 深色**切换、**全部页面 / 交互演示**两种视图；
- 配色（纸白 + 墨绿 + 赭石）、文案、六维指标、四档评分间隔
  全部来自逆向结果；
- 改配色只动 `:root` 的 7 个变量，改内容只动 `DATA` 对象；
- 8 屏总览图：[`design/_shots/overview.png`](design/_shots/overview.png)；
- 修改指南：[`design/README.md`](design/README.md)。

**v2（合并桌面版「浮卡」）**：[`design/v2/index.html`](design/v2/index.html) —— 13 屏，
引入 7 套卡片皮肤、问答/单选/多选、浮墨速记、粘贴拆卡、知识域。
总览图 [`design/v2/_shots/overview.png`](design/v2/_shots/overview.png)，合并说明 [`design/v2/README.md`](design/v2/README.md)。

## 三条最值得知道的发现

### 1. 调度不是标准 SM-2，是「固定阶梯 + 简化 SM-2」

```
难度因子 ease ∈ [1.3, 3.2]，初值 2.35
固定阶梯 [1, 3, 7, 15, 30, 60] 天

重来：1 分钟后、reps 归零、ease −0.2
困难：×1.2、不推进阶梯、ease −0.15
记住：阶梯[reps]（前 6 次），之后 ×ease
轻松：阶梯 ×1.35 跳一级、ease +0.15（上限 3.2）
```

设计目标明显是**可预测的每日负荷**，而不是最大化记忆效率。
完整推导与 12 条编译后实测向量见 [`docs/SCHEDULER.md`](docs/SCHEDULER.md)。

### 2. 保持率就是艾宾浩斯曲线本身

```kotlin
R(t) = exp(-ln2 * t / interval)
```

`interval = 1 天` 时，复习后 1 天正好衰减到 **50%**（实测 0.5000）。
「六维健康指数」= 保持/准确/掌握/坚持/均衡/稳定，公式在
[`docs/SCHEDULER.md`](docs/SCHEDULER.md) 与 `recovered/analytics/Retention.kt`。

### 3. 隐私声明是真的

- 清单里**没有 INTERNET 权限**；
- 全树**没有** OkHttp / Firebase / 友盟 / 广告 / 崩溃上报；
- 唯一 I/O 是本地 SQLite、SharedPreferences、SAF 文件读写、assets 里的三份协议 HTML。

唯一可改进项：`allowBackup="true"`，学习数据可能进系统/云备份。

## 目录结构

```
ebbinghaus/
├─ README.md               ← 本页
├─ docs/                   ← 4 份分析文档
├─ design/                 ← UI 设计稿（index.html + 8 屏截图 + 改法说明）
├─ decompiled/             ← jadx 输出（2,742 个 .java）
├─ apktool/                ← 清单 + 176 个资源 + assets
├─ project/                ← Gradle 骨架 + 可编译还原代码 + 编译验证
├─ strings-all.txt         ← DEX 全部 10,419 条字符串
├─ strings-zh.txt          ← 其中 375 条中文文案
├─ strings-network.txt     ← 网络/密钥扫描结果（仅 4 条无关命中）
├─ scheduler-vectors.txt   ← 16 组调度向量
└─ validation.txt          ← CSV 13 项 + 调度 6,720 组不变量扫描
```

## 复现

```powershell
$JAVA = "D:\我的下载\WorkBuddy库\逆向分析\tools\jdk21\bin\java.exe"
$APK  = "D:\我的下载\WorkBuddy库\逆向分析\艾宾浩斯记忆曲线 1.0.2.apk"

& $JAVA -jar tools\android\apktool_2.12.0.jar d -f --no-src -o ebbinghaus\apktool $APK
$env:JAVA_HOME = "D:\我的下载\WorkBuddy库\逆向分析\tools\jdk21"
tools\android\jadx\bin\jadx.bat --no-res --show-bad-code -d ebbinghaus\decompiled $APK
python scripts\dex_strings.py ebbinghaus\apktool\classes.dex > ebbinghaus\strings-all.txt
python scripts\scheduler_oracle.py
python scripts\validate_recovered.py
```

## 边界

这是互操作性分析 / 学习研究。代码与资源著作权归原作者。
不要重新打包分发、不要商业使用、不要用于绕过任何授权。
