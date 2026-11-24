# 用 GitHub Actions 打安卓 APK

Android 的 PySide6 轮子官方只发给商业用户，但 PySide6 的源码是 LGPL：**自己交叉编译一份 Android 轮子完全合法**。
交叉编译只能在 Linux 上做 —— GitHub Actions 免费提供 Ubuntu 机器，所以这条路不需要本地 Linux、不需要 Qt 商业许可。

## 一、准备（5 分钟）

1. 在 GitHub 新建一个仓库（**公开仓库**：Actions 分钟数不限；私有仓库免费额度 2000 分钟/月，够跑十几次）。
2. 把 `ebbinghaus/` **目录里的内容**推成仓库根目录（`main.py`、`app/`、`.github/` 必须在根上）：

   ```bash
   cd ebbinghaus
   git init
   git add .
   git commit -m "FrogLog"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/<仓库名>.git
   git push -u origin main
   ```

3. 推之前确认 `.gitignore` 已生效（仓库里已带一份）：`decompiled/`、`apktool/`、`project/`、`app001.zip`、`_scratch/` 这些不要上传。

## 二、触发构建

1. 打开仓库页面 → **Actions** 标签；
2. 左侧选 **Android APK**；
3. 右上角 **Run workflow** → 再点绿色 **Run workflow**；
4. 等它跑完（首次约 **60–120 分钟**，之后有缓存会快一些）。

## 三、下载与安装

1. 构建成功后点进这次运行，页面底部 **Artifacts** → 下载 `FrogLog-android-apk.zip`；
2. 解压得到 `.apk`（debug 模式出的是 `apk`）；
3. 传到手机点开安装；第一次需要在系统里允许"安装未知来源的应用"。

## 四、这次工作流做了什么

`.github/workflows/android.yml` 的步骤：

1. 装编译工具 + JDK 17；
2. `aqtinstall` 装 Qt for Android 6.11.1（与桌面 PySide6 同版本）；
3. 克隆 `pyside-setup` 6.11.1，跑 `tools/cross_compile_android/main.py`：
   自动下载 Android NDK r28c、SDK、python.org 的 Android CPython，然后编出
   `PySide6-*-android_arm64_v8a.whl` 和 `shiboken6-*.whl`；
4. `pip install pyside6==6.11.1` 拿到 `pyside6-android-deploy` 工具；
5. `pyside6-android-deploy --name FrogLog`：内部用 buildozer 打包成 APK；
6. 上传 APK 作为 artifact。

## 五、缓存

工作流缓存了三样东西，第二次之后会快很多：

| 缓存 | 路径 | key |
|---|---|---|
| Qt for Android | `~/Qt` | `qt-android-<os>-6.11.1` |
| NDK / SDK / Android 轮子 | `~/.pyside6-android-deploy`、`pyside-setup/dist_android` | `pyside-android-<os>-6.11.1` |

换 Qt 版本时把 key 里的版本号一起改掉即可。

## 六、常见失败与排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `Commercial License NOT found` | 用了 `qtpip download` 下载官方轮子 | 不要用 qtpip，走工作流里的源码交叉编译 |
| 编译轮子超时 | 首次要编译整个 Qt for Python | 重新跑一次（缓存已生效），或把 job 拆成"编轮子"和"打包"两个 job |
| `pyside6-android-deploy: command not found` | 桌面 PySide6 版本和轮子不一致 | 确认 `pip install pyside6==6.11.1` |
| APK 安装后闪退 | 数据目录/字体/屏幕尺寸等安卓适配问题 | 看 `adb logcat`，把日志发我，我改代码 |
| `main.py` 找不到 | 入口不在仓库根目录 | 本仓库根目录已有 `main.py`，不要把它挪进 `app/` |

## 七、安卓适配（已做了一部分）

- `core.data_path()`：安卓走 `ANDROID_PRIVATE`（应用私有目录），桌面仍用 `%APPDATA%\FloCardLite`；
- `app/main.py`：安卓上 `showMaximized()` 铺满屏幕，字体回退到 `Noto Sans CJK SC`；
- 根目录 `main.py`：`pyside6-android-deploy` 要求入口文件必须叫这个名字。

还没验证、首次跑可能要调的地方：窗口尺寸策略（手机竖屏 430px 逻辑宽度）、文件选择框（导入导出备份在安卓上受限）、
`QMessageBox`/`QMenu` 在触屏上的表现。跑出第一版 APK 后逐个修。
