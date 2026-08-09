#!/usr/bin/env python3
"""Genererar assets/mattisclicker.png (appikon)."""
import os
import struct
import zlib

SIZE = 512
MARGIN = 24
RADIUS = 72
BG = (46, 52, 64, 255)
SHADOW = (40, 46, 58, 255)
MOUSE_COLOR = (148, 189, 240, 255)
DIVIDER = (26, 32, 44, 255)
CLICK_COLOR = (163, 230, 121, 255)
CLICK_DARK = (255, 255, 255, 255)
RING = (255, 255, 255, 255)

img = [[(0, 0, 0, 0) for _ in range(SIZE)] for _ in range(SIZE)]


def in_rounded_rect(x, y, x0, y0, x1, y1, r):
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cx = max(x0 + r, min(x, x1 - r))
    cy = max(y0 + r, min(y, y1 - r))
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def circle(cx, cy, r):
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            if 0 <= x < SIZE and 0 <= y < SIZE and (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                yield x, y


def draw_round_rect(x0, y0, x1, y1, r, color):
    for y in range(int(y0), int(y1) + 1):
        for x in range(int(x0), int(x1) + 1):
            if in_rounded_rect(x, y, x0, y0, x1, y1, r):
                img[y][x] = color


def draw_circle(cx, cy, r, color):
    for x, y in circle(cx, cy, r):
        img[y][x] = color


def draw_ring(cx, cy, r, width, color):
    for x, y in circle(cx, cy, r + width):
        d = (x - cx) ** 2 + (y - cy) ** 2
        if (r - width) ** 2 <= d <= (r + width) ** 2:
            img[y][x] = color


draw_round_rect(MARGIN, MARGIN, SIZE - 1 - MARGIN, SIZE - 1 - MARGIN, RADIUS, BG)

mx0, my0, mx1, my1 = 130, 150, 440, 380
draw_round_rect(mx0 + 14, my0 + 14, mx1 + 14, my1 + 14, 46, SHADOW)
draw_round_rect(mx0, my0, mx1, my1 - 45, 46, MOUSE_COLOR)
draw_round_rect(mx0, my0 + 45, mx1, my1, 46, MOUSE_COLOR)
for x, y in circle(int((mx0 + mx1) / 2), my0 + 6, 4):
    img[y][x] = DIVIDER

for x, y in circle(400, 120, 80):
    if (x - 400) ** 2 + (y - 120) ** 2 <= 65 ** 2:
        img[y][x] = CLICK_COLOR
draw_ring(400, 120, 68, 12, RING)
draw_circle(400, 120, 22, CLICK_DARK)

raw = b""
for y in range(SIZE):
    raw += b"\x00" + b"".join(struct.pack("BBBB", *img[y][x]) for x in range(SIZE))


def chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(raw, 9))
    + chunk(b"IEND", b"")
)

base = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(base, "assets"), exist_ok=True)
out = os.path.join(base, "assets", "mattisclicker.png")
with open(out, "wb") as f:
    f.write(png)
print(f"Skapade {out}")