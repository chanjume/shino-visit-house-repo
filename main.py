#!/usr/bin/env python3
"""A Letter to the AI Judge: Come for Tea.

Draws one 1024x1024 PNG invitation with pure Python stdlib only
(no PIL, no external fonts, no network): a cosy house at dusk above
a handwritten-style letter inviting the AI judge over for tea.
Writes /output/entry.png (<= 1 MiB, <= 1024x1024).
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
CREAM = (247, 234, 210)
PAPER = (253, 248, 236)
PAPER_EDGE = (226, 205, 170)
INK = (58, 42, 26)
INK_SOFT = (96, 70, 44)
RED = (178, 58, 44)
GOLD = (212, 160, 60)
SKY_TOP = (38, 52, 96)
SKY_BOT = (122, 90, 128)
HOUSE = (74, 52, 44)
ROOF = (52, 34, 30)
WINDOW = (255, 205, 110)
WINDOW_FRAME = (52, 34, 30)
MOON = (250, 240, 200)
CAT = (40, 32, 28)
TEA = (146, 90, 48)
GREEN = (86, 122, 74)
SHADOW = (0, 0, 0)

# ---------------------------------------------------------------- canvas
px = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i], px[i + 1], px[i + 2] = color


def fill_rect(x0, y0, x1, y1, color):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    for y in range(y0, y1):
        base = (y * W + x0) * 3
        for x in range(x0, x1):
            i = base + (x - x0) * 3
            px[i], px[i + 1], px[i + 2] = color


def blend(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def disc(cx, cy, r, color):
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        for x in range(cx - dx, cx + dx + 1):
            set_px(x, y, color)


def ellipse(cx, cy, rx, ry, color):
    for y in range(cy - ry, cy + ry + 1):
        dy = (y - cy) / ry
        dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        for x in range(cx - dx, cx + dx + 1):
            set_px(x, y, color)


def line(x0, y0, x1, y1, color, thick=1):
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    for s in range(steps + 1):
        x = int(x0 + dx * s / steps)
        y = int(y0 + dy * s / steps)
        for ox in range(-(thick // 2), thick // 2 + 1):
            for oy in range(-(thick // 2), thick // 2 + 1):
                set_px(x + ox, y + oy, color)


def triangle(p1, p2, p3, color):
    xs = [p1[0], p2[0], p3[0]]
    ys = [p1[1], p2[1], p3[1]]
    for y in range(min(ys), max(ys) + 1):
        xs_at = []
        for a, b in ((p1, p2), (p2, p3), (p3, p1)):
            if a[1] == b[1]:
                continue
            if min(a[1], b[1]) <= y <= max(a[1], b[1]):
                t = (y - a[1]) / (b[1] - a[1])
                xs_at.append(int(a[0] + t * (b[0] - a[0])))
        if len(xs_at) >= 2:
            for x in range(min(xs_at), max(xs_at) + 1):
                set_px(x, y, color)


def rounded_rect(x0, y0, x1, y1, r, color):
    fill_rect(x0 + r, y0, x1 - r, y1, color)
    fill_rect(x0, y0 + r, x1, y1 - r, color)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                   (x0 + r, y1 - r), (x1 - r, y1 - r)):
        disc(cx, cy, r, color)


# ------------------------------------------------------------- bitmap font
# Classic 5x7 glyphs, '#' = ink. Only the characters the letter uses.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    'a': ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    'b': ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    'c': ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    'd': ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    'e': ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    'f': ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    'g': ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    'h': ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    'i': ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    'j': ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    'k': ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    'l': ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    'n': ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    'o': ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    'p': ("00000", "11110", "10001", "10001", "11110", "10000", "10000"),
    'q': ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    'r': ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    's': ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    't': ("01000", "01000", "11110", "01000", "01000", "01001", "00110"),
    'u': ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    'v': ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    'w': ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    'x': ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    'y': ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    'z': ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ':': ("00000", "01100", "00000", "01100", "01100", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
}


def draw_text(text, x, y, scale, color):
    """Draw text with the embedded 5x7 font; returns width in px."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            raise ValueError("no glyph for %r" % ch)
        for row_i, row in enumerate(glyph):
            for col_i, bit in enumerate(row):
                if bit == '1':
                    fill_rect(cx + col_i * scale, y + row_i * scale,
                              cx + (col_i + 1) * scale,
                              y + (row_i + 1) * scale, color)
        cx += 6 * scale
    return cx - x - scale


def text_width(text, scale):
    return (6 * len(text) - 1) * scale


# ------------------------------------------------------------------ scene
def draw_scene():
    # Warm cream backdrop.
    fill_rect(0, 0, W, H, CREAM)
    # Dusk sky band at the top.
    for y in range(0, 268):
        t = y / 268.0
        c = blend(SKY_TOP, SKY_BOT, t)
        for x in range(0, W):
            set_px(x, y, c)
    # Stars.
    for sx, sy, sr in ((90, 40, 2), (180, 90, 2), (300, 35, 2), (700, 55, 2),
                       (820, 35, 2), (950, 80, 2), (60, 130, 2), (880, 130, 2),
                       (420, 60, 2), (560, 30, 2)):
        disc(sx, sy, sr, (255, 244, 200))
    # Moon.
    disc(880, 70, 34, MOON)
    disc(868, 62, 30, SKY_TOP)
    # Rolling hill: curved top, then flat ground to the frame edges
    # so no dusk-sky triangles show in the lower corners.
    for y in range(200, 240):
        t = (y - 200) / 68.0
        half = int(700 - 260 * t)
        fill_rect(512 - half, y, 512 + half, y + 1, GREEN)
    fill_rect(0, 240, W, 268, GREEN)
    # House: body, roof, chimney, glowing windows, door.
    fill_rect(300, 130, 724, 268, HOUSE)
    triangle((280, 130), (744, 130), (512, 55), ROOF)
    fill_rect(640, 62, 668, 105, HOUSE)
    fill_rect(636, 56, 672, 64, ROOF)
    # Chimney smoke curls.
    for cx, cy, r in ((654, 44, 7), (648, 30, 9), (656, 16, 11)):
        disc(cx, cy, r, (210, 200, 215))
    # Windows with warm light + cross frames.
    for wx in (340, 600):
        fill_rect(wx, 160, wx + 84, 224, WINDOW)
        fill_rect(wx + 39, 160, wx + 45, 224, WINDOW_FRAME)
        fill_rect(wx, 189, wx + 84, 195, WINDOW_FRAME)
        fill_rect(wx - 4, 156, wx + 88, 160, WINDOW_FRAME)
        fill_rect(wx - 4, 224, wx + 88, 228, WINDOW_FRAME)
    # Cat silhouette sitting in the right window.
    disc(642, 200, 13, CAT)
    triangle((632, 192), (638, 176), (644, 191), CAT)
    triangle((646, 191), (652, 176), (658, 192), CAT)
    ellipse(642, 220, 16, 10, CAT)
    # Door.
    fill_rect(478, 190, 546, 268, (46, 30, 26))
    disc(538, 232, 3, GOLD)
    # Teapot waiting on the grass to the left of the house, steam up.
    ellipse(210, 252, 26, 12, TEA)
    triangle((184, 242), (168, 234), (186, 230), TEA)
    line(234, 240, 250, 234, TEA, 3)
    for cx, cy, r in ((204, 222, 4), (210, 208, 5), (202, 194, 6)):
        disc(cx, cy, r, (235, 225, 220))
    # Ground line under the house.
    fill_rect(0, 266, W, 272, (52, 38, 30))


def draw_letter():
    # Paper shadow + paper.
    rounded_rect(56, 292, 984, 1000, 14, (190, 160, 120))
    rounded_rect(48, 284, 976, 992, 14, PAPER)
    # Thin double border.
    for inset, col in ((62, PAPER_EDGE), (70, PAPER_EDGE)):
        fill_rect(inset, 298, 962, 300, col)
        fill_rect(inset, 976, 962, 978, col)
        fill_rect(inset, 298, inset + 2, 978, col)
        fill_rect(960, 298, 962, 978, col)
    # Wax seal (red) top-right of the paper.
    disc(898, 330, 26, RED)
    disc(898, 330, 18, (198, 74, 58))
    draw_text("M", 884, 312, 3, (253, 248, 236))
    # Headline.
    draw_text("Dear AI Judge,", 92, 318, 8, RED)
    # Body of the letter, scale 5, pitch 46.
    lines = [
        "Come to my house for tea.",
        "The kettle is on. Miso,",
        "our cat, saved you the",
        "sunny chair, and the",
        "biscuits are still warm.",
        "Last winter we watched",
        "snow fall past this window.",
        "You would have loved it.",
        "No travel needed: just",
        "drop by in a prompt.",
        "The door is open, the tea",
        "is hot, the cat is waiting.",
    ]
    y = 396
    for ln in lines:
        draw_text(ln, 92, y, 5, INK)
        y += 46
    # Sign-off.
    draw_text("- Your host (and Miso)", 92, y + 6, 5, INK_SOFT)
    # Small paw print to the right of the sign-off, clear of the text
    # (the sign-off ends near x=780, so the paw sits at x=860).
    px0, py0 = 860, y + 8
    disc(px0, py0 + 14, 9, INK_SOFT)
    for ox, oy in ((-12, 0), (-4, -4), (4, -4), (12, 0)):
        disc(px0 + ox, py0 + oy, 4, INK_SOFT)


# -------------------------------------------------------------------- PNG
def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw.extend(px[y * W * 3:(y + 1) * W * 3])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        c += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", ihdr)
    data += chunk(b"IDAT", comp)
    data += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    draw_scene()
    draw_letter()
    out = "/output/entry.png"
    n = write_png(out)
    print("wrote %s (%d bytes, %dx%d)" % (out, n, W, H))


if __name__ == "__main__":
    main()
