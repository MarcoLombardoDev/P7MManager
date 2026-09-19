# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.

"""Every phrase the interface shows must have an Italian.

The table is a plain dict, so it can be checked: the source is walked for
``tr(...)`` calls and any literal missing from the table fails here. That is
the check a compiled ``.qm`` file cannot give, and the reason the table was
chosen over ``QTranslator``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from p7mmanager.core import payload
from p7mmanager.i18n import (
    TRANSLATIONS,
    Language,
    current_language,
    detect_language,
    set_language,
    tr,
    tr_message,
)

PACKAGE = Path(__file__).resolve().parent.parent / "p7mmanager"


def _translated_literals() -> list[tuple[str, str, int]]:
    """Every literal string passed to ``tr``/``tr_message`` in the package."""
    found: list[tuple[str, str, int]] = []
    for source in sorted(PACKAGE.rglob("*.py")):
        if source.name == "i18n.py":
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in ("tr", "tr_message") or not node.args:
                continue
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                found.append((argument.value, source.name, node.lineno))
    return found


def test_the_source_is_walked_and_finds_something():
    literals = _translated_literals()
    assert len(literals) > 60, "the AST walk stopped finding calls; fix the test"


def test_every_phrase_has_an_italian():
    missing = sorted(
        f"{name}:{line}: {text!r}"
        for text, name, line in _translated_literals()
        if text not in TRANSLATIONS
    )
    assert not missing, "phrases with no Italian:\n" + "\n".join(missing)


def test_payload_labels_are_translated():
    kinds = [
        value
        for value in vars(payload).values()
        if isinstance(value, payload.PayloadKind)
    ]
    assert kinds
    missing = [kind.label for kind in kinds if kind.label not in TRANSLATIONS]
    assert not missing


# Words that are the same in both languages. Listed rather than tolerated in
# general, so a genuinely forgotten translation still fails the test below.
IDENTICAL_IN_ITALIAN = {"File", "&File"}


def test_no_translation_is_left_as_english():
    same = [
        key
        for key, value in TRANSLATIONS.items()
        if key == value and key not in IDENTICAL_IN_ITALIAN
    ]
    assert not same, f"untranslated entries: {same}"


@pytest.mark.parametrize(
    "locale_name, expected",
    [("it_IT", Language.ITALIAN), ("it-CH", Language.ITALIAN),
     ("en_GB", Language.ENGLISH), (None, Language.ENGLISH), ("", Language.ENGLISH)],
)
def test_detect_language(locale_name, expected):
    assert detect_language(locale_name) is expected


def test_english_returns_the_source_string():
    set_language(Language.ENGLISH)
    assert current_language() is Language.ENGLISH
    assert tr("Add files") == "Add files"


def test_italian_translates():
    set_language(Language.ITALIAN)
    assert tr("Add files") == "Aggiungi file"
    assert tr("something never written") == "something never written"


def test_engine_messages_keep_their_variable_tail():
    set_language(Language.ITALIAN)
    assert tr_message("read failed: Permission denied") == (
        "lettura non riuscita: Permission denied"
    )
    assert tr_message("file too large (700 MB)") == "file troppo grande (700 MB)"
    assert tr_message("") == ""


def test_language_label_is_written_in_itself():
    assert Language.ITALIAN.label == "Italiano"
    assert Language.ENGLISH.label == "English"
