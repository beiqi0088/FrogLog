# -*- coding: utf-8 -*-
"""仓库根入口：桌面双击 / 安卓打包（pyside6-android-deploy 要求入口文件叫 main.py）。"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
sys.path.insert(0, APP)


def _load_launcher():
    spec = importlib.util.spec_from_file_location(
        "froglog_launcher", os.path.join(APP, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


if __name__ == "__main__":
    _load_launcher().main()
