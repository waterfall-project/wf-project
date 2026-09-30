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


def canonical(value: object) -> str:
    """Write a value as the index of the fixtures writes it."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def answering(examples: dict[str, object], status: str = "200") -> dict[str, object]:
    """Return a contract of one operation, whose answer of one status gives these examples."""
    content = {"application/json": {"examples": examples}}
    return {
        "paths": {"/projects": {"get": {"responses": {status: {"content": content}}}}},
        "components": {
            "examples": {
                "projects": {"value": PROJECTS},
                "projects-3": {"value": PROJECTS},
                "projects_empty": {"value": {"items": [], "meta": {"total": 7}}},
                "rate": {"value": {"p": 1}},
            }
        },
    }


def test_fixtures_are_indexed_by_their_value(directory: Path) -> None:
    assert exampleroutes.fixtures(directory) == {
        canonical(PROJECTS): ["projects"],
        canonical(EMPTY): ["projects_empty", "revisions_empty"],
        canonical(PROJECT): ["project"],
        canonical(TASK): ["volume/task_queued"],
    }


def test_each_operation_answers_the_fixtures_its_contract_cites(directory: Path) -> None:
    table = exampleroutes.routes(CONTRACT, exampleroutes.fixtures(directory))
    assert table == {
        # An inline example is no fixture — here, of no fixture's value either —; the Problem
        # of a 404 is not an example of JSON.
        "GET /projects": {200: ["projects", "projects_empty"]},
        # Two fixtures of the same value: the one the bundle named.
        "GET /projects/{project_id}/revisions": {200: ["revisions_empty"]},
        # A response by reference, an example whose name the bundle suffixed, in a subdirectory.
        "POST /projects/{project_id}/mark": {202: ["volume/task_queued"]},
    }


def test_an_inline_example_is_no_fixture_even_of_the_value_of_one(directory: Path) -> None:
    contract = answering({"inline": {"value": PROJECTS}})
    assert exampleroutes.routes(contract, exampleroutes.fixtures(directory)) == {}


def test_a_name_the_bundle_suffixed_is_the_fixture_it_was_taken_from(directory: Path) -> None:
    contract = answering({"again": {"$ref": "#/components/examples/projects-3"}})
    table = exampleroutes.routes(contract, exampleroutes.fixtures(directory))
    assert table == {"GET /projects": {200: ["projects"]}}


def test_a_number_is_read_alike_in_the_fixture_and_in_the_bundle(tmp_path: Path) -> None:
    # The fixture says 1.0, the bundle writes 1: the same value.
    (tmp_path / "rate.json").write_text('{"summary": "Taux.", "value": {"p": 1.0}}', "utf-8")
    contract = answering({"rate": {"$ref": "#/components/examples/rate"}})
    assert exampleroutes.routes(contract, exampleroutes.fixtures(tmp_path)) == {
        "GET /projects": {200: ["rate"]}
    }


def test_an_example_named_after_a_fixture_without_its_value_fails(directory: Path) -> None:
    contract = answering({"empty": {"$ref": "#/components/examples/projects_empty"}})
    with pytest.raises(exampleroutes.ExampleError, match="projects_empty"):
        exampleroutes.routes(contract, exampleroutes.fixtures(directory))


def test_main_fails_on_an_example_without_the_value_of_its_fixture(
    directory: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(answering({"empty": {"$ref": "#/components/examples/projects_empty"}})),
        encoding="utf-8",
    )
    output = tmp_path / "examples.d.ts"
    assert exampleroutes.main([str(bundle), str(output)], directory) == 1
    assert "named after the fixture projects_empty" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("status", ["default", "4XX"])
def test_a_status_that_is_no_number_is_left_out(directory: Path, status: str) -> None:
    contract = answering({"witness": {"$ref": "#/components/examples/projects"}}, status)
    assert exampleroutes.routes(contract, exampleroutes.fixtures(directory)) == {}


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
