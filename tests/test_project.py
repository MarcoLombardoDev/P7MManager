# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The promises the repository itself makes: licence headers, docs, packaging.

Dual licensing only works if every file carries the notice, and the claim the
tool must never overstate — that this is not a legal validation — is checked
here as well, because it belongs in the README and the interface alike.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "p7mmanager"

SOURCES = sorted(
    path
    for path in list(PACKAGE.rglob("*.py")) + list((ROOT / "tests").glob("*.py"))
)


@pytest.mark.parametrize("path", SOURCES, ids=lambda path: str(path.relative_to(ROOT)))
def test_every_source_file_carries_the_licence_header(path: Path):
    head = path.read_text(encoding="utf-8")[:400]
    assert "SPDX-License-Identifier: AGPL-3.0-or-later" in head
    assert "Copyright (C) 2026 Marco Lombardo" in head


@pytest.mark.parametrize(
    "path",
    sorted(PACKAGE.rglob("*.py")),
    ids=lambda path: str(path.relative_to(ROOT)),
)
def test_package_files_point_at_the_commercial_licence(path: Path):
    head = path.read_text(encoding="utf-8")[:500]
    assert "COMMERCIAL-LICENSE.md" in head


def test_the_engine_does_not_import_qt():
    """The layout rule in CLAUDE.md, enforced rather than trusted."""
    offenders = [
        path.relative_to(ROOT)
        for path in (PACKAGE / "core").rglob("*.py")
        if "PySide6" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"Qt imported inside the engine: {offenders}"


@pytest.mark.parametrize(
    "name",
    ["README.md", "LICENSE", "COMMERCIAL-LICENSE.md", "CLA.md", "CONTRIBUTING.md",
     "CLAUDE.md", "CHANGELOG.md", "pyproject.toml", "requirements.txt",
     "docs/ARCHITECTURE.md"],
)
def test_the_repository_has_its_documents(name: str):
    assert (ROOT / name).is_file(), f"{name} is missing"


def test_the_readme_states_what_the_tool_does_not_claim():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "not a legal validation" in readme
    assert "revocation" in readme


def test_the_licence_is_the_agpl():
    licence = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in licence
    assert "Version 3" in licence


def test_the_commercial_licence_offers_both():
    text = (ROOT / "COMMERCIAL-LICENSE.md").read_text(encoding="utf-8")
    assert "dual-licensed" in text
    assert "AGPL" in text


@pytest.mark.parametrize(
    "price", ["€900 / year", "€1,800 / year", "€3,200 / year", "from €5,500 / year",
              "€2,900 / year", "from €10,000 / year"]
)
def test_the_price_list_agrees_with_itself(price: str):
    """The README quotes the tiers; a reader must not find two answers."""
    for name in ("README.md", "COMMERCIAL-LICENSE.md"):
        assert price in (ROOT / name).read_text(encoding="utf-8"), f"{price} missing from {name}"


def test_the_interface_carries_the_copyright_line():
    """AGPL-3.0 section 5, as a constant the window cannot be built without."""
    from p7mmanager import APP_AUTHOR, APP_NAME, CONTACT_EMAIL, LICENSE_NOTICE

    assert APP_NAME in LICENSE_NOTICE
    assert APP_AUTHOR in LICENSE_NOTICE
    assert "AGPL-3.0" in LICENSE_NOTICE
    assert CONTACT_EMAIL in (ROOT / "COMMERCIAL-LICENSE.md").read_text(encoding="utf-8")


def test_claude_md_states_the_branch_and_attribution_rules():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "`main` is the only branch" in text
    assert "Co-Authored-By" in text
    assert "MarcoLombardoDev" in text


def test_pyproject_declares_the_entry_points():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'p7mmanager = "p7mmanager.main:main"' in text
    assert "AGPL-3.0-or-later" in text
    assert "PySide6" in text


def test_the_launchers_are_shipped():
    assert (ROOT / "packaging" / "start.cmd").is_file()
    assert (ROOT / "packaging" / "start.sh").is_file()
    assert (ROOT / "p7mmanager.spec").is_file()
