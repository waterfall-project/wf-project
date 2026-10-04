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
