# v2 · 浮卡 × 艾宾浩斯 合并版

> 在 v1（纯艾宾浩斯 App 还原）的基础上，把桌面版「浮卡 FloCard」的核心能力融进来。
> 单文件 `index.html`，双击可看；13 屏。

打开：`http://127.0.0.1:8765/v2/index.html`
单屏：`?only=reviewmulti`（consent / today / memo / split / library / deck /
reviewqa / reviewsingle / reviewmulti / templates / plan / insights / settings）

## 一、这次从「浮卡」搬了什么

来源：`D:\我的下载\WorkBuddy库\闪卡制作\浮卡exe`
（PySide6 桌面应用，`README.md` 115 KB，`templates_data.json` / `data/cards.json` 为实际数据）

| 浮卡的能力 | 在 v2 里变成 | 证据 |
|---|---|---|
| **7 套 Anki 式卡片模板** | 卡片皮肤 `.tpl-*`，7 套配色原样取用 | `templates_data.json` 的 7 个 key；CSS 注释里写明主色 |
| **问答 / 单选 / 多选** | 三种复习卡：`reviewqa` / `reviewsingle` / `reviewmulti`，带选项正误态与解析 | `cards.json` 的 `type: multi` + `options` + `answer` + `analysis` |
| **浮墨记录**（`---` 拆正反） | 底部弹层 `memo`：一个输入框 + `---` 提示 + 卡包选择 + AI 拆题 | README「核心交互：浮墨记录 = flomo 对话框式制卡」 |
| **批量拆卡**（序号行规则） | `split`：粘贴 → 自动判题型 → 解析预览 → 导入 | README「批量拆卡」；`pages/split.py` |
| **知识域**（学习/工作/生活） | 今日与记忆库顶部的横条筛选 | `data/domains.json` 三个域 |
| **三档模式**（刷题/学习/浏览） | 卡包详情页的 `seg3` | README「铁盒页·四档页签」 |
| **导出到手机** | 设置页「导出到手机」条目 | `export_mobile_backup.py` |
| **AI 拆题** | 浮墨弹层的「✨ AI 拆题」 | `ai_core.py`、README「AI 大模型配置」 |

## 二、没搬的，以及为什么

| 浮卡的结构 | 处理 | 理由 |
|---|---|---|
| 知识域 → **圆桌** → **铁盒** → 卡包 → 卡组（4 级，可无限嵌套） | 压成 **知识域 → 卡包 → 卡组** | 手机上 4 级嵌套会让「找到一张卡」变成 5 次点击；桌面有大屏和拖拽，手机没有 |
| Logseq 式树状笔记 / 双链 / 反链 | 只保留「浮墨」这一条轻量入口 | 完整笔记系统是另一个产品；手机端只需要「随手记 → 变卡片」 |
| 桌面拖拽、右键菜单、批量勾选 | 不做 | 触屏交互范式不同 |
| 四档页签（第 4 档「批量拆卡」） | 拆卡改为独立页，从设置/卡包进入 | 手机上不适合塞进页签 |

## 三、两个需要拍板的冲突（我做了选择）

**1. 评级档位：浮卡 3 档 vs 艾宾浩斯 4 档**

- 浮卡：`重来 / 良好 / 记住`（`pages/review.py` 的 `RATE_DEFS`，色值 `#E8503A / #5A6470 / #2E9E67`）
- 艾宾浩斯：`重来 / 困难 / 记住 / 轻松`，且调度算法（`b4.v.T0`）**按 4 档的 ease 增减实现**

**v2 采用 4 档**，因为算法是围绕 4 档写的，改成 3 档要重算 ease。若坚持 3 档，
映射建议：浮卡「良好」→ 艾宾浩斯「困难」+「记住」之间，需要给 `GOOD` 拆出两个步长。

**2. 卡片皮肤 vs 应用主题**

浮卡 7 套模板是**整屏**换肤（Anki 的 qfmt/afmt/css 直接控制整张卡）。
v2 的处理是：**外壳保持纸感（v1 的 7 个变量不动），只有卡片正反面换皮肤**。
好处是品牌一致、7 套皮肤不会互相打架；代价是失去「整屏沉浸」的强度。

如果更想要沉浸感，改法很简单：让 `.skin` 铺满屏幕（去掉 20px 边距、
把 `.screen` 背景设成皮肤底色），评级按钮浮在底部。

## 四、13 屏清单

| # | key | 页面 | 新增/改动 |
|---|---|---|---|
| 00 | `consent` | 合规门禁 | 文案改为「笔记、卡片与复习记录都留在本机」 |
| 01 | `today` | 今日 | + 知识域横条、题型徽标、浮墨 FAB |
| 02 | `memo` | 浮墨记录 | **新**：`---` 拆正反、AI 拆题 |
| 03 | `split` | 批量拆卡 | **新**：粘贴 → 解析 → 导入 |
| 04 | `library` | 记忆库 | + 知识域筛选、模板名 |
| 05 | `deck` | 卡包详情 | **新**：三档模式、卡组列表 |
| 06 | `reviewqa` | 复习 · 问答 | 卡面用「豆沙绿语」皮肤 |
| 07 | `reviewsingle` | 复习 · 单选 | **新**：选项 A–D + 正误态 |
| 08 | `reviewmulti` | 复习 · 多选 | **新**：多选判定 + 解析 |
| 09 | `templates` | 卡片模板 | **新**：7 套皮肤选择 |
| 10 | `plan` | 计划 | + 按知识域的负荷 |
| 11 | `insights` | 洞察 | + 按题型正确率 |
| 12 | `settings` | 设置 | + 模板 / 知识域 / 导出到手机 |

## 五、改法

```css
/* 外壳 */
:root { --bg; --primary; --accent; --line; }
/* 卡片皮肤（7 套，类名即模板） */
.tpl-bean  { background:#C7EDCC; color:#2d4b4b; }  .tpl-bean .label { background:#4f8f9d; }
.tpl-mint  { background:#c7ecee; }  .tpl-sky { background:#B3E5FC; }
.tpl-pink  { background:#FFE5F1; }  .tpl-candy { background:#fff0f8; }
.tpl-lime  { background:#d1f2eb; }  .tpl-glass { background:linear-gradient(...); }
.tpl-sunset{ background:#F5F5FF; }
```

- 数据：`D` 对象（decks / deck.groups / memo / split / review.{qa,single,multi} / templates）
- 页面：`sToday()`、`sMemo()`、`sSplit()`、`sReviewQA()` … 一个函数一屏
- 重新出图：`python capture.py`（13 屏 + 总览）

## 六、还没做的

- 空态 / 加载态 / 错误态
- 多选题「提交前」的状态（现在展示的是已判定态）
- 模板在暗色模式下的适配（7 套皮肤都是浅色底；暗色下需要各配一套夜间值）
- 笔记的树状结构（只做了浮墨单条入口）
