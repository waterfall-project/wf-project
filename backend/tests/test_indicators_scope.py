# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scope of the indicators: the project, a subproject, the lines of the project alone.

A reference of 650 on four subprojects and the project alone (``day_indicators_support``): the
cabling, 100, re-estimated to 70 and charged 70; the tests, 300, completed on Monday and charged 50;
the acceptance, 50, its line carried to the tests in the current revision; the commissioning,
nothing; the works out of any subproject, 200, charged 30. The five amounts of each scope sum to the
project's; a line moved since the reference earns where the reference put it and counts its
remaining where the revision puts it; the scope refused when it names no subproject of the project.
Every answer is checked against the contract (US-1660/L3).
"""

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from costs_support import cost, load_import
from day_indicators_support import (
    Planned,
    completed,
    indicators,
    indicators_answer,
    line_of,
    priced,
    reestimated,
    subproject,
)
from estimate_support import Lines
from indicators_support import clock_setter
from nodes_support import faults
from planning_support import DAY
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene
from remaining_support import line_named

if TYPE_CHECKING:
    from day_indicators_support import Priced
    from indicators_support import Clock
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

D = Decimal
AMOUNTS = ("reference_budget", "planned_value", "earned_value", "actual_cost", "remaining")
SCOPE_UNKNOWN: list[tuple[str, str, dict[str, Any]]] = [("/query/scope", "UNKNOWN_SUBPROJECT", {})]


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the indicators are computed on."""
    return clock_setter(monkeypatch)


@pytest.fixture
def scopes(api: ContractClient, stage: Scene) -> dict[str, str]:
    """Give the four subprojects of the project, by their code."""
    labels = {"SP-1": "Câblage", "SP-2": "Essais", "SP-3": "Recette", "SP-4": "Mise en service"}
    return {code: subproject(api, stage, code, label) for code, label in labels.items()}


@pytest.fixture
def split(api: ContractClient, stage: Scene, clock: Clock, scopes: dict[str, str]) -> Priced:
    """Give the project of four subprojects and the project alone, the clock the day after Monday.

    In the current revision, the cabling re-estimated to 70, the tests completed on Monday, the line
    of the acceptance carried to the tests; 150 of actual cost.
    """
    found = priced(
        api,
        stage,
        [
            Planned("Câblage", "100", scopes["SP-1"]),
            Planned("Essais", "300", scopes["SP-2"]),
            Planned("Recette", "50", scopes["SP-3"]),
            Planned("Travaux", "200"),
        ],
    )
    tree = found.tree
    reestimated(tree, "Câblage", "70")
    completed(tree, "Essais", DAY)
    Lines(tree).changed(line_named(tree, line_of("Recette")), subproject_id=scopes["SP-2"])
    costs = [cost("A", "SP-1", "70.00"), cost("B", "SP-2", "50.00"), cost("C", None, "30.00")]
    load_import(stage, UUID(stage.project["project_id"]), costs)
    clock(DAY + timedelta(days=1))
    return found


def amounts(body: dict[str, Any]) -> tuple[str, ...]:
    """Give the five amounts of an answer, in the order of ``AMOUNTS``."""
    return tuple(body[name] for name in AMOUNTS)


@pytest.mark.requirement("WF-IND-0020-A")
@pytest.mark.usefixtures("split")
def test_the_amounts_of_the_subprojects_and_of_the_project_alone_sum_to_those_of_the_project(
    api: ContractClient, stage: Scene, scopes: dict[str, str]
) -> None:
    # « La somme des valeurs acquises des sous-projets, ensemble « hors sous-projet » compris,
    # égale celle du projet, de même pour le budget de référence, le coût réel, la valeur
    # planifiée et le reste à engager. »
    whole = indicators(api, stage)
    assert amounts(whole) == ("650.00", "650.00", "300.00", "150.00", "320.00")
    keys = [*scopes.values(), "unassigned"]
    parts = {key: indicators(api, stage, f"?scope={key}") for key in keys}
    assert amounts(parts[scopes["SP-1"]]) == ("100.00", "100.00", "0.00", "70.00", "70.00")
    assert amounts(parts[scopes["SP-2"]]) == ("300.00", "300.00", "300.00", "50.00", "50.00")
    assert amounts(parts[scopes["SP-3"]]) == ("50.00", "50.00", "0.00", "0.00", "0.00")
    assert amounts(parts["unassigned"]) == ("200.00", "200.00", "0.00", "30.00", "200.00")
    for index, name in enumerate(AMOUNTS):
        assert sum(D(amounts(each)[index]) for each in parts.values()) == D(whole[name]), name
    assert [each["context"]["scope"] for each in parts.values()] == list(parts)


@pytest.mark.requirement("WF-IND-0020-A")
def test_a_line_moved_since_the_reference_earns_in_its_first_subproject_and_remains_in_the_second(
    api: ContractClient, stage: Scene, clock: Clock, scopes: dict[str, str], split: Priced
) -> None:
    # « Une ligne passée du sous-projet A au sous-projet B après la référence acquiert sa valeur
    # dans A, et compte son reste à engager dans B. » The acceptance, carried from SP-3 to SP-2:
    # its remaining in SP-2 while it runs, then, completed, its value earned in SP-3.
    acceptance, tests = f"?scope={scopes['SP-3']}", f"?scope={scopes['SP-2']}"
    assert indicators(api, stage, acceptance)["remaining"] == "0.00"
    assert indicators(api, stage, tests)["remaining"] == "50.00"
    completed(split.tree, "Recette", DAY + timedelta(days=1))
    clock(DAY + timedelta(days=2))
    held = indicators(api, stage, acceptance)
    assert (held["reference_budget"], held["earned_value"]) == ("50.00", "50.00")
    assert indicators(api, stage, tests)["earned_value"] == "300.00"


@pytest.mark.requirement("WF-IND-0040-A")
@pytest.mark.usefixtures("split")
def test_a_subproject_of_budget_100_cost_70_and_remaining_70_is_at_50_and_70_percent_served(
    api: ContractClient, stage: Scene, scopes: dict[str, str]
) -> None:
    # « Sur un sous-projet de budget 100, de coût réel 70 et de reste à engager 70, l'avancement
    # financier vaut 50 % et la consommation 70 %. » The cabling, on the service.
    body = indicators(api, stage, f"?scope={scopes['SP-1']}")
    assert body["financial_progress"] == {"is_computable": True, "value": "0.5", "reason": None}
    assert body["budget_consumption"] == {"is_computable": True, "value": "0.7", "reason": None}


@pytest.mark.requirement("WF-IND-0040-A")
@pytest.mark.usefixtures("split")
def test_a_subproject_without_actual_cost_nor_remaining_has_no_financial_progress_served(
    api: ContractClient, stage: Scene, scopes: dict[str, str]
) -> None:
    # « Un sous-projet sans coût réel ni reste à engager affiche un avancement financier non
    # calculable. » The commissioning has neither, nor a budget: nothing is shown as nought.
    body = indicators(api, stage, f"?scope={scopes['SP-4']}")
    assert amounts(body) == ("0.00",) * 5
    assert body["financial_progress"] == {
        "is_computable": False,
        "value": None,
        "reason": "no_actual_or_remaining",
    }
    assert body["physical_progress"]["reason"] == "no_reference_budget"
    assert body["context"]["scope"] == scopes["SP-4"]


@pytest.mark.requirement("WF-IND-0020-A")
@pytest.mark.usefixtures("split")
def test_a_scope_that_names_no_subproject_of_the_project_is_refused_on_its_parameter(
    api: ContractClient, stage: Scene
) -> None:
    # A subproject the project does not have — unknown, or another project's — or
    # a malformed identifier, 422 ``UNKNOWN_SUBPROJECT`` on ``/query/scope``; no empty reading.
    elsewhere = create(api, stage.manager, label="Extension de la ligne d'essais")
    theirs = subproject_of(api, stage, elsewhere["project_id"])
    for scope in (str(uuid4()), theirs, "câblage", ""):
        assert faults(indicators_answer(api, stage, f"?scope={scope}")) == SCOPE_UNKNOWN, scope


@pytest.mark.requirement("WF-IND-0020-A")
@pytest.mark.usefixtures("split")
def test_a_scope_is_read_as_the_hyphenated_identifier_the_contract_writes(
    api: ContractClient, stage: Scene, scopes: dict[str, str]
) -> None:
    # ``format: uuid``: the subproject by its hyphenated identifier, in either case; the forms
    # ``UUID`` also reads — no hyphen, braces, ``urn:uuid:`` — name no subproject.
    key = scopes["SP-1"]
    assert indicators(api, stage, f"?scope={key.upper()}")["context"]["scope"] == key
    for scope in (key.replace("-", ""), "{" + key + "}", "urn:uuid:" + key):
        assert faults(indicators_answer(api, stage, f"?scope={scope}")) == SCOPE_UNKNOWN, scope


@pytest.mark.requirement("WF-IND-0020-A")
def test_the_planned_values_of_the_scopes_sum_to_the_project_s_to_the_cent(
    api: ContractClient, stage: Scene, clock: Clock, scopes: dict[str, str]
) -> None:
    # Two lines of 100.00 on tasks of 3 days, one per subproject: at the end of the first day each
    # has 33.33, and the project 66.66, not the 66.67 of one rounding of the exact sum.
    priced(
        api,
        stage,
        [
            Planned("Câblage", "100", scopes["SP-1"], "3"),
            Planned("Essais", "100", scopes["SP-2"], "3"),
        ],
    )
    clock(DAY)
    whole = indicators(api, stage)
    parts = [indicators(api, stage, f"?scope={key}") for key in (scopes["SP-1"], scopes["SP-2"])]
    assert [each["planned_value"] for each in parts] == ["33.33", "33.33"]
    assert whole["planned_value"] == "66.66"
    assert sum(D(each["planned_value"]) for each in parts) == D(whole["planned_value"])


def subproject_of(api: ContractClient, stage: Scene, project_id: str) -> str:
    """Create a subproject of another project of the manager; give its identifier."""
    answer = api.post(
        f"{PROJECTS}/{project_id}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-9", "label": "Ailleurs"},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["subproject_id"]
