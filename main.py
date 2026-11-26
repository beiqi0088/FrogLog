# -*- coding: utf-8 -*-
"""仓库根入口：桌面双击 / 安卓打包（pyside6-android-deploy 要求入口文件叫 main.py）。

注意：python-for-android 打包时会执行 compileall 并把 .py 源文件删掉，
APK 里只剩 app/main.pyc。所以这里不能按 .py 路径加载，必须兼容 .pyc。
"""
import importlib.machinery
import importlib.util
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
sys.path.insert(0, APP)


def _load_launcher():
    name = "froglog_launcher"
    source = os.path.join(APP, "main.py")
    if os.path.exists(source):
        spec = importlib.util.spec_from_file_location(name, source)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    # Android APK 里源码不存在，只有 app/main.pyc
    compiled = os.path.join(APP, "main.pyc")
    loader = importlib.machinery.SourcelessFileLoader(name, compiled)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _report_crash(exc: BaseException) -> None:
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    sys.stderr.write(text)
    base = os.environ.get("ANDROID_PRIVATE") or os.environ.get("APPDATA") or os.path.expanduser("~")
    try:
        with open(os.path.join(base, "froglog_crash.log"), "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "FrogLog 启动失败", text[-1200:])
    except Exception:
        pass


if __name__ == "__main__":
    try:
        _load_launcher().main()
    except BaseException as exc:      # noqa: BLE001 - 兜底，把启动异常留下来
        _report_crash(exc)
        raise
