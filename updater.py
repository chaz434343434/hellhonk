"""Self-updater: checks the latest GitHub release, downloads the new exe, swaps it in and restarts.

Only active in the packaged exe. Windows lets a running exe be renamed, so the swap is:
  HellHonk.exe -> HellHonk.exe.old,  HellHonk.exe.new -> HellHonk.exe,  launch, exit.
The .old file is deleted on the next start.
"""
import json
import os
import subprocess
import sys
import threading
import urllib.request

from version import APP_VERSION, EXE_NAME, REPO

API = "https://api.github.com/repos/%s/releases/latest" % REPO
UA = {"User-Agent": "HellHonk-updater", "Accept": "application/vnd.github+json"}


def frozen():
    return bool(getattr(sys, "frozen", False))


def parse(v):
    out = []
    for part in str(v).lstrip("vV").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def cleanup_old():
    if frozen():
        try:
            os.remove(sys.executable + ".old")
        except OSError:
            pass


class Updater:
    def __init__(self):
        self.state = "dev" if not frozen() else "idle"   # dev|idle|checking|none|downloading|ready|error
        self.latest = None
        self.url = None
        self.progress = 0.0
        self.error = ""

    # ---------------------------------------------------------------- check
    def check_async(self):
        if self.state == "dev":
            return
        threading.Thread(target=self._check_and_fetch, daemon=True).start()

    def _check_and_fetch(self):
        try:
            self.state = "checking"
            fake = os.environ.get("HELLHONK_FAKE_LATEST")   # "9.9.9|file:///C:/x/HellHonk.exe" for testing
            if fake:
                self.latest, self.url = fake.split("|", 1)
            else:
                with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=8) as r:
                    data = json.load(r)
                self.latest = data.get("tag_name", "")
                self.url = next((a["browser_download_url"] for a in data.get("assets", [])
                                 if a.get("name") == EXE_NAME), None)
            if not self.url or parse(self.latest) <= parse(APP_VERSION):
                self.state = "none"
                return
            self._download()
        except Exception as ex:   # no internet, rate limit, etc. - just keep playing
            self.state, self.error = "error", str(ex)[:120]

    def _download(self):
        self.state = "downloading"
        target = sys.executable + ".new"
        with urllib.request.urlopen(urllib.request.Request(self.url, headers={"User-Agent": UA["User-Agent"]}),
                                    timeout=30) as r, open(target, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    self.progress = got / total
        with open(target, "rb") as f:
            head = f.read(2)
        if head != b"MZ" or os.path.getsize(target) < 1_000_000 or (total and got != total):
            os.remove(target)
            raise IOError("downloaded file is not a valid game exe")
        self.state = "ready"

    # ---------------------------------------------------------------- apply
    def apply_and_restart(self, extra_args=()):
        exe = sys.executable
        new, old = exe + ".new", exe + ".old"
        try:
            if os.path.exists(old):
                os.remove(old)
        except OSError:
            pass
        os.replace(exe, old)
        os.replace(new, exe)
        env = dict(os.environ)
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"    # make the new exe unpack itself fresh
        env.pop("HELLHONK_FAKE_LATEST", None)
        subprocess.Popen([exe] + list(extra_args), env=env, close_fds=True)

    def status_line(self):
        if self.state == "downloading":
            return "Downloading update %s... %d%%" % (self.latest, int(self.progress * 100))
        if self.state == "ready":
            return "Update %s ready - restarting..." % self.latest
        if self.state == "checking":
            return "Checking for updates..."
        return ""
