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
        patch_buildozer_spec(spec)
        patch_buildozer_constants()
        return original_create_executable(mode)

    Buildozer.create_executable = staticmethod(create_executable)

    deploy_script = scripts_dir / "android_deploy.py"
    sys.argv[0] = str(deploy_script)
    runpy.run_path(str(deploy_script), run_name="__main__")


if __name__ == "__main__":
    main()
