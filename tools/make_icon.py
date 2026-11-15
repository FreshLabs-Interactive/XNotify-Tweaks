#!/usr/bin/env python3
"""Draws the notification skin's logo: a glassy badge with a ringing bell and
an unread-dot, tinted with a preset's accent (ring, glow) and secondary (dot).

The badge carries its own dark disc, so it reads on both the dark and the white
bar presets. tools/make_skins.py calls draw_icon() once per preset so every
colour scheme gets a matching logo; run this file directly to get previews.

Usage: python tools/make_icon.py            -> skins/icon_preview.png + skins/src/icon.png
Needs Pillow.
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SS = 4  # supersampling factor


def _rgb(c):
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def _mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def _lum(c):
    r, g, b = c
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def _radial(size, center, radius, inner, outer):
    """RGB radial gradient image."""
    import numpy as np
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    t = np.clip(np.hypot(xx - center[0], yy - center[1]) / radius, 0, 1)[..., None]
    a, b = np.array(inner, float), np.array(outer, float)
    return Image.fromarray(np.round(a + (b - a) * t).astype(np.uint8), 'RGB')


def _vertical(size, top, bottom):
    w, h = size
    img = Image.new('RGB', size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=_mix(top, bottom, y / max(1, h - 1)))
    return img


def _bell_polygon(cx, cy, s):
    """Bell outline (dome + flared rim) as a polygon, centred at cx, cy, scale s."""
    pts = []
    # profile: list of (y, half_width) from top to rim, in units of s
    prof = []
    for i in range(0, 41):                      # dome: quarter circle, r=0.17 at y=-0.19
        a = math.pi / 2 * i / 40
        prof.append((-0.19 - 0.17 * math.cos(a), 0.17 * math.sin(a)))
    for i in range(1, 41):                      # waist widening to the shoulder
        t = i / 40
        prof.append((-0.19 + 0.31 * t, 0.17 + 0.085 * t * t))
    prof += [(0.13, 0.30), (0.20, 0.30)]        # rim flare
    right = [(cx + w * s, cy + y * s) for y, w in prof]
    left = [(cx - w * s, cy + y * s) for y, w in reversed(prof)]
    return right + left


def draw_icon(accent=0x0F8E0F, secondary=0x650FB7, size=64):
    """Returns an RGBA PIL image (size x size)."""
    S = size * SS
    acc, sec = _rgb(accent), _rgb(secondary)
    # Very dark or grey accents (e.g. Black / White) still need a visible ring.
    ring = acc if _lum(acc) > 0.18 else _mix(acc, (200, 200, 205), 0.55)
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    c = S / 2
    R = S * 0.46                                  # badge radius (leaves room for glow)

    # Soft outer glow in the accent colour
    glow = Image.new('L', (S, S), 0)
    ImageDraw.Draw(glow).ellipse([c - R * 1.02, c - R * 1.02, c + R * 1.02, c + R * 1.02], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.035))
    img.paste(Image.new('RGBA', (S, S), ring + (255,)), (0, 0), glow)

    # Outer ring: accent with a lighter top-left
    ring_img = _radial((S, S), (c - R * 0.5, c - R * 0.6), R * 2.0, _mix(ring, (255, 255, 255), 0.55), _mix(ring, (0, 0, 0), 0.35))
    ring_mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(ring_mask).ellipse([c - R, c - R, c + R, c + R], fill=255)
    img.paste(ring_img, (0, 0), ring_mask)

    # Inner glass disc: dark, faintly tinted with the accent
    r2 = R * 0.84
    disc = _radial((S, S), (c, c - r2 * 0.45), r2 * 1.5, _mix(acc, (8, 10, 14), 0.62), (6, 7, 10))
    disc_mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(disc_mask).ellipse([c - r2, c - r2, c + r2, c + r2], fill=255)
    img.paste(disc, (0, 0), disc_mask)

    # Inner shadow along the top edge of the disc
    shade = Image.new('L', (S, S), 0)
    ImageDraw.Draw(shade).ellipse([c - r2, c - r2, c + r2, c + r2], fill=110)
    off = Image.new('L', (S, S), 0)
    ImageDraw.Draw(off).ellipse([c - r2 * 0.98, c - r2 * 0.90, c + r2 * 0.98, c + r2 * 1.06], fill=110)
    shade = ImageChops.subtract(shade, off).filter(ImageFilter.GaussianBlur(S * 0.01))
    img.paste(Image.new('RGBA', (S, S), (0, 0, 0, 255)), (0, 0), shade)

    # Thin bright bevel where the ring meets the glass
    bev = Image.new('L', (S, S), 0)
    bvd = ImageDraw.Draw(bev)
    bvd.ellipse([c - r2 * 1.03, c - r2 * 1.03, c + r2 * 1.03, c + r2 * 1.03], outline=170, width=max(1, int(S * 0.012)))
    grad = Image.linear_gradient('L').resize((S, S)).transpose(Image.FLIP_TOP_BOTTOM)   # bright at the top
    bev = ImageChops.multiply(bev, grad)
    img.paste(Image.new('RGBA', (S, S), (255, 255, 255, 255)), (0, 0), bev)

    # Faint accent light behind the bell
    halo = Image.new('L', (S, S), 0)
    ImageDraw.Draw(halo).ellipse([c - r2 * 0.55, c - r2 * 0.5, c + r2 * 0.55, c + r2 * 0.6], fill=70)
    halo = ImageChops.multiply(halo.filter(ImageFilter.GaussianBlur(S * 0.06)), disc_mask)
    img.paste(Image.new('RGBA', (S, S), ring + (255,)), (0, 0), halo)

    # Ringing arcs either side of the bell
    arcs = Image.new('L', (S, S), 0)
    ad = ImageDraw.Draw(arcs)
    bw = max(2, int(S * 0.034))
    for k, rr in enumerate((0.58, 0.76)):
        box = [c - r2 * rr, c - r2 * rr - S * 0.01, c + r2 * rr, c + r2 * rr - S * 0.01]
        a = 235 - k * 85
        ad.arc(box, 200, 250, fill=a, width=bw)   # left
        ad.arc(box, 290, 340, fill=a, width=bw)   # right
    img.paste(Image.new('RGBA', (S, S), _mix(ring, (255, 255, 255), 0.6) + (255,)), (0, 0), arcs)

    # Bell: white-to-accent-tint gradient, with a darker outline for depth
    bs = r2 * 1.42
    by = c + S * 0.03
    poly = _bell_polygon(c, by, bs)
    bell_mask = Image.new('L', (S, S), 0)
    bd = ImageDraw.Draw(bell_mask)
    bd.polygon(poly, fill=255)
    bd.ellipse([c - bs * 0.045, by - bs * 0.42, c + bs * 0.045, by - bs * 0.33], fill=255)    # top knob
    bd.ellipse([c - bs * 0.075, by + bs * 0.19, c + bs * 0.075, by + bs * 0.33], fill=255)    # clapper
    shadow = bell_mask.filter(ImageFilter.GaussianBlur(S * 0.02))
    img.paste(Image.new('RGBA', (S, S), (0, 0, 0, 255)), (int(S * 0.008), int(S * 0.02)),
              shadow.point(lambda v: v * 0.7))
    bell_fill = _vertical((S, S), (255, 255, 255), _mix((255, 255, 255), ring, 0.35))
    img.paste(bell_fill, (0, 0), bell_mask)
    # Highlight stripe on the bell's left side
    hl = Image.new('L', (S, S), 0)
    ImageDraw.Draw(hl).ellipse([c - bs * 0.20, by - bs * 0.30, c - bs * 0.08, by + bs * 0.10], fill=120)
    hl = ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(S * 0.008)), bell_mask)
    img.paste(Image.new('RGBA', (S, S), (255, 255, 255, 255)), (0, 0), hl)

    # Unread dot in the secondary colour, with a dark rim so it separates from the bell
    dr = R * 0.135
    dx, dy = c + bs * 0.20, c - bs * 0.20 + (by - c)
    dot_col = sec if _lum(sec) > 0.12 else _mix(ring, (255, 255, 255), 0.25)
    dd = ImageDraw.Draw(img)
    dd.ellipse([dx - dr * 1.28, dy - dr * 1.28, dx + dr * 1.28, dy + dr * 1.28], fill=(6, 7, 10, 255))
    dot = _radial((S, S), (dx - dr * 0.35, dy - dr * 0.4), dr * 1.6, _mix(dot_col, (255, 255, 255), 0.45), _mix(dot_col, (0, 0, 0), 0.15))
    dm = Image.new('L', (S, S), 0)
    ImageDraw.Draw(dm).ellipse([dx - dr, dy - dr, dx + dr, dy + dr], fill=255)
    img.paste(dot, (0, 0), dm)

    # Glass reflection over the top of the disc
    gl = Image.new('L', (S, S), 0)
    ImageDraw.Draw(gl).ellipse([c - r2 * 0.80, c - r2 * 0.95, c + r2 * 0.80, c + r2 * 0.05], fill=46)
    gl = ImageChops.multiply(gl.filter(ImageFilter.GaussianBlur(S * 0.02)), disc_mask)
    img.paste(Image.new('RGBA', (S, S), (255, 255, 255, 255)), (0, 0), gl)

    return img.resize((size, size), Image.LANCZOS)


def png_bytes(img):
    import io
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


if __name__ == '__main__':
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    draw_icon(size=64).save(os.path.join(root, 'skins', 'src', 'icon.png'), optimize=True)
    big = draw_icon(size=512)
    big.save(os.path.join(root, 'skins', 'icon_512.png'))
    print('wrote skins/src/icon.png (64x64) and skins/icon_512.png')
