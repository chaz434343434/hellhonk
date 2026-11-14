"""HELLHONK Episode 1: FOWL WATERS - six original levels.

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
        BUILDERS[index](self)
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


BUILDERS = [e1l1, e1l2, e1l3, e1l4, e1l5, e1l6]
NUM_LEVELS = len(BUILDERS)
