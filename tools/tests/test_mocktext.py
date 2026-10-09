# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of how the fake back compares a searched text: whatever its case and its accents.

The rule of every search of the contract (docs/api/README.md, « Une recherche… »), decided by the
author on 2026-10-09 — not the Vérif of a requirement: none is cited (WF-QUA-0010). A search
transliterates as PostgreSQL's ``unaccent`` does with the table it ships, then lowers, as the
service will by ``lower(unaccent(…))`` (EP-03).
"""

import json

import pytest

from wftools import REPOSITORY, mocktext


@pytest.mark.parametrize("text", ["etudes", "ETUDES", "Études", "études", "EtUdEs"])
def test_a_search_finds_a_text_whatever_its_case_and_its_accents(text: str) -> None:
    assert mocktext.holds("Études de détail", text)
    assert mocktext.holds("ETUDES", text)


@pytest.mark.parametrize(
    ("value", "text"),
    [
        ("Études", "etudes"),
        ("Main-d'œuvre", "main-d'oeuvre"),
        ("Main-d'œuvre", "MAIN-D'OEUVRE"),
        ("Main-d'oeuvre", "Main-d'Œuvre"),
        ("Straße", "strasse"),
        ("Strasse", "STRAẞE"),
        ("Søren", "soren"),
        ("SØREN", "Soren"),
        ("Łódź", "lodz"),
    ],
)
def test_a_search_transliterates_as_unaccent_does(value: str, text: str) -> None:
    assert mocktext.holds(value, text)


def test_a_search_finds_the_labour_nature_of_the_witness_written_without_its_ligature() -> None:
    natures = json.loads((REPOSITORY / "fixtures/api/cost_types.json").read_text(encoding="utf-8"))
    labels = [each["label"] for each in natures["value"]["items"]]
    assert [label for label in labels if mocktext.holds(label, "oeuvre")] == ["Main-d'œuvre"]


def test_a_text_is_transliterated_then_lowered_and_nothing_else() -> None:
    assert mocktext.folded("Inès Roux") == "ines roux"
    assert mocktext.folded("Ingélec Études, Noël, ÇA") == "ingelec etudes, noel, ca"
    assert mocktext.folded("Main-d'Œuvre, Æther, Straße, ẞ, Søren, Đorđe") == (
        "main-d'oeuvre, aether, strasse, ss, soren, dorde"
    )
    # A decomposed accent is a combining mark, which the table drops as it drops a composed one.
    assert mocktext.folded("E\u0301tudes") == "etudes"
    assert mocktext.holds("Inès Roux", "ines")
    assert mocktext.holds("ines.roux@example.com", "Inès")
    assert not mocktext.holds("Inès Roux", "inez")
    assert not mocktext.holds("Études", "etudes de")


def test_a_character_the_table_does_not_name_stays_itself() -> None:
    # « й » and « Ǣ » decompose under NFD, yet the shipped table names neither: unaccent leaves
    # them as they are, and so does a search — lowered only.
    assert "й" not in mocktext.UNACCENT.rules
    assert "Ǣ" not in mocktext.UNACCENT.rules
    assert mocktext.UNACCENT("й Ǣ") == "й Ǣ"
    assert mocktext.folded("Й Ǣ") == "й ǣ"
    assert not mocktext.holds("Й", "и")


def test_the_shipped_table_is_read_as_unaccent_reads_it() -> None:
    rules = mocktext.UNACCENT.rules
    assert (rules["œ"], rules["Œ"], rules["æ"]) == ("oe", "OE", "ae")
    assert (rules["ß"], rules["ẞ"]) == ("ss", "SS")
    assert (rules["ø"], rules["ł"], rules["đ"]) == ("o", "l", "d")
    # A translation after blanks, as the vulgar fractions have it, and a source alone, dropped.
    assert rules["¼"] == "1/4"
    assert rules["\u0301"] == ""
    assert not any(source.startswith("#") for source in rules)


def test_the_longest_source_of_a_table_is_replaced_first() -> None:
    table = mocktext.Unaccent.read("# header\n\nae\tX\na\tY\n\u0301\n")
    assert table.rules == {"ae": "X", "a": "Y", "\u0301": ""}
    assert table.longest == 2
    assert table("aea\u0301b") == "XYb"


def test_a_rule_of_more_than_two_strings_is_refused() -> None:
    with pytest.raises(ValueError, match="more than two strings"):
        mocktext.Unaccent.read("¼\t1 / 4\n")
