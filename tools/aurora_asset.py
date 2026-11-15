#!/usr/bin/env python3
"""Packs art/*.png into the .asset files Aurora reads from
Data/GameData/<TitleID>_<n>/:

    GC<TitleID>.asset   box art (cover.png, 900x600)
    BK<TitleID>.asset   background (background.png, 1920x1080)
    GL<TitleID>.asset   icon (icon.png, 64x64) + banner (banner.png, 420x95)

File layout (big-endian), as documented by the Aurora community
(jrobiche/xbox360-aurora-developer-documentation, Aurora Asset Editor):
    "RXEA", version 1, image data length, used-entry bit flags, screenshot count
    25 entries x 64 bytes: data offset, data length, extended info (0), then a
        52-byte D3D texture header (common, ref count, fences, identifier,
        base/mip flush, 6 GPU fetch-constant dwords)
    zero padding to 2048 bytes, then each texture's data
Textures are DXT5, linear (untiled), 8-in-16 byte swapped, with each side
padded up to a multiple of 128.

Usage:
    python tools/aurora_asset.py                 # FFFF584E, reads/writes art/
    python tools/aurora_asset.py --check         # also decodes the files back and compares
    python tools/aurora_asset.py <TitleID> <outdir>
Needs Pillow and numpy.
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

ENTRIES = 25
HEADER_SIZE = 2048
ICON, BANNER, BOXART, SLOT, BACKGROUND = 0, 1, 2, 3, 4
SIZES = {ICON: (64, 64), BANNER: (420, 95), BOXART: (900, 600), BACKGROUND: (1920, 1080)}

FMT_DXT4_5 = 0x14
ENDIAN_8IN16 = 1


def pad128(n):
    return (n + 127) & ~127


# ---------------------------------------------------------------- DXT5 encode
def _to565(rgb):
    rgb = np.clip(np.round(rgb), 0, 255).astype(np.uint32)
    return (rgb[:, 0] >> 3) << 11 | (rgb[:, 1] >> 2) << 5 | (rgb[:, 2] >> 3)


def _from565(v):
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], 1).astype(np.float32)


def encode_dxt5(rgba):
    """rgba: HxWx4 uint8, sides multiples of 4. Returns little-endian DXT5 blocks
    in row-major block order (16 bytes each)."""
    h, w = rgba.shape[:2]
    px = rgba.astype(np.float32).reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4)
    n = len(px)
    out = np.zeros((n, 16), np.uint8)

    # Alpha: a0 = max > a1 = min selects the 8-value ramp.
    a = px[:, :, 3]
    a0 = np.round(a.max(1)).astype(np.int32)
    a1 = np.round(a.min(1)).astype(np.int32)
    flat = a0 == a1
    a0 = np.where(flat & (a0 < 255), a0 + 1, a0)            # keep a0 > a1 so the 8-step ramp is used
    a1 = np.where(flat & (a0 == a1), a1 - 1, a1)
    ramp = np.stack([a0, a1] + [((7 - i) * a0 + i * a1) / 7.0 for i in range(1, 7)], 1)
    aidx = np.abs(a[:, :, None] - ramp[:, None, :]).argmin(2).astype(np.uint64)
    abits = np.zeros(n, np.uint64)
    for i in range(16):
        abits |= aidx[:, i] << np.uint64(3 * i)
    out[:, 0] = a0
    out[:, 1] = a1
    for i in range(6):
        out[:, 2 + i] = ((abits >> np.uint64(8 * i)) & np.uint64(0xFF)).astype(np.uint8)

    # Colour: endpoints along the block's principal axis (better than a bounding box).
    rgb = px[:, :, :3]
    mean = rgb.mean(1, keepdims=True)
    centered = rgb - mean
    cov = np.einsum('nki,nkj->nij', centered, centered)
    axis = np.ones((n, 3), np.float32)
    for _ in range(8):                                        # power iteration
        axis = np.einsum('nij,nj->ni', cov, axis)
        norm = np.linalg.norm(axis, axis=1, keepdims=True)
        axis = np.where(norm > 1e-6, axis / np.maximum(norm, 1e-6), np.array([[0.577, 0.577, 0.577]], np.float32))
    proj = np.einsum('nki,ni->nk', centered, axis)
    hi = mean[:, 0] + axis * proj.max(1, keepdims=True)
    lo = mean[:, 0] + axis * proj.min(1, keepdims=True)
    c0 = _to565(hi)
    c1 = _to565(lo)
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    p0, p1 = _from565(c0), _from565(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)
    cidx = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(3).argmin(2).astype(np.uint32)
    cidx = np.where((c0 == c1)[:, None], 0, cidx)
    cbits = np.zeros(n, np.uint32)
    for i in range(16):
        cbits |= cidx[:, i] << np.uint32(2 * i)
    out[:, 8] = c0 & 0xFF
    out[:, 9] = c0 >> 8
    out[:, 10] = c1 & 0xFF
    out[:, 11] = c1 >> 8
    for i in range(4):
        out[:, 12 + i] = (cbits >> np.uint32(8 * i)) & 0xFF
    return out.tobytes()


def swap16(data):
    return np.frombuffer(data, np.uint8).reshape(-1, 2)[:, ::-1].tobytes()


# ---------------------------------------------------------------- asset files
def build_texture(img, slot):
    w, h = SIZES[slot]
    img = img.convert('RGBA')
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    pw, ph = pad128(w), pad128(h)
    canvas = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    data = swap16(encode_dxt5(np.asarray(canvas)))

    fetch = [
        (pw // 32) << 22 | 2,                    # pitch in 32-texel units, fetch type: texture
        ENDIAN_8IN16 << 6 | FMT_DXT4_5,          # base address 0, 8-in-16, DXT4_5
        (h - 1) << 13 | (w - 1),                 # 2D size
        0xD10,                                   # swizzle XYZW, default filters
        0,
        0xA00,                                   # 2D, packed mips
    ]
    header = struct.pack('>13I', 3, 1, 0, 0, 0, 0xFFFF0000, 0xFFFF0000, *fetch)
    return header, data


def build_asset(images):
    """images: {slot: PIL.Image}. Returns the .asset file's bytes."""
    table, blobs, offset, flags = [], [], 0, 0
    for slot in range(ENTRIES):
        if slot in images:
            header, data = build_texture(images[slot], slot)
            table.append(struct.pack('>3I', offset, len(data), 0) + header)
            blobs.append(data)
            offset += len(data)
            flags |= 1 << slot
        else:
            table.append(bytes(64))
    head = struct.pack('>4sIIII', b'RXEA', 1, offset, flags, 0) + b''.join(table)
    assert len(head) <= HEADER_SIZE
    return head + bytes(HEADER_SIZE - len(head)) + b''.join(blobs)


# ---------------------------------------------------- independent read-back
def decode_dxt5_block(b):
    a0, a1 = b[0], b[1]
    ramp = [a0, a1] + ([((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)] if a0 > a1
                       else [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255])
    abits = int.from_bytes(b[2:8], 'little')
    c0, c1 = struct.unpack('<HH', b[8:12])
    def rgb(c):
        r, g, bb = (c >> 11) & 31, (c >> 5) & 63, c & 31
        return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (bb << 3) | (bb >> 2))
    p0, p1 = rgb(c0), rgb(c1)
    pal = [p0, p1, tuple((2 * x + y) // 3 for x, y in zip(p0, p1)), tuple((x + 2 * y) // 3 for x, y in zip(p0, p1))]
    cbits = struct.unpack('<I', b[12:16])[0]
    return [pal[(cbits >> (2 * i)) & 3] + (ramp[(abits >> (3 * i)) & 7],) for i in range(16)]


def read_asset(data):
    """Decodes every texture in an .asset file -> {slot: PIL image}."""
    magic, version, length, flags, shots = struct.unpack('>4sIIII', data[:20])
    assert magic == b'RXEA' and version == 1, 'bad header'
    assert len(data) == HEADER_SIZE + length, 'length mismatch'
    result = {}
    for slot in range(ENTRIES):
        if not flags & (1 << slot):
            continue
        at = 20 + slot * 64
        off, size, _ = struct.unpack('>3I', data[at:at + 12])
        d = struct.unpack('>13I', data[at + 12:at + 64])
        f0, f1, f2 = d[7], d[8], d[9]
        assert f1 & 0x3F == FMT_DXT4_5 and (f1 >> 6) & 3 == ENDIAN_8IN16 and f0 >> 31 == 0
        w, h = (f2 & 0x1FFF) + 1, ((f2 >> 13) & 0x1FFF) + 1
        pitch = ((f0 >> 22) & 0x1FF) * 32
        raw = swap16(data[HEADER_SIZE + off:HEADER_SIZE + off + size])
        bw = pitch // 4
        img = np.zeros((h, w, 4), np.uint8)
        for by in range((h + 3) // 4):
            for bx in range((w + 3) // 4):
                n = (by * bw + bx) * 16
                for i, p in enumerate(decode_dxt5_block(raw[n:n + 16])):
                    x, y = bx * 4 + i % 4, by * 4 + i // 4
                    if x < w and y < h:
                        img[y, x] = p
        result[slot] = Image.fromarray(img, 'RGBA')
    return result


def psnr(a, b):
    a = np.asarray(a.convert('RGB'), np.float64)
    b = np.asarray(b.convert('RGB'), np.float64)
    mse = ((a - b) ** 2).mean()
    return 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)


def main():
    argv = [a for a in sys.argv[1:] if a != '--check']
    check = '--check' in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    art = os.path.normpath(os.path.join(here, '..', 'art'))
    tid = (argv[0] if argv else 'FFFF584E').upper()
    outdir = argv[1] if len(argv) > 1 else art

    files = {
        'GC': {BOXART: 'cover.png'},
        'BK': {BACKGROUND: 'background.png'},
        'GL': {ICON: 'icon.png', BANNER: 'banner.png'},
    }
    for prefix, slots in files.items():
        images = {slot: Image.open(os.path.join(art, name)) for slot, name in slots.items()}
        data = build_asset(images)
        path = os.path.join(outdir, f'{prefix}{tid}.asset')
        with open(path, 'wb') as f:
            f.write(data)
        line = f'{os.path.basename(path)}: {len(data)} bytes'
        if check:
            back = read_asset(data)
            for slot, img in images.items():
                src = img.convert('RGBA').resize(SIZES[slot], Image.LANCZOS) if img.size != SIZES[slot] else img
                line += f'  slot {slot} {back[slot].size} PSNR {psnr(src, back[slot]):.1f} dB'
                back[slot].save(os.path.join(outdir, f'_check_{prefix}_{slot}.png'))
        print(line)


if __name__ == '__main__':
    main()
