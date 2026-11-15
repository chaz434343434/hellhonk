"""HONK: three original episodes, sixteen levels.

Every level is built from rectangles with room()/door()/put() so the layouts
stay easy to read and edit. (x right, y down; grid is MW x MH cells.)
"""
import numpy as np

from assets import Assets as A

MW = MH = 48
SKY = -1


class Door:
    def __init__(self, x, y, tex, key=None, secret=False):
        self.x, self.y, self.tex, self.key, self.secret = x, y, tex, key, secret
        self.open = 0.0       # 0 closed .. 1 fully raised
        self.dir = 0          # +1 opening, -1 closing
        self.wait = 0.0       # time left fully open before closing


class Level:
    def __init__(self, index=0):
        self.index = index
        self.wall = np.full((MH, MW), A.BRICK, dtype=np.int16)   # -1 = open cell
        self.floor = np.full((MH, MW), A.TILES, dtype=np.int16)
        self.ceil = np.full((MH, MW), SKY, dtype=np.int16)
        self.light = np.full((MH, MW), 1.0, dtype=np.float32)
        self.flicker = np.zeros((MH, MW), dtype=bool)
        self.hurt = np.zeros((MH, MW), dtype=np.int16)          # damage per second
        self.door_at = np.full((MH, MW), -1, dtype=np.int16)
        self.claimed = np.zeros((MH, MW), dtype=bool)
        self.doors = []
        self.secret_cells = {}
        self.secrets_total = 0
        self.things = []
        self.tele = {}
        self.exit_cell = None
        self.boss_level = False
        self.sky = "hell"
        self.song = index
        self.episode = 0
        BUILDERS[index](self)
        self.episode = episode_of(index)
        for edge in (self.wall[0, :], self.wall[-1, :], self.wall[:, 0], self.wall[:, -1]):
            edge[edge < 0] = A.BRICK

    # ---------------------------------------------------------- building helpers
    def room(self, x0, y0, x1, y1, floor, ceil, light, walls, flicker=False):
        # a wall cell keeps the texture of the first room that claimed it
        for y in range(y0 - 1, y1 + 2):
            for x in range(x0 - 1, x1 + 2):
                if (0 <= x < MW and 0 <= y < MH and self.wall[y, x] >= 0 and self.door_at[y, x] < 0
                        and not self.claimed[y, x]):
                    self.wall[y, x] = walls
                    self.claimed[y, x] = True
        self.wall[y0:y1 + 1, x0:x1 + 1] = -1
        self.floor[y0:y1 + 1, x0:x1 + 1] = floor
        self.ceil[y0:y1 + 1, x0:x1 + 1] = ceil
        self.light[y0:y1 + 1, x0:x1 + 1] = light
        self.flicker[y0:y1 + 1, x0:x1 + 1] = flicker

    def door(self, x, y, tex=A.DOOR, key=None, secret=False, floor=A.TILES, ceil=A.BEAMS, light=0.8):
        self.wall[y, x] = tex
        self.floor[y, x] = floor
        self.ceil[y, x] = ceil
        self.light[y, x] = light
        self.door_at[y, x] = len(self.doors)
        self.doors.append(Door(x, y, tex, key, secret))

    def secret_room(self, door_xy, base_tex, x0, y0, x1, y1, floor, ceil, light=0.5):
        self.room(x0, y0, x1, y1, floor, ceil, light, base_tex)
        self.door(door_xy[0], door_xy[1], A.crack(base_tex), secret=True, floor=floor, ceil=ceil, light=light)
        self.secret([(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)])

    def pool(self, x0, y0, x1, y1, dmg=5):
        self.floor[y0:y1 + 1, x0:x1 + 1] = A.SLUDGE
        self.hurt[y0:y1 + 1, x0:x1 + 1] = dmg

    def lava(self, x0, y0, x1, y1):
        self.floor[y0:y1 + 1, x0:x1 + 1] = A.LAVA
        self.hurt[y0:y1 + 1, x0:x1 + 1] = 10
        self.light[y0:y1 + 1, x0:x1 + 1] = 1.0

    def strip(self, x0, y0, x1, y1, floor):
        self.floor[y0:y1 + 1, x0:x1 + 1] = floor
        self.hurt[y0:y1 + 1, x0:x1 + 1] = 0

    def solid(self, x, y, tex, w=1, h=1):
        self.wall[y:y + h, x:x + w] = tex

    def teleport(self, a, b):
        for (x, y) in (a, b):
            self.floor[y, x] = A.TELE
            self.hurt[y, x] = 0
        self.tele[a] = b
        self.tele[b] = a

    def secret(self, cells):
        sid = self.secrets_total
        self.secrets_total += 1
        for c in cells:
            self.secret_cells[c] = sid

    def put(self, kind, x, y, flags=""):
        self.things.append((kind, x + 0.5, y + 0.5, flags))

    def puts(self, kind, cells, flags=""):
        for x, y in cells:
            self.put(kind, x, y, flags)

    # ---------------------------------------------------------- queries
    def door_obj(self, x, y):
        i = self.door_at[y, x] if (0 <= x < MW and 0 <= y < MH) else -1
        return self.doors[i] if i >= 0 else None

    def passable(self, x, y):
        if not (0 <= x < MW and 0 <= y < MH):
            return False
        if self.wall[y, x] < 0:
            return True
        d = self.door_obj(x, y)
        return d is not None and d.open > 0.85


# ======================================================================= L1
def e1l1(L):
    L.name, L.par, L.sky = "E1L1: GATEHOUSE GROUNDS", 120, "hell"
    L.room(4, 38, 10, 44, A.WOODF, A.BEAMS, 0.85, A.WOOD)
    L.start = (7.5, 42.5, -np.pi / 2)
    L.door(7, 37, floor=A.WOODF, ceil=A.BEAMS)
    L.puts("feather", [(5, 39), (9, 39)])
    L.put("remains", 9, 43)
    L.room(6, 29, 8, 36, A.GRASS, SKY, 1.0, A.HEDGE)
    L.room(6, 28, 18, 30, A.GRASS, SKY, 1.0, A.HEDGE)
    L.puts("quackling", [(7, 32), (13, 29)])
    L.puts("crumbs", [(7, 34), (10, 29)])
    L.put("pebbles", 17, 30)
    L.room(14, 14, 31, 27, A.TILES, SKY, 1.0, A.HEDGE)
    L.pool(19, 18, 26, 23)
    L.strip(19, 20, 26, 21, A.TILES)
    L.puts("tree", [(15, 15), (30, 15), (30, 26)])
    L.puts("lamp", [(18, 17), (27, 17), (18, 24), (27, 24)])
    L.puts("barrel", [(20, 25), (21, 25), (28, 20)])
    L.put("egggun", 22, 20)
    L.puts("crumbs", [(19, 21), (25, 21)])
    L.put("bread", 16, 14)
    L.put("pebbles", 30, 22)
    L.put("eggs", 23, 21)
    L.put("remains", 24, 25)
    L.puts("quackling", [(16, 22), (29, 18)])
    L.puts("fireswan", [(24, 15), (29, 25)])
    L.put("quackling", 20, 15, "hard")
    L.room(3, 12, 11, 22, A.TILES, SKY, 0.95, A.GLASS)
    L.room(12, 17, 12, 17, A.TILES, SKY, 0.95, A.GLASS)
    L.door(13, 17, floor=A.TILES, ceil=A.BEAMS)
    for x in range(2, 13):
        L.wall[23, x] = A.BRICK
    L.puts("planter", [(6, 15), (8, 15), (6, 19), (8, 19)])
    L.put("ykey", 4, 13)
    L.put("loaf", 10, 21)
    L.put("fireswan", 9, 13)
    L.put("fireswan", 4, 20, "notEasy")
    L.put("quackling", 10, 18)
    L.room(6, 24, 8, 26, A.TILES, A.BEAMS, 0.5, A.BRICK)
    L.door(7, 23, A.CRACK, secret=True, floor=A.TILES, ceil=A.BEAMS, light=0.5)
    L.secret([(x, y) for x in range(6, 9) for y in range(24, 27)])
    L.put("vest", 7, 25)
    L.puts("eggs", [(6, 24), (8, 24)])
    L.room(32, 19, 32, 19, A.TILES, SKY, 1.0, A.HEDGE)
    L.room(34, 12, 44, 24, A.WOODF, A.BEAMS, 0.6, A.WOOD, flicker=True)
    L.door(33, 19, A.YDOOR, key="yellow", floor=A.WOODF, ceil=A.BEAMS, light=0.6)
    L.pool(40, 13, 43, 23)
    L.strip(40, 17, 43, 19, A.WOODF)
    L.puts("crate", [(36, 13), (37, 13), (36, 23)])
    L.put("bkey", 42, 18)
    L.put("pebblebox", 35, 23)
    L.put("eggs", 43, 19)
    L.put("bread", 38, 23)
    L.put("brute", 38, 15)
    L.put("brute", 38, 21, "notEasy")
    L.puts("quackling", [(35, 17), (42, 17)])
    L.put("brute", 36, 19, "hard")
    L.room(22, 11, 22, 13, A.METALF, A.LIGHTS, 0.7, A.METAL)
    L.door(22, 10, A.BDOOR, key="blue", floor=A.METALF, ceil=A.LIGHTS, light=0.7)
    L.room(18, 3, 27, 9, A.METALF, A.LIGHTS, 0.75, A.METAL)
    L.solid(20, 5, A.METAL)
    L.solid(25, 5, A.METAL)
    L.wall[2, 22] = A.SWOFF
    L.exit_cell = (22, 2)
    L.put("fireswan", 19, 4)
    L.put("brute", 24, 7)
    L.put("quackling", 26, 3)
    L.put("quackling", 19, 8, "notEasy")
    L.put("loaf", 26, 8)
    L.put("pebbles", 18, 3)
    L.room(29, 9, 31, 12, A.GRASS, SKY, 0.9, A.HEDGE)
    L.door(29, 13, A.HEDGEX, secret=True, floor=A.GRASS, ceil=SKY, light=0.9)
    L.secret([(x, y) for x in range(29, 32) for y in range(9, 13)])
    L.put("loaf", 30, 10)
    L.put("pebblebox", 29, 9)
    L.puts("feather", [(31, 12), (31, 11)])


# ======================================================================= L2
def e1l2(L):
    L.name, L.par, L.sky = "E1L2: THE DUCK SEWERS", 150, "hell"
    F, C, W = A.STONEF, A.PIPES, A.SEWER
    # start
    L.room(2, 2, 7, 6, F, C, 0.65, W)
    L.start = (4.5, 4.5, 0.0)
    L.put("pebbles", 3, 3)
    L.door(8, 4, floor=F, ceil=C, light=0.6)
    # sewer hall with a one-wide bridge over the sludge
    L.room(9, 2, 24, 12, F, C, 0.55, W)
    L.pool(12, 5, 21, 9)
    L.strip(12, 7, 21, 7, F)
    L.puts("quackling", [(14, 3), (20, 11)])
    L.put("mallard", 22, 4)
    L.puts("gosling", [(11, 10), (12, 11), (13, 10)])
    L.puts("barrel", [(23, 11), (23, 10)])
    L.put("pebbles", 10, 3)
    L.puts("crumbs", [(15, 7), (17, 7), (19, 7)])
    L.put("quackling", 10, 11, "hard")
    # control room (yellow door)
    L.door(25, 7, A.YDOOR, key="yellow", floor=A.METALF, ceil=A.LIGHTS, light=0.85)
    L.room(26, 3, 37, 11, A.METALF, A.LIGHTS, 0.85, A.METAL)
    for x, y in ((29, 5), (34, 5), (29, 9), (34, 9)):
        L.solid(x, y, A.METAL)
    L.put("flinger", 31, 7)
    L.put("bkey", 36, 4)
    L.puts("mallard", [(28, 10), (35, 10)])
    L.put("quackling", 32, 4)
    L.put("fireswan", 36, 9, "notEasy")
    L.put("pebblebox", 27, 4)
    # secret behind the control room's east wall
    L.secret_room((38, 7), A.METAL, 39, 5, 41, 9, A.METALF, A.LIGHTS, 0.6)
    L.put("rage", 40, 7)
    L.put("pebblebox", 40, 5)
    L.put("crumbs", 41, 9)
    # tunnel south of the hall
    L.door(16, 13, floor=F, ceil=C, light=0.5)
    L.room(10, 14, 22, 17, F, C, 0.5, W, flicker=True)
    L.pool(10, 17, 22, 17)
    L.puts("quackling", [(12, 15)])
    L.put("fireswan", 20, 15)
    L.puts("gosling", [(15, 16), (16, 16), (17, 16)])
    L.put("eggs", 21, 14)
    L.secret_room((21, 18), A.SEWER, 20, 19, 22, 21, F, C, 0.4)
    L.put("vest", 21, 20)
    L.put("eggs", 20, 19)
    L.put("pebblebox", 22, 21)
    # yellow key vault (west)
    L.door(9, 15, floor=F, ceil=C, light=0.45)
    L.room(2, 12, 8, 20, F, C, 0.45, W)
    L.pool(2, 17, 5, 20)
    L.put("ykey", 3, 19)
    L.put("brute", 6, 14)
    L.put("quackling", 4, 13)
    L.put("bread", 7, 19)
    L.teleport((7, 13), (2, 6))
    # exit room (blue door)
    L.door(31, 12, A.BDOOR, key="blue", floor=A.METALF, ceil=A.LIGHTS, light=0.75)
    L.room(27, 13, 36, 19, A.METALF, A.LIGHTS, 0.75, A.METAL)
    L.wall[20, 31] = A.SWOFF
    L.exit_cell = (31, 20)
    L.puts("brute", [(29, 16), (34, 16)])
    L.put("fireswan", 28, 18)
    L.put("mallard", 35, 18, "hard")
    L.put("loaf", 35, 14)
    L.put("pebbles", 28, 14)


# ======================================================================= L3
def e1l3(L):
    L.name, L.par, L.sky = "E1L3: THE BREAD FACTORY", 210, "dusk"
    # yard (outdoors)
    L.room(2, 2, 14, 12, A.TILES, SKY, 1.0, A.BRICK)
    L.start = (4.5, 10.5, -np.pi / 2)
    L.puts("tree", [(3, 3), (13, 3)])
    L.puts("barrel", [(7, 6), (8, 6), (12, 11)])
    L.puts("quackling", [(10, 4), (6, 3), (13, 8)])
    L.put("fireswan", 11, 9)
    L.puts("gosling", [(4, 5), (5, 5)])
    L.put("pebbles", 2, 7)
    # loading bay
    L.door(15, 7, floor=A.FACTF, ceil=A.LIGHTS, light=0.8)
    L.room(16, 3, 28, 12, A.FACTF, A.LIGHTS, 0.8, A.FACTORY)
    L.puts("crate", [(18, 6), (19, 6), (18, 7), (24, 9), (25, 9), (24, 10), (21, 4)])
    L.put("pelican", 26, 5)
    L.put("mallard", 20, 10)
    L.put("quackling", 18, 4)
    L.put("pelican", 27, 11, "notEasy")
    L.puts("eggs", [(22, 11)])
    L.put("pebbles", 17, 11)
    # ovens (yellow key) with lava channels
    L.door(29, 8, floor=A.METALF, ceil=A.LIGHTS, light=0.9)
    L.room(30, 3, 42, 13, A.METALF, A.LIGHTS, 0.9, A.FACTORY)
    L.lava(33, 5, 34, 11)
    L.lava(38, 5, 39, 11)
    L.puts("fireswan", [(36, 4), (36, 12)])
    L.put("pelican", 41, 8)
    L.put("brute", 31, 12, "notEasy")
    L.put("ykey", 41, 12)
    L.put("loaf", 36, 8)
    L.put("boots", 31, 5)
    # mill (yellow door from yard) - bazooka + red key
    L.door(8, 13, A.YDOOR, key="yellow", floor=A.WOODF, ceil=A.BEAMS, light=0.65)
    L.room(3, 14, 20, 22, A.WOODF, A.BEAMS, 0.65, A.WOOD, flicker=True)
    for x, y in ((7, 17), (12, 17), (7, 20), (12, 20), (16, 17), (16, 20)):
        L.solid(x, y, A.WOOD)
    L.puts("brute", [(10, 16), (14, 21)])
    L.put("mallard", 18, 15)
    L.puts("gosling", [(5, 19), (5, 20), (6, 21)])
    L.put("bazooka", 12, 18)
    L.put("baguettes", 4, 21)
    L.put("rkey", 19, 21)
    L.put("bread", 18, 21)
    L.teleport((4, 15), (31, 4))
    L.secret_room((10, 23), A.WOOD, 9, 24, 11, 26, A.WOODF, A.BEAMS, 0.45)
    L.put("rage", 10, 25)
    L.put("baguettes", 9, 24)
    # packing hall (red door from ovens) - exit
    L.door(36, 14, A.RDOOR, key="red", floor=A.FACTF, ceil=A.LIGHTS, light=0.75)
    L.room(26, 15, 42, 22, A.FACTF, A.LIGHTS, 0.75, A.METAL)
    L.puts("crate", [(28, 17), (29, 17), (38, 20), (39, 20)])
    L.puts("pelican", [(30, 21), (40, 16)])
    L.puts("mallard", [(34, 18), (41, 21)])
    L.put("fireswan", 27, 20)
    L.put("brute", 35, 21, "hard")
    L.put("loaf", 26, 15)
    L.put("baguette", 42, 15)
    L.wall[18, 43] = A.SWOFF
    L.exit_cell = (43, 18)
    L.secret_room((31, 23), A.METAL, 30, 24, 32, 26, A.METALF, A.LIGHTS, 0.5)
    L.put("downjacket", 31, 25)
    L.put("eggcrate", 30, 24)


# ======================================================================= L4
def e1l4(L):
    L.name, L.par, L.sky = "E1L4: FROZEN FOUNTAIN", 210, "night"
    # courtyard
    L.room(12, 10, 32, 28, A.SNOW, SKY, 0.9, A.ICE)
    L.start = (22.5, 27.5, -np.pi / 2)
    L.solid(21, 18, A.ICE, 3, 3)                      # the frozen fountain
    L.puts("lamp", [(19, 16), (25, 16), (19, 22), (25, 22)])
    L.puts("snowman", [(13, 27), (31, 27), (13, 11)])
    L.puts("tree", [(31, 11), (14, 20), (30, 20)])
    L.puts("heron", [(16, 12), (28, 12)])
    L.puts("quackling", [(15, 24), (29, 24), (22, 14)])
    L.put("fireswan", 22, 23)
    L.put("pelican", 26, 13, "notEasy")
    L.puts("crumbs", [(17, 27), (27, 27)])
    L.put("baguettes", 22, 25)
    # chapel (west) - blue key
    L.door(11, 19, floor=A.TILES, ceil=A.BEAMS, light=0.6)
    L.room(2, 14, 10, 24, A.TILES, A.BEAMS, 0.6, A.CASTLE, flicker=True)
    L.puts("candle", [(3, 15), (9, 15), (3, 23), (9, 23)])
    L.put("bkey", 3, 19)
    L.put("brute", 6, 17)
    L.put("fireswan", 8, 21)
    L.puts("gosling", [(4, 22), (5, 22), (6, 22), (7, 22)])
    L.put("loaf", 9, 19)
    L.teleport((3, 24), (31, 28))
    L.secret_room((5, 13), A.CASTLE, 4, 10, 6, 12, A.TILES, A.BEAMS, 0.5)
    L.put("downjacket", 5, 11)
    # ice cave (east, blue door) - red key
    L.door(33, 19, A.BDOOR, key="blue", floor=A.SNOW, ceil=SKY, light=0.75)
    L.room(34, 12, 44, 26, A.SNOW, SKY, 0.7, A.ICE)
    for x, y in ((36, 14), (40, 15), (37, 19), (42, 20), (36, 23), (40, 24)):
        L.solid(x, y, A.ICE)
    L.puts("heron", [(41, 13), (43, 22)])
    L.put("pelican", 38, 25)
    L.put("mallard", 35, 17)
    L.put("heron", 39, 21, "hard")
    L.put("rkey", 43, 25)
    L.put("eggs", 35, 25)
    L.put("pebblebox", 44, 12)
    # gatehouse (north, red door) - exit
    L.door(22, 9, A.RDOOR, key="red", floor=A.TILES, ceil=A.BEAMS, light=0.75)
    L.room(16, 2, 28, 8, A.TILES, A.BEAMS, 0.75, A.CASTLE)
    L.solid(19, 4, A.CASTLE)
    L.solid(25, 4, A.CASTLE)
    L.puts("brute", [(18, 6), (26, 6)])
    L.put("mallard", 22, 3)
    L.put("heron", 27, 3)
    L.put("loaf", 17, 3)
    L.wall[1, 22] = A.SWOFF
    L.exit_cell = (22, 1)
    # secret: golden egg behind the south ice wall
    L.secret_room((14, 29), A.ICE, 13, 30, 15, 32, A.SNOW, SKY, 0.6)
    L.put("goldegg", 14, 31)
    L.put("pebblebox", 13, 30)


# ======================================================================= L5
def e1l5(L):
    L.name, L.par, L.sky = "E1L5: THE NESTING GROUNDS", 240, "fire"
    H, N = A.HELL, A.NEST
    # start ledge opening onto the lava field
    L.room(3, 20, 9, 26, A.ASH, SKY, 1.0, H)
    L.start = (6.5, 25.5, -0.35)
    L.put("cornsack", 4, 25)
    L.put("loaf", 8, 21)
    L.room(10, 14, 30, 30, A.ASH, SKY, 1.0, H)
    L.lava(11, 15, 29, 29)
    L.strip(10, 22, 30, 22, A.ASH)            # east-west causeway
    L.strip(20, 14, 20, 30, A.ASH)            # north-south causeway
    L.strip(24, 26, 28, 29, A.ASH)            # island
    L.strip(12, 15, 13, 17, A.ASH)            # teleport ledge
    L.puts("fireswan", [(26, 22), (20, 27)])
    L.puts("pelican", [(20, 16), (26, 28)])
    L.put("heron", 15, 22)
    L.puts("gosling", [(22, 22), (23, 22), (20, 19), (20, 18)])
    L.put("baguettes", 27, 27)
    L.put("rage", 25, 29)
    L.teleport((12, 15), (15, 4))
    # temple (north) - yellow key + MEGAHONK
    L.room(20, 13, 20, 13, A.ASH, SKY, 1.0, N)
    L.door(20, 12, floor=A.ASH, ceil=SKY, light=0.9)
    L.room(14, 3, 26, 11, A.ASH, SKY, 0.9, N)
    L.puts("candle", [(15, 10), (25, 10), (15, 3), (25, 3)])
    L.put("megahonk", 20, 6)
    L.put("ykey", 25, 4)
    L.puts("brute", [(17, 8), (23, 8)])
    L.put("brute", 20, 9, "notEasy")
    L.put("heron", 18, 4)
    L.put("mallard", 24, 6)
    L.put("corn", 21, 6)
    L.secret_room((27, 7), N, 28, 6, 30, 8, A.ASH, SKY, 0.6)
    L.put("downjacket", 29, 7)
    L.put("cornsack", 30, 6)
    # hatchery (east, yellow door) - red key
    L.door(31, 22, A.YDOOR, key="yellow", floor=A.ASH, ceil=SKY, light=0.9)
    L.room(32, 14, 44, 28, A.ASH, SKY, 0.9, N)
    L.puts("eggpile", [(34, 16), (42, 17), (35, 26), (41, 26), (38, 21)])
    L.put("rkey", 43, 15)
    L.puts("pelican", [(36, 18), (40, 24)])
    L.put("heron", 43, 27)
    L.puts("fireswan", [(33, 25), (42, 21)])
    L.put("brute", 37, 15)
    L.puts("gosling", [(38, 19), (39, 19), (38, 23), (39, 23), (36, 21), (40, 21)])
    L.put("eggcrate", 44, 22)
    L.put("bread", 33, 15)
    L.secret_room((38, 29), N, 37, 30, 39, 32, A.ASH, SKY, 0.6)
    L.put("goldegg", 38, 31)
    L.put("baguettes", 37, 30)
    # pit (north of the start, red door) - exit
    L.room(5, 18, 5, 18, A.ASH, A.BEAMS, 0.5, H)
    L.door(5, 19, A.RDOOR, key="red", floor=A.ASH, ceil=A.BEAMS, light=0.5)
    L.room(2, 3, 8, 17, A.ASH, A.BEAMS, 0.5, H, flicker=True)
    L.lava(2, 8, 4, 12)
    L.puts("brute", [(6, 14), (3, 5)])
    L.put("heron", 7, 7)
    L.puts("mallard", [(3, 15), (7, 4)])
    L.put("loaf", 8, 16)
    L.put("corn", 2, 16)
    L.wall[2, 5] = A.SWOFF
    L.exit_cell = (5, 2)


# ======================================================================= L6
def e1l6(L):
    L.name, L.par, L.sky = "E1L6: THRONE OF THE HONKMOTHER", 180, "fire"
    L.boss_level = True
    H, N = A.HELL, A.NEST
    # antechamber stocked for the fight
    L.room(18, 38, 26, 44, A.ASH, SKY, 0.8, H)
    L.start = (22.5, 43.5, -np.pi / 2)
    L.puts("cornsack", [(19, 39), (25, 39)])
    L.puts("baguettes", [(19, 43), (25, 43)])
    L.put("eggcrate", 22, 41)
    L.puts("loaf", [(20, 40), (24, 40)])
    L.put("downjacket", 22, 39)
    L.door(22, 37, floor=A.ASH, ceil=SKY, light=0.9)
    # the arena
    L.room(8, 8, 36, 36, A.ASH, SKY, 1.0, N)
    for x0, y0 in ((9, 9), (32, 9), (9, 32), (32, 32)):
        L.lava(x0, y0, x0 + 3, y0 + 3)
    for x0, y0 in ((15, 15), (28, 15), (15, 28), (28, 28)):
        L.solid(x0, y0, H, 2, 2)
    L.puts("eggpile", [(14, 22), (30, 22), (22, 12)])
    L.puts("barrel", [(18, 20), (26, 20), (18, 25), (26, 25)])
    L.put("honkmother", 22, 14)
    L.puts("gosling", [(20, 17), (24, 17)])
    L.puts("heron", [(11, 22)], "notEasy")
    L.puts("heron", [(33, 22)], "hard")
    # supply alcoves
    L.door(7, 22, floor=A.ASH, ceil=A.BEAMS, light=0.7)
    L.room(3, 20, 6, 24, A.ASH, A.BEAMS, 0.7, H)
    L.puts("loaf", [(4, 21), (4, 23)])
    L.put("corn", 3, 22)
    L.door(37, 22, floor=A.ASH, ceil=A.BEAMS, light=0.7)
    L.room(38, 20, 41, 24, A.ASH, A.BEAMS, 0.7, H)
    L.put("goldegg", 40, 22)
    L.put("baguettes", 39, 21)
    L.secret_room((22, 7), N, 21, 4, 23, 6, A.ASH, SKY, 0.6)
    L.put("rage", 22, 5)
    L.put("cornsack", 21, 4)


# ======================================================================= EPISODE 2: DOWNSTREAM
def e2l1(L):
    L.name, L.par, L.sky = "E2L1: THE RIVER DOCKS", 150, "storm"
    W, C = A.WOOD, A.CONCRETE
    L.room(3, 38, 9, 44, A.WOODF, SKY, 0.9, W)                     # the pier
    L.start = (6.5, 43.5, -np.pi / 2)
    L.puts("crumbs", [(4, 39), (8, 39)])
    L.put("eggs", 4, 43)
    L.door(6, 37, floor=A.WOODF, ceil=SKY, light=0.9)
    L.room(3, 24, 24, 36, A.TILES, SKY, 1.0, A.BRICK)               # dock yard on the river
    L.pool(3, 33, 24, 36)
    L.strip(6, 33, 7, 36, A.WOODF)
    L.strip(3, 33, 24, 33, A.WOODF)
    L.puts("crate", [(10, 26), (11, 26), (10, 27), (20, 29), (21, 29)])
    L.puts("barrel", [(15, 31), (16, 31), (23, 25)])
    L.puts("quackling", [(9, 30), (18, 26), (22, 32)])
    L.put("mallard", 14, 27)
    L.puts("cormorant", [(12, 33), (19, 33)])
    L.put("cormorant", 4, 26, "notEasy")
    L.put("pebbles", 3, 24)
    L.door(25, 30, floor=A.WOODF, ceil=A.BEAMS, light=0.6)
    L.room(26, 24, 40, 36, A.WOODF, A.BEAMS, 0.6, W, flicker=True)  # warehouse
    for x, y in ((29, 27), (29, 33), (35, 27), (35, 33)):
        L.solid(x, y, W)
    L.puts("crate", [(31, 25), (32, 25), (38, 35), (38, 34)])
    L.put("ykey", 39, 25)
    L.put("brute", 33, 30)
    L.put("mallard", 38, 28)
    L.put("pelican", 27, 35)
    L.puts("gosling", [(36, 31), (37, 31), (36, 32)])
    L.put("loaf", 27, 25)
    L.secret_room((41, 30), W, 42, 29, 44, 31, A.WOODF, A.BEAMS, 0.45)
    L.put("downjacket", 43, 30)
    L.put("cornsack", 42, 29)
    L.door(17, 23, A.YDOOR, key="yellow", floor=A.METALF, ceil=A.LIGHTS, light=0.8)
    L.room(10, 12, 24, 22, A.METALF, A.LIGHTS, 0.8, A.METAL)        # harbourmaster's office
    L.solid(13, 15, A.METAL, 2, 1)
    L.solid(20, 15, A.METAL, 2, 1)
    L.put("heron", 17, 14)
    L.puts("mallard", [(11, 20), (23, 20)])
    L.put("quackling", 12, 13)
    L.put("cormorant", 22, 13, "hard")
    L.put("bread", 23, 13)
    L.wall[11, 17] = A.SWOFF
    L.exit_cell = (17, 11)
    L.secret_room((7, 45), W, 6, 46, 8, 46, A.WOODF, SKY, 0.6)
    L.put("rage", 7, 46)


def e2l2(L):
    L.name, L.par, L.sky = "E2L2: CANAL STREET", 200, "storm"
    C = A.CONCRETE
    L.room(20, 38, 28, 44, A.TILES, SKY, 1.0, C)
    L.start = (24.5, 43.5, -np.pi / 2)
    L.put("pebblebox", 21, 39)
    L.door(24, 37, floor=A.TILES, ceil=SKY, light=1.0)
    L.room(4, 26, 44, 36, A.TILES, SKY, 1.0, C)                     # the canal street
    L.pool(4, 30, 44, 32)
    L.strip(12, 30, 13, 32, A.TILES)
    L.strip(34, 30, 35, 32, A.TILES)
    L.strip(23, 30, 25, 32, A.WOODF)
    L.puts("lamp", [(8, 27), (16, 27), (32, 27), (40, 27), (8, 35), (16, 35), (32, 35), (40, 35)])
    L.puts("barrel", [(20, 34), (28, 28)])
    L.puts("cormorant", [(10, 31), (30, 31), (40, 31)])
    L.puts("quackling", [(6, 34), (42, 34), (18, 28)])
    L.put("mallard", 30, 34)
    L.put("pelican", 38, 28, "notEasy")
    L.puts("crumbs", [(12, 31), (34, 31)])
    L.door(11, 25, floor=A.STONEF, ceil=A.LIGHTS, light=0.7)
    L.room(4, 12, 18, 24, A.STONEF, A.LIGHTS, 0.7, A.BRICK)         # bakery building (blue key)
    for x, y in ((8, 16), (14, 16), (8, 20), (14, 20)):
        L.solid(x, y, A.BRICK)
    L.put("bkey", 5, 13)
    L.put("brute", 11, 18)
    L.puts("gosling", [(16, 13), (17, 13), (16, 14), (17, 14)])
    L.put("fireswan", 5, 23)
    L.put("loaf", 17, 23)
    L.door(37, 25, A.BDOOR, key="blue", floor=A.METALF, ceil=A.LIGHTS, light=0.75)
    L.room(30, 12, 44, 24, A.METALF, A.LIGHTS, 0.75, A.METAL)       # pump station (red key)
    L.pool(33, 15, 41, 16)
    L.put("rkey", 43, 13)
    L.puts("mallard", [(31, 22), (43, 22)])
    L.put("heron", 37, 13)
    L.put("cormorant", 32, 13)
    L.put("eggcrate", 31, 18)
    L.door(24, 25, floor=A.STONEF, ceil=A.PIPES, light=0.5)
    L.room(21, 12, 27, 24, A.STONEF, A.PIPES, 0.5, C, flicker=True)  # alley
    L.puts("quackling", [(22, 16), (26, 20)])
    L.put("baguettes", 24, 13)
    L.put("flinger", 24, 18)
    L.door(24, 11, A.RDOOR, key="red", floor=A.TILES, ceil=A.BEAMS, light=0.7)
    L.room(20, 3, 28, 10, A.TILES, A.BEAMS, 0.7, A.CASTLE)          # clock tower (exit)
    L.puts("brute", [(21, 5), (27, 5)])
    L.put("pelican", 24, 4)
    L.put("loaf", 21, 9)
    L.wall[2, 24] = A.SWOFF
    L.exit_cell = (24, 2)
    L.secret_room((3, 31), C, 1, 30, 2, 32, A.TILES, SKY, 0.7)
    L.put("goldegg", 1, 31)
    L.secret_room((45, 18), A.METAL, 46, 16, 46, 20, A.METALF, A.LIGHTS, 0.5)
    L.put("downjacket", 46, 18)


def e2l3(L):
    L.name, L.par, L.sky = "E2L3: THE WATERWORKS", 210, "storm"
    L.room(3, 3, 10, 10, A.METALF, A.LIGHTS, 0.8, A.METAL)
    L.start = (6.5, 6.5, 0.0)
    L.put("pebbles", 4, 9)
    L.door(11, 6, floor=A.METALF, ceil=A.LIGHTS, light=0.7)
    L.room(12, 3, 32, 16, A.METALF, A.LIGHTS, 0.7, A.FACTORY)       # pump hall
    L.pool(15, 6, 18, 13)
    L.pool(26, 6, 29, 13)
    L.puts("barrel", [(21, 4), (22, 4), (31, 15)])
    L.puts("mallard", [(22, 9), (31, 4)])
    L.puts("cormorant", [(14, 15), (24, 15)])
    L.put("pelican", 30, 10)
    L.put("heron", 13, 4, "notEasy")
    L.put("eggs", 23, 12)
    L.put("bazooka", 21, 9)
    L.door(16, 17, floor=A.STONEF, ceil=A.PIPES, light=0.55)
    L.room(3, 18, 22, 30, A.STONEF, A.PIPES, 0.55, A.SEWER)         # filter beds (yellow key)
    L.pool(5, 22, 20, 23)
    L.pool(5, 27, 20, 28)
    L.strip(12, 22, 12, 23, A.STONEF)
    L.strip(12, 27, 12, 28, A.STONEF)
    L.put("ykey", 4, 29)
    L.puts("quackling", [(8, 20), (18, 25), (6, 25)])
    L.put("brute", 15, 29)
    L.puts("gosling", [(10, 25), (11, 25), (14, 25)])
    L.put("loaf", 21, 19)
    L.teleport((20, 15), (21, 19))
    L.door(33, 10, A.YDOOR, key="yellow", floor=A.METALF, ceil=A.LIGHTS, light=0.8)
    L.room(34, 3, 44, 20, A.METALF, A.LIGHTS, 0.8, A.METAL)         # pressure room (blue key)
    for y in (6, 10, 14):
        L.solid(37, y, A.METAL)
        L.solid(41, y, A.METAL)
    L.put("bkey", 43, 19)
    L.puts("heron", [(39, 4), (39, 18)])
    L.put("mallard", 35, 12)
    L.put("brute", 43, 8, "hard")
    L.put("baguettes", 35, 4)
    L.door(39, 21, A.BDOOR, key="blue", floor=A.STONEF, ceil=A.PIPES, light=0.6)
    L.room(24, 22, 44, 32, A.STONEF, A.PIPES, 0.6, A.SEWER)         # outflow (exit)
    L.pool(26, 29, 42, 31)
    L.puts("pelican", [(28, 24), (42, 24)])
    L.puts("cormorant", [(32, 27), (38, 27)])
    L.put("fireswan", 25, 27)
    L.put("bread", 43, 26)
    L.wall[33, 34] = A.SWOFF
    L.exit_cell = (34, 33)
    L.secret_room((6, 2), A.METAL, 5, 1, 7, 1, A.METALF, A.LIGHTS, 0.5)
    L.put("pebblebox", 5, 1)
    L.put("cornsack", 7, 1)
    L.secret_room((28, 33), A.SEWER, 27, 34, 29, 36, A.STONEF, A.PIPES, 0.4)
    L.put("rage", 28, 35)


def e2l4(L):
    L.name, L.par, L.sky = "E2L4: MUDFLAT MARSH", 220, "storm"
    R = A.REEDS
    L.room(20, 40, 26, 45, A.WOODF, A.BEAMS, 0.7, A.WOOD)           # fisher's shack
    L.start = (23.5, 44.5, -np.pi / 2)
    L.put("eggcrate", 21, 41)
    L.door(23, 39, floor=A.MUD, ceil=SKY, light=0.9)
    L.room(4, 20, 42, 38, A.MUD, SKY, 0.9, R)                       # the marsh
    L.pool(8, 24, 16, 30)
    L.pool(26, 22, 36, 28)
    L.pool(18, 32, 30, 36)
    L.puts("tree", [(6, 22), (20, 25), (40, 21), (38, 35), (5, 36), (22, 29)])
    L.puts("cormorant", [(12, 27), (31, 25), (24, 34), (40, 30)])
    L.puts("heron", [(18, 22), (35, 33)])
    L.puts("pelican", [(6, 32), (41, 24)])
    L.puts("gosling", [(14, 35), (15, 35), (16, 36), (33, 37), (34, 37)])
    L.put("mallard", 23, 21, "notEasy")
    L.puts("crumbs", [(12, 31), (13, 31), (14, 31)])
    L.put("baguettes", 41, 37)
    L.put("megahonk", 23, 24)
    L.door(10, 19, floor=A.WOODF, ceil=A.BEAMS, light=0.6)
    L.room(4, 6, 16, 18, A.WOODF, A.BEAMS, 0.6, A.WOOD, flicker=True)  # hunter's lodge (red key)
    L.puts("crate", [(5, 7), (6, 7), (15, 17)])
    L.put("rkey", 15, 7)
    L.put("brute", 10, 12)
    L.put("mallard", 5, 16)
    L.put("fireswan", 12, 7)
    L.put("loaf", 5, 12)
    L.secret_room((3, 11), A.WOOD, 1, 10, 2, 12, A.WOODF, A.BEAMS, 0.45)
    L.put("goldegg", 1, 11)
    L.door(35, 19, A.RDOOR, key="red", floor=A.WOODF, ceil=A.BEAMS, light=0.65)
    L.room(28, 6, 42, 18, A.WOODF, A.BEAMS, 0.65, A.WOOD)           # boathouse (exit)
    L.pool(36, 8, 41, 13)
    L.strip(38, 8, 38, 13, A.WOODF)
    L.puts("brute", [(30, 8), (31, 16)])
    L.puts("heron", [(41, 16)])
    L.puts("cormorant", [(34, 10), (40, 15)])
    L.put("loaf", 29, 17)
    L.wall[12, 43] = A.SWOFF
    L.exit_cell = (43, 12)
    L.secret_room((6, 39), R, 5, 40, 7, 42, A.MUD, SKY, 0.6)
    L.put("cornsack", 6, 41)
    L.put("rage", 5, 40)


def e2l5(L):
    L.name, L.par, L.sky = "E2L5: THE KING'S LOCK", 200, "storm"
    L.boss_level = True
    C = A.CONCRETE
    L.room(18, 38, 26, 44, A.METALF, A.LIGHTS, 0.8, A.METAL)        # supply room
    L.start = (22.5, 43.5, -np.pi / 2)
    L.puts("cornsack", [(19, 39), (25, 39)])
    L.puts("baguettes", [(19, 43), (25, 43)])
    L.put("eggcrate", 22, 41)
    L.puts("loaf", [(20, 40), (24, 40)])
    L.put("downjacket", 22, 39)
    L.door(22, 37, floor=A.TILES, ceil=SKY, light=1.0)
    L.room(6, 8, 38, 36, A.TILES, SKY, 1.0, C)                      # the lock
    L.pool(6, 20, 38, 24)
    for x in (12, 22, 31):
        L.strip(x, 20, x + 1, 24, A.WOODF)
    for x0, y0 in ((14, 12), (29, 12), (14, 29), (29, 29)):
        L.solid(x0, y0, C, 2, 2)
    L.puts("barrel", [(18, 17), (26, 17), (18, 27), (26, 27)])
    L.put("mallardking", 22, 13)
    L.puts("mallard", [(9, 11), (35, 11)], "notEasy")
    L.puts("cormorant", [(9, 33), (35, 33)], "hard")
    L.door(5, 28, floor=A.METALF, ceil=A.LIGHTS, light=0.7)
    L.room(2, 26, 4, 30, A.METALF, A.LIGHTS, 0.7, A.METAL)
    L.puts("loaf", [(2, 26), (2, 30)])
    L.put("corn", 3, 28)
    L.door(39, 28, floor=A.METALF, ceil=A.LIGHTS, light=0.7)
    L.room(40, 26, 42, 30, A.METALF, A.LIGHTS, 0.7, A.METAL)
    L.put("baguettes", 41, 27)
    L.put("pebblebox", 41, 29)
    L.secret_room((22, 7), C, 21, 4, 23, 6, A.TILES, SKY, 0.6)
    L.put("goldegg", 22, 5)


# ======================================================================= EPISODE 3: THE ROOST OF ASH
def e3l1(L):
    L.name, L.par, L.sky = "E3L1: OBSIDIAN STAIR", 210, "void"
    O = A.OBSIDIAN
    L.room(3, 40, 10, 45, A.ASH, SKY, 1.0, O)
    L.start = (6.5, 44.5, -np.pi / 2)
    L.put("cornsack", 9, 44)
    L.door(6, 39, floor=A.ASH, ceil=SKY, light=1.0)
    L.room(3, 30, 20, 38, A.ASH, SKY, 1.0, O)                       # first landing: lava pit
    L.lava(8, 31, 15, 37)
    L.strip(8, 34, 15, 34, A.ASH)
    L.puts("owl", [(18, 31), (4, 31)])
    L.puts("fireswan", [(17, 36), (11, 34)])
    L.put("pebbles", 19, 37)
    L.door(21, 34, floor=A.MARBLE, ceil=SKY, light=1.0)
    L.room(22, 30, 40, 38, A.MARBLE, SKY, 1.0, O)                   # marble landing (yellow key)
    L.puts("candle", [(24, 31), (24, 37), (38, 37)])
    L.put("ykey", 39, 31)
    L.puts("heron", [(30, 33), (37, 36)])
    L.put("owl", 34, 31)
    L.puts("gosling", [(27, 36), (28, 36), (29, 36)])
    L.put("loaf", 23, 35)
    L.secret_room((41, 34), O, 42, 33, 44, 35, A.MARBLE, SKY, 0.6)
    L.put("goldegg", 43, 34)
    L.door(31, 29, A.YDOOR, key="yellow", floor=A.ASH, ceil=SKY, light=1.0)
    L.room(22, 18, 40, 28, A.ASH, SKY, 1.0, O)                      # ember walk (blue key)
    L.lava(25, 20, 30, 26)
    L.lava(33, 20, 38, 26)
    L.strip(25, 23, 38, 23, A.ASH)
    L.put("bkey", 23, 19)
    L.puts("owl", [(39, 19), (39, 27)])
    L.put("brute", 31, 19)
    L.put("pelican", 31, 27)
    L.put("baguettes", 23, 27)
    L.door(21, 23, A.BDOOR, key="blue", floor=A.MARBLE, ceil=A.BEAMS, light=0.7)
    L.room(3, 18, 20, 28, A.MARBLE, A.BEAMS, 0.7, A.GOLD)           # gilded hall
    for x in (6, 10, 14, 18):
        L.solid(x, 20, A.GOLD)
        L.solid(x, 26, A.GOLD)
    L.puts("mallard", [(4, 23), (19, 23)])
    L.put("owl", 12, 23)
    L.put("loaf", 4, 19)
    L.door(12, 17, floor=A.ASH, ceil=SKY, light=1.0)
    L.room(8, 4, 30, 16, A.ASH, SKY, 1.0, O)                        # the summit (exit)
    L.lava(8, 4, 30, 5)
    L.puts("owl", [(10, 8), (28, 8), (19, 12)])
    L.puts("brute", [(14, 14), (24, 14)])
    L.put("heron", 19, 7)
    L.put("cormorant", 29, 15, "hard")
    L.wall[3, 19] = A.SWOFF
    L.strip(19, 4, 19, 5, A.ASH)
    L.exit_cell = (19, 3)
    L.secret_room((26, 3), O, 25, 1, 27, 2, A.ASH, SKY, 0.6)
    L.put("cornsack", 26, 1)
    L.put("rage", 25, 2)


def e3l2(L):
    L.name, L.par, L.sky = "E3L2: THE FEATHER VAULT", 220, "void"
    G = A.GOLD
    L.room(20, 40, 26, 45, A.MARBLE, A.LIGHTS, 0.8, G)
    L.start = (23.5, 44.5, -np.pi / 2)
    L.put("pebblebox", 21, 41)
    L.door(23, 39, floor=A.MARBLE, ceil=A.BEAMS, light=0.75)
    L.room(14, 20, 32, 38, A.MARBLE, A.BEAMS, 0.75, G)              # the nave
    for y in (23, 27, 31, 35):
        L.solid(17, y, G)
        L.solid(29, y, G)
    L.puts("candle", [(15, 21), (31, 21), (15, 37), (31, 37)])
    L.puts("owl", [(23, 24), (16, 30), (30, 30)])
    L.puts("mallard", [(20, 36), (26, 36)])
    L.puts("gosling", [(22, 28), (23, 28), (24, 28), (23, 29)])
    L.put("crumbs", 23, 33)
    L.put("flinger", 23, 31)
    L.door(13, 28, floor=A.MARBLE, ceil=A.LIGHTS, light=0.6)
    L.room(2, 22, 12, 34, A.MARBLE, A.LIGHTS, 0.6, A.CASTLE)        # west chapel (yellow key)
    L.put("ykey", 3, 23)
    L.put("brute", 7, 28)
    L.put("heron", 11, 33)
    L.put("loaf", 3, 33)
    L.secret_room((7, 35), A.CASTLE, 6, 36, 8, 38, A.MARBLE, A.LIGHTS, 0.45)
    L.put("downjacket", 7, 37)
    L.door(33, 28, A.YDOOR, key="yellow", floor=A.MARBLE, ceil=A.LIGHTS, light=0.6)
    L.room(34, 22, 44, 34, A.MARBLE, A.LIGHTS, 0.6, A.CASTLE)       # east chapel (red key)
    L.put("rkey", 43, 33)
    L.puts("owl", [(43, 23), (36, 33)])
    L.put("pelican", 39, 28)
    L.put("fireswan", 35, 23)
    L.put("eggcrate", 43, 28)
    L.teleport((44, 23), (31, 37))
    L.door(23, 19, A.RDOOR, key="red", floor=A.MARBLE, ceil=A.LIGHTS, light=0.9)
    L.room(14, 4, 32, 18, A.MARBLE, A.LIGHTS, 0.9, G)               # the vault (exit)
    L.puts("eggpile", [(16, 6), (30, 6), (16, 16), (30, 16)])
    L.puts("brute", [(18, 10), (28, 10)])
    L.puts("owl", [(23, 6), (15, 12), (31, 12)])
    L.put("heron", 23, 14)
    L.put("mallard", 20, 16, "hard")
    L.wall[3, 23] = A.SWOFF
    L.exit_cell = (23, 3)
    L.secret_room((33, 10), G, 34, 8, 36, 12, A.MARBLE, A.LIGHTS, 0.6)
    L.put("goldegg", 35, 10)
    L.put("cornsack", 36, 8)


def e3l3(L):
    L.name, L.par, L.sky = "E3L3: OWLWOOD", 220, "night"
    H = A.HEDGE
    L.room(3, 3, 9, 9, A.GRASS, SKY, 0.8, H)
    L.start = (6.5, 6.5, np.pi / 2)
    L.put("eggs", 4, 4)
    L.door(6, 10, floor=A.GRASS, ceil=SKY, light=0.8)
    L.room(3, 11, 24, 30, A.GRASS, SKY, 0.8, H)                     # the wood
    L.puts("tree", [(6, 14), (12, 13), (19, 16), (8, 21), (15, 24), (21, 27), (5, 28), (11, 18)])
    L.puts("owl", [(10, 15), (20, 22), (6, 25)])
    L.puts("cormorant", [(16, 12), (14, 29)])
    L.put("fireswan", 22, 13)
    L.puts("gosling", [(17, 20), (18, 20), (17, 21)])
    L.put("pebbles", 23, 29)
    L.door(25, 20, floor=A.GRASS, ceil=SKY, light=0.9)
    L.room(26, 11, 44, 30, A.GRASS, SKY, 0.9, H)                    # moonlit clearing (blue key)
    L.puts("candle", [(33, 18), (37, 18), (33, 23), (37, 23)])
    L.put("bkey", 35, 20)
    L.puts("owl", [(30, 14), (40, 14), (30, 27), (40, 27)])
    L.put("heron", 43, 20)
    L.put("brute", 27, 29, "notEasy")
    L.put("loaf", 44, 29)
    L.put("bazooka", 35, 25)
    L.teleport((8, 8), (43, 12))
    L.secret_room((18, 10), H, 17, 6, 19, 9, A.GRASS, SKY, 0.6)
    L.put("rage", 18, 7)
    L.put("cornsack", 17, 6)
    L.door(13, 31, A.BDOOR, key="blue", floor=A.TILES, ceil=A.BEAMS, light=0.55)
    L.room(3, 32, 24, 44, A.TILES, A.BEAMS, 0.55, A.CASTLE, flicker=True)  # ruined abbey (yellow key)
    for x, y in ((7, 35), (12, 35), (17, 35), (7, 41), (12, 41), (17, 41)):
        L.solid(x, y, A.CASTLE)
    L.put("ykey", 4, 43)
    L.puts("brute", [(10, 38), (20, 38)])
    L.puts("owl", [(4, 33), (23, 43)])
    L.put("pelican", 15, 43)
    L.put("baguettes", 23, 33)
    L.secret_room((2, 38), A.CASTLE, 1, 36, 1, 40, A.TILES, A.BEAMS, 0.45)
    L.put("goldegg", 1, 38)
    L.door(35, 31, A.YDOOR, key="yellow", floor=A.TILES, ceil=A.LIGHTS, light=0.7)
    L.room(26, 32, 44, 44, A.TILES, A.LIGHTS, 0.7, A.CASTLE)        # owl tower (exit)
    L.solid(33, 37, A.CASTLE, 4, 3)
    L.puts("owl", [(28, 34), (43, 34), (28, 43), (43, 43)])
    L.puts("heron", [(35, 42)])
    L.put("mallard", 31, 38)
    L.put("loaf", 40, 38)
    L.wall[38, 45] = A.SWOFF
    L.exit_cell = (45, 38)


def e3l4(L):
    L.name, L.par, L.sky = "E3L4: THE HATCHING DARK", 240, "void"
    N, O = A.NEST, A.OBSIDIAN
    L.room(21, 39, 27, 45, A.ASH, SKY, 0.7, N)
    L.start = (24.5, 44.5, -np.pi / 2)
    L.put("cornsack", 22, 41)
    L.door(24, 38, floor=A.ASH, ceil=SKY, light=0.8)
    L.room(5, 8, 43, 37, A.ASH, SKY, 0.8, N)                        # the ring of nests
    L.solid(14, 15, O, 21, 14)                                      # the central hatchery block
    for x0, y0 in ((6, 9), (39, 9), (6, 33), (39, 33)):
        L.lava(x0, y0, x0 + 3, y0 + 3)
    L.puts("eggpile", [(10, 20), (38, 20), (24, 11), (24, 34)])
    L.puts("owl", [(9, 14), (39, 14), (9, 31), (39, 31)])
    L.puts("gosling", [(20, 12), (21, 12), (27, 12), (28, 12), (20, 33), (21, 33), (27, 33), (28, 33)])
    L.puts("pelican", [(12, 24), (36, 24)])
    L.puts("heron", [(24, 31)])
    L.put("brute", 30, 34, "notEasy")
    L.puts("crumbs", [(15, 35), (33, 35)])
    L.put("megahonk", 12, 30)
    L.door(4, 22, floor=A.ASH, ceil=A.LIGHTS, light=0.6)
    L.room(1, 18, 3, 26, A.ASH, A.LIGHTS, 0.6, N)                   # west vault (yellow key)
    L.put("ykey", 1, 22)
    L.put("brute", 2, 25)
    L.door(44, 22, A.YDOOR, key="yellow", floor=A.ASH, ceil=A.LIGHTS, light=0.6)
    L.room(45, 18, 46, 26, A.ASH, A.LIGHTS, 0.6, N)                 # east vault (red key)
    L.put("rkey", 46, 25)
    L.put("owl", 45, 19)
    L.room(24, 15, 24, 15, A.ASH, A.BEAMS, 0.5, O)
    L.door(24, 16, A.RDOOR, key="red", floor=A.ASH, ceil=A.BEAMS, light=0.5)
    L.room(16, 17, 32, 27, A.ASH, A.BEAMS, 0.5, O, flicker=True)    # the hatchery (exit)
    L.puts("eggpile", [(18, 19), (30, 19), (18, 25), (30, 25)])
    L.puts("owl", [(17, 22), (31, 22)])
    L.puts("brute", [(20, 26), (28, 26)])
    L.put("heron", 24, 20)
    L.put("loaf", 24, 26)
    L.wall[16, 28] = A.SWOFF
    L.exit_cell = (28, 16)
    L.secret_room((20, 42), N, 17, 41, 19, 43, A.ASH, SKY, 0.5)
    L.put("downjacket", 18, 42)
    L.secret_room((24, 7), N, 23, 4, 25, 6, A.ASH, SKY, 0.6)
    L.put("cornsack", 23, 4)
    L.put("rage", 25, 5)


def e3l5(L):
    L.name, L.par, L.sky = "E3L5: THE FIRST NEST", 240, "void"
    L.boss_level = True
    O, N = A.OBSIDIAN, A.NEST
    L.room(18, 38, 26, 44, A.ASH, SKY, 0.8, O)                      # last stand supplies
    L.start = (22.5, 43.5, -np.pi / 2)
    L.puts("cornsack", [(19, 39), (25, 39), (22, 43)])
    L.puts("baguettes", [(19, 43), (25, 43)])
    L.put("eggcrate", 22, 41)
    L.puts("loaf", [(20, 40), (24, 40)])
    L.put("downjacket", 22, 39)
    L.door(22, 37, floor=A.ASH, ceil=SKY, light=1.0)
    L.room(5, 6, 39, 36, A.ASH, SKY, 1.0, N)                        # the first nest
    L.lava(6, 7, 38, 35)
    L.strip(11, 12, 33, 30, A.ASH)                                  # the platform
    L.strip(21, 7, 23, 11, A.ASH)                                   # four bridges
    L.strip(21, 31, 23, 35, A.ASH)
    L.strip(6, 20, 10, 22, A.ASH)
    L.strip(34, 20, 38, 22, A.ASH)
    for x0, y0 in ((15, 16), (28, 16), (15, 26), (28, 26)):
        L.solid(x0, y0, O)
    L.puts("eggpile", [(13, 14), (31, 14), (13, 28), (31, 28)])
    L.put("greatgander", 22, 15)
    L.puts("owl", [(12, 21), (32, 21)], "notEasy")
    L.puts("owl", [(22, 29)], "hard")
    L.door(4, 21, floor=A.ASH, ceil=A.BEAMS, light=0.7)
    L.room(1, 19, 3, 23, A.ASH, A.BEAMS, 0.7, O)
    L.puts("loaf", [(1, 19), (1, 23)])
    L.put("cornsack", 2, 21)
    L.door(40, 21, floor=A.ASH, ceil=A.BEAMS, light=0.7)
    L.room(41, 19, 43, 23, A.ASH, A.BEAMS, 0.7, O)
    L.put("goldegg", 42, 21)
    L.put("baguettes", 43, 19)
    L.secret_room((22, 5), N, 21, 2, 23, 4, A.ASH, SKY, 0.6)
    L.put("goldegg", 22, 3)
    L.put("rage", 21, 2)


BUILDERS = [e1l1, e1l2, e1l3, e1l4, e1l5, e1l6,
            e2l1, e2l2, e2l3, e2l4, e2l5,
            e3l1, e3l2, e3l3, e3l4, e3l5]
NUM_LEVELS = len(BUILDERS)
# (title, first level index, last level index) - the last level of each episode is its boss fight
EPISODES = [("FOWL WATERS", 0, 5), ("DOWNSTREAM", 6, 10), ("THE ROOST OF ASH", 11, 15)]


def episode_of(idx):
    for n, (_, a, b) in enumerate(EPISODES):
        if a <= idx <= b:
            return n
    return 0
