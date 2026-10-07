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
famille: {family}
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
    family: str = "front, back",
) -> roadmap.Epic:
    """Read the sample epic, with some of its fields replaced."""
    filled = text.format(status=status, scope=scope, cited=cited, family=family)
    return roadmap.parse_epic("EP-09", filled)


def problems(*epics: roadmap.Epic, identifiers: tuple[str, ...] = ("WF-QUA-0010-A",)) -> list[str]:
    """Confront epics with a document of these requirements."""
    return roadmap.confront(epics, document(*identifiers)).problems


def test_an_epic_is_read() -> None:
    read = epic()
    assert (read.identifier, read.status) == ("EP-09", "en cours")
    assert read.families == ("front", "back")
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
        roadmap.Epic(f"EP-{9 + n:02d}", e.status, e.rows, e.stories, e.families)
        for n, e in enumerate(epics)
    ]
    assert f"WF-QUA-0010-A: closed by {closers}, and by one epic only" in problems(*epics)


@pytest.mark.parametrize("family", ["front", "back", "plateforme", "front, back, plateforme"])
def test_an_epic_declares_one_family_or_several(family: str) -> None:
    assert problems(epic(family=family)) == []


@pytest.mark.parametrize(
    ("family", "problem"),
    [
        ("", "EP-09: its front matter declares no famille (front, back, plateforme)"),
        ("front, métier", "EP-09: famille « métier » is unknown (front, back, plateforme)"),
        ("back, front, back", "EP-09: famille « back » is declared more than once"),
    ],
)
def test_a_missing_unknown_or_repeated_family_fails(family: str, problem: str) -> None:
    assert problems(epic(family=family)) == [problem]


def test_an_epic_without_a_family_field_fails() -> None:
    text = EPIC.replace("famille: {family}\n", "")
    assert problems(epic(text=text)) == [
        "EP-09: its front matter declares no famille (front, back, plateforme)"
    ]


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


MAKEFILE = """\
check: ## Run what the change touches
\t@echo check

lint-back: ## Lint
\t@echo lint
"""


def test_the_targets_of_a_makefile_are_read() -> None:
    assert roadmap.targets(MAKEFILE) == {"check", "lint-back"}


def test_a_command_an_agent_cites_must_exist() -> None:
    texts = {
        ".claude/agents/a.md": "Lance `make check`, puis `make lint-back` et `make lint-fron`."
    }
    assert roadmap.missing_commands(texts, roadmap.targets(MAKEFILE)) == [
        ".claude/agents/a.md: cites `make lint-fron`, which the Makefile does not define"
    ]


def test_a_command_with_arguments_is_read_by_its_target() -> None:
    texts = {
        "docs/dev/agents.md": "`make check BASE=origin/epic/EP-nn` et `make check-back TIER=full`"
    }
    assert roadmap.missing_commands(texts, {"check"}) == [
        "docs/dev/agents.md: cites `make check-back`, which the Makefile does not define"
    ]


@pytest.mark.parametrize(
    ("text", "target"),
    [
        ("`TIER=full make check-back`", "check-back"),
        ("`cd tools && make -s lint-tools`", "lint-tools"),
        ("`make -C .. mock`", "mock"),
        ("```bash\nmake e2e\n```", "e2e"),
    ],
)
def test_commands_are_found_in_any_code(text: str, target: str) -> None:
    assert roadmap.cited_targets(text) == {target}


def test_options_that_read_two_ways_do_not_backtrack() -> None:
    # Before the fix, this string ran for days: `-C -A` was a directory or two options.
    assert roadmap.cited_targets("`make " + "-C -A " * 40 + "!`") == set()
    assert roadmap.cited_targets("`make -C -A check`") == {"check"}


def test_a_pattern_of_targets_is_not_a_command() -> None:
    assert roadmap.cited_targets("`make check-<famille>`") == set()


def test_the_word_make_in_prose_is_not_a_command() -> None:
    assert roadmap.cited_targets("On make sure que tout passe, sans code.") == set()


def test_the_agents_of_the_repository_cite_existing_commands() -> None:
    defined = roadmap.targets(roadmap.MAKEFILE.read_text(encoding="utf-8"))
    texts = roadmap.agent_texts()
    assert ".claude/agents/python-developer.md" in texts
    assert "docs/dev/python.md" in texts
    assert "docs/dev/python-fastapi-expert.md" not in texts  # untracked: never read
    assert roadmap.missing_commands(texts, defined) == []


def test_a_wrapped_requirements_field_is_read_whole() -> None:
    text = EPIC.format(status="en cours", scope="entière", cited="x", family="back").replace(
        "- **exigences** : x",
        "- **exigences** : `WF-QUA-0010-A`,\n  `WF-QUA-0020-A`\n- **autre** : champ suivant",
    )
    (story,) = roadmap.parse_epic("EP-09", text).stories
    assert story.requirements == ("WF-QUA-0010-A", "WF-QUA-0020-A")
