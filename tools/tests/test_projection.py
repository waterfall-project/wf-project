# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the reader of the specification projection."""

import pytest

from wftools import projection
from wftools.projection import ProjectionError, Requirement

BLOCK = """\
```yaml exigence
section: "4.7"
id: "WF-QUA-0010-A"
titre: "Traçabilité des exigences par les tests"
flexibilite: "F0"
fbs: "FBS-4"
pbs: "PBS-5.2"
corps: "Chaque exigence F0 est couverte."
motif: "Une exigence sans test est une intention."
verification: "Le rapport cite chaque exigence. Le retrait d’un test la découvre."
```
"""


def block(**changes: str) -> str:
    """Return BLOCK with some field values replaced."""
    text = BLOCK
    for field, value in changes.items():
        start = text.index(f"{field}: ")
        end = text.index("\n", start)
        text = f'{text[:start]}{field}: "{value}"{text[end:]}'
    return text


def test_a_block_becomes_a_requirement() -> None:
    (requirement,) = projection.parse(BLOCK)
    assert requirement.identifier == "WF-QUA-0010-A"
    assert requirement.key == "WF-QUA-0010"
    assert requirement.revision == "A"
    assert requirement.title == "Traçabilité des exigences par les tests"
    assert requirement.flexibility == "F0"
    assert requirement.motive == "Une exigence sans test est une intention."


def test_text_around_blocks_is_ignored() -> None:
    text = f"# 4.7\n\nUn paragraphe.\n\n{BLOCK}\nUn autre.\n\n{block(id='WF-QUA-0020-A')}"
    assert [r.identifier for r in projection.parse(text)] == ["WF-QUA-0010-A", "WF-QUA-0020-A"]


def test_a_missing_field_is_refused() -> None:
    text = BLOCK.replace('motif: "Une exigence sans test est une intention."\n', "")
    with pytest.raises(ProjectionError, match=r"missing \['motif'\]"):
        projection.parse(text)


def test_an_unknown_field_is_refused() -> None:
    text = BLOCK.replace('section: "4.7"\n', 'section: "4.7"\nsource: "revue"\n')
    with pytest.raises(ProjectionError, match=r"unknown \['source'\]"):
        projection.parse(text)


@pytest.mark.parametrize("identifier", ["WF-QUA-0010", "WF-QUA-010-A", "wf-qua-0010-a"])
def test_a_malformed_identifier_is_refused(identifier: str) -> None:
    with pytest.raises(ProjectionError, match="malformed identifier"):
        projection.parse(block(id=identifier))


def test_a_repeated_identifier_is_refused() -> None:
    with pytest.raises(ProjectionError, match="appears twice"):
        projection.parse(BLOCK + BLOCK)


def test_the_example_is_not_mandatory() -> None:
    (example,) = projection.parse(block(id=projection.EXAMPLE_IDENTIFIER))
    assert example.is_example
    assert not example.is_mandatory


@pytest.mark.parametrize(("flexibility", "mandatory"), [("F0", True), ("F1", False), ("F2", False)])
def test_only_f0_is_mandatory(flexibility: str, mandatory: bool) -> None:
    (requirement,) = projection.parse(block(flexibilite=flexibility))
    assert requirement.is_mandatory is mandatory


def test_normalize_makes_apostrophes_and_spaces_plain() -> None:
    assert projection.normalize("L’API : « X »  ") == "L'API : « X »"


def test_sentences_split_on_full_stops_question_and_exclamation_marks() -> None:
    assert projection.sentences("Un. Deux ? Trois ! « Quatre. » Cinq.") == (
        "Un.",
        "Deux ?",
        "Trois !",
        "« Quatre. » Cinq.",
    )


def test_sentences_keep_section_numbers_and_decimals_whole() -> None:
    text = "Voir le §4.4.1 pour 0,917. Un indice de 1.5 reste entier."
    assert projection.sentences(text) == ("Voir le §4.4.1 pour 0,917.", "Un indice de 1.5 reste entier.")


def test_sentences_do_not_split_before_a_lowercase_word() -> None:
    assert projection.sentences("Le libellé « Annuler. » reste visible.") == (
        "Le libellé « Annuler. » reste visible.",
    )


def test_verification_sentences_are_normalized() -> None:
    (requirement,) = projection.parse(BLOCK)
    assert requirement.verification_sentences == (
        "Le rapport cite chaque exigence.",
        "Le retrait d'un test la découvre.",
    )


@pytest.fixture(scope="module")
def requirements() -> tuple[Requirement, ...]:
    """Every requirement of the projection of the document itself."""
    return projection.read()


class TestTheDocument:
    """The reader against the projection of the document itself."""

    def test_every_block_is_read(self, requirements: tuple[Requirement, ...]) -> None:
        text = projection.PROJECTION.read_text(encoding="utf-8")
        assert len(requirements) == text.count("```yaml exigence\n")

    def test_the_example_is_there_once(self, requirements: tuple[Requirement, ...]) -> None:
        assert [r.identifier for r in requirements if r.is_example] == [projection.EXAMPLE_IDENTIFIER]

    def test_every_mandatory_requirement_has_a_verification(
        self, requirements: tuple[Requirement, ...]
    ) -> None:
        mandatory = [r for r in requirements if r.is_mandatory]
        assert mandatory
        assert all(r.verification_sentences for r in mandatory)

    def test_a_known_verification_splits_as_quoted_in_the_roadmap(
        self, requirements: tuple[Requirement, ...]
    ) -> None:
        by_identifier = {r.identifier: r for r in requirements}
        assert by_identifier["WF-ARC-0010-A"].verification_sentences[1:] == (
            "Un module qui lit une table d'un autre module est rejeté par les contrôles "
            "de la chaîne CI/CD.",
            "L'API et le worker d'une installation portent la même version.",
        )
