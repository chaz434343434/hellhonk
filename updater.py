"""Self-updater: checks the latest GitHub release, downloads the new build, swaps it in and restarts.

Only active in packaged builds (PyInstaller).
  Windows: HellHonk.exe -> HellHonk.exe.old, HellHonk.exe.new -> HellHonk.exe (a running exe can be renamed).
  macOS:   HellHonk.app -> HellHonk.app.old, freshly unzipped HellHonk.app moves into place, `open` it.
Leftover .old files/bundles are deleted on the next start.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import urllib.request

from version import APP_VERSION, EXE_NAME, REPO

API = "https://api.github.com/repos/%s/releases/latest" % REPO
UA = {"User-Agent": "HellHonk-updater", "Accept": "application/vnd.github+json"}
IS_MAC = sys.platform == "darwin"


def frozen():
    return bool(getattr(sys, "frozen", False))


def parse(v):
    out = []
    for part in str(v).lstrip("vV").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def asset_name():
    if IS_MAC:
        return "HellHonk-mac-%s.zip" % ("arm64" if platform.machine() == "arm64" else "intel")
    return EXE_NAME


def mac_bundle():
    """/path/HellHonk.app when running from inside the bundle, else None."""
    p = os.path.abspath(sys.executable)
    marker = ".app/Contents/MacOS/"
    i = p.find(marker)
    return p[:i + 4] if i >= 0 else None


def cleanup_old():
    if not frozen():
        return
    try:
        if IS_MAC:
            b = mac_bundle()
            if b:
                shutil.rmtree(b + ".old", ignore_errors=True)
                shutil.rmtree(os.path.join(os.path.dirname(b), ".hellhonk_update"), ignore_errors=True)
        else:
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
        if self.state != "dev" and IS_MAC:
            b = mac_bundle()
            if not b:
                self.state = "dev"
            elif "/AppTranslocation/" in b:
                # macOS runs un-moved downloads from a read-only copy; we can't replace ourselves there
                self.state, self.error = "error", "Move HellHonk to Applications to get updates"

    # ---------------------------------------------------------------- check
    def check_async(self):
        if self.state != "idle":
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
                                 if a.get("name") == asset_name()), None)
            if not self.url or parse(self.latest) <= parse(APP_VERSION):
                self.state = "none"
                return
            self._download()
        except Exception as ex:   # no internet, rate limit, etc. - just keep playing
            self.state, self.error = "error", str(ex)[:120]

    def _fetch(self, target):
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
        if total and got != total:
            raise IOError("download was cut short")

    def _download(self):
        self.state = "downloading"
        if IS_MAC:
            bundle = mac_bundle()
            work = os.path.join(os.path.dirname(bundle), ".hellhonk_update")
            shutil.rmtree(work, ignore_errors=True)
            os.makedirs(work)
            z = os.path.join(work, "update.zip")
            self._fetch(z)
            with open(z, "rb") as f:
                if f.read(2) != b"PK":
                    raise IOError("downloaded file is not a zip")
            # ditto keeps permissions, symlinks and the code signature intact (zipfile does not)
            subprocess.check_call(["ditto", "-x", "-k", z, work])
            new = os.path.join(work, "HellHonk.app")
            if not os.path.isfile(os.path.join(new, "Contents", "MacOS", "HellHonk")):
                raise IOError("update zip has no HellHonk.app")
            subprocess.call(["xattr", "-dr", "com.apple.quarantine", new])
            self.new_bundle = new
        else:
            target = sys.executable + ".new"
            self._fetch(target)
            with open(target, "rb") as f:
                head = f.read(2)
            if head != b"MZ" or os.path.getsize(target) < 1_000_000:
                os.remove(target)
                raise IOError("downloaded file is not a valid game exe")
        self.state = "ready"

    # ---------------------------------------------------------------- apply
    def apply_and_restart(self, extra_args=()):
        env = dict(os.environ)
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"    # make the new build unpack itself fresh
        env.pop("HELLHONK_FAKE_LATEST", None)
        if IS_MAC:
            bundle = mac_bundle()
            old = bundle + ".old"
            shutil.rmtree(old, ignore_errors=True)
            os.rename(bundle, old)
            shutil.move(self.new_bundle, bundle)
            cmd = ["open", "-n", bundle] + (["--args"] + list(extra_args) if extra_args else [])
            subprocess.Popen(cmd, env=env, close_fds=True)
            return
        exe = sys.executable
        new, old = exe + ".new", exe + ".old"
        try:
            if os.path.exists(old):
                os.remove(old)
        except OSError:
            pass
        os.replace(exe, old)
        os.replace(new, exe)
        subprocess.Popen([exe] + list(extra_args), env=env, close_fds=True)

    def status_line(self):
        if self.state == "downloading":
            return "Downloading update %s... %d%%" % (self.latest, int(self.progress * 100))
        if self.state == "ready":
            return "Update %s ready - restarting..." % self.latest
        if self.state == "checking":
            return "Checking for updates..."
        if self.state == "error" and self.error.startswith("Move HellHonk"):
            return self.error
        return ""
