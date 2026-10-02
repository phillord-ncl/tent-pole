"""Generates test-image.png: a small synthetic checkerboard, purely so the
image-feature test doesn't need a real (and possibly copyrighted) asset
checked into the repo. No third-party dependencies -- just struct/zlib."""
import struct
import zlib


def chunk(tag, data):
    c = tag + data
    return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))


def main():
    width, height = 64, 64
    rows = []
    for y in range(height):
        row = bytearray([0])  # filter type 0
        for x in range(width):
            if (x // 8 + y // 8) % 2 == 0:
                r, g, b = 230, 126, 34  # orange
            else:
                r, g, b = 41, 128, 185  # blue
            row += bytes([r, g, b])
        rows.append(bytes(row))
    raw = b"".join(rows)
    compressed = zlib.compress(raw, 9)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")

    with open("test-image.png", "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
