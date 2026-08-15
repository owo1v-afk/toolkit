import sys
import os
import io
import re
import shutil
import json
import warnings
import zipfile
import traceback
import urllib.request
import urllib.parse
import urllib.error
import importlib.util
import importlib.machinery

from java import jclass

TerminalIO = jclass("com.toolkit.app.TerminalIO")

PKG_ALIASES = {
    "bs4": "beautifulsoup4",
    "PIL": "pillow",
    "yaml": "pyyaml",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "Crypto": "pycryptodome",
    "serial": "pyserial",
    "socks": "pysocks",
    "jwt": "pyjwt",
    "flask": "flask",
}

PYPY_JSON = "https://pypi.org/pypi/%s/json"
PYPY_VERSION_JSON = "https://pypi.org/pypi/%s/%s/json"
MIRRORS = [
    "https://mirrors.aliyun.com/pypi/simple/%s/",
    "https://mirrors.cloud.tencent.com/pypi/simple/%s/",
    "https://pypi.tuna.tsinghua.edu.cn/simple/%s/",
    "https://repo.huaweicloud.com/repository/pypi/simple/%s/",
]

PLATFORM_STDLIB = {
    "winreg", "_winapi", "msvcrt", "_msi", "winsound", "nt", "nturl2path",
    "macpath", "EasyDialogs", "ic", "macostools", "clr", "_scproxy",
    "pty", "termios", "fcntl", "pwd", "grp", "spwd", "crypt", "nis",
    "readline", "curses", "tkinter", "turtle", "dbm", "tty", "select",
}

INSTALL_DIR = None
_skip = set()


def _open(url, timeout):
    try:
        return urllib.request.urlopen(url, timeout=timeout)
    except urllib.error.HTTPError as e:
        e.close()
        raise


class Stream(object):
    def write(self, s):
        if TerminalIO.cancelled:
            raise SystemExit("(остановлено пользователем)")
        if isinstance(s, bytes):
            s = s.decode("utf-8", "replace")
        TerminalIO.append(str(s))

    def flush(self):
        pass

    def readline(self):
        if TerminalIO.cancelled:
            raise SystemExit("(остановлено пользователем)")
        line = TerminalIO.readInput()
        stripped = line.strip()
        if stripped.startswith("pip install "):
            _run_pip(stripped[12:].strip())
            return "\n"
        return line + "\n"

    def read(self, n=-1):
        return self.readline()

    def readlines(self, hint=-1):
        while True:
            line = self.readline()
            if not line.strip():
                break
            yield line

    def isatty(self):
        return True

    def fileno(self):
        raise OSError("no file descriptor")

    def close(self):
        pass


def _run_pip(arg):
    if arg.startswith(("http://", "https://")):
        _install_url(arg)
        return
    version = None
    if "==" in arg:
        arg, version = arg.split("==", 1)
    _install(arg, echo=True, version=version)


def _wheel_score(filename):
    if filename.endswith("-none-any.whl"):
        return 0
    m = re.search(r"-cp314-(?:cp314|abi3|none)-android_\d+_(arm64_v8a|x86_64)\.whl$", filename)
    if not m:
        return None
    return 1 if m.group(1) == "arm64_v8a" else 2


def _wheel_version(pkg, filename):
    base = pkg.replace("-", "_").lower()
    rest = filename[len(base) + 1:-4]
    m = re.match(r"(\d+(?:\.\d+)*)", rest)
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split("."))


def _pick_wheel(pkg, candidates):
    best = None
    best_key = None
    for filename, url in candidates:
        score = _wheel_score(filename)
        if score is None:
            continue
        version = _wheel_version(pkg, filename)
        if version is None:
            continue
        key = (version, score)
        if (
            best_key is None
            or key[0] > best_key[0]
            or (key[0] == best_key[0] and key[1] < best_key[1])
        ):
            best, best_key = url, key
    return best


def _pypi_json_wheel(pkg, version):
    if version is None:
        with _open(PYPY_JSON % pkg, 30) as r:
            data = json.load(r)
        version = data["info"]["version"]
    with _open(PYPY_VERSION_JSON % (pkg, version), 30) as r:
        data = json.load(r)
    return _pick_wheel(pkg, [(u["filename"], u["url"]) for u in data["urls"]])


def _mirror_wheel(pkg, base, version):
    url = base % pkg
    with _open(url, 30) as r:
        html = r.read().decode("utf-8", "replace")
    candidates = []
    for m in re.finditer(r'href="([^"]+)"', html):
        href = m.group(1)
        fname = href.split("#", 1)[0].rsplit("/", 1)[-1]
        if not fname.endswith(".whl"):
            continue
        if version and not fname.startswith(
            "%s-%s-" % (pkg.replace("-", "_").lower(), version)
        ):
            continue
        candidates.append((fname, urllib.parse.urljoin(url, href.split("#", 1)[0])))
    return _pick_wheel(pkg, candidates)


def _wheel_url(pkg, version):
    errors = []
    try:
        url = _pypi_json_wheel(pkg, version)
        if url:
            return url, errors
    except BaseException as e:
        errors.append("pypi.org: %s" % e)
    for base in MIRRORS:
        host = urllib.parse.urlparse(base).netloc
        try:
            url = _mirror_wheel(pkg, base, version)
            if url:
                return url, errors
        except BaseException as e:
            errors.append("%s: %s" % (host, e))
    return None, errors


def _download(url, pkg):
    req = urllib.request.Request(url, headers={"User-Agent": "toolkit-android/1.0"})
    with _open(req, 120) as resp:
        total = resp.headers.get("Content-Length")
        total = int(total) if total else 0
        blob = b""
        read = 0
        last = -1
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            blob += chunk
            read += len(chunk)
            pct = 0 if not total else max(0, min(100, int(read * 100 / total)))
            if pct != last:
                last = pct
                TerminalIO.progress(pkg, pct)
    return blob


def _extract(blob, dest):
    tmp = dest + ".tmp"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if name.startswith("."):
                continue
            target = os.path.join(tmp, name)
            if name.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(name) as src, open(target, "wb") as dst:
                dst.write(src.read())
    for entry in os.listdir(tmp):
        src = os.path.join(tmp, entry)
        dst = os.path.join(dest, entry)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.move(src, dst)
        else:
            if os.path.isfile(dst):
                os.remove(dst)
            shutil.move(src, dst)
    shutil.rmtree(tmp)
    if INSTALL_DIR not in sys.path:
        sys.path.insert(0, INSTALL_DIR)


def _version_tuple(v):
    m = re.match(r"(\d+(?:\.\d+)*)", v)
    if not m:
        return None
    return tuple(int(x) for x in m.group(1).split("."))


def _parse_req(req):
    parts = re.split(r";", req)
    if "extra" in (parts[1] if len(parts) > 1 else ""):
        return None
    req = parts[0].strip()
    req = re.sub(r"\[[^\]]*\]", "", req)
    req_parts = [p.strip() for p in req.split(",")]
    name = re.split(r"[<>=~!]", req_parts[0])[0].strip()
    if not name:
        return None
    constraints = []
    for p in req_parts[1:]:
        m = re.match(r"(>=|<=|==|!=|>|<|~=)\s*(\S+)", p)
        if not m:
            continue
        op, val = m.group(1), m.group(2)
        if op == "~=":
            vt = _version_tuple(val)
            if vt:
                constraints.append((">=", val))
                if len(vt) == 1:
                    constraints.append(("<", "%d" % (vt[0] + 1)))
                else:
                    constraints.append(("<", "%d.%d" % (vt[0], vt[1] + 1)))
            continue
        constraints.append((op, val))
    return name, constraints


def _satisfies(vt, constraints):
    for op, val in constraints:
        vt2 = _version_tuple(val)
        if vt2 is None:
            continue
        if op == ">=" and not vt >= vt2:
            return False
        if op == ">" and not vt > vt2:
            return False
        if op == "<=" and not vt <= vt2:
            return False
        if op == "<" and not vt < vt2:
            return False
        if op == "==" and not vt == vt2:
            return False
        if op == "!=" and vt == vt2:
            return False
    return True


def _deps_of(pkg):
    try:
        with _open(PYPY_JSON % pkg, 30) as r:
            data = json.load(r)
    except BaseException:
        return []
    deps = []
    seen = set()
    for req in data.get("info", {}).get("requires_dist") or []:
        parsed = _parse_req(req)
        if not parsed:
            continue
        name, constraints = parsed
        if name in PLATFORM_STDLIB or name.startswith("_") or name == pkg or name in seen:
            continue
        seen.add(name)
        try:
            with _open(PYPY_JSON % name, 30) as r:
                dep_data = json.load(r)
        except BaseException:
            continue
        best = None
        best_vt = None
        for v in (dep_data.get("releases") or {}).keys():
            vt = _version_tuple(v)
            if vt is None or not _satisfies(vt, constraints):
                continue
            if best_vt is None or vt > best_vt:
                best, best_vt = v, vt
        deps.append((name, best))
    return deps


def _install(pkg, echo=True, version=None, _depth=0):
    pkg = PKG_ALIASES.get(pkg, pkg)
    if echo:
        TerminalIO.append("[автоустановка] скачиваю %s…\n" % pkg)
    try:
        TerminalIO.progress(pkg, 0)
        url, errors = _wheel_url(pkg, version)
        if not url:
            if errors:
                detail = "источники недоступны: " + "; ".join(errors)
            else:
                detail = ("у пакета нет колеса для Android: нужен чистый python "
                          "или готовое колесо cp314-android (arm64)")
            TerminalIO.append(
                "[автоустановка] %s: не нашлось подходящего колеса (%s)\n" % (pkg, detail)
            )
            TerminalIO.progress(pkg, -1)
            return False
        blob = _download(url, pkg)
        _extract(blob, INSTALL_DIR)
        if _depth < 4:
            for dep, dep_version in _deps_of(pkg):
                if dep in _skip or dep == pkg:
                    continue
                if dep in sys.modules:
                    continue
                if os.path.isdir(os.path.join(INSTALL_DIR, dep)) or os.path.isfile(
                    os.path.join(INSTALL_DIR, dep + ".py")
                ):
                    continue
                _skip.add(dep)
                _install(dep, echo=echo, version=dep_version, _depth=_depth + 1)
        TerminalIO.progress(pkg, -1)
        if echo:
            TerminalIO.append("[автоустановка] %s установлен ✓\n" % pkg)
        return True
    except BaseException as e:
        TerminalIO.progress(pkg, -1)
        if echo:
            TerminalIO.append("[автоустановка] %s: ошибка: %s\n" % (pkg, e))
        return False


def _install_url(url):
    fname = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
    name = re.sub(r"-(\d.*)$", "", fname) or "pkg"
    TerminalIO.append("[автоустановка] скачиваю %s по прямой ссылке…\n" % name)
    try:
        TerminalIO.progress(name, 0)
        blob = _download(url, name)
        _extract(blob, INSTALL_DIR)
        _skip.discard(name)
        TerminalIO.progress(name, -1)
        TerminalIO.append("[автоустановка] %s установлен ✓\n" % name)
    except BaseException as e:
        TerminalIO.progress(name, -1)
        TerminalIO.append("[автоустановка] %s: ошибка: %s\n" % (name, e))


_checking = False


class AutoInstallFinder(object):
    def _available(self, fullname):
        global _checking
        if _checking:
            return True
        _checking = True
        try:
            return importlib.util.find_spec(fullname) is not None
        except BaseException:
            return False
        finally:
            _checking = False

    def _top_ok(self, topdir):
        try:
            if os.path.isfile(os.path.join(topdir, "__init__.py")):
                return True
            for entry in os.listdir(topdir):
                if entry.endswith((".py", ".so")):
                    return True
        except OSError:
            return False
        return False

    def find_spec(self, fullname, path=None, target=None):
        if fullname in sys.modules:
            return None
        top = fullname.split(".")[0]
        broken = os.path.join(INSTALL_DIR, top, top)
        if os.path.isdir(broken):
            shutil.rmtree(os.path.join(INSTALL_DIR, top))
            _skip.discard(top)
        if self._available(fullname):
            return None
        if top in PLATFORM_STDLIB or top.startswith("_"):
            return None
        pkg = PKG_ALIASES.get(top, top)
        if pkg in _skip:
            return None
        topdir = os.path.join(INSTALL_DIR, pkg)
        if os.path.isdir(topdir):
            if self._top_ok(topdir):
                return None
            shutil.rmtree(topdir, ignore_errors=True)
            _skip.discard(pkg)
        _skip.add(pkg)
        if not _install(pkg, echo=True):
            return None
        try:
            return importlib.machinery.PathFinder.find_spec(fullname, [INSTALL_DIR])
        except BaseException:
            return None


def run(path, args_str=""):
    global INSTALL_DIR, _skip
    INSTALL_DIR = os.path.join(os.environ.get("HOME", "/data/data/com.toolkit.app/files"), "pymods")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    if INSTALL_DIR not in sys.path:
        sys.path.insert(0, INSTALL_DIR)
    if not any(isinstance(f, AutoInstallFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, AutoInstallFinder())
    _skip = set()
    TerminalIO.reset()
    warnings.simplefilter("ignore", ResourceWarning)
    sys.stdin = Stream()
    sys.stdout = Stream()
    sys.stderr = Stream()
    sys.argv = [path] + ([a for a in args_str.split("\0") if a] if args_str else [])
    if not os.path.isfile(path):
        TerminalIO.append("[ошибка] файл не найден: %s\n" % path)
        TerminalIO.finished()
        return
    try:
        os.chdir(os.path.dirname(path) or os.getcwd())
    except BaseException:
        pass
    try:
        with open(path, "rb") as f:
            code = compile(f.read(), path, "exec")
        exec(code, {"__name__": "__main__", "__file__": path, "__builtins__": __builtins__})
    except SystemExit:
        pass
    except BaseException:
        traceback.print_exc()
    finally:
        TerminalIO.append("\n[процесс завершен]\n")
        TerminalIO.finished()
