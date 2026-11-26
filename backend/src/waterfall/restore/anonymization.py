# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``waterfall-restore anonymize``: a copy of the production anonymised before it is opened.

(WF-EXP-0010, US-2960.) A copy of the production is installed in another environment — a
preproduction — only once its accounts designate nobody: restored, anonymised, then opened. The
command runs between the restoration and the opening, the API, the worker and Keycloak stopped. It
reads ``WATERFALL_DATABASE_URL`` and ``WATERFALL_KEYCLOAK_DATABASE_URL``, the owners of the two
databases, and ``WATERFALL_KEYCLOAK_REALM``, the realm of the installation; a setting that lacks
stops it at start, named (2), and so does ``master``, the realm of the administration of Keycloak.
Its databases being those of the production too, it changes nothing unless told, by
``--yes-this-is-a-copy``, that they are a copy's: without it, it stops at start (2).

It anonymises each database in one transaction, Waterfall's first, the migrations applied before:

- **Waterfall's**: every account anonymised at once, by the rules of the anonymisation of one
  account, and the journal of audit forgets their names (``anonymize_every_account``, WF-ADM-0060,
  WF-SEC-0030) — but its administrators, the active accounts that hold the administration, which
  stay active under an identity in the reserved domain ``waterfall.test``, lest nobody enter the
  copy (WF-ADM-0120, #4068);
- **the identity provider's**, which is not a module of Waterfall and is read in its tables, as the
  backup counts them (``worker.inventory``): every person of the realm — the accounts of service of
  its clients apart — keeps her identifier, the subject Waterfall knows her by, and loses her user
  name, which becomes that identifier, her names, her address, her attributes, her links to an
  external provider or to the directory, her credentials and her consents; she is disabled. An
  administrator kept is given the identity Waterfall gave it, its address as its user name, and
  stays enabled, without a password. The events of the realm, of sign-in and of administration,
  which copy names and addresses, and its sessions, are deleted. The realm is cut off from what is
  outside it: its federations of users — a directory, with their mappers and their settings, the
  account they bind as among them — and its external identity providers, with their mappers, are
  removed, lest the copy opened read the directory of the production again, or sign in through its
  provider. The persons of ``master``, who administer Keycloak, lose their names and their
  addresses — a user name that is an address too —, and keep their credentials: ``keycloak-realm``
  gives its administrator the password of the environment back. Its events go too. Last, no realm
  keeps its mail server, nor its listeners of events: the copy opened sends no mail by the server
  of the production (#5048). A table that the version of Keycloak does not have is passed over.

The amounts, the projects and their dates stay: only the accounts designate persons. The
administrators kept are written on the standard output, the installation's said: nothing is mailed
to them, and the operator gives them their access back by the link of the installation, which
``waterfall-api install`` writes once the copy is opened (WF-EXP-0020). Run again, it changes
nothing more and succeeds: a run that failed halfway is run again. A realm the database of the
provider does not hold stops it before anything is changed (1); so does any failure, said in the
structured logs.
"""

import sys
from typing import IO, TYPE_CHECKING

from sqlalchemy import text

from waterfall import schema
from waterfall.core.access_roles.interface import administrators
from waterfall.core.users.interface import (
    CopyAnonymized,
    KeptAdministrator,
    anonymize_every_account,
    read_installation_administrator,
)
from waterfall.migrations.runner import upgrade
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.installation import THE_ROW, Installation
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.settings import (
    ADMINISTRATION_REALM,
    AnonymizationSettings,
    SettingsError,
    load_anonymization_settings,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from uuid import UUID

    from sqlalchemy import Connection
    from sqlalchemy.orm import Session

COMMAND = "anonymize"
# What tells the command that the databases it is given are those of a copy, not the production's.
CONFIRMATION = "--yes-this-is-a-copy"
# What follows the address of the installation administrator kept: where its link is had.
INSTALLATION_NOTE = " (installation administrator: waterfall-api install writes its link)"

logger = get_logger(__name__)

REALM = text("SELECT id FROM realm WHERE name = :name")
COUNT = text(
    "SELECT count(*) FROM user_entity "
    "WHERE realm_id = :realm AND service_account_client_link IS NULL"
)
# What names a person of the realm — one of its accounts, those of the service of its clients
# apart — besides her account, deleted before it is changed: what she holds, then what the realm
# keeps of her doings. Each statement is given with its table, passed over if the version of
# Keycloak does not have it.
FORGOTTEN: tuple[tuple[str, str], ...] = (
    (
        "user_attribute",
        (
            "DELETE FROM user_attribute WHERE user_id IN (SELECT id FROM user_entity "
            "WHERE realm_id = :realm AND service_account_client_link IS NULL)"
        ),
    ),
    (
        "federated_identity",
        (
            "DELETE FROM federated_identity WHERE user_id IN (SELECT id FROM user_entity "
            "WHERE realm_id = :realm AND service_account_client_link IS NULL)"
        ),
    ),
    (
        "credential",
        (
            "DELETE FROM credential WHERE user_id IN (SELECT id FROM user_entity "
            "WHERE realm_id = :realm AND service_account_client_link IS NULL)"
        ),
    ),
    (
        "user_consent_client_scope",
        (
            "DELETE FROM user_consent_client_scope WHERE user_consent_id IN (SELECT consent.id "
            "FROM user_consent AS consent "
            "JOIN user_entity AS person ON person.id = consent.user_id "
            "WHERE person.realm_id = :realm AND person.service_account_client_link IS NULL)"
        ),
    ),
    (
        "user_consent",
        (
            "DELETE FROM user_consent WHERE user_id IN (SELECT id FROM user_entity "
            "WHERE realm_id = :realm AND service_account_client_link IS NULL)"
        ),
    ),
    # The persons of a directory the realm does not import, kept beside its accounts.
    ("fed_user_attribute", "DELETE FROM fed_user_attribute WHERE realm_id = :realm"),
    (
        "fed_user_consent_cl_scope",
        (
            "DELETE FROM fed_user_consent_cl_scope WHERE user_consent_id IN "
            "(SELECT id FROM fed_user_consent WHERE realm_id = :realm)"
        ),
    ),
    ("fed_user_consent", "DELETE FROM fed_user_consent WHERE realm_id = :realm"),
    ("fed_user_credential", "DELETE FROM fed_user_credential WHERE realm_id = :realm"),
    (
        "fed_user_group_membership",
        "DELETE FROM fed_user_group_membership WHERE realm_id = :realm",
    ),
    ("fed_user_required_action", "DELETE FROM fed_user_required_action WHERE realm_id = :realm"),
    ("fed_user_role_mapping", "DELETE FROM fed_user_role_mapping WHERE realm_id = :realm"),
    # The events copy the user name, the address and the representation of an account.
    ("event_entity", "DELETE FROM event_entity WHERE realm_id = :realm"),
    ("admin_event_entity", "DELETE FROM admin_event_entity WHERE realm_id = :realm"),
    # The sessions, kept in the database, and their notes.
    (
        "offline_client_session",
        (
            "DELETE FROM offline_client_session WHERE user_session_id IN "
            "(SELECT user_session_id FROM offline_user_session WHERE realm_id = :realm)"
        ),
    ),
    ("offline_user_session", "DELETE FROM offline_user_session WHERE realm_id = :realm"),
    ("login_failure", "DELETE FROM login_failure WHERE realm_id = :realm"),
)
# What ties the realm to the outside, removed: its federations of users, which would read the
# directory of the production again and import its persons, with their settings — the address of
# the directory and the account it binds as among them —, then its external identity providers,
# with their mappers and their settings. A federation — a directory, or Kerberos — is a component
# of the realm, under which its mappers lie, at any depth. Their former shape, kept by Keycloak
# beside the components, goes too. Given as the persons' are.
DETACHED: tuple[tuple[str, str], ...] = (
    (
        "component_config",
        (
            "WITH RECURSIVE federation(id) AS (SELECT id FROM component WHERE realm_id = :realm"
            " AND provider_type = 'org.keycloak.storage.UserStorageProvider'"
            " UNION SELECT component.id FROM component"
            " JOIN federation ON component.parent_id = federation.id) "
            "DELETE FROM component_config WHERE component_id IN (SELECT id FROM federation)"
        ),
    ),
    (
        "component",
        (
            "WITH RECURSIVE federation(id) AS (SELECT id FROM component WHERE realm_id = :realm"
            " AND provider_type = 'org.keycloak.storage.UserStorageProvider'"
            " UNION SELECT component.id FROM component"
            " JOIN federation ON component.parent_id = federation.id) "
            "DELETE FROM component WHERE id IN (SELECT id FROM federation)"
        ),
    ),
    (
        "user_federation_mapper_config",
        (
            "DELETE FROM user_federation_mapper_config WHERE user_federation_mapper_id IN "
            "(SELECT id FROM user_federation_mapper WHERE realm_id = :realm)"
        ),
    ),
    ("user_federation_mapper", "DELETE FROM user_federation_mapper WHERE realm_id = :realm"),
    (
        "user_federation_config",
        (
            "DELETE FROM user_federation_config WHERE user_federation_provider_id IN "
            "(SELECT id FROM user_federation_provider WHERE realm_id = :realm)"
        ),
    ),
    ("user_federation_provider", "DELETE FROM user_federation_provider WHERE realm_id = :realm"),
    # The links of the persons of a directory the realm does not import, to an external provider.
    ("broker_link", "DELETE FROM broker_link WHERE realm_id = :realm"),
    (
        "idp_mapper_config",
        (
            "DELETE FROM idp_mapper_config WHERE idp_mapper_id IN "
            "(SELECT id FROM identity_provider_mapper WHERE realm_id = :realm)"
        ),
    ),
    ("identity_provider_mapper", "DELETE FROM identity_provider_mapper WHERE realm_id = :realm"),
    (
        "identity_provider_config",
        (
            "DELETE FROM identity_provider_config WHERE identity_provider_id IN "
            "(SELECT internal_id FROM identity_provider WHERE realm_id = :realm)"
        ),
    ),
    ("identity_provider", "DELETE FROM identity_provider WHERE realm_id = :realm"),
)
# The account of a person: her identifier stays, and names her user name; nothing else names her.
ANONYMIZED = text(
    "UPDATE user_entity SET username = id, email = NULL, email_constraint = id, "
    "email_verified = false, first_name = NULL, last_name = NULL, enabled = false, "
    "federation_link = NULL "
    "WHERE realm_id = :realm AND service_account_client_link IS NULL"
)
# An administrator Waterfall keeps: the identity it gave it, its address as its user name, as the
# realm names its persons, enabled. Its credentials are gone with the others': it has no password.
KEPT = text(
    "UPDATE user_entity SET username = :email, email = :email, email_constraint = :email, "
    "email_verified = true, first_name = :first_name, last_name = :last_name, enabled = true "
    "WHERE realm_id = :realm AND id = :subject AND service_account_client_link IS NULL"
)
# A person of the realm of the administration of Keycloak: her names and her address go, and her
# user name if it is an address; her credentials stay, which administer Keycloak.
ADMINISTERING = text(
    "UPDATE user_entity SET email = NULL, email_constraint = id, email_verified = false, "
    "first_name = NULL, last_name = NULL, "
    "username = CASE WHEN strpos(username, '@') > 0 THEN id ELSE username END "
    "WHERE realm_id = :realm AND service_account_client_link IS NULL"
)
# What the realm of the administration keeps of the doings of its persons.
ADMINISTRATION_EVENTS: tuple[tuple[str, str], ...] = (
    ("event_entity", "DELETE FROM event_entity WHERE realm_id = :realm"),
    ("admin_event_entity", "DELETE FROM admin_event_entity WHERE realm_id = :realm"),
)
# What would send a mail from a realm: its mail server, with its account and its password, and its
# listeners of events, among which the one that mails (#5048).
SILENCED: tuple[tuple[str, str], ...] = (
    ("realm_smtp_config", "DELETE FROM realm_smtp_config WHERE realm_id = ANY(:realms)"),
    ("realm_events_listeners", "DELETE FROM realm_events_listeners WHERE realm_id = ANY(:realms)"),
)
EVERY_REALM = text("SELECT id FROM realm ORDER BY id")
EXISTS = text("SELECT to_regclass(:table) IS NOT NULL")


def main(arguments: Sequence[str] = ()) -> int:
    """Anonymise the copy the settings designate; say why not, a setting that lacks returning 2.

    ``arguments`` are those after the command: ``--yes-this-is-a-copy`` alone, without which it
    changes nothing and returns 2.
    """
    if list(arguments) != [CONFIRMATION]:
        sys.stderr.write(
            f"waterfall-restore {COMMAND}: changes the databases it is given for good; "
            f"run it on a copy restored alone, with {CONFIRMATION}\n"
        )
        return 2
    try:
        settings = load_anonymization_settings()
    except SettingsError as error:
        sys.stderr.write(f"waterfall-restore {COMMAND}: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        return anonymize(settings, sys.stdout)


def anonymize(settings: AnonymizationSettings, out: IO[str]) -> int:
    """Anonymise the two databases of the copy, Waterfall's first; give the status.

    The realm is looked for before anything is changed: one the provider does not hold stops it,
    nothing changed in either database. The migrations are applied then, before the accounts of
    Waterfall are read. The administrators kept are written on ``out`` once both are anonymised.
    """
    schema.declared()
    waterfall = create_database_engine(settings.database_url.get_secret_value())
    provider = create_database_engine(settings.keycloak_database_url.get_secret_value())
    try:
        with provider.connect() as connection:
            known = connection.execute(REALM, {"name": settings.keycloak_realm}).scalar()
        if known is None:
            logger.error("anonymization.realm_unknown", realm=settings.keycloak_realm)
            return 1
        upgrade(waterfall)
        with Database(waterfall).transaction() as session:
            done = anonymize_every_account(session, utc_now(), administrators(session))
            installer = _installation_administrator(session)
        with provider.begin() as connection:
            persons = anonymize_realm(connection, settings.keycloak_realm, done.administrators)
            administering = anonymize_administration(connection)
            silence(connection, connection.execute(EVERY_REALM).scalars().all())
    except Exception:
        logger.exception("anonymization.failed")
        return 1
    finally:
        provider.dispose()
        waterfall.dispose()
    _tell(out, done, installer)
    logger.info(
        "anonymization.done",
        persons=persons,
        accounts=done.accounts,
        administrators=len(done.administrators),
        administering=administering,
    )
    return 0


def _installation_administrator(session: Session) -> UUID | None:
    """Give the administrator the bootstrap created, if the copy holds it."""
    installation = session.get(Installation, THE_ROW)
    if installation is None:
        return None
    account = read_installation_administrator(session, installation.installed_at)
    return None if account is None else account.user_id


def _tell(out: IO[str], done: CopyAnonymized, installer: UUID | None) -> None:
    """Write for the operator the administrators kept, and how their access is given back.

    Nothing is mailed to them: their addresses reach nobody. The link of the installation, which
    ``waterfall-api install`` writes once the copy is opened, is the installation administrator's;
    the others are given theirs by an administrator signed in (WF-ADM-0140). An installation
    administrator not kept is said in the logs: the bootstrap refuses it, anonymised.
    """
    out.write(f"waterfall-restore {COMMAND}: administrators kept active, without a password:\n")
    for kept in done.administrators:
        note = INSTALLATION_NOTE if kept.user_id == installer else ""
        out.write(f"{kept.email}{note}\n")
    if all(kept.user_id != installer for kept in done.administrators):
        logger.warning("anonymization.installation_administrator_not_kept")


def anonymize_realm(
    connection: Connection, realm: str, kept: Sequence[KeptAdministrator] = ()
) -> int | None:
    """Anonymise every person of ``realm`` in the database of the provider; give how many.

    The administrators ``kept`` are given the identity Waterfall gave them, and stay enabled. The
    realm is cut off from its federations of users and its external providers. ``None`` if the
    database holds no such realm, nothing changed.
    """
    realm_id = connection.execute(REALM, {"name": realm}).scalar()
    if realm_id is None:
        return None
    _run(connection, (*FORGOTTEN, *DETACHED), {"realm": realm_id})
    persons = connection.execute(COUNT, {"realm": realm_id}).scalar_one()
    connection.execute(ANONYMIZED, {"realm": realm_id})
    for administrator in kept:
        identity = {
            "subject": administrator.subject,
            "email": administrator.email,
            "first_name": administrator.first_name,
            "last_name": administrator.last_name,
        }
        connection.execute(KEPT, {"realm": realm_id, **identity})
    return int(persons)


def anonymize_administration(connection: Connection, realm: str = ADMINISTRATION_REALM) -> int:
    """Take from the persons of the realm of the administration their names and their addresses.

    Their events go too. Give how many persons it holds; none if the database holds no such realm.
    """
    realm_id = connection.execute(REALM, {"name": realm}).scalar()
    if realm_id is None:
        return 0
    _run(connection, ADMINISTRATION_EVENTS, {"realm": realm_id})
    persons = connection.execute(COUNT, {"realm": realm_id}).scalar_one()
    connection.execute(ADMINISTERING, {"realm": realm_id})
    return int(persons)


def silence(connection: Connection, realm_ids: Collection[str]) -> None:
    """Take from the realms given, by their identifiers, their mail server and their listeners."""
    _run(connection, SILENCED, {"realms": list(realm_ids)})


def _run(
    connection: Connection, statements: Sequence[tuple[str, str]], values: dict[str, object]
) -> None:
    """Run each statement whose table the database of the provider has; pass over the others."""
    for table, statement in statements:
        if connection.execute(EXISTS, {"table": table}).scalar():
            connection.execute(text(statement), values)
