# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the check of the screens of the front against the FBS."""

import json
from pathlib import Path
from typing import cast

import pytest

from wftools import projection, screens
from wftools.projection import Function

TREE = (
    Function("FBS-3", "Paramètres applicatifs"),
    Function("FBS-3.2", "Paramètres de ressources"),
    Function("FBS-3.2.1", "Arbre d'organisation"),
    Function("FBS-3.2.3", "Calendriers"),
    Function("FBS-4", "Projets"),
    Function("FBS-4.4", "Chiffrage et devis"),
    Function("FBS-4.4.2", "Grille de devis"),
    Function("FBS-4.4.4", "Plan de charge du projet"),
    Function("FBS-4.9", "Cycle de vie du projet"),
)
ESTIMATE = "/projects/[projectId]/revisions/[revisionId]/estimate"
WORKLOAD = "/projects/[projectId]/revisions/[revisionId]/workload"


def table() -> dict[str, object]:
    """Return a table that addresses every leaf of TREE, each way the front addresses one."""
    return {
        "groups": [
            {
                "code": "FBS-3",
                "functions": [
                    {
                        "code": "FBS-3.2",
                        "route": "/reference/resources",
                        "sections": [
                            {"code": "FBS-3.2.1", "role": "region", "name": "a.title"},
                            {"code": "FBS-3.2.3", "name": "b.title"},
                        ],
                    }
                ],
            },
            {
                "code": "FBS-4",
                "route": "/",
                "functions": [
                    {
                        "code": "FBS-4.4",
                        "route": ESTIMATE,
                        "sections": [{"code": "FBS-4.4.2", "role": "grid", "name": "c"}],
                        "leaves": [{"code": "FBS-4.4.4", "route": WORKLOAD}],
                    },
                    {"code": "FBS-4.9", "route": "/projects/[projectId]/lifecycle"},
                ],
            },
        ]
    }


def app() -> dict[str, str]:
    """Return the pages of every route of `table()`, the estimate leading to the workload."""
    return {
        "/": "",
        "/reference/resources": "",
        ESTIMATE: 'const WORKLOAD = leafOf("FBS-4.4.4");',
        WORKLOAD: "",
        "/projects/[projectId]/lifecycle": "",
    }


def functions(found: dict[str, object]) -> list[dict[str, object]]:
    """Return the functions of the second group of a table, to be changed in place."""
    groups = cast("list[dict[str, object]]", found["groups"])
    return cast("list[dict[str, object]]", groups[1]["functions"])


def test_a_table_that_addresses_every_leaf_on_a_page_of_the_app_passes() -> None:
    assert screens.confront(TREE, table(), app(), {}) == []


def test_a_leaf_without_a_route_is_named() -> None:
    found = table()
    del functions(found)[1]
    assert screens.confront(TREE, found, app(), {}) == [
        "FBS-4.9 Cycle de vie du projet: a leaf of the FBS without a route in the table"
    ]


def test_a_leaf_declared_without_a_screen_passes_with_its_reason() -> None:
    found = table()
    del functions(found)[1]
    assert screens.confront(TREE, found, app(), {"FBS-4.9": "not yet, #1"}) == []


def test_a_declaration_that_no_longer_holds_is_named() -> None:
    assert screens.confront(TREE, table(), app(), {"FBS-4.9": "", "FBS-4.4": ""}) == [
        "FBS-4.9: declared without a screen, but the table addresses it",
        "FBS-4.4: declared without a screen, but not a leaf of the FBS",
    ]


def test_a_route_no_page_answers_is_named() -> None:
    pages = app()
    del pages[WORKLOAD]
    assert screens.confront(TREE, table(), pages, {}) == [
        f"{WORKLOAD}: a route of the table that no page of the application answers"
    ]


@pytest.mark.parametrize(
    "source",
    [
        'const ICON = LEAF_ICONS["FBS-4.4.9"];',
        # The icon of the same code, with no link to it.
        'const ICON = LEAF_ICONS["FBS-4.4.4"];',
        'const OTHER = leafOf("FBS-4.4.44");',
    ],
)
def test_a_leaf_the_page_of_its_function_does_not_name_by_leaf_of_is_unreachable(
    source: str,
) -> None:
    pages = app()
    pages[ESTIMATE] = source
    assert screens.confront(TREE, table(), pages, {}) == [
        (
            f"{WORKLOAD}: the screen of FBS-4.4.4, which the page of FBS-4.4 does not name by"
            " leafOf, and so does not lead to"
        )
    ]


@pytest.mark.parametrize(
    ("code", "finding"),
    [
        ("FBS-4.4.7", "FBS-4.4.7: in the table, but not a function of the FBS"),
        (
            "FBS-3.2.1",
            "FBS-3.2.1: a section of FBS-4.4 in the table, but not a leaf under it in the FBS",
        ),
        (
            "FBS-4.4",
            "FBS-4.4: a section of FBS-4.4 in the table, but not a leaf under it in the FBS",
        ),
    ],
)
def test_a_section_that_is_no_leaf_under_its_function_is_named(code: str, finding: str) -> None:
    found = table()
    functions(found)[0]["sections"] = [{"code": "FBS-4.4.2", "name": "c"}, {"code": code}]
    findings = screens.confront(TREE, found, app(), {})
    assert finding in findings


def test_the_leaves_of_a_function_the_fbs_has_not_are_named() -> None:
    found = table()
    functions(found)[0]["code"] = "FBS-4.40"
    assert screens.confront(TREE, found, app(), {}) == [
        "FBS-4.40: in the table, but not a function of the FBS",
        "FBS-4.4.2: a section of FBS-4.40 in the table, but not a leaf under it in the FBS",
        "FBS-4.4.4: a leaf of FBS-4.40 in the table, but not a leaf under it in the FBS",
    ]


def test_a_code_twice_in_the_table_is_named() -> None:
    found = table()
    functions(found)[0]["sections"] = [{"code": "FBS-4.4.2"}, {"code": "FBS-4.4.2"}]
    assert screens.confront(TREE, found, app(), {}) == ["FBS-4.4.2: twice in the table"]


def test_the_routes_are_those_of_the_groups_the_functions_and_the_leaves() -> None:
    assert screens.routes(table()) == [
        "/",
        "/reference/resources",
        ESTIMATE,
        WORKLOAD,
        "/projects/[projectId]/lifecycle",
    ]


def test_a_page_answers_its_route_groups_aside_and_the_catch_all_answers_none(
    tmp_path: Path,
) -> None:
    for directory in ["(home)", "reference/resources", "[...path]", "projects/[projectId]"]:
        (tmp_path / directory).mkdir(parents=True)
        (tmp_path / directory / "page.tsx").write_text(directory, encoding="utf-8")
    (tmp_path / "reference" / "layout.tsx").write_text("", encoding="utf-8")
    assert screens.pages(tmp_path) == {
        "/": "(home)",
        "/projects/[projectId]": "projects/[projectId]",
        "/reference/resources": "reference/resources",
    }


def test_the_command_names_what_it_finds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    found = table()
    del functions(found)[1]
    path = tmp_path / "functions.json"
    path.write_text(json.dumps(found), encoding="utf-8")
    monkeypatch.setattr(screens, "TABLE", path)
    monkeypatch.setattr(projection, "read_functions", lambda: TREE)

    def pages(_: Path) -> dict[str, str]:
        return app()

    monkeypatch.setattr(screens, "pages", pages)
    monkeypatch.setattr(screens, "WITHOUT_SCREEN", {"FBS-3.2.1": "no screen, #1"})
    assert screens.main() == 1
    out, err = capsys.readouterr()
    assert err.splitlines() == [
        "FBS-4.9 Cycle de vie du projet: a leaf of the FBS without a route in the table",
        "FBS-3.2.1: declared without a screen, but the table addresses it",
    ]
    assert "5 leaves of the FBS, 1 declared without a screen; 4 routes; 2 finding(s)" in out
    assert "without a screen: FBS-3.2.1, no screen, #1" in out


def test_the_repository_declares_only_leaves_without_a_screen() -> None:
    leaves = {fn.code for fn in projection.leaves(projection.read_functions())}
    assert set(screens.WITHOUT_SCREEN) <= leaves
