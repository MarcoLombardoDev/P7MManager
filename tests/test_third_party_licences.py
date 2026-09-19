#!/usr/bin/env python
# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Keeps THIRD-PARTY-LICENSES.md honest about the dependencies it describes.

The document is generated from an extracted release bundle, which no test can
reach: CI has no release archive and no Ubuntu package database to consult. So
this file does not try to re-derive the inventory. It checks the part that *is*
checkable from the repository, which is also the part most likely to rot: the
dependency tables, the classifier, and the licence tree the spec ships.

The failure this guards against is mundane and easy to miss. Someone adds a
dependency, or swaps one library for another, and the licence document keeps
describing the old set — which is worse than having no document, because a
stale licence document is one people rely on.

The classifier in tools/licence_inventory.py is tested here too. It is pure
string handling over bundle-relative paths, so it needs no bundle: the paths
below were copied out of a real build of each platform's layout.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENT = os.path.join(REPO, "THIRD-PARTY-LICENSES.md")

sys.path.insert(0, os.path.join(REPO, "tools"))

from collect_licences import (  # noqa: E402
    RUNTIME_DISTRIBUTIONS,
    SUPPLIED_TEXTS,
    _flatten,
    _is_licence,
    collect,
)
from licence_inventory import classify, is_native  # noqa: E402


@pytest.fixture(scope="module")
def document() -> str:
    with open(DOCUMENT, encoding="utf-8") as handle:
        return handle.read()


def declared_requirements() -> list[str]:
    """The runtime dependency names, read from requirements.txt."""
    path = os.path.join(REPO, "requirements.txt")
    with open(path, encoding="utf-8") as handle:
        lines = [line.strip() for line in handle]
    names = []
    for line in lines:
        if not line or line.startswith(("#", "-")):
            continue
        names.append(re.split(r"[<>=!~\[]", line)[0].strip())
    return names


def table_rows(document: str, heading: str) -> set[str]:
    """First-column names of the table that follows ``heading``."""
    section = document[document.index(heading):]
    rows = set()
    for line in section.splitlines():
        if not line.startswith("| "):
            if rows:
                break              # the table has ended
            continue
        cell = line.split("|")[1].strip()
        if not cell or "---" in cell or cell == "Package":
            continue
        rows.add(re.sub(r"[*]", "", cell).strip())
    return rows


def test_every_runtime_dependency_is_documented(document: str) -> None:
    """A dependency the user receives but the licence file never mentions."""
    missing = [
        name for name in declared_requirements()
        if name.lower() not in document.lower()
    ]
    assert not missing, (
        f"{missing} are in requirements.txt but absent from "
        "THIRD-PARTY-LICENSES.md — a dependency was added without recording "
        "what licenses it"
    )


def test_the_direct_table_is_exactly_requirements_txt(document: str) -> None:
    """Both directions at once.

    The table of direct dependencies is the one a reader treats as the answer
    to "what is this built on". A package added to requirements.txt and not to
    the table is undocumented; one left in the table after being dropped is a
    claim about software that is no longer here. The transitive packages have
    a table of their own precisely so this one can be compared exactly.
    """
    listed = table_rows(document, "## What P7M Manager depends on directly")
    declared = set(declared_requirements())
    assert listed == declared, (
        f"the document lists {sorted(listed)}; requirements.txt says "
        f"{sorted(declared)}"
    )


@pytest.mark.parametrize(
    "dependency, licence",
    [
        # The only one there is, and the one that constrains redistribution.
        # If this string stops matching the wheel metadata, the licensing
        # analysis in COMMERCIAL-LICENSE.md is built on a false premise.
        ("PySide6", "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"),
    ],
)
def test_licence_of_each_dependency_is_stated(
    document: str, dependency: str, licence: str
) -> None:
    row = next(
        (line for line in document.splitlines()
         if line.startswith(f"| **{dependency}**")),
        None,
    )
    assert row is not None, f"no table row for {dependency}"
    assert licence in row, (
        f"{dependency} is documented as something other than {licence!r}: {row}"
    )


def test_the_declared_licences_are_the_ones_the_wheels_declare(document: str) -> None:
    """The table is not allowed to be someone's memory of these projects.

    Read back out of the installed distributions' own metadata, so a wheel that
    relicenses between versions is caught here rather than after a release.
    Skipped per package that is not installed, which keeps this useful in an
    environment that has only some of them.
    """
    from importlib.metadata import PackageNotFoundError, distribution

    checked = 0
    for name in ("playwright", "greenlet", "typing_extensions"):
        try:
            metadata = distribution(name).metadata
        except PackageNotFoundError:
            continue
        declared = metadata.get("License-Expression") or metadata.get("License")
        if not declared:
            continue
        row = next(line for line in document.splitlines()
                   if line.startswith(f"| **{name}**"))
        assert declared in row, f"{name} declares {declared!r}; the table says {row}"
        checked += 1
    if not checked:
        pytest.skip("none of the packages with a declared licence are installed")


def test_the_document_says_which_claims_are_this_machines(document: str) -> None:
    """A licence document has to say how strongly each claim was checked.

    The counts here come from a build on one Ubuntu machine, and the numbers a
    given download actually has come from the runner that produced it. Those
    are not the same claim, and presenting them as one uniform "verified" is
    the kind of accurate-but-misleading that gets somebody into trouble.
    """
    assert "## Known gaps" in document
    assert "THIRD-PARTY-LICENSES-<platform>.md" in document, (
        "the document does not point at the copy inside the archive, which is "
        "the only one authoritative for a given download"
    )
    assert "not this file" in document, (
        "the document does not say which of the two copies is authoritative"
    )
    assert "## How this was produced" in document


class TestBundleClassifier:
    """Paths taken from a real build of each platform's layout."""

    @pytest.mark.parametrize(
        "path, component",
        [
            # Linux: PyInstaller hoists wheel libraries next to system ones,
            # so the name is all there is to go on.
            ("libQt6Core.so.6", "PySide6 / Qt 6"),
            # ICU is vendored inside the PySide6 wheel and looks exactly like
            # a system library once hoisted. Attributing it to the system
            # would credit it to a package the build machine never had.
            ("libicuuc.so.73", "PySide6 / Qt 6 (ICU)"),
            ("greenlet/_greenlet.cpython-311-x86_64-linux-gnu.so", "greenlet"),
            ("_ssl.cpython-312-x86_64-linux-gnu.so", "CPython"),
            # macOS: the framework binary has no extension at all.
            ("QtGui.framework/Versions/A/QtGui", "PySide6 / Qt 6"),
            ("Python.framework/Versions/3.12/Python", "CPython"),
            # Windows: a bare .pyd is a stdlib extension module; one inside a
            # package belongs to that package.
            ("_socket.pyd", "CPython"),
            ("PySide6/QtCore.pyd", "PySide6 / Qt 6"),
        ],
    )
    def test_attribution(self, path: str, component: str) -> None:
        classified = classify(path)
        assert classified is not None, f"{path} was not recognised as native"
        assert classified[1] == component

    def test_a_file_merely_called_node_is_not_the_driver(self) -> None:
        """``node`` is a generic enough name to belong to anything; the match
        is on the path Playwright actually puts it at.
        """
        assert not is_native("resources/node")
        assert not is_native("app/x/node")

    def test_the_frozen_executable_is_not_a_library(self) -> None:
        assert not is_native("P7MManager")
        assert not is_native("base_library.zip")


class TestLicenceCollection:
    """The tree that p7mmanager.spec puts inside the archive as licenses/."""

    @pytest.fixture(scope="class")
    def tree(self, tmp_path_factory) -> str:
        return collect(REPO, str(tmp_path_factory.mktemp("licences") / "out"))

    def test_xips_own_licence_is_there(self, tree: str) -> None:
        with open(os.path.join(tree, "P7MManager-LICENSE.txt"), encoding="utf-8") as f:
            assert "GNU AFFERO GENERAL PUBLIC LICENSE" in f.read()

    def test_qt_gets_a_licence_text_the_wheel_never_shipped(self, tree: str) -> None:
        """PySide6's wheels declare LGPL-3.0 and include no licence file.

        Nothing can be copied forward from a wheel that ships nothing, so the
        text has to be supplied — which is the whole reason licenses/ exists in
        the repository rather than being generated from dist-info alone.
        """
        supplied = os.path.join(tree, "python", "PySide6_Essentials")
        assert os.path.isdir(supplied), "PySide6-Essentials got no licence directory"
        assert os.path.exists(os.path.join(supplied, "LGPL-3.0.txt"))

    def test_lgpl3_never_travels_without_gpl3(self, tree: str) -> None:
        """LGPL-3.0 is a set of additional permissions on top of GPL-3.0.

        Its text is seven kilobytes and defines almost nothing on its own:
        shipping it alone ships half a licence. Every distribution that gets
        LGPL-3.0 gets GPL-3.0 with it.
        """
        for name, texts in SUPPLIED_TEXTS.items():
            if "LGPL-3.0.txt" not in texts:
                continue
            assert "GPL-3.0.txt" in texts, (
                f"{name} is given LGPL-3.0 without the GPL-3.0 it builds on"
            )
            directory = os.path.join(tree, "python", name)
            if os.path.isdir(directory):
                assert os.path.exists(os.path.join(directory, "GPL-3.0.txt"))

    def test_a_distribution_that_is_not_installed_gets_no_directory(
        self, tree: str
    ) -> None:
        """PySide6 comes in three distributions and P7M Manager needs one of them.

        Writing the supplied LGPL-3.0 text for all three regardless put a
        PySide6_Addons directory into an archive containing no such thing,
        which reads as a claim about what is in the bundle.
        """
        from importlib.metadata import PackageNotFoundError, distribution

        for name in SUPPLIED_TEXTS:
            try:
                distribution(name)
            except PackageNotFoundError:
                assert not os.path.isdir(os.path.join(tree, "python", name)), (
                    f"{name} is not installed but got a licence directory"
                )

    def test_the_playwright_driver_aggregate_is_collected(self, tree: str) -> None:
        """The 154 KB file that is the notice for the whole Node binary.

        It is package data, not distribution metadata, so a collector that
        reads dist-info alone picks up Playwright's own 11 KB Apache-2.0 text,
        reports success, and leaves out the largest and most necessary licence
        in the archive — the one §11 of COMMERCIAL-LICENSE.md promises travels
        with it.
        """
        pytest.importorskip("playwright")
        driver = os.path.join(tree, "python", "playwright", "driver", "LICENSE")
        assert os.path.exists(driver), "the Node aggregate was not collected"
        assert os.path.getsize(driver) > 100_000, (
            "the collected file is too small to be the aggregate; dist-info's "
            "own LICENSE was probably picked up instead"
        )

    def test_the_driver_notices_beside_the_code_are_collected_too(
        self, tree: str
    ) -> None:
        """Three of them are named after what they cover rather than after the
        word — utilsBundle.js.LICENSE and friends — so matching only on the
        start of a file name collected none of them.
        """
        pytest.importorskip("playwright")
        directory = os.path.join(tree, "python", "playwright")
        collected = {
            os.path.basename(name)
            for _root, _dirs, files in os.walk(directory)
            for name in files
        }
        for notice in ("NOTICE", "ThirdPartyNotices.txt"):
            assert notice in collected, f"Playwright ships {notice} and says so"

        # The bug this guards against was matching only the start of a file
        # name, which collected nothing whose name *ends* in ".LICENSE" --
        # utilsBundle.js.LICENSE and its siblings. Which of those sidecars
        # exists depends on the Playwright release, and requirements.txt admits
        # a range, so assert against what this installation actually ships
        # rather than against one version's file list.
        import playwright

        driver = os.path.join(os.path.dirname(playwright.__file__), "driver")
        shipped = {
            name
            for _root, _dirs, files in os.walk(driver)
            for name in files
            if name.endswith(".LICENSE")
        }
        missing = sorted(shipped - collected)
        assert not missing, f"licence sidecars left behind: {missing}"

    def test_the_pyinstaller_bootloader_exception_travels_with_the_binary(
        self, tree: str
    ) -> None:
        """The bootloader is compiled into the executable, so its terms ship.

        Skipped where PyInstaller is not installed. CI installs the test
        dependencies and not always the packaging ones, so demanding the file
        exist here would assert a property of one machine rather than of the
        collector — which is right to omit terms for software that is not
        present.
        """
        from importlib.metadata import PackageNotFoundError, distribution

        try:
            distribution("pyinstaller")
        except PackageNotFoundError:
            pytest.skip("PyInstaller is not installed in this environment")
        path = os.path.join(tree, "python", "pyinstaller", "COPYING.txt")
        with open(path, encoding="utf-8") as f:
            assert "Bootloader Exception" in f.read()

    def test_a_missing_licence_is_recorded_rather_than_passed_over(
        self, tree: str
    ) -> None:
        """Silence is the dangerous failure mode for a licence collector.

        If a distribution ships no licence file and none is supplied for it,
        the tree simply has no directory for it — which looks identical to a
        distribution that is not used at all. The index has to say so, so that
        a gap is visible in the archive instead of being indistinguishable
        from completeness.
        """
        from importlib.metadata import PackageNotFoundError, distribution

        with open(os.path.join(tree, "README.md"), encoding="utf-8") as f:
            index = f.read()
        for name in RUNTIME_DISTRIBUTIONS:
            try:
                distribution(name)
            except PackageNotFoundError:
                continue
            assert name in index, (
                f"{name} appears nowhere in the shipped index, so its absence "
                "from the tree carries no explanation"
            )

    def test_build_tools_that_are_not_shipped_are_not_documented(self, tree: str) -> None:
        """Terms for software that is not in the archive are noise in it."""
        packaged = os.listdir(os.path.join(tree, "python"))
        for tool in ("pytest", "ruff", "setuptools"):
            assert tool not in packaged


class TestWhatCountsAsALicenceFile:
    """Three shapes, because Playwright uses all three.

    A file named like a licence, a file in a directory named like licences,
    and a file named after the code it covers with the word appended. The
    third was not matched at first, and it is where 149 KB of Playwright's
    notices live.
    """

    def test_named_like_one(self) -> None:
        assert _is_licence(["LICENSE"])
        assert _is_licence(["COPYING.txt"])
        assert _is_licence(["driver", "package", "NOTICE"])
        assert _is_licence(["ThirdPartyNotices.txt"])

    def test_housed_in_a_licences_directory(self) -> None:
        assert _is_licence(["licenses", "anything.txt"])
        assert _is_licence(["licences", "freetype"])

    def test_named_after_what_it_covers(self) -> None:
        assert _is_licence(["lib", "utilsBundle.js.LICENSE"])
        assert _is_licence(["lib", "webp_codec.LICENSE"])
        assert _is_licence(["serverRegistry.js.LICENSE"])

    def test_and_not_everything_else(self) -> None:
        assert not _is_licence(["driver", "node"])
        assert not _is_licence(["package", "lib", "utilsBundle.js"])
        assert not _is_licence(["README.md"])


class TestLicencePathHandling:
    """Two licence files with the same name must not become one.

    Wheels put licence texts both beside METADATA and under a ``licenses/``
    directory, and Playwright ships eight at four different depths. Writing
    them by base name leaves a tree that looks complete and has silently kept
    only the last, which is the single failure this collector exists to
    prevent.
    """

    def test_the_conventional_licenses_prefix_is_dropped(self) -> None:
        """It is packaging convention, not information."""
        assert _flatten([("licenses/LICENSE", "x")]) == [("LICENSE", "x")]

    def test_but_not_when_that_would_collide(self) -> None:
        """A wheel shipping both keeps both, under distinct names."""
        flattened = dict(_flatten([("LICENSE", "outer"), ("licenses/LICENSE", "inner")]))
        assert flattened == {"LICENSE": "outer", "licenses/LICENSE": "inner"}

    def test_deeper_paths_are_preserved(self) -> None:
        """Playwright's driver notices differ only by path."""
        vendored = [
            ("driver/LICENSE", "the aggregate"),
            ("driver/package/LICENSE", "the npm package"),
            ("driver/package/lib/webp_codec.LICENSE", "webp"),
        ]
        flattened = dict(_flatten(vendored))
        assert len(flattened) == 3
        assert flattened["driver/LICENSE"] == "the aggregate"
