#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Android 16（API 36）打包包装器。

pyside6-android-deploy 生成 buildozer.spec 时不设置 Android API，buildozer 1.5.0
会退回自己的默认常量（ANDROID_API='31'、ANDROID_MINAPI='21'），于是 APK 的
targetSdkVersion 只有 31。本包装器在调用 buildozer 之前做两件事：

1. 改 buildozer.spec（buildozer 正常会读它）：
       android.api                = 36
       android.minapi             = 28
       android.ndk                = 28c
       android.accept_sdk_license = True
       p4a.extra_args            += --android-api=36
2. 直接改 buildozer 源码里的默认常量 ANDROID_API / ANDROID_MINAPI。
   buildozer 的 spec 里这两项是注释行，getdefault() 回落到常量；
   改常量能保证即便 spec 没被读到，python-for-android 仍收到
   $ANDROIDAPI=36 / --minsdk 28，最终 compileSdkVersion 与 targetSdkVersion 都是 36。

用法与 pyside6-android-deploy 完全一致，只是把命令换成本脚本：

    python3 scripts/android16_deploy.py \
        --name FrogLog --wheel-pyside ... --wheel-shiboken ... -v
"""
from __future__ import annotations

import re
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

TARGET_API = "36"
MIN_API = "28"
NDK_VERSION = "28c"

# 固定 p4a 到已验证的 commit，避免 master 漂移导致 Java 锚点/manifest 模板变化、
# 诊断补丁失效。通过 buildozer 的 p4a.source_dir 指向我们事先打好补丁的克隆，
# 这样补丁一定在编译前生效（buildozer 直接用这个目录，不再 clone / git reset）。
P4A_COMMIT = "58d21141f17c889bf8585f5665921d72028f8831"
P4A_URL = "https://github.com/kivy/python-for-android.git"
P4A_SRC_DIRNAME = ".p4a-src"

# PySide6 6.11.1 的 Android 轮子是按 CPython 3.11 交叉编译出来的（官方
# download.qt.io 上的 Android 轮子也只有 cp311，6.11.1 的交叉编译脚本里
# PYTHON_VERSION 写死 3.11），扩展模块 NEEDED 里是 libpython3.11.so。
# 而 p4a master 的 python3 recipe 已经升到 3.14.2，打出来的 APK 只有
# libpython3.14.so —— import PySide6 时 dlopen 找不到 libpython3.11.so，
# 应用在 Python 启动阶段就退出，表现为打开即闪退、什么都看不到。
# 所以这里把 p4a 的 python3 / hostpython3 recipe 钉回 3.11.11。
P4A_PYTHON_VERSION = "3.11.11"

PATCHED_KEYS = {
    "android.api": TARGET_API,
    "android.minapi": MIN_API,
    "android.ndk": NDK_VERSION,
    "android.accept_sdk_license": "True",
}


def _log(message: str) -> None:
    # GitHub Actions 里 stdout 是块缓冲的，不 flush 的话日志顺序会乱
    print(f"[android16] {message}", flush=True)


def patch_buildozer_constants() -> None:
    """把 buildozer 的默认 API 常量改成 Android 16。"""
    import buildozer

    module = Path(buildozer.__file__).resolve().parent / "targets" / "android.py"
    text = module.read_text(encoding="utf-8")
    new_text = text
    for name, value in (("ANDROID_API", TARGET_API), ("ANDROID_MINAPI", MIN_API)):
        pattern = re.compile(rf"(?m)^{name} = '.*'$")
        if not pattern.search(new_text):
            raise SystemExit(f"[android16] 在 {module} 中找不到 {name}，无法设置 API 级别")
        new_text = pattern.sub(f"{name} = '{value}'", new_text)
    module.write_text(new_text, encoding="utf-8")
    _log(f"buildozer 默认常量已改为 ANDROID_API='{TARGET_API}', ANDROID_MINAPI='{MIN_API}'")
    _log(f"已写入 {module}")


def _set_app_key(text: str, key: str, value: str) -> str:
    """在 buildozer.spec 的 [app] 段里设置键。

    注意：spec 末尾还有 [buildozer] 段，直接 append 到文件尾会被当成
    [buildozer] 的键，buildozer 读 app.p4a.source_dir 时读不到——上一版就是
    因此仍然 clone 了官方 p4a（Python 3.14），补丁全部失效。
    """
    line = f"{key} = {value}"
    pattern = re.compile(rf"(?m)^[ \t]*#?[ \t]*{re.escape(key)}[ \t]*=.*$")
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    header = re.search(r"(?m)^\[app\][^\n]*\n", text)
    if not header:
        raise SystemExit("[android16] buildozer.spec 里没有 [app] 段")
    return text[:header.end()] + line + "\n" + text[header.end():]


def verify_buildozer_spec(spec: Path, expected: dict) -> None:
    """真正用 configparser 读一遍，确认键落在 [app] 段。"""
    import configparser

    parser = configparser.RawConfigParser(strict=False)
    parser.read(spec, encoding="utf-8")
    problems = []
    for key, value in expected.items():
        actual = parser.get("app", key, fallback="<缺失>")
        if actual != value:
            problems.append(f"{key}={actual!r}（期望 {value!r}）")
    if problems:
        raise SystemExit("[android16] buildozer.spec 校验失败：" + "；".join(problems))


def patch_buildozer_spec(spec: Path) -> None:
    if not spec or not spec.exists():
        _log(f"没找到 buildozer.spec（{spec}），跳过 spec 修改")
        return

    # p4a 必须先克隆并打好补丁，再用 p4a.source_dir 指过去；
    # buildozer 看到 source_dir 就不会再 clone / git reset，补丁一定生效。
    p4a_dir = prepare_p4a_source(Path(__file__).resolve().parent.parent)

    text = spec.read_text(encoding="utf-8")
    for key, value in PATCHED_KEYS.items():
        text = _set_app_key(text, key, value)
    text = _set_app_key(text, "p4a.source_dir", str(p4a_dir))

    # buildozer 1.5.0 不会把 android.api 传给 p4a 的 apk 命令，
    # 这里额外通过 p4a.extra_args 显式传一次（p4a 的通用参数，create/apk 都接受）
    api_arg = f"--android-api={TARGET_API}"
    p4a_args = re.search(r"(?m)^[ \t]*#?[ \t]*p4a\.extra_args[ \t]*=(.*)$", text)
    if p4a_args:
        current = p4a_args.group(1).strip()
        if api_arg not in current:
            text = _set_app_key(text, "p4a.extra_args", f"{current} {api_arg}".strip())
    else:
        text = _set_app_key(text, "p4a.extra_args", api_arg)

    spec.write_text(text, encoding="utf-8")

    expected = dict(PATCHED_KEYS)
    expected["p4a.source_dir"] = str(p4a_dir)
    verify_buildozer_spec(spec, expected)

    # 双保险：在 buildozer 的默认 p4a 目录预置一份打好补丁的源码。
    # 上一版 p4a.source_dir 没被 buildozer 读到（它仍然 clone 了官方 develop 分支，
    # Python 又是 3.14），这里保证即使 spec 失效也会用到我们的补丁。
    stage_p4a_for_buildozer(spec, p4a_dir)

    _log(f"buildozer.spec 已改为 Android 16 配置并校验通过（{spec}）")
    for key, value in expected.items():
        _log(f"  {key} = {value}")
    _log(f"  p4a.extra_args += {api_arg}")


def patch_icon(spec: Path) -> None:
    """把应用图标换成仓库里的 assets/icon.png（默认是 pyside 的 logo）。"""
    icon = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    if not icon.exists():
        _log(f"没找到图标 {icon}，沿用默认图标")
        return
    text = spec.read_text(encoding="utf-8")
    text = _set_app_key(text, "icon.filename", str(icon))
    spec.write_text(text, encoding="utf-8")
    _log(f"应用图标已换成 {icon}")


# 自定义 Application：在 Qt/Python 启动之前写“阶梯标记”，并捕获未捕获的 Java 异常。
# 继承 QtApplication 并调用 super.onCreate()，正常运行时行为完全不变。
# 标记会写到三个地方，其中「下载/FrogLog/froglog-android.txt」在系统文件管理器和
# 数据线 MTP 里都能直接看到（Android 11+ 会隐藏 Android/data，所以必须有这个）。
DIAG_APP_JAVA = r'''package org.kivy.android;

import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.Log;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.RandomAccessFile;
import java.io.StringWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

// FrogLog startup trace. Writes a ladder of markers so a startup crash can be
// located without logcat:
//   Application.attachBaseContext -> Application.onCreate -> super.onCreate
//   -> PythonActivity.onCreate -> unpack -> QtActivity.super.onCreate
// The same text is appended to Download/FrogLog/froglog-android.txt, which is
// visible in the system file manager / via USB MTP.
public class FrogLogDiagApp extends org.qtproject.qt.android.bindings.QtApplication {
    private static final String TAG = "FrogLogDiag";
    private static final String DIR = "FrogLog";
    private static final String TRACE_FILE = "froglog-android.txt";
    private static volatile Context sCtx;
    private static Uri sTraceUri;

    private static void appendFile(File f, String s) {
        try {
            FileOutputStream os = new FileOutputStream(f, true);
            os.write(s.getBytes("UTF-8"));
            os.close();
        } catch (Throwable t) {
            Log.e(TAG, "append " + f, t);
        }
    }

    private static Uri traceUri(Context ctx) {
        if (sTraceUri != null) return sTraceUri;
        if (Build.VERSION.SDK_INT < 29) return null;   // Downloads 集合需要 API 29+
        ContentResolver cr = ctx.getContentResolver();
        Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
        String rel = Environment.DIRECTORY_DOWNLOADS + "/" + DIR + "/";
        try (Cursor c = cr.query(collection, new String[]{MediaStore.MediaColumns._ID},
                MediaStore.MediaColumns.RELATIVE_PATH + "=? AND "
                        + MediaStore.MediaColumns.DISPLAY_NAME + "=?",
                new String[]{rel, TRACE_FILE}, null)) {
            if (c != null && c.moveToFirst()) {
                sTraceUri = ContentUris.withAppendedId(collection, c.getLong(0));
                return sTraceUri;
            }
        } catch (Throwable t) {
            Log.e(TAG, "query downloads", t);
        }
        try {
            ContentValues cv = new ContentValues();
            cv.put(MediaStore.MediaColumns.DISPLAY_NAME, TRACE_FILE);
            cv.put(MediaStore.MediaColumns.MIME_TYPE, "text/plain");
            cv.put(MediaStore.MediaColumns.RELATIVE_PATH, rel);
            sTraceUri = cr.insert(collection, cv);
        } catch (Throwable t) {
            Log.e(TAG, "insert downloads", t);
        }
        return sTraceUri;
    }

    // 追加一行追踪信息：应用私有目录 + 外部目录 + 下载/FrogLog
    static void stage(Context ctx, String msg) {
        Log.i(TAG, msg);
        if (ctx == null) ctx = sCtx;
        String line = "[" + new SimpleDateFormat("MM-dd HH:mm:ss.SSS", Locale.US)
                .format(new Date()) + "] " + msg + "\n";
        if (ctx == null) return;
        try { appendFile(new File(ctx.getFilesDir(), TRACE_FILE), line); } catch (Throwable t) {}
        try {
            File ext = ctx.getExternalFilesDir(null);
            if (ext != null) { ext.mkdirs(); appendFile(new File(ext, TRACE_FILE), line); }
        } catch (Throwable t) {}
        try {
            Uri uri = traceUri(ctx);
            if (uri != null) {
                OutputStream os = ctx.getContentResolver().openOutputStream(uri, "wa");
                if (os != null) { os.write(line.getBytes("UTF-8")); os.close(); }
            }
        } catch (Throwable t) {
            Log.e(TAG, "append downloads", t);
        }
    }

    private static String readTail(File f, int max) {
        try {
            long len = f.length();
            if (len <= 0) return null;
            RandomAccessFile raf = new RandomAccessFile(f, "r");
            raf.seek(Math.max(0, len - max));
            byte[] buf = new byte[(int) Math.min(max, len)];
            int n = raf.read(buf);
            raf.close();
            return n > 0 ? new String(buf, 0, n, "UTF-8") : null;
        } catch (Throwable t) {
            return null;
        }
    }

    // 把 Python 端写的日志（froglog.log / froglog_crash.log）发布到 下载/FrogLog
    static void publishPythonLogs(Context ctx) {
        if (ctx == null) ctx = sCtx;
        if (ctx == null) return;
        for (String name : new String[]{"froglog_crash.log", "froglog.log"}) {
            String body = readTail(new File(ctx.getFilesDir(), name), 96 * 1024);
            if (body == null) {
                try {
                    File ext = ctx.getExternalFilesDir(null);
                    if (ext != null) body = readTail(new File(ext, name), 96 * 1024);
                } catch (Throwable t) {}
            }
            if (body == null || body.length() == 0) continue;
            stage(ctx, "----- " + name + " -----\n" + body + "\n----- " + name + " end -----");
        }
    }

    @Override
    public void attachBaseContext(Context base) {
        sCtx = base;
        super.attachBaseContext(base);
        stage(base, "Application.attachBaseContext 完成 | abi="
                + (Build.SUPPORTED_ABIS.length > 0 ? Build.SUPPORTED_ABIS[0] : "?")
                + " sdk=" + Build.VERSION.SDK_INT + " model=" + Build.MODEL);
    }

    @Override
    public void onCreate() {
        sCtx = this;
        stage(this, "===== FrogLog 启动 =====");
        stage(this, "Application.onCreate 开始（下一步 super.onCreate → QtApplication）");

        // 先把上一次运行留下的 Python 日志发到 下载/FrogLog/，方便用户直接取出
        try { publishPythonLogs(this); } catch (Throwable t) { Log.e(TAG, "publish previous", t); }

        final Thread.UncaughtExceptionHandler prev =
                Thread.getDefaultUncaughtExceptionHandler();
        final Context appCtx = this;
        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
            public void uncaughtException(Thread t, Throwable e) {
                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                stage(appCtx, "!!! 未捕获 Java 异常 thread=" + t.getName() + "\n" + sw);
                try { publishPythonLogs(appCtx); } catch (Throwable ignore) {}
                if (prev != null && prev != this) {
                    try { prev.uncaughtException(t, e); } catch (Throwable ignore) {}
                }
            }
        });

        super.onCreate();
        stage(this, "QtApplication.super.onCreate 已返回（Qt 已启动，接下来 Activity）");

        // Python 由 Qt 在后台线程拉起，延迟几次把它的日志同步到 下载/FrogLog
        Handler h = new Handler(Looper.getMainLooper());
        for (long delay : new long[]{3000, 8000, 20000, 60000}) {
            h.postDelayed(new Runnable() {
                public void run() {
                    try { publishPythonLogs(appCtx); } catch (Throwable ignore) {}
                }
            }, delay);
        }
    }
}
'''

# PythonActivity.onCreate 里的阶梯标记（Activity 级）
ACTIVITY_STAGE_BEFORE_UNPACK = '''        FrogLogDiagApp.stage(this, "PythonActivity.onCreate 开始（准备解包 private.tar / libpybundle）");
'''
ACTIVITY_STAGE_AFTER_UNPACK = '''        FrogLogDiagApp.stage(this, "Python 资源解包完成（private.tar + libpybundle → files/app）");
'''
ACTIVITY_STAGE_BEFORE_SUPER = '''        FrogLogDiagApp.stage(this, "即将调用 QtActivity.super.onCreate（加载 libmain → 启动 Python）");
'''
ACTIVITY_STAGE_AFTER_SUPER = '''        FrogLogDiagApp.stage(this, "PythonActivity.super.onCreate 已返回");
'''

# 状态栏和底部手势区透明，Qt 的渐变背景可以直接画到系统栏后面。
SYSTEM_BARS_JAVA = r'''package org.kivy.android;

import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.os.SystemClock;
import android.view.View;
import android.view.Window;
import android.view.WindowInsetsController;

public final class FrogLogSystemBars {
    private FrogLogSystemBars() {}

    // Qt 在窗口首次 show 时会重新设置系统栏（恢复主题色、把内容收回安全区），
    // 只在前台 onCreate 里调用一次会被覆盖。这里在启动后多次重放，最后一次
    // 一定落在 Qt 的首次 show 之后，渐变才能真正铺到状态栏和手势条后面。
    private static final long[] REPLAY_DELAYS = {300L, 1000L, 2500L, 5000L, 8000L};

    public static void apply(final Activity activity) {
        if (activity == null) return;
        applyNow(activity);
        final View decor = activity.getWindow().getDecorView();
        for (long delay : REPLAY_DELAYS) {
            decor.postDelayed(new Runnable() {
                @Override
                public void run() {
                    applyNow(activity);
                }
            }, delay);
        }
        // 兜底：Qt 首次 show 会引发一次布局，此时再校正一次。
        // 20 秒后自动摘掉监听，之后不再有额外开销。
        decor.addOnLayoutChangeListener(new View.OnLayoutChangeListener() {
            private long lastApplied = 0L;
            private final long startedAt = SystemClock.elapsedRealtime();

            @Override
            public void onLayoutChange(View v, int left, int top, int right, int bottom,
                                       int oldLeft, int oldTop, int oldRight, int oldBottom) {
                long now = SystemClock.elapsedRealtime();
                if (now - startedAt > 20000L) {
                    v.removeOnLayoutChangeListener(this);
                    return;
                }
                if (now - lastApplied < 400L) return;
                lastApplied = now;
                applyNow(activity);
            }
        });
    }

    private static void applyNow(Activity activity) {
        if (activity == null || activity.isFinishing()) return;
        Window window = activity.getWindow();
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false);
            WindowInsetsController controller = window.getInsetsController();
            if (controller != null) {
                int light = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                        | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
                // 状态栏 / 手势条为主题深色：系统图标用白色（清掉 LIGHT 标志）
                controller.setSystemBarsAppearance(0, light);
            }
        } else {
            int flags = View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION;
            // 不加 LIGHT_STATUS_BAR / LIGHT_NAVIGATION_BAR：深色底上用白色系统图标
            window.getDecorView().setSystemUiVisibility(flags);
        }
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.TRANSPARENT);
        if (Build.VERSION.SDK_INT >= 29) {
            window.setStatusBarContrastEnforced(false);
            window.setNavigationBarContrastEnforced(false);
        }
    }
}
'''

# p4a 默认会在第一次返回时弹 “Click again to close the app”，并吞掉这次按键。
# 改为直接交给 QtActivity，Python 里的 Qt.Key_Back 就能在第一次返回时生效。
P4A_BACK_DOUBLE_TAP = '''    long lastBackClick = SystemClock.elapsedRealtime();

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        // If it wasn't the Back key or there's no web page history, bubble up to the default
        // system behavior (probably exit the activity)
        if (SystemClock.elapsedRealtime() - lastBackClick > 2000) {
            lastBackClick = SystemClock.elapsedRealtime();
            Toast.makeText(this, "Click again to close the app", Toast.LENGTH_LONG).show();
            return true;
        }

        lastBackClick = SystemClock.elapsedRealtime();
        return super.onKeyDown(keyCode, event);
    }
'''

P4A_BACK_DIRECT = '''    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        return super.onKeyDown(keyCode, event);
    }
'''


def _qt_bootstrap_java_dir(p4a_dir: Path) -> Path | None:
    if not p4a_dir:
        return None
    d = (Path(p4a_dir) / "pythonforandroid" / "bootstraps" / "qt" / "build"
         / "src" / "main" / "java" / "org" / "kivy" / "android")
    return d if d.exists() else None


def _p4a_manifest(p4a_dir: Path) -> Path:
    return (Path(p4a_dir) / "pythonforandroid" / "bootstraps" / "qt" / "build"
            / "templates" / "AndroidManifest.tmpl.xml")


def apply_p4a_diag_patch(p4a_dir: Path) -> None:
    """在 p4a 的 qt bootstrap 里注入启动诊断标记（幂等）。"""
    java_dir = _qt_bootstrap_java_dir(p4a_dir)
    if java_dir is None:
        raise SystemExit(f"[android16] {p4a_dir} 不是 p4a 源码目录（找不到 qt bootstrap）")

    # 1) FrogLogDiagApp.java（启动诊断）+ FrogLogSystemBars.java（全屏渐变系统栏）
    (java_dir / "FrogLogDiagApp.java").write_text(DIAG_APP_JAVA, encoding="utf-8")
    (java_dir / "FrogLogSystemBars.java").write_text(SYSTEM_BARS_JAVA, encoding="utf-8")

    # 2) PythonActivity.onCreate 插入 4 个 Activity 级标记
    py_act = java_dir / "PythonActivity.java"
    text = py_act.read_text(encoding="utf-8")
    if "FrogLogDiagApp.stage(" not in text:
        replacements = [
            ("    public void onCreate(Bundle savedInstanceState) {\n        this.mActivity = this;",
             "    public void onCreate(Bundle savedInstanceState) {\n"
             + ACTIVITY_STAGE_BEFORE_UNPACK + "        this.mActivity = this;"),
            ('        Log.v("Python", "Device: " + android.os.Build.DEVICE);',
             ACTIVITY_STAGE_AFTER_UNPACK
             + '        Log.v("Python", "Device: " + android.os.Build.DEVICE);'),
            ('        Log.v(TAG, "About to do super onCreate");',
             ACTIVITY_STAGE_BEFORE_SUPER
             + '        Log.v(TAG, "About to do super onCreate");'),
            ('        Log.v(TAG, "Did super onCreate");',
             ACTIVITY_STAGE_AFTER_SUPER
             + '        Log.v(TAG, "Did super onCreate");'),
        ]
        for old, new in replacements:
            if old not in text:
                raise SystemExit(f"[android16] PythonActivity.java 里找不到锚点：{old.strip()[:60]}")
            text = text.replace(old, new, 1)
        _log("已在 PythonActivity.onCreate 注入 4 个启动阶梯标记")

    # 3) 首次返回直接交给 Qt，不再先弹英文 Toast
    if P4A_BACK_DOUBLE_TAP in text:
        text = text.replace(P4A_BACK_DOUBLE_TAP, P4A_BACK_DIRECT, 1)
    elif "Click again to close the app" in text:
        raise SystemExit("[android16] PythonActivity.java 的双击返回代码与固定版本不一致")
    if "Click again to close the app" not in text and P4A_BACK_DIRECT not in text:
        raise SystemExit("[android16] PythonActivity.java 没有可替换的返回键实现")

    # 4) Qt 窗口创建后开启沉浸式系统栏，状态栏/手势条都由渐变背景覆盖
    if "FrogLogSystemBars.apply(this);" not in text:
        anchor = '        Log.v(TAG, "Did super onCreate");'
        if anchor not in text:
            raise SystemExit("[android16] PythonActivity.java 找不到系统栏注入锚点")
        text = text.replace(anchor, "        FrogLogSystemBars.apply(this);\n" + anchor, 1)
    py_act.write_text(text, encoding="utf-8")

    # 5) manifest 模板：Application 换成 FrogLogDiagApp
    manifest = _p4a_manifest(p4a_dir)
    text = manifest.read_text(encoding="utf-8")
    if "FrogLogDiagApp" not in text:
        old = 'android:name="org.qtproject.qt.android.bindings.QtApplication"'
        if old not in text:
            raise SystemExit(f"[android16] {manifest} 里找不到 QtApplication 锚点")
        manifest.write_text(text.replace(old, 'android:name="org.kivy.android.FrogLogDiagApp"', 1),
                            encoding="utf-8")
        _log("已把 manifest 的 Application 换成 FrogLogDiagApp")


def patch_p4a_python_version(p4a_dir: Path) -> None:
    """把 p4a 的 python3 / hostpython3 recipe 钉回 3.11（与 PySide6 轮子一致）。"""
    for recipe in ("python3", "hostpython3"):
        path = Path(p4a_dir) / "pythonforandroid" / "recipes" / recipe / "__init__.py"
        text = path.read_text(encoding="utf-8")
        new_text, count = re.subn(
            r"(?m)^(\s+)version = (['\"])[^'\"]+\2",
            lambda m: f'{m.group(1)}version = "{P4A_PYTHON_VERSION}"',
            text, count=1)
        if count != 1:
            raise SystemExit(f"[android16] {path} 里找不到 version = ...")
        path.write_text(new_text, encoding="utf-8")
        _log(f"{recipe} recipe 版本已钉到 {P4A_PYTHON_VERSION}")


def verify_p4a_patch(p4a_dir: Path) -> None:
    """确认所有补丁真的落到实处，否则立刻失败（别浪费一小时 CI）。"""
    java_dir = _qt_bootstrap_java_dir(p4a_dir)
    problems = []
    if java_dir is None or not (java_dir / "FrogLogDiagApp.java").exists():
        problems.append("FrogLogDiagApp.java 未生成")
    if java_dir is None or not (java_dir / "FrogLogSystemBars.java").exists():
        problems.append("FrogLogSystemBars.java 未生成")
    if "org.kivy.android.FrogLogDiagApp" not in _p4a_manifest(p4a_dir).read_text(encoding="utf-8"):
        problems.append("manifest 未指向 FrogLogDiagApp")
    py_act = java_dir / "PythonActivity.java" if java_dir else None
    if py_act is None or "FrogLogDiagApp.stage(" not in py_act.read_text(encoding="utf-8"):
        problems.append("PythonActivity 未注入阶梯标记")
    elif py_act is not None:
        activity = py_act.read_text(encoding="utf-8")
        if "Click again to close the app" in activity:
            problems.append("PythonActivity 仍有双击返回提示")
        if "FrogLogSystemBars.apply(this);" not in activity:
            problems.append("PythonActivity 未启用全屏渐变系统栏")
    for recipe in ("python3", "hostpython3"):
        path = Path(p4a_dir) / "pythonforandroid" / "recipes" / recipe / "__init__.py"
        if f'version = "{P4A_PYTHON_VERSION}"' not in path.read_text(encoding="utf-8"):
            problems.append(f"{recipe} 版本不是 {P4A_PYTHON_VERSION}")
    if problems:
        raise SystemExit("[android16] p4a 补丁校验失败：" + "；".join(problems))
    _log("p4a 补丁校验通过（启动诊断 + 全屏系统栏 + 直接返回 + Python 3.11）")


def stage_p4a_for_buildozer(spec: Path, p4a_dir: Path) -> Path:
    """把打好补丁的 p4a 放到 buildozer 默认位置（source_dir 不生效时兜底）。

    buildozer 会检查该目录的 remote url 与分支名是否和 spec 一致：
    kivy / develop。所以这里 checkout 出 develop 分支，并把补丁提交进去，
    这样它既不会删目录，也不会 git reset 掉补丁。
    """
    dest = spec.parent / ".buildozer" / "android" / "platform" / "python-for-android"
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(p4a_dir, dest, symlinks=True)

    git = ["git", "-C", str(dest)]
    if not (dest / ".git").exists():
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["remote", "add", "origin", P4A_URL], check=True)
    # 先提交补丁，再建 develop 分支；顺序反了 git 会把未提交的补丁直接丢掉
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["-c", "user.name=froglog", "-c", "user.email=froglog@local",
                          "commit", "-q", "-m", "froglog android16 p4a patches"], check=True)
    subprocess.run(git + ["checkout", "-B", "develop"], check=True)
    verify_p4a_patch(dest)
    _log(f"已预置补丁版 p4a 到 {dest}（buildozer 默认路径兜底）")
    return dest


def prepare_p4a_source(repo_root: Path) -> Path:
    """克隆并打好补丁的 p4a，之后通过 buildozer 的 p4a.source_dir 直接用。"""
    dest = repo_root / P4A_SRC_DIRNAME
    if not (dest / "pythonforandroid" / "bootstraps" / "qt").exists():
        if dest.exists():
            shutil.rmtree(dest)
        _log(f"克隆 python-for-android 到 {dest}")
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        P4A_URL, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin", P4A_COMMIT],
                   check=False, capture_output=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "-f", P4A_COMMIT], check=True)
    _log(f"python-for-android 已切到 {P4A_COMMIT[:10]}")

    apply_p4a_diag_patch(dest)
    patch_p4a_python_version(dest)
    verify_p4a_patch(dest)
    return dest


def main() -> None:
    import PySide6

    scripts_dir = Path(PySide6.__file__).resolve().parent / "scripts"
    sys.path.insert(0, str(scripts_dir))

    from deploy_lib.android.buildozer import Buildozer

    spec_holder: dict[str, Path | None] = {"path": None}

    original_initialize = Buildozer.initialize

    def initialize(pysidedeploy_config):
        original_initialize(pysidedeploy_config)
        # 记录 spec 的真实路径，避免依赖运行目录
        project_dir = Path(pysidedeploy_config.project_dir)
        spec_holder["path"] = project_dir / "buildozer.spec"
        _log(f"project_dir = {project_dir}")
        if spec_holder["path"].exists():
            patch_icon(spec_holder["path"])

    Buildozer.initialize = staticmethod(initialize)

    original_create_executable = Buildozer.create_executable

    def create_executable(mode):
        spec = spec_holder["path"] or (Path.cwd() / "buildozer.spec")
        # 这里会克隆并打好 p4a 补丁（阶梯标记 + Python 3.11 recipe），
        # 再写入 p4a.source_dir，buildozer 直接用这份源码编译
        patch_buildozer_spec(spec)
        patch_buildozer_constants()
        return original_create_executable(mode)

    Buildozer.create_executable = staticmethod(create_executable)

    deploy_script = scripts_dir / "android_deploy.py"
    sys.argv[0] = str(deploy_script)
    runpy.run_path(str(deploy_script), run_name="__main__")


if __name__ == "__main__":
    main()
