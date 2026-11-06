# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the bootstrap writes of the reference (US-0810/L2, WF-EXP-0020).

``install_reference``, the step of ``waterfall-api install`` that writes the reference, run on the
database of the test as the owner of the tables, as the bootstrap runs it — without Keycloak, which
the whole command asks (``test_keycloak_bootstrap.py``) —, and the settings the command reads, which
stop it before anything is asked when the currency or the name of the company lacks or is
malformed.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from installed_reference import CHOSEN, install
from sqlalchemy import func, select

from waterfall import bootstrap
from waterfall.bootstrap import Chosen, install_reference
from waterfall.core.cost_settings.interface import read_actual_cost_mapping, read_reference_settings
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.resource_settings.interface import get_duration_units
from waterfall.core.resource_settings.tables import DAYS, Calendar
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, utc_now

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

# What the bootstrap reads besides the reference: the settings of the API do not suffice.
BOOTSTRAP_ENVIRONMENT = {
    "WATERFALL_INSTALLATION_CLIENT_SECRET": "installation-secret",
    "WATERFALL_ADMIN_EMAIL": "administrateur@waterfall.test",
    "WATERFALL_DEFAULT_LANGUAGE": "fr",
    "WATERFALL_CURRENCY": "EUR",
    "WATERFALL_COMPANY_NAME": "Delmas Automatismes",
}


def counted(session: Session) -> list[int]:
    """Count the calendars, the natures and the categories."""
    return [
        session.scalar(select(func.count()).select_from(table)) or 0
        for table in (Calendar, CostType, CostCategory)
    ]


@pytest.mark.requirement("WF-EXP-0020-A")
def test_a_new_installation_holds_the_settings_the_units_and_the_mapping_delivered(
    owner: Engine, database: Database
) -> None:
    # « Sur une installation neuve, les bornes de probabilité valent 25 %, 50 % et 75 %, celles de
    # gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines » ; the currency and
    # the name chosen; the units at 8, 40 and 20; the mapping empty, at its version 1 (#2092).
    install(owner)
    with database.transaction() as session:
        settings = read_reference_settings(session)
        units = get_duration_units(session)
        mapping = read_actual_cost_mapping(session)
    assert (settings.currency_code, settings.company_name) == ("EUR", "Delmas Automatismes")
    assert settings.risk_matrix.probability_bounds == (
        Decimal("0.25"),
        Decimal("0.5"),
        Decimal("0.75"),
    )
    assert settings.risk_matrix.severity_bounds == (
        Decimal("0.01"),
        Decimal("0.05"),
        Decimal("0.1"),
    )
    thresholds = settings.index_thresholds
    assert (thresholds.cost_watch, thresholds.cost_alert) == (Decimal("0.9"), Decimal("0.8"))
    assert (thresholds.schedule_watch, thresholds.schedule_alert) == (
        Decimal("0.9"),
        Decimal("0.8"),
    )
    assert settings.max_weeks_between_reviews == 6
    assert (settings.lock_version, settings.created_by, settings.updated_by) == (1, None, None)
    assert (units.units.hours_per_day, units.units.hours_per_week) == (Decimal(8), Decimal(40))
    assert (units.units.days_per_month, units.lock_version) == (Decimal(20), 1)
    assert (mapping.lock_version, mapping.kept_columns) == (1, ())
    assert all(not column.labels for column in mapping.columns)


@pytest.mark.requirement("WF-EXP-0020-A")
@pytest.mark.parametrize(
    ("language", "labels"),
    [
        ("fr", ("Calendrier standard", "Provision pour risques", "Provision pour risques")),
        ("en", ("Standard calendar", "Risk provision", "Risk provision")),
    ],
)
def test_a_new_installation_holds_its_default_calendar_and_its_provision_labelled_in_its_language(
    owner: Engine, database: Database, language: str, labels: tuple[str, str, str]
) -> None:
    # « … et le calendrier par défaut compte huit heures du lundi au vendredi et aucune le
    # week-end » ; the nature of the kind provision for risks and its category, their labels in the
    # default language, their codes delivered.
    calendar, nature, category = labels
    install(owner, Chosen("EUR", "Delmas Automatismes", language))
    with database.transaction() as session:
        (held,) = session.scalars(select(Calendar)).all()
        (provision,) = session.scalars(select(CostType)).all()
        (kept,) = session.scalars(select(CostCategory)).all()
    assert (held.label, held.is_default, held.is_active) == (calendar, True, True)
    hours = [getattr(held, day) for day in DAYS]
    assert hours == [Decimal(8)] * 5 + [Decimal(0)] * 2
    assert (provision.code, provision.label, provision.kind) == ("PROV", nature, "provision")
    assert provision.is_active
    assert (kept.code, kept.accounting_code, kept.label) == ("PROV-001", "151000", category)
    assert (kept.cost_type_id, kept.is_active) == (provision.id, True)


@pytest.mark.requirement("WF-EXP-0020-A")
def test_a_second_run_creates_nothing_and_keeps_the_currency_and_the_name(
    owner: Engine, database: Database
) -> None:
    # « Une seconde exécution de l'installation ne crée ni compte, ni calendrier, ni nature
    # supplémentaire » : the reference neither, whatever currency and name it is given.
    install(owner)
    with database.transaction() as session:
        made = counted(session)
    with Database(owner).transaction() as session:
        again = Chosen("USD", "Autre", "en")
        assert not install_reference(session, again, Act(None, utc_now()))
    with database.transaction() as session:
        assert counted(session) == made == [1, 1, 1]
        settings = read_reference_settings(session)
    assert (settings.currency_code, settings.company_name, settings.lock_version) == (
        CHOSEN.currency,
        CHOSEN.company_name,
        1,
    )


@pytest.mark.usefixtures("platform_environment")
@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("WATERFALL_CURRENCY", None),
        ("WATERFALL_CURRENCY", "eur"),
        ("WATERFALL_CURRENCY", "EURO"),
        ("WATERFALL_CURRENCY", "E1R"),
        ("WATERFALL_CURRENCY", ""),
        ("WATERFALL_COMPANY_NAME", None),
        ("WATERFALL_COMPANY_NAME", ""),
        ("WATERFALL_COMPANY_NAME", " \t "),
        ("WATERFALL_COMPANY_NAME", "x" * 201),
    ],
)
def test_a_currency_or_a_name_missing_or_malformed_stops_the_bootstrap_before_anything(
    variable: str,
    value: str | None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The command names the variable (WF-SEC-0010), never its value, and returns 2 before it reaches
    # the database or Keycloak.
    for name, given in BOOTSTRAP_ENVIRONMENT.items():
        monkeypatch.setenv(name, given)
    if value is None:
        monkeypatch.delenv(variable)
    else:
        monkeypatch.setenv(variable, value)

    def reached(*_: object) -> int:
        pytest.fail("the bootstrap ran without its settings")

    monkeypatch.setattr(bootstrap, "install", reached)
    assert bootstrap.main(["install"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{variable}: " in captured.err
    if value and value.strip():
        assert value not in captured.err


@pytest.mark.usefixtures("platform_environment")
def test_a_currency_and_a_name_well_formed_are_read_by_the_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, given in BOOTSTRAP_ENVIRONMENT.items():
        monkeypatch.setenv(name, given)
    monkeypatch.setenv("WATERFALL_COMPANY_NAME", "x" * 200)
    read: list[tuple[str, str]] = []

    def reached(settings: bootstrap.InstallationSettings, _: object) -> int:
        read.append((settings.currency, settings.company_name))
        return 0

    monkeypatch.setattr(bootstrap, "install", reached)
    assert bootstrap.main(["install"]) == 0
    assert read == [("EUR", "x" * 200)]
