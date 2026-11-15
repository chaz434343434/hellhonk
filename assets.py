"""Procedural art for HELLHONK: textures, sprites, weapon views, HUD faces.

Everything is generated at startup with numpy + pygame.draw, so the game ships
with no image files. Texture arrays are stored [u, v, rgb] (x first) to match
pygame.surfarray layout.
"""
import math

import numpy as np
import pygame

T = 64  # texture size


# ----------------------------------------------------------------- helpers
def noise(size, cell, octaves=3, seed=0):
    """Tileable value noise in 0..1, shape (size, size) indexed [y, x]."""
    r = np.random.default_rng(seed)
    out = np.zeros((size, size))
    amp, tot = 1.0, 0.0
    for _ in range(octaves):
        n = max(1, size // cell)
        g = r.random((n + 1, n + 1))
        g[-1, :] = g[0, :]
        g[:, -1] = g[:, 0]
        xs = np.linspace(0, n, size, endpoint=False)
        i = xs.astype(int)
        f = xs - i
        f = f * f * (3 - 2 * f)
        fx, fy = f[None, :], f[:, None]
        a, b = g[i][:, i], g[i][:, i + 1]
        c, d = g[i + 1][:, i], g[i + 1][:, i + 1]
        out += (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy) * amp
        tot += amp
        amp *= 0.5
        cell = max(1, cell // 2)
    return out / tot


def col(c):
    return np.array(c, dtype=float)


def finish(img):
    """(y, x, 3) float -> (x, y, 3) uint8."""
    return np.clip(img, 0, 255).astype(np.uint8).transpose(1, 0, 2).copy()


def speckle(img, seed, amount=18):
    r = np.random.default_rng(seed)
    return img + r.normal(0, amount, img.shape[:2])[..., None]


# ----------------------------------------------------------------- wall textures
def tex_brick(base=(128, 58, 44), mortar=(62, 52, 48), seed=1, cracked=False):
    r = np.random.default_rng(seed)
    n = noise(T, 8, 3, seed)
    img = np.zeros((T, T, 3))
    for row in range(8):
        off = (row % 2) * 8
        for c in range(-1, 5):
            x0 = c * 16 + off
            a, b = max(0, x0), min(T, x0 + 16)
            if b > a:
                img[row * 8:row * 8 + 8, a:b] = col(base) * (0.78 + 0.4 * r.random())
    for row in range(8):
        img[row * 8, :] = mortar
        off = (row % 2) * 8
        for c in range(5):
            img[row * 8:row * 8 + 8, (c * 16 + off) % T] = mortar
    img *= (0.72 + 0.5 * n)[..., None]
    if cracked:  # subtle hint for a secret
        x, y = 30, 6
        for _ in range(70):
            img[y, x] = (30, 22, 20)
            if x + 1 < T:
                img[y, x + 1] = (45, 35, 30)
            y = min(T - 1, y + 1)
            x = int(np.clip(x + r.integers(-1, 2), 2, T - 3))
    return finish(speckle(img, seed, 8))


def tex_hedge(seed=2, gap=False):
    n = noise(T, 8, 4, seed)
    r = np.random.default_rng(seed)
    img = col((38, 92, 34))[None, None, :] * (0.45 + 0.9 * n)[..., None]
    for _ in range(260):  # leaves
        x, y = r.integers(0, T, 2)
        img[y, x] = (70 + r.integers(0, 50), 140 + r.integers(0, 60), 50)
    # hell-tinted roots at the bottom
    for y in range(T - 10, T):
        img[y] *= 0.55 + 0.04 * (T - y)
        img[y, :, 0] += 12
    if gap:  # a slightly thinner patch: the secret
        g = np.exp(-(((np.arange(T)[None, :] - 32) / 9.0) ** 2 + ((np.arange(T)[:, None] - 34) / 16.0) ** 2))
        img *= (1 - 0.32 * g)[..., None]
    return finish(img)


def tex_wood(seed=3, base=(110, 72, 40)):
    img = np.zeros((T, T, 3))
    r = np.random.default_rng(seed)
    grain = noise(T, 4, 3, seed)
    for p in range(4):
        y0 = p * 16
        shade = 0.75 + 0.35 * r.random()
        stripes = 0.5 + 0.5 * np.sin(np.arange(T) / 3.0 + r.random() * 6 + grain[y0:y0 + 16] * 5)
        img[y0:y0 + 16] = col(base) * shade * (0.75 + 0.3 * stripes)[..., None]
        img[y0] = (50, 32, 18)
        img[y0 + 15] = (68, 44, 24)
        for nx in (6, 58):  # nails
            img[y0 + 7:y0 + 9, nx:nx + 2] = (150, 150, 150)
    return finish(img)


def tex_metal(seed=4, base=(92, 96, 104), hazard=False):
    n = noise(T, 16, 3, seed)
    img = col(base)[None, None, :] * (0.75 + 0.4 * n)[..., None]
    for p in (0, 32):
        img[p, :] = (150, 155, 165)
        img[:, p] = (150, 155, 165)
        img[p + 31, :] = (45, 46, 52)
        img[:, p + 31] = (45, 46, 52)
    for x in (3, 28, 35, 60):
        for y in (3, 28, 35, 60):
            img[y:y + 2, x:x + 2] = (190, 190, 200)
    if hazard:
        for y in range(52, 62):
            for x in range(T):
                img[y, x] = (210, 170, 20) if ((x + y) // 6) % 2 == 0 else (25, 25, 25)
    return finish(speckle(img, seed, 6))


def tex_glass(seed=5):
    n = noise(T, 16, 2, seed)
    img = col((70, 120, 90))[None, None, :] * (0.6 + 0.5 * n)[..., None]
    for y in range(T):  # diagonal glint
        for x in range(T):
            if 0 <= (x - y) % 64 < 4:
                img[y, x] += 60
    frame = (190, 190, 175)
    for p in (0, 31, 32, 63):
        img[p, :] = frame
        img[:, p] = frame
    img[:, 31] = img[:, 32] = (120, 120, 110)
    return finish(img)


def tex_door(seed=6, stripe=None):
    img = np.zeros((T, T, 3))
    wood = tex_wood(seed, (95, 62, 36)).transpose(1, 0, 2).astype(float)
    img[:] = wood
    img[:, :6] = img[:, -6:] = (85, 88, 96)  # metal frame
    img[:5, :] = (85, 88, 96)
    img[:, 5] = img[:, -6] = (40, 40, 46)
    # goose footprint emblem
    cx, cy = 32, 30
    for ang in (-0.6, 0.0, 0.6):
        for t in range(14):
            x = int(cx + math.sin(ang) * t)
            y = int(cy - math.cos(ang) * t)
            img[y - 1:y + 2, x - 1:x + 2] = (190, 150, 60)
    img[cy - 2:cy + 4, cx - 5:cx + 6] = (190, 150, 60)
    if stripe is not None:
        img[:, 1:5] = stripe
        img[:, -5:-1] = stripe
        img[44:52, 8:-8] = stripe
        img[1:4, :] = stripe
    return finish(speckle(img, seed, 5))


def tex_switch(on):
    img = tex_metal(7, (80, 84, 92), hazard=True).transpose(1, 0, 2).astype(float)
    img[14:46, 20:44] = (40, 40, 46)
    img[16:44, 22:42] = (65, 68, 76)
    lamp = (40, 230, 70) if on else (230, 40, 30)
    img[18:24, 28:36] = lamp
    if on:
        img[30:42, 30:34] = (200, 200, 210)
        img[38:42, 27:37] = (220, 200, 60)
    else:
        img[24:36, 30:34] = (200, 200, 210)
        img[24:28, 27:37] = (220, 200, 60)
    return finish(img)


def tex_hellrock(seed=8):
    n = noise(T, 16, 4, seed)
    img = col((70, 22, 18))[None, None, :] * (0.5 + 0.8 * n)[..., None]
    veins = np.abs(noise(T, 16, 2, seed + 1) - 0.5) < 0.03
    img[veins] = (255, 120, 30)
    return finish(img)


# ----------------------------------------------------------------- flats
def flat_grass(seed=10):
    n = noise(T, 16, 4, seed)
    img = col((52, 84, 36))[None, None, :] * (0.55 + 0.7 * n)[..., None]
    r = np.random.default_rng(seed)
    for _ in range(300):
        x, y = r.integers(0, T, 2)
        img[y, x] = (90, 130 + r.integers(0, 40), 50)
    img[..., 0] += 10
    return finish(img)


def flat_tiles(seed=11, base=(120, 112, 100)):
    n = noise(T, 8, 3, seed)
    r = np.random.default_rng(seed)
    img = np.zeros((T, T, 3))
    for ty in range(4):
        for tx in range(4):
            img[ty * 16:ty * 16 + 16, tx * 16:tx * 16 + 16] = col(base) * (0.8 + 0.3 * r.random())
    img *= (0.75 + 0.4 * n)[..., None]
    for p in range(0, T, 16):
        img[p, :] = (55, 50, 46)
        img[:, p] = (55, 50, 46)
    return finish(img)


def flat_woodfloor(seed=12):
    return tex_wood(seed, (105, 70, 42)).transpose(1, 0, 2)[:, :, :].transpose(1, 0, 2).copy()


def flat_metal(seed=13):
    n = noise(T, 4, 2, seed)
    img = col((78, 80, 86))[None, None, :] * (0.8 + 0.3 * n)[..., None]
    for y in range(T):
        for x in range(T):
            if (x // 4 + y // 4) % 2 == 0 and x % 4 == 1 and y % 4 == 1:
                img[y, x] += 40
    for p in (0, 32):
        img[p, :] = (40, 40, 44)
        img[:, p] = (40, 40, 44)
    return finish(img)


def flat_sludge_frames(seed=14, frames=4):
    out = []
    base = noise(T, 16, 3, seed)
    swirl = noise(T, 8, 2, seed + 1)
    for f in range(frames):
        n = np.roll(base, f * 4, axis=1) * 0.6 + np.roll(swirl, -f * 4, axis=0) * 0.4
        img = np.zeros((T, T, 3))
        img[..., 0] = 40 + 60 * n
        img[..., 1] = 140 + 110 * n
        img[..., 2] = 30 + 40 * n
        bright = n > 0.66
        img[bright] = (190, 255, 120)
        out.append(finish(img))
    return out


def flat_beams(seed=15):
    img = tex_wood(seed, (80, 52, 30)).transpose(1, 0, 2).astype(float)
    img[:, 28:36] *= 0.55
    return finish(img)


def flat_ceillights(seed=16):
    img = flat_metal(seed).transpose(1, 0, 2).astype(float) * 0.8
    img[20:44, 20:44] = (235, 235, 210)
    img[20:44, 20] = img[20:44, 43] = (120, 120, 110)
    return finish(img)


def make_sky(w=512, h=168, seed=20):
    ys = np.linspace(0, 1, h)[:, None]
    img = np.zeros((h, w, 3))
    img[..., 0] = 60 + 170 * ys
    img[..., 1] = 8 + 70 * ys ** 2
    img[..., 2] = 12 + 20 * ys
    cl = noise(w, 64, 4, seed)[:h, :]
    cl = np.clip((cl - 0.45) * 3, 0, 1)
    img = img * (1 - 0.5 * cl[..., None]) + col((40, 10, 10)) * 0.5 * cl[..., None]
    # distant dead tree line
    r = np.random.default_rng(seed)
    ridge = h - 26 + (noise(w, 32, 3, seed + 3)[0] * 18).astype(int)
    for x in range(w):
        top = ridge[x]
        if r.random() < 0.07:
            top -= r.integers(6, 20)
        img[max(0, top):, x] = (25, 8, 10)
    return np.clip(img, 0, 255).astype(np.uint8).transpose(1, 0, 2).copy()


# ----------------------------------------------------------------- sprites
def squash(surf, k):
    """Narrow a sprite horizontally (turned-away views look thinner), keeping the canvas size."""
    if k >= 0.999:
        return surf
    w, h = surf.get_size()
    small = pygame.transform.scale(surf, (max(1, int(w * k)), h))
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(small, ((w - small.get_width()) // 2, 0))
    return out


def surf_arr(s):
    rgb = pygame.surfarray.array3d(s)
    a = pygame.surfarray.array_alpha(s)
    return np.dstack([rgb, a]).astype(np.uint8)


def S(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


ORANGE = (240, 140, 30)
DARKOR = (190, 95, 20)


def feet(s, cx, y, spread, step, color=ORANGE, size=5):
    for side in (-1, 1):
        x = cx + side * spread + (step * side)
        yy = y - (2 if (step and side > 0) else 0)
        pygame.draw.polygon(s, color, [(x - size, yy), (x + size, yy), (x, yy - size)])
        pygame.draw.line(s, DARKOR, (x, yy - size), (x, yy - size - 4), 2)


def quackling(pose, v=0):
    """Hell duckling. poses: walk0 walk1 aim fire pain d0 d1 d2"""
    s = S(48, 48)
    if pose.startswith("d"):
        return dead_pile(s, (150, 25, 30), int(pose[1]), horns=True)
    step = {"walk0": 2, "walk1": -2}.get(pose, 0)
    off = 1 if pose == "pain" else 0
    feet(s, 24, 47, 6, step)
    body = (150, 25, 30) if pose != "pain" else (210, 90, 90)
    pygame.draw.ellipse(s, (60, 10, 15), (4 + off, 22, 14, 18))
    pygame.draw.ellipse(s, (60, 10, 15), (30 + off, 22, 14, 18))
    pygame.draw.ellipse(s, body, (9 + off, 20, 30, 24))
    if v < 3:
        pygame.draw.ellipse(s, (105, 15, 20), (15 + off + view_shift(v), 29, 18, 13))
    else:
        pygame.draw.ellipse(s, (90, 10, 15), (12 + off, 24, 24, 14))
    hx, hy = 24 + off + view_shift(v), 15
    pygame.draw.polygon(s, (225, 205, 165), [(hx - 7, hy - 5), (hx - 11, hy - 14), (hx - 3, hy - 8)])
    pygame.draw.polygon(s, (225, 205, 165), [(hx + 7, hy - 5), (hx + 11, hy - 14), (hx + 3, hy - 8)])
    pygame.draw.circle(s, (120, 20, 25), (hx, hy), 10)
    glow = (255, 250, 160) if pose == "fire" else ((255, 200, 80) if pose == "aim" else None)
    tip = bird_face(s, hx, hy, 10, v, (255, 225, 40), 2, ORANGE, 7, open_=pose == "fire", glow=glow,
                    brow=(20, 0, 0), closed=pose == "pain")
    if pose == "fire" and tip:
        pygame.draw.circle(s, (255, 255, 255), tip, 2)
    return s


def fireswan(pose, v=0):
    """Black hell-swan. poses: walk0 walk1 wind fire pain d0 d1 d2"""
    s = S(48, 72)
    if pose.startswith("d"):
        return dead_pile(s, (35, 30, 40), int(pose[1]), wide=True)
    step = {"walk0": 2, "walk1": -2}.get(pose, 0)
    body = (34, 28, 40) if pose != "pain" else (110, 80, 110)
    feet(s, 24, 71, 7, step, (200, 60, 30))
    if pose in ("wind", "fire"):
        pygame.draw.polygon(s, (20, 16, 26), [(10, 52), (0, 26), (6, 30), (2, 40), (14, 46)])
        pygame.draw.polygon(s, (20, 16, 26), [(38, 52), (47, 26), (42, 30), (46, 40), (34, 46)])
    pygame.draw.ellipse(s, body, (6, 44, 36, 24))
    pygame.draw.ellipse(s, (90, 20, 25), (12, 56, 24, 10), 2)
    sh = view_shift(v)
    for i in range(16):
        t = i / 15
        x = 24 + math.sin(t * 3.2) * (4 if v in (0, 4) else 2) + sh * t * 1.5
        y = 48 - t * 34
        pygame.draw.circle(s, body, (int(x), int(y)), 5)
    hx, hy = int(25 + sh * 1.5), 12
    pygame.draw.circle(s, body, (hx, hy), 7)
    eyes = (255, 40, 30) if pose != "pain" else (255, 255, 255)
    tip = bird_face(s, hx, hy, 7, v, eyes, 2, (220, 60, 30), 7, open_=pose == "fire",
                    glow=(255, 130, 20) if pose == "wind" else None)
    if pose == "fire" and tip:
        pygame.draw.circle(s, (255, 120, 20), tip, 6)
        pygame.draw.circle(s, (255, 230, 120), tip, 3)
    return s


def brute(pose, v=0):
    """Gander Brute: armoured charger. poses: walk0 walk1 bite0 bite1 pain d0 d1 d2"""
    s = S(64, 56)
    if pose.startswith("d"):
        return dead_pile(s, (110, 95, 120), int(pose[1]), wide=True)
    step = {"walk0": 3, "walk1": -3}.get(pose, 0)
    body = (112, 96, 124) if pose != "pain" else (190, 160, 200)
    feet(s, 32, 55, 13, step, ORANGE, 8)
    pygame.draw.ellipse(s, body, (4, 14, 56, 38))
    for i, y in enumerate((20, 30, 40)):
        pygame.draw.arc(s, (60, 62, 72), (8, y - 6, 48, 22), 0.3, math.pi - 0.3, 4)
        pygame.draw.circle(s, (170, 170, 180), (14 + i * 4, y + 2), 2)
    hx, hy = 32 + view_shift(v) * 2, 16
    pygame.draw.circle(s, body, (hx, hy), 12)
    tip = bird_face(s, hx, hy - 1, 12, v, (255, 200, 40), 2, ORANGE, 10, open_=pose in ("bite0", "bite1"),
                    brow=(30, 20, 30))
    if pose in ("bite0", "bite1") and v <= 1:
        for tx in range(-6, 7, 4):
            pygame.draw.polygon(s, (240, 240, 230), [(hx + tx - 2 + view_shift(v), hy + 1),
                                                     (hx + tx + 2 + view_shift(v), hy + 1), (hx + tx + view_shift(v), hy + 4)])
    return s


def dead_pile(s, color, stage, horns=False, wide=False):
    w, h = s.get_size()
    r = np.random.default_rng(stage + w)
    cx = w // 2
    if stage == 0:
        pygame.draw.ellipse(s, color, (cx - w // 3, h - h // 2, 2 * w // 3, h // 3))
        for _ in range(12):
            x, y = r.integers(0, w), r.integers(0, h // 2)
            pygame.draw.circle(s, (240, 240, 240), (int(x), int(h // 3 + y)), 1)
        pygame.draw.circle(s, (170, 0, 0), (cx, h - h // 3), 4)
    elif stage == 1:
        pygame.draw.ellipse(s, (130, 0, 0), (cx - w // 2 + 2, h - 10, w - 4, 8))
        pygame.draw.ellipse(s, color, (cx - w // 3, h - 16, 2 * w // 3, 12))
    else:
        pygame.draw.ellipse(s, (120, 0, 0), (2, h - 9, w - 4, 8))
        pygame.draw.ellipse(s, color, (cx - w // 4, h - 12, w // 2, 8))
        for _ in range(10):
            x = r.integers(4, w - 4)
            pygame.draw.line(s, (235, 235, 235), (int(x), h - 4), (int(x + r.integers(-3, 4)), h - 9), 1)
        if horns:
            pygame.draw.polygon(s, (225, 205, 165), [(cx - 8, h - 6), (cx - 12, h - 12), (cx - 5, h - 8)])
    return s


def item(kind):
    if kind == "bread":
        s = S(20, 16)
        pygame.draw.rect(s, (160, 100, 40), (1, 3, 18, 13), border_radius=5)
        pygame.draw.rect(s, (235, 205, 150), (3, 5, 14, 9), border_radius=3)
        return s
    if kind == "loaf":
        s = S(30, 18)
        pygame.draw.ellipse(s, (170, 100, 35), (1, 2, 28, 16))
        for x in (8, 14, 20):
            pygame.draw.line(s, (230, 190, 120), (x, 5), (x + 3, 10), 2)
        return s
    if kind == "crumbs":
        s = S(14, 8)
        for x, y in ((2, 5), (6, 3), (9, 6), (11, 2), (4, 1)):
            pygame.draw.circle(s, (230, 190, 110), (x, y), 2)
        return s
    if kind == "vest":
        s = S(28, 24)
        pygame.draw.polygon(s, (40, 150, 130), [(4, 4), (10, 1), (14, 6), (18, 1), (24, 4), (24, 23), (4, 23)])
        for y in range(8, 22, 4):
            for x in range(6, 23, 5):
                pygame.draw.arc(s, (150, 230, 210), (x - 3, y - 2, 6, 5), math.pi, 2 * math.pi, 1)
        return s
    if kind == "feather":
        s = S(12, 18)
        pygame.draw.ellipse(s, (120, 170, 255), (2, 0, 8, 15))
        pygame.draw.line(s, (240, 240, 255), (6, 2), (6, 17), 1)
        return s
    if kind == "pebbles":
        s = S(18, 14)
        pygame.draw.ellipse(s, (120, 90, 55), (1, 2, 16, 12))
        pygame.draw.line(s, (70, 50, 30), (5, 3), (12, 3), 2)
        for x, y in ((6, 8), (10, 9), (8, 6)):
            pygame.draw.circle(s, (170, 170, 170), (x, y), 2)
        return s
    if kind == "pebblebox":
        s = S(26, 18)
        pygame.draw.rect(s, (110, 80, 45), (1, 3, 24, 15))
        pygame.draw.rect(s, (70, 50, 30), (1, 3, 24, 15), 2)
        for x in range(5, 22, 5):
            pygame.draw.circle(s, (180, 180, 180), (x, 4), 3)
        return s
    if kind == "eggs":
        s = S(24, 12)
        pygame.draw.rect(s, (170, 160, 140), (1, 5, 22, 7))
        for x in (5, 12, 19):
            pygame.draw.ellipse(s, (250, 245, 230), (x - 3, 0, 7, 9))
        return s
    if kind == "egggun":
        s = S(40, 14)
        pygame.draw.rect(s, (120, 75, 40), (0, 6, 14, 7))
        pygame.draw.rect(s, (180, 140, 50), (12, 3, 26, 6))
        pygame.draw.rect(s, (150, 110, 40), (12, 8, 22, 4))
        pygame.draw.ellipse(s, (250, 245, 230), (18, 0, 8, 6))
        return s
    if kind in ("ykey", "bkey"):
        c = (240, 210, 40) if kind == "ykey" else (60, 120, 255)
        s = S(12, 16)
        pygame.draw.rect(s, c, (1, 1, 10, 14), border_radius=2)
        pygame.draw.rect(s, (255, 255, 255), (1, 1, 10, 14), 1, border_radius=2)
        pygame.draw.circle(s, (40, 30, 20), (6, 9), 2)
        return s
    raise KeyError(kind)


def decor(kind, frame=0):
    if kind == "tree":
        s = S(48, 96)
        pygame.draw.polygon(s, (45, 28, 22), [(20, 95), (28, 95), (27, 40), (21, 40)])
        for (x0, y0, x1, y1) in ((24, 50, 6, 26), (24, 44, 42, 20), (24, 40, 18, 6), (24, 40, 32, 2), (12, 34, 3, 30), (36, 28, 46, 30)):
            pygame.draw.line(s, (45, 28, 22), (x0, y0), (x1, y1), 4 if y0 > 45 else 3)
        return s
    if kind == "lamp":
        s = S(16, 80)
        pygame.draw.rect(s, (40, 40, 45), (6, 14, 4, 66))
        pygame.draw.rect(s, (60, 60, 66), (2, 76, 12, 4))
        glow = (255, 200, 90) if frame == 0 else (255, 160, 60)
        pygame.draw.rect(s, (40, 40, 45), (1, 0, 14, 16))
        pygame.draw.rect(s, glow, (3, 2, 10, 12))
        return s
    if kind == "planter":
        s = S(36, 34)
        pygame.draw.rect(s, (120, 60, 40), (4, 18, 28, 16))
        for x in range(6, 32, 5):
            pygame.draw.line(s, (60, 140, 50), (x, 18), (x + (x % 7) - 3, 2), 3)
            pygame.draw.circle(s, (200, 30, 60), (x + (x % 7) - 3, 3), 3)
        return s
    if kind == "crate":
        s = S(40, 40)
        pygame.draw.rect(s, (120, 85, 45), (0, 0, 40, 40))
        pygame.draw.rect(s, (70, 48, 25), (0, 0, 40, 40), 3)
        pygame.draw.line(s, (70, 48, 25), (0, 0), (40, 40), 3)
        pygame.draw.line(s, (70, 48, 25), (40, 0), (0, 40), 3)
        return s
    if kind == "remains":
        s = S(36, 10)
        pygame.draw.ellipse(s, (130, 0, 0), (0, 3, 36, 7))
        pygame.draw.ellipse(s, (230, 230, 225), (8, 1, 18, 6))
        pygame.draw.polygon(s, ORANGE, [(26, 3), (33, 4), (26, 6)])
        return s
    if kind == "barrel":
        s = S(24, 32)
        pygame.draw.rect(s, (40, 70, 72), (2, 3, 20, 29), border_radius=3)
        pygame.draw.line(s, (25, 40, 42), (2, 12), (22, 12), 2)
        pygame.draw.line(s, (25, 40, 42), (2, 24), (22, 24), 2)
        glow = (140, 255, 90) if frame == 0 else (100, 220, 70)
        pygame.draw.ellipse(s, glow, (3, 0, 18, 7))
        pygame.draw.circle(s, glow, (8, 8), 2)
        return s
    raise KeyError(kind)


def fx(kind, frame):
    if kind == "puff":
        s = S(12, 12)
        r = 2 + frame * 2
        pygame.draw.circle(s, (200, 200, 190, 220 - frame * 60), (6, 6), r)
        return s
    if kind == "blood":
        s = S(14, 14)
        for i in range(5 + frame * 2):
            ang = i * 2.4
            pygame.draw.circle(s, (180, 0, 0) if i % 2 else (245, 245, 245), (int(7 + math.cos(ang) * frame * 2.5), int(7 + math.sin(ang) * frame * 2.5)), 2)
        return s
    if kind == "fireball":
        s = S(16, 16)
        pygame.draw.circle(s, (255, 100, 10), (8, 8), 7 - frame)
        pygame.draw.circle(s, (255, 230, 120), (8, 8), 4 - frame)
        return s
    if kind == "boom":
        s = S(48, 48)
        rr = 10 + frame * 7
        pygame.draw.circle(s, (255, 90, 10, 230 - frame * 50), (24, 24), rr)
        pygame.draw.circle(s, (255, 220, 90, 230 - frame * 60), (24, 24), max(2, rr - 8))
        return s
    if kind == "flash":  # muzzle flash in the world
        s = S(16, 16)
        pygame.draw.circle(s, (255, 240, 150), (8, 8), 6)
        return s
    raise KeyError(kind)


# ----------------------------------------------------------------- first-person weapon views
WHITE = (240, 240, 232)
WSHADE = (190, 190, 182)


def wing(s, x, y, flip=False):
    pts = [(x, y), (x + 34, y - 8), (x + 46, y + 30), (x + 6, y + 40)]
    if flip:
        pts = [(2 * x - px, py) for px, py in pts]
    pygame.draw.polygon(s, WHITE, pts)
    for i in range(4):
        a = (x + (8 + i * 9) * (-1 if flip else 1), y + 2)
        b = (x + (14 + i * 9) * (-1 if flip else 1), y + 34)
        pygame.draw.line(s, WSHADE, a, b, 2)


def weapon_view(kind, frame):
    s = S(140, 90)
    if kind == "peck":
        lift = (0, 26, 40, 18)[frame]
        y = 92 - lift
        pygame.draw.ellipse(s, WHITE, (40, y - 18, 60, 80))
        pygame.draw.polygon(s, ORANGE, [(52, y - 4), (88, y - 4), (70, y - 34 - lift // 3)])
        pygame.draw.polygon(s, DARKOR, [(52, y - 4), (70, y - 4), (70, y - 34 - lift // 3)])
        pygame.draw.circle(s, (60, 30, 10), (64, y - 12), 2)
        return s
    if kind == "honker":
        kick = (0, 6, 3, 1)[frame]
        y = 40 + kick
        pygame.draw.rect(s, (150, 110, 30), (60, y + 4, 14, 46))  # pipe
        pygame.draw.polygon(s, (215, 170, 50), [(54, y + 6), (80, y + 6), (92, y - 16), (42, y - 16)])  # bell
        pygame.draw.ellipse(s, (120, 80, 20), (42, y - 22, 50, 12))
        pygame.draw.ellipse(s, (40, 25, 10), (48, y - 20, 38, 8))
        for vx in (64, 70):
            pygame.draw.rect(s, (230, 200, 90), (vx, y + 14, 4, 10))
        wing(s, 74, y + 24)
        if frame == 1:
            for rr, c in ((22, (255, 240, 150)), (14, (255, 255, 220))):
                pygame.draw.ellipse(s, c, (67 - rr, y - 30 - rr // 2, rr * 2, rr))
            for i in range(3):
                pygame.draw.arc(s, (255, 230, 120), (37 - i * 8, y - 52 - i * 6, 60 + i * 16, 30), 0.3, math.pi - 0.3, 2)
        return s
    if kind == "egggun":
        kick = (0, 8, 4, 0, 0)[frame]
        pump = (0, 0, 0, 10, 4)[frame]
        y = 34 + kick
        pygame.draw.rect(s, (110, 70, 38), (56, y + 20, 30, 50))  # stock
        pygame.draw.rect(s, (175, 135, 50), (52, y - 6, 16, 44), border_radius=4)
        pygame.draw.rect(s, (175, 135, 50), (72, y - 6, 16, 44), border_radius=4)
        pygame.draw.ellipse(s, (35, 22, 10), (54, y - 10, 12, 8))
        pygame.draw.ellipse(s, (35, 22, 10), (74, y - 10, 12, 8))
        pygame.draw.rect(s, (90, 60, 32), (48, y + 26 + pump, 44, 12), border_radius=3)
        pygame.draw.ellipse(s, (250, 245, 230), (63, y + 40, 14, 18))
        wing(s, 40, y + 30 + pump, flip=True)
        wing(s, 92, y + 36)
        if frame == 1:
            pygame.draw.circle(s, (255, 240, 150), (70, y - 16), 22)
            pygame.draw.circle(s, (255, 255, 230), (70, y - 16), 11)
        return s
    raise KeyError(kind)


# ----------------------------------------------------------------- HUD faces
def face(look=0, pain=0, mood="normal"):
    """look -1/0/1, pain 0..4 (0 healthy), mood normal/ouch/grin/dead"""
    s = S(26, 30)
    head = (245, 245, 240)
    if pain >= 3:
        head = (225, 215, 210)
    pygame.draw.ellipse(s, head, (2, 1, 22, 28))
    # ruffled feathers when hurt
    for i in range(pain):
        pygame.draw.line(s, (200, 200, 195), (3 + i * 5, 3), (1 + i * 5, -1), 2)
    for i in range(max(0, pain - 1)):
        pygame.draw.circle(s, (190, 20, 20), (5 + i * 6, 20 - i * 3), 2)
    if pain >= 4:
        pygame.draw.line(s, (170, 0, 0), (17, 4), (20, 12), 2)
    ex = 2 * look
    if mood == "dead":
        for x in (8, 17):
            pygame.draw.line(s, (20, 20, 20), (x - 2, 9), (x + 2, 13), 2)
            pygame.draw.line(s, (20, 20, 20), (x + 2, 9), (x - 2, 13), 2)
    else:
        big = 3 if mood == "ouch" else 2
        for x in (8, 17):
            pygame.draw.circle(s, (20, 20, 20), (x + ex, 11), big)
            pygame.draw.circle(s, (255, 255, 255), (x + ex - 1, 10), 1)
        brow = 1 if mood == "grin" else (-1 if mood == "ouch" else 0)
        pygame.draw.line(s, (40, 40, 40), (5, 7 + brow), (11, 8 - brow), 2)
        pygame.draw.line(s, (40, 40, 40), (20, 7 + brow), (14, 8 - brow), 2)
    if mood in ("ouch", "grin", "dead"):
        pygame.draw.polygon(s, ORANGE, [(7, 16), (19, 16), (13, 21)])
        pygame.draw.polygon(s, ORANGE, [(8, 23), (18, 23), (13, 27)])
        pygame.draw.polygon(s, (110, 10, 20), [(8, 18), (18, 18), (17, 23), (9, 23)])
        if mood == "grin":
            for x in (10, 13, 16):
                pygame.draw.line(s, (255, 255, 255), (x, 18), (x, 20), 1)
    else:
        pygame.draw.polygon(s, ORANGE, [(7, 16), (19, 16), (13, 27)])
        pygame.draw.line(s, DARKOR, (9, 19), (17, 19), 1)
    return s


# ----------------------------------------------------------------- episode-wide additions
def tex_sewer(seed=30):
    img = tex_brick((78, 92, 70), (40, 46, 38), seed).transpose(1, 0, 2).astype(float)
    r = np.random.default_rng(seed)
    for _ in range(6):  # slime streaks
        x = r.integers(0, T)
        ln = r.integers(10, 40)
        img[:ln, x:x + 2] = img[:ln, x:x + 2] * 0.5 + col((90, 200, 60)) * 0.5
    img[50:56, :] = (60, 64, 66)  # pipe
    img[51, :] = (120, 126, 130)
    return finish(img)


def tex_factory(seed=31):
    img = tex_metal(seed, (70, 76, 84)).transpose(1, 0, 2).astype(float)
    img[8:20, 6:58] = (30, 32, 36)
    for i, x in enumerate(range(9, 56, 8)):
        img[11:17, x:x + 5] = (60, 220, 90) if i % 3 else (240, 80, 40)
    img[40:46, :] = (150, 110, 40)
    img[42, :] = (210, 170, 70)
    return finish(img)


def tex_ice(seed=32):
    n = noise(T, 16, 4, seed)
    img = col((150, 200, 235))[None, None, :] * (0.65 + 0.45 * n)[..., None]
    cr = np.abs(noise(T, 16, 2, seed + 1) - 0.5) < 0.025
    img[cr] = (235, 250, 255)
    return finish(img)


def tex_castle(seed=33):
    r = np.random.default_rng(seed)
    n = noise(T, 8, 3, seed)
    img = np.zeros((T, T, 3))
    for row in range(4):
        off = (row % 2) * 16
        for c in range(-1, 3):
            x0 = c * 32 + off
            a, b = max(0, x0), min(T, x0 + 32)
            if b > a:
                img[row * 16:row * 16 + 16, a:b] = col((112, 112, 118)) * (0.75 + 0.35 * r.random())
    for row in range(4):
        img[row * 16, :] = (50, 50, 56)
        off = (row % 2) * 16
        for c in range(3):
            img[row * 16:row * 16 + 16, (c * 32 + off) % T] = (50, 50, 56)
    img *= (0.7 + 0.5 * n)[..., None]
    return finish(img)


def tex_nest(seed=34):
    n = noise(T, 8, 4, seed)
    img = col((120, 40, 35))[None, None, :] * (0.45 + 0.8 * n)[..., None]
    r = np.random.default_rng(seed)
    for _ in range(40):  # twigs
        x, y = r.integers(0, T, 2)
        a = r.random() * math.pi
        for t in range(12):
            xx, yy = int(x + math.cos(a) * t) % T, int(y + math.sin(a) * t) % T
            img[yy, xx] = (70, 45, 25)
    for _ in range(5):  # eggs
        x, y = r.integers(8, T - 8, 2)
        yy, xx = np.ogrid[:T, :T]
        m = ((xx - x) / 5.0) ** 2 + ((yy - y) / 7.0) ** 2 < 1
        img[m] = (235, 225, 200)
    return finish(img)


def crack_variant(arr, seed):
    img = arr.transpose(1, 0, 2).astype(float)
    r = np.random.default_rng(seed)
    x, y = 30, 4
    for _ in range(80):
        img[y, x] *= 0.35
        if x + 1 < T:
            img[y, x + 1] *= 0.6
        y = min(T - 1, y + 1)
        x = int(np.clip(x + r.integers(-1, 2), 2, T - 3))
    return finish(img)


def flat_stone(seed=40):
    return flat_tiles(seed, (70, 76, 70))


def flat_snow(seed=41):
    n = noise(T, 16, 4, seed)
    img = col((225, 232, 245))[None, None, :] * (0.8 + 0.25 * n)[..., None]
    r = np.random.default_rng(seed)
    for _ in range(80):
        x, y = r.integers(0, T, 2)
        img[y, x] = (255, 255, 255)
    return finish(img)


def flat_tele(seed=42):
    img = flat_metal(seed).transpose(1, 0, 2).astype(float) * 0.6
    yy, xx = np.ogrid[:T, :T]
    d = np.hypot(xx - 31.5, yy - 31.5)
    for rr, c in ((28, (90, 255, 150)), (20, (60, 200, 255)), (12, (90, 255, 150))):
        img[np.abs(d - rr) < 2] = c
    return finish(img)


def flat_factory(seed=43):
    img = flat_metal(seed).transpose(1, 0, 2).astype(float)
    for y in range(T):
        for x in range(56, 64):
            img[y, x] = (210, 170, 20) if ((x + y) // 4) % 2 == 0 else (25, 25, 25)
    return finish(img)


def flat_pipes(seed=44):
    img = flat_stone(seed).transpose(1, 0, 2).astype(float) * 0.7
    for y0 in (10, 40):
        img[y0:y0 + 10, :] = (75, 80, 72)
        img[y0 + 2, :] = (140, 146, 135)
    return finish(img)


def flat_ash(seed=45):
    n = noise(T, 16, 4, seed)
    img = col((60, 40, 38))[None, None, :] * (0.55 + 0.7 * n)[..., None]
    veins = np.abs(noise(T, 16, 2, seed + 2) - 0.5) < 0.02
    img[veins] = (200, 70, 20)
    return finish(img)


def flat_lava_frames(seed=46, frames=4):
    out = []
    base = noise(T, 16, 3, seed)
    swirl = noise(T, 8, 2, seed + 1)
    for f in range(frames):
        n = np.roll(base, f * 4, axis=0) * 0.6 + np.roll(swirl, f * 4, axis=1) * 0.4
        img = np.zeros((T, T, 3))
        img[..., 0] = 200 + 55 * n
        img[..., 1] = 40 + 160 * n ** 2
        img[..., 2] = 10 + 30 * n
        img[n < 0.35] = (110, 20, 10)
        out.append(finish(img))
    return out


def make_sky_pal(w, h, top, bottom, cloud, ridge, seed, stars=False):
    ys = np.linspace(0, 1, h)[:, None, None]
    img = col(top)[None, None, :] * (1 - ys) + col(bottom)[None, None, :] * ys
    img = np.repeat(img, w, axis=1)
    cl = np.clip((noise(w, 64, 4, seed)[:h, :] - 0.45) * 3, 0, 1)
    img = img * (1 - 0.5 * cl[..., None]) + col(cloud) * 0.5 * cl[..., None]
    r = np.random.default_rng(seed)
    if stars:
        for _ in range(250):
            x, y = r.integers(0, w), r.integers(0, h * 2 // 3)
            img[y, x] = (255, 255, 240)
    rd = h - 26 + (noise(w, 32, 3, seed + 3)[0] * 18).astype(int)
    for x in range(w):
        img[max(0, rd[x] - (r.integers(6, 20) if r.random() < 0.07 else 0)):, x] = ridge
    return np.clip(img, 0, 255).astype(np.uint8).transpose(1, 0, 2).copy()


# --- new enemies (all original designs) --------------------------------------
def mallard(pose, v=0):
    """Mallard Gunner: green-headed drake with a pebble repeater."""
    s = S(48, 56)
    if pose.startswith("d"):
        return dead_pile(s, (110, 80, 60), int(pose[1]))
    step = {"walk0": 2, "walk1": -2}.get(pose, 0)
    gy = 36 if pose not in ("aim", "fire") else 32

    def gun():
        if v == 0:
            pygame.draw.rect(s, (60, 60, 66), (10, gy, 28, 8))
            pygame.draw.circle(s, (90, 90, 96), (16, gy + 4), 6)
            pygame.draw.circle(s, (30, 30, 34), (30, gy + 4), 3)
            if pose == "fire":
                pygame.draw.circle(s, (255, 240, 140), (30, gy + 4), 6)
        else:
            L = (0, 16, 22, 14, 10)[v]
            x0 = 18 if v < 3 else 30
            pygame.draw.circle(s, (90, 90, 96), (x0, gy + 4), 5)
            for by in (gy + 2, gy + 5):
                pygame.draw.line(s, (40, 40, 44), (x0, by), (x0 + L, by), 2)
            if pose == "fire" and v < 3:
                pygame.draw.circle(s, (255, 240, 140), (x0 + L + 3, gy + 3), 6)

    if v >= 3:
        gun()
    feet(s, 24, 55, 7, step)
    chest = (130, 70, 50) if pose != "pain" else (200, 150, 130)
    pygame.draw.ellipse(s, (150, 150, 140), (8, 24, 32, 28))
    if v < 3:
        pygame.draw.ellipse(s, chest, (12 + view_shift(v), 22, 24, 16))
        pygame.draw.rect(s, (240, 240, 240), (13 + view_shift(v), 20, 22, 3))
    else:
        pygame.draw.rect(s, (240, 240, 240), (13, 20, 22, 3))
    hx, hy = 24 + view_shift(v), 13
    pygame.draw.circle(s, (20, 110, 50), (hx, hy), 10)
    pygame.draw.circle(s, (60, 170, 90), (hx - 3, hy - 4), 3)
    bird_face(s, hx, hy, 10, v, (255, 60, 30), 2, (220, 190, 40), 6, closed=pose == "pain")
    if v < 3:
        gun()
    return s


def pelican(pose, v=0):
    """Pelican Bomber: lobs egg bombs from its pouch."""
    s = S(56, 64)
    if pose.startswith("d"):
        return dead_pile(s, (225, 220, 210), int(pose[1]), wide=True)
    step = {"walk0": 2, "walk1": -2}.get(pose, 0)
    body = (230, 225, 215) if pose != "pain" else (255, 200, 200)
    feet(s, 28, 63, 9, step, (90, 90, 95), 6)
    if pose in ("wind", "fire"):
        pygame.draw.polygon(s, (60, 60, 66), [(10, 40), (0, 22), (14, 34)])
        pygame.draw.polygon(s, (60, 60, 66), [(46, 40), (55, 22), (42, 34)])
    pygame.draw.ellipse(s, body, (8, 30, 40, 30))
    hx, hy = 28 + view_shift(v) * 2, 14
    pygame.draw.circle(s, body, (hx, hy), 10)
    tip = bird_face(s, hx, hy, 10, v, (230, 40, 20), 2, (240, 150, 50), 14, open_=pose == "fire")
    pouch = 18 if pose == "wind" else 12
    if v <= 1:
        bx = hx + (0 if v == 0 else 5)
        pygame.draw.ellipse(s, (240, 120, 60), (bx - 7, hy + 8, 14, pouch))
    elif v == 2:
        pygame.draw.ellipse(s, (240, 120, 60), (hx + 7, hy + 4, 14, pouch * 2 // 3))
    if pose == "fire" and tip:
        pygame.draw.ellipse(s, (250, 245, 230), (tip[0] - 5, tip[1] - 6, 10, 12))
        pygame.draw.circle(s, (255, 120, 20), (tip[0], tip[1] - 6), 3)
    return s


def gosling(pose, v=0):
    """Hell gosling: small, fast, bitey."""
    s = S(28, 26)
    if pose.startswith("d"):
        return dead_pile(s, (230, 200, 60), int(pose[1]))
    step = {"walk0": 1, "walk1": -1}.get(pose, 0)
    body = (240, 210, 70) if pose != "pain" else (255, 255, 200)
    feet(s, 14, 25, 4, step, ORANGE, 3)
    pygame.draw.ellipse(s, body, (4, 10, 20, 14))
    hx, hy = 14 + view_shift(v), 9
    pygame.draw.circle(s, body, (hx, hy), 7)
    bird_face(s, hx, hy, 7, v, (200, 0, 0), 2, ORANGE, 4, open_=pose in ("bite0", "bite1"))
    return s


def heron(pose, v=0):
    """Heron Wraith: tall frost caster."""
    s = S(40, 84)
    if pose.startswith("d"):
        return dead_pile(s, (120, 140, 170), int(pose[1]), wide=True)
    step = {"walk0": 2, "walk1": -2}.get(pose, 0)
    body = (120, 140, 170) if pose != "pain" else (210, 220, 240)
    for side in (-1, 1):
        x = 20 + side * 5 + step * side
        pygame.draw.line(s, (60, 60, 70), (x, 56), (x, 82), 2)
        pygame.draw.line(s, (60, 60, 70), (x - 4, 83), (x + 4, 83), 2)
    pygame.draw.ellipse(s, body, (6, 32, 28, 26))
    if pose in ("wind", "fire"):
        pygame.draw.polygon(s, (90, 105, 130), [(8, 40), (0, 14), (12, 34)])
        pygame.draw.polygon(s, (90, 105, 130), [(32, 40), (40, 14), (28, 34)])
    hx, hy = 20 + view_shift(v), 11
    pygame.draw.line(s, body, (20, 34), (hx, 14), 5)
    pygame.draw.circle(s, body, (hx, hy), 6)
    back = -1 if v in (1, 2, 3) else 1
    pygame.draw.line(s, (40, 40, 60), (hx - 6 * back if v else hx - 6, hy - 4), (hx - 14 * back if v else hx - 14, hy - 7), 2)
    bird_face(s, hx, hy, 6, v, (120, 230, 255), 1, (230, 200, 80), 11)
    glow = {"wind": 4, "fire": 8}.get(pose, 0)
    if glow:
        gx = 20 + view_shift(v) * 2
        pygame.draw.circle(s, (150, 230, 255), (gx, 26), glow)
        pygame.draw.circle(s, (255, 255, 255), (gx, 26), glow // 2)
    return s


def honkmother(pose, v=0):
    """THE HONKMOTHER: crowned giant goose, the episode boss."""
    s = S(112, 112)
    if pose.startswith("d"):
        st = int(pose[1])
        dead_pile(s, (210, 205, 200), min(st, 2), wide=True)
        if st == 0:
            pygame.draw.circle(s, (255, 120, 20), (56, 60), 30)
            pygame.draw.circle(s, (255, 230, 120), (56, 60), 18)
        return s
    step = {"walk0": 5, "walk1": -5}.get(pose, 0)
    body = (238, 234, 226) if pose != "pain" else (255, 170, 170)
    feet(s, 56, 111, 22, step, ORANGE, 12)
    pygame.draw.ellipse(s, (200, 196, 190), (4, 46, 30, 44))
    pygame.draw.ellipse(s, (200, 196, 190), (78, 46, 30, 44))
    if pose in ("atk0", "atk1"):
        pygame.draw.polygon(s, (215, 210, 205), [(18, 60), (0, 10), (30, 46)])
        pygame.draw.polygon(s, (215, 210, 205), [(94, 60), (111, 10), (82, 46)])
    pygame.draw.ellipse(s, body, (14, 44, 84, 62))
    if v < 3:
        pygame.draw.ellipse(s, (170, 20, 30), (34 + view_shift(v) * 2, 62, 44, 30), 4)
    hx, hy = 56 + view_shift(v) * 3, 30
    pygame.draw.circle(s, body, (hx, hy), 20)
    pygame.draw.polygon(s, (230, 180, 40), [(hx - 18, hy - 14), (hx - 14, hy - 32), (hx - 6, hy - 20), (hx, hy - 36),
                                            (hx + 6, hy - 20), (hx + 14, hy - 32), (hx + 18, hy - 14)])
    for gx in (-10, 0, 10):
        pygame.draw.circle(s, (200, 30, 40), (hx + gx, hy - 22), 3)
    tip = bird_face(s, hx, hy, 20, v, (255, 140, 20), 4, ORANGE, 18, open_=pose in ("atk0", "atk1"),
                    brow=(40, 10, 10))
    if pose == "atk1" and tip:
        pygame.draw.circle(s, (255, 200, 60), tip, 6)
    return s


VEST_COLORS = [((40, 150, 130), (150, 230, 210)),    # P1 teal
               ((220, 120, 30), (255, 200, 140)),    # P2 orange
               ((130, 60, 190), (210, 170, 255))]    # P3 purple


def coop_goose(pose, vest=0, weapon="honker", v=0):
    """A co-op player: a white goose in a coloured vest, holding their current weapon, facing direction v."""
    vest_c, vest_hi = VEST_COLORS[vest % len(VEST_COLORS)]
    s = S(44, 60)
    if pose.startswith("d"):
        return dead_pile(s, (240, 240, 232), int(pose[1]))
    step = {"walk0": 3, "walk1": -3}.get(pose, 0)
    white = (245, 245, 238) if pose != "pain" else (255, 170, 170)
    firing = pose == "fire"
    if v >= 3:
        held_weapon(s, weapon, v, 24, 41, firing)
    feet(s, 22, 59, 7, step)
    pygame.draw.ellipse(s, white, (6, 28, 32, 28))
    pygame.draw.polygon(s, vest_c, [(9, 34), (35, 34), (33, 52), (11, 52)])
    for y in (39, 45):
        pygame.draw.line(s, vest_hi, (11, y), (33, y), 1)
    if v >= 3:
        pygame.draw.line(s, vest_hi, (22, 34), (22, 52), 1)     # back seam
    sh = view_shift(v)
    for i in range(10):
        pygame.draw.circle(s, white, (int(22 + sh * i / 9), 30 - i * 2), 5)
    hx, hy = 22 + sh, 9
    pygame.draw.circle(s, white, (hx, hy), 7)
    bird_face(s, hx, hy, 7, v, (20, 20, 20), 1, ORANGE, 6, open_=firing and weapon == "peck")
    if v < 3:
        held_weapon(s, weapon, v, 24, 41, firing)
    return s


def darker(c, k=0.72):
    return tuple(int(v * k) for v in c[:3])


def bird_face(s, hx, hy, r, v, eye, eye_r, beak, blen, open_=False, glow=None, brow=None, closed=False):
    """Eyes + beak for a bird head seen from view v: 0 front, 1 three-quarter, 2 side, 3 back-quarter, 4 back.
    Side views face +x (the caller mirrors the whole sprite for the other side).
    Returns the beak tip (x, y), or None when the face is turned away."""
    if v >= 3:
        if v == 3:   # just the tip of the beak past the cheek
            pygame.draw.polygon(s, beak, [(hx + r - 1, hy), (hx + r - 1, hy + 3), (hx + r + max(2, blen // 3), hy + 2)])
        return None
    ey = int(hy - r * 0.2)
    if v == 0:
        eyes, bx = [hx - r * 0.42, hx + r * 0.42], hx
    elif v == 1:
        eyes, bx = [hx + r * 0.0, hx + r * 0.58], hx + r * 0.5
    else:
        eyes, bx = [hx + r * 0.38], None
    for i, ex in enumerate(eyes):
        ex = int(ex)
        if closed:
            pygame.draw.line(s, (30, 0, 0), (ex - eye_r - 1, ey), (ex + eye_r + 1, ey + 1), 2)
        else:
            pygame.draw.circle(s, eye, (ex, ey), eye_r)
        if brow:
            right_eye = (v == 0 and i == 1)
            d = -1 if right_eye else 1
            pygame.draw.line(s, brow, (ex - 3 * d, ey - eye_r - 2), (ex + 2 * d, ey - eye_r), 2)
    dk = darker(beak)
    if bx is not None:
        w = r * (0.6 if v == 0 else 0.5)
        if open_:
            pygame.draw.polygon(s, beak, [(bx - w, hy + 1), (bx + w, hy + 1), (bx, hy + 1 + blen * 0.5)])
            pygame.draw.ellipse(s, (70, 0, 10), (bx - w * 0.7, hy + 2, w * 1.4, max(3, blen * 0.7)))
            pygame.draw.polygon(s, dk, [(bx - w * 0.8, hy + 2 + blen * 0.6), (bx + w * 0.8, hy + 2 + blen * 0.6),
                                        (bx, hy + 2 + blen)])
        else:
            pygame.draw.polygon(s, beak, [(bx - w, hy + 1), (bx + w, hy + 1), (bx, hy + 1 + blen)])
            pygame.draw.line(s, dk, (bx - w * 0.7, hy + 3), (bx + w * 0.7, hy + 3), 1)
        tip = (int(bx), int(hy + 2 + blen * 0.55))
    else:
        x0 = hx + r * 0.7
        if open_:
            pygame.draw.polygon(s, beak, [(x0, hy - 1), (x0, hy + 2), (x0 + blen, hy)])
            pygame.draw.polygon(s, (70, 0, 10), [(x0, hy + 2), (x0, hy + 3), (x0 + blen * 0.8, hy + 3)])
            pygame.draw.polygon(s, dk, [(x0, hy + 3), (x0, hy + 6), (x0 + blen * 0.8, hy + 5)])
        else:
            pygame.draw.polygon(s, beak, [(x0, hy - 1), (x0, hy + 4), (x0 + blen, hy + 2)])
        tip = (int(x0 + blen), int(hy + 2))
    if glow:
        pygame.draw.circle(s, glow, tip, max(2, int(r * 0.4)))
    return tip


WEAPON_LEN = {"honker": 16, "egggun": 16, "flinger": 16, "bazooka": 20, "megahonk": 18}


def weapon_profile(s, w, x0, y, L, firing):
    """Side view of a held weapon pointing +x, starting at x0."""
    if w == "honker":
        pygame.draw.rect(s, (200, 160, 50), (x0, y - 1, int(L * 0.6), 3))
        pygame.draw.polygon(s, (225, 185, 60), [(x0 + L * 0.6, y - 1), (x0 + L, y - 5), (x0 + L, y + 6), (x0 + L * 0.6, y + 2)])
    elif w == "egggun":
        pygame.draw.rect(s, (120, 75, 40), (x0 - 5, y - 1, 7, 5))
        pygame.draw.rect(s, (185, 145, 55), (x0, y - 3, L, 2))
        pygame.draw.rect(s, (185, 145, 55), (x0, y + 1, L, 2))
        pygame.draw.ellipse(s, (250, 245, 230), (x0 + 3, y - 1, 5, 4))
    elif w == "flinger":
        pygame.draw.circle(s, (60, 60, 66), (int(x0 + 3), int(y)), 4)
        for i in range(3):
            pygame.draw.rect(s, (120, 120, 128), (x0 + 6, y - 3 + i * 2, L - 6, 1))
        pygame.draw.polygon(s, (240, 240, 232), [(x0 + L - 3, y - 4), (x0 + L, y - 6), (x0 + L, y - 3)])
    elif w == "bazooka":
        pygame.draw.rect(s, (95, 75, 52), (x0 - 4, y - 3, L + 4, 6))
        pygame.draw.ellipse(s, (205, 150, 70), (x0 + L - 2, y - 3, 7, 6))
    elif w == "megahonk":
        pygame.draw.polygon(s, (220, 180, 60), [(x0, y - 2), (x0 + L * 0.5, y - 2), (x0 + L, y - 8),
                                                (x0 + L, y + 9), (x0 + L * 0.5, y + 3), (x0, y + 3)])
        pygame.draw.ellipse(s, (90, 255, 160), (x0 + L - 3, y - 6, 4, 13))
    if firing:
        pygame.draw.circle(s, (255, 240, 150), (int(x0 + L + 3), int(y)), 5)
        pygame.draw.circle(s, (255, 255, 230), (int(x0 + L + 3), int(y)), 2)


def weapon_endon(s, w, cx, cy, firing):
    """Front view: the weapon is pointed straight at you."""
    if w == "honker":
        pygame.draw.circle(s, (225, 185, 60), (cx, cy), 6)
        pygame.draw.circle(s, (60, 35, 10), (cx, cy), 3)
    elif w == "egggun":
        for dx in (-3, 3):
            pygame.draw.circle(s, (185, 145, 55), (cx + dx, cy), 3)
            pygame.draw.circle(s, (40, 25, 10), (cx + dx, cy), 1)
    elif w == "flinger":
        pygame.draw.circle(s, (60, 60, 66), (cx, cy), 6)
        for dx, dy in ((-2, -2), (2, -2), (0, 2)):
            pygame.draw.circle(s, (130, 130, 138), (cx + dx, cy + dy), 2)
            pygame.draw.circle(s, (20, 20, 22), (cx + dx, cy + dy), 1)
    elif w == "bazooka":
        pygame.draw.circle(s, (95, 75, 52), (cx, cy), 6)
        pygame.draw.circle(s, (205, 150, 70), (cx, cy), 4)
    elif w == "megahonk":
        pygame.draw.circle(s, (220, 180, 60), (cx, cy), 8)
        pygame.draw.circle(s, (90, 255, 160), (cx, cy), 5)
    if firing:
        pygame.draw.circle(s, (255, 240, 150), (cx, cy), 8)
        pygame.draw.circle(s, (255, 255, 230), (cx, cy), 4)


def held_weapon(s, w, v, cx, cy, firing):
    if w == "peck":
        return
    L = WEAPON_LEN[w]
    if v == 0:
        weapon_endon(s, w, cx, cy, firing)
    elif v in (1, 3):
        weapon_profile(s, w, cx - 2, cy, int(L * 0.7), firing and v == 1)
    elif v == 2:
        weapon_profile(s, w, cx - 4, cy, L, firing)
    else:                               # from behind: only the muzzle pokes out past the shoulder
        weapon_profile(s, w, cx + 6, cy - 2, int(L * 0.5), False)


def view_shift(v):
    return (0, 2, 4, 2, 0)[v]


# --- enemies with facing --------------------------------------------------------


def item2(kind):
    if kind == "downjacket":
        s = S(28, 24)
        pygame.draw.polygon(s, (60, 90, 220), [(4, 4), (10, 1), (14, 6), (18, 1), (24, 4), (24, 23), (4, 23)])
        for y in range(6, 22, 5):
            pygame.draw.line(s, (150, 180, 255), (5, y), (23, y), 2)
        return s
    if kind == "eggcrate":
        s = S(30, 18)
        pygame.draw.rect(s, (150, 110, 60), (1, 5, 28, 13))
        for x in range(5, 27, 6):
            pygame.draw.ellipse(s, (250, 245, 230), (x - 3, 0, 7, 9))
        return s
    if kind in ("baguette", "baguettes"):
        n = 1 if kind == "baguette" else 4
        s = S(30, 6 + 5 * n)
        for i in range(n):
            pygame.draw.ellipse(s, (205, 150, 70), (1, 2 + i * 5, 28, 7))
            for x in (7, 14, 21):
                pygame.draw.line(s, (240, 210, 150), (x, 3 + i * 5), (x + 3, 7 + i * 5), 1)
        return s
    if kind in ("corn", "cornsack"):
        if kind == "corn":
            s = S(10, 18)
            pygame.draw.ellipse(s, (250, 210, 40), (1, 1, 8, 16))
            pygame.draw.line(s, (90, 160, 40), (1, 16), (5, 6), 2)
            return s
        s = S(24, 22)
        pygame.draw.ellipse(s, (170, 140, 90), (1, 4, 22, 18))
        for x in (6, 11, 16):
            pygame.draw.ellipse(s, (250, 210, 40), (x - 2, 0, 5, 9))
        return s
    if kind == "flinger":
        s = S(40, 16)
        for y in (3, 7, 11):
            pygame.draw.line(s, (90, 90, 96), (14, y), (38, y), 3)
        pygame.draw.rect(s, (60, 60, 66), (2, 2, 14, 12))
        pygame.draw.polygon(s, (240, 240, 232), [(30, 2), (38, 0), (36, 6)])
        return s
    if kind == "bazooka":
        s = S(44, 14)
        pygame.draw.rect(s, (90, 70, 50), (2, 3, 40, 9), border_radius=4)
        pygame.draw.ellipse(s, (205, 150, 70), (32, 1, 12, 12))
        pygame.draw.rect(s, (60, 45, 30), (14, 10, 6, 4))
        return s
    if kind == "megahonk":
        s = S(44, 26)
        pygame.draw.polygon(s, (220, 180, 60), [(4, 8), (24, 8), (42, 0), (42, 26), (24, 18), (4, 18)])
        pygame.draw.ellipse(s, (90, 255, 160), (34, 4, 8, 18))
        pygame.draw.rect(s, (90, 70, 40), (6, 18, 10, 7))
        return s
    if kind == "rkey":
        s = S(12, 16)
        pygame.draw.rect(s, (230, 40, 40), (1, 1, 10, 14), border_radius=2)
        pygame.draw.rect(s, (255, 255, 255), (1, 1, 10, 14), 1, border_radius=2)
        pygame.draw.circle(s, (40, 30, 20), (6, 9), 2)
        return s
    if kind == "rage":
        s = S(22, 18)
        pygame.draw.rect(s, (170, 40, 30), (1, 3, 20, 15), border_radius=6)
        pygame.draw.rect(s, (250, 120, 90), (4, 6, 14, 9), border_radius=3)
        pygame.draw.line(s, (255, 255, 255), (7, 8), (14, 13), 2)
        pygame.draw.line(s, (255, 255, 255), (14, 8), (7, 13), 2)
        return s
    if kind == "goldegg":
        s = S(16, 20)
        pygame.draw.ellipse(s, (255, 200, 30), (1, 1, 14, 19))
        pygame.draw.ellipse(s, (255, 250, 190), (4, 3, 5, 7))
        return s
    if kind == "boots":
        s = S(24, 18)
        for x in (2, 13):
            pygame.draw.rect(s, (230, 200, 30), (x, 1, 8, 13))
            pygame.draw.rect(s, (230, 200, 30), (x, 11, 10, 6))
        return s
    if kind == "parkmap":
        s = S(22, 18)
        pygame.draw.rect(s, (230, 220, 180), (1, 1, 20, 16))
        pygame.draw.line(s, (60, 130, 60), (3, 12), (18, 4), 2)
        pygame.draw.rect(s, (200, 40, 40), (12, 8, 3, 3))
        return s
    raise KeyError(kind)


def decor2(kind):
    if kind == "eggpile":
        s = S(34, 16)
        for x, y in ((5, 8), (13, 6), (21, 8), (29, 9), (9, 2), (18, 1), (25, 3)):
            pygame.draw.ellipse(s, (235, 225, 200), (x - 4, y, 9, 11))
            pygame.draw.ellipse(s, (180, 160, 130), (x - 4, y, 9, 11), 1)
        return s
    if kind == "candle":
        s = S(12, 40)
        pygame.draw.rect(s, (200, 190, 170), (3, 10, 6, 30))
        pygame.draw.circle(s, (255, 170, 40), (6, 6), 4)
        pygame.draw.circle(s, (255, 250, 200), (6, 6), 2)
        return s
    if kind == "snowman":
        s = S(32, 48)
        pygame.draw.circle(s, (240, 245, 255), (16, 36), 12)
        pygame.draw.circle(s, (240, 245, 255), (16, 16), 9)
        pygame.draw.polygon(s, ORANGE, [(12, 17), (20, 17), (16, 24)])
        for ex in (13, 19):
            pygame.draw.circle(s, (20, 20, 20), (ex, 13), 1)
        return s
    raise KeyError(kind)


def fx2(kind, frame):
    if kind == "eggbomb":
        s = S(14, 16)
        pygame.draw.ellipse(s, (250, 245, 230), (2, 1, 10, 14))
        pygame.draw.circle(s, (255, 120, 20) if frame else (255, 220, 60), (7, 2), 3)
        return s
    if kind == "icebolt":
        s = S(14, 14)
        pygame.draw.circle(s, (120, 220, 255), (7, 7), 6 - frame)
        pygame.draw.circle(s, (255, 255, 255), (7, 7), 3)
        return s
    if kind == "rocket":
        s = S(20, 12)
        pygame.draw.ellipse(s, (205, 150, 70), (2, 2, 16, 8))
        pygame.draw.circle(s, (255, 200, 60) if frame else (255, 120, 20), (3, 6), 3)
        return s
    if kind == "megaring":
        s = S(40, 40)
        pygame.draw.circle(s, (90, 255, 160), (20, 20), 18 - frame * 2, 4)
        pygame.draw.circle(s, (255, 240, 120), (20, 20), 10 + frame * 2, 3)
        pygame.draw.circle(s, (255, 255, 255), (20, 20), 5)
        return s
    if kind == "megaboom":
        s = S(80, 80)
        rr = 14 + frame * 11
        pygame.draw.circle(s, (90, 255, 160, 220 - frame * 50), (40, 40), rr)
        pygame.draw.circle(s, (255, 250, 200, 230 - frame * 60), (40, 40), max(3, rr - 12))
        return s
    if kind == "telefog":
        s = S(30, 50)
        for i in range(8):
            y = 48 - (i * 6 + frame * 5) % 48
            pygame.draw.circle(s, (120, 255, 170), (8 + (i * 7) % 16, y), 3 - frame % 2)
        return s
    raise KeyError(kind)


def weapon_view2(kind, frame):
    s = S(140, 90)
    if kind == "flinger":
        kick = (0, 4, 2)[frame]
        y = 36 + kick
        spin = frame % 2
        pygame.draw.rect(s, (60, 60, 66), (48, y + 24, 44, 40), border_radius=6)
        for i in range(3):
            bx = 54 + i * 12 + (4 if spin else 0)
            pygame.draw.rect(s, (110, 110, 118), (bx, y - 10, 8, 40))
            pygame.draw.ellipse(s, (30, 30, 34), (bx + 1, y - 13, 6, 6))
        pygame.draw.rect(s, (150, 120, 60), (44, y + 18, 52, 8))
        wing(s, 30, y + 40, flip=True)
        wing(s, 96, y + 40)
        if frame == 1:
            pygame.draw.circle(s, (255, 240, 150), (70, y - 18), 16)
            pygame.draw.circle(s, (255, 255, 230), (70, y - 18), 8)
        return s
    if kind == "bazooka":
        kick = (0, 10, 5, 0)[frame]
        y = 30 + kick
        pygame.draw.rect(s, (95, 75, 52), (52, y, 36, 70), border_radius=10)
        pygame.draw.ellipse(s, (40, 28, 18), (55, y - 4, 30, 16))
        if frame in (0, 3):
            pygame.draw.ellipse(s, (205, 150, 70), (60, y - 2, 20, 12))
        pygame.draw.rect(s, (60, 45, 30), (60, y + 46, 10, 18))
        wing(s, 88, y + 36)
        if frame == 1:
            pygame.draw.circle(s, (255, 200, 80), (70, y - 10), 20)
            pygame.draw.circle(s, (255, 250, 200), (70, y - 10), 10)
        return s
    if kind == "megahonk":
        kick = (0, 0, 12, 6)[frame]
        y = 30 + kick
        pygame.draw.polygon(s, (220, 180, 60), [(56, y + 70), (84, y + 70), (100, y - 6), (40, y - 6)])
        pygame.draw.ellipse(s, (120, 90, 30), (40, y - 14, 60, 18))
        glow = (90, 255, 160) if frame in (1, 2) else (40, 120, 80)
        pygame.draw.ellipse(s, glow, (48, y - 11, 44, 12))
        for vx in (62, 70, 78):
            pygame.draw.rect(s, (240, 210, 100), (vx, y + 20, 5, 14))
        wing(s, 30, y + 44, flip=True)
        wing(s, 92, y + 44)
        if frame == 2:
            for rr in (30, 22, 12):
                pygame.draw.circle(s, (120, 255, 180), (70, y - 26), rr, 3)
        return s
    raise KeyError(kind)


# ----------------------------------------------------------------- bundle
class Assets:
    # wall texture ids
    (BRICK, HEDGE, WOOD, METAL, GLASS, DOOR, YDOOR, BDOOR, SWOFF, SWON, CRACK, HEDGEX, HELL,
     SEWER, FACTORY, ICE, CASTLE, NEST, RDOOR) = range(19)
    CRACKABLE = (BRICK, HEDGE, WOOD, METAL, GLASS, HELL, SEWER, FACTORY, ICE, CASTLE, NEST)
    # flat ids
    GRASS, TILES, WOODF, METALF, BEAMS, LIGHTS, STONEF, SNOW, TELE, FACTF, PIPES, ASH = range(12)
    SLUDGE_FRAMES = 4
    SLUDGE = 12
    LAVA = 16

    @classmethod
    def crack(cls, base):
        """Texture id of a 'cracked' look-alike of a wall (for secret doors)."""
        return 19 + cls.CRACKABLE.index(base)

    def __init__(self, view_h):
        walls = [None] * 19
        walls[self.BRICK] = tex_brick()
        walls[self.HEDGE] = tex_hedge()
        walls[self.WOOD] = tex_wood()
        walls[self.METAL] = tex_metal()
        walls[self.GLASS] = tex_glass()
        walls[self.DOOR] = tex_door()
        walls[self.YDOOR] = tex_door(16, (240, 210, 40))
        walls[self.BDOOR] = tex_door(17, (60, 120, 255))
        walls[self.SWOFF] = tex_switch(False)
        walls[self.SWON] = tex_switch(True)
        walls[self.CRACK] = tex_brick(seed=1, cracked=True)
        walls[self.HEDGEX] = tex_hedge(gap=True)
        walls[self.HELL] = tex_hellrock()
        walls[self.SEWER] = tex_sewer()
        walls[self.FACTORY] = tex_factory()
        walls[self.ICE] = tex_ice()
        walls[self.CASTLE] = tex_castle()
        walls[self.NEST] = tex_nest()
        walls[self.RDOOR] = tex_door(18, (230, 40, 40))
        for i, b in enumerate(self.CRACKABLE):
            walls.append(crack_variant(walls[b], 100 + i))
        self.walls = np.stack(walls)
        flats = [flat_grass(), flat_tiles(), flat_woodfloor(), flat_metal(), flat_beams(), flat_ceillights(),
                 flat_stone(), flat_snow(), flat_tele(), flat_factory(), flat_pipes(), flat_ash()]
        flats += flat_sludge_frames(frames=self.SLUDGE_FRAMES)
        flats += flat_lava_frames(frames=4)
        self.flats = np.stack(flats)
        self.sky = make_sky(512, view_h)
        self.skies = {
            "hell": self.sky,
            "night": make_sky_pal(512, view_h, (8, 12, 40), (60, 80, 140), (30, 40, 80), (10, 14, 30), 21, stars=True),
            "fire": make_sky_pal(512, view_h, (30, 0, 0), (255, 110, 20), (80, 10, 0), (20, 4, 4), 22),
            "dusk": make_sky_pal(512, view_h, (40, 20, 60), (230, 120, 70), (90, 40, 80), (25, 12, 20), 23),
        }

        def dirframes(fn, poses):
            """Every pose from 5 views (front, 3/4, side, back-3/4, back); 3/4 and side views also mirrored.
            Keys look like 'walk0|2' or 'walk0|2m'; death poses ('d0'..) have no direction."""
            out = {}
            for p in poses:
                if p.startswith("d"):
                    out[p] = surf_arr(fn(p, 0))
                    continue
                for v in range(5):
                    surf = squash(fn(p, v), (1.0, 0.92, 0.82, 0.92, 1.0)[v])
                    out["%s|%d" % (p, v)] = surf_arr(surf)
                    if v in (1, 2, 3):
                        out["%s|%dm" % (p, v)] = surf_arr(pygame.transform.flip(surf, True, False))
            return out

        self.sprites = {
            "quackling": dirframes(quackling, ["walk0", "walk1", "aim", "fire", "pain", "d0", "d1", "d2"]),
            "fireswan": dirframes(fireswan, ["walk0", "walk1", "wind", "fire", "pain", "d0", "d1", "d2"]),
            "brute": dirframes(brute, ["walk0", "walk1", "bite0", "bite1", "pain", "d0", "d1", "d2"]),
            "mallard": dirframes(mallard, ["walk0", "walk1", "aim", "fire", "pain", "d0", "d1", "d2"]),
            "pelican": dirframes(pelican, ["walk0", "walk1", "wind", "fire", "pain", "d0", "d1", "d2"]),
            "gosling": dirframes(gosling, ["walk0", "walk1", "bite0", "bite1", "pain", "d0", "d1", "d2"]),
            "heron": dirframes(heron, ["walk0", "walk1", "wind", "fire", "pain", "d0", "d1", "d2"]),
            "honkmother": dirframes(honkmother, ["walk0", "walk1", "atk0", "atk1", "pain", "d0", "d1", "d2"]),
        }
        for i in range(len(VEST_COLORS)):
            g = {}
            for w in ("peck", "honker", "egggun", "flinger", "bazooka", "megahonk"):
                fr = dirframes(lambda p, v, i=i, w=w: coop_goose(p, i, w, v), ["walk0", "walk1", "fire", "pain", "d2"])
                g.update({("d2" if k == "d2" else "%s:%s" % (w, k)): a for k, a in fr.items()})
            self.sprites["goose%d" % i] = g
        for k in ("bread", "loaf", "crumbs", "vest", "feather", "pebbles", "pebblebox", "eggs", "egggun", "ykey", "bkey"):
            self.sprites[k] = {"0": surf_arr(item(k))}
        for k in ("downjacket", "eggcrate", "baguette", "baguettes", "corn", "cornsack", "flinger", "bazooka",
                  "megahonk", "rkey", "rage", "goldegg", "boots", "parkmap"):
            self.sprites[k] = {"0": surf_arr(item2(k))}
        for k in ("tree", "planter", "crate", "remains"):
            self.sprites[k] = {"0": surf_arr(decor(k))}
        for k in ("eggpile", "candle", "snowman"):
            self.sprites[k] = {"0": surf_arr(decor2(k))}
        for k in ("lamp", "barrel"):
            self.sprites[k] = {"0": surf_arr(decor(k, 0)), "1": surf_arr(decor(k, 1))}
        for k, n in (("puff", 3), ("blood", 3), ("fireball", 2), ("boom", 3), ("flash", 1)):
            self.sprites[k] = {str(i): surf_arr(fx(k, i)) for i in range(n)}
        for k, n in (("eggbomb", 2), ("icebolt", 2), ("rocket", 2), ("megaring", 2), ("megaboom", 3), ("telefog", 3)):
            self.sprites[k] = {str(i): surf_arr(fx2(k, i)) for i in range(n)}
        self.weapons = {
            "peck": [weapon_view("peck", i) for i in range(4)],
            "honker": [weapon_view("honker", i) for i in range(4)],
            "egggun": [weapon_view("egggun", i) for i in range(5)],
            "flinger": [weapon_view2("flinger", i) for i in range(3)],
            "bazooka": [weapon_view2("bazooka", i) for i in range(4)],
            "megahonk": [weapon_view2("megahonk", i) for i in range(4)],
        }
        self.faces = {}
        for pain in range(5):
            for look in (-1, 0, 1):
                self.faces[(look, pain, "normal")] = face(look, pain)
            for mood in ("ouch", "grin"):
                self.faces[(0, pain, mood)] = face(0, pain, mood)
        self.faces[(0, 4, "dead")] = face(0, 4, "dead")
