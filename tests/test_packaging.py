# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.

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


#: The committed icons were drawn with this face. Another serif — Times New
#: Roman on a Windows or macOS runner — is metric-compatible but not
#: pixel-identical, so comparing against it would fail on a correct file.
LIBERATION_SERIF = (
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
    Path("/usr/share/fonts/liberation/LiberationSerif-Regular.ttf"),
)


def test_the_icons_are_what_the_script_draws():
    """Regenerate and compare, so "run it again and diff" can be trusted."""
    pytest.importorskip("PIL")
    if not any(path.exists() for path in LIBERATION_SERIF):
        pytest.skip("the committed icons are drawn with Liberation Serif")

    import sys
    import tempfile

    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import make_icon
    finally:
        sys.path.pop(0)

    with tempfile.TemporaryDirectory() as temporary:
        out = Path(temporary)
        make_icon.write_icons("P", out, "p7mmanager")
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
    """Asked of git, not of the filesystem.

    The mode that matters is the one recorded in the index — 100755 — because
    that is what a Linux or macOS checkout gets, and what the release job
    copies into the archive. A Windows filesystem has no execute bit at all,
    so reading st_mode there fails on a file that is perfectly correct.
    """
    import subprocess

    try:
        entry = subprocess.run(
            ["git", "ls-files", "-s", "packaging/start.sh"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        pytest.skip("not a git checkout")
    if not entry.strip():  # pragma: no cover - file not tracked yet
        pytest.skip("start.sh is not in the index")
    assert entry.startswith("100755"), (
        "start.sh must be executable in the repository: "
        "git update-index --chmod=+x packaging/start.sh"
    )


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
    """In licenses/, and only there.

    AGPL-3.0 section 5 wants this program's own licence to travel with the
    object code, and the licence tree carries it as P7MManager-LICENSE.txt --
    the repository's LICENSE under a name that says whose it is, among
    everybody else's.

    The root used to carry LICENSE, COMMERCIAL-LICENSE.md, README.md and
    CHANGELOG.md as well. That duplicated the AGPL, put four documents in
    front of somebody who opened the archive to find a program, and made this
    the only one of the seven products whose download did not unpack to just
    the program, its launcher and its checksum.
    """
    assert 'cp -R build/licenses "$root/licenses"' in WORKFLOW
    assert "cp LICENSE" not in WORKFLOW, (
        "the repository's documents are back in the archive root"
    )

    collector = (ROOT / "tools" / "collect_licences.py").read_text(encoding="utf-8")
    assert '"P7MManager-LICENSE.txt"' in collector, (
        "nothing puts this program's own licence in the tree, so dropping it "
        "from the root drops it from the archive"
    )


def test_the_launcher_itself_is_tested_before_publishing():
    assert "Start the bundle through the launcher" in WORKFLOW
    assert "the launcher started an executable whose checksum did not match" in WORKFLOW


def test_windows_keeps_the_top_level_folder():
    """Compress-Archive drops it; 7z keeps it, so all three unpack alike."""
    assert "7z a -tzip" in WORKFLOW
    # Named in a comment explaining why it is not used; never invoked.
    assert "Compress-Archive -Path" not in WORKFLOW


def test_the_checksums_go_into_the_notes_and_not_the_download_list():
    """As in Orion: three extra files in a download list is not the way.

    A checksum still has to arrive by a route the archive did not, which the
    release page's notes are; what it must not do is sit beside the archive as
    another asset someone has to scroll past.
    """
    assert 'gh release upload "$TAG" "$ARCHIVE" --clobber' in WORKFLOW
    assert '"$ARCHIVE.sha256" --clobber' not in WORKFLOW
    assert "gh release edit \"$TAG\" --notes-file body.md" in WORKFLOW
    assert "<!-- checksums -->" in WORKFLOW, "the block must be rewritable on a re-run"


def test_a_partial_list_of_checksums_is_never_written():
    """The notes job waits for all three builds; two of three is worse than
    none, because a reader cannot tell missing from unlisted."""
    import re

    block = re.search(r"  checksums:\n(.*?)(?:\n  [a-z]|\Z)", WORKFLOW, re.S)
    assert block, "the checksums job is missing"
    assert "needs: [release, build]" in block.group(1)
    assert "no checksums were handed up by the build jobs" in block.group(1)


def test_stale_assets_from_an_earlier_build_are_removed():
    """A moved tag lands on a release that may already carry assets — including
    the .sha256 files this workflow used to publish."""
    assert "Remove assets left by a previous build" in WORKFLOW
    assert "gh release delete-asset" in WORKFLOW


def test_the_launchers_point_at_the_release_notes_for_the_real_check():
    """The launcher may not imply it catches tampering: the digest it reads
    travels in the same archive. It says where the useful check lives."""
    for name in ("start.cmd", "start.sh"):
        text = (ROOT / "packaging" / name).read_text(encoding="utf-8")
        assert "release notes" in text or "release page" in text
        assert "published as a separate" not in text


class TestTheBuildIsOneFile:
    """Every product in this family freezes to a single executable.

    CLAUDE.md carries the rule and what it costs. These hold the two halves
    that a later edit would undo without noticing: the spec that produces one
    file, and the inventory step that can still see inside it.
    """

    def test_the_spec_produces_one_file_and_not_a_folder(self):
        assert "COLLECT(" not in SPEC, (
            "COLLECT is a folder build; this family ships one executable"
        )
        assert "exclude_binaries" not in SPEC, (
            "exclude_binaries=True keeps the libraries out of the executable, "
            "which is the folder build by another name"
        )

    def test_the_executable_carries_the_libraries_and_the_data(self):
        """Passed to EXE, not to a COLLECT that no longer exists. Leaving one
        of them out produces a build that links and then cannot start.
        """
        exe = SPEC[SPEC.index("exe = EXE("):SPEC.index(")", SPEC.index("icon=icon"))]
        for argument in ("a.binaries", "a.zipfiles", "a.datas"):
            assert argument in exe, f"{argument} never reaches the executable"

    def test_macos_still_gets_an_application_bundle(self):
        """Double-clicking a bare Unix executable on macOS opens a terminal,
        when it does anything at all. BUNDLE wraps the same single binary.
        """
        assert "BUNDLE(" in SPEC
        assert "app = BUNDLE(\n        exe," in SPEC, (
            "the bundle is built from something other than the onefile EXE"
        )


def test_the_mac_bundle_reports_the_version_the_program_reports():
    """Info.plist is what Finder, the installer and crash reports read.

    It was written once at 1.0.0 and then not touched for two releases, so a
    macOS user's Get Info panel and the program's own About box disagreed --
    and nothing noticed, because nothing on Linux or Windows reads it.
    """
    from p7mmanager import __version__

    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        assert f'"{key}": "{__version__}"' in SPEC, (
            f"{key} in the bundle does not say {__version__}"
        )
