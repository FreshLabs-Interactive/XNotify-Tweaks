#!/usr/bin/env python3
"""Draws XNotify Tweaks' Aurora artwork into art/:

    cover.png       900x600 full wrap (back | spine | front), the layout Aurora
                    and XboxUnity use: back 0-423, spine 423-475, front 475-900
    background.png  1920x1080
    icon.png        64x64  (icon_512.png is the same art, large)
    banner.png      420x95

Then run tools/aurora_asset.py to turn them into the .asset files Aurora reads.

Needs Pillow. Fonts: Inter (SIL OFL) for the art, DejaVu Sans for the app
screenshot (same font the app uses). Pass font folders with --inter/--dejavu
if they aren't in the default Linux locations.
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ------------------------------------------------------------------ palette
NAVY_0 = (11, 15, 22)
NAVY_1 = (20, 27, 39)
NAVY_2 = (28, 37, 52)
PANEL = (26, 32, 43)
LINE = (60, 69, 86)
TEXT = (242, 244, 247)
DIM = (138, 147, 163)
GREEN = (93, 194, 30)
GREEN_LIGHT = (123, 216, 143)
GREEN_DARK = (44, 110, 47)
BAND = (52, 140, 58)

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "art"))
ap.add_argument("--inter", default="/usr/share/fonts/opentype/inter")
ap.add_argument("--dejavu", default="/usr/share/fonts/truetype/dejavu")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)


def inter(weight, size):
    return ImageFont.truetype(os.path.join(args.inter, f"Inter-{weight}.otf"), size)


def dejavu(size):
    return ImageFont.truetype(os.path.join(args.dejavu, "DejaVuSans.ttf"), size)


def vgradient(w, h, top, bottom):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def tracked(draw, xy, text, font, fill, tracking, anchor_center=False):
    """Letter-spaced text. Returns the width drawn."""
    widths = [font.getlength(c) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=font, fill=fill)
        x += w + tracking
    return total


def glow(base, box, color, radius, strength=1.0):
    """Soft coloured glow behind a rounded box."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=color + (int(255 * strength),))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 1.6))
    base.alpha_composite(layer)


# ------------------------------------------------------------------ the mark
def draw_mark(size, tile=True):
    """The XNotify Tweaks mark: a TV with a 3x3 grid of anchor points and a
    green toast parked in the top-right slot. Drawn 4x and downsampled."""
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = s / 100.0  # design units

    if tile:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=22 * u, fill=NAVY_2 + (255,))
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=22 * u, outline=(48, 59, 78, 255), width=max(int(1.6 * u), 1))

    # Screen
    sx0, sy0, sx1, sy1 = 14 * u, 22 * u, 86 * u, 74 * u
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=7 * u, fill=NAVY_0 + (255,), outline=LINE + (255,), width=int(3 * u))
    # Stand
    d.rounded_rectangle([42 * u, 77 * u, 58 * u, 81 * u], radius=2 * u, fill=LINE + (255,))

    # 3x3 anchor dots
    for row in range(3):
        for col in range(3):
            if (row, col) == (0, 2):
                continue
            cx = sx0 + (sx1 - sx0) * (0.2 + 0.3 * col)
            cy = sy0 + (sy1 - sy0) * (0.24 + 0.26 * row)
            r = 2.6 * u
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(70, 82, 104, 255))

    # Toast, top-right, slightly breaking out of the screen
    tx0, ty0, tx1, ty1 = 46 * u, 15 * u, 92 * u, 37 * u
    toast = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    td = ImageDraw.Draw(toast)
    td.rounded_rectangle([tx0, ty0, tx1, ty1], radius=11 * u, fill=GREEN + (255,))
    # Icon circle + two text lines
    cr = 6.2 * u
    ccx, ccy = tx0 + 11 * u, (ty0 + ty1) / 2
    td.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], fill=(255, 255, 255, 255))
    td.rounded_rectangle([tx0 + 21 * u, ccy - 5.2 * u, tx1 - 7 * u, ccy - 1.6 * u], radius=1.8 * u, fill=(255, 255, 255, 240))
    td.rounded_rectangle([tx0 + 21 * u, ccy + 1.6 * u, tx1 - 15 * u, ccy + 5.2 * u], radius=1.8 * u, fill=(255, 255, 255, 170))
    shadow = toast.split()[3].point(lambda a: int(a * 0.55))
    shadow_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    shadow_img.putalpha(shadow.filter(ImageFilter.GaussianBlur(3 * u)))
    img.alpha_composite(shadow_img, (0, int(2 * u)))
    img.alpha_composite(toast)

    return img.resize((size, size), Image.LANCZOS)


# --------------------------------------------------------- app screenshot
def draw_app_screen():
    """The config app's menu, laid out exactly like App/main.cpp draws it."""
    img = Image.new("RGB", (1280, 720), (16, 20, 28))
    d = ImageDraw.Draw(img)
    f = lambda sc: dejavu(int(round(28 * sc)))
    W = lambda t, sc: f(sc).getlength(t)
    X0, X1, RY, RH = 190, 1090, 136, 31
    d.rectangle([150, 40, 1129, 679], fill=PANEL)
    d.text((X0, 52), "XNotify Tweaks", font=f(1.4), fill=TEXT)
    t = "Plugin: loaded"
    d.text((X1 - W(t, .72), 64), t, font=f(.72), fill=GREEN_LIGHT)
    d.text((X0, 98), "All changes saved", font=f(.72), fill=DIM)
    rows = [("Plugin enabled", "On"), ("Notification position", "<  Top Right  >"),
            ("Override notification options", "On"), ("    Show notifications", "On"),
            ("    Play sound", "Off"), ("    Show during video playback", "On"),
            ("    Show during IPTV / Live TV", "On"), ("Enforce (re-apply every 5 s)", "Off"),
            ("Boot message", "On"), ("    Boot message text", '"Ready to play"'),
            ("Toast icon", "<  Achievement  >"), ("Send test notification", ""),
            ("Restore defaults", ""), ("Save & exit", "")]
    for i, (label, value) in enumerate(rows):
        y = RY + i * RH
        if i == 1:
            d.rectangle([X0 - 16, y - 1, X1 + 15, y + RH - 2], fill=GREEN_DARK)
        d.text((X0, y), label, font=f(.85), fill=TEXT)
        if value:
            col = (158, 203, 255) if value.startswith("<") else (GREEN_LIGHT if value == "On" else (224, 122, 122) if value == "Off" else TEXT)
            d.text((X1 - W(value, .85), y), value, font=f(.85), fill=col)
        if i == 1:
            x, yy = X1 - 430, y + 2
            d.rectangle([x - 3, yy - 3, x + 3 * 16 + 4 + 2, yy + 3 * 7 + 4 + 2], fill=(42, 49, 64))
            for k in range(9):
                cx, cy = x + (k % 3) * 18, yy + (k // 3) * 9
                d.rectangle([cx, cy, cx + 15, cy + 6], fill=GREEN if k == 2 else (60, 69, 86))
    hy = RY + len(rows) * RH + 12
    d.line([(X0 - 16, hy - 6), (X1 + 15, hy - 6)], fill=(46, 54, 68))
    d.text((X0, hy), "Where toasts appear. Changes preview live; a sample toast follows.", font=f(.72), fill=DIM)
    fx = X0
    for key, col, label in [("A", GREEN, "Select"), ("B", (229, 50, 45), "Back"), ("X", (46, 123, 230), "Test"),
                            ("START", TEXT, "Save"), ("D-pad", TEXT, "Change")]:
        d.text((fx, 652), key, font=f(.72), fill=col); fx += W(key, .72) + 8
        d.text((fx, 652), label, font=f(.72), fill=DIM); fx += W(label, .72) + 34
    # The toast it's previewing, top right
    tb = [1010, 4, 1250, 52]
    rgba = img.convert("RGBA")
    glow(rgba, tb, (0, 0, 0), 14, 0.6)
    d = ImageDraw.Draw(rgba)
    d.rounded_rectangle(tb, radius=24, fill=(236, 240, 244))
    d.ellipse([tb[0] + 10, tb[1] + 9, tb[0] + 40, tb[1] + 39], fill=GREEN)
    d.text((tb[0] + 50, tb[1] + 12), "Ready to play", font=dejavu(20), fill=(30, 34, 40))
    return rgba.convert("RGB")


# ------------------------------------------------------------------- cover
def draw_cover():
    W, H = 900, 600
    BACK = (0, 423)
    SPINE = (423, 475)
    FRONT = (475, 900)
    BAND_H, FOOT_H = 60, 10

    img = vgradient(W, H, NAVY_1, NAVY_0).convert("RGBA")
    d = ImageDraw.Draw(img)

    # Subtle diagonal light on the front
    light = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(light).ellipse([560, 40, 860, 340], fill=(93, 194, 30, 46))
    img.alpha_composite(light.filter(ImageFilter.GaussianBlur(70)))

    # Faint anchor-dot texture behind the mark only, fading out before the text
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for gy in range(BAND_H + 18, 292, 22):
        fade = 1 - (gy - BAND_H) / (292 - BAND_H)
        for gx in range(FRONT[0] + 14, FRONT[1] - 6, 22):
            dd.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=(255, 255, 255, int(40 * fade)))
    img.alpha_composite(dots)
    d = ImageDraw.Draw(img)

    # Spine: darker, with a centre highlight like a real case
    spine = Image.new("RGBA", (SPINE[1] - SPINE[0], H))
    sd = ImageDraw.Draw(spine)
    w = spine.width
    for x in range(w):
        t = 1 - abs((x - w / 2) / (w / 2))
        c = tuple(int(a + (b - a) * t) for a, b in zip((13, 18, 27), (30, 40, 58)))
        sd.line([(x, 0), (x, H)], fill=c + (255,))
    img.alpha_composite(spine, (SPINE[0], 0))
    d = ImageDraw.Draw(img)

    # Bands
    d.rectangle([0, 0, W, BAND_H - 1], fill=BAND)
    d.rectangle([0, H - FOOT_H, W, H], fill=BAND)
    band_font = inter("Medium", 25)
    tracked(d, ((FRONT[0] + FRONT[1]) / 2, 15), "APPLICATION", band_font, (255, 255, 255), 1.5, anchor_center=True)

    # ---------------- front
    fcx = (FRONT[0] + FRONT[1]) / 2
    mark = draw_mark(196)
    glow(img, [fcx - 92, 92, fcx + 92, 276], GREEN, 30, 0.22)
    img.alpha_composite(mark, (int(fcx - 98), 86))
    d = ImageDraw.Draw(img)

    title = inter("ExtraBold", 44)
    w1 = title.getlength("XNotify ")
    w2 = title.getlength("Tweaks")
    tx = fcx - (w1 + w2) / 2
    d.text((tx, 302), "XNotify ", font=title, fill=TEXT)
    d.text((tx + w1, 302), "Tweaks", font=title, fill=GREEN)

    tag = inter("Medium", 17)
    t = "Notification controls for every dashboard"
    d.text((fcx - tag.getlength(t) / 2, 368), t, font=tag, fill=DIM)

    bullet_font = inter("Medium", 16)
    bullets = ["Move toasts to any of 9 positions",
               "Sound, video and IPTV toggles",
               "Your own boot message and icon",
               "Aurora, FSD and the stock dash"]
    by = 412
    bx = FRONT[0] + 52
    for b in bullets:
        d.rounded_rectangle([bx, by + 6, bx + 9, by + 15], radius=2, fill=GREEN)
        d.text((bx + 20, by), b, font=bullet_font, fill=TEXT)
        by += 30

    foot = inter("SemiBold", 11)
    tracked(d, (fcx, 560), "DASHLAUNCH PLUGIN  +  CONFIG APP", foot, DIM, 1.6, anchor_center=True)

    # ---------------- spine
    scx = (SPINE[0] + SPINE[1]) / 2
    def vertical(text, font, fill, y_top, tracking=0.0):
        tw = int(sum(font.getlength(c) for c in text) + tracking * (len(text) - 1)) + 4
        th = int(font.size * 1.4)
        layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(layer), (0, 0), text, font, fill, tracking)
        layer = layer.rotate(-90, expand=True)
        img.alpha_composite(layer, (int(scx - layer.width / 2 + 3), int(y_top)))
        return layer.height
    vertical("APPLICATION", inter("Medium", 19), (220, 226, 234), 76, 1.2)
    sp_title = inter("ExtraBold", 26)
    h1 = vertical("XNotify", sp_title, TEXT, 262)
    vertical("Tweaks", sp_title, GREEN, 262 + h1 + 4)
    img.alpha_composite(draw_mark(36), (int(scx - 18), 534))

    # ---------------- back
    d = ImageDraw.Draw(img)
    bxl = 26
    img.alpha_composite(draw_mark(30), (bxl, 78))
    d = ImageDraw.Draw(img)
    small_title = inter("ExtraBold", 21)
    d.text((bxl + 40, 80), "XNotify ", font=small_title, fill=TEXT)
    d.text((bxl + 40 + small_title.getlength("XNotify "), 80), "Tweaks", font=small_title, fill=GREEN)

    d.text((bxl, 124), "Your notifications, your way", font=inter("Bold", 22), fill=TEXT)
    body = inter("Regular", 14)
    para = ("Pick where Xbox 360 notifications pop up, mute the chime, and "
            "choose when they're allowed to appear. A tiny DashLaunch plugin "
            "re-applies your settings every time a dashboard or game starts.")
    # wrap
    words, lines, cur = para.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if body.getlength(trial) > BACK[1] - bxl * 2:
            lines.append(cur); cur = wd
        else:
            cur = trial
    lines.append(cur)
    y = 160
    for ln in lines:
        d.text((bxl, y), ln, font=body, fill=(196, 202, 212))
        y += 21

    # Screenshot
    shot = draw_app_screen()
    sw = BACK[1] - bxl * 2
    sh = int(sw * 720 / 1280)
    shot = shot.resize((sw, sh), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=8, fill=255)
    sy = y + 14
    glow(img, [bxl, sy, bxl + sw, sy + sh], (0, 0, 0), 10, 0.7)
    img.paste(shot, (bxl, sy), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([bxl, sy, bxl + sw - 1, sy + sh - 1], radius=8, outline=(54, 64, 82), width=1)

    y = sy + sh + 18
    small = inter("Medium", 13)
    for b in ["Live preview and test notifications",
              "Settings in one INI on Hdd or USB",
              "Re-applies on every title launch",
              "Requires RGH/JTAG + DashLaunch"]:
        d.rounded_rectangle([bxl, y + 5, bxl + 7, y + 12], radius=2, fill=GREEN)
        d.text((bxl + 16, y), b, font=small, fill=(210, 215, 223))
        y += 22

    return img.convert("RGB")


# -------------------------------------------------------------- background
def draw_background():
    W, H = 1920, 1080
    img = vgradient(W, H, (16, 22, 33), (7, 10, 15)).convert("RGBA")

    light = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    ld.ellipse([1150, -250, 2150, 650], fill=(93, 194, 30, 40))
    ld.ellipse([-400, 600, 700, 1500], fill=(40, 90, 160, 28))
    img.alpha_composite(light.filter(ImageFilter.GaussianBlur(160)))

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # Big faint 3x3 anchor grid, with the top-right slot lit
    for row in range(3):
        for col in range(3):
            cx, cy = 360 + col * 600, 190 + row * 350
            if (row, col) == (0, 2):
                continue
            d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(255, 255, 255, 22))
    # A large soft toast in the lit slot
    tb = [1380, 140, 1840, 240]
    glow(img, tb, GREEN, 40, 0.35)
    d.rounded_rectangle(tb, radius=50, fill=(93, 194, 30, 70))
    img.alpha_composite(ov)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse([tb[0] + 22, tb[1] + 22, tb[0] + 78, tb[1] + 78], fill=(255, 255, 255, 80))
    d.rounded_rectangle([tb[0] + 100, tb[1] + 32, tb[2] - 50, tb[1] + 46], radius=7, fill=(255, 255, 255, 70))
    d.rounded_rectangle([tb[0] + 100, tb[1] + 56, tb[2] - 140, tb[1] + 70], radius=7, fill=(255, 255, 255, 45))

    # Fine dot texture
    for gy in range(30, H, 40):
        for gx in range(30, W, 40):
            d.point((gx, gy), fill=(255, 255, 255, 18))
    img.alpha_composite(ov)
    return img.convert("RGB")


# ------------------------------------------------------------------ banner
def draw_banner():
    W, H = 420, 95
    img = vgradient(W, H, NAVY_2, NAVY_0).convert("RGBA")
    light = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(light).ellipse([-40, -40, 140, 140], fill=(93, 194, 30, 60))
    img.alpha_composite(light.filter(ImageFilter.GaussianBlur(30)))
    img.alpha_composite(draw_mark(71), (12, 12))
    d = ImageDraw.Draw(img)
    title = inter("ExtraBold", 31)
    d.text((98, 14), "XNotify ", font=title, fill=TEXT)
    d.text((98 + title.getlength("XNotify "), 14), "Tweaks", font=title, fill=GREEN)
    d.text((99, 56), "Notification controls", font=inter("Medium", 15), fill=DIM)
    d.rectangle([0, H - 3, W, H], fill=BAND)
    return img.convert("RGB")


if __name__ == "__main__":
    out = args.out
    draw_cover().save(os.path.join(out, "cover.png"))
    draw_background().save(os.path.join(out, "background.png"))
    draw_banner().save(os.path.join(out, "banner.png"))
    draw_mark(512).save(os.path.join(out, "icon_512.png"))
    draw_mark(64).save(os.path.join(out, "icon.png"))
    draw_app_screen().save(os.path.join(out, "screenshot.png"))
    print("wrote art to", os.path.abspath(out))
