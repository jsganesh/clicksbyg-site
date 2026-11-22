#!/usr/bin/env python3
"""Draw placeholder landscape images into photos/source/samples/.

They only exist so the gallery has something to show before real photos
are added. Replace them: put your exports in photos/source/ and point the
entries in photos/site.json at them.
"""
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "photos" / "source" / "samples"


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ridge(w, h, base, rough, rng):
    """Midpoint-displacement ridge line: list of (x, y)."""
    n = 2 ** 9
    ys = [0.0] * (n + 1)
    ys[0], ys[n] = rng.uniform(-1, 1), rng.uniform(-1, 1)
    step, scale = n, 1.0
    while step > 1:
        half = step // 2
        for i in range(half, n, step):
            ys[i] = (ys[i - half] + ys[i + half]) / 2 + rng.uniform(-scale, scale)
        step, scale = half, scale * 0.55
    return [(i * w / n, base - ys[i] * rough * h) for i in range(n + 1)]


def sky(size, top, bottom):
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(size[1]):
        d.line([(0, y), (size[0], y)], fill=lerp(top, bottom, y / size[1]))
    return img


def add_sun(img, sun, pos):
    w, h = img.size
    cx, cy, r = pos[0] * w, pos[1] * h, min(w, h) * 0.05
    glow = Image.new("RGB", img.size)
    ImageDraw.Draw(glow).ellipse([cx - r * 6, cy - r * 6, cx + r * 6, cy + r * 6],
                                 fill=tuple(c // 3 for c in sun))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(r * 3)))
    ImageDraw.Draw(img).ellipse([cx - r, cy - r, cx + r, cy + r], fill=sun)
    return img


def add_ridges(img, layers, near, far, water, rng):
    w, h = img.size
    d = ImageDraw.Draw(img)
    horizon = 0.55 if water else 0.62
    for i in range(layers):
        t = i / max(1, layers - 1)
        base = h * (horizon - 0.18 + 0.18 * t + (0.05 if water else 0.25) * t)
        pts = ridge(w, h, base, 0.12 - 0.05 * t, rng)
        d.polygon(pts + [(w, h), (0, h)], fill=lerp(far, near, t))


def add_water(img, near, ripple, rng):
    w, h = img.size
    top = int(h * 0.66)
    refl = img.crop((0, 0, w, top)).transpose(Image.FLIP_TOP_BOTTOM)
    refl = refl.resize((w, h - top)).filter(ImageFilter.GaussianBlur(6))
    img.paste(Image.blend(refl, Image.new("RGB", refl.size, near), 0.45), (0, top))
    d = ImageDraw.Draw(img)
    for _ in range(140):
        y, x, ln = rng.uniform(top, h), rng.uniform(0, w), rng.uniform(20, 160)
        d.line([(x, y), (x + ln, y)], fill=ripple, width=1)


def scene(name, size, sky_top, sky_bottom, sun, sun_pos, layers, near, far, water=False, seed=1):
    rng = random.Random(seed)
    img = sky(size, sky_top, sky_bottom)
    if sun:
        img = add_sun(img, sun, sun_pos)
    add_ridges(img, layers, near, far, water, rng)
    if water:
        add_water(img, near, lerp(sky_bottom, near, 0.4), rng)
    img = Image.blend(img, Image.effect_noise(size, 18).convert("RGB"), 0.04)  # film grain
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{name}.jpg", quality=90)
    print("wrote", OUT / f"{name}.jpg")

L, P, W = (3000, 2000), (2000, 3000), (3600, 1800)
scene("blue-ridges", L, (196, 210, 226), (236, 230, 222), None, None, 6, (28, 44, 70), (170, 188, 210), seed=3)
scene("low-tide-gold", L, (70, 60, 90), (246, 182, 96), (255, 226, 160), (0.5, 0.56), 2, (22, 20, 26), (90, 70, 80), water=True, seed=7)
scene("violet-hour", L, (40, 34, 78), (232, 140, 150), None, None, 4, (18, 14, 30), (96, 70, 120), seed=11)
scene("first-light", P, (120, 140, 190), (250, 196, 160), (255, 236, 200), (0.62, 0.48), 4, (40, 36, 54), (170, 150, 170), seed=5)
scene("sea-fret", L, (190, 198, 194), (214, 218, 210), None, None, 3, (70, 86, 80), (170, 180, 174), water=True, seed=13)
scene("long-valley", W, (170, 200, 214), (230, 232, 214), None, None, 5, (30, 60, 56), (150, 180, 180), seed=17)
scene("ember", L, (30, 10, 20), (214, 70, 40), (255, 170, 110), (0.35, 0.6), 3, (10, 6, 8), (80, 30, 30), seed=19)
scene("harbour-dusk", P, (36, 56, 100), (238, 150, 90), None, None, 2, (16, 22, 36), (70, 80, 110), water=True, seed=23)
scene("moonrise", L, (10, 18, 42), (44, 64, 110), (236, 236, 222), (0.7, 0.3), 4, (6, 10, 22), (40, 56, 96), seed=29)
