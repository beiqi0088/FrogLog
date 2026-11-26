#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Android 16（API 36）打包包装器。

pyside6-android-deploy 生成 buildozer.spec 时不设置 Android API，最终会落在
buildozer 的默认值上（通常是 API 31/34）。本脚本先加载部署工具，在它刚生成
buildozer.spec、真正调用 buildozer 之前，把目标版本改成 Android 16：

    android.api                = 36   # compileSdkVersion + targetSdkVersion
    android.minapi             = 28   # Qt 6.11 for Android 的最低要求
    android.ndk                = 27c  # 与 PySide6 Android 轮子的交叉编译 NDK 一致
    android.accept_sdk_license = True

用法与 pyside6-android-deploy 完全一致，只是把命令换成本脚本，例如：

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
NDK_VERSION = "27c"

PATCHED_KEYS = {
    "android.api": TARGET_API,
    "android.minapi": MIN_API,
    "android.ndk": NDK_VERSION,
    "android.accept_sdk_license": "True",
}


def patch_buildozer_spec() -> None:
    spec = Path.cwd() / "buildozer.spec"
    if not spec.exists():
        return
    text = spec.read_text(encoding="utf-8")
    for key, value in PATCHED_KEYS.items():
        # buildozer init 生成的是注释行，如 "#android.api = 31"
        pattern = re.compile(rf"(?m)^\s*#?\s*{re.escape(key)}\s*=.*$")
        if pattern.search(text):
            text = pattern.sub(f"{key} = {value}", text)
        else:
            text = text.rstrip() + f"\n{key} = {value}\n"
    spec.write_text(text, encoding="utf-8")
    print("[android16] buildozer.spec 已改为 Android 16 配置：")
    for key, value in PATCHED_KEYS.items():
        print(f"  {key} = {value}")


def main() -> None:
    import PySide6

    scripts_dir = Path(PySide6.__file__).resolve().parent / "scripts"
    sys.path.insert(0, str(scripts_dir))

    from deploy_lib.android.buildozer import Buildozer

    original_create_executable = Buildozer.create_executable

    def create_executable(mode):
        patch_buildozer_spec()
        return original_create_executable(mode)

    Buildozer.create_executable = staticmethod(create_executable)

    deploy_script = scripts_dir / "android_deploy.py"
    sys.argv[0] = str(deploy_script)
    runpy.run_path(str(deploy_script), run_name="__main__")


if __name__ == "__main__":
    main()
