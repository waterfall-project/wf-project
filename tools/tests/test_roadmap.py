# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the confrontation of the roadmap with the requirements of the document."""

import pytest

from wftools import projection, roadmap

BLOCK = """\
```yaml exigence
section: "4.7"
id: "{identifier}"
titre: "Titre"
flexibilite: "F0"
fbs: "FBS-4"
pbs: "PBS-5.2"
corps: "Corps."
motif: "Motif."
verification: "Le rapport cite chaque exigence. Le retrait d’un test la découvre."
```
"""

EPIC = """\
---
id: EP-09
titre: Un EPIC d'essai
statut: {status}
depend_de: rien
issue:
---

# EP-09 — Essai

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-QUA-0010-A` | Traçabilité | {scope} | US-0900 |

---

## US-0900 — Une US d'essai

- **statut** : à faire
- **exigences** : {cited}
- **opérations** : aucune

**Critères d'acceptation.**

- `WF-QUA-0010-A` — « Le rapport cite chaque exigence. »
- écart : « Le retrait d'un test la
  découvre. » attend un autre EPIC.
"""


def document(*identifiers: str) -> tuple[projection.Requirement, ...]:
    """Read requirements with these identifiers and the same Vérif field."""
    return projection.parse("".join(BLOCK.format(identifier=i) for i in identifiers))


def epic(
    status: str = "en cours",
    scope: str = "entière",
    cited: str = "`WF-QUA-0010-A`",
    text: str = EPIC,
) -> roadmap.Epic:
    """Read the sample epic, with some of its fields replaced."""
    return roadmap.parse_epic("EP-09", text.format(status=status, scope=scope, cited=cited))


def problems(*epics: roadmap.Epic, identifiers: tuple[str, ...] = ("WF-QUA-0010-A",)) -> list[str]:
    """Confront epics with a document of these requirements."""
    return roadmap.confront(epics, document(*identifiers)).problems


def test_an_epic_is_read() -> None:
    read = epic()
    assert (read.identifier, read.status) == ("EP-09", "en cours")
    assert read.rows == (roadmap.Row("WF-QUA-0010-A", closes=True),)
    assert [(s.identifier, s.requirements) for s in read.stories] == [
        ("US-0900", ("WF-QUA-0010-A",))
    ]


def test_a_coherent_epic_passes() -> None:
    assert problems(epic()) == []


def test_a_sentence_quoted_across_lines_and_apostrophes_is_found() -> None:
    assert problems(epic()) == []  # « d'un » in the story, « d’un » in the document


def test_an_unknown_identifier_fails() -> None:
    found = problems(epic(cited="`WF-QUA-0099-A`"))
    assert "US-0900: cites WF-QUA-0099-A, unknown" in found


def test_an_outdated_revision_fails() -> None:
    found = problems(epic(), identifiers=("WF-QUA-0010-B",))
    assert "EP-09 table: cites WF-QUA-0010-A, now WF-QUA-0010-B" in found


def test_a_missing_sentence_fails_naming_story_requirement_and_sentence() -> None:
    text = EPIC.replace("- `WF-QUA-0010-A` — « Le rapport cite chaque exigence. »\n", "")
    found = problems(epic(text=text))
    assert found == [
        "US-0900: WF-QUA-0010-A: missing or truncated: « Le rapport cite chaque exigence. »"
    ]


def test_a_truncated_sentence_fails() -> None:
    text = EPIC.replace("« Le rapport cite chaque exigence. »", "« Le rapport cite chaque »")
    assert len(problems(epic(text=text))) == 1


def test_a_requirement_of_the_table_no_story_cites_fails() -> None:
    found = problems(epic(cited="aucune — outil du dépôt"))
    assert "EP-09: WF-QUA-0010-A is in the table but no story cites it" in found


def test_an_epic_to_plan_may_have_no_story_yet() -> None:
    assert problems(epic(status=roadmap.TO_PLAN, cited="aucune — outil du dépôt")) == []


@pytest.mark.parametrize(
    ("scopes", "closers"),
    [
        (("début — close en EP-10",), "no epic"),
        (("entière", "fin — amorcée en EP-09"), "EP-09, EP-10"),
    ],
)
def test_a_requirement_closed_by_no_epic_or_by_two_fails(
    scopes: tuple[str, ...], closers: str
) -> None:
    epics = [epic(scope=scope) for scope in scopes]
    epics = [
        roadmap.Epic(f"EP-{9 + n:02d}", e.status, e.rows, e.stories) for n, e in enumerate(epics)
    ]
    assert f"WF-QUA-0010-A: closed by {closers}, and by one epic only" in problems(*epics)


def test_uncited_requirements_are_listed_without_failing() -> None:
    findings = roadmap.confront((epic(),), document("WF-QUA-0010-A", "WF-QUA-0020-A"))
    assert findings.uncited == ["WF-QUA-0020-A"]
    assert findings.problems == ["WF-QUA-0020-A: closed by no epic, and by one epic only"]


def test_the_example_of_the_document_is_left_out() -> None:
    findings = roadmap.confront((epic(),), document("WF-QUA-0010-A", projection.EXAMPLE_IDENTIFIER))
    assert findings.problems == []
    assert findings.uncited == []


def test_the_roadmap_of_the_repository_holds() -> None:
    assert roadmap.main() == 0
