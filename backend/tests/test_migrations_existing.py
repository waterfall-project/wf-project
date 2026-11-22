# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The migrations of what exists: the partitions, the readings, the permissions, the kinds kept."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from indicators_support import indicator_row
from migrations_support import partition_parts
from project_rows import AT, insert_project, insert_revision, insert_structure, risk_row
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from waterfall.core.access_roles.tables import AccessRole, AccessRolePermission, Permission
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.planning.tables import StructureReading
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import Risk
from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine


@pytest.mark.requirement("WF-DAT-0050-A")
def test_the_projects_that_exist_receive_their_partition_of_the_readings_kept(
    empty_engine: Engine,
) -> None:
    # US-2270: 0031 gives a project that exists its partition of ``structure_reading``, as the
    # function gives one to a project created after it — bound, triggers, keys —; a reading is kept
    # in it, and neither the table nor the partition is truncated. The descent drops them again.
    upgrade(empty_engine, "0029")
    existing, created, revision_id, structure_id = uuid4(), uuid4(), uuid4(), uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=existing))
        connection.execute(select(func.create_project_partitions(existing)))
        connection.execute(insert_revision(existing, id=revision_id))
        connection.execute(insert_structure(existing, revision_id, id=structure_id))
    upgrade(empty_engine, "0031")
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=created))
        connection.execute(select(func.create_project_partitions(created)))
        connection.execute(
            insert(StructureReading).values(
                project_id=existing,
                structure_id=structure_id,
                revision_id=revision_id,
                format=1,
                settings_digest=bytes(32),
                document=b"{}",
                kept_at=datetime(2026, 11, 15, 8, 0, tzinfo=UTC),
            )
        )
    partition = f"structure_reading_p_{existing.hex}"
    with empty_engine.connect() as connection:
        assert partition_parts(connection, existing) == partition_parts(connection, created)
        kept_in = text("SELECT tableoid::regclass::text FROM structure_reading")
        assert connection.scalars(kept_in).all() == [partition]
    for truncated in ("structure_reading", partition):
        with pytest.raises(DBAPIError, match="never truncated"), empty_engine.begin() as connection:
            connection.execute(text(f'TRUNCATE TABLE "{truncated}" CASCADE'))
    downgrade(empty_engine, "0029")
    with empty_engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass(:name)"), {"name": partition}) is None
        procedure = text("SELECT to_regprocedure('structure_reading_refuse_truncate()')")
        assert connection.scalar(procedure) is None


@pytest.mark.requirement("WF-DAT-0050-A")
def test_the_projects_that_exist_receive_their_partition_of_the_indicators(
    empty_engine: Engine,
) -> None:
    # US-1660/L1: 0032 gives a project that exists its partition of ``revision_indicator``, as the
    # function gives one to a project created after it — bound, triggers, keys —; the descent drops
    # it again.
    upgrade(empty_engine, "0031")
    existing, created = uuid4(), uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=existing))
        connection.execute(select(func.create_project_partitions(existing)))
    upgrade(empty_engine, "0032")
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=created))
        connection.execute(select(func.create_project_partitions(created)))
    partition = f"revision_indicator_p_{existing.hex}"
    found = text("SELECT to_regclass(:name)")
    with empty_engine.connect() as connection:
        assert partition_parts(connection, existing) == partition_parts(connection, created)
        assert connection.scalar(found, {"name": partition}) is not None
    downgrade(empty_engine, "0031")
    with empty_engine.connect() as connection:
        assert connection.scalar(found, {"name": partition}) is None


def catalogue_and_grants(
    engine: Engine,
) -> tuple[list[tuple[str, str | None]], set[tuple[str, str]]]:
    """Give the catalogue in its order, code and function, and each role's label with a code."""
    with engine.connect() as connection:
        catalogue = connection.execute(
            select(Permission.code, Permission.fbs_code).order_by(Permission.position)
        ).all()
        grants = connection.execute(
            select(AccessRole.label, Permission.code)
            .join(AccessRolePermission, AccessRolePermission.access_role_id == AccessRole.id)
            .join(Permission, Permission.id == AccessRolePermission.permission_id)
        ).all()
    return [(code, fbs) for code, fbs in catalogue], {(label, code) for label, code in grants}


@pytest.mark.requirement("WF-ADM-0100-A")
def test_the_permissions_of_the_installation_arrive_by_a_migration_to_whoever_administers(
    empty_engine: Engine,
) -> None:
    # Of the Vérif of WF-ADM-0100-A, « Chaque fonction de second niveau de l'arborescence est
    # représentée par ses deux permissions » — the installation, FBS-1.6 — and « Aucun écran ne
    # permet de créer une permission » — they arrive by a migration, as the rest of the catalogue.
    # Given to a role not deleted holding both permissions of administration (WF-ADM-0120), to
    # none other; the descent gives back the catalogue and the grants it found.
    upgrade(empty_engine, "0029")
    holding = {
        "Administrateur": ("users.write", "access_roles.write", "audit_log.read"),
        "Comptes": ("users.write",),
        "Rôles": ("access_roles.write",),
        "Supprimé": ("users.write", "access_roles.write"),
    }
    moment = datetime(2026, 11, 15, tzinfo=UTC)
    with empty_engine.begin() as connection:
        ids = dict(connection.execute(select(Permission.code, Permission.id)).all())
        for label, codes in holding.items():
            role_id = uuid4()
            connection.execute(
                insert(AccessRole).values(
                    id=role_id,
                    label=label,
                    is_predefined=False,
                    deleted_at=moment if label == "Supprimé" else None,
                    created_at=moment,
                    updated_at=moment,
                )
            )
            connection.execute(
                insert(AccessRolePermission),
                [{"access_role_id": role_id, "permission_id": ids[code]} for code in codes],
            )
    before = catalogue_and_grants(empty_engine)
    upgrade(empty_engine)
    catalogue, grants = catalogue_and_grants(empty_engine)
    after = catalogue.index(("audit_log.read", "FBS-1.5"))
    assert catalogue[after + 1 : after + 3] == [
        ("installation.read", "FBS-1.6"),
        ("installation.write", "FBS-1.6"),
    ]
    # The others keep their order.
    assert catalogue[: after + 1] + catalogue[after + 3 :] == before[0]
    added = {grant for grant in grants if grant[1].startswith("installation.")}
    assert added == {
        ("Administrateur", "installation.read"),
        ("Administrateur", "installation.write"),
    }
    assert grants - added == before[1]
    downgrade(empty_engine, "0029")
    assert catalogue_and_grants(empty_engine) == before
    # And up again: the catalogue and the grants of the first rise (0029, the head, 0029, the head).
    upgrade(empty_engine)
    assert catalogue_and_grants(empty_engine) == (catalogue, grants)


@pytest.mark.requirement("WF-DAT-0050-A")
def test_the_projects_that_exist_receive_their_partitions_of_the_risks(
    empty_engine: Engine,
) -> None:
    # US-2550/L1: 0035 gives a project that exists its partitions of the three revised tables of
    # the risks, and to its structures and its nodes the column, the checks, the keys and the
    # indexes it adds, as the function gives them to a project created after it; its main structure
    # stays valid, without a risk. The descent drops them again, and the column with them.
    upgrade(empty_engine, "0034")
    existing, created, revision_id, structure_id = uuid4(), uuid4(), uuid4(), uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=existing))
        connection.execute(select(func.create_project_partitions(existing)))
        connection.execute(insert_revision(existing, id=revision_id))
        connection.execute(insert_structure(existing, revision_id, id=structure_id))
    upgrade(empty_engine, "0035")
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=created))
        connection.execute(select(func.create_project_partitions(created)))
    found = text("SELECT to_regclass(:name)")
    partitions = [
        f"{table}_p_{existing.hex}"
        for table in ("risk_evaluation", "risk_review", "risk_reference_share")
    ]
    risk = text("SELECT kind, risk_id FROM cost_structure WHERE id = :id")
    with empty_engine.connect() as connection:
        assert partition_parts(connection, existing) == partition_parts(connection, created)
        assert all(connection.scalar(found, {"name": each}) for each in partitions)
        assert tuple(connection.execute(risk, {"id": structure_id}).one()) == ("main", None)
    for truncated in ("risk_evaluation", partitions[1]):
        with pytest.raises(DBAPIError, match="never truncated"), empty_engine.begin() as connection:
            connection.execute(text(f'TRUNCATE TABLE "{truncated}" CASCADE'))
    downgrade(empty_engine, "0034")
    column = text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name = 'cost_structure' AND column_name = 'risk_id'"
    )
    with empty_engine.connect() as connection:
        assert [connection.scalar(found, {"name": each}) for each in partitions] == [None] * 3
        assert connection.scalar(found, {"name": "risk"}) is None
        assert connection.scalar(column) == 0


def test_the_kinds_of_the_portfolio_are_admitted_and_one_kept_holds_the_descent_back(
    empty_engine: Engine,
) -> None:
    # Covers no requirement: the check of the kinds and the trigger of ``computed_at``, not a direct
    # write on a marked revision. #3549, US-2670/L1: before 0042, the check of the kinds refuses a
    # document of the portfolio; after it, one written by the transaction that marks its revision
    # is kept, the trigger of 0032 unchanged.
    # The descent would refuse it again: it fails, nothing deleted, the base at 0042.
    upgrade(empty_engine, "0036")
    project_id, revision_id = uuid4(), uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project_id))
        connection.execute(select(func.create_project_partitions(project_id)))
        connection.execute(insert_revision(project_id, id=revision_id))
    document = insert(RevisionIndicator).values(
        **indicator_row(project_id, revision_id, kind="portfolio_risks")
    )
    marking = (
        update(Revision)
        .where(Revision.id == revision_id)
        .values(status="marked", version_name="v1.0", marked_at=AT)
    )
    with pytest.raises(IntegrityError, match="kind_known"), empty_engine.begin() as connection:
        connection.execute(document)
    upgrade(empty_engine, "0042")
    with empty_engine.begin() as connection:
        connection.execute(document)
        connection.execute(marking)
    with pytest.raises(DBAPIError, match="kind_known"):
        downgrade(empty_engine, "0036")
    with empty_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0042"
        kept = connection.scalars(text("SELECT kind FROM revision_indicator")).all()
    assert kept == ["portfolio_risks"]


@pytest.mark.requirement("WF-DAT-0050-A")
def test_the_own_estimates_as_differentials_are_refused_over_an_own_estimate_of_ep_08(
    empty_engine: Engine,
) -> None:
    # EP-30, US-3070/L1: 0044 takes up no own estimate of EP-08 and refuses, saying it, while one
    # exists, nothing applied; without one, it applies, and a project that exists receives its
    # partition of the abandonments. The descent refuses likewise over an own estimate.
    upgrade(empty_engine, "0043")
    project_id, revision_id, risk_id, own = uuid4(), uuid4(), uuid4(), uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project_id))
        connection.execute(select(func.create_project_partitions(project_id)))
        connection.execute(insert_revision(project_id, id=revision_id))
        connection.execute(insert_structure(project_id, revision_id))
        connection.execute(insert(Risk).values(**risk_row(project_id, id=risk_id)))
        connection.execute(
            text(
                "INSERT INTO cost_structure (project_id, id, revision_id, kind, label, is_merged, "
                "lineage_id, risk_id, lock_version, created_at, updated_at) VALUES (:project, "
                ":id, :revision, 'risk', 'Retard', false, :id, :risk, 1, :at, :at)"
            ),
            {"project": project_id, "id": own, "revision": revision_id, "risk": risk_id, "at": AT},
        )
    refused = "an own estimate of a risk exists"
    with pytest.raises(DBAPIError, match=refused):
        upgrade(empty_engine, "0044")
    version = text("SELECT version_num FROM alembic_version")
    with empty_engine.begin() as connection:
        assert connection.scalar(version) == "0043"
        connection.execute(text("DELETE FROM cost_structure WHERE id = :id"), {"id": own})
    upgrade(empty_engine, "0044")
    partition = text("SELECT to_regclass(:name)")
    with empty_engine.begin() as connection:
        name = f"own_estimate_abandonment_p_{project_id.hex}"
        assert connection.scalar(partition, {"name": name}) == name
        connection.execute(
            insert(CostStructure).values(
                project_id=project_id,
                id=own,
                revision_id=revision_id,
                kind="risk",
                label="Retard",
                is_merged=False,
                lineage_id=own,
                risk_id=risk_id,
                main_lock_version=1,
                lock_version=1,
                created_at=AT,
                updated_at=AT,
            )
        )
    with pytest.raises(DBAPIError, match=refused):
        downgrade(empty_engine, "0043")
    with empty_engine.connect() as connection:
        assert connection.scalar(version) == "0044"
