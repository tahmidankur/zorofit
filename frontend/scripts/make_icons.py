"""Draw the app icons (a dumbbell on the accent green) as PNGs with no image library.

Usage: python3 scripts/make_icons.py   (writes into public/icons/)
"""

import struct
import zlib
from pathlib import Path

GREEN = (0x2E, 0x7D, 0x4F)
OFF_WHITE = (0xF7, 0xF6, 0xF2)
SAMPLES = 4

# The mark in a 0..1 box: bar, inner plates, outer plates (x0, y0, x1, y1).
MARK = [
    (0.20, 0.465, 0.80, 0.535),
    (0.26, 0.33, 0.34, 0.67),
    (0.66, 0.33, 0.74, 0.67),
    (0.18, 0.39, 0.25, 0.61),
    (0.75, 0.39, 0.82, 0.61),
]


def in_rounded_square(x: float, y: float, radius: float) -> bool:
    cx = min(max(x, radius), 1 - radius)
    cy = min(max(y, radius), 1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def in_mark(x: float, y: float, scale: float) -> bool:
    # Scale the mark around the centre so maskable icons keep it inside the safe zone.
    mx = 0.5 + (x - 0.5) / scale
    my = 0.5 + (y - 0.5) / scale
    return any(x0 <= mx <= x1 and y0 <= my <= y1 for x0, y0, x1, y1 in MARK)


def render(size: int, corner_radius: float, mark_scale: float) -> bytes:
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            bg = mark = 0
            for sy in range(SAMPLES):
                for sx in range(SAMPLES):
                    x = (px + (sx + 0.5) / SAMPLES) / size
                    y = (py + (sy + 0.5) / SAMPLES) / size
                    if corner_radius == 0 or in_rounded_square(x, y, corner_radius):
                        bg += 1
                        if in_mark(x, y, mark_scale):
                            mark += 1
            total = SAMPLES * SAMPLES
            alpha = bg / total
            share = mark / bg if bg else 0
            color = [round(g + (w - g) * share) for g, w in zip(GREEN, OFF_WHITE)]
            row += bytes(color + [round(alpha * 255)])
        rows.append(bytes(row))
    return png(size, b"".join(rows))


def png(size: int, raw: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "public" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    icons = {
        "icon-192.png": (192, 0.22, 1.0),
        "icon-512.png": (512, 0.22, 1.0),
        "maskable-512.png": (512, 0, 0.78),
        "apple-touch-icon.png": (180, 0, 0.9),
    }
    for name, (size, radius, scale) in icons.items():
        (out / name).write_bytes(render(size, radius, scale))
        print(f"wrote {name}")
