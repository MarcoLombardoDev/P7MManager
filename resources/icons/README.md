# Application icon

| File | What it is |
|---|---|
| `p7mmanager.png` | 512×512, used for the window and taskbar icon at runtime, and for the executable everywhere except Windows and macOS |
| `p7mmanager.ico` | 16 to 256 pixels, seven sizes, embedded in the Windows executable and used by Explorer and the taskbar |
| `p7mmanager.icns` | nine entries, 16 to 512 pixels including the retina pairs, used for the macOS application bundle |

All three are drawn by [`tools/make_icon.py`](../../tools/make_icon.py) — the
initial in black on white, in Liberation Serif, which is metric-compatible with
Times New Roman and redistributable. The sibling products share that script and
differ only in the letter: Orion has an `O`, this one has a `P`, so a taskbar
with both open reads as one family.

They are committed rather than generated during the build, so no release
depends on which fonts a runner happens to have installed — nor, for the
`.icns`, on whether Pillow happens to be installed, which is the difference
between a macOS bundle that builds and one that dies on the last line of the
spec.

```sh
python tools/make_icon.py "P7M Manager" resources/icons p7mmanager
```

The first argument gives the letter drawn; the third gives the file name,
because here the two differ.

A test regenerates the icons and compares them against the committed files, so
"run it again and diff" is an answer that can be trusted.

Every size is drawn for itself rather than scaled down from one master: a frame
that reads as a hairline at 256 pixels is a smear at 16, and the letter that
has room to breathe at 256 has to fill the square at 16 to still be a letter.
