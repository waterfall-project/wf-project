# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the variant of the contract the fake back serves."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from wftools import mock

CONTRACT: dict[str, object] = {
    "openapi": "3.1.0",
    "servers": [{"url": "/api/v1"}],
    "security": [{"bearer": []}],
    "paths": {
        "/projects": {
            "parameters": [],
            "get": {
                "operationId": "listProjects",
                "security": [{"bearer": []}],
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


def test_no_bearer_token_is_required() -> None:
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


STRUCTURES = "/projects/{project_id}/revisions/{revision_id}/structures"
AMENDMENT = "01926f3a-7c00-7000-8000-000000000203"


def amendments_contract() -> dict[str, object]:
    """Return a contract that lists a main structure and an amendment, and reads their nodes."""
    listed = [
        {"structure_id": "main", "kind": "main"},
        {"structure_id": AMENDMENT, "kind": "amendment"},
    ]
    examples = {"witness": {"$ref": "#/x/witness"}, "amendment": {"$ref": "#/x/amendment"}}
    listing = {"witness": {"$ref": "#/components/examples/structures"}}
    return {
        "servers": [{"url": "/api/v1"}],
        "components": {"examples": {"structures": {"value": listed}}},
        "paths": {
            STRUCTURES: {
                "get": {
                    "responses": {
                        "200": {"content": {"application/json": {"examples": listing}}},
                    }
                }
            },
            f"{STRUCTURES}/{{structure_id}}/nodes": {
                "get": {
                    "parameters": [
                        {"$ref": "#/components/parameters/ProjectId"},
                        {"$ref": "#/components/parameters/StructureId"},
                    ],
                    "responses": {
                        "200": {"content": {"application/json": {"examples": examples}}},
                    },
                },
                "post": {"parameters": [{"$ref": "#/components/parameters/StructureId"}]},
            },
        },
    }


def examples_of(path: dict[str, Any]) -> dict[str, Any]:
    """Return the examples of the answer 200 of the reading of a path."""
    content = path["get"]["responses"]["200"]["content"]
    return cast("dict[str, Any]", content["application/json"]["examples"])


def test_the_nodes_of_an_amendment_are_served_at_its_address_leading_with_its_example() -> None:
    paths = paths_of(mock.derive(amendments_contract()))
    served = paths[f"/api/v1{STRUCTURES}/{AMENDMENT}/nodes"]
    assert list(examples_of(served)) == ["amendment", "witness"]
    assert served["get"]["parameters"] == [{"$ref": "#/components/parameters/ProjectId"}]
    assert served["post"]["parameters"] == []
    assert set(paths) == {
        f"/api/v1{STRUCTURES}",
        f"/api/v1{STRUCTURES}/{{structure_id}}/nodes",
        f"/api/v1{STRUCTURES}/{AMENDMENT}/nodes",
    }


def test_the_templated_nodes_keep_their_first_example() -> None:
    paths = paths_of(mock.derive(amendments_contract()))
    templated = paths[f"/api/v1{STRUCTURES}/{{structure_id}}/nodes"]
    assert list(examples_of(templated)) == ["witness", "amendment"]


NODES = f"{STRUCTURES}/{{structure_id}}/nodes"


def test_without_a_nodes_path_the_paths_are_only_prefixed() -> None:
    contract = amendments_contract()
    del paths_of(contract)[NODES]
    assert set(paths_of(mock.derive(contract))) == {f"/api/v1{STRUCTURES}"}


def test_nodes_served_without_a_listing_of_structures_fail_loudly() -> None:
    contract = amendments_contract()
    del paths_of(contract)[STRUCTURES]
    with pytest.raises(ValueError, match="is not: no amendment to route"):
        mock.derive(contract)


COMPARISON = "/projects/{project_id}/revisions/comparison"


def comparison_contract(*, with_volume: bool = True) -> dict[str, object]:
    """Return a contract that reads the comparison of two revisions, by query, with examples."""
    examples = {"witness": {"$ref": "#/x/witness"}}
    if with_volume:
        examples["volume"] = {"$ref": "#/x/volume"}
    return {
        "servers": [{"url": "/api/v1"}],
        "paths": {
            COMPARISON: {
                "get": {
                    "parameters": [
                        {"$ref": "#/components/parameters/ProjectId"},
                        {"name": "from_revision_id", "in": "query"},
                    ],
                    "responses": {
                        "200": {"content": {"application/json": {"examples": examples}}},
                    },
                }
            }
        },
    }


def test_the_volume_comparison_is_served_at_the_project_of_the_volume_first() -> None:
    paths = paths_of(mock.derive(comparison_contract()))
    served = paths[f"/api/v1{COMPARISON.replace('{project_id}', mock.VOLUME_PROJECT)}"]
    assert list(examples_of(served)) == ["volume", "witness"]
    assert served["get"]["parameters"] == [{"name": "from_revision_id", "in": "query"}]
    assert list(examples_of(paths[f"/api/v1{COMPARISON}"])) == ["witness", "volume"]


def test_a_comparison_without_a_volume_example_fails_loudly() -> None:
    with pytest.raises(ValueError, match="has no example 'volume'"):
        mock.derive(comparison_contract(with_volume=False))


def test_without_an_amendment_example_the_nodes_keep_their_examples() -> None:
    contract = amendments_contract()
    examples_of(paths_of(contract)[NODES]).pop("amendment")
    served = paths_of(mock.derive(contract))[f"/api/v1{STRUCTURES}/{AMENDMENT}/nodes"]
    assert list(examples_of(served)) == ["witness"]


def test_a_path_with_parameters_and_no_get_is_routed_without_failing() -> None:
    contract = amendments_contract()
    nodes = cast("dict[str, Any]", paths_of(contract)[NODES])
    del nodes["get"]
    nodes["parameters"] = [
        {"$ref": "#/components/parameters/ProjectId"},
        {"$ref": "#/components/parameters/StructureId"},
    ]
    nodes["summary"] = "nodes"
    served = paths_of(mock.derive(contract))[f"/api/v1{STRUCTURES}/{AMENDMENT}/nodes"]
    assert served["parameters"] == [{"$ref": "#/components/parameters/ProjectId"}]
    assert served["summary"] == "nodes"
    assert "get" not in served


def listing_examples(contract: dict[str, object]) -> dict[str, Any]:
    """Return the examples of the listing of the structures of a contract."""
    return examples_of(paths_of(contract)[STRUCTURES])


def test_a_first_example_without_amendment_fails_loudly() -> None:
    contract = amendments_contract()
    components = cast("dict[str, Any]", contract["components"])
    components["examples"]["main_only"] = {"value": [{"structure_id": "main", "kind": "main"}]}
    listing = listing_examples(contract)
    listing.clear()
    listing["main_only"] = {"$ref": "#/components/examples/main_only"}
    with pytest.raises(ValueError, match="lists no structure of kind"):
        mock.derive(contract)


def test_an_amendment_only_in_a_later_example_is_not_routed() -> None:
    contract = amendments_contract()
    components = cast("dict[str, Any]", contract["components"])
    components["examples"]["main_only"] = {"value": [{"structure_id": "main", "kind": "main"}]}
    listing = {"main_only": {"$ref": "#/components/examples/main_only"}} | listing_examples(
        contract
    )
    listing_examples(contract).clear()
    listing_examples(contract).update(listing)
    with pytest.raises(ValueError, match="lists no structure of kind"):
        mock.derive(contract)


def test_an_unresolved_reference_fails_loudly() -> None:
    contract = amendments_contract()
    listing_examples(contract)["witness"] = {"$ref": "#/components/examples/missing"}
    with pytest.raises(ValueError, match="points at no example"):
        mock.derive(contract)


def test_the_bundle_of_the_repository_serves_the_amendment_203_and_the_volume(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    version = re.search(r"^REDOCLY_VERSION := (\S+)$", makefile, re.MULTILINE)
    assert version is not None
    bundle = tmp_path / "contract.json"
    subprocess.run(
        [
            str(shutil.which("npx")),
            "--yes",
            f"@redocly/cli@{version[1]}",
            "bundle",
            str(root / "docs/api/openapi.yaml"),
            "--ext",
            "json",
            "-o",
            str(bundle),
        ],
        check=True,
        capture_output=True,
    )
    served = paths_of(mock.derive(json.loads(bundle.read_text(encoding="utf-8"))))
    assert any(path.endswith("0203/nodes") for path in served)
    assert f"/api/v1{COMPARISON.replace('{project_id}', mock.VOLUME_PROJECT)}" in served
