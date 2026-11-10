# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imputation of the lines of cost to the subprojects of their project.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1610/L3 writes its tests here ("Les tests du back"): the lines that waited for a code imputed by
the creation of its subproject (``createSubproject``), none by its recoding (``updateSubproject``,
D-10), and a line loaded again with another code imputed again (``load_cost_lines``), on a project
its manager made, its lines loaded through the interface of the actual costs (``costs_support``).
Every answer of the service is checked against the contract.
"""

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import cost, load_import
from project_rows import AT
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene
from sqlalchemy import select, update

from waterfall.core.costs.tables import CostImport, CostLine

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The code of the subproject ten lines wait for, and that of another.
WAITED = "SP-CAB"
OTHER = "SP-AUT"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def project_of(stage: Scene) -> UUID:
    """Give the identifier of the project of the stage."""
    return UUID(stage.project["project_id"])


def subprojects(stage: Scene, *more: str) -> str:
    """Give the path of the subprojects of the project of the stage, or of one of them."""
    return "/".join([f"{PROJECTS}/{stage.project['project_id']}/subprojects", *more])


def made(api: ContractClient, stage: Scene, code: str) -> dict[str, Any]:
    """Create a subproject of the project of the stage, as its manager does; give the answer."""
    answer = api.post(
        subprojects(stage), headers=stage.manager.headers, json={"code": code, "label": code}
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def rows(stage: Scene, project_id: UUID | None = None) -> list[CostLine]:
    """Read the lines of cost of a project, the stage's by default, by document and item."""
    with stage.database.transaction() as session:
        found = session.scalars(
            select(CostLine)
            .where(CostLine.project_id == (project_id or project_of(stage)))
            .order_by(CostLine.document_number, CostLine.document_item)
        ).all()
        session.expunge_all()
        return list(found)


def unassigned(stage: Scene) -> tuple[int, Decimal]:
    """Count the lines of the project of the stage imputed to no subproject, and sum them."""
    alone = [row for row in rows(stage) if row.subproject_id is None]
    return len(alone), sum((row.amount for row in alone), Decimal(0))


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_ten_lines_that_bore_its_code_are_imputed_to_a_subproject_at_its_creation(
    api: ContractClient, stage: Scene
) -> None:
    # « Après création du sous-projet dont dix lignes portaient le code, ces dix lignes lui sont
    # imputées sans réimport, et l'ensemble hors sous-projet diminue d'autant. »
    waiting = [cost(f"FA-2026-{n:04}", WAITED, f"{100 + n}.00") for n in range(10)]
    others = [cost("FA-2026-0900", OTHER, "40.00"), cost("FA-2026-0901", None, "60.00")]
    # Imported by an account that is not the one that creates the subproject.
    importer = stage.reader.user_id
    load_import(stage, project_of(stage), waiting, author=importer)
    load_import(stage, project_of(stage), others, author=importer)
    assert unassigned(stage) == (12, Decimal("1145.00"))

    created = made(api, stage, WAITED)

    # The creation answers what it made: the subproject bears costs, its deletion lacks them.
    assert created["has_actual_costs"] is True
    assert created["available_commands"][1]["missing_conditions"] == [
        "subproject_without_actual_costs"
    ]
    imputed = [row for row in rows(stage) if row.subproject_code == WAITED]
    assert len(imputed) == 10
    assert {row.subproject_id for row in imputed} == {UUID(created["subproject_id"])}
    # The author of the creation is that of the imputation, at its instant; nothing else changes.
    assert {row.updated_by for row in imputed} == {stage.manager.user_id}
    assert all(row.updated_at > AT for row in imputed)
    assert {(row.created_by, row.created_at) for row in imputed} == {(importer, AT)}
    assert unassigned(stage) == (2, Decimal("100.00"))
    untouched = {row.document_number: row for row in rows(stage)}
    assert untouched["FA-2026-0900"].subproject_code == OTHER
    assert (untouched["FA-2026-0901"].subproject_code, untouched["FA-2026-0901"].updated_at) == (
        None,
        AT,
    )


@pytest.mark.requirement("WF-CRE-0020-A")
def test_a_creation_imputes_an_excluded_line_keeping_its_exclusion_not_those_of_another_project(
    api: ContractClient, stage: Scene
) -> None:
    # The lines of another project that bear the same code wait for its own subproject; an
    # excluded line is imputed as a tracked one, and stays excluded (WF-CRE-0030).
    elsewhere = UUID(create(api, stage.manager, label="Autre projet")["project_id"])
    load_import(stage, elsewhere, [cost("X-1", WAITED)])
    load_import(stage, project_of(stage), [cost("X-1", WAITED)])
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostLine)
            .where(CostLine.project_id == project_of(stage))
            .values(is_in_tracked_scope=False, excluded_reason="Hors contrat")
        )

    created = made(api, stage, WAITED)

    [own] = rows(stage)
    assert (own.subproject_id, own.is_in_tracked_scope, own.excluded_reason) == (
        UUID(created["subproject_id"]),
        False,
        "Hors contrat",
    )
    [other] = rows(stage, elsewhere)
    assert (other.subproject_id, other.subproject_code) == (None, WAITED)


@pytest.mark.requirement("WF-CRE-0020-A")
def test_a_creation_does_not_impute_a_line_whose_code_differs_only_by_its_case(
    api: ContractClient, stage: Scene
) -> None:
    # The code of a line is compared as stored, to that of the subproject: no folding of the case.
    load_import(stage, project_of(stage), [cost("FA-1", WAITED.lower())])

    made(api, stage, WAITED)

    [held] = rows(stage)
    assert (held.subproject_id, held.subproject_code) == (None, WAITED.lower())


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_recoding_of_a_subproject_changes_the_imputation_of_no_line(
    api: ContractClient, stage: Scene
) -> None:
    # D-10: the lines imputed stay so by the identifier of their subproject (WF-DAT-0060); those
    # that waited for the new code wait still, until their next import.
    created = made(api, stage, WAITED)
    load_import(
        stage,
        project_of(stage),
        [cost("FA-1", WAITED), cost("FA-2", OTHER)],
    )
    before = {row.document_number: (row.subproject_id, row.updated_at) for row in rows(stage)}
    assert before["FA-1"][0] == UUID(created["subproject_id"])

    answer = api.patch(
        subprojects(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        json={"code": OTHER, "label": "Automatismes", "lock_version": created["lock_version"]},
    )

    assert answer.status_code == 200, answer.text
    assert answer.json()["has_actual_costs"] is True
    after = {row.document_number: (row.subproject_id, row.updated_at) for row in rows(stage)}
    assert after == before
    assert after["FA-2"][0] is None


@pytest.mark.requirement("WF-CRE-0020-A")
def test_a_line_imported_again_with_another_wbs_element_changes_its_imputation(
    api: ContractClient, stage: Scene
) -> None:
    # « Une ligne réimportée avec un autre élément d'OTP change d'imputation. » The line is found by
    # its document and its item: it keeps its identifier and its exclusion, its imputation is
    # computed again from its code — another subproject, a code no subproject bears, none.
    # The loader (`load_cost_lines`) is what is tried here: the phrase of the Vérif is proved at its
    # level, and the real application of an import, that of US-1610/L2 (not merged yet), will be
    # proved by US-1610/L2 (finding #2728).
    cabling, automation = made(api, stage, WAITED), made(api, stage, OTHER)
    project = project_of(stage)
    first = cost("FA-2026-0412", WAITED, "1800.00", item="10")
    load_import(stage, project, [first])
    [line] = rows(stage)
    assert line.subproject_id == UUID(cabling["subproject_id"])
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostLine).where(CostLine.id == line.id).values(is_in_tracked_scope=False)
        )

    imputations: list[tuple[UUID | None, str | None]] = []
    for code in (OTHER, "SP-INCONNU", None):
        later = AT + timedelta(days=len(imputations) + 1)
        again = cost("FA-2026-0412", code, "1750.00", item="10")
        entry = load_import(stage, project, [again], at=later)
        [held] = rows(stage)
        assert (held.id, held.last_import_id, held.updated_at) == (line.id, entry, later)
        assert (held.amount, held.is_in_tracked_scope) == (Decimal("1750.00"), False)
        imputations.append((held.subproject_id, held.subproject_code))

    assert imputations == [
        (UUID(automation["subproject_id"]), OTHER),
        (None, "SP-INCONNU"),
        (None, None),
    ]


@pytest.mark.requirement("WF-DAT-0110-A")
def test_the_loader_writes_the_entry_and_the_lines_of_an_import_at_the_identifiers_imposed(
    stage: Scene,
) -> None:
    # The witness imposes the identifiers of the entry and of the lines it creates, and the instant:
    # two lines of one document and two items are two lines; loaded again, they are updated on
    # their document and item, never doubled (WF-DAT-0110), and keep their identifiers.
    lines = [
        cost("FA-2026-0301", None, "1100.00", "10"),
        cost("FA-2026-0301", None, "-50.00", "20"),
    ]
    project, author = project_of(stage), stage.manager.user_id
    entry = load_import(stage, project, lines)
    with stage.database.transaction() as session:
        held = session.get(CostImport, entry)
        assert held is not None
        assert (held.imported_at, held.requested_by, held.created_count) == (AT, author, 2)
        assert held.passthrough_columns == ["Fournisseur"]
    written = rows(stage)
    assert [row.id for row in written] == [line.cost_line_id for line in lines]
    assert [(row.document_item, row.amount) for row in written] == [
        ("10", Decimal("1100.00")),
        ("20", Decimal("-50.00")),
    ]
    assert {(row.created_by, row.last_import_id) for row in written} == {(author, entry)}
    assert all(row.is_in_tracked_scope and row.excluded_reason is None for row in written)

    later = load_import(stage, project, [cost("FA-2026-0301", None)])
    # A line without an item is another line than those of the items of the same document.
    again = rows(stage)
    assert len(again) == 3
    assert [row.id for row in again[:2]] == [line.cost_line_id for line in lines]
    assert again[2].last_import_id == later
    reloaded = load_import(stage, project, lines)
    assert [(row.id, row.last_import_id) for row in rows(stage)[:2]] == [
        (line.cost_line_id, reloaded) for line in lines
    ]
    assert len(rows(stage)) == 3


@pytest.mark.requirement("WF-DAT-0110-A")
def test_an_import_that_loads_no_line_writes_its_entry_alone(stage: Scene) -> None:
    # The entry of an import that brought no line is written alone.
    entry = load_import(stage, project_of(stage), [])
    with stage.database.transaction() as session:
        held = session.get(CostImport, entry)
        assert held is not None
        assert held.created_count == 0
    assert rows(stage) == []
