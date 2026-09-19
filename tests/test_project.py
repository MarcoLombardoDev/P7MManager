# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.

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


#: Import names that are not the name of the distribution providing them.
#: Short enough to keep by hand; anything not here is assumed to match.
DISTRIBUTION_OF = {"PIL": "Pillow", "yaml": "pyyaml"}

#: Imported from tools/ after the test module puts that directory on the path.
LOCAL_MODULES = {"p7mmanager", "collect_licences", "licence_inventory", "make_icon"}


def test_requirements_dev_declares_everything_the_tests_import():
    """A test file and the line that installs its dependency travel together.

    They did not here: tests/test_release_workflow.py arrived with an outright
    ``import yaml`` and requirements-dev.txt was not told, so CI stopped at
    collection and ran none of the suite. The developer machine had PyYAML for
    other reasons and said nothing, which is exactly the shape of failure a
    dependency list exists to prevent.
    """
    import ast
    import sys

    declared = {
        line.split("#")[0].strip().split(">=")[0].split("==")[0].strip().lower()
        for text in (
            (ROOT / "requirements.txt").read_text(encoding="utf-8"),
            (ROOT / "requirements-dev.txt").read_text(encoding="utf-8"),
        )
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-"))
    }

    imported = set()
    for path in sorted((ROOT / "tests").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                imported.add(node.module.split(".")[0])

    missing = sorted(
        name
        for name in imported
        if name not in sys.stdlib_module_names
        and name not in LOCAL_MODULES
        and DISTRIBUTION_OF.get(name, name).lower() not in declared
    )
    assert not missing, (
        f"the tests import {missing} and no requirements file asks for them, "
        "so a clean checkout fails at collection"
    )


def test_pyproject_declares_the_entry_points():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'p7mmanager = "p7mmanager.main:main"' in text
    assert "AGPL-3.0-or-later" in text
    assert "PySide6" in text


def test_the_entry_point_survives_freezing():
    """PyInstaller runs __main__.py with no parent package.

    A relative import there fails only in the frozen build, which is the one
    place nobody runs before publishing it — as this project found out by
    building one.
    """
    source = (PACKAGE / "__main__.py").read_text(encoding="utf-8")
    assert "from p7mmanager.main import main" in source
    assert "from .main import" not in source


def test_the_release_workflow_builds_on_a_tag():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert 'tags: ["v*"]' in workflow, "a tag must start the release build"
    assert "workflow_dispatch" in workflow, "a tag that predates the workflow needs a way in"
    assert "contents: write" in workflow, "uploading assets needs write permission"
    assert "--self-check" in workflow, "a bundle is smoke-tested before it is published"
    for asset in ("windows-x64", "macos-arm64", "linux-x64"):
        assert asset in workflow
    assert (ROOT / ".github" / "release-body.md").is_file()


def test_the_release_notes_state_the_limits():
    notes = (ROOT / ".github" / "release-body.md").read_text(encoding="utf-8")
    assert "not a legal validation" in notes
    assert "AGPL-3.0" in notes


def test_the_spec_is_shipped():
    """The launchers themselves are covered by tests/test_packaging.py."""
    assert (ROOT / "p7mmanager.spec").is_file()
