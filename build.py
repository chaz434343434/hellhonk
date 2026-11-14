"""Build dist/HellHonk.exe (one file, no console) with PyInstaller.

    py -3.9 build.py
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def make_icon(path):
    """ICO with one 256x256 PNG inside, drawn from the in-game goose face."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    sys.path.insert(0, HERE)
    from assets import face
    img = pygame.transform.scale(face(0, 0, "grin"), (220, 254))
    canvas = pygame.Surface((256, 256), pygame.SRCALPHA)
    canvas.blit(img, (18, 1))
    png = path + ".png"
    pygame.image.save(canvas, png)
    with open(png, "rb") as f:
        data = f.read()
    os.remove(png)
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, 1))
        f.write(struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(data), 6 + 16))
        f.write(data)
    pygame.quit()


def main():
    os.chdir(HERE)
    icon = os.path.join(HERE, "build", "hellhonk.ico")
    os.makedirs(os.path.dirname(icon), exist_ok=True)
    make_icon(icon)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", "HellHonk", "--icon", icon, "--distpath", "dist", "--workpath", "build/pyi",
           "--specpath", "build", "hellhonk.py"]
    subprocess.check_call(cmd)
    exe = os.path.join(HERE, "dist", "HellHonk.exe")
    print("built %s (%.1f MB)" % (exe, os.path.getsize(exe) / 1e6))


if __name__ == "__main__":
    main()
