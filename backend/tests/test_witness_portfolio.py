# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the portfolio, loaded with the witness (EP-11, US-2770/L2; WF-QUA-0040).

``load-witness`` writes, after the march of the events of PRJ-001 — the risks and the amendments of
EP-08 among them —, the ten projects ``fixtures/witness/portfolio/projects`` describes, by the
interfaces of the modules, at the instants the description dates, under the identifiers it names.
What the platform holds of them is compared with their description, here; the readings of the eight
views, with the expected ones, in ``test_witness_portfolio_readings``.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from installed_reference import install
from sqlalchemy import func, select
from support import WITNESS
from test_witness import load, wipe

from waterfall.api.contract.models import Calendar
from waterfall.core.costs.tables import CostImport, CostLine
from waterfall.core.planning.tables import Node
from waterfall.core.planning.tables import Task as TaskFacet
from waterfall.core.projects.tables import Contributor, Project, ProjectStateTransition
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.tables import Risk, RiskReview
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError
from waterfall.witness import portfolio, portfolio_slice
from waterfall.witness.description import Witness
from waterfall.witness.portfolio_slice import Project as Described

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine
    from support import Logs

    from waterfall.platform.database import Database

SLICE = WITNESS.parent / "witness" / "portfolio"
PRJ_001 = UUID("01926f3a-7c00-7000-8000-000000000001")
PRJ_002 = UUID("01926f3a-7c00-7000-8000-000000000002")
PROJECT_MANAGER = UUID("01926f3a-7c00-7000-8000-000000000301")
REQUIREMENT = "WF-QUA-0040-A"


def described() -> list[Described]:
    """Read the projects of the slice as the loader does."""
    return portfolio_slice.read(Witness(WITNESS, Act(None, utc_now())))


def counts(database: Database) -> dict[str, int]:
    """Count the rows the slice writes, the journal included."""
    models = (Project, Revision, Node, Risk, CostImport, CostLine, ProjectStateTransition)
    with database.transaction() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
            for model in (*models, Contributor, UserAccount, AuditEntry)
        }


def identifying(database: Database) -> dict[str, list[tuple[object, ...]]]:
    """Give what identifies the objects of the slice: identifiers, codes, labels, instants."""
    with database.transaction() as session:
        return {
            "project": [
                tuple(row)
                for row in session.execute(
                    select(Project.id, Project.code, Project.label, Project.state)
                    .where(Project.code.like("PRJ-3%"))
                    .order_by(Project.id)
                )
            ],
            "revision": [
                tuple(row)
                for row in session.execute(
                    select(
                        Revision.id,
                        Revision.project_id,
                        Revision.status,
                        Revision.version_name,
                        Revision.marked_at,
                    )
                    .join(Project, Project.id == Revision.project_id)
                    .where(Project.code.like("PRJ-3%"))
                    .order_by(Revision.id)
                )
            ],
            "node": [
                tuple(row)
                for row in session.execute(
                    select(Node.id, Node.lineage_id, Node.kind, Node.revision_id)
                    .join(Project, Project.id == Node.project_id)
                    .where(Project.code.like("PRJ-3%"))
                    .order_by(Node.id)
                )
            ],
            "risk": [tuple(row) for row in session.execute(select(Risk.id).order_by(Risk.id))],
            "cost_line": [
                tuple(row)
                for row in session.execute(
                    select(CostLine.id, CostLine.document_number, CostLine.amount).order_by(
                        CostLine.id
                    )
                )
            ],
            "transition": [
                tuple(row)
                for row in session.execute(
                    select(
                        ProjectStateTransition.project_id,
                        ProjectStateTransition.to_state,
                        ProjectStateTransition.occurred_at,
                    ).order_by(
                        ProjectStateTransition.project_id, ProjectStateTransition.occurred_at
                    )
                )
            ],
        }


@pytest.mark.requirement(REQUIREMENT)
def test_load_witness_loads_on_a_new_platform_the_slice_beside_prj_001_and_prj_002(
    witness: Database,
) -> None:
    # Écart de WF-QUA-0040-A, « L'engendrement du jeu aboutit sur une plateforme neuve » : the
    # volumes of §4.6.2 are EP-13's; here, the ten projects of the slice beside the two of the
    # witness, each in the state its last transition gives.
    slice_ = described()
    assert len(slice_) == 10
    with witness.transaction() as session:
        held = {row.id: row for row in session.scalars(select(Project))}
    assert set(held) == {PRJ_001, PRJ_002, *(each.project_id for each in slice_)}
    for each in slice_:
        assert held[each.project_id].code == each.code
        assert held[each.project_id].state == each.transitions[-1].to_state.value
    assert {each.transitions[-1].to_state.value for each in slice_} == {
        "in_progress",
        "pricing",
        "completed",
        "lost",
        "abandoned",
    }


@pytest.mark.requirement(REQUIREMENT)
def test_the_slice_is_written_at_the_instants_and_under_the_identifiers_of_its_description(
    witness: Database,
) -> None:
    # « les identifiants de la tranche sont imposés par le témoin » : the projects, the revisions
    # (opened, marked, as the description dates them), the risks, the actual costs, the transitions
    # and — in the last revision of each project — the tasks and the lines.
    with witness.transaction() as session:
        for each in described():
            code = each.code
            assert {row.id: row for row in session.scalars(select(Project))}[each.project_id]
            revisions = {
                row.id: row
                for row in session.scalars(
                    select(Revision).where(Revision.project_id == each.project_id)
                )
            }
            # An abandoned revision is deleted with its rows; the others are those described.
            kept = [row for row in each.revisions if row.abandoned_at is None]
            assert set(revisions) == {row.revision_id for row in kept}, code
            for row in kept:
                assert revisions[row.revision_id].marked_at == row.marked_at, code
                assert revisions[row.revision_id].created_at == row.opened_at, code
                if row.mark is not None:
                    assert revisions[row.revision_id].version_name == row.mark.version_name
            transitions = [
                (found.from_state, found.to_state, found.occurred_at, found.reason)
                for found in session.scalars(
                    select(ProjectStateTransition)
                    .where(ProjectStateTransition.project_id == each.project_id)
                    .order_by(ProjectStateTransition.occurred_at)
                )
            ]
            assert transitions == each.moves(), code
            assert (
                session.scalar(select(Project.created_at).where(Project.id == each.project_id))
                == each.created_at
            ), code
            held = session.scalars(select(Risk).where(Risk.project_id == each.project_id))
            risks = {row.id: row.created_at for row in held}
            assert risks == {row.risk_id: row.declared_at for row in each.risks}, code
            reviewed = session.execute(
                select(RiskReview.risk_id, RiskReview.reviewed_on).where(
                    RiskReview.project_id == each.project_id
                )
            )
            # A risk is declared with a first review; the ones the description adds follow it.
            dated = sorted((row.risk_id, row.reviewed_on) for row in reviewed)
            later = sorted(
                (row.risk_id, found.at.date()) for row in each.risks for found in row.reviews
            )
            assert set(later) <= set(dated), code
            lines = set(
                session.scalars(select(CostLine.id).where(CostLine.project_id == each.project_id))
            )
            expected = {line.cost_line_id.root for row in each.imports for line in row.lines}
            assert lines == expected, code
            amounts = {
                row.id: row.amount
                for row in session.scalars(
                    select(CostLine).where(CostLine.project_id == each.project_id)
                )
            }
            brought = {
                line.cost_line_id.root: Decimal(line.amount.root)
                for row in each.imports
                for line in row.lines
            }
            assert amounts == brought, code
            imports = {
                row.id: row.imported_at
                for row in session.scalars(
                    select(CostImport).where(CostImport.project_id == each.project_id)
                )
            }
            assert imports == {row.cost_import_id: row.imported_at for row in each.imports}, code
            if not kept:
                continue
            nodes = set(
                session.scalars(
                    select(Node.id).where(
                        Node.project_id == each.project_id, Node.revision_id == kept[-1].revision_id
                    )
                )
            )
            assert {row.node_id for row in (*each.tasks, *each.lines)} <= nodes, code


@pytest.mark.requirement(REQUIREMENT)
def test_the_duration_of_a_manual_task_has_no_calendar_exception_to_count() -> None:
    # WF-REF-0110: a calendar is a label and seven numbers of hours, « ni jours fériés ni temps
    # partiels »; ``_working_days`` counts the days of the week alone. The day the calendar of the
    # contract gains an exception, this test fails and the count follows it.
    assert set(Calendar.model_fields) == {
        "calendar_id",
        "label",
        "weekly_hours",
        "is_default",
        "is_active",
        "audit",
        "lock_version",
        "available_commands",
    }


@pytest.mark.requirement(REQUIREMENT)
def test_a_second_loading_of_the_slice_finds_it_there_and_writes_nothing(
    witness: Database, service_database_url: str, logs: Logs
) -> None:
    # « les identifiants de la tranche sont imposés par le témoin ; un second chargement ne change
    # rien » : the platform holds the slice, the command succeeds and says so.
    before, identified = counts(witness), identifying(witness)
    logs.clear()
    assert load(service_database_url) == 0
    assert [record["event"] for record in logs.records if "witness." in record["event"]] == [
        "witness.already_loaded"
    ]
    assert counts(witness) == before
    assert identifying(witness) == identified
    assert before["project"] == 12


@pytest.mark.requirement(REQUIREMENT)
def test_two_loadings_of_the_witness_give_the_slice_identical_identifying_data(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. » : the
    # platform emptied and loaded again holds the same identifiers, codes, labels and instants — the
    # ones the loader draws in order included.
    first = identifying(witness)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    assert identifying(witness) == first
    assert len(first["project"]) == 10
    assert first["node"]
    assert first["cost_line"]


@pytest.mark.requirement(REQUIREMENT)
def test_a_platform_that_holds_part_of_the_slice_stops_the_command_and_writes_nothing(
    witness: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A platform half loaded — nine projects of the description held, a tenth under an identifier
    # no platform holds: a collision (409 ``ALREADY_EXISTS``), before the slice writes anything.
    found = described()
    first = found[0].model_copy(update={"project_id": UUID(int=1)})

    def altered(_: Witness) -> list[Described]:
        return [first, *found[1:]]

    monkeypatch.setattr(portfolio_slice, "read", altered)
    before = counts(witness)
    with witness.transaction() as session, pytest.raises(ConflictError) as refused:
        portfolio.load(session, Witness(WITNESS, Act(None, utc_now())))
    assert refused.value.code == "ALREADY_EXISTS"
    assert counts(witness) == before


@pytest.mark.requirement(REQUIREMENT)
def test_no_address_and_no_label_of_a_real_project_is_written_by_the_slice(
    witness: Database,
) -> None:
    # « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » : the projects of
    # the slice bear the labels the description generated, and the only account that contributes to
    # them is the project manager of the witness, under the domain ``waterfall.test``.
    slice_ = described()
    with witness.transaction() as session:
        labels = {
            row.id: row.label
            for row in session.scalars(select(Project))
            if row.code is not None and row.code.startswith("PRJ-3")
        }
        assert labels == {each.project_id: each.project.label for each in slice_}
        assert all(" — Valence" in label for label in labels.values())
        accounts = [
            (row.email, row.id) for row in session.scalars(select(UserAccount)) if row.email
        ]
        assert accounts
        assert all(email.endswith("@waterfall.test") for email, _ in accounts)
        contributors = set(
            session.execute(
                select(Contributor.project_id, Contributor.user_account_id, Contributor.kind).where(
                    Contributor.project_id.in_(labels)
                )
            ).all()
        )
    assert contributors == {(each, PROJECT_MANAGER, "project_manager") for each in labels}


@pytest.mark.story("US-2770")
def test_the_states_of_the_tasks_are_laid_as_they_stand_on_the_day_of_each_marking(
    witness: Database,
) -> None:
    # The tasks of PRJ-301 are not started in the offer; the study is completed in the revision
    # marked on 10 November 2025, the fabrication in the one marked on 4 May 2026; the frame of
    # PRJ-304, started past its finish, stays started.
    by_code = {each.code: each for each in described()}

    def states(code: str, number: int) -> dict[str, str]:
        found = by_code[code]
        with witness.transaction() as session:
            rows = session.execute(
                select(TaskFacet.label, TaskFacet.progress)
                .join(
                    Node, (Node.project_id == TaskFacet.project_id) & (Node.id == TaskFacet.node_id)
                )
                .where(Node.revision_id == found.revisions[number - 1].revision_id)
            ).all()
        planned = {each.node.task.label for each in found.tasks if each.node.task is not None}
        return {row[0]: row[1] for row in rows if row[0] in planned}

    assert set(states("PRJ-301", 1).values()) == {"not_started"}
    assert states("PRJ-301", 2) == {
        "Études": "completed",
        "Fabrication": "not_started",
        "Mise en service": "not_started",
    }
    assert states("PRJ-301", 3) == {
        "Études": "completed",
        "Fabrication": "completed",
        "Mise en service": "not_started",
    }
    assert states("PRJ-304", 2)["Charpente"] == "started"


@pytest.mark.story("US-2770")
def test_the_slice_is_read_beside_the_description_and_a_description_without_it_stops_the_load(
    tmp_path: Path,
) -> None:
    # The slice lives beside the examples, under ``witness/portfolio/projects``; a directory of the
    # description with none beside it is no witness.
    directory = tmp_path / "api"
    directory.mkdir()
    witness = Witness(directory, Act(None, datetime(2026, 6, 3, tzinfo=UTC)))
    assert portfolio_slice.directory(witness) == tmp_path / "witness" / "portfolio" / "projects"
    with pytest.raises(ValueError, match="holds no project"):
        portfolio_slice.read(witness)


@pytest.mark.story("US-2770")
def test_a_file_of_the_slice_that_strays_from_its_model_stops_the_load() -> None:
    # A key no model holds, a task of a revision the project does not have: the command stops
    # before anything is written.
    document = json.loads((SLICE / "projects" / "PRJ-301.json").read_text(encoding="utf-8"))
    value = cast("dict[str, Any]", document["value"])
    with pytest.raises(ValueError, match="beyond"):
        Described.model_validate({**value, "beyond": True})
    with pytest.raises(ValueError, match="names a revision"):
        Described.model_validate(value).revision_number(UUID(int=1))
