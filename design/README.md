# UI 设计稿 · 使用与修改说明

> **v3 已出**：「打卡」改名「征途」，融合 Habitica 的等级/生命/经验、习惯·每日·待办、
> 连击、队伍副本与奖励商店（5 屏）。看 [journey/README.md](journey/README.md) /
> 打开 [journey/index.html](journey/index.html) / 蓝图见
> [`../docs/JOURNEY-PLAN.md`](../docs/JOURNEY-PLAN.md)。

> **v2 已出**：合并了桌面版「浮卡」的 7 套卡片模板、3 种题型、浮墨速记与粘贴拆卡。
> 看 [v2/README.md](v2/README.md) / 打开 [v2/index.html](v2/index.html)。

> 单文件、零依赖，双击 `index.html` 就能看。
> 配色、文案、页面结构全部来自 `艾宾浩斯记忆曲线 1.0.2` 的逆向结果。

## 打开方式

| 方式 | 说明 |
|---|---|
| 直接双击 | `index.html`，无需服务器 |
| 本地服务（推荐） | `python -m http.server 8765` → `http://127.0.0.1:8765` |
| 单页大图 | `?only=today`（`consent` / `today` / `review` / `library` / `deck` / `plan` / `insights` / `settings`） |
| 深色版 | `?only=insights&theme=dark` |
| 高清导出用 | `?only=today&scale=2`，配合 780×1900 窗口截图 |

页面右上角可切换「全部页面 / 交互演示」，以及「浅色 / 深色」。
交互演示里可以点底部四个页签、点「开始今日复习」进入复习流程。

## 文件

```
design/
├─ index.html        ← 全部设计（样式 + 数据 + 8 个页面）
├─ capture.py        ← 批量截图脚本（Edge 无头 + Pillow 拼总览）
└─ _shots/
   ├─ overview.png   ← 8 屏总览（1724×1892）
   ├─ today.png …    ← 单屏 780×1688（390×844 @2x）
   ├─ today-dark.png / insights-dark.png / review-dark.png
```

## 怎么改

### ① 换配色 —— 只动 `:root`

```css
:root {
  --bg: #FBF8F1;      /* 纸白背景 */
  --surface: #FFFFFF; /* 卡片 */
  --ink: #242721;     /* 主文字 */
  --sub: #73766F;     /* 次要文字 */
  --line: #E4E1D6;    /* 分隔线 */
  --primary: #2F6A43; /* 墨绿主色 */
  --accent: #BF5B38;  /* 赭石强调 */
}
html[data-theme="dark"] { /* 深色一一对应 */ }
```

这 7 个变量覆盖了 90% 的视觉。改 `--primary` 一处，按钮、进度条、雷达、
热力图、开关会一起变。

### ② 换圆角 / 字号

```css
--r-sm: 12px;   /* 卡片内小块 */
--r-md: 18px;   /* 常规卡片 */
--r-lg: 26px;   /* 主视觉卡 */
```

大标题在 `.h1`（27px），正文 13–14px，说明文字 11.5px。
想更「大厂」一点，把 `.h1` 提到 30px、`.card` 圆角提到 22px 即可。

### ③ 改内容 —— 只动 `DATA`

```js
const DATA = {
  today: { due: 12, done: 0, minutes: 9 },
  decks: [ { name:'生物 · 细胞结构', cards:5, due:3, mastered:0, color:0 } ],
  review: { question:'线粒体的主要功能是什么？', answer:'…' },
  plan: { limit: 20, forecast: [12,9,14,…] },
  insights: { radar: [...], activity: [...], accuracy: 91 },
};
```

图表都是从数组算出来的：改 `forecast` 柱状图就变，改 `radar` 雷达图就变，
改 `activity` 热力图就变。

### ④ 改结构

每个页面一个函数，返回 HTML 字符串，直接增删标签：

| 函数 | 页面 |
|---|---|
| `screenConsent()` | 合规门禁 |
| `screenToday()` | 今日 |
| `screenReview(revealed)` | 复习会话（`false` 未翻面 / `true` 已翻面） |
| `screenLibrary()` | 记忆库列表 |
| `screenDeck()` | 记忆库详情 |
| `screenPlan()` | 计划 |
| `screenInsights()` | 洞察 |
| `screenSettings()` | 设置 |

想在画廊里加/减一屏，改 `SCREENS` 对象即可（key 会成为 `?only=` 的值）。

### ⑤ 重新出图

```powershell
# 先起本地服务（capture.py 依赖 http://127.0.0.1:8765）
python -m http.server 8765 --directory .
python capture.py
```

## 哪些是「还原」，哪些是「我的设计」

为了你后续改得心里有数，明确区分：

**来自逆向、尽量保真：**

- 配色：`#FBF8F1` 纸白、`#2F6A43` 墨绿、`#BF5B38` 赭石、六个记忆库色
  （`f3.a` / `d3.r`）；
- 全部中文文案（`strings-zh.txt` 375 条）；
- 页面清单与信息层级：今日 / 记忆库 / 计划 / 洞察 + 复习、详情、设置、门禁；
- 六维名称与顺序：保持 / 准确 / 掌握 / 坚持 / 均衡 / 稳定；
- 四档评分与默认间隔：重来 1 分钟、困难 1 天、记住 3 天、轻松 7 天；
- 设置分组：每日节奏 / 显示与反馈 / 示例与模板 / 数据与备份 / 关于与支持；
- 记忆库「已掌握」= `repetitions ≥ 4 且 interval ≥ 30 天` 的语义。

**是我的设计决定（原版长相未知，可放心推翻）：**

- 字号阶梯、卡片圆角、阴影与间距；
- 今日页的绿色大卡（原版可能只是普通卡片）；
- 雷达图 / 柱状图 / 热力图 / 环形图的具体画法（原版用 Compose Canvas，
  形状可读但像素级参数未提取）；
- 图标全部是我手绘的线性图标（原版用 Material Icons）；
- 合规门禁页的同心圆插画；
- 复习卡「问题在上、答案贴底」的排布。

## 已知取舍

- 设计稿按 **390×844** 画（接近 Pixel / iPhone 逻辑尺寸），Android 上多为
  360×800，落实现时把 `.device` 宽度改成 360 并检查换行即可。
- 洞察页内容超出一屏，是**可滚动**的；截图里底部有 30px 渐隐提示还有内容。
- 没有做空态、加载态、错误态（原版有：`还没有卡片`、`数据加载失败`、
  `当前没有到期卡片，稍后再来看看`），需要的话可以直接加。
- 字号/对比度未做无障碍校验，正式落地前建议跑一遍 4.5:1 对比度检查。
