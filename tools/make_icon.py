#!/usr/bin/env python3
# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Draw the application icon: the initial, in black, on white.

One letter, a serif face, a thin frame. The products share this drawing and
differ only in the letter — Orion has an O, this one has a P — so a taskbar
with several of them open reads as one family rather than unrelated programs.
This script is deliberately the same script, kept in step with Orion's rather
than reinvented.

The face is Liberation Serif, metric-compatible with Times New Roman and
redistributable; Times New Roman itself is neither free nor present on the
machines that build these. The output is committed rather than generated at
build time, so no release depends on which fonts a runner happens to have —
nor, for the .icns, on whether Pillow is installed where the bundle is built,
which is the difference between a macOS build that finishes and one that dies
on the last line of the spec.

Every size is drawn for itself rather than scaled down from one master. A
frame that reads as a hairline at 256 pixels is a smear at 16, and the letter
that has room to breathe at 256 has to fill the square at 16 to be a letter at
all.

The .ico is assembled here rather than by Pillow, for one reason: which
compression each frame uses. Pillow writes every frame as PNG. Windows has
accepted PNG frames since Vista, but the format every icon editor produces,
and the one the shell has always read, is an uncompressed DIB below 256 pixels
and PNG only for the 256. Explorer showing a stale or generic icon for an
executable whose resources are demonstrably correct is exactly the shape of
problem that convention exists to avoid.
"""

import io
import pathlib
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

#: Every size Windows asks for. 256 is also what macOS and Linux use.
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZE = 512

#: Each size is drawn this much larger and then reduced, so the edges are
#: antialiased rather than aliased into the few pixels available.
SUPERSAMPLE = 8

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSerif-Regular.ttf",
    "C:/Windows/Fonts/times.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
)

BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if pathlib.Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("no serif font found; install fonts-liberation and retry")


def _frame_width(target: int) -> int:
    """In target pixels, and never zero.

    One shape at every size: the products draw their window icon from
    different sources, so a rule that changed the drawing with the size would
    make one product look like two.
    """
    return max(1, round(target / 28))


def _letter_height(target: int) -> float:
    """As a fraction of the square.

    The smaller the icon, the more of it the letter has to be before it stops
    reading as a letter — but it shares the square with a frame at every size,
    so there is a little less of it to have.
    """
    if target < 32:
        return 0.66
    if target <= 48:
        return 0.68
    return 0.62


def draw(letter: str, target: int) -> Image.Image:
    canvas = target * SUPERSAMPLE
    image = Image.new("RGBA", (canvas, canvas), WHITE)
    pen = ImageDraw.Draw(image)

    frame = _frame_width(target) * SUPERSAMPLE
    if frame:
        pen.rectangle((0, 0, canvas - 1, canvas - 1), outline=BLACK, width=frame)

    # Sized and centred on the ink, not on the font's metrics: a serif capital
    # sits well off-centre inside its own advance box, and centring on that
    # puts it visibly low and to the left.
    wanted = canvas * _letter_height(target)
    font = _font(int(wanted))
    left, top, right, bottom = pen.textbbox((0, 0), letter, font=font)
    if bottom - top:
        font = _font(max(1, int(wanted * wanted / (bottom - top))))
        left, top, right, bottom = pen.textbbox((0, 0), letter, font=font)

    pen.text(
        ((canvas - (right - left)) / 2 - left,
         (canvas - (bottom - top)) / 2 - top),
        letter,
        font=font,
        fill=BLACK,
    )
    return image.resize((target, target), Image.LANCZOS)


def _dib_frame(image: Image.Image) -> bytes:
    """One icon frame in the uncompressed form Windows has always read.

    A BITMAPINFOHEADER whose height is doubled — the convention that says
    "colour rows, then mask rows" — followed by bottom-up BGRA pixels and a
    1-bit AND mask. The mask is all zeroes because these icons are fully
    opaque; it is written out anyway rather than left off, because a header
    that promises mask rows and a frame that does not carry them is the kind
    of nearly-valid file that works in one reader and not the next.
    """
    width, height = image.size
    pixels = image.convert("RGBA").tobytes()

    rows = []
    for y in range(height - 1, -1, -1):          # bottom-up
        row = bytearray()
        for x in range(width):
            r, g, b, a = pixels[(y * width + x) * 4 : (y * width + x) * 4 + 4]
            row += bytes((b, g, r, a))           # BGRA, not RGBA
        rows.append(bytes(row))
    xor = b"".join(rows)

    mask_stride = ((width + 31) // 32) * 4       # rows padded to 4 bytes
    and_mask = b"\x00" * (mask_stride * height)

    header = struct.pack(
        "<IiiHHIIiiII",
        40,              # biSize
        width,
        height * 2,      # colour rows plus mask rows
        1,               # biPlanes
        32,              # biBitCount
        0,               # biCompression: BI_RGB
        len(xor) + len(and_mask),
        0, 0, 0, 0,      # resolution and palette counts
    )
    return header + xor + and_mask


def build_ico(frames: dict[int, Image.Image]) -> bytes:
    """Assemble the .ico: DIB below 256 pixels, PNG for the 256."""
    payloads = []
    for size in sorted(frames):
        if size >= 256:
            buffer = io.BytesIO()
            frames[size].save(buffer, "png")
            payloads.append((size, buffer.getvalue(), True))
        else:
            payloads.append((size, _dib_frame(frames[size]), False))

    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = len(header) + 16 * len(payloads)
    directory, data = b"", b""
    for size, blob, _is_png in payloads:
        directory += struct.pack(
            "<BBBBHHII",
            0 if size >= 256 else size,   # 0 means 256
            0 if size >= 256 else size,
            0,           # no palette
            0,           # reserved
            1,           # planes
            32,          # bits per pixel
            len(blob),
            offset,
        )
        data += blob
        offset += len(blob)
    return header + directory + data


#: The ``.icns`` entries macOS reads, as (four-character type, pixel size).
#:
#: Each is a PNG, which every macOS since 10.7 accepts and which keeps the file
#: a tenth the size of the old raw-ARGB-plus-mask encoding. The pairs are the
#: retina ones: ``ic11`` is 16pt at 2x and ``ic12`` is 32pt at 2x, so a Finder
#: showing 16-point icons on a retina display has a real 32-pixel drawing to
#: use instead of a scaled 16.
ICNS_TYPES = (
    (b"icp4", 16),
    (b"icp5", 32),
    (b"ic11", 32),
    (b"ic12", 64),
    (b"ic07", 128),
    (b"ic13", 256),
    (b"ic08", 256),
    (b"ic14", 512),
    (b"ic09", 512),
)


def build_icns(letter: str) -> bytes:
    """Assemble the ``.icns`` macOS wants for an application bundle.

    Written out here rather than left to PyInstaller, which converts a PNG on
    the fly only when Pillow happens to be installed in the build environment
    — and dies at BUNDLE() with "not in the correct format" when it is not,
    after the whole build has succeeded. An icon committed as a file cannot
    fail that way.
    """
    chunks = b""
    for kind, size in ICNS_TYPES:
        buffer = io.BytesIO()
        draw(letter, size).save(buffer, "png")
        blob = buffer.getvalue()
        chunks += kind + struct.pack(">I", len(blob) + 8) + blob
    return b"icns" + struct.pack(">I", len(chunks) + 8) + chunks


def write_icons(letter: str, out: pathlib.Path, stem: str) -> None:
    """Write the three files a release needs, drawn from one letter."""
    out.mkdir(parents=True, exist_ok=True)
    draw(letter, PNG_SIZE).save(out / f"{stem}.png")
    frames = {size: draw(letter, size) for size in ICO_SIZES}
    (out / f"{stem}.ico").write_bytes(build_ico(frames))
    (out / f"{stem}.icns").write_bytes(build_icns(letter))


def main(argv: list[str]) -> int:
    if not 3 <= len(argv) <= 4:
        print(
            "usage: make_icon.py <Name> <output directory> [file stem]\n"
            "  Name       the product; its initial is the letter drawn\n"
            "  file stem  what the three files are called, when that is not\n"
            "             the product name in lower case",
            file=sys.stderr,
        )
        return 2

    name, out = argv[1], pathlib.Path(argv[2])
    # The letter and the file name are separate arguments because here they
    # are separate things: the icon is a P and the files are called
    # p7mmanager. Deriving both from one argument would mean the only way to
    # get the file name right is to pass the wrong letter.
    stem = argv[3] if len(argv) == 4 else name.lower()
    letter = name[0].upper()
    write_icons(letter, out, stem)
    print(f"{name}: wrote {stem}.png, {stem}.ico and {stem}.icns in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
