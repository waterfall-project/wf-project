# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The matrix of the risks of a project, and the class of a risk in it (US-2600/L2, EP-08).

``getProjectRiskMatrix`` places the risks of a revision on the bounds of the matrix of the reference
settings (WF-REF-0160, WF-RIS-0040): the base of the project is the total of its estimate without
provisions while it is costed, its reference budget once designated (H-06); a cell counts the
identified risks only (#1395); a revision named gives the evaluation it froze. Each answer is
validated against the contract by the client of the tests.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, mark
from projects_support import PROJECTS, Scene, create, designate
from projects_support import scene as make_scene
from risks_support import (
    MOST_STATEMENTS_OF_DETAIL,
    MOST_STATEMENTS_OF_MATRIX,
    Costed,
    Risks,
    costed,
)
from sqlalchemy import delete, event, update

from waterfall.core.cost_settings.tables import ReferenceSetting
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.risks.tables import RiskEvaluation

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The bounds of the installation as the bootstrap writes them: 25 %, 50 %, 75 % of probability,
# 1 %, 5 %, 10 % of the base on the severity axis.
THIRD = 3
SECOND = 2


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@dataclass(frozen=True)
class Matrixed:
    """A project costed, and what reads its matrix, its register and its risks."""

    api: ContractClient
    project: Costed
    risks: Risks

    def path(self, tail: str, query: str = "") -> str:
        """Give the path of a reading of the risks of the project."""
        return f"{PROJECTS}/{self.project.project_id}/risks{tail}{query}"

    def matrix(self, query: str = "") -> dict[str, Any]:
        """Read the matrix as the manager does; it must answer."""
        answer = self.api.get(self.path("/matrix", query), headers=self.risks.headers)
        assert answer.status_code == 200, answer.text
        body: dict[str, Any] = answer.json()
        return body

    def register(self, query: str = "") -> list[dict[str, Any]]:
        """Read the items of the register, in its order."""
        answer = self.api.get(self.path("", query), headers=self.risks.headers)
        assert answer.status_code == 200, answer.text
        items: list[dict[str, Any]] = answer.json()["items"]
        return items

    def declare(self, probability: str, label: str, severity: str) -> dict[str, Any]:
        """Declare a risk of a severity in the current revision; give it."""
        risk = self.risks.declared(probability, label)
        self.risks.costed_at(risk, self.project.revision_id, severity)
        return risk

    def enlarge(self, amount: str) -> None:
        """Add a line of material to the main estimate of the current revision."""
        task = str(self.project.tasks["Étude"])
        sent = {
            "label": "Extension",
            "quantity": "1",
            "cost_category_id": str(self.project.costs.material),
            "unit_disbursement": amount,
        }
        self.project.lines.made(task, **sent)


@pytest.fixture
def matrixed(api: ContractClient, project: Costed) -> Matrixed:
    """Give the means to declare risks in the project costed and read them."""
    return Matrixed(api, project, Risks(api, project))


def cell(body: dict[str, Any], probability: int, severity: int) -> dict[str, Any]:
    """Give a cell of a matrix by its two levels."""
    found = [
        each
        for each in body["cells"]
        if (each["probability_level"], each["severity_level"]) == (probability, severity)
    ]
    assert len(found) == 1
    return found[0]


def point(body: dict[str, Any], label: str) -> dict[str, Any]:
    """Give the point of a risk of a matrix by its label."""
    found = [each for each in body["points"] if each["label"] == label]
    assert len(found) == 1
    return found[0]


def counted(body: dict[str, Any]) -> dict[tuple[int, int], int]:
    """Give the cells that hold risks, with their count."""
    return {
        (each["probability_level"], each["severity_level"]): each["count"]
        for each in body["cells"]
        if each["count"]
    }


# --- The levels and the cells of the matrix ------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_matrix_gives_the_levels_of_the_reference_settings_and_sixteen_cells(
    matrixed: Matrixed,
) -> None:
    body = matrixed.matrix()
    assert body["probability_levels"] == [
        {"level": 1, "lower": "0", "upper": "0.25"},
        {"level": 2, "lower": "0.25", "upper": "0.5"},
        {"level": 3, "lower": "0.5", "upper": "0.75"},
        {"level": 4, "lower": "0.75", "upper": None},
    ]
    assert [(each["lower"], each["upper"]) for each in body["severity_levels"]] == [
        ("0", "0.01"),
        ("0.01", "0.05"),
        ("0.05", "0.1"),
        ("0.1", None),
    ]
    assert [(each["probability_level"], each["severity_level"]) for each in body["cells"]] == [
        (row, column) for row in range(1, 5) for column in range(1, 5)
    ]
    assert body["points"] == []
    assert {each["count"] for each in body["cells"]} == {0}


@pytest.mark.requirement("WF-REF-0160-A")
@pytest.mark.parametrize(
    ("extension", "ratio", "level"),
    [(None, "0.06", THIRD), ("1000.00", "0.03", SECOND)],
    ids=["budget-1000", "budget-2000"],
)
def test_a_severity_of_60_is_the_third_level_on_1000_and_the_second_on_2000(
    matrixed: Matrixed, extension: str | None, ratio: str, level: int
) -> None:
    # Bounds at 1 %, 5 % and 10 %: 60 is 6 % of 1 000, the third level, 3 % of 2 000, the second.
    if extension is not None:
        matrixed.enlarge(extension)
    matrixed.declare("0.3", "Grue", "60.00")
    body = matrixed.matrix()
    assert point(body, "Grue")["severity_ratio"] == {
        "is_computable": True,
        "value": ratio,
        "reason": None,
    }
    assert counted(body) == {(2, level): 1}
    assert matrixed.register()[0]["matrix_cell"]["severity_level"] == level


@pytest.mark.requirement("WF-REF-0160-A")
def test_a_severity_equal_to_a_bound_is_of_the_level_the_bound_opens(matrixed: Matrixed) -> None:
    # 50 on a base of 1 000 is 5 %, the second bound: the third level. The provision the risk
    # carries in the estimate is left out of the base (1 000, not 1 025).
    matrixed.declare("0.5", "Grue", "50.00")
    body = matrixed.matrix()
    assert point(body, "Grue")["severity_ratio"]["value"] == "0.05"
    assert counted(body) == {(3, THIRD): 1}


@pytest.mark.requirement("WF-REF-0160-A")
def test_a_severity_just_under_a_bound_is_shown_at_the_bound_and_stays_under_its_level(
    matrixed: Matrixed,
) -> None:
    # 49.96 on 1 000 is 4.996 %: the share is rounded to four places, "0.05", the bound itself, yet
    # the cell is placed by the exact ratio, under the bound: the second level, not the third.
    matrixed.declare("0.3", "Grue", "49.96")
    body = matrixed.matrix()
    assert point(body, "Grue")["severity_ratio"]["value"] == "0.05"
    assert counted(body) == {(2, SECOND): 1}


@pytest.mark.requirement("WF-REF-0160-A")
def test_a_marked_revision_is_related_to_its_own_total_until_another_is_the_reference(
    matrixed: Matrixed,
) -> None:
    # H-06: before a reference, the base is the total, provisions left out, of the revision read;
    # once one is designated, its budget, whatever the revision read. A is marked at 1 000, the
    # current revision then grows to 2 000 and is marked B: A read is 6 % of its own total, the
    # current revision 3 % of its own, and A read 3 % of the budget of B once B is the reference.
    matrixed.declare("0.3", "Grue", "60.00")
    stage = matrixed.project.stage
    mark(stage, {"revision_id": str(matrixed.project.revision_id)})
    current = matrixed.risks.revision()
    later = Tree(matrixed.api, stage, current)
    extra = later.made("Extension")
    sent = {
        "label": "Extension",
        "quantity": "1",
        "cost_category_id": str(matrixed.project.costs.material),
        "unit_disbursement": "1000.00",
    }
    Lines(later).made(extra, **sent)
    reading = f"?revision_id={matrixed.project.revision_id}"
    assert point(matrixed.matrix(reading), "Grue")["severity_ratio"]["value"] == "0.06"
    assert point(matrixed.matrix(), "Grue")["severity_ratio"]["value"] == "0.03"
    mark(stage, {"revision_id": str(current["revision_id"])}, "v2.0")
    path = f"{PROJECTS}/{matrixed.project.project_id}/revisions/{current['revision_id']}"
    designate(matrixed.api, stage, matrixed.api.get(path, headers=matrixed.risks.headers).json())
    assert point(matrixed.matrix(reading), "Grue")["severity_ratio"]["value"] == "0.03"


@pytest.mark.requirement("WF-REF-0160-A")
def test_in_costing_the_base_is_the_total_without_provisions_and_designation_changes_nothing(
    matrixed: Matrixed,
) -> None:
    # In costing the base is the total of the current estimate without provisions; once the revision
    # is the reference, its budget: at an equal total, the same level, and a later estimate that
    # grows leaves the base at the budget (H-06).
    matrixed.declare("0.3", "Grue", "60.00")
    before = point(matrixed.matrix(), "Grue")
    revision = f"{PROJECTS}/{matrixed.project.project_id}/revisions/{matrixed.project.revision_id}"
    mark(matrixed.project.stage, {"revision_id": str(matrixed.project.revision_id)})
    first = matrixed.api.get(revision, headers=matrixed.risks.headers).json()
    designate(matrixed.api, matrixed.project.stage, first)
    after = matrixed.matrix()
    assert point(after, "Grue") == before
    assert counted(after) == {(2, THIRD): 1}
    later = Tree(matrixed.api, matrixed.project.stage, matrixed.risks.revision())
    extra = later.made("Extension")
    sent = {
        "label": "Extension",
        "quantity": "1",
        "cost_category_id": str(matrixed.project.costs.material),
        "unit_disbursement": "1000.00",
    }
    Lines(later).made(extra, **sent)
    grown = matrixed.matrix()
    assert point(grown, "Grue")["severity_ratio"]["value"] == "0.06"
    assert counted(grown) == {(2, THIRD): 1}


@pytest.mark.requirement("WF-REF-0160-A")
def test_without_a_base_no_share_is_computable_and_each_risk_is_at_the_lowest_severity(
    matrixed: Matrixed, stage: Scene
) -> None:
    # An estimate that carries only provisions relates no severity to anything (#1240).
    matrixed.declare("0.3", "Grue", "60.00")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.cost_category_id == matrixed.project.costs.material)
            .where(EstimateLine.label.in_(("Plans", "Fabrication")))
            .values(cost_category_id=matrixed.project.costs.provision)
        )
    body = matrixed.matrix()
    assert point(body, "Grue")["severity_ratio"] == {
        "is_computable": False,
        "value": None,
        "reason": "no_reference_budget",
    }
    assert counted(body) == {(2, 1): 1}
    assert matrixed.register()[0]["matrix_cell"]["severity_level"] == 1


# --- The points, the cells and the totals --------------------------------------------------------


def _leave(project: Costed, risk: dict[str, Any], state: str, cost: Decimal | None = None) -> None:
    """Make a risk occurred or dismissed in the revision it is read, around the service."""
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskEvaluation)
            .where(RiskEvaluation.risk_id == UUID(risk["risk_id"]))
            .values(state=state, provision_node_id=None, occurrence_cost=cost)
        )


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_cell_counts_the_identified_risks_only_and_every_risk_is_a_point(
    matrixed: Matrixed,
) -> None:
    # #1395: an occurred or a dismissed risk stays a point and is counted in no cell.
    matrixed.declare("0.3", "Reste", "20.00")
    survenu = matrixed.declare("0.3", "Survenu", "20.00")
    ecarte = matrixed.declare("0.3", "Écarté", "20.00")
    _leave(matrixed.project, survenu, "occurred", Decimal("20.00"))
    _leave(matrixed.project, ecarte, "dismissed")
    body = matrixed.matrix()
    assert counted(body) == {(2, SECOND): 1}
    assert {each["label"]: each["state"] for each in body["points"]} == {
        "Reste": "identified",
        "Survenu": "occurred",
        "Écarté": "dismissed",
    }
    assert {each["label"] for each in body["points"]} == {"Reste", "Survenu", "Écarté"}


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_points_and_the_totals_are_those_of_the_register(matrixed: Matrixed) -> None:
    # The matrix and the register read each risk the same way: its zone, its provision, the totals.
    matrixed.declare("0.3", "Une", "20.00")
    matrixed.declare("0.5", "Deux", "120.00")
    body = matrixed.matrix()
    items = {each["label"]: each for each in matrixed.register()}
    for each in body["points"]:
        risk = items[each["label"]]
        assert each["zone"] == risk["matrix_cell"]["zone"]
        assert each["provision_amount"] == risk["provision_amount"]
        assert each["severity_amount"] == risk["severity"]
        assert each["probability"] == risk["probability"]
    register = matrixed.api.get(matrixed.path(""), headers=matrixed.risks.headers).json()
    assert body["totals"] == register["totals"]


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_project_without_revision_has_an_empty_matrix(api: ContractClient, stage: Scene) -> None:
    other = create(api, stage.manager, label="Sans révision")
    path = f"{PROJECTS}/{other['project_id']}/risks/matrix"
    answer = api.get(path, headers=stage.manager.headers)
    assert answer.status_code == 200
    body = answer.json()
    assert body["points"] == []
    assert len(body["cells"]) == 16
    assert set(body["totals"].values()) == {"0.00"}


# --- The colour of a risk follows its probability ------------------------------------------------


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_probability_that_crosses_a_bound_changes_the_cell_and_the_zone(
    matrixed: Matrixed,
) -> None:
    # 2 % of the base: the second severity level. A probability from 45 % to 55 % crosses the
    # bound of 50 %: from the second probability level, nominal, to the third, to watch — in the
    # register, the detail and the matrix; the revision named gives the evaluation it froze.
    # The probability is written by the review (``reviewRisk``, US-2590/L1), the only write of it.
    risk = matrixed.declare("0.45", "Grue", "20.00")
    zones = ["nominal"] * 8 + ["watch"] * 4 + ["alert"] * 4
    with matrixed.project.stage.owner.begin() as connection:
        connection.execute(update(ReferenceSetting).values(risk_zones=zones))
    revision = f"{PROJECTS}/{matrixed.project.project_id}/revisions/{matrixed.project.revision_id}"
    mark(matrixed.project.stage, {"revision_id": str(matrixed.project.revision_id)})
    first = matrixed.api.get(revision, headers=matrixed.risks.headers).json()
    second = matrixed.risks.revision()
    reviewed = matrixed.risks.reviewed(matrixed.risks.risk(risk), probability="0.55")
    assert reviewed["matrix_cell"]["zone"] == "watch"
    assert matrixed.risks.risk(risk)["lock_version"] > risk["lock_version"]
    assert second["revision_id"] != first["revision_id"]
    before = f"?revision_id={first['revision_id']}"
    assert point(matrixed.matrix(before), "Grue")["zone"] == "nominal"
    assert counted(matrixed.matrix(before)) == {(2, SECOND): 1}
    assert point(matrixed.matrix(), "Grue")["zone"] == "watch"
    assert counted(matrixed.matrix()) == {(3, SECOND): 1}
    assert matrixed.register(before)[0]["matrix_cell"] == {
        "probability_level": 2,
        "severity_level": 2,
        "zone": "nominal",
    }
    assert matrixed.register()[0]["matrix_cell"] == {
        "probability_level": 3,
        "severity_level": 2,
        "zone": "watch",
    }
    detail = matrixed.risks.risk(risk)
    assert detail["matrix_cell"]["zone"] == "watch"
    assert matrixed.risks.risk(risk, first["revision_id"])["matrix_cell"]["zone"] == "nominal"


# --- The revision read, the settings, the cost ---------------------------------------------------


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_revision_of_another_project_or_unknown_is_not_found(
    matrixed: Matrixed, api: ContractClient, stage: Scene
) -> None:
    other = create(api, stage.manager, label="Autre")
    unknown = "00000000-0000-4000-8000-000000000001"
    path = matrixed.path("/matrix", f"?revision_id={unknown}")
    answer = api.get(path, headers=stage.manager.headers)
    assert answer.status_code == 404
    named = api.get(
        f"{PROJECTS}/{other['project_id']}/risks/matrix?revision_id={matrixed.project.revision_id}",
        headers=stage.manager.headers,
    )
    assert named.status_code == 404


@pytest.mark.requirement("WF-RIS-0040-A")
def test_without_reference_settings_the_matrix_is_unavailable_and_an_empty_register_is_not(
    matrixed: Matrixed, owner: Engine
) -> None:
    # The levels come from the settings, which an installation not bootstrapped does not have: 503,
    # as the contract says. A register with a revision and no risk reads no setting (#4012).
    with owner.begin() as connection:
        connection.execute(delete(ReferenceSetting))
    answer = matrixed.api.get(matrixed.path("/matrix"), headers=matrixed.risks.headers)
    assert answer.status_code == 503
    assert matrixed.register() == []
    page = matrixed.api.get(matrixed.path("", "?search=rien"), headers=matrixed.risks.headers)
    assert page.status_code == 200
    assert page.json()["meta"]["total"] == 0


def statements(api: ContractClient, project: Costed, path: str) -> int:
    """Count the statements a reading sends to the database."""
    engine = project.stage.database.engine
    sent: list[str] = []

    def heard(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    event.listen(engine, "before_cursor_execute", heard)
    try:
        answer = api.get(path, headers=project.stage.manager.headers)
    finally:
        event.remove(engine, "before_cursor_execute", heard)
    assert answer.status_code == 200, answer.text
    return len(sent)


@pytest.mark.requirement("WF-RIS-0040-A")
@pytest.mark.parametrize("reading", ["matrix", "detail"])
def test_the_matrix_and_the_detail_cost_the_same_statements_whatever_the_number_of_risks(
    matrixed: Matrixed, reading: str
) -> None:
    first = matrixed.declare("0.3", "Risque 00", "100.00")

    def path() -> str:
        if reading == "matrix":
            return matrixed.path("/matrix")
        return matrixed.path(f"/{first['risk_id']}")

    few = statements(matrixed.api, matrixed.project, path())
    for index in range(1, 11):
        matrixed.declare("0.3", f"Risque {index:02d}", "100.00")
    many = statements(matrixed.api, matrixed.project, path())
    most = MOST_STATEMENTS_OF_MATRIX if reading == "matrix" else MOST_STATEMENTS_OF_DETAIL
    assert 0 < few <= most
    assert many == few
