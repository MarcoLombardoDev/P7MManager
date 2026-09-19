#!/usr/bin/env python
# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Guards against the documentation drifting away from the product — and away
from the sibling products it is deliberately kept in step with.

They share a README skeleton, a commercial licence structure and a price-list
format on purpose: the same clause sits at the same number in every one of
them, so a buyer or a contributor who has read one has read them all. Nothing
enforces that at runtime, and a drifting document is invisible to anyone
editing the code — so it is checked here.

A price quoted in two places will eventually disagree with itself, and a
screenshot referenced after being renamed leaves a broken image on the
project's front page. Both are checked here too.
"""

from __future__ import annotations

import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_NAME = "P7M Manager"

#: The README section skeleton shared by the sibling products, in order. A
#: section renamed, dropped or reordered here has to be renamed, dropped or
#: reordered in all of them, or this fails — which is the point.
README_SKELETON = (
    "Screenshots",
    "Table of Contents",
    f"What {APP_NAME} is",
    "Features",
    "Download",
    "Installation from source",
    "Usage",
    "How it works",
    "Requirements",
    "Development",
    "Testing",
    "Building a standalone executable",
    "Troubleshooting",
    "Scope and limitations",
    "License & Commercial Licensing",
    "Contributing",
    "Disclaimer",
)

#: The commercial licence's section structure, likewise shared by all of them.
LICENCE_SECTIONS = (
    "1. Do you actually need this?",
    "2. Licence structure",
    "3. What the Commercial licence grants",
    "4. What the Redistribution licence grants",
    "5. Price list",
    "6. Support",
    "7. Custom development",
    "8. How to buy",
    "9. Term, warranty and liability",
    "10. What is *not* included",
    "11. Third-party components",
    "12. Contributors",
    "13. Contact",
    "14. Terminology",
)


def read(name: str) -> str:
    with open(os.path.join(REPO, name), encoding="utf-8") as fh:
        return fh.read()


def headings(text: str, level: int) -> list[str]:
    """Every heading of exactly `level`, in order, outside code fences."""
    found, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(rf"^#{{{level}}} (?!#)(.+)$", line)
        if match:
            found.append(match.group(1).strip())
    return found


# ---------------------------------------------------------------------------
# The shared skeleton
# ---------------------------------------------------------------------------

def test_the_readme_follows_the_shared_section_skeleton():
    """The sibling READMEs answer the same questions in the same order.
    A reader who knows where "Download" sits in one knows where it sits in all
    of them; a contributor who adds a section to one is told to add it to the
    rest.
    """
    assert tuple(headings(read("README.md"), 2)) == README_SKELETON


def test_the_commercial_licence_follows_the_shared_section_structure():
    """Same reasoning, applied to the document that is actually a contract:
    §11 is Third-party components in every product, so a cross-reference to it
    from anywhere means the same thing.
    """
    found = tuple(headings(read("COMMERCIAL-LICENSE.md"), 2))
    assert found == LICENCE_SECTIONS


def test_every_internal_readme_link_points_at_a_heading_that_exists():
    """A table of contents is the first thing a reader clicks and the first
    thing a restructure breaks.
    """
    text = read("README.md")
    available = set()
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r"^#{1,6} (.+)$", line)
        if not match:
            continue
        slug = match.group(1).strip().lower()
        slug = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", slug)
        slug = re.sub(r"[`*]", "", slug)
        slug = re.sub(r"[^\w\s-]", "", slug)
        available.add(re.sub(r"[ \t]", "-", slug.strip()))

    broken = sorted({t for t in re.findall(r"\]\(#([\w-]+)\)", text) if t not in available})
    assert not broken, f"README links to headings that do not exist: {broken}"


# ---------------------------------------------------------------------------
# Screenshots
# ---------------------------------------------------------------------------

def test_every_referenced_image_exists():
    """A renamed capture must not leave a broken image in the README."""
    missing = [target for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", read("README.md"))
               if not target.startswith("http")
               and not os.path.exists(os.path.join(REPO, target))]
    assert not missing, f"README references missing images: {missing}"


# ---------------------------------------------------------------------------
# Licensing
# ---------------------------------------------------------------------------

#: Tiers that must exist under the same name in both documents. Commercial and
#: Redistribution each cover several sub-tiers (Small/Medium/Large/Enterprise,
#: Standard/Enterprise) that the README does not necessarily spell out row by
#: row, so matching is done at the licence-family level; their figures are
#: checked below by amount instead of by sub-tier name.
TIERS = ("Community", "Commercial", "Redistribution")


def section(text: str, heading: str, stop: str) -> str:
    """The slice of a document between two headings."""
    start = text.index(heading)
    end = text.index(stop, start)
    return text[start:end]


def tier_rows(text: str) -> dict[str, str]:
    """Map each tier name to the raw table row quoting its price."""
    found: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        for tier in TIERS:
            if f"**{tier}" in line:
                found.setdefault(tier, line)
    return found


def amounts(text: str) -> set[str]:
    """Every monetary figure in `text`, normalised."""
    return {a.replace(",", "").replace(" ", "")
            for a in re.findall(r"€\s?[\d,]+", text)}


def test_the_price_list_agrees_with_itself():
    """The README summarises the price list; COMMERCIAL-LICENSE.md is the
    source of truth. Two copies of a number is one copy too many, so they are
    compared rather than trusted.

    Compared by amount rather than by row, because the README legitimately
    collapses rows the licence keeps separate. What must never differ is the
    set of figures a reader is quoted.
    """
    terms = read("COMMERCIAL-LICENSE.md")
    # The README's licensing section summarises the whole offer, so it is
    # compared against both places the licence quotes a figure: the price list
    # and the custom-development day rate.
    licence = (amounts(section(terms, "## 5. Price list", "## 6."))
               | amounts(section(terms, "## 7. Custom development", "## 8.")))
    readme = amounts(section(read("README.md"),
                             "### Commercial Licensing", "## Contributing"))

    assert readme == licence, (f"README quotes {sorted(readme)}, "
                               f"COMMERCIAL-LICENSE.md quotes {sorted(licence)}")


def test_the_perpetual_option_is_three_times_the_annual_rate():
    """The rule the four price lists share. Stated once in the licence and
    repeated in the README, so it is the kind of thing that silently stops
    being true after one edit.
    """
    annual, perpetual = {}, {}
    for line in section(read("COMMERCIAL-LICENSE.md"),
                        "## 5. Price list", "## 6.").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        label = re.sub(r"[*]", "", cells[0]).strip()
        figures = re.findall(r"€([\d,]+)", line)
        # "from €N" is a starting price on a negotiated tier, and the
        # discounts table below quotes a revenue threshold, not a price.
        if not figures or "from" in line or not label.startswith(
                ("Commercial — ", "Redistribution — ")):
            continue
        (annual if "/ year" in line else perpetual)[label] = int(
            figures[0].replace(",", ""))

    priced = ("Commercial — Small", "Commercial — Medium", "Commercial — Large",
              "Redistribution — Standard")
    assert set(perpetual) == set(priced), (
        f"the perpetual table lists {sorted(perpetual)}, expected {sorted(priced)}")
    for tier in priced:
        assert perpetual[tier] == annual[tier] * 3, (
            f"{tier}: perpetual €{perpetual[tier]:,} is not three times "
            f"annual €{annual[tier]:,}")


def test_every_tier_is_named_in_both_documents():
    """A tier the README never mentions is a tier nobody will ask about."""
    licence = tier_rows(section(read("COMMERCIAL-LICENSE.md"), "## 5. Price list", "## 6."))
    readme = tier_rows(section(read("README.md"),
                               "### Commercial Licensing", "## Contributing"))

    assert set(licence) == set(TIERS), f"tiers missing from the licence: {sorted(licence)}"
    assert set(readme) == set(TIERS), f"tiers missing from the README: {sorted(readme)}"


def test_the_free_tier_stays_free():
    """The Community row is the one a hostile reading would quietly reprice. It
    must cost nothing, in both documents, in words a reader cannot misread.
    """
    for document, heading, stop in (
            ("COMMERCIAL-LICENSE.md", "## 5. Price list", "## 6."),
            ("README.md", "### Commercial Licensing", "## Contributing")):
        row = tier_rows(section(read(document), heading, stop))["Community"]
        assert re.search(r"\*\*(Free|€0)\*\*", row), f"{document}: {row.strip()}"


def test_the_agpl_text_is_not_edited():
    """The AGPL may be applied to a work, never rewritten. Adding commercial
    terms to LICENSE itself would make the licence unrecognisable and
    unenforceable — and a reflowed copy is an edited copy: the licence's own
    header says changing it is not allowed, and GitHub stops recognising it.
    """
    licence = read("LICENSE")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in licence
    assert "Version 3, 19 November 2007" in licence
    assert "TERMS AND CONDITIONS" in licence

    # Deliberately not the word "price": the AGPL preamble uses it itself,
    # in "free as in freedom, not price". And matched on word boundaries,
    # because "VAT" is a substring of "private".
    for word in ("€", "VAT", "invoice", "per year", "subscription"):
        pattern = re.escape(word) if not word.isalpha() else rf"\b{word}\b"
        assert not re.search(pattern, licence, re.IGNORECASE), (
            f"LICENSE must stay verbatim AGPL, found {word!r} — "
            "commercial terms belong in COMMERCIAL-LICENSE.md")


def test_the_commercial_terms_do_not_contradict_the_agpl_on_internal_use():
    """Regression against the commonest dual-licensing lie. The AGPL grants
    free internal use to organisations of any size; a price list that implies
    otherwise would be misrepresenting the licence the project ships under.
    """
    terms = read("COMMERCIAL-LICENSE.md").lower()

    # Matched on substance rather than on an exact sentence: the wording has
    # already been rewritten once, and pinning the phrasing only teaches the
    # next editor to delete the test.
    match = re.search(r"organisations of any size", terms)
    assert match, "the terms must state that internal use is free at any size"
    assert "free" in terms[max(0, match.start() - 160):match.end()], (
        "'organisations of any size' must appear in a sentence about it being free")


CONTACT = "marco.lombardo@gmail.com"


@pytest.mark.parametrize("document", ["README.md", "COMMERCIAL-LICENSE.md", "CLA.md"])
def test_a_buyer_can_find_a_way_to_get_in_touch(document):
    """A price list nobody can respond to is decoration."""
    assert CONTACT in read(document)


def test_the_mail_subject_is_the_same_wherever_the_reader_clicks():
    """The README and the licence both open a mail client. The same enquiry
    arriving under two different subjects makes it look like two different
    enquiries — and the drift is invisible, because nobody clicks every link.
    """
    # The name has a space in it, and a mailto subject is percent-encoded:
    # the other products in this family are one word and never had to notice.
    slug = APP_NAME.replace(" ", "%20")
    expected = {f"subject={slug}%20commercial%20licence%20enquiry"}
    for document in ("README.md", "COMMERCIAL-LICENSE.md"):
        subjects = set(re.findall(r"subject=[^)\s]+", read(document)))
        assert subjects, f"{document} has no mailto subject to check"
        assert subjects == expected, f"{document} uses {sorted(subjects)}, expected {expected}"


def test_no_placeholder_survived_into_the_published_terms():
    """Regression: the contact address started life as a marked placeholder. A
    price list shipped with `(to be published)` still in it is worse than one
    with no price list at all.
    """
    terms = read("COMMERCIAL-LICENSE.md").lower()
    for placeholder in ("to be published", "tbd", "todo", "xxx", "your-domain"):
        assert placeholder not in terms, f"placeholder left in the terms: {placeholder!r}"


class TestTheVersionAndTheChangelogAgree:
    """A release is one edit to ``__version__`` plus a tag, and the workflow
    checks the tag against the source. Nothing checked the CHANGELOG, so the
    version could be bumped and shipped with no section describing what
    changed -- and the notes point the reader straight at that file.
    """

    def version(self) -> str:
        from p7mmanager import __version__

        return __version__

    def test_the_changelog_has_a_section_for_it(self):
        changelog = read("CHANGELOG.md")
        version = self.version()
        assert f"## [{version}]" in changelog, (
            f"__version__ is {version} and CHANGELOG.md has no ## [{version}] "
            "section; the release notes link to it"
        )

    def test_pyproject_carries_the_same_version(self):
        """Two declarations, and a wheel built from a disagreeing one is
        mislabelled where nobody would look."""
        pyproject = read("pyproject.toml")
        assert f'version = "{self.version()}"' in pyproject

    def test_it_is_the_newest_section(self):
        """Below an older one it would be a version that shipped before a
        version already released, which is not what the file means."""
        changelog = read("CHANGELOG.md")
        released = [
            line for line in changelog.splitlines()
            if line.startswith("## [") and "Unreleased" not in line
        ]
        assert released, "CHANGELOG.md lists no released version"
        assert released[0].startswith(f"## [{self.version()}]"), (
            f"the newest section is {released[0]!r}, not the current version"
        )


@pytest.mark.parametrize(
    "document", ["README.md", "COMMERCIAL-LICENSE.md", "CLA.md", "CONTRIBUTING.md",
                 "CHANGELOG.md", "LICENSE"])
def test_the_shared_document_set_is_present(document):
    """The sibling products carry the same six documents. One missing is one
    the others link to and this one does not have.
    """
    assert os.path.exists(os.path.join(REPO, document))


@pytest.mark.parametrize("document", ["COMMERCIAL-LICENSE.md", "CLA.md", "LICENSE"])
def test_licensing_documents_are_reachable_from_the_readme(document):
    assert document in read("README.md"), f"{document} is not linked from the README"


class TestThirdPartySection:
    """§11 is what a buyer reads before signing, so it has to be true.

    requirements.txt names one dependency, which makes a summary of it a
    misleading answer to what a redistributor is taking on. The archive holds
    two hundred-odd native binaries: Qt under LGPL-3.0 with obligations that
    outlive the sale, the system libraries the runner linked against, and
    CPython, which is frozen in and appears in no dependency list anywhere.
    §11 has to describe that, and say which of it P7M Manager is in a position
    to license and which of it it is not.
    """

    @pytest.fixture(scope="class")
    def section(self) -> str:
        terms = read("COMMERCIAL-LICENSE.md")
        return terms[
            terms.index("## 11. Third-party components"):terms.index("## 12. Contributors")
        ]

    @pytest.fixture(scope="class")
    def prose(self, section: str) -> str:
        """The same section as one lowercase line.

        Phrases here are checked against this rather than against the raw
        text: "The Qt Company" wrapped across two lines is still the same
        statement, and a test that a reflow can break teaches the next editor
        to delete it rather than to keep the statement true.
        """
        import re as _re

        return _re.sub(r"\s+", " ", section).lower()

    def test_it_distinguishes_the_source_dependencies_from_the_shipped_bundle(
        self, section: str, prose: str
    ) -> None:
        """A redistributor ships the bundle, not requirements.txt."""
        assert "source" in prose
        assert "THIRD-PARTY-LICENSES.md" in section, (
            "§11 does not point at the full inventory, so it remains a summary "
            "of a handful of components presented as the whole picture"
        )

    def test_no_component_is_marked_simply_permitted(self, section: str) -> None:
        """A tick column invites exactly the wrong conclusion."""
        assert "✅" not in section, (
            "a tick in §11 reads as permission granted; this section grants none"
        )

    @pytest.mark.parametrize(
        "obligation",
        [
            # Each of these is carried by something the archives actually
            # contain, and each was absent from a first draft of this section.
            "GCC Runtime Library Exception",
            "Microsoft",
            "LGPL-2.1",
            "Bootloader Exception",
        ],
    )
    def test_obligations_carried_by_the_bundle_are_named(
        self, section: str, obligation: str
    ) -> None:
        assert obligation in section

    def test_the_gpl3_library_that_would_otherwise_ship_is_disclosed(
        self, prose: str
    ) -> None:
        """PyInstaller collects the stdlib's readline extension by default, and
        that links libreadline: GPL-3.0-or-later with no linking exception, in
        an archive also offered under a commercial redistribution licence. It
        is excluded in p7mmanager.spec, and §11 says so rather than leaving a reader
        to wonder whether anyone looked.
        """
        assert "libreadline" in prose
        assert "no linking exception" in prose

    def test_the_qt_position_is_stated_and_not_softened(self, prose: str) -> None:
        """P7M Manager cannot sublicense Qt. A buyer of a Redistribution licence still
        deals with The Qt Company on Qt's terms, and one who learns that after
        paying has bought the wrong thing.
        """
        assert "sublicense" in prose or "sublicence" in prose
        assert "qt company" in prose
        assert "lgpl-3.0" in prose

    def test_it_still_disclaims_being_a_legal_opinion(self, prose: str) -> None:
        """More detail is not more authority."""
        assert "not a legal opinion" in prose
