# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reprise of the codes of the subprojects: migrations 0046 and 0047 (US-3270/L2, #3966)."""

import json
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Protocol, cast
from uuid import UUID, uuid4

import pytest
from costs_support import insert_cost_line, report_row, write_import
from project_rows import STAMP, insert_project
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from waterfall.core.costs.analysing import Held, changed, imputed, known_elements
from waterfall.core.costs.extraction import Kept, Reading, read_lines
from waterfall.core.costs.interface import PROJECT, costs_stamp
from waterfall.core.costs.tables import CostLine
from waterfall.core.costs.writing import held_lines
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.indicators.caching import day_key, scope_key
from waterfall.core.indicators.computing import Basis
from waterfall.core.indicators.shaping import Context
from waterfall.core.projects.interface import subproject_ids
from waterfall.core.projects.tables import Project, Subproject
from waterfall.migrations.runner import downgrade, upgrade
from waterfall.platform.cache import PREFIX as CACHE_PREFIX
from waterfall.platform.cache import IndicatorsCache

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection
    from sqlalchemy.orm import InstrumentedAttribute

    from waterfall.core.costs.interface import CostsStamp
    from waterfall.platform.queue import TaskQueue

CODE = "A.ABC.26001"
OTHER = "PRJ-002"
# The validity of an entry of the cache in these tests, in seconds; the instant of the readings.
TTL = 300
NOON = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
# The reading of an extraction: the element, the document, its item, its date, its amount, and one
# column kept.
READING = Reading(
    {"wbs_element": 0, "document_number": 1, "document_item": 2, "document_date": 3, "amount": 4},
    (Kept(5, "Fournisseur"),),
    (),
)


class Deleting(Protocol):
    """What these tests ask of the client of Redis of the cache: the deletion of keys."""

    def delete(self, *names: str) -> int: ...


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


def kept_under(cache: IndicatorsCache, engine: Engine, project_id: UUID) -> str:
    """Keep an entry of the scope of the project under its key of the day, as it reads now; give it.

    The key is read as ``cached_scopes`` reads it, at one instant of one day.
    """
    key = day_key_of(engine, project_id)
    cache.write_many({scope_key(key, PROJECT): json.dumps({"kept": key})})
    return key


def day_key_of(engine: Engine, project_id: UUID) -> str:
    """Read the key of the day of a project, its current revision none, at ``NOON``."""
    revision_id = uuid4()
    basis = Basis(project_id, revision_id, None)
    context = Context(revision_id, "draft", NOON, PROJECT, is_stored=True)
    with Session(engine) as session:
        return day_key(session, basis, context, subproject_ids(session, project_id))


@pytest.mark.story("US-3270")
def test_no_entry_of_the_cache_kept_before_the_reprise_is_served_after_it(
    empty_engine: Engine, queue: TaskQueue
) -> None:
    # « La suppression fait reculer la somme des compteurs que lit la clé du cache des indicateurs
    # (#3629) : le lot dit comment il l'invalide, et l'éprouve. » Une entrée gardée à chaque import
    # n'est plus lue après la reprise : le nombre des lignes y retombe à celui d'avant le dernier
    # import, mais le nombre des imports, qui ne recule jamais, les sépare.
    upgrade(empty_engine, "0045")
    project = uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code=CODE))
        cabling = subproject(connection, project, "10001")
        first = write_import(connection, project)
        insert_cost_line(
            connection,
            first,
            document_number="FA-1",
            subproject_id=cabling,
            subproject_code="10001",
        )
        insert_cost_line(connection, first, document_number="FA-2", subproject_code="99999")
    cache = IndicatorsCache.of(queue, TTL)
    kept: list[str] = []
    try:
        before_last = kept_under(cache, empty_engine, project)
        kept.append(before_last)
        with empty_engine.begin() as connection:
            second = write_import(connection, project)
            insert_cost_line(connection, second, document_number="FA-3")
            insert_cost_line(connection, second, document_number="FA-4", subproject_code="99998")
        last = kept_under(cache, empty_engine, project)
        kept.append(last)
        assert stamp(empty_engine, project).lines == 4

        upgrade(empty_engine, "0047")

        after = day_key_of(empty_engine, project)
        assert (stamp(empty_engine, project).imports, stamp(empty_engine, project).lines) == (2, 2)
        assert after not in {before_last, last}
        served = cache.lookup_many([scope_key(key, PROJECT) for key in (before_last, last, after)])
        assert served == [
            json.dumps({"kept": before_last}),
            json.dumps({"kept": last}),
            None,
        ]
    finally:
        if kept:
            held = cast("Deleting", cache.client)
            held.delete(*(CACHE_PREFIX + scope_key(key, PROJECT) for key in kept))
        cache.close()


@pytest.mark.story("US-3270")
def test_a_line_imputed_is_found_unchanged_by_the_reimport_of_its_extraction(
    empty_engine: Engine,
) -> None:
    # « … chaque ligne de coût imputée à un sous-projet le reste, et le réimport de son extraction
    # l'impute au même. » : l'élément du fichier, le code du projet et celui d'avant joints, est
    # comparé à la ligne reprise, qui ne change en rien — son sous-projet compris.
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
            passthrough={"Fournisseur": "Atelier Durand"},
        )
    upgrade(empty_engine, "0047")

    row = (f"{CODE}/10001", "FA-1", None, date(2026, 4, 2), 1250.0, "Atelier Durand")
    with Session(empty_engine) as session:
        known = known_elements(session, project)
        [line] = read_lines([row], READING, known).lines
        [held] = held_lines(session, project, {"FA-1"}).values()
        assert imputed(line, known) == cabling
        assert changed(Held.of(held), line, imputed(line, known)) == []


@pytest.mark.story("US-3270")
def test_a_code_at_its_bounds_is_prefixed_to_eighty_two_characters(empty_engine: Engine) -> None:
    # « Le code d'un sous-projet à 100 caractères » (conception) : la reprise préfixe un code de 31
    # caractères d'un code de projet de 50 et d'une barre oblique, soit 82 ; la ligne imputée de
    # même.
    upgrade(empty_engine, "0045")
    project, longest, former = uuid4(), "P" * 50, "S" * 31
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code=longest))
        bound = subproject(connection, project, former)
        imported = write_import(connection, project)
        insert_cost_line(
            connection,
            imported,
            document_number="FA-1",
            subproject_id=bound,
            subproject_code=former,
        )
    upgrade(empty_engine, "0047")
    prefixed = f"{longest}/{former}"
    assert len(prefixed) == 82
    assert codes(empty_engine) == [(prefixed, 1)]
    assert lines(empty_engine) == [("FA-1", bound, prefixed)]


@pytest.mark.story("US-3270")
def test_a_line_imputed_whose_code_would_pass_the_bound_once_prefixed_stops_the_reprise(
    empty_engine: Engine,
) -> None:
    # Une ligne imputée porte le code sous lequel elle a été importée, 31 caractères au plus ; une
    # écrite autour du service, de 50, sous un projet de 50, passerait 100 une fois préfixée : la
    # reprise s'arrête en nommant son projet, sans rien écrire ni couper aucun code.
    upgrade(empty_engine, "0045")
    project, longest = uuid4(), "P" * 50
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code=longest))
        cabling = subproject(connection, project, "10001")
        imported = write_import(connection, project)
        insert_cost_line(
            connection,
            imported,
            document_number="FA-1",
            subproject_id=cabling,
            subproject_code="L" * 50,
        )
        insert_cost_line(connection, imported, document_number="FA-2", subproject_code="99999")
    with pytest.raises(RuntimeError, match=f"beyond 100 characters.*{project}"):
        upgrade(empty_engine, "0047")
    assert codes(empty_engine) == [("10001", 0)]
    assert lines(empty_engine) == [("FA-1", cabling, "L" * 50), ("FA-2", None, "99999")]


@pytest.mark.story("US-3270")
def test_a_subproject_whose_code_would_pass_the_bound_once_prefixed_stops_the_reprise(
    empty_engine: Engine,
) -> None:
    # #4891 : un sous-projet écrit depuis 0046, dont le code est libre jusqu'à 100 caractères,
    # sous un projet de 50, passerait 100 une fois préfixé, même sans ligne imputée : la reprise
    # s'arrête en nommant son projet, sans rien écrire ; le projet voisin, dans la borne, n'est pas
    # nommé.
    upgrade(empty_engine, "0046")
    project, fitting, longest = uuid4(), uuid4(), "P" * 50
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code=longest))
        connection.execute(insert_project(id=fitting, code=OTHER))
        subproject(connection, project, "S" * 60)
        subproject(connection, fitting, "S" * 60)
    with pytest.raises(RuntimeError, match=f"beyond 100 characters.*{project}") as caught:
        upgrade(empty_engine, "0047")
    assert str(fitting) not in str(caught.value)
    assert codes(empty_engine) == [("S" * 60, 0), ("S" * 60, 0)]


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


# What the descent of 0046 refuses: the table and the column whose code breaks a check of before,
# the code, the check.
REFUSED_BY_THE_DESCENT = [
    pytest.param(Project, Project.code, "A/B", "code_without_slash", id="slash-in-a-project-code"),
    pytest.param(
        Subproject,
        Subproject.code,
        "x" * 32,
        "ck_subproject_code_length",
        id="subproject-beyond-31",
    ),
    pytest.param(
        Subproject, Subproject.code, "A:B", "ck_subproject_code_form", id="character-a-tab-refuses"
    ),
    pytest.param(
        CostLine,
        CostLine.subproject_code,
        "y" * 51,
        "ck_cost_line_subproject_code_length",
        id="line-beyond-50",
    ),
]


@pytest.mark.story("US-3270")
@pytest.mark.parametrize(("table", "column", "code", "check"), REFUSED_BY_THE_DESCENT)
def test_the_descent_of_the_schema_fails_while_a_code_holds_what_it_refused(
    empty_engine: Engine,
    table: type[Project | Subproject | CostLine],
    column: InstrumentedAttribute[str | None],
    code: str,
    check: str,
) -> None:
    # 0046 relâche les codes ; sa descente rend les contraintes d'avant, et échoue tant qu'un code
    # les enfreint — un code de sous-projet de plus de 31 caractères, un caractère qu'un onglet
    # refuse, une ligne de plus de 50, un code de projet à barre oblique —, le schéma restant.
    upgrade(empty_engine, "0046")
    project = uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project, code=code if table is Project else "PRJ"))
        if table is Subproject:
            subproject(connection, project, code)
        if table is CostLine:
            imported = write_import(connection, project)
            insert_cost_line(connection, imported, document_number="FA-1", subproject_code=code)
    with pytest.raises(DBAPIError, match=check):
        downgrade(empty_engine, "0045")
    with empty_engine.begin() as connection:
        connection.execute(update(table).where(column == code).values({column: "A-B"}))
        assert connection.scalar(select(func.count()).where(column == "A-B")) == 1
    downgrade(empty_engine, "0045")
