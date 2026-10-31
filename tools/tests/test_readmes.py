# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the check that holds the English READMEs of docs/ in step with their originals.

A check of the repository, which covers no requirement of the product: its tests cite none
(docs/dev/README-fr.md, « Un test qui cite son exigence »).
"""

from pathlib import Path

from wftools import readmes

ORIGINAL = """# Contrat

Une phrase.

## Conventions

### Identifiants

```bash
# un commentaire, pas un titre
make lint-openapi
```

## Décisions
"""
TRANSLATION = """# Contract

A sentence.

## Conventions

### Identifiers

```bash
# a comment, not a heading
make lint-openapi
```

## Decisions
"""


def docs(tmp_path: Path, pairs: dict[str, dict[str, str]]) -> Path:
    """Write a docs/ directory with, for each of its directories, the READMEs given."""
    root = tmp_path / "docs"
    for directory, files in pairs.items():
        (root / directory).mkdir(parents=True)
        for name, text in files.items():
            (root / directory / name).write_text(text, encoding="utf-8")
    return root


def test_the_headings_of_a_readme_are_read_in_order_outside_code_blocks() -> None:
    found = readmes.headings(ORIGINAL)
    assert [(h.line, h.level, h.text) for h in found] == [
        (1, 1, "Contrat"),
        (5, 2, "Conventions"),
        (7, 3, "Identifiants"),
        (14, 2, "Décisions"),
    ]


def test_a_code_block_opened_by_tildes_is_not_closed_by_backticks() -> None:
    text = "~~~\n```\n# not a heading\n~~~\n## Heading ##\n#hashtag\n"
    assert [(h.level, h.text) for h in readmes.headings(text)] == [(2, "Heading")]


def test_pairs_whose_headings_follow_one_for_one_pass(tmp_path: Path) -> None:
    root = docs(
        tmp_path,
        {
            "api": {"README-fr.md": ORIGINAL, "README.md": TRANSLATION},
            "tools": {},
        },
    )
    assert readmes.check(root) == []


def test_a_translation_missing_a_heading_is_named(tmp_path: Path) -> None:
    root = docs(
        tmp_path,
        {"api": {"README-fr.md": ORIGINAL, "README.md": TRANSLATION.replace("## Decisions\n", "")}},
    )
    (finding,) = readmes.check(root)
    assert finding.path == "docs/api/README.md"
    assert "3 heading(s), where README-fr.md has 4" in finding.reason
    assert "README-fr.md goes on with 'Décisions' at line 14" in finding.reason


def test_a_translation_with_a_heading_more_is_named(tmp_path: Path) -> None:
    root = docs(
        tmp_path,
        {"dev": {"README-fr.md": ORIGINAL, "README.md": TRANSLATION + "\n## Extra\n"}},
    )
    (finding,) = readmes.check(root)
    assert finding.path == "docs/dev/README.md"
    assert "5 heading(s), where README-fr.md has 4" in finding.reason
    assert "it goes on with 'Extra' at line 16" in finding.reason


def test_a_heading_of_another_level_is_named_at_its_rank(tmp_path: Path) -> None:
    root = docs(
        tmp_path,
        {
            "spec": {
                "README-fr.md": ORIGINAL,
                "README.md": TRANSLATION.replace("### Identifiers", "## Identifiers"),
            }
        },
    )
    (finding,) = readmes.check(root)
    assert finding.path == "docs/spec/README.md"
    assert finding.reason.startswith("heading 3 is of level 2 at line 7")
    assert "README-fr.md has level 3 at line 7 ('Identifiants')" in finding.reason


def test_an_original_without_its_translation_is_named(tmp_path: Path) -> None:
    root = docs(tmp_path, {"legal": {"README-fr.md": ORIGINAL}})
    assert [str(f) for f in readmes.check(root)] == [
        "docs/legal/README-fr.md: no English README.md next to it"
    ]


def test_a_translation_without_its_original_is_named(tmp_path: Path) -> None:
    root = docs(tmp_path, {"roadmap": {"README.md": TRANSLATION}})
    assert [str(f) for f in readmes.check(root)] == [
        "docs/roadmap/README.md: no French original README-fr.md next to it"
    ]
