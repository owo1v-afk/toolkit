import sys
import os
import io
import shutil
import json
import zipfile
import traceback
import urllib.request

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
}

INSTALL_DIR = None
_skip = set()


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
            _install(stripped.split()[2], echo=True)
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


def _pypi_wheel_url(pkg):
    with urllib.request.urlopen("https://pypi.org/pypi/%s/json" % pkg, timeout=30) as r:
        data = json.load(r)
    version = data["info"]["version"]
    with urllib.request.urlopen("https://pypi.org/pypi/%s/%s/json" % (pkg, version), timeout=30) as r:
        data = json.load(r)
    for u in data["urls"]:
        if u["filename"].endswith("-none-any.whl"):
            return u["url"]
    return None


def _install(pkg, echo=True):
    pkg = PKG_ALIASES.get(pkg, pkg)
    if echo:
        TerminalIO.append("[автоустановка] скачиваю %s с PyPI…\n" % pkg)
    try:
        url = _pypi_wheel_url(pkg)
        if not url:
            TerminalIO.append(
                "[автоустановка] %s: универсального колеса нет (нативное расширение?)\n" % pkg
            )
            return False
        dest = os.path.join(INSTALL_DIR, pkg)
        tmp = dest + ".tmp"
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        req = urllib.request.Request(url, headers={"User-Agent": "toolkit-android/1.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            blob = resp.read()
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
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        os.replace(tmp, dest)
        _skip.discard(pkg)
        if INSTALL_DIR not in sys.path:
            sys.path.insert(0, INSTALL_DIR)
        if echo:
            TerminalIO.append("[автоустановка] %s установлен ✓\n" % pkg)
        return True
    except BaseException as e:
        if echo:
            TerminalIO.append("[автоустановка] %s: ошибка: %s\n" % (pkg, e))
        return False


class AutoInstallFinder(object):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in sys.modules:
            return None
        top = fullname.split(".")[0]
        pkg = PKG_ALIASES.get(top, top)
        if pkg in _skip or os.path.isdir(os.path.join(INSTALL_DIR, pkg)):
            return None
        _skip.add(pkg)
        _install(pkg, echo=True)
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
