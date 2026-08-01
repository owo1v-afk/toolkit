import sys
import traceback
import os

from java import jclass

TerminalIO = jclass("com.toolkit.app.TerminalIO")


class Stream(object):
    def write(self, s):
        if isinstance(s, bytes):
            s = s.decode("utf-8", "replace")
        TerminalIO.append(str(s))

    def flush(self):
        pass

    def readline(self):
        return TerminalIO.readInput() + "\n"

    def read(self, n=-1):
        return TerminalIO.readInput() + "\n"

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


def run(path, args_str=""):
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
