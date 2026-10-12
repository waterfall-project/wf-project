# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a restoration keeps of the database it replaces, and writes back (WF-ADM-0160).

The rows kept — the journal of audit (#894), the backups (#893), a few tasks — are copied, once,
into a schema of their own in the same database, which the replacement of the schema ``public``
does not touch: a restoration taken up after an interruption finds them there, and does not read
again a database already half replaced. So are the rights of the role of the service, which the
dump of another installation names otherwise. Each module keeps and writes back its own table
through these functions, by its table: no text here names one.
"""

from collections.abc import Collection

from sqlalchemy import (
    Column,
    ColumnElement,
    Connection,
    MetaData,
    Table,
    Text,
    case,
    exists,
    insert,
    inspect,
    select,
    text,
)
from sqlalchemy.schema import CreateSchema, DropSchema

from waterfall.platform.database import Base

SCHEMA = "restoring"
# The rights of the role of the service of the database on the tables of ``public``, as statements:
# its own name, ``<database>_service``, is the one the installation gives it (migration 0002).
GRANTS = Table("service_grant", MetaData(schema=SCHEMA), Column("statement", Text))
SERVICE_GRANTS = """
WITH service AS (SELECT current_database() || '_service' AS name)
SELECT format('GRANT USAGE ON SCHEMA public TO %I', name) AS statement FROM service
UNION ALL
SELECT format('GRANT %s ON public.%I TO %I', granted.privilege_type, class.relname, service.name)
FROM pg_class AS class CROSS JOIN LATERAL aclexplode(class.relacl) AS granted, service
WHERE class.relnamespace = 'public'::regnamespace AND granted.grantee = service.name::regrole
UNION ALL
SELECT format(
    'GRANT %s (%I) ON public.%I TO %I',
    granted.privilege_type, attribute.attname, class.relname, service.name
)
FROM pg_attribute AS attribute JOIN pg_class AS class ON class.oid = attribute.attrelid
CROSS JOIN LATERAL aclexplode(attribute.attacl) AS granted, service
WHERE class.relnamespace = 'public'::regnamespace AND granted.grantee = service.name::regrole
"""


def table_of(entity: type[Base]) -> Table:
    """Give the table of a class of rows."""
    return Base.metadata.tables[entity.__tablename__]


def kept(table: Table) -> Table:
    """Give the copy a restoration keeps of a table: its columns, without its constraints."""
    columns = (Column(column.name, column.type) for column in table.columns)
    return Table(table.name, MetaData(schema=SCHEMA), *columns)


def is_kept(connection: Connection) -> bool:
    """Tell whether a restoration taken up has already kept what it writes back."""
    return inspect(connection).has_schema(SCHEMA)


def begin_keeping(connection: Connection) -> None:
    """Make the schema of what is kept, and keep the rights of the role of the service."""
    connection.execute(CreateSchema(SCHEMA))
    connection.execute(text(f"CREATE TABLE {SCHEMA}.service_grant AS {SERVICE_GRANTS}"))


def keep(
    connection: Connection, entity: type[Base], where: ColumnElement[bool] | None = None
) -> None:
    """Keep the rows of a table, those ``where`` says if it says any."""
    table = table_of(entity)
    copy = kept(table)
    copy.create(connection)
    rows = select(*table.columns)
    if where is not None:
        rows = rows.where(where)
    connection.execute(insert(copy).from_select([column.name for column in table.columns], rows))


def write_back(connection: Connection, entity: type[Base], unsure: Collection[str] = ()) -> None:
    """Write back the rows kept that the restored table lacks, by their identifier.

    A column of ``unsure`` refers to a row the restored database may not hold — the account that
    asked for a task, on another installation —: it is written back null where that row lacks.
    """
    table = table_of(entity)
    copy = kept(table)
    names = [column.name for column in copy.columns]
    values = [_sure(table, copy, name) if name in unsure else copy.c[name] for name in names]
    lacking = select(*values).where(~exists().where(table.c.id == copy.c.id))
    connection.execute(insert(table).from_select(names, lacking))


def _sure(table: Table, copy: Table, name: str) -> ColumnElement[object]:
    target = next(iter(table.c[name].foreign_keys)).column
    held = exists().where(target == copy.c[name])
    return case((held, copy.c[name]), else_=None).label(name)


def end_keeping(connection: Connection) -> None:
    """Give the role of the service its rights back, then drop what was kept."""
    for statement in connection.scalars(select(GRANTS.c.statement)).all():
        connection.execute(text(statement))
    connection.execute(DropSchema(SCHEMA, cascade=True))
