# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The bootstrap of a new installation: ``waterfall-api install`` (WF-EXP-0020, US-0420).

It applies the migrations — the catalogue of permissions with them — as the owner of the tables,
who creates the role of the service too (#701). Then, under an advisory lock that keeps two
bootstraps apart, on an installation that has none yet: the local account of the administrator in
the identity provider first, then, in one transaction, the row of the installation with its default
language and its bounds, the three predefined roles labelled in that language, the account in
Waterfall, holding the administrator — the platform their author, each inscribed in the journal
under the correlation of the command —, and the reference a project needs first (WF-EXP-0020,
EP-05): the settings the installation shares, with its currency and the name of its company, the
units of duration, the empty mapping of the actual costs, the default calendar, and the nature and
the category of provision for risks, labelled in that language, each by the interface of its
module. The realm is then given the language of the installation, at
each run: an account that chose none reads its pages and its mails in it (#873). Last, the link
that sets the password of that account, valid until it is used, written alone on the standard
output, its making inscribed without its token.

Run again, it creates nothing: it makes a new link, which replaces the one before, while the
administrator has no password, and none afterwards; another currency or another name of the company
are said ignored. An installation made before the reference existed is given it then, in a
transaction of its own: no migration writes data. Keycloak is never asked inside a transaction
(#669); a run broken once the provider created the account finds it by its address at the next.

The command ``waterfall-api`` starts here: ``install`` bootstraps, anything else is the API's. The
bootstrap applies the migrations, which the API does not import (``[tool.importlinter]``): it sits
above them both, and nothing imports it.
"""

import sys
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import IO, TYPE_CHECKING, Any

from sqlalchemy import Engine, func, select

from waterfall import schema
from waterfall.api import main as api
from waterfall.core.access_roles.interface import (
    RoleWrite,
    create_role,
    give_first_roles,
    predefined_roles,
)
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_actual_cost_mapping,
    create_cost_category,
    create_cost_type,
    install_reference_settings,
    read_reference_settings,
)
from waterfall.core.resource_settings.interface import (
    CalendarContent,
    WeeklyHours,
    create_calendar,
    install_duration_units,
)
from waterfall.core.users.interface import (
    Account,
    Identity,
    create_local_account,
    display_name,
    identity_faults,
    inscribe_password_link,
    read_installation_administrator,
)
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import Act
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import ServiceError
from waterfall.platform.installation import THE_ROW, Installation
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import (
    INSTALLATION_CLIENT,
    KeycloakAdmin,
    LocalIdentity,
    NoInstallationLink,
)
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.settings import (
    InstallationSettings,
    SettingsError,
    load_installation_settings,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from sqlalchemy.orm import Session

# The key of the advisory lock under which a bootstrap reads what is installed, then installs.
INSTALL_LOCK = 4_200_420
# The bounds of a new installation, those of the example ``installation`` of the contract: an
# avatar of two mebibytes, a backup deposited for a restoration of twenty gibibytes.
AVATAR_MAX_BYTES = 2 * 1024**2
EXTERNAL_BACKUP_MAX_BYTES = 20 * 1024**3
# Why the platform refuses a bootstrap: an installation without its administrator, or whose
# administrator was anonymised, an address that is none, an address an account of a directory or of
# a provider holds, an administrator the realm no longer holds, or no longer as a local account.
NO_ADMINISTRATOR = "no_administrator"
ADMINISTRATOR_ANONYMIZED = "administrator_anonymized"
NOT_AN_ADDRESS = "admin_email_not_an_address"
ADDRESS_NOT_LOCAL = "admin_email_held_in_identity_provider"
ADMINISTRATOR_NOT_IN_PROVIDER = "administrator_not_in_provider"
ADMINISTRATOR_NOT_LOCAL = "administrator_not_local"
# The administrator is named after its role, in the language of the installation; it may rename
# itself afterwards, as any local account.
FIRST_NAME = "Waterfall"
# The nature and the category of provision for risks the installation is delivered with: their
# codes, and the accounting code of the category, the same in every language, none of them a code
# of the witness, whose own are added beside them (EP-05, "Le chargeur du témoin").
PROVISION = "provision"
PROVISION_TYPE_CODE = "PROV"
PROVISION_CATEGORY_CODE = "PROV-001"
PROVISION_ACCOUNTING_CODE = "151000"
# The default calendar: eight hours from Monday to Friday, none at the weekend (WF-EXP-0020).
WORKING_DAY = Decimal(8)
RESTING_DAY = Decimal(0)
EIGHT_HOURS = WeeklyHours(
    WORKING_DAY, WORKING_DAY, WORKING_DAY, WORKING_DAY, WORKING_DAY, RESTING_DAY, RESTING_DAY
)


@dataclass(frozen=True, slots=True)
class Chosen:
    """What the installer chooses of the reference, and the language of its labels."""

    currency: str
    company_name: str
    language: str


@dataclass(frozen=True, slots=True)
class DeliveredLabels:
    """The labels of the objects of the reference the installation is delivered with."""

    calendar: str
    nature: str
    category: str


# In each language of an installation, beside those of the predefined roles
# (``access_roles.predefined``); modifiable afterwards, as any label (WF-EXP-0020). The label of
# the calendar is none of the witness's, which are unique.
DELIVERED_LABELS: dict[str, DeliveredLabels] = {
    "fr": DeliveredLabels(
        "Calendrier standard", "Provision pour risques", "Provision pour risques"
    ),
    "en": DeliveredLabels("Standard calendar", "Risk provision", "Risk provision"),
}

logger = get_logger(__name__)


class InstallationRefusedError(Exception):
    """The bootstrap cannot be completed as the platform stands: said by a reason, in snake_case."""

    def __init__(self, reason: str) -> None:
        """Refuse for ``reason``."""
        super().__init__(reason)
        self.reason = reason


def main(argv: Sequence[str] | None = None) -> int:
    """Bootstrap the installation if asked to, ``install``; else, start the API (``api.main``).

    The bootstrap stops at start, naming the variable that lacks (2), rather than run without its
    settings (WF-SEC-0010); it writes the link of the administrator on the standard output, and
    its logs on the error output.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["install"]:
        return api.main(arguments)
    try:
        settings = load_installation_settings()
    except SettingsError as error:
        sys.stderr.write(f"{api.NAME} install: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    return install(settings, sys.stdout)


def install(settings: InstallationSettings, out: IO[str]) -> int:
    """Bootstrap the installation the settings designate, and write its link, if any, on ``out``.

    Under a correlation of its own, which its inscriptions carry (#701). A refusal, or a failure of
    the database or of Keycloak, ends it (1), said in the structured logs.
    """
    schema.declared()
    engine = create_database_engine(settings.database_url.get_secret_value())
    keycloak = Keycloak(settings)
    try:
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            return _install(engine, keycloak, settings, out)
    finally:
        keycloak.close()
        engine.dispose()


def _install(
    engine: Engine, keycloak: Keycloak, settings: InstallationSettings, out: IO[str]
) -> int:
    admin = KeycloakAdmin(keycloak, settings)
    installer = KeycloakAdmin(
        keycloak, settings, client=(INSTALLATION_CLIENT, settings.installation_client_secret)
    )
    # Why the platform refuses the bootstrap: a state to correct, not a failure to trace.
    refusal: tuple[str, dict[str, Any]]
    try:
        upgrade(engine)
        database = Database(engine)
        with _alone(engine):
            administrator, language = _bootstrap(database, admin, settings)
            installer.set_default_language(language)
            link = _link(database, installer, administrator)
    except InstallationRefusedError as refused:
        refusal = (refused.reason, {})
    except ServiceError as refused:
        refusal = (refused.code, dict(refused.params))
    except Exception:
        logger.exception("installation.failed")
        return 1
    else:
        if link is None:
            logger.info("installation.no_link", user_id=str(administrator.user_id))
        else:
            out.write(f"{link}\n")
            logger.info("installation.link_made", user_id=str(administrator.user_id))
        return 0
    logger.error("installation.refused", reason=refusal[0], params=refusal[1])
    return 1


@contextmanager
def _alone(engine: Engine) -> Generator[None]:
    """Hold the lock of the bootstrap, on a connection of its own, outside of any transaction.

    A lock of the session: Keycloak is asked between the transactions it keeps apart (#669).
    """
    with engine.connect() as connection:
        connection.execute(select(func.pg_advisory_lock(INSTALL_LOCK)))
        connection.commit()
        try:
            yield
        finally:
            connection.rollback()
            connection.execute(select(func.pg_advisory_unlock(INSTALL_LOCK)))
            connection.commit()


def _bootstrap(
    database: Database, admin: KeycloakAdmin, settings: InstallationSettings
) -> tuple[Account, str]:
    """Install what nobody may enter without, unless it is installed.

    Give its administrator and its language: those of the installation already made, whatever the
    settings say now — an address that is not the administrator's is said ignored, without it. An
    administrator anonymised since is refused as soon as it is read, before Keycloak is asked: it
    holds no address, and the realm no longer holds its account (WF-ADM-0060).
    """
    with database.transaction() as session:
        installation = session.get(Installation, THE_ROW)
        language = None if installation is None else installation.default_language
        administrator = read_installation_administrator(session)
    if language is not None:
        if administrator is None:
            raise InstallationRefusedError(NO_ADMINISTRATOR)
        if administrator.anonymized_at is not None:
            raise InstallationRefusedError(ADMINISTRATOR_ANONYMIZED)
        logger.info("installation.already_installed")
        if (
            administrator.email is None
            or administrator.email.lower() != settings.admin_email.lower()
        ):
            logger.warning("installation.admin_email_ignored", user_id=str(administrator.user_id))
        with database.transaction() as session:
            _reference_again(session, settings, language)
        return administrator, language
    roles = predefined_roles(settings.default_language)
    label = next(role.label for role in roles if role.key == "administrator")
    identity = Identity(label, FIRST_NAME, settings.admin_email)
    if identity_faults(identity.email):
        raise InstallationRefusedError(NOT_AN_ADDRESS)
    subject = admin.create_account(LocalIdentity(label, FIRST_NAME, identity.email))
    if subject is None:
        subject = _left_by_a_broken_run(admin, identity.email)
    with database.transaction() as session:
        act = Act(None, utc_now())
        session.add(
            Installation(
                id=THE_ROW,
                default_language=settings.default_language,
                avatar_max_bytes=AVATAR_MAX_BYTES,
                external_backup_max_bytes=EXTERNAL_BACKUP_MAX_BYTES,
                installed_at=act.at,
            )
        )
        created = {
            role.key: create_role(
                session, RoleWrite(role.label, role.permissions, is_predefined=True), act
            )
            for role in roles
        }
        account = create_local_account(session, identity, subject, act)
        named = (account.user_id, display_name(account.first_name, account.last_name))
        give_first_roles(session, named, [created["administrator"].access_role_id], act)
        install_reference(session, chosen(settings, settings.default_language), act)
    logger.info("installation.installed", user_id=str(account.user_id))
    return account, settings.default_language


def chosen(settings: InstallationSettings, language: str) -> Chosen:
    """Give what the settings of the bootstrap choose of the reference, labelled in ``language``."""
    return Chosen(settings.currency, settings.company_name, language)


def install_reference(session: Session, choice: Chosen, act: Act) -> bool:
    """Write the reference a project needs first, unless it is there; tell whether it wrote.

    The settings the installation shares first, with the currency and the name of the company
    chosen: written in the same transaction as the rest, they say the whole is there. Then
    the units of duration at 8, 40 and 20, the mapping of the actual costs empty, the default
    calendar of eight hours from Monday to Friday, the nature of provision for risks and its
    category, labelled in the language chosen — each by the interface of its module (WF-EXP-0020).
    """
    if not install_reference_settings(session, choice.currency, choice.company_name, act):
        return False
    labels = DELIVERED_LABELS[choice.language]
    install_duration_units(session, act)
    create_actual_cost_mapping(session, act)
    create_calendar(session, CalendarContent(labels.calendar, EIGHT_HOURS), act, default=True)
    nature = create_cost_type(
        session, CostTypeDraft(PROVISION_TYPE_CODE, labels.nature, PROVISION), act
    )
    category = CostCategoryDraft(
        PROVISION_CATEGORY_CODE, labels.category, PROVISION_ACCOUNTING_CODE, nature.cost_type_id
    )
    create_cost_category(session, category, act)
    return True


def _reference_again(session: Session, settings: InstallationSettings, language: str) -> None:
    """Give an installation made before the reference existed its reference; else, keep it.

    Its currency and the name of its company are those of its first run: others are said ignored,
    without their values, as the address of the administrator is.
    """
    if install_reference(session, chosen(settings, language), Act(None, utc_now())):
        logger.info("installation.reference_installed")
        return
    held = read_reference_settings(session)
    if held.currency_code != settings.currency:
        logger.warning("installation.currency_ignored")
    if held.company_name != settings.company_name:
        logger.warning("installation.company_name_ignored")


def _left_by_a_broken_run(admin: KeycloakAdmin, email: str) -> str:
    """Give the local account of the provider a run broken before its transaction left.

    The address is that of an account of the provider: a local one is taken up, one of a directory
    or of an external provider refused.
    """
    subject = admin.find_account(email)
    held = None if subject is None else admin.read_account(subject)
    if held is None or held.is_federated or held.is_relayed:
        raise InstallationRefusedError(ADDRESS_NOT_LOCAL)
    return held.subject


def _link(database: Database, installer: KeycloakAdmin, administrator: Account) -> str | None:
    """Make the link of the administrator, valid until it is used, while it has no password.

    ``installer`` is the client of the bootstrap, which alone makes such a link. The extension
    alone tells whether the account has a password, however it was set: then there is no link
    (#884). One the realm holds as no local one, or no longer holds — removed in its console —,
    is refused; so is one deactivated in Waterfall, when the link is inscribed (409), and the link
    is not given. An anonymised one never comes here: ``_bootstrap`` refused it when it read it,
    with its own reason, ``administrator_anonymized``, rather than as one removed from the realm.
    """
    made = installer.make_installation_link(administrator.subject)
    if made is NoInstallationLink.CREDENTIAL_HELD:
        return None
    if made is NoInstallationLink.NOT_LOCAL:
        raise InstallationRefusedError(ADMINISTRATOR_NOT_LOCAL)
    if made is NoInstallationLink.UNKNOWN_USER:
        raise InstallationRefusedError(ADMINISTRATOR_NOT_IN_PROVIDER)
    with database.transaction() as session:
        inscribe_password_link(session, administrator.user_id, Act(None, utc_now()))
    return made
