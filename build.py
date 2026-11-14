"""Build the packaged game with PyInstaller.

    Windows:  py -3.9 build.py      -> dist/HellHonk.exe            (one file, no console)
    macOS:    python3 build.py      -> dist/HellHonk.app + dist/HellHonk-mac-<arm64|intel>.zip
"""
import os
import platform
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IS_MAC = sys.platform == "darwin"


def icon_png(path):
    """256x256 PNG of the in-game goose face."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    sys.path.insert(0, HERE)
    from assets import face
    img = pygame.transform.scale(face(0, 0, "grin"), (220, 254))
    canvas = pygame.Surface((256, 256), pygame.SRCALPHA)
    canvas.blit(img, (18, 1))
    pygame.image.save(canvas, path)
    pygame.quit()


def make_ico(path):
    """ICO with one 256x256 PNG inside."""
    png = path + ".png"
    icon_png(png)
    with open(png, "rb") as f:
        data = f.read()
    os.remove(png)
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, 1))
        f.write(struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(data), 6 + 16))
        f.write(data)


def main():
    os.chdir(HERE)
    os.makedirs("build", exist_ok=True)
    common = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "HellHonk",
              "--distpath", "dist", "--workpath", "build/pyi", "--specpath", "build"]
    if IS_MAC:
        icon = os.path.join(HERE, "build", "hellhonk.png")      # PyInstaller turns it into .icns (needs Pillow)
        icon_png(icon)
        subprocess.check_call(common + ["--onedir", "--icon", icon,
                                        "--osx-bundle-identifier", "io.github.chaz434343434.hellhonk", "hellhonk.py"])
        arch = "arm64" if platform.machine() == "arm64" else "intel"
        z = os.path.join("dist", "HellHonk-mac-%s.zip" % arch)
        if os.path.exists(z):
            os.remove(z)
        subprocess.check_call(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", "dist/HellHonk.app", z])
        print("built %s (%.1f MB)" % (z, os.path.getsize(z) / 1e6))
    else:
        icon = os.path.join(HERE, "build", "hellhonk.ico")
        make_ico(icon)
        subprocess.check_call(common + ["--onefile", "--icon", icon, "hellhonk.py"])
        exe = os.path.join(HERE, "dist", "HellHonk.exe")
        print("built %s (%.1f MB)" % (exe, os.path.getsize(exe) / 1e6))


if __name__ == "__main__":
    main()
