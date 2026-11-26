# -*- coding: utf-8 -*-
"""仓库根入口：桌面双击 / 安卓打包（pyside6-android-deploy 要求入口文件叫 main.py）。

注意两点：
1. python-for-android 打包时会执行 compileall 并把 .py 源文件删掉，APK 里只剩
   app/main.pyc，所以不能按 .py 路径加载，必须兼容 .pyc；
2. 安卓上启动即闪退时看不到任何输出，这里把 stdout/stderr、Qt 警告、Python 崩溃
   （faulthandler）统一写到应用自己的外部目录，方便用户直接把日志取出来：
       /sdcard/Android/data/org.froglog.froglog/files/froglog.log
"""
import importlib.machinery
import importlib.util
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
sys.path.insert(0, APP)

LOG_FILE = None


def _open_log():
    """打开启动日志：优先外部可读目录，退回到应用私有目录。"""
    global LOG_FILE
    priv = os.environ.get("ANDROID_PRIVATE") or ""
    # /data/user/0/org.froglog.froglog/files -> org.froglog.froglog
    pkg = ""
    if "/data/" in priv:
        pkg = priv.split("/files")[0].rstrip("/").split("/")[-1]
    ext = f"/storage/emulated/0/Android/data/{pkg}/files" if pkg else ""
    candidates = [ext, priv]
    for base in candidates:
        if not base:
            continue
        try:
            os.makedirs(base, exist_ok=True)
            f = open(os.path.join(base, "froglog.log"), "a", encoding="utf-8", buffering=1)
        except Exception:
            continue
        LOG_FILE = f
        # 把 fd 1/2 也指过去，Qt 的 qWarning/qFatal 和 native abort 信息才会进文件
        try:
            os.dup2(f.fileno(), 1)
            os.dup2(f.fileno(), 2)
        except Exception:
            pass
        return f
    return None


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    if LOG_FILE is not None:
        try:
            LOG_FILE.write(line + "\n")
            LOG_FILE.flush()
            return
        except Exception:
            pass
    try:
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def _load_launcher():
    name = "froglog_launcher"
    source = os.path.join(APP, "main.py")
    if os.path.exists(source):
        log("launcher: 加载 app/main.py")
        spec = importlib.util.spec_from_file_location(name, source)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    compiled = os.path.join(APP, "main.pyc")
    log(f"launcher: 加载 {compiled}")
    loader = importlib.machinery.SourcelessFileLoader(name, compiled)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _report_crash(exc: BaseException) -> None:
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    log("启动失败:\n" + text)
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "FrogLog 启动失败", text[-1200:])
    except Exception:
        pass


def _boot():
    log("=" * 20 + " FrogLog 启动 " + "=" * 20)
    log(f"python: {sys.version}")
    log(f"argv: {sys.argv}")
    log(f"cwd: {os.getcwd()}")
    log(f"__file__: {__file__}")
    log(f"sys.path: {sys.path}")
    interesting = {k: v for k, v in os.environ.items()
                   if k.startswith(("QT_", "ANDROID_", "PYTHON", "LD_", "P4A"))}
    log(f"env: {interesting}")

    try:
        import faulthandler
        if LOG_FILE is not None:
            faulthandler.enable(LOG_FILE.fileno())
        else:
            faulthandler.enable()
        log("faulthandler 已开启")
    except Exception as exc:
        log(f"faulthandler 开启失败: {exc}")

    log("导入 PySide6 ...")
    import PySide6
    log(f"PySide6 版本 {PySide6.__version__}，路径 {PySide6.__file__}")

    sys.froglog_log = log          # app/main.py 里用它打点
    mod = _load_launcher()
    log("调用 launcher.main() ...")
    mod.main()
    log("launcher.main() 返回")


if __name__ == "__main__":
    _open_log()
    try:
        _boot()
    except BaseException as exc:      # noqa: BLE001 - 兜底，把启动异常留下来
        _report_crash(exc)
        if LOG_FILE is not None:
            LOG_FILE.flush()
        raise
    finally:
        log("进程结束")
