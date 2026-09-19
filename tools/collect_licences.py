#!/usr/bin/env python
# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Assemble the licence texts that must travel inside a release archive.

A PyInstaller bundle is a redistribution of every library inside it, and most
of those libraries ask for something in return: LGPL-3.0 §4 requires a copy of
the licence to accompany the object code, and the BSD and MIT notices require
their copyright lines be reproduced in binary distributions. Shipping the
libraries with none of their terms attached is a straightforward compliance
defect, and THIRD-PARTY-LICENSES.md sitting in the repository does not fix it —
someone who downloads a zip never sees it.

So P7M Manager.spec calls this before COLLECT, and the resulting tree is added to the
bundle as ``licenses/``.

Three sources feed it, in descending order of authority:

1. **The distributions themselves.** Most wheels ship their licence in
   dist-info, and that copy is the one their authors chose to send.

2. **Canonical texts vendored in ``licenses/``** for the distributions that
   ship none. PySide6 is the important one — the wheels declare LGPL-3.0 in
   their metadata and then include no licence file at all, so there is nothing
   to copy forward and the text has to come from somewhere. LGPL-3.0 is also
   not self-contained: it is a set of additional permissions on top of GPL-3.0,
   so shipping it alone would be shipping half a licence. Both go.

3. **The build machine's package copyright records**, on Linux, for the
   libraries PyInstaller collected from the system. These vary with the runner
   image, which is exactly why they are read at build time rather than
   committed.

What this script does *not* do is decide anything. It copies texts and records
where each came from. The analysis of what those texts require lives in
THIRD-PARTY-LICENSES.md, and the reader of a bundle gets pointed at both.

**What makes this one matter more than its counterparts elsewhere.** P7M
Manager declares a single runtime dependency, PySide6, because the engine under
``p7mmanager/core/`` is written against the standard library. So the whole
third-party surface of a build is Qt — and Qt is LGPL-3.0, not the BSD and MIT
of the other products. LGPL-3.0 §4 asks for the licence text to accompany the
object code, in as many words, and LGPL-3.0 is not self-contained: it is a set
of additional permissions on top of GPL-3.0, so shipping it alone would be
shipping half a licence. Both texts travel, from ``licenses/``, because the
PySide6 wheels declare LGPL-3.0 in their metadata and then include no licence
file at all — there is nothing to copy forward.

Until this existed, an archive carried P7M Manager's own LICENSE,
COMMERCIAL-LICENSE.md, README and CHANGELOG, and not one line of Qt's.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys

log = logging.getLogger(__name__)

#: Distributions whose wheels ship no licence file, mapped to the canonical
#: texts that have to be supplied on their behalf. Qt's entry carries two
#: files on purpose: LGPL-3.0 is a supplement to GPL-3.0 and means nothing
#: without it.
SUPPLIED_TEXTS = {
    "PySide6": ("LGPL-3.0.txt", "GPL-3.0.txt"),
    "PySide6_Essentials": ("LGPL-3.0.txt", "GPL-3.0.txt"),
    "PySide6_Addons": ("LGPL-3.0.txt", "GPL-3.0.txt"),
    "shiboken6": ("LGPL-3.0.txt", "GPL-3.0.txt"),
}

#: Texts that belong in every archive and that no distribution owns. The
#: interpreter and its standard library are frozen into this bundle and PSF-2.0
#: asks for its notice to be retained, but CPython is not a wheel, so nothing
#: in the loop below would ever find it: reading installed metadata can only
#: see what pip installed.
#:
#: The folder is `cpython/` and not `python/` because `python/` is where the
#: wheels go, and the two collided.
ALWAYS_SUPPLIED = (
    ("cpython", "Python-LICENSE.txt", "CPython — the interpreter and standard library"),
)

#: Runtime distributions, in the order a reader should meet them. Build-time
#: tools are deliberately absent: they are not in the archive, so their terms
#: do not belong in it. PyInstaller is the exception discussed in
#: THIRD-PARTY-LICENSES.md — its bootloader *is* shipped, under an exception
#: that permits exactly that, so its COPYING.txt comes along.
RUNTIME_DISTRIBUTIONS = (
    "PySide6",
    "PySide6_Essentials",
    "PySide6_Addons",
    "shiboken6",
    "pyinstaller",
)

#: A licence file is usually *named* like one...
LICENCE_FILE = re.compile(r"(?i)^(licen[cs]e|copying|notice|authors|thirdparty)")

#: ...or named after what it covers, with the word appended —
#: ``webp_codec.LICENSE``, ``utilsBundle.js.LICENSE``. Matching only on the
#: start of a name collects none of those, silently, which is precisely the
#: failure this script exists to prevent.
LICENCE_SUFFIX = re.compile(r"(?i)\.(licen[cs]e|notice)(\.txt|\.md)?$")

#: ...and sometimes it is neither, but it sits in a directory that announces
#: itself as licences. Wheels vendoring several projects do this.
LICENCE_DIRECTORY = re.compile(r"(?i)^(licen[cs]es?|build_licenses)$")


def _is_licence(parts: list[str]) -> bool:
    """Does this path, split on ``/``, point at a licence text?"""
    name = parts[-1]
    named = LICENCE_FILE.match(name) or LICENCE_SUFFIX.search(name)
    housed = any(LICENCE_DIRECTORY.match(part) for part in parts[:-1])
    return bool(named or housed)


def _distribution_licence_files(name: str) -> list[tuple[str, str]]:
    """Return ``(relative path, text)`` for every licence file a wheel ships.

    Both halves of a wheel are searched: the dist-info directory, where the
    convention puts them, and the installed package itself, where some wheels
    keep the ones that matter as package data instead.

    The path is kept relative rather than reduced to a bare file name. Wheels
    put licence files in several places at once — ``LICENSE`` beside METADATA
    and ``licenses/LICENSE`` below it — and writing by base name would have
    each overwrite the last and leave a tree that looks complete and is not,
    which is the one failure this script exists to prevent.
    """
    try:
        from importlib.metadata import distribution
    except ImportError:  # pragma: no cover - Python < 3.8 is not supported
        return []
    try:
        dist = distribution(name)
    except Exception:
        return []
    found = []
    for file in dist.files or ():
        parts = str(file).split("/")
        info = next(
            (i for i, part in enumerate(parts)
             if part.endswith((".dist-info", ".egg-info"))),
            None,
        )
        # Below dist-info, the path is relative to it. Elsewhere it is relative
        # to the top-level package directory, so foo/bar/LICENSE is filed as
        # bar/LICENSE and not as foo/foo/bar/LICENSE.
        below = parts[info + 1:] if info is not None else parts[1:]
        if not below or not _is_licence(parts):
            continue
        try:
            text = _read_text(file.locate())
        except Exception:
            # Loud on purpose. A licence file that cannot be read has to be
            # noticed, not quietly left out of the archive — a tree that looks
            # complete and is not is worse than one with an obvious hole.
            log.warning("Could not read the licence file %s", file, exc_info=True)
            continue
        found.append(("/".join(below), text))
    return _flatten(found)


def _installed(name: str) -> bool:
    """Is this distribution present in the environment being packaged?"""
    try:
        from importlib.metadata import distribution
    except ImportError:  # pragma: no cover - Python < 3.8 is not supported
        return False
    try:
        distribution(name)
    except Exception:
        return False
    return True


def _read_text(path) -> str:
    """Read a licence file whatever it happens to be encoded in.

    Not everything is UTF-8. Aggregate notices carry the copyright sign and
    contributors' names in whatever encoding the projects they were copied
    from used, and a single stray byte is enough for UTF-8 to reject the
    file — after which the exception handler drops it and the tree comes out
    one notice short with no indication that anything is missing.

    Latin-1 is the fallback because it cannot fail — every byte is a
    character — and it decodes exactly the Western European text these older
    files contain. The result is written back out as UTF-8.
    """
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _flatten(files: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop the leading ``licenses/`` most wheels wrap their texts in.

    It is a packaging convention, not information, and keeping it produces
    licenses/python/PySide6/licenses/LICENSE. Dropped only where it does
    not collide with a file already sitting at the top of dist-info — a wheel
    that ships both LICENSE and licenses/LICENSE keeps them apart.
    """
    names = {path for path, _ in files}
    flattened = []
    for path, text in files:
        head, _, rest = path.partition("/")
        if head == "licenses" and rest and rest not in names:
            path = rest
        flattened.append((path, text))
    return flattened


def _system_packages(binaries) -> list[str]:
    """Package names owning the system libraries PyInstaller collected.

    Only meaningful on a Debian-family build machine. Everywhere else this
    returns nothing and the caller records why.
    """
    if not shutil.which("dpkg-query"):
        return []
    packages = set()
    for entry in binaries:
        source = str(entry[1])
        # Wheel-vendored libraries live under site-packages; only the ones
        # taken from the system's own lib directories have an owning package.
        if "site-packages" in source or not os.path.exists(source):
            continue
        found = subprocess.run(
            ["dpkg-query", "-S", os.path.realpath(source)],
            capture_output=True,
            text=True,
        )
        if found.returncode == 0 and found.stdout.strip():
            packages.add(found.stdout.split(":")[0].strip())
    return sorted(packages)


def collect(repo: str, staging: str, binaries=()) -> str:
    """Build the licence tree under ``staging`` and return its path."""
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    index = [
        "# Licences of the software in this package",
        "",
        "P7M Manager itself is licensed AGPL-3.0-or-later; the full text is in",
        "`P7MManager-LICENSE.txt`. A commercial licence, without the AGPL's",
        "obligations, is available separately — see the project's",
        "COMMERCIAL-LICENSE.md.",
        "",
        "Everything else in this package was written by other people, under",
        "their own terms. This directory holds those terms. The inventory of",
        "which binary belongs to which project is THIRD-PARTY-LICENSES.md in",
        "the P7M Manager repository.",
        "",
        "Nearly all of it is Qt. P7M Manager depends on PySide6 and on nothing",
        "else at run time — the ASN.1, CMS and X.509 engine is written against",
        "the standard library — and Qt is **LGPL-3.0**, which asks more of a",
        "redistributor than the permissive licences most of this kind of",
        "package contains. `python/PySide6/` holds both LGPL-3.0 and GPL-3.0,",
        "because the first is a set of additional permissions on top of the",
        "second and means nothing without it.",
        "",
        "## P7M Manager",
        "",
        "- `P7MManager-LICENSE.txt` — GNU Affero General Public License v3.0",
        "",
    ]

    shutil.copyfile(
        os.path.join(repo, "LICENSE"), os.path.join(staging, "P7MManager-LICENSE.txt")
    )

    index += ["## The interpreter", ""]
    for folder, canonical, description in ALWAYS_SUPPLIED:
        target = os.path.join(staging, folder)
        os.makedirs(target, exist_ok=True)
        shutil.copyfile(
            os.path.join(repo, "licenses", canonical),
            os.path.join(target, canonical),
        )
        index.append(f"- **{description}** — `{folder}/{canonical}`")
    index.append("")

    index += ["## Python packages", ""]
    python_dir = os.path.join(staging, "python")
    os.makedirs(python_dir)
    for name in RUNTIME_DISTRIBUTIONS:
        if not _installed(name):
            # PySide6 comes in three distributions and P7M Manager needs one of them.
            # Writing the supplied LGPL-3.0 text for all three regardless put
            # a PySide6_Addons directory in an archive that contains no such
            # thing, which reads as a claim about what is in the bundle. A
            # licence tree is worth exactly as much as its accuracy.
            continue
        files = _distribution_licence_files(name)
        supplied = SUPPLIED_TEXTS.get(name, ())
        if not files and not supplied:
            index.append(f"- **{name}** — no licence file found; see the inventory")
            continue
        target = os.path.join(python_dir, name)
        os.makedirs(target, exist_ok=True)
        written = []
        for filename, text in files:
            destination = os.path.join(target, *filename.split("/"))
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "w", encoding="utf-8") as out:
                out.write(text)
            written.append(filename)
        for canonical in supplied:
            shutil.copyfile(
                os.path.join(repo, "licenses", canonical),
                os.path.join(target, canonical),
            )
            written.append(f"{canonical} (supplied — the wheel ships none)")
        index.append(f"- **{name}** — {', '.join(written)}")
    index.append("")

    packages = _system_packages(binaries)
    index += ["## System libraries collected at build time", ""]
    if packages:
        system_dir = os.path.join(staging, "system")
        os.makedirs(system_dir)
        for package in packages:
            source = f"/usr/share/doc/{package.split(':')[0]}/copyright"
            if not os.path.exists(source):
                continue
            shutil.copyfile(source, os.path.join(system_dir, f"{package}.txt"))
        index.append(
            f"The build machine's copyright records for {len(packages)} packages "
            "are in `system/`."
        )
    else:
        index.append(
            "This build was not produced on a Debian-family machine, so there "
            "are no package copyright records to copy. The libraries collected "
            "from the platform on this build are the Microsoft Visual C++ and "
            "Universal CRT runtime (redistributable under Microsoft's own "
            "terms, not an open-source licence), and the OpenSSL and libffi "
            "builds that ship inside python.org's distributions — Apache-2.0 "
            "and MIT respectively; `Apache-2.0.txt` is included here."
        )
        shutil.copyfile(
            os.path.join(repo, "licenses", "Apache-2.0.txt"),
            os.path.join(staging, "Apache-2.0.txt"),
        )
    index += [
        "",
        "## Relinking",
        "",
        "Qt is used under the LGPL-3.0. It is unmodified, and it is linked",
        "dynamically: the Qt libraries in this package are separate files, so",
        "they can be replaced with a modified build of the same version",
        "without rebuilding P7M Manager. `python/PySide6/` holds LGPL-3.0 and the",
        "GPL-3.0 text it builds on. The same applies to the LGPL-2.1",
        "libraries collected from the build machine.",
        "",
    ]

    with open(os.path.join(staging, "README.md"), "w", encoding="utf-8") as out:
        out.write("\n".join(index))
    return staging


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    staging = argv[0] if argv else os.path.join(repo, "build", "licenses")
    collect(repo, staging)
    for directory, _subdirs, files in os.walk(staging):
        for name in sorted(files):
            path = os.path.join(directory, name)
            print(f"{os.path.getsize(path):>8}  {os.path.relpath(path, staging)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
