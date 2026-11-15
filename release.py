"""Publish a new HONK version that everyone's game auto-updates to.

    py -3.9 release.py 1.0.1 "Added passive regen"

Steps: bump version.py -> self-test (must pass) -> build exe -> self-test the exe ->
git commit + tag + push -> GitHub release with HellHonk.exe attached.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, **kw):
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=HERE, **kw)


def main():
    if len(sys.argv) < 3 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit('usage: py -3.9 release.py 1.2.3 "release notes"')
    ver, notes = sys.argv[1], sys.argv[2]
    sys.path.insert(0, HERE)
    import updater
    from version import APP_VERSION
    if updater.parse(ver) <= updater.parse(APP_VERSION):
        sys.exit("new version %s must be higher than current %s" % (ver, APP_VERSION))

    vpath = os.path.join(HERE, "version.py")
    with open(vpath) as f:
        src = f.read()
    with open(vpath, "w") as f:
        f.write(re.sub(r'APP_VERSION = "[^"]*"', 'APP_VERSION = "%s"' % ver, src))

    out = tempfile.mkdtemp(prefix="hellhonk_release_")
    run([sys.executable, "-W", "ignore", "hellhonk.py", "--selftest", os.path.join(out, "src")])
    run([sys.executable, "-W", "ignore", "build.py"])
    exe = os.path.join(HERE, "dist", "HellHonk.exe")
    run([exe, "--selftest", os.path.join(out, "exe")])

    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "Release v%s: %s\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" % (ver, notes)])
    run(["git", "tag", "v%s" % ver])
    run(["git", "push", "origin", "HEAD", "--tags"])
    run(["gh", "release", "create", "v%s" % ver, exe, "--title", "HONK v%s" % ver, "--notes", notes])
    print("\nReleased v%s - games will update next time they start." % ver)


if __name__ == "__main__":
    main()
