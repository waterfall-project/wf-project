# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the variant of the contract the fake back serves."""

import json
from pathlib import Path
from typing import cast

from wftools import mock

CONTRACT: dict[str, object] = {
    "openapi": "3.1.0",
    "servers": [{"url": "/api/v1"}],
    "security": [{"session": []}],
    "paths": {
        "/projects": {
            "parameters": [],
            "get": {
                "operationId": "listProjects",
                "security": [{"session": []}],
                "responses": {"200": {"description": "ok"}},
            },
        },
        "/health": {"get": {"operationId": "getLiveness", "security": [], "responses": {}}},
    },
}


def paths_of(contract: dict[str, object]) -> dict[str, dict[str, dict[str, object]]]:
    """Return the paths of a contract, typed."""
    return cast("dict[str, dict[str, dict[str, object]]]", contract["paths"])


def test_paths_are_served_under_the_prefix_of_the_server() -> None:
    assert list(paths_of(mock.derive(CONTRACT))) == ["/api/v1/projects", "/api/v1/health"]


def test_no_session_is_required() -> None:
    derived = mock.derive(CONTRACT)
    assert "security" not in derived
    assert "security" not in json.dumps(derived["paths"])


def test_responses_are_left_as_the_contract_writes_them() -> None:
    operation = paths_of(mock.derive(CONTRACT))["/api/v1/projects"]["get"]
    assert operation == {
        "operationId": "listProjects",
        "responses": {"200": {"description": "ok"}},
    }


def test_the_file_is_rewritten_in_place(tmp_path: Path) -> None:
    bundle = tmp_path / "contract.json"
    bundle.write_text(json.dumps(CONTRACT), encoding="utf-8")
    assert mock.main([str(bundle)]) == 0
    assert "/api/v1/projects" in json.loads(bundle.read_text(encoding="utf-8"))["paths"]
