# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""What a downloader gets: the icon, the launcher, the shape of the archive.

None of this is exercised by running the application from a checkout, which
is why it is checked here instead — the two bugs that only existed in the
frozen build were found by building one, and these tests are the cheap half of
that lesson.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "resources" / "icons"
WORKFLOW = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
SPEC = (ROOT / "p7mmanager.spec").read_text(encoding="utf-8")


# --- the icon ---------------------------------------------------------------

@pytest.mark.parametrize("name", ["p7mmanager.png", "p7mmanager.ico", "p7mmanager.icns"])
def test_the_icons_are_committed(name: str):
    """Committed, not generated at build time: a release must not depend on
    which fonts — or which Pillow — a runner happens to have."""
    assert (ICONS / name).is_file()


def test_the_icons_are_what_the_script_draws():
    """Regenerate and compare, so "run it again and diff" can be trusted."""
    pytest.importorskip("PIL")
    import sys
    import tempfile

    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import make_icon
    except SystemExit:  # pragma: no cover - no serif font on this machine
        pytest.skip("no serif font installed")
    finally:
        sys.path.pop(0)

    with tempfile.TemporaryDirectory() as temporary:
        out = Path(temporary)
        try:
            make_icon.write_icons("P", out, "p7mmanager")
        except SystemExit as exc:  # pragma: no cover - font missing
            pytest.skip(str(exc))
        for name in ("p7mmanager.png", "p7mmanager.ico", "p7mmanager.icns"):
            assert (out / name).read_bytes() == (ICONS / name).read_bytes(), (
                f"{name} differs from what tools/make_icon.py draws; "
                "regenerate it rather than editing it by hand"
            )


def test_the_icon_is_the_product_initial():
    """A P, as Orion's is an O: the products share the drawing and the letter
    is the only thing that differs."""
    pytest.importorskip("PIL")
    from PIL import Image

    image = Image.open(ICONS / "p7mmanager.png").convert("RGB")
    assert image.size == (512, 512)
    # Black ink on white, with a frame: a corner is the frame's, and the strip
    # between the frame and the letter is the ground. Near-white rather than
    # exactly white, because the frame's edge is antialiased.
    assert image.getpixel((0, 0)) == (0, 0, 0)
    assert sum(image.getpixel((256, 60))) > 740


def test_the_spec_embeds_the_icon():
    assert "p7mmanager.ico" in SPEC and "p7mmanager.icns" in SPEC
    assert "icon=icon" in SPEC
    # And it ships inside the bundle, for the window and the taskbar.
    assert '("resources/icons/p7mmanager.png", "resources/icons")' in SPEC


def test_the_application_sets_its_window_icon():
    source = (ROOT / "p7mmanager" / "main.py").read_text(encoding="utf-8")
    assert "_set_application_icon" in source
    assert "icons" in source and "p7mmanager.png" in source


# --- the launcher -----------------------------------------------------------

@pytest.mark.parametrize("name", ["start.cmd", "start.sh"])
def test_the_launchers_are_shipped(name: str):
    assert (ROOT / "packaging" / name).is_file()


@pytest.mark.parametrize("name", ["start.cmd", "start.sh"])
def test_the_launcher_verifies_before_it_launches(name: str):
    """It checks the executable against the checksum shipped beside it, and
    says so rather than implying it catches tampering, which it cannot."""
    text = (ROOT / "packaging" / name).read_text(encoding="utf-8")
    assert "P7MManager" in text
    assert "sha256" in text.lower()
    assert "SKIP_VERIFY" in text, "there must be an explicit escape hatch"
    assert "does not match" in text
    assert "tampering" in text.lower()


def test_the_shell_launcher_is_executable():
    mode = (ROOT / "packaging" / "start.sh").stat().st_mode
    assert mode & 0o111, "start.sh must be executable in the repository"


# --- the archive ------------------------------------------------------------

def test_the_archive_unpacks_to_the_product_name():
    """The folder a downloader ends up with is "P7M Manager", space and all."""
    assert "FOLDER_NAME: P7M Manager" in WORKFLOW
    assert 'root="dist/pkg/$FOLDER_NAME"' in WORKFLOW


def test_the_launcher_travels_inside_the_archive():
    assert "cp packaging/start.cmd" in WORKFLOW
    assert "cp packaging/start.sh" in WORKFLOW
    assert "start.command" in WORKFLOW, "macOS needs the name Finder will open"


def test_the_archive_carries_the_licence_texts():
    assert re.search(r"cp LICENSE COMMERCIAL-LICENSE\.md README\.md CHANGELOG\.md", WORKFLOW)


def test_the_launcher_itself_is_tested_before_publishing():
    assert "Start the bundle through the launcher" in WORKFLOW
    assert "the launcher started an executable whose checksum did not match" in WORKFLOW


def test_windows_keeps_the_top_level_folder():
    """Compress-Archive drops it; 7z keeps it, so all three unpack alike."""
    assert "7z a -tzip" in WORKFLOW
    # Named in a comment explaining why it is not used; never invoked.
    assert "Compress-Archive -Path" not in WORKFLOW


def test_the_archive_checksum_is_published_separately():
    assert 'gh release upload "$TAG" "$ARCHIVE" "$ARCHIVE.sha256"' in WORKFLOW
