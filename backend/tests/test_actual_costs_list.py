# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the actual costs read, and their totals (US-1620/L1).

``listActualCosts`` on the lines an import of the witness loads through the interface: the three
totals of all the lines retained and not of the page, the filters by subproject, by period and by
scope, the sort by each column, the page, the columns kept of the files of the imports the lines
retained name, and the instant of the last import. A filter the server cannot apply is refused
(422).
Every answer is checked against the contract.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from costs_support import report_row
from nodes_support import faults, refusal
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import insert, update

from waterfall.core.costs.interface import (
    PROJECT,
    CostImportLoad,
    CostLineLoad,
    actual_costs_until,
    load_cost_import,
    load_cost_lines,
)
from waterfall.core.costs.tables import CostLine
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from collections.abc import Sequence

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

FIRST = datetime(2026, 5, 4, 8, 30, tzinfo=UTC)
SECOND = datetime(2026, 6, 3, 8, 30, tzinfo=UTC)
LATER = date(2099, 12, 31)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def path(stage: Scene) -> str:
    """Give the path of the actual costs of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/actual-costs"


def project_of(stage: Scene) -> UUID:
    """Give the identifier of the project of the stage."""
    return UUID(stage.project["project_id"])


def made(api: ContractClient, stage: Scene, code: str, label: str) -> dict[str, Any]:
    """Create a subproject of the project of the stage, as its manager does."""
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": label},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def line(
    number: str,
    code: str | None = None,
    amount: str = "100.00",
    day: date = date(2026, 4, 2),
    item: str | None = None,
    **kept: str,
) -> CostLineLoad:
    """Give a line an import loads: its document, its code, its amount, its date, its item."""
    return CostLineLoad(uuid4(), number, item, day, Decimal(amount), code, kept)


def bring(
    stage: Scene,
    lines: Sequence[CostLineLoad],
    columns: Sequence[str] = ("Fournisseur",),
    at: datetime = FIRST,
) -> UUID:
    """Load an import applied on the project of the stage, with its columns kept; give its entry."""
    report = uuid4()
    entry = CostImportLoad(
        cost_import_id=uuid4(),
        import_report_id=report,
        imported_at=at,
        requested_by=stage.manager.user_id,
        period_from=date(2026, 4, 1),
        period_to=date(2026, 4, 30),
        created_count=len(lines),
        updated_count=0,
        unchanged_count=0,
        rejected_count=0,
        passthrough_columns=tuple(columns),
    )
    with stage.owner.begin() as connection:
        connection.execute(insert(ImportReport).values(**report_row(project_of(stage), id=report)))
    with stage.database.transaction() as session:
        load_cost_import(session, project_of(stage), entry)
        load_cost_lines(
            session, project_of(stage), entry.cost_import_id, lines, Act(stage.manager.user_id, at)
        )
    return entry.cost_import_id


def exclude_by_owner(stage: Scene, *numbers: str, reason: str | None = None) -> None:
    """Exclude lines around the service, as a past exclusion would have left them."""
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostLine)
            .where(CostLine.document_number.in_(numbers))
            .values(is_in_tracked_scope=False, excluded_reason=reason)
        )


def read(api: ContractClient, stage: Scene, **query: str | int) -> dict[str, Any]:
    """Read the actual costs as the manager does, with a query that must be accepted."""
    answer = api.get(path(stage), headers=stage.manager.headers, params=query)
    assert answer.status_code == 200, answer.text
    return answer.json()


def numbers(read_: dict[str, Any]) -> list[str]:
    """Give the document numbers of the lines of a page, in their order."""
    return [item["document_number"] for item in read_["items"]]


def three_lines(stage: Scene) -> None:
    """Load three lines: two for SP-CAB, one of them excluded, and one without a subproject."""
    bring(
        stage,
        [
            line("FA-1", "SP-CAB", "100.00", date(2026, 4, 2), Fournisseur="Durand"),
            line("FA-2", "SP-CAB", "250.50", date(2026, 4, 10), Fournisseur="Rhône"),
            line("FA-3", None, "-40.00", date(2026, 5, 5), Fournisseur="Durand"),
        ],
    )
    exclude_by_owner(stage, "FA-2", reason="Câbles d'un autre projet")


@pytest.mark.requirement("WF-CRE-0040-A")
def test_the_three_totals_are_those_of_all_the_lines_retained_and_not_of_the_page(
    api: ContractClient, stage: Scene
) -> None:
    # « Les trois totaux sont présents, et le total général égale la somme du total du périmètre
    # suivi et du total exclu. » : on the whole set, a page of one line or a page beyond the end.
    three_lines(stage)
    whole = read(api, stage)
    assert whole["totals"] == {"tracked": "60.00", "excluded": "250.50", "overall": "310.50"}
    assert whole["meta"]["total"] == 3
    paged = read(api, stage, limit=1)
    assert len(paged["items"]) == 1
    assert paged["totals"] == whole["totals"]
    assert paged["meta"] == {**whole["meta"], "limit": 1}
    beyond = read(api, stage, offset=10)
    assert (beyond["items"], beyond["totals"]) == ([], whole["totals"])


@pytest.mark.requirement("WF-CRE-0030-A")
def test_an_excluded_line_stays_in_the_list_and_in_no_tracked_sum(
    api: ContractClient, stage: Scene
) -> None:
    # « Une ligne exclue n'apparaît dans aucun total d'indicateur, et reste visible dans la
    # consultation des coûts réels. » : ``in_tracked_scope=false`` retains it alone.
    three_lines(stage)
    everything = read(api, stage)
    [excluded] = [item for item in everything["items"] if item["document_number"] == "FA-2"]
    assert (excluded["is_in_tracked_scope"], excluded["excluded_reason"]) == (
        False,
        "Câbles d'un autre projet",
    )
    alone = read(api, stage, in_tracked_scope="false")
    assert numbers(alone) == ["FA-2"]
    assert alone["totals"] == {"tracked": "0.00", "excluded": "250.50", "overall": "250.50"}
    tracked = read(api, stage, in_tracked_scope="true")
    assert sorted(numbers(tracked)) == ["FA-1", "FA-3"]
    assert tracked["totals"] == {"tracked": "60.00", "excluded": "0.00", "overall": "60.00"}
    # The sum the indicators read, the tracked lines alone, leaves the excluded line out.
    with stage.database.transaction() as session:
        assert actual_costs_until(session, project_of(stage), LATER, PROJECT) == Decimal("60.00")


@pytest.mark.requirement("WF-CRE-0040-A")
def test_a_filter_by_subproject_by_period_or_by_scope_applies_to_the_three_totals(
    api: ContractClient, stage: Scene
) -> None:
    # « Un filtre par sous-projet ou par période s'applique aux trois (WF-IHM-0130). » : the
    # subproject by its identifier or ``unassigned``, the period on the date of the document, its
    # two ends included.
    cabling = made(api, stage, "SP-CAB", "Câblage")
    three_lines(stage)
    by_subproject = read(api, stage, subproject_id=cabling["subproject_id"])
    assert sorted(numbers(by_subproject)) == ["FA-1", "FA-2"]
    assert by_subproject["totals"] == {
        "tracked": "100.00",
        "excluded": "250.50",
        "overall": "350.50",
    }
    unassigned = read(api, stage, subproject_id="unassigned")
    assert numbers(unassigned) == ["FA-3"]
    assert unassigned["totals"] == {"tracked": "-40.00", "excluded": "0.00", "overall": "-40.00"}
    between = read(api, stage, **{"from": "2026-04-10", "to": "2026-05-05"})
    assert sorted(numbers(between)) == ["FA-2", "FA-3"]
    assert between["totals"] == {"tracked": "-40.00", "excluded": "250.50", "overall": "210.50"}
    one_day = read(api, stage, **{"from": "2026-04-10", "to": "2026-04-10"})
    assert numbers(one_day) == ["FA-2"]
    after = read(api, stage, **{"from": "2026-05-06"})
    assert (after["items"], after["totals"]["overall"]) == ([], "0.00")
    combined = read(api, stage, subproject_id=cabling["subproject_id"], in_tracked_scope="true")
    assert numbers(combined) == ["FA-1"]


@pytest.mark.requirement("WF-CRE-0040-A")
def test_the_columns_kept_and_the_last_import_follow_the_filters(
    api: ContractClient, stage: Scene
) -> None:
    # The union of the columns kept, like the totals, is the one of the lines retained: the two
    # imports of the project declare different columns, and a filter keeps the lines of one.
    bring(stage, [line("FA-1", "SP-CAB", Fournisseur="Durand")], ("Fournisseur",), FIRST)
    bring(
        stage,
        [line("FA-2", None, "20.00", date(2026, 5, 20), Fournisseur="Rhône", Commande="Pupitre")],
        ("Fournisseur", "Commande"),
        SECOND,
    )
    whole = read(api, stage)
    assert whole["meta"]["passthrough_columns"] == ["Fournisseur", "Commande"]
    assert whole["last_import_at"] == "2026-06-03T08:30:00Z"
    older = read(api, stage, to="2026-04-30")
    assert numbers(older) == ["FA-1"]
    assert older["meta"]["passthrough_columns"] == ["Fournisseur"]
    assert older["last_import_at"] == "2026-05-04T08:30:00Z"
    assert older["items"][0]["passthrough"] == {"Fournisseur": "Durand"}


@pytest.mark.requirement("WF-CRE-0010-A")
def test_the_columns_kept_are_the_union_in_the_order_of_the_imports_that_the_lines_name(
    api: ContractClient, stage: Scene
) -> None:
    # Each column at its first declaration, the imports in the order they were applied, the columns
    # of an import in the order of its file; an import no retained line names any longer declares
    # nothing: the line it brought was written again by the next.
    bring(stage, [line("FA-1", Fournisseur="a")], ("B", "A"), FIRST)
    bring(stage, [line("FA-2", Fournisseur="b")], ("A", "C"), SECOND)
    assert read(api, stage)["meta"]["passthrough_columns"] == ["B", "A", "C"]
    bring(stage, [line("FA-1", Fournisseur="a")], ("D",), datetime(2026, 7, 1, tzinfo=UTC))
    assert read(api, stage)["meta"]["passthrough_columns"] == ["A", "C", "D"]


@pytest.mark.requirement("WF-CRE-0050-A")
def test_a_project_without_a_line_reads_empty_totals_and_no_last_import(
    api: ContractClient, stage: Scene
) -> None:
    empty = read(api, stage)
    assert empty == {
        "items": [],
        "totals": {"tracked": "0.00", "excluded": "0.00", "overall": "0.00"},
        "last_import_at": None,
        "meta": {"limit": 50, "offset": 0, "total": 0, "passthrough_columns": []},
    }


@pytest.mark.requirement("WF-CRE-0020-A")
def test_a_line_names_its_subproject_by_its_code_and_its_label_unknown_code_included(
    api: ContractClient, stage: Scene
) -> None:
    # The code is kept as read; the label is resolved at the reading, none for a line charged to
    # the project alone, whether it bears no code or one no subproject bears.
    cabling = made(api, stage, "SP-CAB", "Câblage")
    bring(stage, [line("FA-1", "SP-CAB"), line("FA-2", "SP-AUT"), line("FA-3", None)])
    items = {item["document_number"]: item for item in read(api, stage)["items"]}
    held = items["FA-1"]
    assert (held["subproject_id"], held["subproject_code"], held["subproject_label"]) == (
        cabling["subproject_id"],
        "SP-CAB",
        "Câblage",
    )
    waiting = items["FA-2"]
    assert (waiting["subproject_id"], waiting["subproject_code"], waiting["subproject_label"]) == (
        None,
        "SP-AUT",
        None,
    )
    assert items["FA-3"]["subproject_code"] is None
    assert held["audit"]["created_by"]["user_id"] == str(stage.manager.user_id)


@pytest.mark.requirement("WF-CRE-0040-A")
def test_a_period_reversed_and_an_unknown_subproject_are_refused_on_their_parameter(
    api: ContractClient, stage: Scene
) -> None:
    # « … une fin qui précède le début refusée par 422 ; un sous-projet inconnu par
    # UNKNOWN_SUBPROJECT » : no empty list stands for a refusal.
    three_lines(stage)
    inverted = api.get(
        path(stage),
        headers=stage.manager.headers,
        params={"from": "2026-04-30", "to": "2026-03-01"},
    )
    assert faults(inverted) == [("/query/to", "VALUE_OUT_OF_RANGE", {"minimum": "2026-04-30"})]
    for unknown in (str(uuid4()), "not-an-identifier"):
        answer = api.get(
            path(stage), headers=stage.manager.headers, params={"subproject_id": unknown}
        )
        assert faults(answer) == [("/query/subproject_id", "UNKNOWN_SUBPROJECT", {})]
    both = api.get(
        path(stage),
        headers=stage.manager.headers,
        params={"from": "2026-04-30", "to": "2026-03-01", "subproject_id": str(uuid4())},
    )
    assert [pointer for pointer, _, _ in faults(both)] == ["/query/to", "/query/subproject_id"]
    malformed = api.get(path(stage), headers=stage.manager.headers, params={"from": "2026-13-45"})
    assert faults(malformed)[0][:2] == ("/query/from", "DATE_INVALID")


@pytest.mark.requirement("WF-CRE-0040-A")
def test_a_subproject_of_another_project_is_unknown(api: ContractClient, stage: Scene) -> None:
    other = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "Autre projet"})
    assert other.status_code == 201, other.text
    elsewhere = api.post(
        f"{PROJECTS}/{other.json()['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-AUT", "label": "Ailleurs"},
    )
    assert elsewhere.status_code == 201, elsewhere.text
    answer = api.get(
        path(stage),
        headers=stage.manager.headers,
        params={"subproject_id": elsewhere.json()["subproject_id"]},
    )
    assert faults(answer) == [("/query/subproject_id", "UNKNOWN_SUBPROJECT", {})]


@pytest.mark.requirement("WF-IHM-0060-A")
def test_the_most_recent_documents_come_first_by_default_and_a_page_continues_the_last(
    api: ContractClient, stage: Scene
) -> None:
    bring(
        stage,
        [
            line("FA-1", day=date(2026, 4, 1)),
            line("FA-2", day=date(2026, 4, 3)),
            line("FA-3", day=date(2026, 4, 2)),
            line("FA-4", day=date(2026, 4, 4)),
            line("FA-5", day=date(2026, 4, 5)),
        ],
    )
    assert numbers(read(api, stage)) == ["FA-5", "FA-4", "FA-2", "FA-3", "FA-1"]
    assert numbers(read(api, stage, limit=2)) == ["FA-5", "FA-4"]
    assert numbers(read(api, stage, limit=2, offset=2)) == ["FA-2", "FA-3"]
    assert numbers(read(api, stage, limit=2, offset=4)) == ["FA-1"]
    assert numbers(read(api, stage, sort_by="document_date", sort_order="asc")) == [
        "FA-1",
        "FA-3",
        "FA-2",
        "FA-4",
        "FA-5",
    ]


@pytest.mark.requirement("WF-IHM-0060-A")
def test_each_column_sorts_in_code_point_order_the_absent_values_after_in_ascending_order(
    api: ContractClient, stage: Scene
) -> None:
    # « Every column of the grid can be sorted » : the item and the reason compare as text, without
    # reading a number ("10" before "2"), a line without a value after the others in ascending order
    # and before them in descending order.
    bring(
        stage,
        [
            line("FA-1", "SP-B", "30.00", date(2026, 4, 3), "2", Fournisseur="Zéphyr"),
            line("FA-2", "SP-A", "-5.00", date(2026, 4, 2), "10", Fournisseur="Atelier"),
            line("FA-3", None, "7.00", date(2026, 4, 1), None),
            line("FA-4", "SP-C", "100.00", date(2026, 4, 4), "A", Fournisseur="Zeta"),
        ],
    )
    exclude_by_owner(stage, "FA-4", reason="b")
    exclude_by_owner(stage, "FA-1", reason="a")

    def order(column: str, way: str = "asc") -> list[str]:
        return numbers(read(api, stage, sort_by=column, sort_order=way))

    assert order("document_number") == ["FA-1", "FA-2", "FA-3", "FA-4"]
    assert order("document_number", "desc") == ["FA-4", "FA-3", "FA-2", "FA-1"]
    assert order("document_item") == ["FA-2", "FA-1", "FA-4", "FA-3"]
    assert order("document_item", "desc") == ["FA-3", "FA-4", "FA-1", "FA-2"]
    assert order("amount") == ["FA-2", "FA-3", "FA-1", "FA-4"]
    assert order("subproject") == ["FA-2", "FA-1", "FA-4", "FA-3"]
    # The reasons "a" and "b" first; the lines without one are tied, in no order the contract fixes.
    assert order("excluded_reason")[:2] == ["FA-1", "FA-4"]
    assert order("excluded_reason", "desc")[2:] == ["FA-4", "FA-1"]
    # The excluded lines before the tracked lines in ascending order.
    assert sorted(order("in_tracked_scope")[:2]) == ["FA-1", "FA-4"]
    assert sorted(order("in_tracked_scope", "desc")[:2]) == ["FA-2", "FA-3"]
    # A column kept: compared as text by code point ("Zeta" before "Zéphyr"), a line without it
    # after.
    assert order("passthrough.Fournisseur") == ["FA-2", "FA-4", "FA-1", "FA-3"]
    assert order("passthrough.Fournisseur", "desc") == ["FA-3", "FA-1", "FA-4", "FA-2"]
    assert sorted(order("passthrough.Absente")) == ["FA-1", "FA-2", "FA-3", "FA-4"]


@pytest.mark.requirement("WF-IHM-0060-A")
def test_a_sort_by_a_column_that_is_none_is_refused(api: ContractClient, stage: Scene) -> None:
    answer = api.get(path(stage), headers=stage.manager.headers, params={"sort_by": "colour"})
    assert answer.status_code in {400, 422}, answer.text


@pytest.mark.requirement("WF-CYC-0110-A")
@pytest.mark.parametrize("state", ["completed", "lost", "abandoned"])
def test_the_lines_are_read_on_a_terminal_project(
    api: ContractClient, stage: Scene, state: str
) -> None:
    three_lines(stage)
    put_in_state(stage.owner, stage.project["project_id"], state)
    assert read(api, stage)["meta"]["total"] == 3


@pytest.mark.requirement("WF-ADM-0110-A")
def test_the_lines_are_read_by_a_reader_and_unknown_to_an_outsider(
    api: ContractClient, stage: Scene
) -> None:
    three_lines(stage)
    seen = api.get(path(stage), headers=stage.reader.headers)
    assert seen.status_code == 200, seen.text
    unseen = api.get(path(stage), headers=stage.outsider.headers)
    assert refusal(unseen)[:2] == (404, "NOT_FOUND")
    unknown = api.get(f"{PROJECTS}/{uuid4()}/actual-costs", headers=stage.manager.headers)
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
