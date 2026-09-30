# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the table of the fixtures the contract cites, by operation and status."""

import json
from pathlib import Path

import pytest

from wftools import exampleroutes

PROJECTS: dict[str, object] = {"items": [{"project_id": "p"}], "meta": {"total": 1}}
EMPTY: dict[str, object] = {"items": [], "meta": {"total": 0}}
PROJECT: dict[str, object] = {"project_id": "p"}
TASK: dict[str, object] = {"task_id": "t", "status": "queued"}

CONTRACT: dict[str, object] = {
    "paths": {
        "/projects": {
            "parameters": [],
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "examples": {
                                    "witness": {"$ref": "#/components/examples/projects"},
                                    "empty": {"$ref": "#/components/examples/projects_empty"},
                                    "inline": {"value": {"items": [], "meta": {"total": 9}}},
                                }
                            }
                        }
                    },
                    "404": {"$ref": "#/components/responses/NotFound"},
                }
            },
        },
        "/projects/{project_id}/revisions": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "examples": {
                                    "empty": {"$ref": "#/components/examples/revisions_empty"}
                                }
                            }
                        }
                    }
                }
            },
        },
        "/projects/{project_id}/mark": {
            "post": {"responses": {"202": {"$ref": "#/components/responses/Queued"}}},
        },
        "/projects/{project_id}/avatar": {
            "get": {
                "responses": {
                    "200": {"content": {"image/png": {"examples": {"a": {"value": PROJECT}}}}}
                }
            },
            "trace": {"responses": {"200": {"content": {"application/json": {}}}}},
        },
    },
    "components": {
        "examples": {
            "projects": {"summary": "Projets.", "value": PROJECTS},
            "projects_empty": {"summary": "Aucun.", "value": EMPTY},
            "revisions_empty": {"summary": "Aucune.", "value": EMPTY},
            "task_queued-2": {"summary": "En file.", "value": TASK},
        },
        "responses": {
            "NotFound": {
                "content": {"application/problem+json": {"example": {"code": "NOT_FOUND"}}}
            },
            "Queued": {
                "content": {
                    "application/json": {
                        "examples": {"queued": {"$ref": "#/components/examples/task_queued-2"}}
                    }
                }
            },
        },
    },
}


@pytest.fixture
def directory(tmp_path: Path) -> Path:
    """Write fixtures, one of them in a subdirectory, and a file that is none."""
    for name, value in {
        "projects": PROJECTS,
        "projects_empty": EMPTY,
        "revisions_empty": EMPTY,
        "project": PROJECT,
        "volume/task_queued": TASK,
    }.items():
        path = tmp_path / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"summary": name, "value": value}), encoding="utf-8")
    (tmp_path / "listing.json").write_text(json.dumps([1, 2]), encoding="utf-8")
    return tmp_path


def test_fixtures_are_indexed_by_their_value(directory: Path) -> None:
    known = exampleroutes.fixtures(directory)
    assert sorted(name for names in known.values() for name in names) == [
        "project",
        "projects",
        "projects_empty",
        "revisions_empty",
        "volume/task_queued",
    ]


def test_each_operation_answers_the_fixtures_its_contract_cites(directory: Path) -> None:
    table = exampleroutes.routes(CONTRACT, exampleroutes.fixtures(directory))
    assert table == {
        # An inline example is no fixture; the Problem of a 404 is not an example of JSON.
        "GET /projects": {200: ["projects", "projects_empty"]},
        # Two fixtures of the same value: the one the bundle named.
        "GET /projects/{project_id}/revisions": {200: ["revisions_empty"]},
        # A response by reference, an example whose name the bundle suffixed, in a subdirectory.
        "POST /projects/{project_id}/mark": {202: ["volume/task_queued"]},
    }


def test_the_table_is_written_as_a_declaration_sorted_and_stable() -> None:
    text = exampleroutes.render({"GET /b": {200: ["y", "x"]}, "GET /a": {202: ["z"], 200: ["w"]}})
    assert text.endswith(
        "export interface Examples {\n"
        '  "GET /a": {\n'
        '    200: "w";\n'
        '    202: "z";\n'
        "  };\n"
        '  "GET /b": {\n'
        '    200: "x" | "y";\n'
        "  };\n"
        "}\n"
    )
    assert text.startswith("// Written by `make generate-client`")


def test_main_writes_the_declaration_with_lf(directory: Path, tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(CONTRACT), encoding="utf-8")
    output = tmp_path / "examples.d.ts"
    assert exampleroutes.main([str(bundle), str(output)], directory) == 0
    written = output.read_bytes().decode("utf-8")
    assert '"GET /projects": {\n    200: "projects" | "projects_empty";\n' in written
    assert "\r" not in written
