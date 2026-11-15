"""Synthesised sound effects and an original honk-metal loop for HELLHONK."""
import numpy as np
import pygame

SR = 22050
rng = np.random.default_rng(99)


def t_(dur):
    return np.arange(int(SR * dur)) / SR


def env(n, a=0.005, r=0.05, curve=1.0):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if nr < n:
        e[-nr:] *= np.linspace(1, 0, nr) ** curve
    return e


def fft_filter(x, lo=0, hi=SR / 2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi < SR / 2:
        g *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * g, len(x))


def formant(f):
    return (np.exp(-((f - 1050) / 380) ** 2) + 0.6 * np.exp(-((f - 2500) / 600) ** 2)
            + 0.25 * np.exp(-((f - 450) / 200) ** 2) + 0.05)


def honk(f0, dur, glide=2.0, vib=6.0, buzz=0.0, bright=1.0):
    """Goose honk: nasal additive tone that sags in pitch at the end."""
    t = t_(dur)
    sag = 2 ** (-glide * (t / dur) ** 2 / 12)
    f = f0 * sag * (1 + 0.012 * np.sin(2 * np.pi * vib * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    out = np.zeros_like(t)
    for k in range(1, 24):
        if f0 * k > SR / 2 - 500:
            break
        out += formant(f0 * k * bright) * np.sin(k * ph) / k ** 0.35
    out /= np.max(np.abs(out)) + 1e-9
    if buzz:
        out += buzz * np.sign(np.sin(ph)) * 0.3
    out += rng.normal(0, 0.04, len(t))
    return np.tanh(out * 1.6) * env(len(t), 0.012, min(0.06, dur / 3))


def noise_burst(dur, lo=0, hi=SR / 2, decay=8.0):
    t = t_(dur)
    return fft_filter(rng.normal(0, 1, len(t)), lo, hi) * np.exp(-t * decay)


def sweep(f1, f2, dur, decay=10):
    t = t_(dur)
    f = f1 * (f2 / f1) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay)


def norm(x, peak=0.9):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def to_sound(x, vol=1.0):
    a = (np.clip(x * vol, -1, 1) * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([a, a])))


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def build_sfx():
    s = {}
    s["honker"] = norm(mix(honk(520, 0.2, glide=4, bright=1.1), noise_burst(0.05, 2000) * 0.5))
    s["egggun"] = norm(mix(noise_burst(0.5, 60, 2500, 7) * 1.2, sweep(140, 40, 0.35, 9),
                           honk(300, 0.25, glide=5) * 0.5))
    s["pump"] = norm(mix(noise_burst(0.04, 1500, 6000, 60), np.pad(noise_burst(0.05, 800, 4000, 50), (int(SR * 0.12), 0))) * 0.5)
    s["peck"] = norm(noise_burst(0.08, 400, 3000, 40) * 0.6)
    s["punch"] = norm(mix(sweep(200, 60, 0.12, 25), noise_burst(0.06, 200, 2000, 40)) * 0.8)
    s["quack"] = norm(honk(330, 0.17, glide=3, buzz=0.9, bright=1.3))
    s["quack_sight"] = norm(mix(honk(340, 0.14, glide=2, buzz=0.9, bright=1.3),
                                np.pad(honk(300, 0.2, glide=4, buzz=0.9, bright=1.3), (int(SR * 0.17), 0))))
    s["quackshot"] = norm(mix(honk(300, 0.12, glide=6, buzz=1.0), noise_burst(0.1, 500, 4000, 25)))
    s["hiss"] = norm(noise_burst(0.5, 2500, 8000, 3) * env(int(SR * 0.5), 0.08, 0.2))
    s["swan_sight"] = norm(mix(noise_burst(0.6, 2000, 7000, 2), honk(220, 0.5, glide=6, buzz=0.4) * 0.6))
    s["fireball"] = norm(mix(noise_burst(0.45, 200, 1500, 4), sweep(90, 300, 0.4, 3) * 0.4))
    s["boom"] = norm(mix(noise_burst(1.0, 30, 1200, 4), sweep(90, 30, 0.6, 5)))
    s["growl"] = norm(honk(115, 0.6, glide=3, buzz=0.6, bright=0.8) * (0.7 + 0.3 * np.sin(2 * np.pi * 28 * t_(0.6))))
    s["bite"] = norm(mix(noise_burst(0.12, 300, 3000, 30), sweep(400, 80, 0.15, 20)))
    s["pain_q"] = norm(honk(480, 0.2, glide=7, buzz=1.0, bright=1.4))
    s["pain_s"] = norm(mix(honk(380, 0.25, glide=8, buzz=0.5), noise_burst(0.25, 3000, 8000, 8) * 0.5))
    s["pain_b"] = norm(honk(160, 0.35, glide=6, buzz=0.7))
    s["die_q"] = norm(honk(420, 0.55, glide=14, buzz=0.9, bright=1.3))
    s["die_s"] = norm(mix(honk(330, 0.8, glide=16, buzz=0.5), noise_burst(0.8, 2500, 7000, 4) * 0.4))
    s["die_b"] = norm(honk(140, 0.9, glide=12, buzz=0.8, bright=0.8))
    s["oof"] = norm(honk(230, 0.18, glide=3) * 0.8)
    s["player_pain"] = norm(honk(420, 0.28, glide=6, bright=1.0))
    s["player_die"] = norm(honk(500, 1.3, glide=24, vib=9))
    s["door"] = norm(fft_filter(rng.normal(0, 1, int(SR * 0.7)), 40, 400) * env(int(SR * 0.7), 0.05, 0.2)
                     + sweep(60, 70, 0.7, 1) * 0.3)
    s["doorshut"] = norm(mix(s["door"][: int(SR * 0.5)] * 0.6, np.pad(noise_burst(0.15, 40, 800, 20), (int(SR * 0.45), 0))))
    s["switch"] = norm(mix(noise_burst(0.05, 500, 5000, 50), sweep(900, 600, 0.08, 30)))
    s["item"] = norm(mix(sweep(880, 880, 0.07, 20), np.pad(sweep(1320, 1320, 0.09, 20), (int(SR * 0.06), 0))) * 0.6)
    s["weapon"] = norm(mix(*[np.pad(honk(f, 0.12, glide=1), (int(SR * 0.09 * i), 0)) for i, f in enumerate((392, 494, 587, 784))]))
    s["key"] = norm(mix(*[np.pad(sweep(f, f, 0.25, 6), (int(SR * 0.08 * i), 0)) for i, f in enumerate((1047, 1319, 1568))]) * 0.6)
    s["secret"] = norm(mix(*[np.pad(honk(f, 0.18, glide=0.5), (int(SR * 0.15 * i), 0)) for i, f in enumerate((294, 370, 440, 587))]))
    s["noammo"] = norm(noise_burst(0.03, 1000, 5000, 80) * 0.4)
    s["sludge"] = norm(mix(noise_burst(0.2, 100, 900, 10), honk(260, 0.1, glide=3) * 0.4))
    # episode additions
    s["flinger"] = norm(mix(honk(620, 0.07, glide=3, bright=1.2), noise_burst(0.04, 2500, 9000, 50) * 0.5))
    s["rocket"] = norm(mix(noise_burst(0.6, 100, 2500, 4), sweep(70, 160, 0.4, 4) * 0.5))
    s["megahonk"] = norm(mix(sweep(120, 900, 0.6, 1.5) * 0.6, np.pad(honk(150, 0.9, glide=8, buzz=0.6, bright=0.7), (int(SR * 0.45), 0)),
                             np.pad(noise_burst(0.9, 40, 3000, 3), (int(SR * 0.45), 0))))
    s["megaboom"] = norm(mix(noise_burst(1.6, 20, 2000, 2.2), sweep(80, 25, 1.2, 2.5), honk(200, 1.0, glide=12) * 0.4))
    s["mallard_sight"] = norm(mix(honk(260, 0.16, glide=2, buzz=0.9), np.pad(honk(240, 0.16, glide=2, buzz=0.9), (int(SR * 0.18), 0)),
                                  np.pad(honk(210, 0.3, glide=5, buzz=0.9), (int(SR * 0.36), 0))))
    s["mallard_shot"] = norm(mix(noise_burst(0.07, 600, 6000, 40), sweep(500, 200, 0.06, 30) * 0.5))
    s["pelican_sight"] = norm(honk(140, 0.6, glide=-3, buzz=0.3, bright=0.6))
    s["pelican_atk"] = norm(mix(sweep(300, 120, 0.25, 6) * 0.6, noise_burst(0.2, 200, 1500, 10)))
    s["peep"] = norm(honk(1100, 0.08, glide=-2, bright=1.6) * 0.7)
    s["gosling_die"] = norm(honk(1000, 0.25, glide=10, bright=1.6) * 0.7)
    s["heron_sight"] = norm(mix(noise_burst(0.5, 3000, 9000, 4), sweep(1400, 600, 0.5, 2) * 0.5))
    s["heron_atk"] = norm(mix(sweep(600, 2400, 0.3, 4) * 0.6, noise_burst(0.3, 4000, 9000, 8) * 0.4))
    s["boss_sight"] = norm(mix(honk(90, 1.6, glide=4, buzz=0.8, bright=0.6), honk(180, 1.6, glide=4, bright=0.8) * 0.5,
                               noise_burst(1.6, 30, 400, 1.5) * 0.6))
    s["boss_pain"] = norm(honk(130, 0.5, glide=9, buzz=0.7, bright=0.7))
    s["boss_die"] = norm(mix(honk(160, 2.8, glide=30, buzz=0.6, bright=0.8, vib=3), noise_burst(2.8, 20, 1500, 1.2)))
    s["stomp"] = norm(mix(sweep(90, 30, 0.4, 7), noise_burst(0.3, 20, 500, 10)))
    s["teleport"] = norm(mix(sweep(200, 1600, 0.5, 3) * 0.5, noise_burst(0.5, 1500, 8000, 5) * 0.5))
    s["powerup"] = norm(mix(*[np.pad(honk(f, 0.16, glide=0.3), (int(SR * 0.08 * i), 0)) for i, f in
                              enumerate((392, 523, 659, 784, 1047))]))
    # episodes 2 and 3
    s["corm_sight"] = norm(mix(honk(200, 0.35, glide=-4, buzz=0.8, bright=0.7), noise_burst(0.35, 1500, 6000, 6) * 0.3))
    s["corm_spit"] = norm(mix(noise_burst(0.12, 800, 5000, 25), sweep(700, 300, 0.1, 20) * 0.5))
    s["hoot"] = norm(mix(*[np.pad(sweep(f, f * 0.92, 0.22, 5), (int(SR * 0.26 * i), 0)) for i, f in enumerate((420, 380))]))
    s["king_sight"] = norm(mix(honk(110, 1.4, glide=3, buzz=0.9, bright=0.7), honk(165, 1.4, glide=3, buzz=0.5) * 0.6,
                               noise_burst(1.4, 30, 500, 1.6) * 0.5))
    s["gander_sight"] = norm(mix(honk(70, 2.0, glide=5, buzz=0.6, bright=0.5), sweep(900, 200, 2.0, 1.2) * 0.4,
                                 noise_burst(2.0, 20, 300, 1.0) * 0.6))
    return s


# ------------------------------------------------------------------ generated songs
MODES = {"minor": [0, 2, 3, 5, 7, 8, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
         "dorian": [0, 2, 3, 5, 7, 9, 10], "harm": [0, 1, 4, 5, 7, 8, 10]}
RHYTHMS = {
    "chug": ["x.xxn-x.xxn-x.nn", "x.xxn-x.x.n-xxn.", "xx.xn-xx.xn-n-n."],
    "gallop": ["xxx.xxx.xxn-xxn-", "xxx.xxn-xxx.n-n-", "xxx.xxx.n-n-xxx."],
    "doom": ["n-----x.n---x.x.", "n---x.x.n-----n-", "n-------x.x.n---"],
}


def build_song(seed, bpm, root, mode, feel, lead_density=0.7):
    """Original procedural metal song: riff A/B, transposed section, breakdown, honk lead."""
    r = np.random.default_rng(seed)
    sc = MODES[mode]
    step = 60 / bpm / 4
    bars = 16
    n = int(SR * step * 16 * bars) + SR
    gtr, bas, drm, lead = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)

    def make_riff():
        tpl = RHYTHMS[feel][r.integers(0, len(RHYTHMS[feel]))]
        pool = [d for d in sc[1:] if d != 0] + [12]
        riff = []
        for ch in tpl:
            if ch == "x":
                riff.append("x")
            elif ch == "n":
                riff.append(int(pool[r.integers(0, len(pool))]))
            else:
                riff.append(ch)
        return riff

    ra, rb = make_riff(), make_riff()
    prog = [0, sc[5] - 12, sc[3] - 12 if sc[3] > 4 else sc[3], sc[4] - 12]
    hold = lambda t: [t] + ["-"] * 15
    plan = [(ra, 0, "intro"), (ra, 0, "intro"), (ra, 0, "full"), (rb, 0, "full"),
            (ra, sc[3], "full"), (ra, sc[2], "full"), (ra, 0, "full"), (rb, 0, "full"),
            (hold(0), prog[1], "half"), (hold(0), prog[2], "half"), (hold(0), prog[3], "half"), (hold(0), 0, "half"),
            (ra, 0, "full"), (rb, 0, "full"), (ra, 0, "full"), (rb, 0, "fill")]
    k, sn, hh = kick(), snare(), hat()

    def add(buf, x, i):
        a = int(i * step * SR)
        b = min(n, a + len(x))
        buf[a:b] += x[: b - a]

    for bi, (riff, tr, dr) in enumerate(plan):
        base = bi * 16
        for i, tok in enumerate(riff):
            if tok in ("-", "."):
                continue
            j = i + 1
            while j < 16 and riff[j] == "-":
                j += 1
            dur = (j - i) * step + 0.02
            m = root + tr + (0 if tok == "x" else tok)
            add(gtr, guitar(m, dur, tok == "x"), base + i)
            add(bas, bass(m, dur), base + i)
        for i in range(16):
            if dr == "intro":
                if i in (0, 8):
                    add(drm, k, base + i)
                if i % 4 == 0:
                    add(drm, hh, base + i)
            elif dr == "half" or feel == "doom":
                if i in (0, 10):
                    add(drm, k, base + i)
                if i == 8:
                    add(drm, sn, base + i)
                if i % 2 == 0:
                    add(drm, hh, base + i)
            else:
                kicks = (0, 2, 4, 6, 8, 10, 12, 14) if feel == "gallop" else (0, 3, 6, 10)
                if i in kicks or (dr == "fill" and i >= 12):
                    add(drm, k, base + i)
                if i in (4, 12) or (dr == "fill" and i in (13, 14, 15)):
                    add(drm, sn, base + i)
                if i % 2 == 0:
                    add(drm, hh, base + i)

    # honk lead: random walk over the mode, two octaves up, resolving to the root
    deg = 7
    for bar in list(range(4, 8)) + list(range(8, 12)):
        pos = 0
        slow = bar >= 8
        while pos < 16:
            ln = int(r.choice([4, 4, 8] if slow else [2, 2, 4, 4]))
            ln = min(ln, 16 - pos)
            if r.random() < lead_density:
                deg = int(np.clip(deg + r.choice([-2, -1, -1, 1, 1, 2, 3, -3]), 0, 13))
                if bar in (7, 11) and pos + ln >= 16:
                    deg = 7
                m = root + 24 + sc[deg % 7] + 12 * (deg // 7) - 12
                add(lead, honk(midi(m), ln * step * 0.95, glide=1.2, vib=5.5) * 0.9, bar * 16 + pos)
            pos += ln

    gtr = fft_filter(gtr, 70, 3200)
    out = 0.55 * gtr + 0.5 * bas + 0.75 * drm + 0.42 * lead
    loop = int(SR * step * 16 * bars)
    out[:n - loop] += out[loop:]
    return norm(out[:loop], 0.85)


SONGS = [
    None,                                                     # L1: the hand-written loop
    dict(seed=11, bpm=112, root=45, mode="phrygian", feel="doom", lead_density=0.5),   # sewers
    dict(seed=12, bpm=160, root=47, mode="minor", feel="gallop"),                      # factory
    dict(seed=13, bpm=132, root=50, mode="dorian", feel="chug"),                       # frozen
    dict(seed=14, bpm=144, root=46, mode="harm", feel="chug"),                         # nesting
    dict(seed=15, bpm=178, root=45, mode="phrygian", feel="gallop", lead_density=0.85),  # boss
    # episode 2: DOWNSTREAM
    dict(seed=21, bpm=138, root=48, mode="minor", feel="chug"),                        # river docks
    dict(seed=22, bpm=150, root=50, mode="dorian", feel="gallop"),                     # canal street
    dict(seed=23, bpm=118, root=45, mode="phrygian", feel="doom", lead_density=0.55),  # waterworks
    dict(seed=24, bpm=126, root=47, mode="dorian", feel="doom", lead_density=0.6),     # mudflat marsh
    dict(seed=25, bpm=172, root=48, mode="harm", feel="gallop", lead_density=0.85),    # mallard king
    # episode 3: THE ROOST OF ASH
    dict(seed=31, bpm=146, root=46, mode="harm", feel="chug"),                         # obsidian stair
    dict(seed=32, bpm=134, root=49, mode="minor", feel="chug", lead_density=0.8),      # feather vault
    dict(seed=33, bpm=112, root=44, mode="phrygian", feel="doom", lead_density=0.5),   # owlwood
    dict(seed=34, bpm=158, root=45, mode="harm", feel="gallop"),                       # hatching dark
    dict(seed=35, bpm=184, root=43, mode="phrygian", feel="gallop", lead_density=0.9), # great gander
]


def song_samples(i):
    spec = SONGS[i % len(SONGS)]
    return build_music() if spec is None else build_song(**spec)


# ------------------------------------------------------------------ music
def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def guitar(m, dur, mute):
    t = t_(dur)
    f = midi(m)
    ph = 2 * np.pi * f * t
    saw = lambda p: 2 * ((p / (2 * np.pi)) % 1) - 1
    x = saw(ph) + 0.8 * saw(ph * 1.4983) + 0.5 * saw(ph * 2.003)
    x = np.tanh(x * 3.5)
    e = np.exp(-t * (22 if mute else 1.2)) * env(len(t), 0.003, 0.03)
    return x * e


def bass(m, dur):
    t = t_(dur)
    p = (midi(m - 12) * t) % 1
    return (2 * p - 1) * np.exp(-t * 3) * env(len(t), 0.003, 0.03)


def kick():
    return sweep(130, 42, 0.25, 14) * 1.3


def snare():
    return mix(noise_burst(0.18, 1200, 9000, 18) * 0.8, sweep(190, 170, 0.1, 30) * 0.6)


def hat():
    return noise_burst(0.05, 6000, SR / 2 - 1, 60) * 0.35


def build_music():
    """Original 16-bar loop in D minor, 150 BPM. Riff + honk lead."""
    bpm = 150
    step = 60 / bpm / 4                    # 16th note
    bars = 16
    n = int(SR * step * 16 * bars) + SR
    gtr = np.zeros(n)
    bas = np.zeros(n)
    drm = np.zeros(n)
    lead = np.zeros(n)
    D = 50  # D3 root for power chords

    # x = palm-muted root chug, numbers = semitones above root (open, ringing), - hold, . rest
    riff_a = ["x", ".", "x", "x", 3, "-", "x", ".", "x", "x", 5, "-", "x", ".", 6, 5]
    riff_b = ["x", ".", "x", "x", 3, "-", "x", ".", "x", "x", 8, "-", 7, "-", 5, 3]
    hold = lambda r: [r] + ["-"] * 15
    plan = [  # (riff, transpose, drums)
        (riff_a, 0, "intro"), (riff_b, 0, "intro"), (riff_a, 0, "full"), (riff_b, 0, "full"),
        (riff_a, 5, "full"), (riff_a, 3, "full"), (riff_a, 0, "full"), (riff_b, 0, "full"),
        (hold(0), -4, "half"), (hold(0), -2, "half"), (hold(0), -9, "half"), (hold(0), -5, "half"),
        (riff_a, 0, "full"), (riff_b, 0, "full"), (riff_a, 0, "full"), (riff_a, 0, "fill"),
    ]
    k, sn, hh = kick(), snare(), hat()

    def add(buf, x, i):
        a = int(i * step * SR)
        b = min(n, a + len(x))
        buf[a:b] += x[: b - a]

    for bi, (riff, tr, dr) in enumerate(plan):
        base = bi * 16
        for i, tok in enumerate(riff):
            if tok in ("-", "."):
                continue
            # length of this note: until the next non-hold token
            j = i + 1
            while j < 16 and riff[j] == "-":
                j += 1
            dur = (j - i) * step + 0.02
            m = D + tr + (0 if tok == "x" else tok)
            add(gtr, guitar(m, dur, tok == "x"), base + i)
            add(bas, bass(m, dur), base + i)
        for i in range(16):
            if dr == "intro":
                if i in (0, 8):
                    add(drm, k, base + i)
                if i % 4 == 0:
                    add(drm, hh, base + i)
            elif dr == "half":
                if i == 0:
                    add(drm, k, base + i)
                if i == 8:
                    add(drm, sn, base + i)
                if i % 2 == 0:
                    add(drm, hh, base + i)
            else:
                if i in (0, 3, 6, 10) or (dr == "fill" and i >= 12):
                    add(drm, k, base + i)
                if i in (4, 12) or (dr == "fill" and i in (13, 14, 15)):
                    add(drm, sn, base + i)
                if i % 2 == 0:
                    add(drm, hh, base + i)

    # honk lead: (bar, 16th position, midi note, length in 16ths)
    def line(bar, notes):
        pos = 0
        for nm, ln in notes:
            if nm is not None:
                add(lead, honk(midi(nm), ln * step * 0.95, glide=1.2, vib=5.5) * 0.9, bar * 16 + pos)
            pos += ln

    A4, Bb4, C5, D5, E5, F5, G5, A5, Bb5, C6 = 69, 70, 72, 74, 76, 77, 79, 81, 82, 84
    line(4, [(D5, 2), (None, 2), (F5, 2), (None, 2), (G5, 4), (A5, 4)])
    line(5, [(C6, 4), (A5, 2), (G5, 2), (F5, 4), (D5, 4)])
    line(6, [(D5, 2), (None, 2), (F5, 2), (None, 2), (G5, 4), (A5, 4)])
    line(7, [(Bb5, 4), (A5, 4), (G5, 4), (E5, 4)])
    line(8, [(A5, 8), (F5, 4), (G5, 4)])
    line(9, [(A5, 4), (C6, 4), (Bb5, 4), (A5, 4)])
    line(10, [(G5, 8), (E5, 4), (F5, 4)])
    line(11, [(G5, 4), (A5, 4), (D5, 8)])
    line(15, [(D5, 1), (E5, 1), (F5, 1), (G5, 1), (A5, 1), (G5, 1), (F5, 1), (E5, 1),
              (F5, 1), (G5, 1), (A5, 1), (C6, 1), (D5 + 12, 4)])

    gtr = fft_filter(gtr, 70, 3200)
    out = 0.55 * gtr + 0.5 * bas + 0.75 * drm + 0.42 * lead
    loop = int(SR * step * 16 * bars)
    out[:n - loop] += out[loop:]  # wrap tails so the loop is seamless
    return norm(out[:loop], 0.85)
