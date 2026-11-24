# -*- coding: utf-8 -*-
"""backup.py - 备份快照的发现、摘要、创建与恢复（纯逻辑，不依赖 Qt）。

快照来源：
  <数据目录>/state.json.bak          同步/导入前自动留的那份
  <数据目录>/state.json.<tag>-<ts>   历史修复时留的快照（keyfix / prefix …）
  <数据目录>/backups/*.json          这里自己建的快照（手动 / 回滚前）
  <数据目录>/backups/*.zip           导出的备份包

恢复永远是「整份换掉」，所以恢复前会先给当前数据存一份 before-restore 快照；
同步用的账号密钥属于本机配置，恢复时不会被备份里的那份覆盖。
"""
from __future__ import annotations

import glob
import json
import os
import time
import zipfile

import core

KIND_LABEL = {
    "auto": "自动备份",
    "manual": "手动备份",
    "before-restore": "回滚前快照",
    "daily": "每日自动",
    "zip": "导出包",
    "migrate": "迁移快照",
}


def data_dir(store) -> str:
    return os.path.dirname(os.path.abspath(store.path))


def backup_dir(store) -> str:
    d = os.path.join(data_dir(store), "backups")
    os.makedirs(d, exist_ok=True)
    return d


def _kind_of(path: str) -> str:
    name = os.path.basename(path)
    if name.lower().endswith(".zip"):
        return "zip"
    if name == "state.json.bak":
        return "auto"
    if name.startswith("before-restore-"):
        return "before-restore"
    if name.startswith("daily-"):
        return "daily"
    if name.startswith("backup-"):
        return "manual"
    return "migrate"


def _payload(path: str) -> bytes:
    """读快照内容：.zip 里取 state.json（或第一个非 manifest 的 json）。"""
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            inner = next((n for n in names if n.lower().endswith("state.json")), None)
            if inner is None:
                inner = next((n for n in names
                              if n.lower().endswith(".json") and "manifest" not in n.lower()),
                             None)
            if inner is None:
                raise ValueError("压缩包里没有 state.json")
            return z.read(inner)
    with open(path, "rb") as f:
        return f.read()


def summarize(path: str) -> dict:
    """读一个快照的标头，用来列表展示；坏文件不抛异常。"""
    info = {
        "path": path,
        "name": os.path.basename(path),
        "kind": _kind_of(path),
        "mtime": os.path.getmtime(path) * 1000,
        "size": os.path.getsize(path),
        "cards": 0,
        "decks": 0,
        "updated_at": 0,
        "ok": False,
        "error": "",
    }
    try:
        obj = json.loads(_payload(path).decode("utf-8"))
        info["cards"] = len(obj.get("cards") or [])
        info["decks"] = len(obj.get("decks") or [])
        info["updated_at"] = int(obj.get("updated_at") or 0)
        info["ok"] = bool(obj.get("cards"))
        if not info["ok"]:
            info["error"] = "里面没有卡片"
    except Exception as e:
        info["error"] = f"读不出来：{e}"
    return info


def list_snapshots(store) -> list[dict]:
    """所有可用快照，新的在前（不含当前 state.json）。"""
    d = data_dir(store)
    paths: list[str] = []

    bak = os.path.join(d, "state.json.bak")
    if os.path.exists(bak):
        paths.append(bak)

    for p in glob.glob(os.path.join(d, "state.json.*")):
        if p.endswith(".tmp") or p == bak:
            continue
        paths.append(p)

    for pattern in ("*.json", "*.zip"):
        paths.extend(glob.glob(os.path.join(backup_dir(store), pattern)))

    items = [summarize(p) for p in paths]
    items.sort(key=lambda x: -x["mtime"])       # 新的在前，先看到最可能想恢复的那份
    return items


def create_snapshot(store, tag: str = "backup") -> str:
    """把当前数据存成 <backups>/<tag>-YYYYmmdd-HHMMSS.json。"""
    d = backup_dir(store)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(d, f"{tag}-{stamp}.json")
    n = 2
    while os.path.exists(path):
        path = os.path.join(d, f"{tag}-{stamp}-{n}.json")
        n += 1
    data = store.export_bytes(bump=False)      # 不改内存里的 updated_at
    with open(path, "wb") as f:
        f.write(data)
    _prune(store)
    return path


def _prune(store, keep: int = 30):
    """手动/回滚前快照最多留 30 份、每日自动留 14 份，避免无限增长。"""
    for prefix, limit in (("backup-", keep), ("before-restore-", keep), ("daily-", 14)):
        items = sorted(glob.glob(os.path.join(backup_dir(store), prefix + "*.json")),
                       key=os.path.getmtime, reverse=True)
        for old in items[limit:]:
            try:
                os.remove(old)
            except OSError:
                pass


def daily_snapshot(store) -> str | None:
    """每天第一次启动存一份（同一天只存一次）。异常一律吞掉，不影响启动。"""
    try:
        stamp = time.strftime("%Y%m%d")
        existing = glob.glob(os.path.join(backup_dir(store), f"daily-{stamp}-*.json"))
        if existing:
            return None
        return create_snapshot(store, "daily")
    except Exception:
        return None


def restore(store, path: str) -> tuple[bool, str]:
    """用快照整份替换当前数据。恢复前先给当前数据存一份 before-restore 快照。"""
    try:
        obj = json.loads(_payload(path).decode("utf-8"))
    except Exception as e:
        return False, f"这份备份读不出来：{e}"
    if not isinstance(obj, dict) or not obj.get("cards"):
        return False, "这份备份里没有卡片，已放弃"
    if not os.path.exists(path):
        return False, "文件不见了"

    try:
        create_snapshot(store, "before-restore")
    except Exception as e:
        return False, f"回滚前备份失败，已放弃：{e}"

    core.keep_device_sync_settings(store.state, obj)   # 本机同步配置不被覆盖
    store.state = obj
    store.save()
    return True, f"已恢复 {len(obj.get('cards') or [])} 张卡片"


def delete_snapshot(store, path: str) -> tuple[bool, str]:
    """只允许删数据目录里的快照；当前 state.json 不在列表里，删不到。"""
    root = os.path.abspath(data_dir(store))
    target = os.path.abspath(path)
    if not target.startswith(root + os.sep):
        return False, "不在数据目录里，已拒绝"
    if os.path.basename(target) == "state.json":
        return False, "不能删当前数据"
    try:
        os.remove(target)
    except OSError as e:
        return False, f"删除失败：{e}"
    return True, "已删除"


def fmt_time(ms: float) -> str:
    if not ms:
        return "—"
    return time.strftime("%m-%d %H:%M", time.localtime(ms / 1000))


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 / 1024:.1f} MB"
