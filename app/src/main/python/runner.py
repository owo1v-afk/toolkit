import sys
import os
import io
import re
import shutil
import json
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
        if isinstance(s, bytes):
            s = s.decode("utf-8", "replace")
        TerminalIO.append(str(s))

    def flush(self):
        pass

    def readline(self):
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


def _pypi_json_wheel(pkg, version):
    if version is None:
        with _open(PYPY_JSON % pkg, 30) as r:
            data = json.load(r)
        version = data["info"]["version"]
    with _open(PYPY_VERSION_JSON % (pkg, version), 30) as r:
        data = json.load(r)
    for u in data["urls"]:
        if u["filename"].endswith("-none-any.whl"):
            return u["url"]
    return None


def _mirror_wheel(pkg, base, version):
    url = base % pkg
    with _open(url, 30) as r:
        html = r.read().decode("utf-8", "replace")
    for m in re.finditer(r'href="([^"]+-none-any\.whl)"', html):
        href = m.group(1)
        fname = href.rsplit("/", 1)[-1]
        if version and not fname.startswith("%s-%s-" % (pkg, version)):
            continue
        return urllib.parse.urljoin(url, href)
    return None


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
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            blob += chunk
            read += len(chunk)
            if total:
                TerminalIO.progress(pkg, max(0, min(100, int(read * 100 / total))))
    return blob


def _extract(blob, dest):
    tmp = dest + ".tmp"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if name.startswith(".") or ".dist-info" in name:
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


def _install(pkg, echo=True, version=None):
    pkg = PKG_ALIASES.get(pkg, pkg)
    if echo:
        TerminalIO.append("[автоустановка] скачиваю %s…\n" % pkg)
    try:
        url, errors = _wheel_url(pkg, version)
        if not url:
            detail = "; ".join(errors) if errors else "источники недоступны"
            TerminalIO.append(
                "[автоустановка] %s: не нашлось подходящего колеса (%s)\n" % (pkg, detail)
            )
            TerminalIO.progress(pkg, -1)
            return False
        blob = _download(url, pkg)
        _extract(blob, INSTALL_DIR)
        _skip.discard(pkg)
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
        blob = _download(url, name)
        _extract(blob, INSTALL_DIR)
        _skip.discard(name)
        TerminalIO.progress(name, -1)
        TerminalIO.append("[автоустановка] %s установлен ✓\n" % name)
    except BaseException as e:
        TerminalIO.progress(name, -1)
        TerminalIO.append("[автоустановка] %s: ошибка: %s\n" % (name, e))


class AutoInstallFinder(object):
    def _available(self, fullname):
        try:
            sys.meta_path.remove(self)
            try:
                spec = importlib.util.find_spec(fullname)
            finally:
                sys.meta_path.insert(0, self)
            return spec is not None
        except BaseException:
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
        if pkg in _skip or os.path.isdir(os.path.join(INSTALL_DIR, pkg)):
            return None
        _skip.add(pkg)
        if not _install(pkg, echo=True):
            return None
        try:
            return importlib.machinery.PathFinder.find_spec(fullname, [INSTALL_DIR])
        except BaseException:
            return None


def run(path, args_str=""):
    global INSTALL_DIR
    INSTALL_DIR = os.path.join(os.environ.get("HOME", "/data/data/com.toolkit.app/files"), "pymods")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    if INSTALL_DIR not in sys.path:
        sys.path.insert(0, INSTALL_DIR)
    sys.meta_path.insert(0, AutoInstallFinder())
    sys.stdin = Stream()
    sys.stdout = Stream()
    sys.stderr = Stream()
    sys.argv = [path] + ([a for a in args_str.split("\0") if a] if args_str else [])
    if not os.path.isfile(path):
        TerminalIO.append("[ошибка] файл не найден: %s\n" % path)
        TerminalIO.finished()
        return
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
