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
import sys
from pathlib import Path

TARGET_API = "36"
MIN_API = "28"
NDK_VERSION = "28c"

# 固定 p4a 到已验证的 commit，避免 master 漂移导致 Java 锚点/manifest 模板变化、
# 诊断补丁失效。该 commit 已确认 apply_p4a_diag_patch 能正确注入。
P4A_COMMIT = "58d21141f17c889bf8585f5665921d72028f8831"

PATCHED_KEYS = {
    "android.api": TARGET_API,
    "android.minapi": MIN_API,
    "android.ndk": NDK_VERSION,
    "android.accept_sdk_license": "True",
    "p4a.branch": "master",
    "p4a.commit": P4A_COMMIT,
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


def patch_buildozer_spec(spec: Path) -> None:
    if not spec or not spec.exists():
        _log(f"没找到 buildozer.spec（{spec}），跳过 spec 修改")
        return

    text = spec.read_text(encoding="utf-8")
    for key, value in PATCHED_KEYS.items():
        # buildozer init 生成的是注释行，如 "#android.api = 31"
        pattern = re.compile(rf"(?m)^\s*#?\s*{re.escape(key)}\s*=.*$")
        if pattern.search(text):
            text = pattern.sub(f"{key} = {value}", text)
        else:
            text = text.rstrip() + f"\n{key} = {value}\n"

    # buildozer 1.5.0 不会把 android.api 传给 p4a 的 apk 命令，
    # 这里额外通过 p4a.extra_args 显式传一次（p4a 的通用参数，create/apk 都接受）
    p4a_args = re.search(r"(?m)^\s*#?\s*p4a\.extra_args\s*=(.*)$", text)
    api_arg = f"--android-api={TARGET_API}"
    if p4a_args:
        current = p4a_args.group(1).strip()
        if api_arg not in current:
            # 整行重写，去掉注释符，保留 pyside 写入的 --qt-libs 等参数
            text = (text[:p4a_args.start()]
                    + f"p4a.extra_args = {current} {api_arg}".rstrip()
                    + text[p4a_args.end():])
    else:
        text = text.rstrip() + f"\np4a.extra_args = {api_arg}\n"

    spec.write_text(text, encoding="utf-8")
    _log(f"buildozer.spec 已改为 Android 16 配置（{spec}）")
    for key, value in PATCHED_KEYS.items():
        _log(f"  {key} = {value}")
    _log(f"  p4a.extra_args += {api_arg}")


def patch_icon(spec: Path) -> None:
    """把应用图标换成仓库里的 assets/icon.png（默认是 pyside 的 logo）。"""
    icon = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    if not icon.exists():
        _log(f"没找到图标 {icon}，沿用默认图标")
        return
    text = spec.read_text(encoding="utf-8")
    line = f"icon.filename = {icon}"
    pattern = re.compile(r"(?m)^\s*#?\s*icon\.filename\s*=.*$")
    if pattern.search(text):
        text = pattern.sub(line, text)
    else:
        text = text.rstrip() + f"\n{line}\n"
    spec.write_text(text, encoding="utf-8")
    _log(f"应用图标已换成 {icon}")


# 自定义 Application：在 Qt/Python 启动之前写标记文件，并捕获未捕获的 Java 异常。
# 继承 QtApplication 并调用 super.onCreate()，正常运行时行为完全不变。
DIAG_APP_JAVA = r'''package org.kivy.android;

import android.util.Log;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.io.StringWriter;

// FrogLog diagnostic Application. Runs before Qt/Python. Writes marker files
// and records uncaught Java exceptions so a startup crash can be diagnosed
// without logcat. Behavior is unchanged when everything works.
public class FrogLogDiagApp extends org.qtproject.qt.android.bindings.QtApplication {
    private static final String TAG = "FrogLogDiag";

    private static void write(File dir, String name, String body) {
        if (dir == null) return;
        try {
            dir.mkdirs();
            FileWriter w = new FileWriter(new File(dir, name));
            w.write(body);
            w.close();
        } catch (Throwable t) {
            Log.e(TAG, "write " + name + " failed", t);
        }
    }

    @Override
    public void onCreate() {
        // BEFORE super.onCreate(). If app_started.txt is missing, the crash
        // happened while loading the application class / native libraries
        // (native crash -> need logcat/tombstone).
        File ext = null, intd = null;
        try { ext = getExternalFilesDir(null); } catch (Throwable t) {}
        try { intd = getFilesDir(); } catch (Throwable t) {}
        String info = "model=" + android.os.Build.MODEL + " sdk=" + android.os.Build.VERSION.SDK_INT;
        write(ext, "app_started.txt", "FrogLogDiagApp.onCreate before super | " + info);
        write(intd, "app_started.txt", "FrogLogDiagApp.onCreate before super | " + info);

        final File logExt = ext, logInt = intd;
        final Thread.UncaughtExceptionHandler prev = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
            public void uncaughtException(Thread t, Throwable e) {
                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                String body = "=== UNCAUGHT EXCEPTION ===\nthread: " + t + "\n" + sw.toString();
                write(logExt, "froglog_crash.log", body);
                write(logInt, "froglog_crash.log", body);
                Log.e(TAG, body, e);
                if (prev != null) {
                    try { prev.uncaughtException(t, e); } catch (Throwable ignore) {}
                }
            }
        });

        super.onCreate();
        write(ext, "app_after_super.txt", "QtApplication.super.onCreate() returned OK");
        write(intd, "app_after_super.txt", "QtApplication.super.onCreate() returned OK");
    }
}
'''

# 插在 PythonActivity.onCreate 的最开头（this.mActivity = this 之前），
# 用于区分崩溃发生在 Activity 创建之前还是 super.onCreate（Qt/Python 启动）之中。
ACTIVITY_MARKER = '''        try { // FrogLogDiag
            java.io.File _e = getExternalFilesDir(null);
            if (_e != null) { _e.mkdirs(); new java.io.FileWriter(new java.io.File(_e, "activity_started.txt")).append("onCreate").close(); }
        } catch (Throwable _t) { Log.e("FrogLogDiag", "ext marker failed", _t); }
        try {
            java.io.File _i = getFilesDir();
            if (_i != null) { _i.mkdirs(); new java.io.FileWriter(new java.io.File(_i, "activity_started.txt")).append("onCreate").close(); }
        } catch (Throwable _t2) {}
'''


def _qt_bootstrap_java_dir(p4a_dir: Path) -> Path | None:
    if not p4a_dir:
        return None
    d = (Path(p4a_dir) / "pythonforandroid" / "bootstraps" / "qt" / "build"
         / "src" / "main" / "java" / "org" / "kivy" / "android")
    return d if d.exists() else None


def apply_p4a_diag_patch(p4a_dir) -> None:
    """在 p4a 的 qt bootstrap 里注入启动诊断标记（幂等）。

    必须在 p4a 编译 Java 之前调用——通过 monkeypatch TargetAndroid._p4a 保证。
    """
    java_dir = _qt_bootstrap_java_dir(p4a_dir)
    if java_dir is None:
        return  # p4a 还没 clone，等下次 _p4a 调用

    # 1) FrogLogDiagApp.java（Application 级早期标记 + 未捕获异常日志）
    diag = java_dir / "FrogLogDiagApp.java"
    diag.write_text(DIAG_APP_JAVA, encoding="utf-8")

    # 2) PythonActivity.onCreate 最开头打标记
    py_act = java_dir / "PythonActivity.java"
    if py_act.exists():
        text = py_act.read_text(encoding="utf-8")
        if "activity_started.txt" not in text:
            anchor = "    public void onCreate(Bundle savedInstanceState) {\n        this.mActivity = this;"
            if anchor in text:
                text = text.replace(anchor, "    public void onCreate(Bundle savedInstanceState) {\n" + ACTIVITY_MARKER + "        this.mActivity = this;", 1)
                py_act.write_text(text, encoding="utf-8")
                _log(f"已在 PythonActivity.onCreate 注入 activity 启动标记")
            else:
                _log(f"PythonActivity.java 里找不到 onCreate 锚点，跳过 activity 标记")

    # 3) manifest 模板：把 Application 换成 FrogLogDiagApp
    manifest = (Path(p4a_dir) / "pythonforandroid" / "bootstraps" / "qt" / "build"
                / "templates" / "AndroidManifest.tmpl.xml")
    if manifest.exists():
        text = manifest.read_text(encoding="utf-8")
        if "FrogLogDiagApp" not in text:
            old = 'android:name="org.qtproject.qt.android.bindings.QtApplication"'
            if old in text:
                text = text.replace(old, 'android:name="org.kivy.android.FrogLogDiagApp"', 1)
                manifest.write_text(text, encoding="utf-8")
                _log("已把 manifest 的 Application 换成 FrogLogDiagApp")


def install_target_patch() -> None:
    """挂钩 buildozer 的 p4a 调用入口，保证补丁在编译前生效。"""
    try:
        from buildozer.targets.android import TargetAndroid
    except Exception as exc:
        _log(f"无法导入 buildozer.targets.android.TargetAndroid，跳过诊断补丁（{exc}）")
        return
    if getattr(TargetAndroid, "_froglog_patched", False):
        return
    orig_p4a = TargetAndroid._p4a

    def _p4a_patched(self, cmd, env, **kwargs):
        try:
            apply_p4a_diag_patch(self.p4a_dir)
        except Exception as exc:  # noqa: BLE001 - 诊断补丁失败不能阻断打包
            _log(f"应用 p4a 诊断补丁失败: {exc}")
        return orig_p4a(self, cmd, env, **kwargs)

    TargetAndroid._p4a = _p4a_patched
    TargetAndroid._froglog_patched = True
    _log("已挂钩 TargetAndroid._p4a，将在 p4a 编译前注入启动诊断标记")


def main() -> None:
    import PySide6

    scripts_dir = Path(PySide6.__file__).resolve().parent / "scripts"
    sys.path.insert(0, str(scripts_dir))

    from deploy_lib.android.buildozer import Buildozer

    # 挂钩 buildozer 的 p4a 调用，在编译 Java 前注入启动诊断标记
    install_target_patch()

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
        patch_buildozer_spec(spec)
        patch_buildozer_constants()
        # Java 诊断标记由 install_target_patch() 挂钩的 _p4a 在编译前注入
        return original_create_executable(mode)

    Buildozer.create_executable = staticmethod(create_executable)

    deploy_script = scripts_dir / "android_deploy.py"
    sys.argv[0] = str(deploy_script)
    runpy.run_path(str(deploy_script), run_name="__main__")


if __name__ == "__main__":
    main()
