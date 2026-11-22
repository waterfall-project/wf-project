# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The migrations of what exists: the partitions, the readings and the permissions they give."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from migrations_support import partition_parts
from project_rows import insert_project, insert_revision, insert_structure
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import DBAPIError

from waterfall.core.access_roles.tables import AccessRole, AccessRolePermission, Permission
from waterfall.core.planning.tables import StructureReading
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


# The columns of the schedule of the backups, and whether the date of its timing may be null.
SCHEDULE_COLUMNS = text(
    "SELECT column_name, is_nullable FROM information_schema.columns "
    "WHERE table_name = 'backup_schedule'"
)


@pytest.mark.story("US-2910")
def test_the_schedule_of_the_backups_that_exists_is_dated_by_its_last_writing_at_0039(
    empty_engine: Engine,
) -> None:
    # #4375: 0039 dates the timing of the schedule there by its last writing, ``updated_at``, so
    # that an installation that exists does not owe at once the occurrence it had passed before its
    # update; the column is then required, and the descent drops it.
    upgrade(empty_engine, "0038")
    written_at = datetime(2026, 11, 15, 8, 30, tzinfo=UTC)
    with empty_engine.begin() as connection:
        connection.execute(
            text("UPDATE backup_schedule SET updated_at = :at, retained_count = 9"),
            {"at": written_at},
        )
    upgrade(empty_engine, "0039")
    with empty_engine.connect() as connection:
        row = connection.execute(
            text("SELECT timing_changed_at, updated_at, retained_count FROM backup_schedule")
        ).one()
        columns = dict(connection.execute(SCHEDULE_COLUMNS).all())
    assert tuple(row) == (written_at, written_at, 9)
    assert columns["timing_changed_at"] == "NO"
    downgrade(empty_engine, "0038")
    with empty_engine.connect() as connection:
        assert "timing_changed_at" not in dict(connection.execute(SCHEDULE_COLUMNS).all())
