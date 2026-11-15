#!/usr/bin/env python3
"""Builds the notification skin package for the XNotifyTweaks plugin.

Input (skins/src/):
    visual.xur   your compiled toast visual (from the XUI tool), visual Id "eacbe6b504a"
    visual.xui   its source (only used to write recoloured .xui copies for editing)
    scene.xur    the tiny NotifyPopupScene that uses the visual
    icon.png     the built-in logo (the plugin writes it out as Logos/Default.png)
    NotifyPopup.xma  popup sound, carried along unchanged

Output:
    Plugin/XNotifySkins.xzp   scene<N>.xur + visual<N>.xur per colour preset, icon.png, sound
    Shared/SkinPresets.h      preset names/keys for the plugin and the app (same order)
    skins/xui/<Key>.xui       recoloured sources, ready to open in the XUI tool
    skins/swatches.png        quick look at the presets

How the recolour works: a compiled .xur keeps every colour in one table (the
COLR section, big-endian ARGB, first-use order). Each colour is given a role:
    body       the exact marker colour 0x141414: the bar's solid fill and the
               inside of the right end cap. Swapped for the preset's body colour.
    accent     colours near the theme's green (0x0F8E0F): edge lines and text.
    secondary  colours near the theme's purple (0x650FB7): rings and effects.
    (greys, whites and near-blacks are left alone)
Accent and secondary colours move to the preset's colour while keeping their
alpha and their brightness/saturation relative to the original.

Each variant's visual is renamed XNTSkinV000, XNTSkinV001... (same length as
the original Id, so nothing else in the file moves) and gets its own scene that
points at it. The plugin preloads every visual once at boot, then hands the
console the scene for whichever colour is selected, so colours switch live.

Usage: python tools/make_skins.py [--check]
After running it, rebuild BOTH the plugin and the app (they share
Shared/SkinPresets.h) and copy both .xex files to the console.
"""
import colorsys
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC = os.path.join(ROOT, 'skins', 'src')

ORIGINAL_VISUAL_ID = b'eacbe6b504a'
SECTION_NAME = '584E5453'          # "XNTS"; must match Plugin/xex.xml
SOURCE_ACCENT = 0x0F8E0F
SOURCE_SECONDARY = 0x650FB7
# The bar's solid middle and the inside of the right end cap. It's a marker
# value used nowhere else in the visual, so it can be swapped exactly.
SOURCE_BODY = 0x141414
# Where the visual's logo (xenonLogo1) loads from. The plugin maps XNTLOGO: to the
# XNotifyTweaks folder and keeps logo.png set to the logo picked in the app.
# icon.png is still packed: the plugin writes it out as Logos/Default.png.
LOGO_PATH = 'file://XNTLOGO:/logo.png'

# ---------------------------------------------------------------------------
# Presets: key, display name, accent, secondary, body
#   key        saved in XNotifyTweaks.ini - letters/digits only, must be unique.
#              Changing a key makes anyone using it fall back to preset 0.
#   name       shown in the app - plain ASCII, 24 characters at most
#   accent     edge lines and the notification TEXT
#   secondary  rings and effects
#   body       the bar's solid fill - the text sits on this, so keep contrast
# The first preset is the default, and must stay your original design.
# Order only affects the order in the app's list.
# ---------------------------------------------------------------------------
PRESETS = [
    # --- Your designs -----------------------------------------------------
    ('GreenPurple',     'Green / Purple',        0x0F8E0F, 0x650FB7, 0x141414),  # your design, unchanged
    ('RedBlack',        'Red / Black',           0xEB0F0F, 0x1A1A1A, 0x0F0F0F),  # like your red build
    ('PinkWhite',       'Pink / White',          0xEB0FEB, 0xEBEBEB, 0xEBEBEB),  # like the original template

    # --- Your requests ----------------------------------------------------
    ('RedBlackWhite',   'Red / Black / White',   0xD01818, 0x101010, 0xEBEBEB),  # red text on white, black rings
    ('BlueSilverBlack', 'Blue / Silver / Black', 0x2A7FFF, 0xC4C8D0, 0x0C0C0E),  # blue text on black, silver rings
    ('GoldGreen',       'Gold / Green',          0xF0C030, 0x1F9A4A, 0x0A1A10),  # gold text on deep green
    ('BlueOrange',      'Blue / Orange',         0x3A8DFF, 0xFF7A1A, 0x10141C),  # blue text, orange rings, charcoal
    ('PinkPurple',      'Pink / Purple',         0xFF5AB8, 0x7A2BD0, 0x1A0A20),  # pink text on dark plum
    ('RedBlueWhite',    'Red / Blue / White',    0xD02030, 0x1F45B0, 0xEBEBEB),  # red text on white, blue rings

    # --- Cool -------------------------------------------------------------
    ('BlueCyan',        'Blue / Cyan',           0x2F80F0, 0x0FC4E7, 0x0A1428),
    ('IceBlue',         'Ice / Blue',            0xA8E4FF, 0x2A6FD8, 0x0A1424),
    ('TealNavy',        'Teal / Navy',           0x0FB7A0, 0x1A2A8C, 0x0A1A3A),
    ('MintTeal',        'Mint / Teal',           0x5CF2B0, 0x10A890, 0x0A1814),

    # --- Warm -------------------------------------------------------------
    ('OrangeGold',      'Orange / Gold',         0xF07010, 0xF0C020, 0x1A1006),
    ('OrangePink',      'Orange / Pink',         0xFF8A3A, 0xFF4FA8, 0x1A0C10),
    ('CrimsonGold',     'Crimson / Gold',        0xE0283C, 0xE8B820, 0x16080A),
    ('RedGrey',         'Red / Grey',            0xE83030, 0x707070, 0x18181A),

    # --- Purple & green ---------------------------------------------------
    ('PurpleGreen',     'Purple / Green',        0x9A4DFF, 0x0F8E0F, 0x141414),
    ('PurpleGold',      'Purple / Gold',         0xA35CFF, 0xE8B820, 0x140A20),
    ('LimeGrey',        'Lime / Grey',           0x8CE03A, 0x7A7A7A, 0x101210),

    # --- Neutral & high contrast ------------------------------------------
    ('GoldBlack',       'Gold / Black',          0xE8B820, 0x3A3A3A, 0x0C0C0C),
    ('YellowBlack',     'Yellow / Black',        0xFFD400, 0x202020, 0x0E0E0E),
    ('Silver',          'Silver / Grey',         0xD8D8D8, 0x606060, 0x1E1E1E),
    ('BlackWhite',      'Black / White',         0x1A1A1A, 0x808080, 0xEBEBEB),  # dark text on white
]

MAX_NAME_LEN = 24
MIN_TEXT_CONTRAST = 3.0     # WCAG contrast ratio of text (accent) on the bar (body)


# ------------------------------------------------------------------ colour
def hsv(rgb):
    return colorsys.rgb_to_hsv(((rgb >> 16) & 255) / 255.0, ((rgb >> 8) & 255) / 255.0, (rgb & 255) / 255.0)


def hue_dist(a, b):
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


def recolor(argb, accent, secondary, body=SOURCE_BODY):
    alpha, rgb = argb & 0xFF000000, argb & 0xFFFFFF
    if (accent, secondary, body) == (SOURCE_ACCENT, SOURCE_SECONDARY, SOURCE_BODY):
        return argb
    if rgb == SOURCE_BODY:
        return alpha | body
    h, s, v = hsv(rgb)
    if s < 0.30 or v < 0.12:
        return argb                                   # greys / near-black: keep
    src_acc, src_sec = hsv(SOURCE_ACCENT), hsv(SOURCE_SECONDARY)
    if hue_dist(h, src_acc[0]) <= hue_dist(h, src_sec[0]):
        ref, tgt = src_acc, hsv(accent)
    else:
        ref, tgt = src_sec, hsv(secondary)
    nh = (tgt[0] + (h - ref[0])) % 1.0
    ns = tgt[1] if tgt[1] < 0.05 else min(1.0, tgt[1] * s / ref[1])
    nv = min(1.0, tgt[2] * v / ref[2])
    r, g, b = colorsys.hsv_to_rgb(nh, ns, nv)
    return alpha | int(round(r * 255)) << 16 | int(round(g * 255)) << 8 | int(round(b * 255))


def luminance(rgb):
    def chan(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * chan((rgb >> 16) & 255) + 0.7152 * chan((rgb >> 8) & 255) + 0.0722 * chan(rgb & 255)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def validate_presets():
    """Stops with a clear message on mistakes in PRESETS; warns on hard-to-read text."""
    errors, warnings, keys = [], [], set()
    if not PRESETS:
        errors.append('PRESETS is empty.')
    elif PRESETS[0][2:] != (SOURCE_ACCENT, SOURCE_SECONDARY, SOURCE_BODY):
        errors.append('The first preset must be your original design (0x0F8E0F, 0x650FB7, 0x141414).')
    if len(PRESETS) > 1000:
        errors.append('At most 1000 presets (visual names are XNTSkinV000-999).')
    for i, entry in enumerate(PRESETS):
        if len(entry) != 5:
            errors.append(f'Preset {i}: needs 5 values (key, name, accent, secondary, body), has {len(entry)}.')
            continue
        key, name, acc, sec, body = entry
        if not re.fullmatch(r'[A-Za-z0-9]+', key):
            errors.append(f'Preset {i}: key {key!r} must be letters/digits only.')
        if key.lower() in keys:
            errors.append(f'Preset {i}: key {key!r} is used twice (keys are not case-sensitive).')
        keys.add(key.lower())
        if not name or len(name) > MAX_NAME_LEN or not all(32 <= ord(c) < 127 for c in name) or '"' in name or '\\' in name:
            errors.append(f'Preset {i}: name {name!r} must be 1-{MAX_NAME_LEN} plain characters, no quotes/backslashes.')
        for label, c in (('accent', acc), ('secondary', sec), ('body', body)):
            if not isinstance(c, int) or not 0 <= c <= 0xFFFFFF:
                errors.append(f'Preset {i} ({key}): {label} must be a 0xRRGGBB number.')
        if not errors and contrast(acc, body) < MIN_TEXT_CONTRAST:
            warnings.append(f'Preset {i} ({key}): text may be hard to read - accent on body contrast is '
                            f'{contrast(acc, body):.1f}:1 (aim for {MIN_TEXT_CONTRAST}:1 or more).')
    if errors:
        sys.exit('Fix PRESETS in tools/make_skins.py:\n  ' + '\n  '.join(errors))
    for w in warnings:
        print('warning:', w)


# --------------------------------------------------------------------- XUR
def xur_sections(data):
    assert data[:4] == b'XUIB', 'not a .xur'
    size = struct.unpack('>I', data[14:18])[0]
    assert size == len(data), 'size field mismatch'
    p = data.find(b'STRN')
    sections = {}
    while data[p:p + 4].isalpha():
        off, length = struct.unpack('>II', data[p + 4:p + 12])
        sections[data[p:p + 4].decode()] = (off, length)
        p += 12
    return sections


def xur_colors(data):
    off, length = xur_sections(data)['COLR']
    return [struct.unpack('>I', data[off + i:off + i + 4])[0] for i in range(0, length, 4)]


def xur_recolor(data, accent, secondary, body=SOURCE_BODY):
    data = bytearray(data)
    off, length = xur_sections(bytes(data))['COLR']
    for i in range(0, length, 4):
        c = struct.unpack('>I', data[off + i:off + i + 4])[0]
        data[off + i:off + i + 4] = struct.pack('>I', recolor(c, accent, secondary, body))
    return bytes(data)


def xur_rename(data, old, new):
    assert len(old) == len(new)
    off, length = xur_sections(data)['STRN']
    strn = data[off:off + length]
    needle = b'\0' + old + b'\0'
    assert strn.count(needle) == 1, f'expected one {old!r} in the string table'
    i = off + strn.index(needle) + 1
    return data[:i] + new + data[i + len(new):]


# --------------------------------------------------------------------- XZP
def xzp_pack(files):
    """files: list of (name, bytes). Same layout as the XDK's packer: 'XUIZ',
    version 3, total size, 0, table size, u16 count, then size/offset/name
    per file (offsets relative to the end of the table), then the data."""
    table = b''
    offset = 0
    for name, blob in files:
        nb = name.encode('ascii')
        table += struct.pack('>IIB', len(blob), offset, len(nb)) + nb
        offset += len(blob)
    total = 0x16 + len(table) + offset
    head = struct.pack('>4sIIIIH', b'XUIZ', 3, total, 0, len(table), len(files))
    return head + table + b''.join(blob for _, blob in files)


def xzp_unpack(data):
    assert data[:4] == b'XUIZ'
    count = struct.unpack('>H', data[20:22])[0]
    p, entries = 22, []
    for _ in range(count):
        size, off, n = struct.unpack('>IIB', data[p:p + 9])
        entries.append((data[p + 9:p + 9 + n].decode('ascii'), off, size))
        p += 9 + n
    return [(name, data[p + off:p + off + size]) for name, off, size in entries]


# ------------------------------------------------------------------ outputs
def write_header(path):
    lines = [
        '// Generated by tools/make_skins.py - do not edit by hand.',
        '#pragma once',
        '',
        f'#define XNT_SKIN_COUNT   {len(PRESETS)}',
        f'#define XNT_SKIN_SECTION L"{SECTION_NAME}"',
        '',
        'struct XntSkinPreset { const char* name; const char* key; unsigned long accent; unsigned long secondary; unsigned long body; };',
        '',
        'static const XntSkinPreset g_SkinPresets[XNT_SKIN_COUNT] = {',
    ]
    for key, name, acc, sec, body in PRESETS:
        lines.append(f'    {{ "{name}", "{key}", 0x{acc:06X}, 0x{sec:06X}, 0x{body:06X} }},')
    lines += ['};', '']
    with open(path, 'w', newline='\r\n') as f:
        f.write('\n'.join(lines))


def write_swatches(path):
    """Rough preview: bar = body, edges + text = accent, ring = secondary. Two columns."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Medium.otf', 17)
    except OSError:
        font = ImageFont.load_default()
    hexrgb = lambda c: ((c >> 16) & 255, (c >> 8) & 255, c & 255)
    cols, colw, rowh = 2, 560, 60
    rows = (len(PRESETS) + cols - 1) // cols
    img = Image.new('RGB', (colw * cols + 16, rowh * rows + 16), (14, 18, 26))
    d = ImageDraw.Draw(img)
    for i, (key, name, acc, sec, body) in enumerate(PRESETS):
        x, y = 8 + (i // rows) * colw, 8 + (i % rows) * rowh
        a = hexrgb(recolor(0xFF000000 | SOURCE_ACCENT, acc, sec, body))
        s = hexrgb(recolor(0xFF000000 | SOURCE_SECONDARY, acc, sec, body))
        d.rounded_rectangle([x + 8, y + 6, x + 290, y + 50], radius=10, fill=hexrgb(body))
        d.rectangle([x + 14, y + 6, x + 284, y + 9], fill=a)
        d.rectangle([x + 14, y + 47, x + 284, y + 50], fill=a)
        d.ellipse([x + 14, y + 10, x + 50, y + 46], outline=s, width=4)
        d.text((x + 62, y + 17), 'Notification text', font=font, fill=a)
        d.text((x + 306, y + 17), f'{i:2d}  {name}', font=font, fill=(230, 233, 238))
    img.save(path)


def main():
    check = '--check' in sys.argv
    validate_presets()

    visual = open(os.path.join(SRC, 'visual.xur'), 'rb').read()
    scene = open(os.path.join(SRC, 'scene.xur'), 'rb').read()
    xui = open(os.path.join(SRC, 'visual.xui'), encoding='utf-8', errors='strict', newline='').read()
    if not any((c & 0xFFFFFF) == SOURCE_BODY for c in xur_colors(visual)):
        sys.exit('skins/src/visual.xur has no body colour (0x%06X). It is older than visual.xui:\n'
                 'open skins/src/visual.xui in the XUI tool, save it as skins/src/visual.xur, then run this again.'
                 % SOURCE_BODY)

    if LOGO_PATH.encode() not in visual:
        print(f'note: visual.xur still uses the packed logo (icon.png), so the app\'s Skin logo picker\n'
              f'      has no effect. Compile the current visual.xui (logo path {LOGO_PATH}) to fix that.')

    xui_dir = os.path.join(ROOT, 'skins', 'xui')
    os.makedirs(xui_dir, exist_ok=True)
    for old in os.listdir(xui_dir):                   # drop variants of presets that were removed
        if old.endswith('.xui'):
            os.remove(os.path.join(xui_dir, old))

    files = []
    for i, (key, name, acc, sec, body) in enumerate(PRESETS):
        new_id = f'XNTSkinV{i:03d}'.encode()
        v = xur_rename(xur_recolor(visual, acc, sec, body), ORIGINAL_VISUAL_ID, new_id)
        s = xur_rename(scene, ORIGINAL_VISUAL_ID, new_id)
        files += [(f'scene{i}.xur', s), (f'visual{i}.xur', v)]

        x = re.sub(r'0x([0-9a-fA-F]{8})', lambda m: '0x%08x' % recolor(int(m.group(1), 16), acc, sec, body), xui)
        x = x.replace('<Id>eacbe6b504a</Id>', f'<Id>{new_id.decode()}</Id>')
        with open(os.path.join(xui_dir, f'{key}.xui'), 'w', encoding='utf-8', newline='') as f:
            f.write(x)

    files.append(('icon.png', open(os.path.join(SRC, 'icon.png'), 'rb').read()))
    files.append(('NotifyPopup.xma', open(os.path.join(SRC, 'NotifyPopup.xma'), 'rb').read()))
    xzp = xzp_pack(files)
    with open(os.path.join(ROOT, 'Plugin', 'XNotifySkins.xzp'), 'wb') as f:
        f.write(xzp)
    write_header(os.path.join(ROOT, 'Shared', 'SkinPresets.h'))
    write_swatches(os.path.join(ROOT, 'skins', 'swatches.png'))
    print(f'XNotifySkins.xzp: {len(xzp)} bytes ({len(xzp) // 1024} KB), {len(files)} files, {len(PRESETS)} presets')
    if len(xzp) > 160 * 1024:
        print('note: a big skin package. If the plugin stops loading, move <baseaddr> in Plugin/xex.xml '
              'to a free 64 KB-aligned address with more room.')

    if check:
        back = dict(xzp_unpack(xzp))
        assert xur_colors(back['visual0.xur']) == xur_colors(visual), 'preset 0 must be unchanged'
        for i, (key, name, acc, sec, body) in enumerate(PRESETS):
            v, s = back[f'visual{i}.xur'], back[f'scene{i}.xur']
            assert len(v) == len(visual) and len(s) == len(scene)
            diff = [j for j in range(len(v)) if v[j] != visual[j]]
            off, length = xur_sections(v)['COLR']
            soff, slen = xur_sections(v)['STRN']
            assert all(off <= j < off + length or soff <= j < soff + slen for j in diff), 'bytes changed outside COLR/STRN'
            assert f'XNTSkinV{i:03d}'.encode() in s and ORIGINAL_VISUAL_ID not in s and ORIGINAL_VISUAL_ID not in v
            print(f'  {i:2d} {key:16s} {len(diff):3d} bytes changed (colours + name only)')
        print('check OK')

    print('Next: rebuild BOTH the plugin and the app, then copy both .xex files to the console.')


if __name__ == '__main__':
    main()
