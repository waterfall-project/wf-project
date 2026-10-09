# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the inventory of the contract."""

from pathlib import Path

import inventory
import pytest


def test_the_inventory_reads_the_contract_and_neither_its_bundle_nor_its_lint_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "openapi.yaml",
        "paths/projects.yaml",
        "components/schemas/projects.yaml",
        "waterfall.bundle.yaml",
        "redocly.yaml",
        "tools/settings.yaml",
    ):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("", encoding="utf-8")
    monkeypatch.setattr(inventory, "ROOT", tmp_path)

    read = [path.relative_to(tmp_path).as_posix() for path in inventory.contract_sources()]

    assert read == ["openapi.yaml", "paths/projects.yaml", "components/schemas/projects.yaml"]


def _paths(root: Path, *families: str) -> None:
    for family in families:
        (root / "paths" / f"{family}.yaml").parent.mkdir(parents=True, exist_ok=True)
        (root / "paths" / f"{family}.yaml").write_text("", encoding="utf-8")


def test_the_inventory_fails_naming_a_family_of_paths_it_does_not_declare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A family it did not declare would escape the check that each operation cites a requirement,
    # without a word (#538): the inventory names it and writes nothing.
    _paths(tmp_path, *(family for family, _ in inventory.FAMILIES), "invoices", "nested/notes")
    monkeypatch.setattr(inventory, "ROOT", tmp_path)

    assert inventory.unknown_path_files() == ["paths/invoices.yaml", "paths/nested/notes.yaml"]
    assert inventory.main() == 1
    assert "paths/invoices.yaml" in capsys.readouterr().err
    assert not (tmp_path / "INVENTORY.md").exists()


def test_the_inventory_counts_no_file_an_editor_leaves_beside_the_families_as_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _paths(tmp_path, *(family for family, _ in inventory.FAMILIES))
    for name in (".revisions.yaml.swp", ".backup.yaml", "README.txt", ".old/risks.yaml"):
        (tmp_path / "paths" / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "paths" / name).write_text("", encoding="utf-8")
    monkeypatch.setattr(inventory, "ROOT", tmp_path)

    assert inventory.unknown_path_files() == []


def test_the_inventory_fails_naming_a_declared_family_without_its_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _paths(tmp_path, *(family for family, _ in inventory.FAMILIES if family != "audit"))
    monkeypatch.setattr(inventory, "ROOT", tmp_path)

    assert inventory.unknown_path_files() == ["paths/audit.yaml"]
    assert inventory.main() == 1


def test_the_families_of_the_inventory_are_the_files_of_the_contract() -> None:
    assert inventory.unknown_path_files() == []


OPERATION = """/projects/{project_id}/nodes:
  get:
    operationId: listNodes
    tags: [revisions]
    summary: Arbre commun de la structure
    description: >-
      Les mêmes tâches, vues du côté du temps ou du côté de l'argent (WF-DEV-0020).

      Une grille arborescente ne se trie pas (WF-IHM-0060).
    parameters:
      - name: sort_by
        in: query
        description: >-
          Colonne du tri (WF-IHM-0130).
    responses:
      '200':
        description: Nœuds (WF-PLA-0080).
  post:
    operationId: createNode
    tags: [revisions]
    summary: Créer une tâche (WF-DEV-0050)
    responses:
      '201':
        description: Créé.
"""


def test_a_requirement_cited_in_a_later_paragraph_of_a_description_is_the_operations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A folded description reads whole, its blank lines included, even after `tags`; what its
    # parameters and its responses cite is not the operation's.
    _paths(tmp_path, *(family for family, _ in inventory.FAMILIES))
    (tmp_path / "paths" / "revisions.yaml").write_text(OPERATION, encoding="utf-8")
    monkeypatch.setattr(inventory, "ROOT", tmp_path)

    cited = {o.identifier: o.requirements for o in inventory.operations()}

    assert cited == {
        "listNodes": ("WF-DEV-0020", "WF-IHM-0060"),
        "createNode": ("WF-DEV-0050",),
    }
