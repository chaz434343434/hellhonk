"""HELLHONK - an original goose-themed retro FPS.  Episode 1: FOWL WATERS (6 levels), solo or 2-player co-op.

Run:  python hellhonk.py                  (play)
      python hellhonk.py --selftest DIR   (headless checks + screenshots)
"""
import json
import math
import os
import random
import socket
import struct
import sys
import time
import zlib
from collections import deque

import numpy as np
import pygame

from assets import VEST_COLORS, Assets
from audio import SR, build_sfx, song_samples, to_sound
from level import Level, MH, MW, NUM_LEVELS
from updater import Updater, cleanup_old
from version import APP_VERSION

VERSION = "hellhonk-" + APP_VERSION       # co-op players must match exactly
PORT = 29331
VW, VH = 320, 168            # 3D view
SW, SH = 320, 200            # full low-res screen (view + 32px status bar)
WIN = (960, 720)             # 4:3 output, pixels 1.2x taller like old DOS games
PROJ_H, PROJ_V = 160.0, 192.0
EYE = 0.41
PR = 0.27                    # player radius
SKILLS = ["GENTLE GOSLING", "HONK IF YOU DARE", "PEACE WAS NEVER AN OPTION"]
MAX_PLAYERS = 3


def _save_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/HELLHONK")
    if os.environ.get("APPDATA"):
        return os.path.join(os.environ["APPDATA"], "HELLHONK")
    return os.path.expanduser("~/.local/share/hellhonk")


SAVE = os.path.join(_save_dir(), "save.json")

ENEMY = {
    "quackling": dict(hp=20, speed=2.0, r=.30, h=.55, pain=.78, sight="quack_sight", pains="pain_q", die="die_q",
                      idle="quack", drop="pebbles", poses=("aim", "fire"),
                      attacks=[dict(tl=[(.35, ("hit", 3, 1, 5, "quackshot"))], end=.6)]),
    "mallard": dict(hp=70, speed=2.2, r=.32, h=.62, pain=.67, sight="mallard_sight", pains="pain_q", die="die_q",
                    idle="quack", drop="pebbles", poses=("aim", "fire"),
                    attacks=[dict(tl=[(.3 + .1 * i, ("hit", 3, 1, 5, "mallard_shot")) for i in range(4)], end=.85)]),
    "fireswan": dict(hp=60, speed=2.0, r=.32, h=.85, pain=.78, sight="swan_sight", pains="pain_s", die="die_s",
                     idle="hiss", drop=None, poses=("wind", "fire"),
                     attacks=[dict(tl=[(.4, ("miss", "fireball", 1, 0, "fireball"))], end=.75),
                              dict(melee=True, tl=[(.35, ("bite", 3, 1, 8, "bite"))], end=.7)]),
    "brute": dict(hp=150, speed=3.4, r=.45, h=.75, pain=.70, sight="growl", pains="pain_b", die="die_b",
                  idle="growl", drop=None, poses=("bite0", "bite1"),
                  attacks=[dict(melee=True, tl=[(.25, ("bite", 4, 1, 10, "bite"))], end=.55)]),
    "pelican": dict(hp=100, speed=1.8, r=.38, h=.80, pain=.50, sight="pelican_sight", pains="pain_b", die="die_s",
                    idle="pelican_sight", drop=None, poses=("wind", "fire"),
                    attacks=[dict(tl=[(.5, ("miss", "eggbomb", 1, 0, "pelican_atk"))], end=.9)]),
    "gosling": dict(hp=12, speed=4.6, r=.20, h=.30, pain=.60, sight="peep", pains="peep", die="gosling_die",
                    idle="peep", drop=None, poses=("bite0", "bite1"),
                    attacks=[dict(melee=True, tl=[(.18, ("bite", 2, 1, 5, "bite"))], end=.4)]),
    "heron": dict(hp=120, speed=2.6, r=.30, h=1.0, pain=.40, sight="heron_sight", pains="pain_s", die="die_s",
                  idle="hiss", drop=None, poses=("wind", "fire"),
                  attacks=[dict(tl=[(.5, ("miss", "icebolt", 3, .16, "heron_atk"))], end=.85)]),
    "honkmother": dict(hp=3000, speed=2.6, r=.80, h=1.75, pain=.06, sight="boss_sight", pains="boss_pain",
                       die="boss_die", idle="growl", drop=None, poses=("atk0", "atk1"), boss=True,
                       attacks=[dict(weight=3, end=1.4, tl=[(t, ("miss", "fireball", 5, .14, "fireball")) for t in (.5, .8, 1.1)]),
                                dict(weight=2, end=1.2, tl=[(t, ("miss", "eggbomb", 3, .25, "pelican_atk")) for t in (.5, .9)]),
                                dict(weight=1, end=1.0, tl=[(.6, ("spawn", "gosling", 3, "boss_sight"))]),
                                dict(melee=True, end=.8, tl=[(.4, ("stomp", 70, "stomp"))])]),
}
MISSILES = {
    "fireball": dict(speed=7.0, dmg=(3, 1, 8), splash=None, h=.25, sprite="fireball", boom="boom"),
    "eggbomb": dict(speed=5.5, dmg=(2, 1, 5), splash=(1.7, 45), h=.25, sprite="eggbomb", boom="boom"),
    "icebolt": dict(speed=9.5, dmg=(2, 1, 6), splash=None, h=.2, sprite="icebolt", boom="puff"),
    "rocket": dict(speed=13.0, dmg=(20, 1, 8), splash=(2.5, 128), h=.22, sprite="rocket", boom="boom"),
    "megaring": dict(speed=10.0, dmg=(100, 2, 5), splash=(4.2, 300), h=.6, sprite="megaring", boom="megaboom",
                     noself=True),
}
ITEM_H = {"bread": .18, "loaf": .2, "crumbs": .08, "vest": .3, "feather": .2, "pebbles": .16, "pebblebox": .2,
          "eggs": .14, "egggun": .14, "ykey": .2, "bkey": .2, "rkey": .2, "downjacket": .3, "eggcrate": .18,
          "baguette": .1, "baguettes": .2, "corn": .2, "cornsack": .25, "flinger": .16, "bazooka": .16,
          "megahonk": .3, "rage": .2, "goldegg": .22, "boots": .2, "parkmap": .2}
DECOR = {"tree": (1.45, 0.3, True), "lamp": (1.1, 0.18, True), "planter": (.45, .3, True),
         "crate": (.6, .42, True), "remains": (.1, 0, False), "barrel": (.48, .25, True),
         "eggpile": (.18, 0, False), "candle": (.5, .12, True), "snowman": (.7, .3, True)}
COUNT_ITEMS = {"crumbs", "feather", "vest", "loaf", "downjacket", "rage", "goldegg", "boots", "parkmap"}
FX_H = {"puff": .12, "blood": .16, "boom": .8, "flash": .2, "megaboom": 1.5, "telefog": .8}

WEAPONS = {
    "peck": dict(ammo=None, cost=0, frames=[(1, .08), (2, .12), (3, .12), (0, .2)], fire_at=1),
    "honker": dict(ammo="pebbles", cost=1, frames=[(1, .07), (2, .1), (3, .1), (0, .12)], fire_at=0),
    "egggun": dict(ammo="eggs", cost=1, frames=[(1, .08), (2, .12), (0, .15), (3, .2), (4, .2), (0, .15)], fire_at=0),
    "flinger": dict(ammo="pebbles", cost=1, frames=[(1, .06), (2, .05)], fire_at=0),
    "bazooka": dict(ammo="baguettes", cost=1, frames=[(1, .1), (2, .15), (3, .2), (0, .25)], fire_at=0),
    "megahonk": dict(ammo="corn", cost=40, frames=[(1, .4), (2, .15), (3, .3), (0, .3)], fire_at=1),
}
WEAPON_ORDER = ["peck", "honker", "egggun", "flinger", "bazooka", "megahonk"]
FIRST_LEVEL = {"egggun": 0, "flinger": 1, "bazooka": 2, "megahonk": 4}   # level index where each is found
MAXAMMO = {"pebbles": 200, "eggs": 50, "baguettes": 50, "corn": 300}
LEVEL_AMMO_BONUS = {"pebbles": 60, "eggs": 12, "baguettes": 6, "corn": 80}   # given on entering each new level
AMMO_LABEL = (("pebbles", "PEBL"), ("eggs", "EGGS"), ("baguettes", "BAGT"), ("corn", "CORN"))
ONE_SHOT = ("use", "wnext", "wprev", "respawn") + tuple("w%d" % i for i in range(1, 7))

# per-player state; Game reads/writes these on whichever player is "current" (self.cur)
PFIELDS = frozenset((
    "px", "py", "ang", "vx", "vy", "health", "armor", "armor_class", "ammo", "owned", "weapon", "wstate",
    "wtimer", "wfi", "pending", "queued", "wraise", "refire", "rage", "invuln", "boots", "tint", "flash",
    "shake", "face", "bob", "bob_amt", "eye", "hurt_t", "tele_lock", "msgs", "dead", "dead_t", "snapshot", "carry",
    "calm_t", "regen_t"))
REGEN_DELAY = 4.0      # seconds without taking damage before regen starts
REGEN_EVERY = 1.5      # seconds per +1 health
REGEN_CAP = 100        # regen never goes above this


def shade_of(light, dist):
    s = light * np.clip(1.35 - dist / (5.0 + 12.0 * light * light), 0.1, 1.0)
    return np.floor(np.clip(s, 0.04, 1.0) * 20) / 20


def load_save():
    try:
        with open(SAVE) as f:
            d = json.load(f)
        return dict(unlocked=max(1, min(NUM_LEVELS, int(d.get("unlocked", 1)))), last_ip=str(d.get("last_ip", "")))
    except (OSError, ValueError, TypeError, AttributeError):
        return dict(unlocked=1, last_ip="")


def write_save(data):
    try:
        os.makedirs(os.path.dirname(SAVE), exist_ok=True)
        with open(SAVE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def local_ips():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:  # the address used for outbound traffic (no packets are sent)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    ips.discard("127.0.0.1")
    ips = {ip for ip in ips if not ip.startswith("169.254.")}      # self-assigned, never reachable

    def label(ip):
        if ip.startswith("26."):
            return "%s  (Radmin VPN)" % ip
        if ip.startswith("100.") and 64 <= int(ip.split(".")[1]) <= 127:
            return "%s  (Tailscale)" % ip
        if ip.startswith("192.168.137."):
            return "%s  (hotspot)" % ip
        return "%s  (local network)" % ip

    def rank(ip):   # VPN addresses first: that's what a friend in another house needs
        return (0 if ip.startswith(("26.", "100.")) else 2 if ip.startswith("192.168.137.") else 1, ip)

    return [label(ip) for ip in sorted(ips, key=rank)] or ["127.0.0.1"]


# =================================================================== networking
class Net:
    """Length-prefixed, zlib-compressed JSON messages over a non-blocking TCP socket."""

    def __init__(self, sock):
        self.sock = sock
        sock.setblocking(False)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.buf = b""
        self.out = b""
        self.alive = True

    def send(self, obj, droppable=False):
        if not self.alive or (droppable and len(self.out) > 256 * 1024):
            return
        data = zlib.compress(json.dumps(obj, separators=(",", ":")).encode(), 1)
        self.out += struct.pack("!I", len(data)) + data
        self.flush()

    def flush(self):
        try:
            while self.out:
                n = self.sock.send(self.out)
                if n <= 0:
                    break
                self.out = self.out[n:]
        except (BlockingIOError, InterruptedError):
            pass
        except OSError:
            self.alive = False

    def poll(self):
        msgs = []
        if not self.alive:
            return msgs
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    self.alive = False
                    break
                self.buf += chunk
        except (BlockingIOError, InterruptedError):
            pass
        except OSError:
            self.alive = False
        while len(self.buf) >= 4:
            n = struct.unpack("!I", self.buf[:4])[0]
            if len(self.buf) < 4 + n:
                break
            try:
                msgs.append(json.loads(zlib.decompress(self.buf[4:4 + n])))
            except (zlib.error, ValueError):
                self.alive = False
            self.buf = self.buf[4 + n:]
        self.flush()
        return msgs

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass


# =================================================================== world objects
class Player:
    def __init__(self, pid, remote=False):
        self.pid, self.remote = pid, remote
        self.px = self.py = self.ang = self.vx = self.vy = 0.0
        self.health, self.armor, self.armor_class = 100, 0, 1
        self.ammo = {k: 0 for k in MAXAMMO}
        self.owned = {w: w in ("peck", "honker") for w in WEAPON_ORDER}
        self.weapon = "honker"
        self.wstate, self.wtimer, self.wfi, self.pending, self.queued, self.wraise = "up", 0.0, 0, None, None, 0.0
        self.refire = 0.0
        self.rage = False
        self.invuln = self.boots = 0.0
        self.tint = [0.0, 0.0, 0.0]
        self.flash = self.shake = 0.0
        self.face = dict(look=0, t=1.0, mood="normal", mt=0.0)
        self.bob = self.bob_amt = 0.0
        self.eye = EYE
        self.hurt_t = 0.75
        self.tele_lock = None
        self.msgs = []
        self.dead = False
        self.dead_t = 0.0
        self.calm_t = self.regen_t = 0.0
        self.snapshot = None
        self.carry = None
        # network bookkeeping (remote players only)
        self.net = None
        self.snd = []
        self.fire_held = False
        self.events = []
        self.warp = [0, 0.0, 0.0, 0.0]
        self.warp_ack = 0
        self.moved = 0.0


class Mob:
    def __init__(self, kind, x, y):
        self.kind, self.x, self.y = kind, x, y
        self.z = 0.0
        self.alive = True
        self.removed = False


class Enemy(Mob):
    def __init__(self, kind, x, y, hp_mul=1.0):
        super().__init__(kind, x, y)
        self.st = ENEMY[kind]
        self.hp = int(self.st["hp"] * hp_mul)
        self.max_hp = self.hp
        self.r = self.st["r"]
        self.boss = self.st.get("boss", False)
        self.state = "idle"
        self.t = 0.0
        self.think = random.random() * 0.3
        self.cd = 0.5 + random.random()
        self.anim = random.random()
        self.zig = 0.0
        self.zigt = 0.0
        self.sees = False
        self.target = None
        self.atk = None
        self.done = 0
        self.last_ev = -9.0
        self.idle_snd = 3 + random.random() * 6


class Pickup(Mob):
    dropped = False


class Decor(Mob):
    def __init__(self, kind, x, y):
        super().__init__(kind, x, y)
        self.h, self.r, self.solid = DECOR[kind]
        self.hp = 20 if kind == "barrel" else None
        self.boom_t = -1.0


class Missile(Mob):
    def __init__(self, kind, x, y, dx, dy, owner):
        super().__init__(kind, x, y)
        self.spec = MISSILES[kind]
        self.dx, self.dy, self.owner = dx, dy, owner
        self.z = 0.36 if isinstance(owner, Player) else 0.42
        self.anim = 0.0


class Effect(Mob):
    def __init__(self, kind, x, y, z, frames, dur):
        super().__init__(kind, x, y)
        self.z, self.frames, self.dur, self.t = z, frames, dur, 0.0


# =================================================================== renderer
class Renderer:
    def __init__(self, A, L):
        self.A, self.L = A, L
        self.camx = (2 * (np.arange(VW) + 0.5) / VW - 1).astype(np.float64)
        self.ys = np.arange(VH)
        self.frame = np.zeros((VW, VH, 3), np.uint8)
        self.seen = np.zeros((MH, MW), bool)
        self.zbuf = np.full(VW, 1e9)
        self.sky = A.skies.get(L.sky, A.sky)

    def cast(self, px, py, rdx, rdy, solid, partial):
        mapx = np.full(VW, int(px), np.int32)
        mapy = np.full(VW, int(py), np.int32)
        with np.errstate(divide="ignore"):
            ddx = np.where(rdx == 0, 1e30, np.abs(1 / rdx))
            ddy = np.where(rdy == 0, 1e30, np.abs(1 / rdy))
        stx = np.where(rdx < 0, -1, 1).astype(np.int32)
        sty = np.where(rdy < 0, -1, 1).astype(np.int32)
        sdx = np.where(rdx < 0, (px - mapx) * ddx, (mapx + 1 - px) * ddx)
        sdy = np.where(rdy < 0, (py - mapy) * ddy, (mapy + 1 - py) * ddy)
        side = np.zeros(VW, np.int8)
        hitm = np.zeros(VW, bool)
        dd = np.full(VW, np.inf)
        dside = np.zeros(VW, np.int8)
        dcx = np.zeros(VW, np.int32)
        dcy = np.zeros(VW, np.int32)
        for _ in range(110):
            act = ~hitm
            if not act.any():
                break
            mx = act & (sdx < sdy)
            my = act & ~mx
            sdx[mx] += ddx[mx]
            mapx[mx] += stx[mx]
            side[mx] = 0
            sdy[my] += ddy[my]
            mapy[my] += sty[my]
            side[my] = 1
            np.clip(mapx, 0, MW - 1, out=mapx)
            np.clip(mapy, 0, MH - 1, out=mapy)
            pc = act & partial[mapy, mapx] & np.isinf(dd)
            if pc.any():
                dist = np.where(side == 0, sdx - ddx, sdy - ddy)
                dd[pc] = dist[pc]
                dside[pc] = side[pc]
                dcx[pc] = mapx[pc]
                dcy[pc] = mapy[pc]
            hitm |= act & solid[mapy, mapx]
        perp = np.maximum(np.where(side == 0, sdx - ddx, sdy - ddy), 0.02)
        return perp, side, mapx, mapy, stx, sty, dd, dside, dcx, dcy

    def texu(self, perp, side, rdx, rdy, px, py):
        wx = np.where(side == 0, py + perp * rdy, px + perp * rdx)
        wx -= np.floor(wx)
        u = (wx * 64).astype(np.int32)
        flip = ((side == 0) & (rdx > 0)) | ((side == 1) & (rdy < 0))
        return np.where(flip, 63 - u, u) & 63

    def render(self, g, px, py, ang, hz, eye, things):
        A, L = self.A, self.L
        dirx, diry = math.cos(ang), math.sin(ang)
        plx, ply = -diry, dirx
        rdx = dirx + plx * self.camx
        rdy = diry + ply * self.camx
        light = g.light_now
        fr = self.frame
        hzi = int(np.clip(hz, 1, VH - 1))

        fy = np.arange(hzi, VH)
        rowd = eye * PROJ_V / (fy - hz + 0.5)
        FX = px + rdx[:, None] * rowd[None, :]
        FY = py + rdy[:, None] * rowd[None, :]
        cx = np.clip(FX.astype(np.int32), 0, MW - 1)
        cy = np.clip(FY.astype(np.int32), 0, MH - 1)
        fid = L.floor[cy, cx]
        fid = np.where(fid == A.SLUDGE, A.SLUDGE + g.anim_frame, fid)
        fid = np.where(fid == A.LAVA, A.LAVA + g.anim_frame, fid)
        u = (FX * 64).astype(np.int32) & 63
        v = (FY * 64).astype(np.int32) & 63
        sh = shade_of(light[cy, cx], rowd[None, :])
        fr[:, hzi:] = (A.flats[fid, u, v] * sh[..., None]).astype(np.uint8)

        cyr = np.arange(0, hzi)
        rowc = (1 - eye) * PROJ_V / (hz - cyr - 0.5)
        CX = px + rdx[:, None] * rowc[None, :]
        CY = py + rdy[:, None] * rowc[None, :]
        cx = np.clip(CX.astype(np.int32), 0, MW - 1)
        cy = np.clip(CY.astype(np.int32), 0, MH - 1)
        cid = L.ceil[cy, cx]
        u = (CX * 64).astype(np.int32) & 63
        v = (CY * 64).astype(np.int32) & 63
        sh = shade_of(light[cy, cx], rowc[None, :])
        ceil = (A.flats[np.maximum(cid, 0), u, v] * sh[..., None]).astype(np.uint8)
        skyu = (((ang + np.arctan(self.camx)) / math.pi * 512) % 512).astype(np.int32)
        skyv = np.clip(cyr - int(hz - VH / 2), 0, VH - 1)
        sky = self.sky[skyu[:, None], skyv[None, :]]
        fr[:, :hzi] = np.where((cid < 0)[..., None], sky, ceil)

        solid, partial, dopen = g.solid_grid, g.partial_grid, g.open_grid
        perp, side, mx, my, stx, sty, dd, dside, dcx, dcy = self.cast(px, py, rdx, rdy, solid, partial)
        self.seen[my, mx] = True
        u = self.texu(perp, side, rdx, rdy, px, py)
        h = PROJ_V / perp
        top = hz - (1 - eye) * h
        y = self.ys[None, :]
        vv = ((y - top[:, None]) / h[:, None] * 64).astype(np.int32)
        np.clip(vv, 0, 63, out=vv)
        mask = (y >= top[:, None]) & (y < (hz + eye * h)[:, None])
        tex = L.wall[my, mx]
        tex = np.where(tex < 0, 0, tex)
        lx = np.where(side == 0, mx - stx, mx)
        ly = np.where(side == 1, my - sty, my)
        sh = shade_of(light[np.clip(ly, 0, MH - 1), np.clip(lx, 0, MW - 1)], perp) * np.where(side == 1, 0.8, 1.0)
        pix = (A.walls[tex[:, None], u[:, None], vv] * sh[:, None, None]).astype(np.uint8)
        fr[:] = np.where(mask[..., None], pix, fr)
        zb = perp.copy()

        cols = np.nonzero(np.isfinite(dd) & (dd < perp))[0]
        if cols.size:
            self.seen[dcy[cols], dcx[cols]] = True
            dp = dd[cols]
            op = dopen[dcy[cols], dcx[cols]]
            hh = PROJ_V / dp
            tp = hz - (1 - eye) * hh
            vb = hz + eye * hh - op * hh
            uu = self.texu(dp, dside[cols], rdx[cols], rdy[cols], px, py)
            m = (y >= tp[:, None]) & (y < vb[:, None])
            v2 = (((y - tp[:, None]) / hh[:, None] + op[:, None]) * 64).astype(np.int32)
            np.clip(v2, 0, 63, out=v2)
            t2 = L.wall[dcy[cols], dcx[cols]]
            lx2 = np.where(dside[cols] == 0, dcx[cols] - stx[cols], dcx[cols])
            ly2 = np.where(dside[cols] == 1, dcy[cols] - sty[cols], dcy[cols])
            s2 = shade_of(light[np.clip(ly2, 0, MH - 1), np.clip(lx2, 0, MW - 1)], dp)
            p2 = (A.walls[t2[:, None], uu[:, None], v2] * s2[:, None, None]).astype(np.uint8)
            fr[cols] = np.where(m[..., None], p2, fr[cols])
            zb[cols] = np.minimum(zb[cols], dp)
        self.zbuf = zb

        S = A.sprites
        items = []
        for m in things:
            rx, ry = m[2] - px, m[3] - py
            depth = rx * dirx + ry * diry
            if depth > 0.12:
                items.append((depth, rx * plx + ry * ply, m))
        items.sort(key=lambda t: -t[0])
        for depth, lat, (key, frm, wx, wy, z, wh, bright) in items:
            spr = S.get(key, {}).get(frm)
            if spr is not None:
                self.sprite(spr, wx, wy, z, wh, bright, depth, lat, hz, eye, light)
        return fr

    def sprite(self, arr, wx, wy, z, wh, bright, depth, lat, hz, eye, light):
        w, h = arr.shape[0], arr.shape[1]
        sx = VW / 2 * (1 + lat / depth)
        shp = wh * PROJ_V / depth
        swp = wh * (w / h) * PROJ_H / depth
        bot = hz + (eye - z) * PROJ_V / depth
        top = bot - shp
        x0 = sx - swp / 2
        xa, xb = max(0, int(math.ceil(x0))), min(VW, int(math.ceil(x0 + swp)))
        ya, yb = max(0, int(math.ceil(top))), min(VH, int(math.ceil(bot)))
        if xa >= xb or ya >= yb:
            return
        xs = np.arange(xa, xb)
        vis_cols = depth < self.zbuf[xa:xb]
        if not vis_cols.any():
            return
        us = np.clip(((xs - x0) / swp * w).astype(np.int32), 0, w - 1)
        vs = np.clip(((np.arange(ya, yb) - top) / shp * h).astype(np.int32), 0, h - 1)
        sub = arr[us[:, None], vs[None, :]]
        vis = (sub[..., 3] > 110) & vis_cols[:, None]
        s = 1.0 if bright else float(shade_of(light[int(np.clip(wy, 0, MH - 1)), int(np.clip(wx, 0, MW - 1))], depth))
        reg = self.frame[xa:xb, ya:yb]
        reg[vis] = (sub[..., :3][vis] * s).astype(np.uint8)


# =================================================================== game
class Game:
    # ---- per-player attribute delegation -------------------------------------
    def __getattr__(self, name):
        if name in PFIELDS:
            return getattr(self.__dict__["cur"], name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in PFIELDS:
            setattr(self.__dict__["cur"], name, value)
        else:
            object.__setattr__(self, name, value)

    def __init__(self, headless=False):
        self.me = self.cur = Player(0)
        self.players = [self.me]
        self.headless = headless
        self.role = "solo"            # solo | host | client
        self.net = None              # client: connection to the host
        self.listener = None         # host: accepts joiners (also mid-game)
        self.joiners = []            # host: [Net, connect_time] waiting for their hello
        pygame.mixer.pre_init(SR, -16, 2, 512)
        pygame.init()
        self.window = pygame.display.set_mode(WIN)
        pygame.display.set_caption("HELLHONK")
        self.screen = pygame.Surface((SW, SH))
        self.view = pygame.Surface((VW, VH))
        self.clock = pygame.time.Clock()
        self.A = Assets(VH)
        self.songs = {}
        self.song_now = None
        try:
            self.sfx = {k: to_sound(v, 0.8) for k, v in build_sfx().items()}
            pygame.mixer.set_reserved(1)
            self.music_ch = pygame.mixer.Channel(0)
            self.audio = True
        except pygame.error:
            self.audio = False
        self.music_on = True
        self.font_big = pygame.font.Font(None, 26)
        self.font = pygame.font.Font(None, 14)
        self.font_small = pygame.font.Font(None, 12)
        self.font_mid = pygame.font.Font(None, 20)
        self.font_title = pygame.font.Font(None, 64)
        self.bar_bg = self.make_bar()
        self.title_bg = self.make_title()
        self.mode = "title"
        self.menu_open = False
        self.menu_i = 0
        self.skill = 1
        self.save = load_save()
        self.unlocked = self.save["unlocked"]
        self.pick_level = self.unlocked - 1
        self.ip_text = self.save["last_ip"]
        self.banner = ""
        self.t = 0.0
        self.level = None
        self.level_idx = 0
        self.boss = None
        self.boss_frac = None
        self.automap = False
        self.updater = Updater()
        if not headless:
            cleanup_old()
            self.updater.check_async()
        self.play_song(0)

    # ------------------------------------------------------------- setup
    def play_song(self, i):
        if not self.audio:
            return
        if i not in self.songs:
            self.songs[i] = to_sound(song_samples(i), 1.0)
        if self.song_now == i and self.music_ch.get_busy():
            return
        self.song_now = i
        self.music_ch.stop()
        if self.music_on:
            self.music_ch.play(self.songs[i], loops=-1)
            self.music_ch.set_volume(0.45)

    def make_bar(self):
        s = pygame.Surface((SW, 32))
        wood = pygame.surfarray.make_surface(self.A.walls[Assets.WOOD])
        for x in range(0, SW, 64):
            s.blit(wood, (x, 0))
        dark = pygame.Surface((SW, 32), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 120))
        s.blit(dark, (0, 0))
        pygame.draw.line(s, (200, 170, 90), (0, 0), (SW, 0), 1)
        for x in (48, 104, 146, 174, 230, 250):
            pygame.draw.line(s, (30, 20, 12), (x, 1), (x, 31), 2)
            pygame.draw.line(s, (150, 120, 70), (x + 2, 1), (x + 2, 31), 1)
        for x, label in ((24, "AMMO"), (76, "HEALTH"), (125, "WINGS"), (202, "ARMOR")):
            t = self.font.render(label, False, (235, 210, 150))
            s.blit(t, (x - t.get_width() // 2, 22))
        return s

    def make_title(self):
        s = pygame.surfarray.make_surface(self.A.sky)
        s = pygame.transform.scale(s, (SW, SH))
        raw = self.font_title.render("HELLHONK", False, (255, 255, 255), (0, 0, 0))
        txt = pygame.Surface(raw.get_size())
        txt.blit(raw, (0, 0))
        arr = pygame.surfarray.pixels3d(txt)
        grad = np.linspace(0, 1, arr.shape[1])[None, :]
        mask = arr[..., 0] > 128
        arr[..., 0] = np.where(mask, 255, 0)
        arr[..., 1] = np.where(mask, (230 - 180 * grad).astype(np.uint8), 0)
        arr[..., 2] = np.where(mask, (60 - 50 * grad).astype(np.uint8), 0)
        del arr
        txt.set_colorkey((0, 0, 0))
        out = pygame.Surface((txt.get_width() + 8, txt.get_height() + 8), pygame.SRCALPHA)
        sh = txt.copy()
        sh.fill((30, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
        for ox, oy in ((0, 0), (8, 0), (0, 8), (8, 8), (4, 8), (8, 4)):
            out.blit(sh, (ox, oy))
        out.blit(txt, (4, 4))
        s.blit(out, (SW // 2 - out.get_width() // 2, 10))
        sub = self.font_mid.render("EPISODE 1: FOWL WATERS", False, (255, 220, 160))
        s.blit(sub, (SW // 2 - sub.get_width() // 2, 58))
        goose = pygame.transform.scale(self.A.faces[(0, 0, "grin")], (44, 51))
        s.blit(goose, (10, 92))
        s.blit(pygame.transform.flip(goose, True, False), (SW - 54, 92))
        return s

    def default_loadout(self, idx):
        owned = {w: (w in ("peck", "honker") or FIRST_LEVEL[w] < idx) for w in WEAPON_ORDER}
        ammo = {"pebbles": 50 if idx == 0 else 100, "eggs": 20 if owned["egggun"] else 0,
                "baguettes": 8 if owned["bazooka"] else 0, "corn": 80 if owned["megahonk"] else 0}
        return dict(health=100, armor=0 if idx == 0 else 50, armor_class=1, ammo=ammo, owned=owned,
                    weapon="egggun" if owned["egggun"] else "honker")

    def new_game(self, idx=0, skill=None):
        if skill is not None:
            self.skill = skill
        for p in self.players:
            p.carry = self.default_loadout(idx)
        self.total = dict(kills=0, kills_total=0, items=0, items_total=0, secrets=0, secrets_total=0, time=0.0)
        self.load_level(idx)

    def spawn_point(self, p):
        """Level start for P1; free spots beside/behind it for the others."""
        sx, sy, sa = self.level.start
        if p.pid == 0:
            return sx, sy, sa
        cands = []
        for d in (0.8, -0.8, 1.6, -1.6):
            cands += [(math.cos(sa + math.pi / 2) * d, math.sin(sa + math.pi / 2) * d),
                      (-math.cos(sa) * abs(d), -math.sin(sa) * abs(d))]
        placed = [(o.px, o.py) for o in self.players if o is not p and getattr(o, "placed", False)]
        for ox, oy in cands:
            x, y = sx + ox, sy + oy
            if not self.solid_at(x, y, PR + 0.05) and all((x - a) ** 2 + (y - b) ** 2 >= 0.36 for a, b in placed):
                return x, y, sa
        return sx, sy, sa

    def spawn_things(self, L, enemies=True):
        hp_mul = (0.7, 1.0, 1.3)[self.skill]
        if self.role == "host" and len(self.players) > 1:
            hp_mul *= 1.3
        self.enemies, self.pickups, self.decor = [], [], []
        skipped = 0
        for kind, x, y, flags in L.things:
            if "hard" in flags and self.skill < 2:
                continue
            if "notEasy" in flags and self.skill == 0:
                continue
            if kind in ENEMY:
                if self.skill == 0 and kind == "gosling":
                    skipped += 1
                    if skipped % 2:
                        continue
                if enemies:
                    self.enemies.append(Enemy(kind, x, y, hp_mul if ENEMY[kind].get("boss") else 1.0))
            elif kind in DECOR:
                self.decor.append(Decor(kind, x, y))
            elif enemies:
                self.pickups.append(Pickup(kind, x, y))

    def load_level(self, idx):
        self.loading_screen()
        L = self.level = Level(idx)
        self.level_idx = idx
        self.R = Renderer(self.A, L)
        self.keys = set()
        self.missiles, self.effects = [], []
        self.spawn_things(L)
        self.boss = next((e for e in self.enemies if e.boss), None)
        self.kills_total = len(self.enemies)
        self.items_total = sum(1 for p in self.pickups if p.kind in COUNT_ITEMS)
        self.kills = self.items = 0
        self.secrets_found = set()
        self.level_time = 0.0
        self.exit_t = -1.0
        self.anim_t = 0.0
        self.anim_frame = 0
        self.flicker = 1.0
        self.flow = np.full((MH, MW), 999, np.int32)
        self.flow_t = 0.0
        self.alldead_t = 0.0
        self.automap = False
        self.mode = "play"
        self.menu_open = False
        self.update_grids()
        self.light_now = L.light.copy()
        for p in self.players:
            p.placed = False
        for p in self.players:
            self.cur = p
            self.reset_player(p, p.carry)
            self.msg(L.name)
        self.cur = self.me
        self.grab(True)
        self.play_song(L.song)

    def reset_player(self, p, c):
        p.placed = False
        p.px, p.py, p.ang = self.spawn_point(p)
        p.placed = True
        p.vx = p.vy = 0.0
        p.health, p.armor, p.armor_class = c["health"], c["armor"], c["armor_class"]
        p.ammo = dict(c["ammo"])
        p.owned = dict(c["owned"])
        p.weapon = c["weapon"]
        p.snapshot = json.loads(json.dumps(c))
        p.wstate, p.wtimer, p.wfi, p.pending, p.queued, p.wraise = "up", 0.0, 0, None, None, 0.0
        p.refire = 0.0
        p.rage = False
        p.invuln = p.boots = 0.0
        p.tint = [0.0, 0.0, 0.0]
        p.flash = p.shake = 0.0
        p.face = dict(look=0, t=1.0, mood="normal", mt=0.0)
        p.bob = p.bob_amt = 0.0
        p.eye = EYE
        p.hurt_t = 0.75
        p.tele_lock = None
        p.msgs = []
        p.dead, p.dead_t = False, 0.0
        p.calm_t = p.regen_t = 0.0
        if p.remote:
            p.warp = [p.warp[0] + 1, p.px, p.py, p.ang]

    def respawn(self, p):
        c = json.loads(json.dumps(p.snapshot))
        c["health"] = 100
        self.reset_player(p, c)
        self.effects.append(Effect("telefog", p.px, p.py, 0.0, 3, 0.5))
        self.sound("teleport", p.px, p.py)

    def loading_screen(self):
        if self.headless:
            return
        self.screen.fill((0, 0, 0))
        self.text_c(self.screen, "LOADING...", SH // 2 - 6, (255, 200, 120), self.font_mid)
        self.present()

    def grab(self, on):
        if self.headless:
            return
        pygame.mouse.set_visible(not on)
        pygame.event.set_grab(on)
        pygame.mouse.get_rel()

    # ------------------------------------------------------------- helpers
    def msg(self, text, who=None):
        p = who or self.cur
        p.msgs.append([text, 3.0])
        p.msgs = p.msgs[-3:]

    def msg_all(self, text):
        for p in self.players:
            self.msg(text, p)

    def sound(self, name, x=None, y=None, vol=1.0, who=None):
        """Positional sounds are heard by everyone; sounds without a position belong to the current player."""
        if x is None and who is None:
            who = self.cur
        if self.role == "host":
            ev = [name, None if x is None else round(x, 2), None if y is None else round(y, 2), vol]
            for p in self.players:
                if p.remote and (who is None or who is p):
                    p.snd.append(ev)
        if who is not None and who is not self.me:
            return
        self.play_sfx(name, x, y, vol)

    def play_sfx(self, name, x, y, vol):
        if not self.audio or name not in self.sfx:
            return
        l = r = vol
        if x is not None:
            me = self.me
            dx, dy = x - me.px, y - me.py
            d = math.hypot(dx, dy)
            v = vol * max(0.0, 1 - d / 26)
            if v <= 0.02:
                return
            side = math.sin(math.atan2(dy, dx) - me.ang)
            l, r = v * (1 - max(0, side) * 0.6), v * (1 + min(0, side) * 0.6)
        ch = self.sfx[name].play()
        if ch:
            ch.set_volume(l, r)

    def update_grids(self):
        L = self.level
        op = np.zeros((MH, MW), np.float32)
        for d in L.doors:
            op[d.y, d.x] = d.open
        isdoor = L.door_at >= 0
        self.open_grid = op
        self.solid_grid = (L.wall >= 0) & (~isdoor | (op <= 0.0))
        self.partial_grid = isdoor & (op > 0.0) & (op < 1.0)

    def blocked_cell(self, x, y):
        return not self.level.passable(int(x), int(y))

    def solid_at(self, x, y, r):
        for ox in (-r, r):
            for oy in (-r, r):
                if self.blocked_cell(x + ox, y + oy):
                    return True
        return False

    def mob_block(self, me, x, y, r):
        for o in self.blockers():
            if o is me:
                continue
            rr = r + o.r
            dx, dy = x - o.x, y - o.y
            if dx * dx + dy * dy < rr * rr and dx * dx + dy * dy < (me.x - o.x) ** 2 + (me.y - o.y) ** 2:
                return True
        return False

    def blockers(self):
        for e in self.enemies:
            if e.alive:
                yield e
        for d in self.decor:
            if d.solid and not d.removed:
                yield d

    def try_move(self, me, nx, ny, r):
        moved = False
        if not self.solid_at(nx, me.y, r) and not self.mob_block(me, nx, me.y, r):
            me.x = nx
            moved = True
        if not self.solid_at(me.x, ny, r) and not self.mob_block(me, me.x, ny, r):
            me.y = ny
            moved = True
        return moved

    def ray_wall(self, x, y, dx, dy, maxd=64.0):
        mapx, mapy = int(x), int(y)
        ddx = abs(1 / dx) if dx else 1e30
        ddy = abs(1 / dy) if dy else 1e30
        stx = -1 if dx < 0 else 1
        sty = -1 if dy < 0 else 1
        sdx = (x - mapx) * ddx if dx < 0 else (mapx + 1 - x) * ddx
        sdy = (y - mapy) * ddy if dy < 0 else (mapy + 1 - y) * ddy
        while True:
            if sdx < sdy:
                d = sdx
                sdx += ddx
                mapx += stx
            else:
                d = sdy
                sdy += ddy
                mapy += sty
            if d > maxd:
                return maxd
            if not self.level.passable(mapx, mapy):
                return d

    def los(self, x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return True
        return self.ray_wall(x0, y0, dx / d, dy / d, d) >= d - 1e-6

    def bfs(self, starts, doors_ok, limit=999, keys=None):
        L = self.level
        dist = np.full((MH, MW), 999, np.int32)
        q = deque()
        for sx, sy in starts:
            dist[sy, sx] = 0
            q.append((sx, sy))
        while q:
            x, y = q.popleft()
            nd = dist[y, x] + 1
            if nd > limit:
                continue
            for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + ax, y + ay
                if not (0 <= nx < MW and 0 <= ny < MH) or dist[ny, nx] <= nd:
                    continue
                ok = L.passable(nx, ny)
                if not ok and doors_ok:
                    d = L.door_obj(nx, ny)
                    ok = d is not None and not d.secret and (d.key is None or (keys is not None and d.key in keys))
                if ok:
                    dist[ny, nx] = nd
                    q.append((nx, ny))
        return dist

    def living(self):
        return [p for p in self.players if not p.dead]

    # ------------------------------------------------------------- player actions (act on self.cur)
    def damage_player(self, dmg, src=None):
        if self.dead or self.mode != "play" or self.invuln > 0:
            return
        if self.skill == 0:
            dmg = max(1, dmg // 2)
        if self.armor > 0:
            saved = min(self.armor, dmg // 3 if self.armor_class == 1 else dmg // 2)
            self.armor -= saved
            dmg -= saved
        self.health -= dmg
        self.calm_t = 0.0
        self.tint[0] = min(0.8, self.tint[0] + dmg / 40)
        self.shake = max(self.shake, min(0.3, dmg / 100))
        if self.health <= 0:
            self.health = 0
            self.dead, self.dead_t = True, 0.0
            self.sound("player_die", self.px, self.py)
            if len(self.players) > 1:
                self.msg("You got cooked! Press USE to rejoin the fight.")
            return
        self.sound("player_pain")
        if dmg >= 20:
            self.face.update(mood="ouch", mt=1.0)
        elif src is not None and hasattr(src, "x"):
            side = math.sin(math.atan2(src.y - self.py, src.x - self.px) - self.ang)
            self.face.update(look=1 if side > 0.3 else (-1 if side < -0.3 else 0), t=0.8)

    def use(self):
        dx, dy = math.cos(self.ang), math.sin(self.ang)
        d = self.ray_wall(self.px, self.py, dx, dy, 1.6)
        if d >= 1.6:
            return
        cx, cy = int(self.px + dx * (d + 0.01)), int(self.py + dy * (d + 0.01))
        L = self.level
        door = L.door_obj(cx, cy)
        if door:
            if door.key and door.key not in self.keys:
                self.msg("You need a %s key to open this door." % door.key)
                self.sound("oof")
                return
            if door.dir <= 0 and door.open < 1:
                door.dir = 1
                self.sound("door", door.x + .5, door.y + .5)
            return
        if (cx, cy) == L.exit_cell and self.exit_t < 0:
            L.wall[cy, cx] = Assets.SWON
            self.sound("switch", cx + .5, cy + .5)
            self.exit_t = 1.0
            return
        self.sound("oof")

    def has_ammo(self, w):
        spec = WEAPONS[w]
        return spec["ammo"] is None or self.ammo[spec["ammo"]] >= spec["cost"]

    def fire(self):
        w = WEAPONS[self.weapon]
        if not self.has_ammo(self.weapon):
            self.sound("noammo")
            for cand in ("megahonk", "flinger", "egggun", "honker", "bazooka", "peck"):
                if self.owned[cand] and self.has_ammo(cand):
                    self.switch(cand)
                    break
            return
        self.wstate, self.wfi, self.wtimer = "fire", 0, w["frames"][0][1]
        if self.weapon == "megahonk":
            self.sound("megahonk", self.px, self.py)
        if w["fire_at"] == 0:
            self.shoot()

    def shoot(self):
        w = self.weapon
        spec = WEAPONS[w]
        if w == "peck":
            self.sound("peck", self.px, self.py)
            dmg = 2 * random.randint(1, 10) * (8 if self.rage else 1)
            if self.hitscan(self.ang + random.uniform(-0.05, 0.05), 1.15, dmg, puff=False):
                self.sound("punch", self.px, self.py)
            return
        if not self.has_ammo(w):
            return
        self.ammo[spec["ammo"]] -= spec["cost"]
        self.flash = 0.1
        self.alert()
        if w == "honker":
            self.sound("honker", self.px, self.py)
            spread = 0.0 if self.refire <= 0 else 0.06
            self.hitscan(self.ang + random.uniform(-spread, spread), 40, 5 * random.randint(1, 3))
            self.refire = 0.5
        elif w == "flinger":
            self.sound("flinger", self.px, self.py)
            spread = 0.0 if self.refire <= 0 else 0.07
            self.hitscan(self.ang + random.uniform(-spread, spread), 40, 5 * random.randint(1, 3))
            self.refire = 0.25
        elif w == "egggun":
            self.sound("egggun", self.px, self.py)
            for _ in range(7):
                self.hitscan(self.ang + random.uniform(-0.098, 0.098), 40, 5 * random.randint(1, 3))
        elif w == "bazooka":
            self.sound("rocket", self.px, self.py)
            self.spawn_missile("rocket", self.px, self.py, self.ang, self.cur)
        elif w == "megahonk":
            self.spawn_missile("megaring", self.px, self.py, self.ang, self.cur)
            self.shake = 0.25

    def spawn_missile(self, kind, x, y, a, owner, offset=0.35):
        m = Missile(kind, x + math.cos(a) * offset, y + math.sin(a) * offset, math.cos(a), math.sin(a), owner)
        self.missiles.append(m)
        return m

    def hitscan(self, a, maxd, dmg, puff=True):
        dx, dy = math.cos(a), math.sin(a)
        wd = self.ray_wall(self.px, self.py, dx, dy, maxd)
        best, bt = None, wd
        for o in list(self.enemies) + [d for d in self.decor if d.hp is not None and d.alive]:
            if not o.alive:
                continue
            rx, ry = o.x - self.px, o.y - self.py
            t = rx * dx + ry * dy
            if 0 < t < bt and abs(rx * dy - ry * dx) < o.r + 0.04:
                best, bt = o, t
        if best is not None:
            if isinstance(best, Enemy):
                self.effects.append(Effect("blood", best.x - dx * best.r, best.y - dy * best.r, 0.35, 3, 0.3))
                self.hurt_enemy(best, dmg)
            else:
                self.effects.append(Effect("puff", best.x - dx * best.r, best.y - dy * best.r, 0.3, 3, 0.25))
                self.hurt_barrel(best, dmg)
            return True
        if puff and wd < maxd:
            self.effects.append(Effect("puff", self.px + dx * (wd - 0.04), self.py + dy * (wd - 0.04), EYE - 0.05, 3, 0.25))
        return False

    def switch(self, name):
        if not self.owned.get(name) or name == self.weapon:
            return
        if self.wstate != "up":
            self.queued = name
            return
        self.queued = None
        self.pending = name
        self.wstate, self.wtimer = "lower", 0.15

    def alert(self):
        dist = self.bfs([(int(self.px), int(self.py))], False, 26)
        for e in self.enemies:
            if e.alive and e.state == "idle" and dist[int(e.y), int(e.x)] < 999:
                self.wake(e)

    # ------------------------------------------------------------- enemies
    def wake(self, e):
        e.state = "chase"
        e.t = 0
        e.cd = 0.3 + random.random() * 0.8
        self.sound(e.st["sight"], e.x, e.y)
        if e.boss:
            self.msg_all("THE HONKMOTHER AWAKENS!")

    def hurt_enemy(self, e, dmg):
        if not e.alive:
            return
        e.hp -= dmg
        if e.hp <= 0:
            e.alive = False
            e.state, e.t = "dying", 0.0
            self.kills += 1
            self.sound(e.st["die"], e.x, e.y)
            if e.st["drop"]:
                p = Pickup(e.st["drop"], e.x, e.y)
                p.dropped = True
                self.pickups.append(p)
            if e.boss:
                self.msg_all("THE HONKMOTHER IS SILENCED!")
                for p in self.players:
                    p.shake = 1.0
                for i in range(6):
                    a = i * 1.05
                    self.effects.append(Effect("megaboom", e.x + math.cos(a) * 0.6, e.y + math.sin(a) * 0.6, 0.2, 3, 0.9 + i * 0.1))
                for o in self.enemies:
                    if o.alive and o.kind == "gosling":
                        self.hurt_enemy(o, 999)
                self.exit_t = 4.0
            return
        if e.state == "idle":
            self.wake(e)
        if random.random() < e.st["pain"] and e.state != "pain":
            e.state, e.t = "pain", 0.0
            self.sound(e.st["pains"], e.x, e.y)

    def hurt_barrel(self, b, dmg):
        if b.boom_t >= 0 or not b.alive:
            return
        b.hp -= dmg
        if b.hp <= 0:
            b.boom_t = 0.18

    def explode(self, x, y, radius=2.3, power=90, src=None, noself=False, fxkind="boom", owner=None):
        self.effects.append(Effect(fxkind, x, y, 0.05, 3, 0.6 if fxkind == "megaboom" else 0.45))
        self.sound("megaboom" if fxkind == "megaboom" else "boom", x, y)
        keep = self.cur
        for p in self.players:
            if p.dead or noself:
                continue
            d = math.hypot(p.px - x, p.py - y)
            if fxkind == "megaboom" and d < 12:
                p.shake = max(p.shake, 0.5)
            if d < radius and self.los(x, y, p.px, p.py):
                self.cur = p
                self.damage_player(int(power * (1 - d / radius)))
        self.cur = keep
        targets = [("e", e) for e in self.enemies if e.alive and e is not owner] + \
                  [("b", d) for d in self.decor if d.hp is not None and d.alive and d.boom_t < 0 and d is not src]
        for kind, o in targets:
            d = math.hypot(o.x - x, o.y - y)
            if d >= radius or not self.los(x, y, o.x, o.y):
                continue
            dmg = int(power * (1 - d / radius))
            if kind == "e":
                self.hurt_enemy(o, dmg)
            else:
                self.hurt_barrel(o, dmg)

    def pick_target(self, e):
        alive = self.living()
        if not alive:
            return None
        if e.target in alive and e.think > 0:
            return e.target
        vis = [p for p in alive if self.los(e.x, e.y, p.px, p.py)]
        pool = vis or alive
        return min(pool, key=lambda p: (p.px - e.x) ** 2 + (p.py - e.y) ** 2)

    def think_enemy(self, e, dt):
        e.anim += dt
        st = e.st
        if e.state == "dying":
            e.t += dt
            return
        if not e.alive:
            return
        tgt = self.pick_target(e)
        if tgt is None:
            return
        e.target = tgt
        self.cur = tgt
        dx, dy = self.px - e.x, self.py - e.y
        dist = math.hypot(dx, dy)
        e.think -= dt
        if e.think <= 0:
            e.think = 0.2
            e.sees = dist < 40 and self.los(e.x, e.y, self.px, self.py)
        if e.state == "idle":
            if e.sees:
                self.wake(e)
            return
        e.idle_snd -= dt
        if e.idle_snd <= 0:
            e.idle_snd = 4 + random.random() * 8
            self.sound(st["idle"], e.x, e.y, 0.5)
        if e.state == "pain":
            e.t += dt
            if e.t > 0.22:
                e.state = "chase"
            return
        if e.state == "attack":
            self.attack_step(e, dt, dist)
            return
        e.cd -= dt
        if e.cd <= 0:
            e.cd = 0.3
            reach = e.r + PR + 0.38
            melee = [a for a in st["attacks"] if a.get("melee")]
            ranged = [a for a in st["attacks"] if not a.get("melee")]
            chance = 0.22 + 0.5 * max(0, 1 - dist / 14) + (0.35 if e.boss else 0)
            pick = None
            if melee and dist < reach:
                pick = random.choice(melee)
            elif ranged and e.sees and random.random() < chance:
                tot = sum(a.get("weight", 1) for a in ranged)
                rr = random.random() * tot
                for a in ranged:
                    rr -= a.get("weight", 1)
                    if rr <= 0:
                        pick = a
                        break
            if pick:
                e.state, e.t, e.atk, e.done, e.last_ev = "attack", 0.0, pick, 0, -9.0
                return
        if e.sees:
            tx, ty = self.px, self.py
        else:
            cx, cy = int(e.x), int(e.y)
            best, bv = None, self.flow[cy, cx]
            for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = self.flow[cy + ay, cx + ax]
                if v < bv:
                    best, bv = (cx + ax, cy + ay), v
            if best is None:
                return
            door = self.level.door_obj(*best)
            if door and door.open < 0.85:
                if door.key is None and not door.secret and door.dir <= 0:
                    door.dir = 1
                    self.sound("door", door.x + .5, door.y + .5)
                return
            tx, ty = best[0] + 0.5, best[1] + 0.5
        e.zigt -= dt
        if e.zigt <= 0:
            e.zigt = 0.5 + random.random() * 0.8
            e.zig = random.uniform(-0.9, 0.9)
        mx, my = tx - e.x, ty - e.y
        md = math.hypot(mx, my)
        if md < 0.05 or (e.sees and dist < e.r + PR + 0.15):
            return
        a = math.atan2(my, mx) + (e.zig if e.sees else 0)
        sp = st["speed"] * (1.25 if self.skill == 2 else 1.0) * dt
        if not self.try_move(e, e.x + math.cos(a) * sp, e.y + math.sin(a) * sp, e.r):
            e.zigt = 0

    def attack_step(self, e, dt, dist):
        e.t += dt
        atk = e.atk
        tl = atk["tl"]
        while e.done < len(tl) and e.t >= tl[e.done][0]:
            self.attack_event(e, tl[e.done][1], dist)
            e.done += 1
            e.last_ev = e.t
        if e.t >= atk["end"]:
            e.state = "chase"
            e.cd = (0.6 + random.random() * 0.6) if e.boss else (0.6 + random.random() * 1.4)

    def attack_event(self, e, ev, dist):
        kind = ev[0]
        a = math.atan2(self.py - e.y, self.px - e.x)
        if kind == "hit":
            _, mult, lo, hi, snd = ev
            self.sound(snd, e.x, e.y)
            if self.los(e.x, e.y, self.px, self.py):
                speed = math.hypot(self.vx, self.vy)
                p = max(0.2, 0.85 - dist * 0.035 - speed * 0.04)
                if random.random() < p:
                    self.damage_player(mult * random.randint(lo, hi), e)
        elif kind == "miss":
            _, mk, count, spread, snd = ev
            self.sound(snd, e.x, e.y)
            for i in range(count):
                off = (i - (count - 1) / 2) * spread
                self.spawn_missile(mk, e.x, e.y, a + off, e, e.r + 0.15)
        elif kind == "bite":
            _, mult, lo, hi, snd = ev
            if dist < e.r + PR + 0.55:
                self.sound(snd, e.x, e.y)
                self.damage_player(mult * random.randint(lo, hi), e)
        elif kind == "spawn":
            _, sk, count, snd = ev
            alive = sum(1 for o in self.enemies if o.alive and o.kind == sk)
            self.sound(snd, e.x, e.y, 0.7)
            for _ in range(count):
                if alive >= 14:
                    break
                ang = random.random() * math.tau
                sx, sy = e.x + math.cos(ang) * 1.4, e.y + math.sin(ang) * 1.4
                if self.blocked_cell(sx, sy):
                    continue
                g = Enemy(sk, sx, sy)
                g.state = "chase"
                self.enemies.append(g)
                self.kills_total += 1
                alive += 1
                self.effects.append(Effect("telefog", sx, sy, 0.0, 3, 0.5))
        elif kind == "stomp":
            _, power, snd = ev
            self.sound(snd, e.x, e.y)
            for p in self.players:
                if math.hypot(p.px - e.x, p.py - e.y) < 6:
                    p.shake = max(p.shake, 0.4)
            if dist < 2.4:
                self.damage_player(int(power * (1 - dist / 2.4)) + 5, e)

    # ------------------------------------------------------------- update
    def update(self, dt, inp):
        """One simulation step. `inp` is the local player's input; remote players use their queued input."""
        L = self.level
        self.t += dt
        self.level_time += dt
        self.anim_t += dt
        self.anim_frame = int(self.anim_t * 6) % Assets.SLUDGE_FRAMES
        if random.random() < dt * 8:
            self.flicker = random.choice((1.0, 1.0, 0.55, 0.8))
        lt = np.where(L.flicker, L.light * self.flicker, L.light)
        if any(p.flash > 0 for p in self.players):
            lt = np.minimum(1.0, lt + 0.25)
        self.light_now = lt

        for p in list(self.players):
            self.cur = p
            if p.remote:
                pin = {"fire": p.fire_held}
                for ev in p.events:
                    pin[ev] = True
                p.events = []
            else:
                pin = inp
            self.player_tick(dt, pin)
        self.cur = self.me

        changed = False
        for d in L.doors:
            if d.dir > 0:
                d.open = min(1.0, d.open + dt * 2.0)
                changed = True
                if d.open >= 1.0:
                    d.dir = 0
                    d.wait = 4.0
            elif d.dir < 0:
                if self.cell_occupied(d.x, d.y):
                    d.dir = 1
                else:
                    d.open = max(0.0, d.open - dt * 2.0)
                    changed = True
                    if d.open <= 0:
                        d.dir = 0
            elif d.open >= 1.0 and not d.secret:
                d.wait -= dt
                if d.wait <= 0 and not self.cell_occupied(d.x, d.y):
                    d.dir = -1
                    self.sound("doorshut", d.x + .5, d.y + .5)
        if changed:
            self.update_grids()

        self.flow_t -= dt
        if self.flow_t <= 0:
            self.flow_t = 0.4
            starts = [(int(p.px), int(p.py)) for p in self.living()] or [(int(self.me.px), int(self.me.py))]
            self.flow = self.bfs(starts, True)

        for e in list(self.enemies):
            self.think_enemy(e, dt)
        self.cur = self.me
        self.update_missiles(dt)
        for b in self.decor:
            if b.boom_t >= 0 and b.alive:
                b.boom_t -= dt
                if b.boom_t <= 0:
                    b.alive = False
                    b.removed = True
                    self.explode(b.x, b.y, src=b)
        for fx in self.effects:
            fx.t += dt
        self.effects = [e for e in self.effects if e.t < e.dur]
        self.boss_frac = (max(0, self.boss.hp) / self.boss.max_hp) if (
            self.boss and self.boss.state != "idle" and (self.boss.alive or self.boss.t < 1.5)) else None

        if len(self.players) > 1:
            if not self.living():
                self.alldead_t += dt
                if self.alldead_t > 3.0:
                    self.restart_level()
                    return
            else:
                self.alldead_t = 0.0

        if self.exit_t >= 0 and self.mode == "play":
            self.exit_t -= dt
            if self.exit_t < 0:
                self.finish_level()

    def player_tick(self, dt, inp):
        L = self.level
        self.tint[0] = max(0, self.tint[0] - dt * 1.2)
        self.tint[1] = max(0, self.tint[1] - dt * 1.5)
        self.tint[2] = max(0, self.tint[2] - dt * 2.0)
        self.flash = max(0, self.flash - dt)
        self.shake = max(0, self.shake - dt)
        self.refire = max(0, self.refire - dt)
        for m in self.msgs:
            m[1] -= dt
        self.msgs = [m for m in self.msgs if m[1] > 0]
        f = self.face
        f["t"] -= dt
        f["mt"] -= dt
        if f["mt"] <= 0:
            f["mood"] = "normal"
        if f["t"] <= 0:
            f["t"] = 0.8 + random.random() * 1.6
            f["look"] = random.choice((-1, 0, 0, 1))
        if self.dead:
            self.dead_t += dt
            self.eye = max(0.1, self.eye - dt * 0.4)
            self.tint[0] = max(self.tint[0], 0.45)
            if (inp.get("use") or inp.get("respawn")) and self.dead_t > 1.0:
                if len(self.players) > 1 and self.living():
                    self.respawn(self.cur)
                elif len(self.players) == 1:
                    self.restart_level()
            return
        # small passive regen once you've been out of trouble for a few seconds
        self.calm_t += dt
        if self.calm_t >= REGEN_DELAY and self.health < REGEN_CAP:
            self.regen_t += dt
            if self.regen_t >= REGEN_EVERY:
                self.regen_t -= REGEN_EVERY
                self.health += 1
        else:
            self.regen_t = 0.0
        for pw in ("invuln", "boots"):
            v = getattr(self.cur, pw)
            if v > 0:
                setattr(self.cur, pw, max(0.0, v - dt))
                if v > 3 >= v - dt:
                    self.msg("%s is wearing off..." % ("The golden egg" if pw == "invuln" else "Your rubber boots"))
        if self.cur.remote:
            self.remote_motion(dt)
        else:
            self.player_move(dt, inp)
        self.weapon_tick(dt, inp)
        if inp.get("use"):
            self.use()
        for i, name in enumerate(WEAPON_ORDER):
            if inp.get("w%d" % (i + 1)):
                self.switch(name)
        if inp.get("wnext") or inp.get("wprev"):
            owned = [w for w in WEAPON_ORDER if self.owned[w]]
            i = owned.index(self.weapon) + (1 if inp.get("wnext") else -1)
            self.switch(owned[i % len(owned)])
        self.pickup_check()
        cell = (int(self.px), int(self.py))
        if cell in L.secret_cells and L.secret_cells[cell] not in self.secrets_found:
            self.secrets_found.add(L.secret_cells[cell])
            self.msg("A secret is revealed!")
            self.sound("secret")
        if cell in L.tele and self.tele_lock != cell:
            tx, ty = L.tele[cell]
            self.effects.append(Effect("telefog", self.px, self.py, 0.0, 3, 0.5))
            self.px, self.py = tx + 0.5, ty + 0.5
            self.vx = self.vy = 0
            self.tele_lock = (tx, ty)
            self.tint[2] = 0.6
            self.sound("teleport")
            if self.cur.remote:
                p = self.cur
                p.warp = [p.warp[0] + 1, p.px, p.py, p.ang]
        elif self.tele_lock and cell != self.tele_lock:
            self.tele_lock = None
        dmg = int(L.hurt[cell[1], cell[0]])
        if dmg and self.boots <= 0:
            self.hurt_t += dt
            if self.hurt_t >= 1.0:
                self.hurt_t = 0
                self.sound("sludge")
                self.damage_player(dmg if self.skill else max(1, dmg // 2 + 1))
        else:
            self.hurt_t = 0.75

    def remote_motion(self, dt):
        p = self.cur
        spd = min(1.0, p.moved / max(dt, 1e-3) / 6.2)
        p.moved = 0.0
        p.bob += dt * 11 * min(1, spd * 1.5)
        p.bob_amt = spd

    def cell_occupied(self, cx, cy):
        if any(not p.dead and int(p.px) == cx and int(p.py) == cy for p in self.players):
            return True
        return any(o.alive and int(o.x) == cx and int(o.y) == cy for o in self.enemies)

    def player_move(self, dt, inp):
        self.ang = (self.ang + inp.get("turn", 0.0)) % (2 * math.pi)
        fwd, strafe = inp.get("fwd", 0), inp.get("strafe", 0)
        speed = 3.4 if inp.get("walk") else 6.2
        cs, sn = math.cos(self.ang), math.sin(self.ang)
        wx, wy = cs * fwd - sn * strafe, sn * fwd + cs * strafe
        n = math.hypot(wx, wy)
        if n > 1:
            wx, wy = wx / n, wy / n
        k = min(1.0, dt * 9)
        self.vx += (wx * speed - self.vx) * k
        self.vy += (wy * speed - self.vy) * k
        me = Mob("player", self.px, self.py)
        self.try_move(me, self.px + self.vx * dt, self.py + self.vy * dt, PR)
        self.px, self.py = me.x, me.y
        spd = math.hypot(self.vx, self.vy) / 6.2
        self.bob += dt * 11 * min(1, spd * 1.5)
        self.bob_amt = min(1.0, spd)

    def weapon_tick(self, dt, inp):
        w = WEAPONS[self.weapon]
        if self.wstate == "lower":
            self.wtimer -= dt
            self.wraise = 1 - max(0, self.wtimer) / 0.15
            if self.wtimer <= 0:
                self.weapon = self.pending
                self.wstate, self.wtimer = "raise", 0.15
        elif self.wstate == "raise":
            self.wtimer -= dt
            self.wraise = max(0, self.wtimer) / 0.15
            if self.wtimer <= 0:
                self.wstate, self.wraise = "up", 0.0
        elif self.wstate == "fire":
            self.wtimer -= dt
            if self.wtimer <= 0:
                self.wfi += 1
                if self.wfi >= len(w["frames"]):
                    self.wstate, self.wfi = "up", 0
                else:
                    self.wtimer = w["frames"][self.wfi][1]
                    if self.wfi == w["fire_at"] and w["fire_at"] > 0:
                        self.shoot()
                    if self.weapon == "egggun" and self.wfi == 3:
                        self.sound("pump")
        if self.wstate == "up" and self.queued:
            self.switch(self.queued)
        if self.wstate == "up" and inp.get("fire"):
            self.fire()

    def give_ammo(self, kind, n):
        if self.ammo[kind] >= MAXAMMO[kind]:
            return False
        mul = 2 if self.skill == 0 else 1
        self.ammo[kind] = min(MAXAMMO[kind], self.ammo[kind] + n * mul)
        return True

    def give_weapon(self, name, ammo, n, text):
        first = not self.owned[name]
        self.owned[name] = True
        self.give_ammo(ammo, n)
        self.face.update(mood="grin", mt=1.5)
        if first:
            self.switch(name)
        return True, text, "weapon"

    def pickup_check(self):
        for p in self.pickups:
            if p.removed or (p.x - self.px) ** 2 + (p.y - self.py) ** 2 > 0.45:
                continue
            k = p.kind
            took, text, snd = False, "", "item"
            if k == "bread" and self.health < 100:
                self.health = min(100, self.health + 10); took, text = True, "Picked up a slice of bread."
            elif k == "loaf" and self.health < 100:
                self.health = min(100, self.health + 25); took, text = True, "Picked up a whole loaf!"
            elif k == "crumbs":
                self.health = min(200, self.health + 1); took, text = True, "Picked up some crumbs."
            elif k == "vest" and self.armor < 100:
                self.armor, self.armor_class = 100, 1; took, text = True, "Picked up the feather vest!"
            elif k == "downjacket" and self.armor < 200:
                self.armor, self.armor_class = 200, 2; took, text = True, "Picked up the armored down jacket!"
            elif k == "feather":
                self.armor = min(200, self.armor + 1); took, text = True, "Picked up a loose feather."
            elif k == "pebbles" and self.give_ammo("pebbles", 5 if p.dropped else 10):
                took, text = True, "Picked up a pouch of pebbles."
            elif k == "pebblebox" and self.give_ammo("pebbles", 50):
                took, text = True, "Picked up a box of pebbles."
            elif k == "eggs" and self.give_ammo("eggs", 4):
                took, text = True, "Picked up an egg carton."
            elif k == "eggcrate" and self.give_ammo("eggs", 20):
                took, text = True, "Picked up a crate of eggs."
            elif k == "baguette" and self.give_ammo("baguettes", 1):
                took, text = True, "Picked up a baguette."
            elif k == "baguettes" and self.give_ammo("baguettes", 5):
                took, text = True, "Picked up a rack of baguettes."
            elif k == "corn" and self.give_ammo("corn", 20):
                took, text = True, "Picked up a hell corn cob."
            elif k == "cornsack" and self.give_ammo("corn", 100):
                took, text = True, "Picked up a sack of hell corn."
            elif k == "egggun":
                took, text, snd = self.give_weapon("egggun", "eggs", 8, "You got the Egg-Gun!")
            elif k == "flinger":
                took, text, snd = self.give_weapon("flinger", "pebbles", 20, "You got the Feather Flinger!")
            elif k == "bazooka":
                took, text, snd = self.give_weapon("bazooka", "baguettes", 2, "You got the Baguette Bazooka!")
            elif k == "megahonk":
                took, text, snd = self.give_weapon("megahonk", "corn", 40, "You got the MEGAHONK! Hold on to your feathers.")
            elif k in ("ykey", "bkey", "rkey"):
                c = {"ykey": "yellow", "bkey": "blue", "rkey": "red"}[k]
                self.keys.add(c)
                took, text, snd = True, "Picked up a %s key." % c, "key"
                for other in self.players:
                    if other is not self.cur:
                        self.msg("Your partner found the %s key!" % c, other)
            elif k == "rage":
                self.rage = True
                self.health = max(self.health, 100)
                self.tint[0] = 1.0
                self.switch("peck")
                took, text, snd = True, "RAGE BREAD! Your beak is a weapon of war.", "powerup"
            elif k == "goldegg":
                self.invuln = 25.0
                took, text, snd = True, "GOLDEN EGG! Nothing can touch you.", "powerup"
            elif k == "boots":
                self.boots = 40.0
                took, text, snd = True, "Rubber boots! Sludge and lava can't hurt you.", "powerup"
            elif k == "parkmap":
                self.R.seen[:] = True
                self.map_reveal = True
                took, text, snd = True, "Park map! The whole area is on your automap.", "powerup"
            if took:
                p.removed = True
                if k in COUNT_ITEMS:
                    self.items += 1
                self.tint[1] = 0.35
                self.msg(text)
                self.sound(snd)
        self.pickups = [p for p in self.pickups if not p.removed]

    def update_missiles(self, dt):
        for m in self.missiles:
            m.anim += dt
            sp = m.spec
            step = sp["speed"] * dt
            nx, ny = m.x + m.dx * step, m.y + m.dy * step
            hitwall = self.blocked_cell(nx, ny)
            target = None
            if not hitwall:
                if not isinstance(m.owner, Player):
                    for p in self.players:
                        if not p.dead and (nx - p.px) ** 2 + (ny - p.py) ** 2 < (PR + 0.15) ** 2:
                            target = p
                            break
                if target is None:
                    for o in list(self.enemies) + [d for d in self.decor if d.solid and not d.removed]:
                        if o is m.owner or not o.alive:
                            continue
                        if isinstance(o, Enemy) and isinstance(m.owner, Enemy) and o.kind == m.owner.kind:
                            continue   # same species can't hurt each other
                        if (nx - o.x) ** 2 + (ny - o.y) ** 2 < (o.r + 0.12) ** 2:
                            target = o
                            break
            if not (hitwall or target):
                m.x, m.y = nx, ny
                continue
            m.removed = True
            mult, lo, hi = sp["dmg"]
            dmg = mult * random.randint(lo, hi)
            if isinstance(target, Player):
                self.cur = target
                self.damage_player(dmg, m.owner)
                self.cur = self.me
            elif isinstance(target, Enemy):
                self.hurt_enemy(target, dmg)
            elif target is not None and target.hp is not None:
                self.hurt_barrel(target, dmg)
            bx, by = m.x - m.dx * 0.1, m.y - m.dy * 0.1
            if sp["splash"]:
                rad, power = sp["splash"]
                self.explode(bx, by, rad, power, noself=sp.get("noself", False), fxkind=sp["boom"],
                             owner=target if isinstance(target, Enemy) else (m.owner if isinstance(m.owner, Enemy) else None))
            else:
                self.effects.append(Effect(sp["boom"], bx, by, m.z - 0.1, 3, 0.3))
                self.sound("boom", bx, by, 0.4)
        self.missiles = [m for m in self.missiles if not m.removed]

    def finish_level(self):
        self.mode = "intermission"
        self.inter_t = 0.0
        self.grab(False)
        T = self.total
        T["kills"] += self.kills
        T["kills_total"] += self.kills_total
        T["items"] += self.items
        T["items_total"] += self.items_total
        T["secrets"] += len(self.secrets_found)
        T["secrets_total"] += self.level.secrets_total
        T["time"] += self.level_time
        nxt = self.level_idx + 1
        if nxt < NUM_LEVELS and nxt + 1 > self.unlocked:
            self.unlocked = nxt + 1
            self.save["unlocked"] = self.unlocked
            write_save(self.save)
        for p in self.players:
            if p.dead:
                p.carry = json.loads(json.dumps(p.snapshot))
            else:
                p.carry = dict(health=p.health, armor=p.armor, armor_class=p.armor_class,
                               ammo=dict(p.ammo), owned=dict(p.owned), weapon=p.weapon)

    def next_level(self):
        nxt = self.level_idx + 1
        if nxt >= NUM_LEVELS:
            self.mode = "victory"
            self.inter_t = 0.0
            self.play_song(0)
            return
        for p in self.players:
            c = p.carry
            c["health"] = max(c["health"], 100)
            for kind, bonus in LEVEL_AMMO_BONUS.items():
                if any(c["owned"].get(w) and WEAPONS[w]["ammo"] == kind for w in WEAPON_ORDER):
                    c["ammo"][kind] = min(MAXAMMO[kind], c["ammo"][kind] + bonus)
        self.load_level(nxt)

    def restart_level(self):
        for p in self.players:
            p.carry = json.loads(json.dumps(p.snapshot))
        self.load_level(self.level_idx)

    # ------------------------------------------------------------- co-op: hosting
    def start_host(self, bind=""):
        try:
            ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            ls.bind((bind, PORT))
            ls.listen(4)
            ls.setblocking(False)
        except OSError as ex:
            self.banner = "Could not host on port %d: %s" % (PORT, ex)
            return False
        self.listener = ls
        self.joiners = []
        self.role = "host"
        self.me = self.cur = Player(0)
        self.players = [self.me]
        self.level = None
        self.mode = "host_wait"          # the lobby
        self.lobby_sent = 0.0
        self.host_ips = local_ips()
        return True

    def lobby_start(self):
        """Host pressed START in the lobby: everyone drops into the chosen level."""
        self.new_game(self.pick_level)
        if len(self.players) > 1:
            self.msg_all("Co-op started! Shared keys, separate ammo. Don't peck each other.")

    def host_accept_tick(self):
        """Accept joiners into the lobby, or straight into a match already running."""
        if self.listener:
            try:
                while True:
                    sock, _ = self.listener.accept()
                    self.joiners.append([Net(sock), time.time()])
            except (BlockingIOError, InterruptedError):
                pass
            except OSError:
                pass
        for item in list(self.joiners):
            net, t0 = item
            hello = next((m for m in net.poll() if m.get("t") == "hello"), None)
            if hello is None:
                if not net.alive or time.time() - t0 > 5:
                    net.close()
                    self.joiners.remove(item)
                continue
            self.joiners.remove(item)
            if hello.get("v") != VERSION:
                theirs = str(hello.get("v", "?")).replace("hellhonk-", "v")
                net.send({"t": "reject", "why": "host is on v%s, you are on %s - restart the game to update"
                          % (APP_VERSION, theirs)})
                net.close()
                self.banner = "A player on %s tried to join (you are v%s)." % (theirs, APP_VERSION)
                self.msg("A player on %s tried to join - they need to update." % theirs, self.me)
                continue
            if len(self.players) >= MAX_PLAYERS:
                net.send({"t": "reject", "why": "the game is full (%d geese max)" % MAX_PLAYERS})
                net.close()
                continue
            used = {p.pid for p in self.players}
            p = Player(min(set(range(MAX_PLAYERS)) - used), remote=True)
            p.net = net
            self.players.append(p)
            net.send({"t": "welcome", "skill": self.skill, "pid": p.pid})
            if self.mode == "host_wait":
                self.play_sfx("key", None, None, 1.0)      # someone arrived in the lobby
            else:
                # late join: drop them in at the level start with a fresh loadout for this level
                p.carry = self.default_loadout(self.level_idx)
                self.cur = p
                self.reset_player(p, p.carry)
                self.cur = self.me
                self.effects.append(Effect("telefog", p.px, p.py, 0.0, 3, 0.5))
                self.msg_all("Player %d joined the flock!" % (p.pid + 1))
                self.sound("teleport", p.px, p.py)

    def host_net_tick(self):
        if self.role != "host":
            return
        for p in [q for q in self.players if q.remote]:
            for m in p.net.poll():
                if m.get("t") != "in":
                    continue
                if m.get("ack", 0) >= p.warp[0] and self.level and m.get("lvl") == self.level_idx:
                    nx, ny = float(m["x"]), float(m["y"])
                    if 0 < nx < MW and 0 < ny < MH and not self.blocked_cell(nx, ny):
                        p.moved += math.hypot(nx - p.px, ny - p.py)
                        p.px, p.py = nx, ny
                    p.ang = float(m["a"]) % math.tau
                p.fire_held = bool(m.get("fire"))
                p.events.extend(e for e in m.get("ev", []) if e in ONE_SHOT)
            if not p.net.alive:
                p.net.close()
                self.players.remove(p)
                self.cur = self.me
                if self.mode in ("play", "intermission", "victory"):
                    self.msg_all("Player %d left the pond." % (p.pid + 1))
                continue
            if self.mode == "host_wait":
                if time.time() - self.lobby_sent > 0.25:
                    p.net.send(self.lobby_info(), droppable=True)
            elif self.level is not None:
                p.net.send(self.build_snapshot(p), droppable=True)
        if self.mode == "host_wait" and time.time() - self.lobby_sent > 0.25:
            self.lobby_sent = time.time()

    def lobby_info(self):
        return {"t": "lobby", "players": sorted(p.pid for p in self.players),
                "level": LEVEL_NAMES[self.pick_level], "skill": SKILLS[self.skill]}

    def build_snapshot(self, p):
        L = self.level
        things = [[k, f, round(x, 2), round(y, 2), round(z, 2), h, int(b)] for k, f, x, y, z, h, b in self.drawables(p)]
        snap = dict(
            t="snap", lvl=self.level_idx, mode=self.mode, skill=self.skill, pid=p.pid,
            doors=[round(d.open, 2) for d in L.doors],
            sw=bool(L.exit_cell and L.wall[L.exit_cell[1], L.exit_cell[0]] == Assets.SWON),
            gone=[i for i, d in enumerate(self.decor) if d.removed], things=things,
            keys=sorted(self.keys), boss=None if self.boss_frac is None else round(self.boss_frac, 3),
            snd=p.snd, warp=p.warp,
            mates=[[o.pid, round(o.health), int(o.dead), round(o.px, 2), round(o.py, 2)] for o in self.players if o is not p],
            stats=[self.kills, self.kills_total, self.items, self.items_total, len(self.secrets_found),
                   L.secrets_total, round(self.level_time, 1)],
            total=getattr(self, "total", {}), inter=round(getattr(self, "inter_t", 0.0), 2),
            me=dict(health=p.health, armor=p.armor, ammo=p.ammo, owned=p.owned, weapon=p.weapon, wstate=p.wstate,
                    wfi=p.wfi, wraise=round(p.wraise, 2), tint=[round(v, 2) for v in p.tint], flash=round(p.flash, 2),
                    shake=round(p.shake, 2), face=dict(look=p.face["look"], mood=p.face["mood"]), rage=p.rage,
                    invuln=round(p.invuln, 1), boots=round(p.boots, 1), dead=p.dead, dead_t=round(p.dead_t, 2),
                    eye=round(p.eye, 3), msgs=p.msgs, reveal=bool(getattr(self, "map_reveal", False))))
        p.snd = []
        return snap

    # ------------------------------------------------------------- co-op: joining
    def start_join(self, ip):
        ip = ip.strip()
        self.banner = ""
        try:
            sock = socket.create_connection((ip, PORT), timeout=4)
        except OSError as ex:
            self.banner = "Could not reach %s:%d (%s)" % (ip, PORT, ex.__class__.__name__)
            self.mode = "title"
            return False
        self.save["last_ip"] = ip
        write_save(self.save)
        self.net = Net(sock)
        self.net.send({"t": "hello", "v": VERSION})
        self.role = "client"
        self.mode = "joining"
        self.join_t = time.time()
        self.level = None
        self.client_seq = 0
        return True

    def client_load(self, idx):
        self.loading_screen()
        L = self.level = Level(idx)
        self.level_idx = idx
        self.R = Renderer(self.A, L)
        self.missiles, self.effects, self.enemies, self.pickups = [], [], [], []
        self.spawn_things(L, enemies=False)
        self.keys = set()
        self.anim_t = 0.0
        self.anim_frame = 0
        self.flicker = 1.0
        self.update_grids()
        self.light_now = L.light.copy()
        self.net_things = []
        self.automap = False
        me = self.me
        me.px, me.py, me.ang = L.start
        me.vx = me.vy = 0.0
        me.eye = EYE
        self.play_song(L.song)
        self.grab(True)

    def client_net_tick(self):
        if not self.net:
            return
        for m in self.net.poll():
            t = m.get("t")
            if t == "reject":
                self.banner = "Host refused: %s" % m.get("why")
                self.net.alive = False
            elif t == "welcome":
                self.skill = m.get("skill", 1)
                self.me.pid = m.get("pid", 1)
            elif t == "lobby":
                self.lobby = m
                if self.mode == "joining":
                    self.mode = "client_lobby"
            elif t == "snap":
                self.apply_snapshot(m)
        if not self.net.alive or (self.mode == "joining" and time.time() - self.join_t > 8):
            if not self.banner:
                self.banner = "Lost connection to the host."
            self.leave_coop()

    def apply_snapshot(self, s):
        if self.level is None or s["lvl"] != self.level_idx:
            self.client_load(s["lvl"])
        L = self.level
        changed = False
        for d, o in zip(L.doors, s["doors"]):
            if d.open != o:
                d.open = o
                changed = True
        if changed:
            self.update_grids()
        if s["sw"] and L.exit_cell:
            L.wall[L.exit_cell[1], L.exit_cell[0]] = Assets.SWON
        gone = set(s["gone"])
        for i, d in enumerate(self.decor):
            d.removed = i in gone
        self.net_things = [tuple(t) for t in s["things"]]
        self.keys = set(s["keys"])
        self.boss_frac = s["boss"]
        self.skill = s["skill"]
        me = self.me
        for k, v in s["me"].items():
            if k == "face":
                me.face.update(v)
            elif k == "reveal":
                if v:
                    self.R.seen[:] = True
            else:
                setattr(me, k, v)
        w = s["warp"]
        if w[0] > me.warp_ack:
            me.warp_ack = w[0]
            me.px, me.py, me.ang = w[1], w[2], w[3]
            me.vx = me.vy = 0.0
        self.mates = s["mates"]
        me.pid = s.get("pid", me.pid)
        (self.kills, self.kills_total, self.items, self.items_total, nsec, self.secrets_total_net,
         self.level_time) = s["stats"]
        self.secrets_found = set(range(nsec))
        self.total = s["total"]
        prev = self.mode
        self.mode = s["mode"]
        self.inter_t = s["inter"]
        if self.mode in ("intermission", "victory") and prev == "play":
            self.grab(False)
            # joiners unlock levels too, not just the host
            nxt = self.level_idx + 1
            if nxt < NUM_LEVELS and nxt + 1 > self.unlocked:
                self.unlocked = nxt + 1
                self.pick_level = self.unlocked - 1
                self.save["unlocked"] = self.unlocked
                write_save(self.save)
        if self.mode == "play" and prev in ("intermission", "victory", "joining", "client_lobby"):
            self.grab(True)
        for name, x, y, vol in s["snd"]:
            self.play_sfx(name, x, y, vol)

    def client_step(self, dt, inp):
        """Client frame: move locally, send input, animate the world copy we got from the host."""
        if self.level is None:
            return
        self.t += dt
        self.anim_t += dt
        self.anim_frame = int(self.anim_t * 6) % Assets.SLUDGE_FRAMES
        if random.random() < dt * 8:
            self.flicker = random.choice((1.0, 1.0, 0.55, 0.8))
        L = self.level
        lt = np.where(L.flicker, L.light * self.flicker, L.light)
        if self.me.flash > 0:
            lt = np.minimum(1.0, lt + 0.25)
        self.light_now = lt
        self.cur = self.me
        if self.mode == "play" and not self.me.dead:
            self.player_move(dt, inp)
        ev = [k for k in ONE_SHOT if inp.get(k)]
        self.client_seq += 1
        self.net.send({"t": "in", "lvl": self.level_idx, "x": round(self.me.px, 3), "y": round(self.me.py, 3),
                       "a": round(self.me.ang, 4), "fire": bool(inp.get("fire")), "ev": ev,
                       "ack": self.me.warp_ack, "seq": self.client_seq}, droppable=True)

    def leave_coop(self):
        if self.net:
            self.net.close()
        self.net = None
        for p in self.players:
            if p.net:
                p.net.close()
        for net, _ in self.joiners:
            net.close()
        self.joiners = []
        if self.listener:
            self.listener.close()
            self.listener = None
        self.role = "solo"
        self.me = self.cur = Player(0)
        self.players = [self.me]
        self.level = None
        self.mode, self.menu_i, self.menu_open = "title", 0, False
        self.grab(False)
        self.play_song(0)

    # ------------------------------------------------------------- drawing
    def drawables(self, viewer):
        """Everything visible as (sprite, frame, x, y, z, height, fullbright) for one viewer."""
        out = []
        for e in self.enemies:
            if e.state == "dying" or not e.alive:
                f = "d%d" % min(2, int(e.t / (0.3 if e.boss else 0.15)))
            elif e.state == "pain":
                f = "pain"
            elif e.state == "attack":
                f = e.st["poses"][1] if (e.t - e.last_ev) < 0.15 else e.st["poses"][0]
            elif e.state == "idle":
                f = "walk0"
            else:
                f = "walk%d" % (int(e.anim * 5) % 2)
            bright = f == e.st["poses"][1] and e.state == "attack" and e.kind not in ("brute", "gosling")
            out.append((e.kind, f, e.x, e.y, 0.0, e.st["h"], bright))
        for p in self.players:
            if p is viewer:
                continue
            if p.dead:
                f = "d2"
            elif p.wstate == "fire" and p.wfi == 0:
                f = "fire"
            elif p.tint[0] > 0.3:
                f = "pain"
            else:
                f = "walk%d" % (int(p.bob) % 2)
            out.append(("goose%d" % (p.pid % 3), f, p.px, p.py, 0.0, 0.62, p.wstate == "fire" and p.wfi == 0))
        for p in self.pickups:
            out.append((p.kind, "0", p.x, p.y, 0.0, ITEM_H[p.kind], p.kind in ("ykey", "bkey", "rkey", "goldegg", "megahonk")))
        for d in self.decor:
            if d.removed:
                continue
            fr = str(int(self.t * 3 + d.x) % 2) if d.kind in ("lamp", "barrel") else "0"
            out.append((d.kind, fr, d.x, d.y, 0.0, d.h, d.kind in ("lamp", "candle")))
        for m in self.missiles:
            out.append((m.spec["sprite"], str(int(m.anim * 10) % 2), m.x, m.y, m.z, m.spec["h"], True))
        for fx in self.effects:
            i = min(fx.frames - 1, int(fx.t / fx.dur * fx.frames))
            out.append((fx.kind, str(i), fx.x, fx.y, fx.z, FX_H[fx.kind], fx.kind != "blood"))
        return out

    def mate_status(self):
        """[(pid, health, dead)] for every other player, host or client side."""
        if self.role == "client":
            return [(m[0], m[1], bool(m[2])) for m in getattr(self, "mates", [])]
        return [(p.pid, p.health, p.dead) for p in self.players if p is not self.me]

    def client_things(self):
        """The host's list plus our own animated decor (lamps/barrels flicker locally)."""
        return self.net_things

    def overlay(self, rgb, a):
        o = pygame.Surface((VW, VH), pygame.SRCALPHA)
        o.fill(rgb + (int(a),))
        self.view.blit(o, (0, 0))

    def draw_play(self):
        self.cur = self.me
        bobv = math.sin(self.bob * 2) * 1.6 * self.bob_amt
        hz = VH / 2 + bobv + (random.uniform(-6, 6) * self.shake if self.shake > 0 else 0)
        things = self.client_things() if self.role == "client" else self.drawables(self.me)
        frame = self.R.render(self, self.px, self.py, self.ang, hz, self.eye, things)
        pygame.surfarray.blit_array(self.view, frame)
        if not self.dead:
            self.draw_weapon()
        if self.automap:
            self.draw_automap()
        if self.tint[0] > 0:
            self.overlay((200, 0, 0), 160 * min(1, self.tint[0]))
        if self.tint[1] > 0:
            self.overlay((255, 210, 80), 110 * min(1, self.tint[1]))
        if self.tint[2] > 0:
            self.overlay((80, 255, 150), 140 * min(1, self.tint[2]))
        if self.invuln > 0 and (self.invuln > 3 or int(self.t * 6) % 2):
            self.overlay((255, 215, 60), 55)
        if self.boots > 0 and (self.boots > 3 or int(self.t * 6) % 2):
            self.overlay((80, 255, 80), 25)
        for i, (m, _) in enumerate(self.msgs):
            self.text(self.view, m, 3, 2 + i * 10, (255, 230, 170))
        pw = []
        for pid, hp, dead in self.mate_status():
            pw.append(("P%d %s" % (pid + 1, "DOWN" if dead else "%d%%" % hp),
                       (255, 120, 120) if dead else (150, 230, 255)))
        if self.rage:
            pw.append(("RAGE", (255, 80, 60)))
        if self.invuln > 0:
            pw.append(("GOLD %d" % math.ceil(self.invuln), (255, 220, 60)))
        if self.boots > 0:
            pw.append(("BOOTS %d" % math.ceil(self.boots), (120, 255, 120)))
        for i, (t, c) in enumerate(pw):
            self.text(self.view, t, VW - self.font.size(t)[0] - 3, 2 + i * 10, c)
        if self.boss_frac is not None:
            r = pygame.Rect(60, VH - 14, 200, 7)
            pygame.draw.rect(self.view, (30, 0, 0), r)
            pygame.draw.rect(self.view, (230, 40, 30), (r.x, r.y, int(r.w * self.boss_frac), r.h))
            pygame.draw.rect(self.view, (255, 220, 150), r, 1)
            self.text_c(self.view, "THE HONKMOTHER", VH - 25, (255, 220, 150))
        if self.dead and self.dead_t > 1.0:
            line = "YOU GOT COOKED. Press USE to try again."
            mates = self.mate_status()
            if mates:
                alive = any(not dead for _, _, dead in mates)
                line = "YOU GOT COOKED. Press USE to rejoin." if alive else "THE WHOLE FLOCK GOT COOKED... restarting"
            self.text_c(self.view, line, VH // 2 - 6, (255, 220, 200))
        self.screen.blit(self.view, (0, 0))
        self.draw_bar()

    def draw_weapon(self):
        w = self.weapon
        fr = WEAPONS[w]["frames"][min(self.wfi, len(WEAPONS[w]["frames"]) - 1)][0] if self.wstate == "fire" else 0
        surf = self.A.weapons[w][fr]
        bx = math.cos(self.bob) * 9 * self.bob_amt
        by = abs(math.sin(self.bob)) * 7 * self.bob_amt
        x = VW // 2 - surf.get_width() // 2 + bx + (18 if w == "honker" else 0)
        y = VH - surf.get_height() + 8 + by + self.wraise * 70
        lt = float(self.light_now[int(self.py) % MH, int(self.px) % MW])
        if self.rage and w == "peck":
            surf = surf.copy()
            surf.fill((255, 150, 150), special_flags=pygame.BLEND_RGB_MULT)
        if self.flash <= 0 and lt < 0.95:
            surf = surf.copy()
            k = int(255 * max(0.35, lt))
            surf.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
        self.view.blit(surf, (x, y))

    def draw_automap(self):
        v = self.view
        v.fill((0, 0, 0))
        sc = 5
        ox, oy = VW / 2 - self.px * sc, VH / 2 - self.py * sc
        L = self.level
        seen = self.R.seen
        for y in range(1, MH - 1):
            for x in range(1, MW - 1):
                if not seen[y, x] or L.wall[y, x] < 0:
                    continue
                col = (220, 60, 50)
                if L.door_at[y, x] >= 0:
                    d = L.doors[L.door_at[y, x]]
                    col = {"yellow": (240, 210, 40), "blue": (60, 120, 255), "red": (255, 60, 60)}.get(
                        d.key, (220, 60, 50) if d.secret else (200, 160, 60))
                X, Y = ox + x * sc, oy + y * sc
                if L.wall[y, x - 1] < 0 or L.door_at[y, x - 1] >= 0:
                    pygame.draw.line(v, col, (X, Y), (X, Y + sc))
                if L.wall[y, x + 1] < 0 or L.door_at[y, x + 1] >= 0:
                    pygame.draw.line(v, col, (X + sc, Y), (X + sc, Y + sc))
                if L.wall[y - 1, x] < 0 or L.door_at[y - 1, x] >= 0:
                    pygame.draw.line(v, col, (X, Y), (X + sc, Y))
                if L.wall[y + 1, x] < 0 or L.door_at[y + 1, x] >= 0:
                    pygame.draw.line(v, col, (X, Y + sc), (X + sc, Y + sc))
        for (tx, ty) in L.tele:
            if seen[max(0, ty - 1):ty + 2, max(0, tx - 1):tx + 2].any():
                pygame.draw.circle(v, (90, 255, 150), (int(ox + tx * sc + sc / 2), int(oy + ty * sc + sc / 2)), 2)
        if self.role == "client":
            mates = [(t[2], t[3]) for t in self.net_things if t[0].startswith("goose")]
        else:
            mates = [(p.px, p.py) for p in self.players if p is not self.me]
        for mx_, my_ in mates:
            pygame.draw.circle(v, (90, 200, 255), (int(ox + mx_ * sc), int(oy + my_ * sc)), 3)
        cx, cy = VW / 2, VH / 2
        a = self.ang
        pts = [(cx + math.cos(a) * 6, cy + math.sin(a) * 6),
               (cx + math.cos(a + 2.5) * 4, cy + math.sin(a + 2.5) * 4),
               (cx + math.cos(a - 2.5) * 4, cy + math.sin(a - 2.5) * 4)]
        pygame.draw.polygon(v, (255, 255, 255), pts)
        self.text(v, L.name, 3, VH - 12, (255, 255, 255))

    def draw_bar(self):
        s = self.screen
        s.blit(self.bar_bg, (0, VH))
        y = VH + 2
        w = WEAPONS[self.weapon]
        self.big("" if w["ammo"] is None else str(self.ammo[w["ammo"]]), 24, y)
        self.big("%d%%" % self.health, 76, y)
        self.big("%d%%" % self.armor, 202, y)
        for i, name in enumerate(WEAPON_ORDER):
            c = (255, 220, 60) if self.owned[name] else (110, 100, 90)
            if name == self.weapon:
                c = (255, 255, 255)
            self.text(s, str(i + 1), 112 + (i % 3) * 10, VH + 2 + (i // 3) * 9, c, self.font_small)
        f = self.face
        if self.dead:
            key = (0, 4, "dead")
        else:
            pain = min(4, max(0, (100 - self.health) // 20))
            mood = "grin" if self.invuln > 0 else f["mood"]
            key = (0, pain, mood) if mood != "normal" else (f["look"], pain, "normal")
        face = self.A.faces.get(key, self.A.faces[(0, 0, "normal")])
        if self.invuln > 0:
            face = face.copy()
            face.fill((255, 220, 90), special_flags=pygame.BLEND_RGB_MULT)
        s.blit(face, (147, VH + 1))
        for i, (k, c) in enumerate((("yellow", (240, 210, 40)), ("blue", (60, 120, 255)), ("red", (230, 40, 40)))):
            r = pygame.Rect(237, VH + 3 + i * 9, 8, 7)
            if k in self.keys:
                pygame.draw.rect(s, c, r)
                pygame.draw.rect(s, (255, 255, 255), r, 1)
            else:
                pygame.draw.rect(s, (40, 30, 20), r, 1)
        for i, (k, lab) in enumerate(AMMO_LABEL):
            c = (255, 240, 200) if w["ammo"] == k else (225, 200, 140)
            self.text(s, "%s %3d/%d" % (lab, self.ammo[k], MAXAMMO[k]), 254, VH + 2 + i * 7, c, self.font_small)

    def big(self, t, cx, y):
        img = self.font_big.render(t, False, (230, 60, 30))
        sh = self.font_big.render(t, False, (40, 0, 0))
        self.screen.blit(sh, (cx - img.get_width() // 2 + 1, y + 1))
        self.screen.blit(img, (cx - img.get_width() // 2, y))

    def text(self, surf, t, x, y, c, font=None):
        font = font or self.font
        surf.blit(font.render(t, False, (0, 0, 0)), (x + 1, y + 1))
        surf.blit(font.render(t, False, c), (x, y))

    def text_c_at(self, surf, t, cx, y, c, font=None):
        font = font or self.font_small
        self.text(surf, t, cx - font.size(t)[0] // 2, y, c, font)

    def text_c(self, surf, t, y, c, font=None):
        font = font or self.font
        self.text(surf, t, surf.get_width() // 2 - font.size(t)[0] // 2, y, c, font)

    def menu_items(self):
        if self.mode == "title":
            return ["START: " + LEVEL_NAMES[self.pick_level], "CO-OP: HOST GAME", "CO-OP: JOIN GAME",
                    "SKILL: " + SKILLS[self.skill], "MUSIC: " + ("ON" if self.music_on else "OFF"), "QUIT"]
        if self.role == "client":
            return ["RESUME", "MUSIC: " + ("ON" if self.music_on else "OFF"), "LEAVE CO-OP GAME"]
        items = ["RESUME", "MUSIC: " + ("ON" if self.music_on else "OFF"), "RESTART LEVEL"]
        return items + (["END CO-OP GAME"] if self.role == "host" else ["QUIT TO TITLE"])

    def draw_menu(self):
        s = self.screen
        if self.mode == "title":
            s.blit(self.title_bg, (0, 0))
            y0 = 82
        else:
            self.draw_play()
            o = pygame.Surface((SW, SH), pygame.SRCALPHA)
            o.fill((0, 0, 0, 150))
            s.blit(o, (0, 0))
            self.text_c(s, "PAUSED" if self.role == "solo" else "MENU (the game keeps going!)", 50, (255, 200, 80),
                        self.font_big if self.role == "solo" else self.font_mid)
            y0 = 80
        for i, it in enumerate(self.menu_items()):
            sel = i == self.menu_i
            c = (255, 240, 200) if sel else (200, 120, 80)
            self.text_c(s, it, y0 + i * 12, c, self.font_mid if sel else self.font)
        if self.mode == "title":
            if self.banner:
                self.text_c(s, self.banner, y0 + 74, (255, 120, 100), self.font_small)
            else:
                self.text_c(s, "LEFT/RIGHT picks level and skill" if self.unlocked > 1 else "LEFT/RIGHT picks skill",
                            y0 + 74, (200, 170, 140), self.font_small)
            self.text_c(s, "WASD move  MOUSE turn  CLICK fire  E use", SH - 22, (230, 210, 190))
            self.text_c(s, "1-6 weapons  TAB map  SHIFT walk  M music", SH - 11, (230, 210, 190))
            ver = "v" + APP_VERSION
            self.text(s, ver, SW - self.font_small.size(ver)[0] - 3, SH - 9, (160, 140, 120), self.font_small)
            up = self.updater.status_line()
            if up:
                self.text_c(s, up, 2, (140, 255, 170), self.font_small)

    def draw_lobby(self):
        s = self.screen
        s.blit(self.title_bg, (0, 0))
        o = pygame.Surface((SW, SH), pygame.SRCALPHA)
        o.fill((0, 0, 0, 215))
        s.blit(o, (0, 0))
        if self.mode in ("host_wait", "client_lobby"):
            host = self.mode == "host_wait"
            info = self.lobby_info() if host else getattr(self, "lobby", {"players": [0], "level": "?", "skill": "?"})
            self.text_c(s, "CO-OP LOBBY", 10, (255, 210, 120), self.font_mid)
            if host:
                self.text_c(s, "Friends JOIN this address:", 30, (240, 225, 200), self.font_small)
                self.text_c(s, self.host_ips[0] if self.host_ips else "?", 40, (140, 255, 170), self.font_mid)
            # the flock: three slots
            for slot in range(MAX_PLAYERS):
                x = 58 + slot * 72
                here = slot in info["players"]
                vest = VEST_COLORS[slot][0]
                box = pygame.Rect(x, 62, 60, 56)
                pygame.draw.rect(s, (40, 18, 14) if here else (20, 10, 8), box)
                pygame.draw.rect(s, vest if here else (70, 50, 40), box, 2)
                if here:
                    face = pygame.transform.scale(self.A.faces[(0, 0, "grin" if slot == 0 else "normal")], (26, 30))
                    s.blit(face, (x + 17, 66))
                    pygame.draw.rect(s, vest, (x + 14, 98, 32, 6))
                    who = "HOST" if slot == 0 else "P%d" % (slot + 1)
                    if not host and slot == self.me.pid:
                        who += " (YOU)"
                    elif host and slot == 0:
                        who = "YOU (HOST)"
                    self.text_c_at(s, who, x + 30, 106, (255, 240, 200))
                else:
                    self.text_c_at(s, "open", x + 30, 84, (120, 100, 90))
            self.text_c(s, "LEVEL: %s" % info["level"], 126, (255, 230, 170))
            self.text_c(s, "SKILL: %s" % info["skill"], 138, (255, 200, 150), self.font_small)
            n = len(info["players"])
            if host:
                self.text_c(s, "ENTER start   LEFT/RIGHT level   UP/DOWN skill   ESC cancel", 158, (230, 210, 190),
                            self.font_small)
                self.text_c(s, ("%d goose%s ready" % (n, "" if n == 1 else "s")) +
                            ("   -   waiting for friends" + "." * (int(self.t * 2) % 4) if n < MAX_PLAYERS else "   -   flock is full!"),
                            172, (140, 255, 170) if n > 1 else (200, 180, 160), self.font_small)
                self.text_c(s, "Friends can still join after the match starts.", 184, (170, 150, 130), self.font_small)
            else:
                self.text_c(s, "Waiting for the host to start" + "." * (int(self.t * 2) % 4), 162, (140, 255, 170))
                self.text_c(s, "ESC to leave", 180, (200, 180, 160), self.font_small)
        elif self.mode == "join_entry":
            self.text_c(s, "JOIN CO-OP", 60, (255, 210, 120), self.font_mid)
            self.text_c(s, "Type the host's address and press ENTER:", 88, (240, 225, 200))
            box = pygame.Rect(70, 104, 180, 18)
            pygame.draw.rect(s, (20, 10, 10), box)
            pygame.draw.rect(s, (255, 200, 120), box, 1)
            cursor = "_" if int(self.t * 3) % 2 else " "
            self.text(s, self.ip_text + cursor, box.x + 5, box.y + 3, (255, 255, 255), self.font_mid)
            self.text_c(s, "ESC to go back", 140, (200, 180, 160))
            if self.banner:
                self.text_c(s, self.banner, 160, (255, 120, 100), self.font_small)
        elif self.mode == "joining":
            self.text_c(s, "CONNECTING" + "." * (int(self.t * 2) % 4), 96, (255, 230, 170), self.font_mid)

    def draw_intermission(self):
        s = self.screen
        s.blit(self.title_bg, (0, 0))
        o = pygame.Surface((SW, SH), pygame.SRCALPHA)
        o.fill((0, 0, 0, 175))
        s.blit(o, (0, 0))
        self.text_c(s, self.level.name.split(": ")[1], 16, (255, 210, 120), self.font_big)
        self.text_c(s, "FINISHED", 38, (255, 255, 255), self.font_mid)
        t = self.inter_t
        pct = lambda a, b: 100 if b == 0 else int(100 * a / b)
        stot = self.level.secrets_total
        rows = [("KILLS", pct(self.kills, self.kills_total)), ("ITEMS", pct(self.items, self.items_total)),
                ("SECRETS", pct(len(self.secrets_found), stot))]
        for i, (lab, v) in enumerate(rows):
            shown = min(v, int(max(0, t - 0.4 * i) * 120))
            self.text(s, lab, 90, 62 + i * 17, (255, 120, 60), self.font_mid)
            self.text(s, "%d%%" % shown, 200, 62 + i * 17, (255, 240, 200), self.font_mid)
        tm = int(self.level_time)
        self.text(s, "TIME", 90, 116, (255, 120, 60), self.font_mid)
        self.text(s, "%d:%02d" % (tm // 60, tm % 60), 200, 116, (255, 240, 200), self.font_mid)
        self.text(s, "PAR", 90, 132, (255, 120, 60), self.font_mid)
        self.text(s, "%d:%02d" % (self.level.par // 60, self.level.par % 60), 200, 132, (255, 240, 200), self.font_mid)
        if t > 1.5:
            nxt = self.level_idx + 1
            line = ("NEXT: " + LEVEL_NAMES[nxt]) if nxt < NUM_LEVELS else "THE POND FALLS SILENT..."
            self.text_c(s, line, 158, (140, 255, 170))
            self.text_c(s, "waiting for the host..." if self.role == "client" else "press a key", 178, (220, 200, 180))

    def draw_victory(self):
        s = self.screen
        s.blit(self.title_bg, (0, 0))
        o = pygame.Surface((SW, SH), pygame.SRCALPHA)
        o.fill((0, 0, 0, 190))
        s.blit(o, (0, 0))
        self.text_c(s, "VICTORY", 14, (255, 220, 90), self.font_big)
        story = ["The Honkmother's crown rolls across the ash.",
                 "Her brood scatters, the sludge settles, and the",
                 "pond goes quiet for the first time in years.",
                 "",
                 "But somewhere downstream, something quacks back...",
                 "Thanks for playing HELLHONK Episode 1: FOWL WATERS"]
        shown = int(self.inter_t * 25)
        y = 44
        for line in story:
            self.text_c(s, line[:max(0, shown)], y, (240, 225, 200))
            shown -= len(line) + 4
            y += 12
        T = self.total
        pct = lambda a, b: 100 if b == 0 else int(100 * a / b)
        tm = int(T.get("time", 0))
        if self.inter_t > 4 and T:
            self.text_c(s, "EPISODE  KILLS %d%%   ITEMS %d%%   SECRETS %d%%   TIME %d:%02d" % (
                pct(T["kills"], T["kills_total"]), pct(T["items"], T["items_total"]),
                pct(T["secrets"], T["secrets_total"]), tm // 60, tm % 60), 132, (140, 255, 170))
            self.text_c(s, "Skill: " + SKILLS[self.skill], 146, (255, 200, 150))
            self.text_c(s, "waiting for the host..." if self.role == "client" else "press a key", 178, (220, 200, 180))

    def present(self):
        pygame.transform.scale(self.screen, WIN, self.window)
        pygame.display.flip()

    # ------------------------------------------------------------- main loop
    def toggle_music(self):
        self.music_on = not self.music_on
        if self.audio:
            if self.music_on and self.song_now is not None:
                self.music_ch.play(self.songs[self.song_now], loops=-1)
                self.music_ch.set_volume(0.45)
            else:
                self.music_ch.stop()

    def close_menu(self):
        self.menu_open = False
        self.grab(True)

    def menu_select(self, i, delta=0):
        it = self.menu_items()[i]
        if it.startswith("MUSIC"):
            self.toggle_music()
        elif it.startswith("SKILL"):
            self.skill = (self.skill + (delta or 1)) % 3
        elif it.startswith("START"):
            if delta:
                self.pick_level = (self.pick_level + delta) % self.unlocked
            else:
                self.new_game(self.pick_level)
        elif it == "CO-OP: HOST GAME" and not delta:
            self.banner = ""
            self.start_host()
        elif it == "CO-OP: JOIN GAME" and not delta:
            self.banner = ""
            self.mode = "join_entry"
        elif it == "QUIT":
            return False
        elif it == "RESUME":
            self.close_menu()
        elif it == "RESTART LEVEL":
            self.restart_level()
        elif it in ("QUIT TO TITLE", "END CO-OP GAME", "LEAVE CO-OP GAME"):
            self.leave_coop()
        if delta == 0:
            self.play_sfx("item", None, None, 1.0)
        return True

    def handle_key(self, k, ev, inp):
        """Returns False to quit."""
        if self.mode == "title" or self.menu_open:
            n = len(self.menu_items())
            if k in (pygame.K_UP, pygame.K_w):
                self.menu_i = (self.menu_i - 1) % n
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.menu_i = (self.menu_i + 1) % n
            elif k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                return self.menu_select(self.menu_i)
            elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                if self.menu_items()[self.menu_i].startswith(("SKILL", "START")):
                    self.menu_select(self.menu_i, -1 if k in (pygame.K_LEFT, pygame.K_a) else 1)
            elif k == pygame.K_ESCAPE and self.menu_open:
                self.close_menu()
        elif self.mode == "host_wait":
            if k == pygame.K_ESCAPE:
                self.leave_coop()
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                self.lobby_start()
            elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                self.pick_level = (self.pick_level + (-1 if k in (pygame.K_LEFT, pygame.K_a) else 1)) % self.unlocked
            elif k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.skill = (self.skill + (-1 if k in (pygame.K_UP, pygame.K_w) else 1)) % 3
        elif self.mode == "client_lobby":
            if k == pygame.K_ESCAPE:
                self.leave_coop()
        elif self.mode == "join_entry":
            if k == pygame.K_ESCAPE:
                self.mode = "title"
            elif k == pygame.K_RETURN and self.ip_text.strip():
                self.mode = "joining"
                self.draw_lobby()
                self.present()
                self.start_join(self.ip_text)
            elif k == pygame.K_BACKSPACE:
                self.ip_text = self.ip_text[:-1]
            elif ev.unicode and (ev.unicode.isalnum() or ev.unicode in ".-:") and len(self.ip_text) < 40:
                self.ip_text += ev.unicode
        elif self.mode == "joining":
            if k == pygame.K_ESCAPE:
                self.leave_coop()
        elif self.mode == "intermission":
            if self.role != "client" and self.inter_t > 1.0:
                self.next_level()
        elif self.mode == "victory":
            if self.role != "client" and self.inter_t > 4.0:
                if self.role == "host":
                    self.leave_coop()
                self.mode, self.menu_i = "title", 0
                self.pick_level = self.unlocked - 1
                self.play_song(0)
        elif self.mode == "play":
            if k == pygame.K_ESCAPE:
                self.menu_open, self.menu_i = True, 0
                self.grab(False)
            elif k in (pygame.K_e, pygame.K_SPACE):
                inp["use"] = True
            elif k == pygame.K_TAB:
                self.automap = not self.automap
            elif k == pygame.K_m:
                self.toggle_music()
            elif pygame.K_1 <= k <= pygame.K_6:
                inp["w%d" % (k - pygame.K_0)] = True
        return True

    def run(self):
        running = True
        while running:
            dt = min(0.05, self.clock.tick(70) / 1000.0)
            self.t += 0 if self.mode == "play" else dt
            inp = {}
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    running = self.handle_key(ev.key, ev, inp) and running
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.mode == "play" and not self.menu_open:
                    if ev.button == 3:
                        inp["use"] = True
                    elif ev.button == 4:
                        inp["wprev"] = True
                    elif ev.button == 5:
                        inp["wnext"] = True
            if not running:
                break
            if self.updater.state == "ready" and self.mode == "title":
                self.draw_menu()
                self.present()
                self.updater.apply_and_restart()
                break
            if self.listener:
                self.host_accept_tick()
            if self.role == "client":
                self.client_net_tick()
            if self.mode == "play" and self.level is not None:
                if not self.menu_open:
                    keys = pygame.key.get_pressed()
                    fwd = (keys[pygame.K_w] or keys[pygame.K_UP]) - (keys[pygame.K_s] or keys[pygame.K_DOWN])
                    strafe = keys[pygame.K_d] - keys[pygame.K_a]
                    turn = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 2.8 * dt
                    mx, _ = pygame.mouse.get_rel()
                    turn += mx * 0.0032
                    inp.update(fwd=fwd, strafe=strafe, turn=turn,
                               walk=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
                               fire=keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or pygame.mouse.get_pressed()[0])
                if self.role == "client":
                    self.client_step(dt, inp)
                elif not self.menu_open or self.role == "host":
                    self.update(dt, inp if not self.menu_open else {})
            if self.role == "host":
                self.host_net_tick()
            if self.mode == "play" and self.level is not None:
                if self.menu_open:
                    self.draw_menu()
                else:
                    self.draw_play()
            elif self.mode == "intermission":
                if self.role != "client":
                    self.inter_t += dt
                self.draw_intermission()
            elif self.mode == "victory":
                if self.role != "client":
                    self.inter_t += dt
                self.draw_victory()
            elif self.mode in ("host_wait", "client_lobby", "join_entry", "joining"):
                self.draw_lobby()
            else:
                self.draw_menu()
            self.present()
        if self.net:
            self.net.close()
        pygame.quit()


def _level_names():
    names = []
    for i in range(NUM_LEVELS):
        L = Level(i)
        names.append(L.name.split(": ", 1)[0] + " " + L.name.split(": ", 1)[1])
    return names


LEVEL_NAMES = _level_names()


# =================================================================== self test
def overview(level, game_things, path):
    """Top-down picture of a level for checking layouts."""
    sc = 10
    surf = pygame.Surface((MW * sc, MH * sc))
    for y in range(MH):
        for x in range(MW):
            if level.wall[y, x] >= 0:
                d = level.door_obj(x, y)
                c = (70, 70, 80)
                if d:
                    c = {"yellow": (240, 210, 40), "blue": (60, 120, 255), "red": (230, 40, 40)}.get(
                        d.key, (150, 60, 150) if d.secret else (170, 120, 60))
                if (x, y) == level.exit_cell:
                    c = (255, 255, 255)
            else:
                c = (25, 25, 25)
                if level.hurt[y, x] >= 10:
                    c = (150, 50, 10)
                elif level.hurt[y, x]:
                    c = (40, 110, 30)
                if (x, y) in level.tele:
                    c = (40, 200, 200)
                if (x, y) in level.secret_cells:
                    c = (60, 30, 60)
            pygame.draw.rect(surf, c, (x * sc, y * sc, sc, sc))
    for kind, x, y in game_things:
        c = (255, 60, 60) if kind in ENEMY else (255, 220, 80) if kind in ITEM_H else (120, 120, 120)
        if kind in ("ykey", "bkey", "rkey"):
            c = {"ykey": (255, 255, 0), "bkey": (0, 150, 255), "rkey": (255, 0, 0)}[kind]
            pygame.draw.circle(surf, c, (int(x * sc), int(y * sc)), 4)
        else:
            pygame.draw.circle(surf, c, (int(x * sc), int(y * sc)), 2)
    sx, sy, sa = level.start
    pygame.draw.circle(surf, (255, 255, 255), (int(sx * sc), int(sy * sc)), 4)
    pygame.draw.line(surf, (255, 255, 255), (sx * sc, sy * sc), (sx * sc + math.cos(sa) * 12, sy * sc + math.sin(sa) * 12), 2)
    pygame.image.save(surf, path)


def selftest(out):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.makedirs(out, exist_ok=True)
    global SAVE
    SAVE = os.path.join(out, "save.json")
    if os.path.exists(SAVE):
        os.remove(SAVE)
    t0 = time.time()
    g = Game(headless=True)
    print("startup %.2fs audio=%s" % (time.time() - t0, g.audio))

    def shot(game, name):
        pygame.image.save(pygame.transform.scale(game.screen, WIN), os.path.join(out, name + ".png"))

    def step(n=1, **inp):
        for _ in range(n):
            g.update(1 / 35, dict(inp))
        g.draw_play()

    g.draw_menu()
    shot(g, "00_title")

    # ---- every level: layout sanity, key order, exit, screenshot
    for i in range(NUM_LEVELS):
        g.new_game(i, 2)
        L = g.level
        things = [(e.kind, e.x, e.y) for e in g.enemies] + [(p.kind, p.x, p.y) for p in g.pickups] + \
                 [(d.kind, d.x, d.y) for d in g.decor]
        overview(L, things, os.path.join(out, "map_%d.png" % (i + 1)))
        for kind, x, y in things:
            assert L.wall[int(y), int(x)] < 0, ("thing in wall", i, kind, x, y)
        for (x, y) in L.tele:
            assert L.wall[y, x] < 0, ("teleport pad in wall", i, x, y)
        start = [(int(L.start[0]), int(L.start[1]))]
        keys = set()
        while True:
            dist = g.bfs(start, True, keys=keys)
            changed = True
            while changed:
                changed = False
                for a, b in L.tele.items():
                    if dist[a[1], a[0]] < 999 and dist[b[1], b[0]] >= 999:
                        dist = np.minimum(dist, g.bfs([b], True, keys=keys))
                        changed = True
            new = {c for p in g.pickups for k, c in (("ykey", "yellow"), ("bkey", "blue"), ("rkey", "red"))
                   if p.kind == k and dist[int(p.y), int(p.x)] < 999} - keys
            if not new:
                break
            keys |= new
        needed = {d.key for d in L.doors if d.key}
        assert needed <= keys, ("keys unreachable", i, needed - keys)
        if L.boss_level:
            assert g.boss and dist[int(g.boss.y), int(g.boss.x)] < 999, ("boss unreachable", i)
        else:
            ex, ey = L.exit_cell
            assert min(dist[ey + dy, ex + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) < 999, ("exit unreachable", i)
        for e in g.enemies:
            e.state = "idle"
        step(1)
        shot(g, "lvl%d_start" % (i + 1))
        print("level %d ok: %-34s enemies %2d items %2d secrets %d keys %s" % (
            i + 1, L.name, len(g.enemies), g.items_total, L.secrets_total, sorted(keys) or "-"))

    # ---- door + walk
    g.new_game(0, 1)
    for _ in range(80):
        step(1, fwd=1)
        if g.py < 38.8:
            break
    g.use()
    step(40)
    assert g.level.door_obj(7, 37).open >= 1.0, "door did not open"
    for _ in range(70):
        step(1, fwd=1)
    assert g.py < 36.5, "player did not walk through the door"
    print("doors ok")

    # ---- every weapon fires and uses ammo
    g.new_game(5, 1)
    g.enemies, g.boss = [], None
    for w in WEAPON_ORDER:
        g.owned[w] = True
    for k in MAXAMMO:
        g.ammo[k] = MAXAMMO[k]
    g.px, g.py, g.ang = 22.5, 30.5, -math.pi / 2
    for w in WEAPON_ORDER:
        g.weapon, g.wstate = w, "up"
        before = dict(g.ammo)
        step(1, fire=True)
        step(40)
        spec = WEAPONS[w]
        if spec["ammo"]:
            assert g.ammo[spec["ammo"]] == before[spec["ammo"]] - spec["cost"], ("ammo not used", w)
    print("weapons ok")

    # ---- combat vs each enemy type
    for kind in ("quackling", "mallard", "fireswan", "pelican", "gosling", "heron", "brute"):
        g.new_game(5, 1)
        g.boss = None
        e = Enemy(kind, 22.5, 26.5)
        g.enemies = [e]
        g.kills_total = 1
        g.px, g.py, g.ang = 22.5, 30.5, -math.pi / 2
        g.health = 200
        g.owned["egggun"] = True
        g.ammo["eggs"] = 50
        g.weapon = "egggun"
        g.wake(e)
        for _ in range(35 * 12):
            g.ang = math.atan2(e.y - g.py, e.x - g.px)
            step(1, fire=True)
            if not e.alive or g.dead:
                break
        assert not e.alive, ("could not kill", kind, e.hp)
    print("all enemy types killable")

    # ---- teleporter
    g.new_game(1, 1)
    a, b = next(iter(g.level.tele.items()))
    g.px, g.py = a[0] + 0.5, a[1] + 0.5
    step(1)
    assert (int(g.px), int(g.py)) == b, "teleport failed"
    step(5)
    assert (int(g.px), int(g.py)) == b, "teleport ping-ponged"
    print("teleport ok")

    # ---- powerups
    g.new_game(3, 1)
    g.pickups.append(Pickup("goldegg", g.px, g.py))
    step(1)
    hp = g.health
    g.damage_player(50)
    assert g.health == hp and g.invuln > 0, "golden egg failed"
    print("powerups ok")

    # ---- passive regen: nothing for REGEN_DELAY, then +1 per REGEN_EVERY, capped
    g.new_game(0, 1)
    g.enemies = []
    g.health = 50
    g.calm_t = 0.0
    step(int(35 * (REGEN_DELAY - 0.5)))
    assert g.health == 50, ("regen started too early", g.health)
    step(int(35 * (0.5 + REGEN_EVERY * 4 + 0.2)))
    assert 53 <= g.health <= 55, ("regen rate off", g.health)
    g.health = REGEN_CAP
    step(35 * 3)
    assert g.health == REGEN_CAP, "regen went over the cap"
    print("regen ok")

    # ---- solo death restarts the level
    g.new_game(1, 1)
    g.damage_player(500)
    assert g.dead
    step(40)
    step(1, use=True)
    assert not g.dead and g.health == 100 and g.level_idx == 1, "solo restart failed"
    print("solo death/restart ok")

    # ---- boss fight and the end of the episode
    g.new_game(5, 1)
    boss = g.boss
    g.owned["megahonk"] = True
    g.ammo["corn"] = 300
    g.weapon = "megahonk"
    g.health = 200
    g.invuln = 999
    g.px, g.py = 22.5, 24.5
    for _ in range(35 * 40):
        g.ang = math.atan2(boss.y - g.py, boss.x - g.px)
        step(1, fire=True)
        if g.mode != "play":
            break
    shot(g, "boss_fight")
    assert not boss.alive, ("boss survived", boss.hp)
    assert g.mode == "intermission", g.mode
    g.next_level()
    assert g.mode == "victory"
    g.inter_t = 10
    g.draw_victory()
    shot(g, "victory")
    print("boss + victory ok")

    # ---- progression keeps the loadout, refills health, tops up ammo, saves
    g.new_game(0, 1)
    g.owned["egggun"] = True
    g.ammo["eggs"] = 33
    g.health = 20
    g.finish_level()
    g.inter_t = 5
    g.draw_intermission()
    shot(g, "intermission")
    g.next_level()
    assert g.level_idx == 1 and g.owned["egggun"], "carry-over failed"
    assert g.health == 100, ("no health refill", g.health)
    assert g.ammo["eggs"] == 33 + LEVEL_AMMO_BONUS["eggs"], ("no ammo top-up", g.ammo)
    assert load_save()["unlocked"] >= 2, "save not written"
    print("progression + save ok")

    # ---- CO-OP: a host and two clients in this process, over real localhost sockets
    host, c1, c2 = g, Game(headless=True), Game(headless=True)
    host.leave_coop()
    host.pick_level, host.skill = 0, 1
    assert host.start_host("127.0.0.1"), host.banner     # localhost only: never collide with real games on a VPN
    assert c1.start_join("127.0.0.1"), c1.banner
    for _ in range(300):
        host.host_accept_tick()
        host.host_net_tick()
        c1.client_net_tick()
        if len(host.players) == 2 and c1.mode == "client_lobby":
            break
        time.sleep(0.01)
    assert host.role == "host" and len(host.players) == 2, (
        "host never accepted the client", host.mode, host.banner, c1.mode, c1.banner)
    assert host.mode == "host_wait" and host.level is None, "match started before the host pressed START"
    assert c1.mode == "client_lobby" and c1.lobby["players"] == [0, 1], ("joiner not in lobby", c1.mode)
    host.draw_lobby()
    shot(host, "lobby_host")
    c1.draw_lobby()
    shot(c1, "lobby_joiner")
    host.lobby_start()
    clients = [c1]
    print("co-op lobby ok")

    def coop_frames(n, inputs=None):
        for _ in range(n):
            host.host_accept_tick()
            host.update(1 / 35, {})
            host.host_net_tick()
            time.sleep(0.002)
            for c in clients:
                c.client_net_tick()
                if c.mode == "play" and c.level is not None:
                    c.client_step(1 / 35, dict((inputs or {}).get(c, {})))
            time.sleep(0.002)
            host.host_net_tick()

    coop_frames(20)
    assert c1.level is not None and c1.level_idx == 0 and c1.mode == "play", "client never got the level"
    p2 = host.players[1]
    assert abs(p2.px - c1.me.px) < 0.01, "client spawn not synced"
    c1.draw_play()
    shot(c1, "coop_client_start")
    y0 = p2.py
    coop_frames(30, {c1: dict(fwd=1)})
    assert p2.py < y0 - 0.5, ("host did not get client movement", y0, p2.py)
    print("co-op connect + movement sync ok")

    # a third goose joins a game that's already running
    assert c2.start_join("127.0.0.1"), c2.banner
    clients.append(c2)
    coop_frames(30)
    assert len(host.players) == 3 and c2.mode == "play" and c2.level_idx == host.level_idx, "late join failed"
    p3 = host.players[2]
    assert p3.pid == 2 and math.hypot(p3.px - host.me.px, p3.py - host.me.py) > 0.5, "P3 spawned on top of P1"
    assert sorted(k for k, *_ in host.drawables(host.me) if k.startswith("goose")) == ["goose1", "goose2"]
    for p in (p2, p3):
        assert len([t for t in host.build_snapshot(p)["things"] if t[0].startswith("goose")]) == 2, "missing geese"
    coop_frames(5)
    assert len(c2.mates) == 2 and len(c1.mates) == 2, "HUD partner list wrong"
    c2.me.ang = math.atan2(host.me.py - c2.me.py, host.me.px - c2.me.px)
    coop_frames(3)
    c2.draw_play()
    shot(c2, "coop3_late_joiner")
    print("3-player co-op + late join ok")

    # client opens the gazebo door
    c1.me.px, c1.me.py, c1.me.ang = 7.5, 38.7, -math.pi / 2
    coop_frames(3)
    coop_frames(1, {c1: dict(use=True)})
    coop_frames(40)
    assert host.level.door_obj(7, 37).open >= 1.0, "client could not open a door"
    assert c2.level.door_obj(7, 37).open >= 0.99, "door state not synced to the other client"
    print("co-op doors ok")

    # client shoots a monster the host simulates
    e = Enemy("quackling", 7.5, 33.5)
    host.enemies = [e]          # just this one, so nothing else gets in the way
    host.kills_total += 1
    c1.me.px, c1.me.py, c1.me.ang = 7.5, 36.0, -math.pi / 2
    k0 = host.kills
    for _ in range(300):
        c1.me.ang = math.atan2(e.y - c1.me.py, e.x - c1.me.px)   # track it like a real player
        coop_frames(1, {c1: dict(fire=True)})
        if not e.alive:
            break
    assert not e.alive and host.kills == k0 + 1, "client's shots did not count on the host"
    c1.draw_play()
    shot(c1, "coop_client_kill")
    print("co-op combat ok")

    # one goose dies and respawns while the others live
    host.cur = p2
    host.damage_player(999)
    host.cur = host.me
    coop_frames(40)
    assert c1.me.dead, "client death not synced"
    coop_frames(1, {c1: dict(use=True)})
    coop_frames(10)
    assert not p2.dead and not c1.me.dead and p2.health == 100, "respawn failed"
    print("co-op death + respawn ok")

    # the whole flock dies: level restarts by itself
    for p in host.players:
        host.cur = p
        host.damage_player(999)
    host.cur = host.me
    coop_frames(int(35 * 3.6))
    assert all(not p.dead for p in host.players), "flock wipe did not restart the level"
    print("co-op flock wipe restart ok")

    # level change follows the host, and joiners save their progress too
    c1.unlocked = 1
    c1.save["unlocked"] = 1
    host.finish_level()
    coop_frames(5)
    assert c1.mode == "intermission" and c2.mode == "intermission", (c1.mode, c2.mode)
    assert c1.unlocked == 2 and load_save()["unlocked"] >= 2, "joiner did not save the unlocked level"
    c1.draw_intermission()
    shot(c1, "coop_client_intermission")
    host.next_level()
    coop_frames(10)
    assert all(c.mode == "play" and c.level_idx == 1 for c in clients), "clients did not follow to level 2"
    print("co-op level change + joiner save ok")

    # players leave one at a time; the host keeps going
    c2.leave_coop()
    clients.remove(c2)
    coop_frames(5)
    assert host.role == "host" and len(host.players) == 2, "host did not drop P3 cleanly"
    c1.leave_coop()
    clients.remove(c1)
    coop_frames(5)
    assert len(host.players) == 1, "host did not drop P2 cleanly"
    host.leave_coop()
    print("co-op disconnect ok")

    # ---- fuzz every level
    g = host
    rnd = random.Random(3)
    for i in range(NUM_LEVELS):
        g.new_game(i, 1)
        for n in range(35 * 15):
            inp = dict(fwd=rnd.choice((-1, 0, 1, 1)), strafe=rnd.choice((-1, 0, 1)), turn=rnd.uniform(-0.1, 0.1),
                       fire=rnd.random() < 0.3, use=rnd.random() < 0.05)
            if rnd.random() < 0.03:
                inp["w%d" % rnd.randint(1, 6)] = True
            g.update(1 / 35, inp)
            if g.mode == "play" and n % 15 == 0:
                g.draw_play()
    print("fuzz ok")

    # ---- speed
    g.new_game(4, 1)
    t1 = time.time()
    for _ in range(60):
        g.update(1 / 60, {})
        g.draw_play()
    ms = (time.time() - t1) / 60 * 1000
    print("frame time %.1f ms (%.0f fps)" % (ms, 1000 / ms))
    print("ALL OK")


def update_now(report):
    """Test hook: check, download and apply an update with no window, then the new exe reports in."""
    up = Updater()
    up._check_and_fetch()
    with open(report, "a") as f:
        f.write("old %s state=%s latest=%s err=%s\n" % (APP_VERSION, up.state, up.latest, up.error))
    if up.state == "ready":
        up.apply_and_restart(["--report-version", report])


def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--selftest":
        if sys.stdout is None:           # windowed exe has no console
            os.makedirs(args[1], exist_ok=True)
            sys.stdout = sys.stderr = open(os.path.join(args[1], "selftest.log"), "w")
        selftest(args[1])
        return
    if len(args) >= 2 and args[0] == "--report-version":
        with open(args[1], "a") as f:
            f.write("new process %s from %s\n" % (APP_VERSION, sys.executable))
        return
    if len(args) >= 2 and args[0] == "--update-now":
        update_now(args[1])
        return
    Game().run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        log = os.path.join(os.path.dirname(SAVE), "crash.log")
        try:
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "a") as f:
                f.write("\n=== %s v%s ===\n" % (time.ctime(), APP_VERSION))
                traceback.print_exc(file=f)
        except OSError:
            pass
        raise
