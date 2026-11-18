# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators a revision keeps at its marking (WF-DAT-0040, WF-IND-0010; US-1670/L1).

Laid by US-1660/L1, the socle of EP-10, so that no two stories create the same file;
US-1670/L1 writes its tests here (EP-10, "Les tests du back"). A project priced task by task, a
subproject among its lines, moved In progress, its review marked by the transaction of the worker
at the instant of the clock: the documents kept for each kind and each scope, their context, their
zones; each document held to the model of the contract of its kind (#3551); the offer marked in
pricing, which keeps its estimate alone; the actual cost kept, which a line dated after the
marking does not enter, nor a line imported after it, and which an extraction applied since —
a line added, a line updated — leaves as it was. The readings of a marked revision are
US-1670/L2's: the documents are read here as the module keeps them (``stored_document``).
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import declare, extraction, line, opening
from costs_support import load_import
from curves_support import COST_CURVE, EARNED_VALUE_CURVES, curve, curve_answer, series
from day_indicators_support import (
    Planned,
    completed,
    dated,
    indicators,
    priced,
    subproject,
)
from fastapi.testclient import TestClient
from imports_trial import apply, import_worker, read, run
from indicators_support import clock_setter
from jsonschema_path import SchemaPath
from nodes_support import opened, refusal
from openapi_core.validation.schemas import oas31_schema_validators_factory
from planning_support import DAY
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import CONTRACT, ContractClient, walk

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.interface import PROJECT, UNASSIGNED
from waterfall.core.costs.tables import CostLine
from waterfall.core.indicators.interface import stored_document
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import current_day
from waterfall.core.revisions.interface import mark_revision
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.installation import TIME_ZONE
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from day_indicators_support import Priced
    from indicators_support import Clock
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

ONE_DAY = timedelta(days=1)
# The code the project receives when it moves In progress (``remaining_support.in_progress``): an
# element of an extraction that names it alone imputes its line to no subproject.
ELEMENT = "PRJ-1580"
# The schemas of the indicators in the contract.
INDICATORS = SchemaPath.from_file_path(
    str(CONTRACT.parent / "components" / "schemas" / "indicators.yaml")
)
MODELS = {
    "estimate": "EstimateIndicators",
    "remaining": "RemainingIndicators",
    "project": "ProjectIndicators",
    "cost_curve": "CurveSeries",
    "cost_curve_payment_delays": "CurveSeries",
    "earned_value_curves": "CurveSeries",
}
CURVES = ("cost_curve", "cost_curve_payment_delays", "earned_value_curves")
FORBIDDEN: tuple[int, str, dict[str, Any]] = (409, "STATE_FORBIDS_OPERATION", {})


@pytest.fixture
def import_services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API on the database, the queue and the bucket of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def api(contract: OpenAPI, import_services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(import_services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, the mapping of the extractions declared, and a project."""
    made = make_scene(api, owner, database, realm)
    declare(database)
    return made


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the indicators are computed on."""
    return clock_setter(monkeypatch)


@pytest.fixture
def lot(api: ContractClient, stage: Scene) -> str:
    """Give a subproject of the project, which the line of the wiring bears."""
    return subproject(api, stage, "10001", "Lot 10001")


@pytest.fixture
def project(api: ContractClient, stage: Scene, lot: str) -> Priced:
    """Give a project of budget 1 000 In progress, the studies, 400, completed on ``DAY``.

    The wiring, 600, is borne by the subproject; the studies by none.
    """
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600", lot)])
    completed(found.tree, "Études", DAY)
    return found


def marked_now(stage: Scene, clock: Clock, revision: dict[str, Any]) -> datetime:
    """Mark a revision by the transaction of the worker, at the clock set tomorrow; give it.

    The day after the real one: the reference was marked at the instant it was written. The
    manager is the requester.
    """
    at = clock(utc_now().date() + ONE_DAY)
    marked_at(stage, revision, at, "Revue")
    return at


def marked_at(stage: Scene, revision: dict[str, Any], at: datetime, version_name: str) -> None:
    """Mark a revision by the transaction of the worker at an instant, the manager the requester."""
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        act = Act(stage.manager.user_id, at)
        mark_revision(session, UUID(revision["revision_id"]), version_name, None, act)


def kept(database: Database, revision_id: str) -> dict[tuple[str, str], Any]:
    """Read the rows a revision kept, by kind and scope: the document, the instant, the author."""
    with database.transaction() as session:
        rows = session.execute(
            select(
                RevisionIndicator.kind,
                RevisionIndicator.scope,
                RevisionIndicator.document,
                RevisionIndicator.computed_at,
                RevisionIndicator.created_at,
                RevisionIndicator.created_by,
            ).where(RevisionIndicator.revision_id == UUID(revision_id))
        ).all()
    return {(row.kind, row.scope): tuple(row[2:]) for row in rows}


def document(database: Database, revision_id: str, kind: Any, scope: Any) -> Any:
    """Read a document a revision kept, as the module gives it."""
    with database.transaction() as session:
        return stored_document(session, UUID(revision_id), kind, scope)


def zulu(at: datetime) -> str:
    """Give an instant as the contract writes it."""
    return at.isoformat().replace("+00:00", "Z")


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_marking_keeps_the_estimate_the_remaining_and_the_project_of_each_scope_at_its_instant(
    stage: Scene, clock: Clock, project: Priced, lot: str
) -> None:
    # The table keeps, for the marked revision, the estimate of the project, of the lines out of
    # any subproject and of the subproject, its remaining once, and, the project In progress, its
    # indicators on each scope: each at the instant of the marking, its requester the author, the
    # context the revision marked and stored, every zone null.
    revision_id = project.tree.revision["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    at = marked_now(stage, clock, project.tree.revision)
    rows = kept(stage.database, revision_id)
    scopes = (PROJECT, UNASSIGNED, lot)
    assert set(rows) == {
        *(("estimate", scope) for scope in scopes),
        ("remaining", PROJECT),
        *(("project", scope) for scope in scopes),
        *((name, scope) for name in CURVES for scope in scopes),
    }
    with stage.database.transaction() as session:
        marked_at = session.scalar(select(Revision.marked_at).where(Revision.id == revision_id))
    assert marked_at == at
    for (_, scope), (held, computed_at, created_at, created_by) in rows.items():
        assert (computed_at, created_at, created_by) == (at, at, stage.manager.user_id)
        assert held["context"] == {
            "revision_id": revision_id,
            "revision_status": "marked",
            "computed_at": zulu(at),
            "scope": scope,
            "is_stored": True,
        }
    whole = rows["project", PROJECT][0]
    assert (whole["cost_index"]["zone"], whole["schedule_index"]["zone"]) == (None, None)
    assert (whole["reference_budget"], whole["earned_value"], whole["actual_cost"]) == (
        "1000.00",
        "400.00",
        "500.00",
    )
    assert rows["project", lot][0]["reference_budget"] == "600.00"
    assert rows["estimate", lot][0]["total"]["value"] == "600.00"


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.parametrize("kind", sorted(MODELS))
def test_each_document_kept_is_the_answer_of_the_contract_of_its_kind(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced, kind: str
) -> None:
    # #3551: a document is a JSON object the core writes without the models of the contract; each
    # kept is held to the schema of its kind, every property it requires and none it does not
    # declare, as an answer of the service would be.
    marked_now(stage, clock, project.tree.revision)
    rows = kept(stage.database, project.tree.revision["revision_id"])
    schema = INDICATORS / MODELS[kind]
    validator = oas31_schema_validators_factory.create(api.contract.spec, schema)
    held = [each for (of, _), (each, *_) in rows.items() if of == kind]
    assert held
    for each in held:
        validator.validate(each)
        assert list(walk([schema], each, "")) == []


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-IND-0010-A")
def test_an_offer_marked_in_pricing_keeps_the_total_of_its_estimate_and_no_project_indicator(
    stage: Scene, project: Priced, lot: str
) -> None:
    # « Le marquage d'une offre, sur un projet en chiffrage, aboutit et conserve le total du devis
    # sans aucun indicateur projet. » — « Sur un projet à l'état Chiffrage, aucun indicateur projet
    # n'est proposé. » The reference was marked in pricing, the project moved In progress since:
    # its estimate by scope and its remaining, and still no indicator of the project.
    reference = project.review.reference["revision_id"]
    rows = kept(stage.database, reference)
    assert set(rows) == {
        ("estimate", PROJECT),
        ("estimate", UNASSIGNED),
        ("estimate", lot),
        ("remaining", PROJECT),
    }
    assert rows["estimate", PROJECT][0]["total"]["value"] == "1000.00"
    assert document(stage.database, reference, "project", PROJECT) is None


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_line_of_cost_dated_after_the_marking_does_not_enter_its_actual_cost(
    stage: Scene, clock: Clock, project: Priced
) -> None:
    # « Une ligne de coût datée après la date de marquage n'entre pas dans le coût réel de cette
    # révision. » Two lines known at the marking, one dated the day after it: it counts nought.
    revision_id = project.tree.revision["revision_id"]
    tomorrow = utc_now().date() + ONE_DAY
    lines = [dated("FA-1", None, "500.00", DAY), dated("FA-2", None, "300.00", tomorrow + ONE_DAY)]
    load_import(stage, UUID(stage.project["project_id"]), lines)
    marked_now(stage, clock, project.tree.revision)
    held = document(stage.database, revision_id, "project", PROJECT)
    assert held is not None
    assert held["actual_cost"] == "500.00"
    assert held["cost_index"]["value"]["value"] == "0.8"


def imported(api: ContractClient, stage: Scene, worker: Worker, rows: list[Any]) -> None:
    """Open, analyse and apply an extraction of the lines given, as the manager does."""
    opened = opening(api, stage, extraction(rows))
    assert opened.status_code == 202, opened.text
    run(worker)
    import_id = opened.json()["import_id"]
    assert read(api, stage, import_id)["status"] == "analysed"
    applied = apply(api, stage, import_id)
    assert applied.status_code == 202, applied.text
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-IND-0010-A")
def test_the_indicators_kept_are_unchanged_by_an_import_applied_after_the_marking(
    api: ContractClient, stage: Scene, worker: Worker, clock: Clock, project: Priced
) -> None:
    # « Les indicateurs conservés d'une révision marquée sont identiques avant et après un import
    # de coûts réels postérieur. » — « Les indicateurs d'une révision marquée ne changent pas après
    # son marquage, même après l'import d'une ligne de coût datée avant le marquage, qui n'entre ni
    # dans son coût réel ni dans ses courbes. » An extraction applied after the marking adds a line
    # dated before it and updates the amount of a line known then: every document kept is the same,
    # its actual cost the lines known at the marking as they were; the day reads the import.
    revision_id = project.tree.revision["revision_id"]
    first = line(element=ELEMENT, number="FA-1", on="2026-04-02", amount=500)
    imported(api, stage, worker, [first])
    marked_now(stage, clock, project.tree.revision)
    before = kept(stage.database, revision_id)
    assert before["project", PROJECT][0]["actual_cost"] == "500.00"
    imported(
        api,
        stage,
        worker,
        [
            line(element=ELEMENT, number="FA-1", on="2026-04-02", amount=700),
            line(element=ELEMENT, number="FA-2", on="2026-04-03", amount=250),
        ],
    )
    assert kept(stage.database, revision_id) == before
    assert indicators(api, stage)["actual_cost"] == "950.00"


def read_curves(api: ContractClient, stage: Scene, query: str) -> dict[str, dict[str, Any]]:
    """Read the three kinds of curve of the project of the stage, the query said."""
    separator = "&" if "?" in query else "?"
    return {
        "cost_curve": curve(api, stage, COST_CURVE, query),
        "cost_curve_payment_delays": curve(
            api, stage, COST_CURVE, f"{query}{separator}payment_delays=true"
        ),
        "earned_value_curves": curve(api, stage, EARNED_VALUE_CURVES, query),
    }


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-IND-0100-A")
@pytest.mark.requirement("WF-IND-0110-A")
def test_a_marked_revision_gives_the_curves_its_marking_kept_stored_at_its_instant(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced, lot: str
) -> None:
    # « Les courbes d'une révision marquée sont rendues telles que le marquage les a conservées »,
    # on each scope, the three kinds, by the revision named and by a date, `is_stored` true, the
    # context that of the marking; the two variants of the cost curve are kept.
    revision_id = project.tree.revision["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    at = marked_now(stage, clock, project.tree.revision)
    rows = kept(stage.database, revision_id)
    for scope in (PROJECT, UNASSIGNED, lot):
        by_name = read_curves(api, stage, f"?revision_id={revision_id}&scope={scope}")
        for name, body in by_name.items():
            assert body == rows[name, scope][0]
            assert body["context"]["is_stored"] is True
            assert body["context"]["computed_at"] == zulu(at)
        as_of = current_day(at).isoformat()
        assert read_curves(api, stage, f"?as_of={as_of}&scope={scope}") == by_name
    whole = read_curves(api, stage, f"?revision_id={revision_id}")
    assert whole["cost_curve"]["payment_delays"] is False
    assert whole["cost_curve_payment_delays"]["payment_delays"] is True
    assert whole["cost_curve_payment_delays"]["cash_out_by_month"]
    assert series(whole["cost_curve"], "actual_cost")[-1][1] == "500.00"
    assert series(whole["earned_value_curves"], "earned_value")[-1][1] == "400.00"


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-IND-0010-A")
def test_the_kept_actual_cost_curve_is_the_same_after_an_exclusion_and_after_an_import(
    api: ContractClient, stage: Scene, worker: Worker, clock: Clock, project: Priced
) -> None:
    # « La courbe de coût réel conservée est identique avant et après l'exclusion d'une ligne connue
    # au marquage, et avant et après un import postérieur » : the curves read are those of the
    # marking, a line excluded, a line updated and a line added since changing nothing, while the
    # day reads them.
    revision_id = project.tree.revision["revision_id"]
    imported(
        api,
        stage,
        worker,
        [
            line(element=ELEMENT, number="FA-1", on="2026-04-02", amount=500),
            line(element=ELEMENT, number="FA-2", on="2026-04-03", amount=250),
        ],
    )
    marked_now(stage, clock, project.tree.revision)
    query = f"?revision_id={revision_id}"
    before = read_curves(api, stage, query)
    assert series(before["cost_curve"], "actual_cost")[-1][1] == "750.00"
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostLine)
            .where(CostLine.document_number == "FA-2")
            .values(is_in_tracked_scope=False, excluded_reason="Hors contrat")
        )
    assert read_curves(api, stage, query) == before
    imported(
        api,
        stage,
        worker,
        [
            line(element=ELEMENT, number="FA-1", on="2026-04-02", amount=700),
            line(element=ELEMENT, number="FA-3", on="2026-04-04", amount=90),
        ],
    )
    assert read_curves(api, stage, query) == before
    assert series(curve(api, stage, COST_CURVE), "actual_cost")[-1][1] != "750.00"


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-IND-0100-A")
def test_a_revision_marked_before_in_progress_or_a_date_before_any_marking_is_refused(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # The 409 `STATE_FORBIDS_OPERATION`, without a state, when no document `project` was kept: the
    # reference, marked in pricing, keeps the estimate alone; a date before the marking of the
    # review has no revision that kept the indicators.
    reference = project.review.reference["revision_id"]
    day = current_day(marked_now(stage, clock, project.tree.revision))
    for name in (COST_CURVE, EARNED_VALUE_CURVES):
        named = curve_answer(api, stage, name, f"?revision_id={reference}")
        assert refusal(named) == FORBIDDEN
        early = curve_answer(api, stage, name, f"?as_of={(day - 2 * ONE_DAY).isoformat()}")
        assert refusal(early) == FORBIDDEN
    kept_day = curve_answer(api, stage, COST_CURVE, f"?as_of={day.isoformat()}")
    assert kept_day.status_code == 200


def curve_of_date(api: ContractClient, stage: Scene, day: Any) -> Any:
    """Read the cost curve of the project of the stage as of a day."""
    return curve_answer(api, stage, COST_CURVE, f"?as_of={day.isoformat()}")


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_date_reads_the_last_revision_marked_on_or_before_it_among_two_markings_in_progress(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # « as_of → la dernière révision marquée dont marked_at ≤ la fin de la date, parmi celles qui
    # ont un document project » : two revisions marked In progress, two days apart; a date between
    # reads the first, the day of the second and after it reads the second.
    first = project.tree.revision
    at = marked_now(stage, clock, first)
    later = at + 2 * ONE_DAY
    second = opened(api, stage)
    marked_at(stage, second, later, "Revue 2")
    for day, expected in (
        (current_day(at), first),
        (current_day(at + ONE_DAY), first),
        (current_day(later), second),
        (current_day(later + ONE_DAY), second),
    ):
        answer = curve_of_date(api, stage, day)
        assert answer.status_code == 200, answer.text
        assert answer.json()["context"]["revision_id"] == expected["revision_id"]
    assert curve_of_date(api, stage, current_day(at - ONE_DAY)).status_code == 409


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_day_of_a_marking_is_the_day_of_the_time_zone_of_the_installation(
    api: ContractClient, stage: Scene, project: Priced
) -> None:
    # A marking at 23:30 universal time falls, in Paris, on the next day: the date asked is read
    # in the time zone of the installation (`current_day`), as the marking of the day is.
    TIME_ZONE.read_from(lambda: "Europe/Paris")
    at = datetime.combine(utc_now().date() + ONE_DAY, datetime.min.time(), UTC).replace(
        hour=23, minute=30
    )
    marked_at(stage, project.tree.revision, at, "Revue")
    assert current_day(at) == at.date() + ONE_DAY
    assert refusal(curve_of_date(api, stage, at.date())) == FORBIDDEN
    assert curve_of_date(api, stage, current_day(at)).status_code == 200
