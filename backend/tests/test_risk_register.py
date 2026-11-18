# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The register of the risks of a project through the service (``listRisks``; US-2600/L1).

The columns as ``getRisk`` reads them, the sort on each, the filters on each column alone and
together (H-01, #1786), the totals of the risks the filters retain whatever the page, the reserve
beside them, the provision of a risk occurred or dismissed as the reference held it (H-03), and the
revision read: the one named, which a marked revision froze. Every answer is checked against the
contract (``ContractClient``).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from nodes_support import mark, put_risk
from projects_support import PROJECTS, Scene, create, designate
from projects_support import scene as make_scene
from risks_support import Costed, Risks, costed, share_row
from sqlalchemy import delete, event, insert, select, update

from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.estimate.interface import Coverage, register_coverage
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node
from waterfall.core.risk_settings.interface import zone_of
from waterfall.core.risks.tables import RiskEvaluation, RiskReferenceShare, RiskReview

if TYPE_CHECKING:
    from collections.abc import Iterator

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

RESERVE = Decimal("850.00")
# The statements the register sends at most, whatever the number of its risks (#4013).
MOST_STATEMENTS = 40
# The five risks: label, probability, severity, the day of the last review.
DELAY = ("Retard de livraison", "0.30", "200.00", date(2026, 1, 10))
STUDY = ("Étude hydrologique incomplète", "0.50", "400.00", date(2026, 2, 20))
STRIKE = ("Grève des transporteurs", "0.10", "100.00", date(2026, 3, 15))
CRANE = ("Panne de la grue", "0.30", "300.00", date(2026, 2, 2))
FOREMAN = ("Départ du chef de chantier", "0.05", "1000.00", date(2026, 4, 1))
ALL = (DELAY, STUDY, STRIKE, CRANE, FOREMAN)
# What the reference held of the two that left the identified state, and the cost at occurrence.
CRANE_SHARE = Decimal("80.00")
FOREMAN_SHARE = Decimal("25.00")
CRANE_COST = Decimal("300.00")


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@pytest.fixture
def reserve() -> Iterator[None]:
    """Answer the coverage of the risks with a reserve, as US-2610 will with the shares."""
    nought = Decimal("0.00")
    withdraw = register_coverage(
        lambda _session, _project, _revision: Coverage(RESERVE, nought, nought, nought, nought)
    )
    yield
    withdraw()


@dataclass(frozen=True)
class Registered:
    """The project with its five risks, the first revision marked and the reference.

    ``first`` the marked revision, which holds the five identified; ``second`` the current one, in
    which the crane occurred and the foreman was dismissed.
    """

    api: ContractClient
    project: Costed
    risks: Risks
    declared: dict[str, dict[str, Any]]
    first: dict[str, Any]
    second: dict[str, Any]

    def path(self, query: str = "") -> str:
        """Give the path of the register, with its query."""
        return f"{PROJECTS}/{self.project.project_id}/risks{query}"

    def read(self, query: str = "") -> Any:
        """Read the register as the manager does."""
        return self.api.get(self.path(query), headers=self.project.stage.manager.headers)

    def page(self, query: str = "") -> dict[str, Any]:
        """Read the register, which must answer; give its body."""
        answer = self.read(query)
        assert answer.status_code == 200, answer.text
        return answer.json()

    def labels(self, query: str = "") -> list[str]:
        """Give the labels of the risks the register lists, in its order."""
        return [item["label"] for item in self.page(query)["items"]]


def _write_reviews(project: Costed, days: dict[UUID, date]) -> None:
    """Set the day of the last review of each risk, in the revision before it is marked."""
    with project.stage.owner.begin() as connection:
        for risk_id, day in days.items():
            connection.execute(
                update(RiskReview).where(RiskReview.risk_id == risk_id).values(reviewed_on=day)
            )


def _reestimate(project: Costed, task_id: UUID, amount: Decimal) -> None:
    """Set the reestimated amount of the lines a task bears, apart from their budgeted amount."""
    with project.stage.owner.begin() as connection:
        lines = select(Node.id).where(Node.parent_id == task_id)
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id.in_(lines))
            .values(reestimated_amount=amount)
        )


def _occur(project: Costed, risk: dict[str, Any], cost: Decimal, task: str | None) -> None:
    """Make a risk occurred at a cost, and a task of the estimate the one that came from it."""
    risk_id = UUID(risk["risk_id"])
    if task is not None:
        put_risk(project.stage, str(project.tasks[task]), risk_id)
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskEvaluation)
            .where(RiskEvaluation.risk_id == risk_id)
            .values(state="occurred", provision_node_id=None, occurrence_cost=cost)
        )


@pytest.fixture
def register(api: ContractClient, project: Costed) -> Registered:
    """Declare the five risks, mark and designate the revision, open the next and move two."""
    risks = Risks(api, project)
    declared: dict[str, dict[str, Any]] = {}
    for label, probability, severity, _ in ALL:
        risk = risks.declared(probability, label)
        risks.costed_at(risk, project.revision_id, severity)
        declared[label] = risks.risk(risk)
    days = {UUID(declared[each[0]]["risk_id"]): each[3] for each in ALL}
    _write_reviews(project, days)
    revision = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
    mark(project.stage, {"revision_id": str(project.revision_id)})
    first = api.get(revision, headers=risks.headers).json()
    designate(api, project.stage, first)
    with project.stage.owner.begin() as connection:
        connection.execute(delete(RiskReferenceShare))
        for each, share in ((CRANE, CRANE_SHARE), (FOREMAN, FOREMAN_SHARE)):
            connection.execute(
                insert(RiskReferenceShare).values(
                    **share_row(
                        project.project_id,
                        UUID(declared[each[0]]["risk_id"]),
                        UUID(first["revision_id"]),
                        provision_amount=share,
                    )
                )
            )
    second = risks.revision()
    current = UUID(second["revision_id"])
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskEvaluation)
            .where(
                RiskEvaluation.risk_id == UUID(declared[CRANE[0]]["risk_id"]),
                RiskEvaluation.revision_id == current,
            )
            .values(state="occurred", provision_node_id=None, occurrence_cost=CRANE_COST)
        )
        connection.execute(
            update(RiskEvaluation)
            .where(
                RiskEvaluation.risk_id == UUID(declared[FOREMAN[0]]["risk_id"]),
                RiskEvaluation.revision_id == current,
            )
            .values(state="dismissed", provision_node_id=None)
        )
    return Registered(api, project, risks, declared, first, second)


# --- The columns ----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_register_gives_each_risk_with_its_columns_as_the_detail_reads_it(
    register: Registered,
) -> None:
    # The six columns, the cost at occurrence and the reestimated of the occurred, the cell of the
    # matrix: the register gives each risk as ``getRisk`` does, in the order of the declaration.
    body = register.page()
    assert [item["label"] for item in body["items"]] == [each[0] for each in ALL]
    for item in body["items"]:
        detail = register.risks.risk({"risk_id": item["risk_id"]})
        assert item == detail
    delay, _, _, crane, foreman = body["items"]
    assert (delay["probability"], delay["severity"], delay["provision_amount"]) == (
        "0.3",
        "200.00",
        "60.00",
    )
    assert (delay["state"], delay["last_review_on"]) == ("identified", "2026-01-10")
    assert (delay["occurrence_cost"], delay["occurred_reestimated_amount"]) == (None, None)
    assert (crane["state"], crane["occurrence_cost"]) == ("occurred", "300.00")
    assert crane["occurred_reestimated_amount"] == "0.00"
    assert foreman["state"] == "dismissed"
    assert body["meta"] == {"limit": 50, "offset": 0, "total": 5}


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_provision_of_an_occurred_or_dismissed_risk_is_the_one_the_reference_held(
    register: Registered,
) -> None:
    # The crane weighs 300 at 30 % in the severity, 90 as identified; occurred, it keeps the 80 the
    # reference held, and the foreman the 25 (H-03), whatever their probability and severity.
    by_label = {item["label"]: item for item in register.page()["items"]}
    assert by_label[CRANE[0]]["provision_amount"] == "80.00"
    assert by_label[FOREMAN[0]]["provision_amount"] == "25.00"
    assert (by_label[CRANE[0]]["severity"], by_label[FOREMAN[0]]["severity"]) == (
        "300.00",
        "1000.00",
    )


@pytest.mark.requirement("WF-RIS-0040-A")
def test_an_occurred_risk_shows_the_reestimated_amount_of_the_lines_that_came_from_it(
    api: ContractClient, project: Costed
) -> None:
    # The task of 400 that came from the occurrence of the crane: its line, reestimated, is shown
    # beside the cost at occurrence; an occurred risk with no reference holds a provision of nought.
    risks = Risks(api, project)
    risk = risks.declared("0.30", CRANE[0])
    risks.costed_at(risk, project.revision_id, "300.00")
    put_risk(project.stage, str(project.tasks["Réalisation"]), UUID(risk["risk_id"]))
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskEvaluation)
            .where(RiskEvaluation.risk_id == UUID(risk["risk_id"]))
            .values(state="occurred", provision_node_id=None, occurrence_cost=CRANE_COST)
        )
    path = f"{PROJECTS}/{project.project_id}/risks"
    item = api.get(path, headers=project.stage.manager.headers).json()["items"][0]
    assert (item["occurred_reestimated_amount"], item["provision_amount"]) == ("400.00", "0.00")
    # The line reestimated at another amount than it was budgeted at: the column follows the
    # reestimated amount, not the budgeted one.
    _reestimate(project, project.tasks["Réalisation"], Decimal("430.00"))
    item = api.get(path, headers=project.stage.manager.headers).json()["items"][0]
    assert item["occurred_reestimated_amount"] == "430.00"
    assert item == risks.risk(risk)


# --- The sort -------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_sort_by_provision_ranks_the_risks_from_the_heaviest_to_the_lightest(
    register: Registered,
) -> None:
    # 200, 80 (the crane, occurred), 60, 25 (the foreman, dismissed) and 10.
    query = "?sort_by=provision_amount&sort_order=desc"
    assert register.labels(query) == [STUDY[0], CRANE[0], DELAY[0], FOREMAN[0], STRIKE[0]]
    ascending = "?sort_by=provision_amount"
    assert register.labels(ascending) == [STRIKE[0], FOREMAN[0], DELAY[0], CRANE[0], STUDY[0]]


@pytest.mark.requirement("WF-RIS-0040-A")
@pytest.mark.parametrize(
    ("column", "ascending", "descending"),
    [
        # The labels by the order of the code points: « É » comes after every ASCII letter.
        ("label", [FOREMAN, STRIKE, CRANE, DELAY, STUDY], [STUDY, DELAY, CRANE, STRIKE, FOREMAN]),
        # A tie, the delay and the crane at 30 %, keeps the order of the declaration in both.
        (
            "probability",
            [FOREMAN, STRIKE, DELAY, CRANE, STUDY],
            [STUDY, DELAY, CRANE, STRIKE, FOREMAN],
        ),
        (
            "severity",
            [STRIKE, DELAY, CRANE, STUDY, FOREMAN],
            [FOREMAN, STUDY, CRANE, DELAY, STRIKE],
        ),
        ("state", [DELAY, STUDY, STRIKE, CRANE, FOREMAN], [FOREMAN, CRANE, DELAY, STUDY, STRIKE]),
        (
            "last_review_on",
            [DELAY, CRANE, STUDY, STRIKE, FOREMAN],
            [FOREMAN, STRIKE, STUDY, CRANE, DELAY],
        ),
    ],
)
def test_the_register_sorts_on_each_column_in_both_directions(
    register: Registered,
    column: str,
    ascending: list[tuple[str, ...]],
    descending: list[tuple[str, ...]],
) -> None:
    assert register.labels(f"?sort_by={column}") == [each[0] for each in ascending]
    assert register.labels(f"?sort_by={column}&sort_order=desc") == [each[0] for each in descending]


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_risks_with_no_cost_at_occurrence_sort_after_the_others_and_before_when_descending(
    register: Registered,
) -> None:
    # Four risks have none: they come after the crane ascending, before it descending, each tie
    # keeping the order of the declaration in both directions (WF-IHM-0060).
    nulls = [DELAY[0], STUDY[0], STRIKE[0], FOREMAN[0]]
    assert register.labels("?sort_by=occurrence_cost") == [CRANE[0], *nulls]
    assert register.labels("?sort_by=occurrence_cost&sort_order=desc") == [*nulls, CRANE[0]]
    assert register.labels("?sort_by=occurred_reestimated_amount")[0] == CRANE[0]


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_sort_on_the_cost_at_occurrence_and_the_reestimated_amount_ranks_the_occurred(
    api: ContractClient, project: Costed
) -> None:
    # Two risks occurred at other costs, whose tasks hold other reestimated amounts (the study 600
    # reestimated at 650, the realisation 400 at 430), and one identified, which has neither.
    risks = Risks(api, project)
    names = ("Rupture de stock", "Défaillance du sous-traitant", "Crue")
    made = [risks.declared("0.30", label) for label in names]
    for risk in made:
        risks.costed_at(risk, project.revision_id, "100.00")
    _occur(project, made[0], Decimal("120.00"), "Réalisation")
    _occur(project, made[1], Decimal("340.00"), "Étude")
    _reestimate(project, project.tasks["Réalisation"], Decimal("430.00"))
    _reestimate(project, project.tasks["Étude"], Decimal("650.00"))
    path = f"{PROJECTS}/{project.project_id}/risks"
    headers = project.stage.manager.headers

    def labels(query: str) -> list[str]:
        answer = api.get(f"{path}?{query}", headers=headers)
        assert answer.status_code == 200, answer.text
        return [item["label"] for item in answer.json()["items"]]

    cost, reestimated = "sort_by=occurrence_cost", "sort_by=occurred_reestimated_amount"
    first, second, none = names
    assert labels(cost) == [first, second, none]
    assert labels(f"{cost}&sort_order=desc") == [none, second, first]
    # The reestimated amounts, 430 then 650, rank the two the other way round than the costs.
    assert labels(reestimated) == [first, second, none]
    assert labels(f"{reestimated}&sort_order=desc") == [none, second, first]
    listed = {
        item["label"]: item["occurred_reestimated_amount"]
        for item in api.get(path, headers=headers).json()["items"]
    }
    assert listed == {first: "430.00", second: "650.00", none: None}


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_risk_never_reviewed_sorts_after_the_others_and_before_them_when_descending(
    api: ContractClient, project: Costed
) -> None:
    risks = Risks(api, project)
    reviewed = risks.declared("0.30", "Risque revu")
    never = risks.declared("0.30", "Risque jamais revu")
    for risk in (reviewed, never):
        risks.costed_at(risk, project.revision_id, "100.00")
    with project.stage.owner.begin() as connection:
        connection.execute(delete(RiskReview).where(RiskReview.risk_id == UUID(never["risk_id"])))
    _write_reviews(project, {UUID(reviewed["risk_id"]): date(2026, 1, 10)})
    path = f"{PROJECTS}/{project.project_id}/risks?sort_by=last_review_on"
    headers = project.stage.manager.headers
    for query, wanted in (
        ("", [reviewed["label"], never["label"]]),
        ("&sort_order=desc", [never["label"], reviewed["label"]]),
    ):
        body = api.get(f"{path}{query}", headers=headers).json()
        assert [item["label"] for item in body["items"]] == wanted
    assert body["items"][0]["last_review_on"] is None


# --- The totals -----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_three_totals_are_distinct_and_the_reserve_is_beside_them(
    register: Registered, reserve: None
) -> None:
    # 200 + 60 + 10 identified at their provision, the occurred at the 80 the reference held, the
    # dismissed at the 25; the reserve of the coverage beside them.
    del reserve
    assert register.page()["totals"] == {
        "identified": "270.00",
        "occurred": "80.00",
        "dismissed": "25.00",
        "total": "375.00",
        "reserve": "850.00",
    }


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_totals_are_those_of_the_risks_retained_not_of_the_page(
    register: Registered, reserve: None
) -> None:
    del reserve
    body = register.page("?limit=1&offset=1")
    assert [item["label"] for item in body["items"]] == [STUDY[0]]
    assert body["meta"] == {"limit": 1, "offset": 1, "total": 5}
    assert body["totals"]["total"] == "375.00"
    only = register.page("?states=identified&limit=1&sort_by=provision_amount&sort_order=desc")
    assert only["meta"]["total"] == 3
    assert only["totals"] == {
        "identified": "270.00",
        "occurred": "0.00",
        "dismissed": "0.00",
        "total": "270.00",
        "reserve": "850.00",
    }


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_register_with_no_revision_is_empty_and_its_totals_nought(
    api: ContractClient, stage: Scene
) -> None:
    other = create(api, stage.manager, label="Sans révision")
    path = f"{PROJECTS}/{other['project_id']}/risks"
    body = api.get(path, headers=stage.manager.headers).json()
    assert body["items"] == []
    assert body["meta"]["total"] == 0
    assert set(body["totals"].values()) == {"0.00"}


# --- The filters ----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0130-A")
@pytest.mark.parametrize(
    ("query", "kept"),
    [
        ("states=occurred,dismissed", [CRANE, FOREMAN]),
        ("search=etude", [STUDY]),
        ("search=GRÈVE", [STRIKE]),
        ("probability_min=0.3", [DELAY, STUDY, CRANE]),
        ("probability_max=0.1", [STRIKE, FOREMAN]),
        ("probability_min=0.1&probability_max=0.3", [DELAY, STRIKE, CRANE]),
        ("severity_min=300", [STUDY, CRANE, FOREMAN]),
        ("severity_max=200.00", [DELAY, STRIKE]),
        ("provision_amount_min=60&provision_amount_max=80", [DELAY, CRANE]),
        ("occurrence_cost_min=300", [CRANE]),
        ("occurrence_cost_max=299.99", []),
        ("occurred_reestimated_amount_min=0", [CRANE]),
        ("occurred_reestimated_amount_max=0.00", [CRANE]),
        ("last_review_on_from=2026-03-15", [STRIKE, FOREMAN]),
        ("last_review_on_to=2026-02-02", [DELAY, CRANE]),
        ("last_review_on_from=2026-02-02&last_review_on_to=2026-03-15", [STUDY, STRIKE, CRANE]),
        ("states=identified&severity_min=150&provision_amount_max=100", [DELAY]),
    ],
)
def test_the_register_is_filtered_on_each_column_alone_and_combined(
    register: Registered, query: str, kept: list[tuple[str, ...]]
) -> None:
    # Each bound included, the occurred alone retained by a bound of the cost at occurrence or of
    # the reestimated amount, the end of a period included; the filters combine (H-01, #1786).
    body = register.page(f"?{query}")
    wanted = {each[0] for each in kept}
    assert {item["label"] for item in body["items"]} == wanted
    assert body["meta"]["total"] == len(kept)


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_zone_filter_keeps_the_risks_whose_cell_is_in_one_of_the_zones(
    register: Registered, stage: Scene
) -> None:
    # The zone each risk falls in, laid down from the matrix of the reference settings and the base
    # of the project (1 000, the budget of the reference): the severity as a share of it, the
    # probability as it is.
    with stage.database.transaction() as session:
        matrix = read_reference_settings(session).risk_matrix
    ratio = {label: Decimal(severity) / 1000 for label, _, severity, _ in ALL}
    chance = {label: Decimal(probability) for label, probability, _, _ in ALL}
    zone = {
        label: zone_of(matrix, chance[label], ratio[label]) for label in (each[0] for each in ALL)
    }
    assert len(set(zone.values())) > 1
    for each in set(zone.values()):
        expected = {label for label, found in zone.items() if found == each}
        assert set(register.labels(f"?zones={each}")) == expected
    everything = ",".join(sorted(set(zone.values())))
    assert register.page(f"?zones={everything}")["meta"]["total"] == 5


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_totals_follow_a_filter_that_retains_one_risk(
    register: Registered, reserve: None
) -> None:
    del reserve
    body = register.page("?probability_min=0.5")
    assert [item["label"] for item in body["items"]] == [STUDY[0]]
    assert body["totals"] == {
        "identified": "200.00",
        "occurred": "0.00",
        "dismissed": "0.00",
        "total": "200.00",
        "reserve": "850.00",
    }
    nothing = register.page("?probability_min=0.9")
    assert (nothing["items"], nothing["meta"]["total"]) == ([], 0)
    assert set(nothing["totals"]) - {"reserve"} <= {"identified", "occurred", "dismissed", "total"}
    assert nothing["totals"]["total"] == "0.00"


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_risks_not_reviewed_since_a_day_are_those_whose_last_review_ends_before_it(
    register: Registered,
) -> None:
    # The periodic review presents the risks not reviewed since the last marking (WF-RIS-0020).
    assert set(register.labels("?last_review_on_to=2026-02-19")) == {
        DELAY[0],
        CRANE[0],
    }


# --- The refusals ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0130-A")
@pytest.mark.parametrize(
    ("query", "fields"),
    [
        (
            "probability_min=abc",
            [{"pointer": "/query/probability_min", "code": "NUMBER_INVALID"}],
        ),
        (
            "severity_max=1.234&provision_amount_min=x",
            [
                {"pointer": "/query/severity_max", "code": "NUMBER_INVALID"},
                {"pointer": "/query/provision_amount_min", "code": "NUMBER_INVALID"},
            ],
        ),
        (
            "severity_min=500&severity_max=100",
            [
                {
                    "pointer": "/query/severity_max",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": "500"},
                }
            ],
        ),
        (
            "last_review_on_from=2026-03-01&last_review_on_to=2026-02-01",
            [
                {
                    "pointer": "/query/last_review_on_to",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": "2026-03-01"},
                }
            ],
        ),
        (
            "last_review_on_from=2026-13-01&last_review_on_to=hier",
            [
                {"pointer": "/query/last_review_on_from", "code": "DATE_INVALID"},
                {"pointer": "/query/last_review_on_to", "code": "DATE_INVALID"},
            ],
        ),
        ("states=identified,lost", [{"pointer": "/query/states", "code": "VALIDATION_FAILED"}]),
        ("zones=red", [{"pointer": "/query/zones", "code": "VALIDATION_FAILED"}]),
    ],
)
def test_a_filter_at_fault_is_refused_naming_every_parameter(
    register: Registered, query: str, fields: list[dict[str, Any]]
) -> None:
    answer = register.read(f"?{query}")
    assert answer.status_code == 422, answer.text
    body = answer.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert body["fields"] == fields


NUMBER_COLUMNS = (
    "probability",
    "severity",
    "provision_amount",
    "occurrence_cost",
    "occurred_reestimated_amount",
)


@pytest.mark.requirement("WF-IHM-0130-A")
@pytest.mark.parametrize("column", NUMBER_COLUMNS)
def test_each_column_of_numbers_refuses_a_bound_that_is_none_and_an_inverted_pair(
    register: Registered, column: str
) -> None:
    answer = register.read(f"?{column}_min=abc&{column}_max=x")
    assert answer.status_code == 422, answer.text
    assert answer.json()["fields"] == [
        {"pointer": f"/query/{column}_min", "code": "NUMBER_INVALID"},
        {"pointer": f"/query/{column}_max", "code": "NUMBER_INVALID"},
    ]
    inverted = register.read(f"?{column}_min=5&{column}_max=1")
    assert inverted.status_code == 422, inverted.text
    assert inverted.json()["fields"] == [
        {
            "pointer": f"/query/{column}_max",
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"minimum": "5"},
        }
    ]


@pytest.mark.requirement("WF-IHM-0130-A")
def test_a_parameter_repeated_answers_the_same_whichever_way_it_is_read(
    register: Registered,
) -> None:
    # The query is read once, as the service types it: a repeated bound keeps one value, the last,
    # for the filter and for the refusal alike.
    twice = register.page("?severity_min=1&severity_min=300")
    assert twice == register.page("?severity_min=300")
    assert register.read("?severity_min=300&severity_min=abc").status_code == 422
    assert register.read("?severity_min=abc&severity_min=300").status_code == 200


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_register_costs_the_same_statements_whatever_the_number_of_its_risks(
    api: ContractClient, project: Costed
) -> None:
    # The context is read once for all the risks: five risks or fifteen, the same statements.
    risks = Risks(api, project)
    path = f"{PROJECTS}/{project.project_id}/risks"
    engine = project.stage.database.engine
    counts: list[int] = []

    def declare(count: int, offset: int) -> None:
        for index in range(count):
            risk = risks.declared("0.30", f"Risque {offset + index:02d}")
            risks.costed_at(risk, project.revision_id, "100.00")
            if (offset + index) % 5 == 0:
                _occur(project, risk, Decimal("50.00"), None)

    def measure() -> int:
        sent: list[str] = []

        def heard(*arguments: Any) -> None:
            sent.append(str(arguments[2]))

        event.listen(engine, "before_cursor_execute", heard)
        try:
            answer = api.get(path, headers=project.stage.manager.headers)
        finally:
            event.remove(engine, "before_cursor_execute", heard)
        assert answer.status_code == 200, answer.text
        counts.append(answer.json()["meta"]["total"])
        return len(sent)

    declare(5, 0)
    few = measure()
    declare(10, 5)
    many = measure()
    assert counts == [5, 15]
    # A count of nought would hold the equality for nothing; the bound is the reading's own.
    assert 0 < few <= MOST_STATEMENTS
    assert many == few


# --- The revision read ----------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_marked_revision_gives_the_evaluation_it_froze(register: Registered) -> None:
    # Read in the first revision, marked, the crane and the foreman are identified, with the
    # provision of their severity; without it, the current revision, where they left that state.
    first = register.first["revision_id"]
    body = register.page(f"?revision_id={first}")
    assert {item["state"] for item in body["items"]} == {"identified"}
    assert body["totals"]["identified"] == "410.00"
    assert (body["totals"]["occurred"], body["totals"]["dismissed"]) == ("0.00", "0.00")
    current = register.page()
    assert current["totals"]["identified"] == "270.00"


@pytest.mark.requirement("WF-RIS-0030-A")
def test_without_a_current_revision_the_last_marked_one_is_read(register: Registered) -> None:
    # The current revision is abandoned: the register reads the last marked, with no revision
    # named, and the risk occurred there is identified again (WF-RIS-0020).
    register.risks.abandon(register.second)
    body = register.page()
    assert {item["state"] for item in body["items"]} == {"identified"}
    assert body["totals"]["identified"] == "410.00"


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_revision_of_another_project_or_unknown_is_not_found(
    register: Registered, api: ContractClient, stage: Scene
) -> None:
    other = create(api, stage.manager, label="Autre")
    unknown = "00000000-0000-4000-8000-000000000001"
    assert register.read(f"?revision_id={unknown}").status_code == 404
    path = f"{PROJECTS}/{other['project_id']}/risks"
    named = api.get(
        f"{path}?revision_id={register.first['revision_id']}", headers=stage.manager.headers
    )
    assert named.status_code == 404
