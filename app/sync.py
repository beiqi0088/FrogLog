# -*- coding: utf-8 -*-
"""
sync.py - 同步通道：局域网（内置 HTTP 服务）、WebDAV、S3（SigV4）。

只依赖标准库：urllib / http.server / hmac / hashlib。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class SyncError(Exception):
    pass


# ---------------------------------------------------------------- HTTP 基础
def _http(method: str, url: str, data: bytes | None = None,
          headers: dict | None = None, timeout: int = 20) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        raise SyncError(str(e))


# ---------------------------------------------------------------- WebDAV
class WebDAV:
    """WebDAV 同步。支持只填目录（如坚果云 /dav/），会自动补 flocard/state.json 并创建目录。"""

    FILE_NAME = "state.json"

    def __init__(self, url: str, username: str = "", password: str = ""):
        self.raw = url.strip()
        self.username = username
        self.password = password
        self.url = self._normalize(self.raw)

    # ---------------- URL 处理 ----------------
    def _normalize(self, url: str) -> str:
        if not url:
            return ""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        url = url.rstrip("/") + "/"
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.rstrip("/")
        last = path.rsplit("/", 1)[-1]
        # 目录（没有扩展名）→ 自动补 flocard/state.json
        if "." not in last:
            path = path + "/flocard/" + self.FILE_NAME
        return urllib.parse.urlunparse(parsed._replace(path=path))

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"Content-Type": "application/json; charset=utf-8"}
        if self.username:
            raw = f"{self.username}:{self.password}".encode("utf-8")
            h["Authorization"] = "Basic " + base64.b64encode(raw).decode()
        if extra:
            h.update(extra)
        return h

    def _ensure_dirs(self):
        """逐级 MKCOL，已存在返回 405 也算成功。"""
        parsed = urllib.parse.urlparse(self.url)
        parts = [x for x in parsed.path.split("/") if x]
        base = f"{parsed.scheme}://{parsed.netloc}"
        cur = ""
        for seg in parts[:-1]:
            cur += "/" + seg
            status, _ = _http("MKCOL", base + cur + "/", headers=self._headers())
            if status in (201, 204, 405, 301, 403, 409):
                continue

    # ---------------- 操作 ----------------
    def pull(self) -> bytes | None:
        if not self.url:
            raise SyncError("没有填写 WebDAV 地址")
        status, body = _http("GET", self.url, headers=self._headers())
        if status == 404:
            return None
        if status == 409:
            return None
        if 200 <= status < 300:
            return body
        if status in (401, 403):
            raise SyncError("认证失败：坚果云要用「应用密码」，不是登录密码")
        raise SyncError(f"读取失败 HTTP {status}")

    def push(self, data: bytes):
        if not self.url:
            raise SyncError("没有填写 WebDAV 地址")
        self._ensure_dirs()
        status, body = _http("PUT", self.url, data=data, headers=self._headers())
        if 200 <= status < 300:
            return
        if status in (409, 404):
            # 目录刚建好但服务端还没生效，重试一次
            self._ensure_dirs()
            status, body = _http("PUT", self.url, data=data, headers=self._headers())
            if 200 <= status < 300:
                return
        if status in (401, 403):
            raise SyncError("认证失败：检查账号与应用密码")
        msg = body[:120].decode("utf-8", "ignore").strip()
        raise SyncError(f"上传失败 HTTP {status} {msg}".strip())

    def test(self) -> str:
        status, _ = _http("GET", self.url or "http://", headers=self._headers())
        if status in (200, 204, 207):
            return "连接正常"
        if status in (404, 409):
            self._ensure_dirs()
            status, _ = _http("PUT", self.url, data=b"{}", headers=self._headers())
            if 200 <= status < 300:
                return "连接正常（目录已创建）"
            raise SyncError(f"无法写入：HTTP {status}")
        if status in (401, 403):
            raise SyncError("认证失败：坚果云请使用「应用密码」")
        raise SyncError(f"HTTP {status}")


# ---------------------------------------------------------------- S3
def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


# 粘贴密钥时常见的杂质：零宽字符、不换行空格、全角空格
_INVISIBLE = ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00a0", "\u3000")


def clean_cred(value: str) -> str:
    """清掉密钥里的空白、零宽字符、引号和「AK=/SecretKey=」这类多余前缀。

    密钥只可能是可见字符，任何空白都是粘贴带进来的，直接删掉最安全。
    """
    s = str(value or "")
    for ch in _INVISIBLE + (" ", "\t", "\r", "\n"):
        s = s.replace(ch, "")
    s = s.strip().strip("\"'“”‘’")
    low = s.lower()
    for pre in ("accesskey=", "accesskey:", "ak=", "secretkey=", "secretkey:", "sk="):
        if low.startswith(pre):
            s = s[len(pre):]
            break
    return s


def _xml_error(body: bytes) -> tuple[str, str]:
    """从 S3 的错误 XML 里取出 Code / Message。"""
    text = body[:600].decode("utf-8", "ignore")
    code = re.search(r"<Code>([^<]*)</Code>", text)
    msg = re.search(r"<Message>([^<]*)</Message>", text)
    return (code.group(1).strip() if code else "",
            msg.group(1).strip() if msg else text.strip())


class S3:
    def __init__(self, endpoint: str, region: str, bucket: str, key: str,
                 access_key: str, secret_key: str, path_style: bool = True):
        self.endpoint = endpoint.rstrip("/")
        self.region = (region or "").strip()
        self.bucket = bucket.strip().strip("/")
        self.key = key.lstrip("/")
        self.access_key = clean_cred(access_key)
        self.secret_key = clean_cred(secret_key)
        self.path_style = path_style
        self._normalize()

    def _normalize(self):
        """兼容粘贴「S3 域名」：<bucket>.s3.<region>.qiniucs.com 这类。"""
        ep = (self.endpoint or "").strip().rstrip("/")
        if ep and not ep.startswith(("http://", "https://")):
            ep = "https://" + ep
        if ep:
            parsed = urllib.parse.urlparse(ep)
            host = parsed.netloc
            m = re.match(
                r"^([a-z0-9][a-z0-9.\-]*?)\.(s3[.-][a-z0-9-]+\.(?:qiniucs\.com|amazonaws\.com))$",
                host, re.I)
            if m:
                if not self.bucket:
                    self.bucket = m.group(1)
                ep = f"{parsed.scheme}://{m.group(2).lower()}"
                parsed = urllib.parse.urlparse(ep)
            m2 = re.search(r"s3[.-]([a-z]{2}-[a-z]+-\d+)\.", parsed.netloc, re.I)
            if m2:
                self.region = m2.group(1)
            elif not self.region:
                self.region = "us-east-1"
        self.endpoint = ep
        if not self.region:
            self.region = "us-east-1"

    def _host(self) -> str:
        return urllib.parse.urlparse(self.endpoint).netloc

    def _uri(self) -> str:
        if self.path_style:
            return "/" + urllib.parse.quote(f"{self.bucket}/{self.key}")
        return "/" + urllib.parse.quote(self.key)

    def _url(self, query: str = "") -> str:
        if self.path_style:
            url = f"{self.endpoint}/{urllib.parse.quote(self.bucket)}/{urllib.parse.quote(self.key)}"
        else:
            scheme = urllib.parse.urlparse(self.endpoint).scheme
            url = f"{scheme}://{self.bucket}.{self._host()}/{urllib.parse.quote(self.key)}"
        return url + ("?" + query if query else "")

    def _check_creds(self):
        """七牛的 AK/SK 都是 40 位；长度不对直接说清楚，省得白跑一趟网络。"""
        host = (self._host() or "").lower()
        if "qiniucs.com" not in host:
            return
        bad = []
        if len(self.access_key) != 40:
            bad.append(f"Access Key 是 {len(self.access_key)} 位")
        if len(self.secret_key) != 40:
            bad.append(f"Secret Key 是 {len(self.secret_key)} 位")
        if bad:
            raise SyncError(
                "七牛云的 Access Key 和 Secret Key 都是 40 位，而你填的"
                + "、".join(bad)
                + "。请到「七牛控制台 → 密钥管理」重新复制完整密钥（复制时别只选中一部分）")

    def _sign(self, method: str, payload: bytes, query: str = "",
              uri: str | None = None) -> dict:
        if not self.endpoint.startswith(("http://", "https://")):
            raise SyncError("请先填写 Endpoint（含 http/https）")
        if not self.bucket:
            raise SyncError("请先填写 Bucket")
        if not (self.access_key and self.secret_key):
            raise SyncError("请先填写 Access Key 和 Secret Key")
        self._check_creds()
        host = self._host()
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date = now.strftime("%Y%m%d")
        payload_hash = _sha256_hex(payload)
        canonical_headers = (f"host:{host}\n"
                             f"x-amz-content-sha256:{payload_hash}\n"
                             f"x-amz-date:{amz_date}\n")
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        canonical_query = "&".join(sorted(
            f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}"
            for k, v in urllib.parse.parse_qsl(query, keep_blank_values=True)))
        canonical_request = "\n".join([
            method, self._uri() if uri is None else uri, canonical_query,
            canonical_headers, signed_headers, payload_hash])
        scope = f"{date}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256", amz_date, scope,
            _sha256_hex(canonical_request.encode("utf-8"))])
        k = _hmac(("AWS4" + self.secret_key).encode("utf-8"), date)
        k = _hmac(k, self.region)
        k = _hmac(k, "s3")
        k = _hmac(k, "aws4_request")
        sig = hmac.new(k, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        auth = (f"AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, "
                f"SignedHeaders={signed_headers}, Signature={sig}")
        return {"x-amz-date": amz_date,
                "x-amz-content-sha256": payload_hash,
                "Authorization": auth}

    def _auth_error(self, body: bytes, verb: str = "访问") -> SyncError:
        """把 S3 的错误 XML 翻成能照着改的提示。"""
        code, msg = _xml_error(body)
        if code == "InvalidAccessKeyId":
            hint = f"Access Key 只有 {len(self.access_key)} 位"
            if "qiniucs.com" in self._host():
                hint += "，七牛的标准长度是 40 位，多半是复制时开头被截掉了"
            return SyncError(f"{verb}失败：服务器不认识这个 Access Key（{hint}）")
        if code == "SignatureDoesNotMatch":
            return SyncError(f"{verb}失败：签名不匹配，检查 Secret Key 是否完整、AK/SK 有没有填反")
        if code:
            return SyncError(f"{verb}失败：{code} — {msg}")
        return SyncError(f"{verb}失败 HTTP 403（检查密钥与桶权限）")

    def pull(self) -> bytes | None:
        if not (self.endpoint and self.bucket and self.key):
            raise SyncError("S3 配置不完整")
        h = self._sign("GET", b"")
        status, body = _http("GET", self._url(), headers=h)
        if status == 404:
            return None
        if 200 <= status < 300:
            return body
        if status == 403:
            raise self._auth_error(body, "读取")
        raise SyncError(f"读取失败 HTTP {status}")

    def push(self, data: bytes):
        h = self._sign("PUT", data)
        h["Content-Type"] = "application/json"
        status, body = _http("PUT", self._url(), data=data, headers=h)
        if not (200 <= status < 300):
            if status == 403:
                raise self._auth_error(body, "上传")
            code, msg = _xml_error(body)
            raise SyncError(f"上传失败 HTTP {status} {code} {msg}".strip())

    def test(self) -> str:
        h = self._sign("GET", b"")
        status, body = _http("GET", self._url(), headers=h)
        if status == 200:
            return "连接正常"
        if status == 404:
            return "连接正常（桶里还没有 state.json）"
        if status == 403:
            raise self._auth_error(body, "连接")
        raise SyncError(f"HTTP {status}")

    def list_keys(self, prefix: str = "") -> list[tuple[str, int, str]]:
        """列出桶内对象 (Key, 字节数, 修改时间)，排障用。"""
        if not (self.endpoint and self.bucket):
            raise SyncError("S3 配置不完整")
        q = urllib.parse.urlencode({"prefix": prefix})
        if self.path_style:
            uri = "/" + urllib.parse.quote(self.bucket) + "/"
            url = f"{self.endpoint}/{urllib.parse.quote(self.bucket)}/?{q}"
        else:
            uri = "/"
            scheme = urllib.parse.urlparse(self.endpoint).scheme
            url = f"{scheme}://{self.bucket}.{self._host()}/?{q}"
        status, body = _http("GET", url, headers=self._sign("GET", b"", q, uri))
        if status == 403:
            raise self._auth_error(body, "列举")
        if not (200 <= status < 300):
            code, msg = _xml_error(body)
            raise SyncError(f"列举失败 HTTP {status} {code} {msg}".strip())
        text = body.decode("utf-8", "ignore")
        out = []
        for m in re.finditer(r"<Contents>(.*?)</Contents>", text, re.S):
            blk = m.group(1)
            k = re.search(r"<Key>(.*?)</Key>", blk, re.S)
            sz = re.search(r"<Size>(\d+)</Size>", blk)
            mt = re.search(r"<LastModified>(.*?)</LastModified>", blk)
            if k:
                out.append((k.group(1), int(sz.group(1)) if sz else 0,
                            mt.group(1) if mt else ""))
        return out


# ---------------------------------------------------------------- 局域网
class LanPeer:
    """把对方当作一个 HTTP 端点：GET/PUT /state。"""

    def __init__(self, base_url: str, token: str = ""):
        self.base = base_url.strip().rstrip("/")
        self.token = token.strip()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["X-Sync-Token"] = self.token
        return h

    def pull(self) -> bytes | None:
        if not self.base.startswith(("http://", "https://")):
            raise SyncError("请填写完整地址（如 http://192.168.1.5:8765）")
        status, body = _http("GET", self.base + "/state", headers=self._headers())
        if status == 404:
            return None
        if 200 <= status < 300:
            return body
        raise SyncError(f"读取失败 HTTP {status}")

    def push(self, data: bytes):
        status, _ = _http("PUT", self.base + "/state", data=data, headers=self._headers())
        if not (200 <= status < 300):
            raise SyncError(f"上传失败 HTTP {status}")

    def test(self) -> str:
        status, _ = _http("GET", self.base + "/ping", headers=self._headers())
        if 200 <= status < 300:
            return "连接正常"
        raise SyncError(f"HTTP {status}")


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class LanServer:
    """内置 HTTP 服务：GET/PUT /state，带校验口令。"""

    def __init__(self, store, token: str, port: int = 8765):
        self.store = store
        self.token = token
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self) -> str:
        if self.httpd:
            return self.url()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _ok(self, body: bytes, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/ping":
                    return self._ok(b'{"ok":true}')
                if self.path != "/state":
                    return self._ok(b"{}", 404)
                if outer.token and self.headers.get("X-Sync-Token") != outer.token:
                    return self._ok(b'{"error":"token"}', 401)
                return self._ok(outer.store.export_bytes(bump=False))

            def do_PUT(self):
                if self.path != "/state":
                    return self._ok(b"{}", 404)
                if outer.token and self.headers.get("X-Sync-Token") != outer.token:
                    return self._ok(b'{"error":"token"}', 401)
                n = int(self.headers.get("Content-Length") or 0)
                data = self.rfile.read(n)
                ok, msg = outer.store.import_bytes(data)
                return self._ok(json.dumps({"ok": ok, "msg": msg}).encode(), 200 if ok else 400)

        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self.url()

    def url(self) -> str:
        return f"http://{_lan_ip()}:{self.port}"

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        self.httpd = None
        self.thread = None


# ---------------------------------------------------------------- 统一入口
def client_from(cfg: dict):
    kind = (cfg or {}).get("provider", "lan")
    if kind == "webdav":
        c = cfg.get("webdav") or {}
        return WebDAV(c.get("url", ""), c.get("user", ""), c.get("password", ""))
    if kind == "s3":
        c = cfg.get("s3") or {}
        return S3(c.get("endpoint", ""), c.get("region", ""), c.get("bucket", ""),
                  c.get("key", "flocard/state.json"), c.get("access", ""),
                  c.get("secret", ""), bool(c.get("path_style", True)))
    c = cfg.get("lan") or {}
    return LanPeer(c.get("url", ""), c.get("token", ""))


class SyncConflict(Exception):
    """本地和云端都有改动，需要用户选方向。"""

    def __init__(self, local_at: int, remote_at: int,
                 local_cards: int = 0, remote_cards: int = 0):
        self.local_at = local_at
        self.remote_at = remote_at
        self.local_cards = local_cards
        self.remote_cards = remote_cards
        super().__init__("本地和云端都有修改")


def _remote(store, client):
    data = client.pull()
    if data is None:
        return None, 0
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception as e:
        raise SyncError(f"云端数据格式不对：{e}")
    return data, int(obj.get("updated_at") or 0)


def _base(store) -> tuple[int, int]:
    st = store.state.setdefault("settings", {})
    return int(st.get("sync_base_local") or 0), int(st.get("sync_base_remote") or 0)


def _mark(store, local_at: int, remote_at: int, provider: str = ""):
    st = store.state.setdefault("settings", {})
    st["last_sync"] = int(time.time() * 1000)
    st["last_sync_provider"] = provider or st.get("last_sync_provider") or ""
    st["sync_base_remote"] = int(remote_at)
    store.save()                       # 这次会刷新 updated_at
    st["sync_base_local"] = store.updated_at()
    store.save(bump=False)             # 只记基线，不再改时间戳


def plan_sync(store, cfg: dict) -> dict:
    """返回 {action, local, remote}；action ∈ upload/download/conflict/none。"""
    client = client_from(cfg)
    data, r_at = _remote(store, client)
    l_at = store.updated_at()
    base_local, base_remote = _base(store)
    remote_cards = 0
    if data is not None:
        try:
            remote_cards = len(json.loads(data.decode("utf-8")).get("cards") or [])
        except Exception:
            remote_cards = 0
    local_cards = len(store.cards)
    if data is None:
        return {"action": "upload", "local": l_at, "remote": 0, "data": None,
                "local_cards": local_cards, "remote_cards": 0}
    if base_local == 0 and base_remote == 0:
        # 首次同步：内容一致就当已同步，否则让用户选方向。
        # 比较解析后的内容而不是原始字节，避免新旧版本 JSON 缩进不同被误判为冲突。
        try:
            remote_obj = json.loads(data.decode("utf-8"))
            local_obj = json.loads(store.export_bytes().decode("utf-8"))
            remote_obj.pop("updated_at", None)
            local_obj.pop("updated_at", None)
            same = remote_obj == local_obj
        except Exception:
            same = False
        if same:
            return {"action": "none", "local": l_at, "remote": r_at, "data": data}
        return {"action": "conflict", "local": l_at, "remote": r_at, "data": data,
                "local_cards": local_cards, "remote_cards": remote_cards}
    local_changed = l_at > base_local
    remote_changed = r_at > base_remote
    if local_changed and remote_changed:
        action = "conflict"
    elif local_changed:
        action = "upload"
    elif remote_changed:
        action = "download"
    else:
        action = "none"
    return {"action": action, "local": l_at, "remote": r_at, "data": data,
            "local_cards": local_cards, "remote_cards": remote_cards}


def do_sync(store, cfg: dict, mode: str = "auto") -> str:
    """mode: auto（自动判断）/ push（强制上传）/ pull（强制下载）。"""
    client = client_from(cfg)
    mode = (mode or "auto").strip().lower()
    if mode in ("", "both", "sync"):        # 「同步」按钮传的是 both，等同于 auto
        mode = "auto"

    if mode == "auto":
        p = plan_sync(store, cfg)
        act = p["action"]
        if act == "conflict":
            raise SyncConflict(p["local"], p["remote"],
                               p.get("local_cards", 0), p.get("remote_cards", 0))
        if act == "none":
            return "没有需要同步的更改"
        mode = "push" if act == "upload" else "pull"

    if mode == "push":
        data = store.export_bytes()
        client.push(data)
        l_at = store.updated_at()
        remote_at = int(json.loads(data.decode("utf-8")).get("updated_at") or l_at)
        _mark(store, l_at, remote_at, (cfg or {}).get("provider") or "")
        return "已上传本地"

    if mode == "pull":
        data, r_at = _remote(store, client)
        if data is None:
            return "云端还没有数据"
        ok, msg = store.import_bytes(data, force=True)
        if not ok:
            raise SyncError(msg)
        _mark(store, store.updated_at(), r_at, (cfg or {}).get("provider") or "")
        return "已下载云端"

    raise SyncError(f"未知的同步方式：{mode}")


def fmt_ts(ms: int) -> str:
    if not ms:
        return "—"
    return time.strftime("%m-%d %H:%M", time.localtime(ms / 1000))
