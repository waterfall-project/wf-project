# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reprise of the codes of the subprojects: migrations 0046 and 0047 (US-3270/L2, #3966)."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from costs_support import insert_cost_line, report_row, write_import
from project_rows import STAMP, insert_project
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from waterfall.core.costs.interface import costs_stamp
from waterfall.core.costs.tables import CostLine
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.projects.tables import Project, Subproject
from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection

    from waterfall.core.costs.interface import CostsStamp

CODE = "A.ABC.26001"
OTHER = "PRJ-002"


def subproject(connection: Connection, project_id: UUID, code: str) -> UUID:
    """Write a subproject of a project around the service; give it."""
    subproject_id = uuid4()
    connection.execute(
        insert(Subproject).values(
            id=subproject_id, project_id=project_id, code=code, label=f"Lot {code}", **STAMP
        )
    )
    return subproject_id


def codes(engine: Engine) -> list[tuple[str, int]]:
    """Give the code and the counter of each subproject, by code."""
    with engine.connect() as connection:
        rows = connection.execute(
            select(Subproject.code, Subproject.lock_version).order_by(Subproject.code)
        )
        return [(code, version) for code, version in rows]


def lines(engine: Engine) -> list[tuple[str, UUID | None, str | None]]:
    """Give each line of cost by its document, with its subproject and its code."""
    with engine.connect() as connection:
        rows = connection.execute(
            select(
                CostLine.document_number, CostLine.subproject_id, CostLine.subproject_code
            ).order_by(CostLine.document_number)
        )
        return [(number, imputed, code) for number, imputed, code in rows]


def stamp(engine: Engine, project_id: UUID) -> CostsStamp:
    """Read what the key of the cache of the indicators reads of the lines of a project."""
    with Session(engine) as session:
        return costs_stamp(session, project_id)


def reasons(engine: Engine, report_id: UUID) -> list[str]:
    """Give the reasons to confirm the report of an import keeps."""
    with engine.connect() as connection:
        report = connection.scalar(select(ImportReport.report).where(ImportReport.id == report_id))
    assert isinstance(report, dict)
    return list(report["requires_confirmation_reasons"])


@pytest.mark.story("US-3270")
def test_the_codes_are_prefixed_and_the_lines_that_wait_for_a_subproject_are_deleted(
    empty_engine: Engine,
) -> None:
    # Propre à l'US : la reprise. « Une migration préfixe les codes de sous-projets déjà saisis du
    # code de leur projet et d'une barre oblique : chaque ligne de coût imputée à un sous-projet le
    # reste […]. Les lignes de coût importées sous un code de sous-projet inconnu, qui attendaient
    # sa création, sont supprimées par la migration », leur nombre journalisé par projet. L'unicité
    # du code dans le projet tient ; un projet sans code garde les codes de ses sous-projets.
    upgrade(empty_engine, "0045")
    project, other, uncoded = uuid4(), uuid4(), uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code=CODE))
        connection.execute(insert_project(id=other, code=OTHER))
        connection.execute(insert_project(id=uncoded))
        cabling = subproject(connection, project, "10001")
        subproject(connection, project, "10002")
        subproject(connection, other, "10001")
        subproject(connection, uncoded, "SP-1")
        imported = write_import(connection, project)
        insert_cost_line(
            connection,
            imported,
            document_number="FA-1",
            subproject_id=cabling,
            subproject_code="10001",
            lock_version=3,
        )
        insert_cost_line(connection, imported, document_number="FA-2", lock_version=2)
        insert_cost_line(
            connection, imported, document_number="FA-3", subproject_code="99999", lock_version=1
        )
        insert_cost_line(connection, imported, document_number="FA-4", subproject_code="99998")
        elsewhere = write_import(connection, other)
        insert_cost_line(connection, elsewhere, document_number="FB-1", subproject_code="SP-X")
        waiting = report_row(project, status="applied")
        asked = ["lines_outside_project", "unknown_subproject"]
        waiting["report"] = {"requires_confirmation_reasons": asked}
        connection.execute(insert(ImportReport).values(**waiting))
    before = stamp(empty_engine, project)
    upgrade(empty_engine, "0046")
    with capture_logs() as records:
        upgrade(empty_engine, "0047")

    assert codes(empty_engine) == [
        (f"{CODE}/10001", 1),
        (f"{CODE}/10002", 1),
        (f"{OTHER}/10001", 1),
        ("SP-1", 0),
    ]
    assert lines(empty_engine) == [
        ("FA-1", cabling, f"{CODE}/10001"),
        ("FA-2", None, None),
    ]
    deleted = [
        (each["project_id"], each["project_code"], each["count"])
        for each in records
        if each["event"] == "cost_lines_waiting_deleted"
    ]
    assert sorted(deleted) == sorted([(str(project), CODE, 2), (str(other), OTHER, 1)])
    [summary] = [each for each in records if each["event"] == "codes_prefixed"]
    assert (summary["projects_with_lines_deleted"], summary["cost_lines_deleted"]) == (2, 3)
    assert reasons(empty_engine, UUID(str(waiting["id"]))) == ["lines_outside_project"]

    # The key of the cache (#3629): the sum of the counters falls back, the number of the lines
    # falls below any the project had since its last import, whose number is unchanged: the key is
    # one the project never had.
    after = stamp(empty_engine, project)
    assert (before.imports, before.lines, before.versions) == (1, 4, 6)
    assert (after.imports, after.lines, after.versions) == (1, 2, 5)
    assert after != before

    # The unique code holds after the prefix: two subprojects of a project never share one.
    with (
        pytest.raises(IntegrityError, match="uq_subproject_project_id"),
        empty_engine.begin() as connection,
    ):
        subproject(connection, project, f"{CODE}/10002")


@pytest.mark.story("US-3270")
def test_the_descent_strips_the_prefix_and_gives_back_no_line_deleted(
    empty_engine: Engine,
) -> None:
    # La descente retire le préfixe et ne rend pas les lignes supprimées ; un code saisi depuis,
    # libre, la fait échouer quand il serait, une fois le préfixe retiré, celui d'un autre.
    upgrade(empty_engine, "0045")
    project = uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code=CODE))
        cabling = subproject(connection, project, "10001")
        imported = write_import(connection, project)
        insert_cost_line(
            connection,
            imported,
            document_number="FA-1",
            subproject_id=cabling,
            subproject_code="10001",
        )
        insert_cost_line(connection, imported, document_number="FA-3", subproject_code="99999")
    upgrade(empty_engine, "0047")
    downgrade(empty_engine, "0045")
    assert codes(empty_engine) == [("10001", 2)]
    assert lines(empty_engine) == [("FA-1", cabling, "10001")]

    upgrade(empty_engine, "0047")
    with empty_engine.begin() as connection:
        subproject(connection, project, "10001")
    with pytest.raises(IntegrityError, match="uq_subproject_project_id"):
        downgrade(empty_engine, "0046")


@pytest.mark.story("US-3270")
def test_the_descent_of_the_schema_fails_while_a_code_holds_what_it_refused(
    empty_engine: Engine,
) -> None:
    # 0046 relâche les codes ; sa descente rend les contraintes d'avant, et échoue tant qu'un code
    # les enfreint — un code de projet à barre oblique —, le schéma restant.
    upgrade(empty_engine, "0046")
    project = uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code="A/B"))
    with pytest.raises(DBAPIError, match="code_without_slash"):
        downgrade(empty_engine, "0045")
    with empty_engine.begin() as connection:
        connection.execute(update(Project).where(Project.id == project).values(code="A-B"))
        assert connection.scalar(select(func.count()).select_from(Project)) == 1
    downgrade(empty_engine, "0045")
