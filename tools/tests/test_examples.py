# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the listing of numeric examples and of the fixtures that cite them."""

import json
from pathlib import Path

import pytest

from wftools import examples, projection
from wftools.examples import Example

pytestmark = pytest.mark.requirement("WF-QUA-0020-A")

BLOCK = """\
```yaml exigence
section: "3.4"
id: "{identifier}"
titre: "Titre"
flexibilite: "F0"
fbs: "FBS-2.1"
pbs: "PBS-2.3"
corps: "Corps."
motif: "Motif."
verification: "{verification}"
```
"""


def requirements(**verifications: str) -> tuple[projection.Requirement, ...]:
    """Read requirements made of these Vérif fields, keyed by identifier."""
    text = "".join(
        BLOCK.format(identifier=identifier.replace("_", "-"), verification=verification)
        for identifier, verification in verifications.items()
    )
    return projection.parse(text)


@pytest.mark.parametrize(
    ("sentence", "numeric"),
    [
        ("Une offre à 40 % et 100 000 de devis contribue pour 40 000.", True),
        ("Un montant de 0,10 additionné dix fois donne exactement 1,00.", True),
        ("Un projet passé à Perdu le 15 mars compte parmi les offres closes.", True),
        ("La règle de WF-ARC-0010-A s'applique, comme au §4.4.1.", False),
        ("La fonction FBS-4.3.2 et le composant PBS-2.3 sont concernés.", False),
        ("Une exigence F0 est couverte par un test.", False),
        ("Deux projets sont comparés.", False),
    ],
)
def test_a_numeric_example_carries_a_number_that_is_no_code(sentence: str, numeric: bool) -> None:
    assert examples.is_numeric(sentence) is numeric


def test_only_the_numeric_sentences_of_product_requirements_are_listed() -> None:
    found = examples.examples(
        requirements(
            WF_PTF_0020_A="Le pipeline est pondéré. Une offre à 40 % pèse 40 000.",
            WF_EXA_0010_A="Un écran liste 10 utilisateurs.",
        )
    )
    assert found == [Example("WF-PTF-0020-A", "Une offre à 40 % pèse 40 000.")]


def test_the_key_is_the_requirement_and_the_fingerprint_of_the_text() -> None:
    example = Example("WF-PTF-0020-A", "Une offre à 40 % pèse 40 000.")
    assert example.key.startswith("WF-PTF-0020-A#")
    assert example.key != Example("WF-PTF-0020-A", "Une offre à 50 % pèse 50 000.").key


def test_inserting_a_sentence_keeps_the_keys_of_the_others() -> None:
    before = examples.examples(requirements(WF_PTF_0020_A="Une offre à 40 % pèse 40 000."))
    after = examples.examples(
        requirements(WF_PTF_0020_A="Une offre à 10 % pèse 10 000. Une offre à 40 % pèse 40 000.")
    )
    assert before[0].key == after[1].key


def test_the_listing_is_stable_json() -> None:
    found = [Example("WF-PTF-0020-A", "Une offre à 40 % pèse 40 000.")]
    document = json.loads(examples.listing(found))
    assert document["examples"] == [
        {"key": found[0].key, "requirement": "WF-PTF-0020-A", "sentence": found[0].sentence}
    ]
    assert examples.listing(found) == examples.listing(list(found))


@pytest.fixture
def fixtures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the tool at an empty fixtures directory inside a sample repository."""
    directory = tmp_path / "fixtures"
    directory.mkdir()
    monkeypatch.setattr(examples, "REPOSITORY", tmp_path)
    monkeypatch.setattr(examples, "FIXTURES", directory)
    monkeypatch.setattr(examples, "LISTING", directory / "examples.json")
    return directory


def test_a_fixture_cites_keys(fixtures: Path) -> None:
    (fixtures / "portfolio.json").write_text('{"examples": ["K#1"], "offers": []}')
    (fixtures / "api.json").write_text('{"projects": []}')
    assert examples.cited(fixtures) == {"fixtures/portfolio.json": ["K#1"]}


def test_a_fixture_with_malformed_examples_is_refused(fixtures: Path) -> None:
    (fixtures / "bad.json").write_text('{"examples": "K#1"}')
    with pytest.raises(ValueError, match="must be a list of keys"):
        examples.cited(fixtures)


@pytest.mark.usefixtures("fixtures")
def test_a_key_that_is_gone_is_a_problem() -> None:
    found = [Example("WF-PTF-0020-A", "Une offre à 40 % pèse 40 000.")]
    examples.LISTING.write_text(examples.listing(found), encoding="utf-8")
    problems = examples.check(found, {"fixtures/portfolio.json": [found[0].key, "WF-PTF-0020-A#0"]})
    expected = "fixtures/portfolio.json: cites WF-PTF-0020-A#0, which is no sentence"
    assert problems == [f"{expected} of the document any more"]


@pytest.mark.usefixtures("fixtures")
def test_an_outdated_listing_is_a_problem() -> None:
    found = [Example("WF-PTF-0020-A", "Une offre à 40 % pèse 40 000.")]
    examples.LISTING.write_text("{}\n", encoding="utf-8")
    assert examples.check(found, {}) == ["fixtures/examples.json is outdated: run make fixtures"]


def test_the_listing_of_the_repository_is_up_to_date() -> None:
    assert examples.main([]) == 0
