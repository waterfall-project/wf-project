# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spending projection of a project, served (``getProjectSpending``; US-2050/L1, WF-DEV-0100).

On the main structure of the revisions of a project its manager made (``workload_support``): the
amount of each line outside the provisions spread over the months of its task, by nature of cost
and by category, on the three bases of the plan of workload, the payment delays on request, the
subproject filter, and the refusals. A role works eight hours from Monday to Friday: November and
December 2026 hold 168 and 184 hours, 352 for a task from 2 November to 31 December. Every answer
is checked against the contract.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from day_indicators_support import subproject
from estimate_support import YEAR
from nodes_support import faults, refusal, set_progress
from project_rows import STAMP
from sqlalchemy import delete, insert, select, update
from workload_support import NOV_DEC, NOVEMBER, STATE_FORBIDS, Site, make_site

from waterfall.core.cost_settings.tables import CostCategory, CostType, HourlyRate
from waterfall.core.estimate.interface import remaining_of_revision
from waterfall.core.estimate.tables import EstimateLine

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

type Clock = Callable[[date], None]
D = Decimal
NOVEMBER_AND_DECEMBER = ("2026-11", "2026-12")


@pytest.fixture
def site(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Site:
    """Give a platform, a project its manager made, its revision opened, and a role to load."""
    return make_site(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the projection is read on, and the worker marks on."""

    def set_day(day: date) -> None:
        now = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
        monkeypatch.setattr("waterfall.api.spending.utc_now", lambda: now)
        monkeypatch.setattr("nodes_support.utc_now", lambda: now)

    return set_day


def asked(site: Site, basis: str, **query: Any) -> Any:
    """Ask for the projection on a basis; give the answer."""
    text = "&".join(f"{name}={value}" for name, value in {"basis": basis, **query}.items())
    return site.api.get(f"{site.path}/spending?{text}", headers=site.stage.manager.headers)


def projection(site: Site, basis: str, **query: Any) -> dict[str, Any]:
    """Ask for a projection that must be given; give it."""
    answer = asked(site, basis, **query)
    assert answer.status_code == 200, answer.text
    return answer.json()


def months(entries: list[dict[str, str]]) -> list[tuple[str, str]]:
    """Give the months of an amount with their amounts."""
    return [(each["month"], each["amount"]) for each in entries]


def natures(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Give the natures of a projection by label."""
    return {each["label"]: each for each in body["cost_types"]}


def referenced_with(site: Site) -> None:
    """Give a task from 2 November to 31 December a line of 1 200 of material; reference it."""
    site.material(site.task("Câblage", NOV_DEC), "1200")
    site.referenced()


def unrate(site: Site) -> None:
    """Withdraw the rate of the category of labour for this year from the reference.

    Before the marking: a marked revision keeps its rates, a trigger forbids deleting them.
    """
    with site.stage.owner.begin() as connection:
        connection.execute(
            delete(HourlyRate).where(
                HourlyRate.cost_category_id == site.costs.labour, HourlyRate.year == YEAR
            )
        )


# --- The sentences of the Vérif -------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_line_of_1200_on_a_task_of_two_months_is_on_both_by_the_hours_worked_of_the_task(
    site: Site, clock: Clock
) -> None:
    # « Une ligne de 1 200 portée par une tâche qui couvre exactement deux mois civils apparaît sur
    # ces deux mois, au prorata des heures travaillées de la tâche dans chacun. » 168 and 184 hours
    # of 352: 572.73 and 627.27. The nature and the category that carry it, and the context.
    clock(date(2026, 10, 15))
    referenced_with(site)
    body = projection(site, "reference_budget")
    assert months(body["monthly_totals"]) == [("2026-11", "572.73"), ("2026-12", "627.27")]
    assert body["total"] == "1200.00"
    (nature,) = body["cost_types"]
    assert (nature["label"], nature["total"]) == ("Matériel", "1200.00")
    assert months(nature["months"]) == months(body["monthly_totals"])
    (category,) = nature["categories"]
    assert (category["cost_category_id"], category["label"], category["total"]) == (
        str(site.costs.material),
        "Matériel électrique",
        "1200.00",
    )
    assert months(category["months"]) == months(body["monthly_totals"])
    assert body["basis"] == "reference_budget"
    assert body["payment_delays"] is False
    assert body["context"]["revision_status"] == "marked"
    assert body["context"]["scope"] == "project"
    assert body["context"]["is_stored"] is False


@pytest.mark.requirement("WF-DEV-0100-A")
def test_with_a_payment_delay_of_30_days_the_disbursements_are_shifted_by_as_much(
    site: Site, clock: Clock
) -> None:
    # « Avec un délai de paiement de trente jours, en mode décaissement, sa dépense est décalée
    # d'autant. » The line of 1 200 paid 30 days after: what the task had spent 30 days before the
    # end of each month, half on 1 December, the whole on 1 January.
    clock(date(2026, 10, 15))
    site.material(site.task("Câblage", NOV_DEC), "1200", payment_delay_days=30)
    site.referenced()
    plain = projection(site, "reference_budget")
    shifted = projection(site, "reference_budget", payment_delays="true")
    assert shifted["payment_delays"] is True
    assert months(shifted["monthly_totals"]) == [("2026-12", "600.00"), ("2027-01", "600.00")]
    assert months(plain["monthly_totals"]) == [("2026-11", "572.73"), ("2026-12", "627.27")]
    assert shifted["total"] == plain["total"] == "1200.00"


@pytest.mark.requirement("WF-DEV-0100-A")
def test_on_the_remaining_the_total_is_the_remaining_to_commit_and_no_month_precedes_the_day(
    site: Site, clock: Clock
) -> None:
    # « Sur la base du reste à engager, le total de la projection égale le reste à engager du
    # projet hors provisions (WF-RAE-0010), et aucune colonne ne précède le mois de la date de
    # calcul. » Calculated on Monday 16 November: the 1 200 of the material are spread over the
    # 80 hours left of November and the 184 of December, the 22 880 of the labour over the same;
    # the task Repérage, over since October, falls whole on November, the month of the day.
    clock(date(2026, 10, 15))
    site.material(site.task("Câblage", NOV_DEC), "1200")
    site.labour(site.task("Pose", NOV_DEC), "352")
    site.material(site.task("Repérage", ("2026-10-05", "2026-10-30")), "300")
    site.referenced()
    clock(date(2026, 11, 16))
    body = projection(site, "current_remaining")
    assert [month for month, _ in months(body["monthly_totals"])] == list(NOVEMBER_AND_DECEMBER)
    assert body["context"]["revision_status"] == "draft"
    assert body["context"]["computed_at"] == "2026-11-16T09:00:00Z"
    project = UUID(site.stage.project["project_id"])
    with site.stage.database.transaction() as session:
        revision = UUID(_current(site)["revision_id"])
        left = remaining_of_revision(session, project, revision).total
    assert D(body["total"]) == left == D("24380.00")
    material = natures(body)["Matériel"]
    # The material of the cabling: 80 / 264 of 1 200 in November, with the 300 of the task over.
    assert months(material["months"]) == [("2026-11", "663.64"), ("2026-12", "836.36")]
    assert months(natures(body)["Main-d'œuvre"]["months"]) == [
        ("2026-11", "6933.33"),
        ("2026-12", "15946.67"),
    ]


def _current(site: Site) -> dict[str, Any]:
    """Give the current revision of the project of the site."""
    answer = site.api.get(f"{site.path}/revisions", headers=site.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return next(each for each in answer.json()["items"] if each["status"] == "draft")


@pytest.mark.requirement("WF-DEV-0100-A")
def test_on_the_remaining_a_completed_task_is_not_projected(site: Site, clock: Clock) -> None:
    # « le reste à engager de chaque ligne » : a line of a task completed has none (WF-RAE-0010).
    clock(date(2026, 10, 15))
    site.material(site.task("Câblage", NOV_DEC), "1200")
    site.material(site.task("Repérage", NOVEMBER), "400")
    current = site.referenced()
    done = next(
        each
        for each in current.items()
        if each["kind"] == "task" and each["task"]["label"] == "Repérage"
    )
    set_progress(site.stage, done["node_id"], "completed", date(2026, 11, 10))
    clock(date(2026, 11, 3))
    body = projection(site, "current_remaining")
    assert body["total"] == "1200.00"
    reference = projection(site, "reference_budget")
    assert reference["total"] == "1600.00"


@pytest.mark.requirement("WF-DEV-0100-A")
def test_on_the_reference_of_a_project_in_progress_the_months_before_the_day_are_shown(
    site: Site, clock: Clock
) -> None:
    # « Sur la base de la révision de référence d'un projet en cours, la projection présente aussi
    # les mois antérieurs à la date de calcul. » Read on 15 December, the reference still has
    # November, which the remaining of the same day has not.
    clock(date(2026, 10, 15))
    referenced_with(site)
    clock(date(2026, 12, 15))
    reference = projection(site, "reference_budget")
    assert [month for month, _ in months(reference["monthly_totals"])] == list(
        NOVEMBER_AND_DECEMBER
    )
    remaining = projection(site, "current_remaining")
    assert [month for month, _ in months(remaining["monthly_totals"])] == ["2026-12"]


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_month_between_two_loaded_months_is_in_the_total_at_nought_to_the_cent(
    site: Site, clock: Clock
) -> None:
    # « Le total de chaque mois » runs from the first month loaded to the last, none left out: a
    # December that no line loads, between a task of November and one of January, is at `0.00` as
    # every amount is written, and is in no nature (#3096).
    clock(date(2026, 10, 15))
    site.material(site.task("Câblage", NOVEMBER), "600")
    site.material(site.task("Essais", ("2027-01-04", "2027-01-29")), "400")
    site.referenced()
    body = projection(site, "reference_budget")
    assert months(body["monthly_totals"]) == [
        ("2026-11", "600.00"),
        ("2026-12", "0.00"),
        ("2027-01", "400.00"),
    ]
    (nature,) = body["cost_types"]
    assert [month for month, _ in months(nature["months"])] == ["2026-11", "2027-01"]


@pytest.mark.requirement("WF-DEV-0100-A")
def test_the_categories_of_a_nature_are_in_the_order_of_their_code_not_of_their_creation(
    site: Site, clock: Clock
) -> None:
    # « les catégories dans l'ordre du référentiel » : two categories of the nature of the material,
    # created in the reverse order of their codes, are listed by code.
    clock(date(2026, 10, 15))
    with site.stage.owner.begin() as connection:
        nature = connection.execute(
            select(CostCategory.cost_type_id).where(CostCategory.id == site.costs.material)
        ).scalar_one()
    made: dict[str, UUID] = {}
    for code in ("MAT-009", "MAT-002"):
        made[code] = uuid4()
        with site.stage.owner.begin() as connection:
            connection.execute(
                insert(CostCategory).values(
                    id=made[code],
                    code=code,
                    label=f"Catégorie {code}",
                    accounting_code=f"606{code[-3:]}",
                    cost_type_id=nature,
                    is_active=True,
                    **STAMP,
                )
            )
    task = site.task("Câblage", NOV_DEC)
    site.material(task, "100", cost_category_id=str(made["MAT-009"]))
    site.material(task, "200", cost_category_id=str(made["MAT-002"]))
    site.material(task, "300")
    site.referenced()
    (nature_read,) = projection(site, "reference_budget")["cost_types"]
    assert [each["label"] for each in nature_read["categories"]] == [
        "Matériel électrique",
        "Catégorie MAT-002",
        "Catégorie MAT-009",
    ]


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_provision_line_is_under_no_nature(site: Site, clock: Clock) -> None:
    # « Une ligne de provision n'y figure sous aucune nature. » The line of 250, of the category of
    # the provision, is neither in a nature nor in a total, on the reference as on the remaining.
    clock(date(2026, 10, 15))
    task = site.task("Câblage", NOV_DEC)
    site.material(task, "600")
    provision = site.material(task, "250")
    with site.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(provision))
            .values(cost_category_id=site.costs.provision)
        )
    site.referenced()
    for basis in ("reference_budget", "current_remaining"):
        body = projection(site, basis)
        assert body["total"] == "600.00", basis
        assert [each["label"] for each in body["cost_types"]] == ["Matériel"], basis
        with site.stage.owner.begin() as connection:
            kinds = connection.execute(
                select(CostType.kind).where(
                    CostType.id.in_([UUID(each["cost_type_id"]) for each in body["cost_types"]])
                )
            ).scalars()
            assert "provision" not in set(kinds), basis


@pytest.mark.requirement("WF-DEV-0100-A")
def test_the_total_of_each_month_is_the_sum_of_its_natures_and_that_of_each_nature_its_categories(
    site: Site, clock: Clock
) -> None:
    # « Le total de chaque mois égale la somme des natures de ce mois, et celui de chaque nature la
    # somme de ses catégories. » A line of labour and one of material over two months, rounded by
    # part: every amount is a sum of parts already rounded, whatever the rounding of a total would
    # have been. Each nature and each category lists only the months it loads (#3096).
    clock(date(2026, 10, 15))
    site.material(site.task("Câblage", NOV_DEC), "1000.01")
    site.labour(site.task("Pose", NOVEMBER), "100")
    site.referenced()
    body = projection(site, "reference_budget")
    assert len(body["cost_types"]) == 2
    by_month: dict[str, D] = {}
    for nature in body["cost_types"]:
        categories = nature["categories"]
        assert D(nature["total"]) == sum(D(each["total"]) for each in categories)
        for month, amount in months(nature["months"]):
            held = [dict(months(each["months"])).get(month, "0") for each in categories]
            assert D(amount) == sum(D(each) for each in held), (nature["label"], month)
            by_month[month] = by_month.get(month, D(0)) + D(amount)
        assert D(nature["total"]) == sum(D(amount) for _, amount in months(nature["months"]))
    assert {month: D(amount) for month, amount in months(body["monthly_totals"])} == by_month
    assert D(body["total"]) == sum(by_month.values())
    # The labour is on November only, a month the material loads too: December is the material's.
    assert months(natures(body)["Main-d'œuvre"]["months"]) == [("2026-11", "6500.00")]
    assert [month for month, _ in months(natures(body)["Matériel"]["months"])] == [
        "2026-11",
        "2026-12",
    ]


@pytest.mark.requirement("WF-DEV-0100-A")
def test_the_natures_are_in_the_order_of_the_reference_data_and_those_without_amount_are_left(
    site: Site, clock: Clock
) -> None:
    # « les natures de coût dans l'ordre du référentiel » : by code, then by identifier, as the
    # reference lists them; a nature that carries nothing, here the provision's, is not listed.
    clock(date(2026, 10, 15))
    task = site.task("Câblage", NOV_DEC)
    site.material(task, "600")
    site.labour(task, "10")
    site.referenced()
    body = projection(site, "reference_budget")
    with site.stage.owner.begin() as connection:
        rows = connection.execute(
            select(CostType.id).order_by(CostType.code, CostType.id)
        ).scalars()
        order = [str(each) for each in rows]
    held = [each["cost_type_id"] for each in body["cost_types"]]
    assert held == [each for each in order if each in held]
    assert len(held) == 2


# --- The filter by subproject ---------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0100-A")
def test_the_projection_is_restricted_to_a_subproject_or_to_what_falls_under_none(
    site: Site, clock: Clock
) -> None:
    # « La projection se filtre par sous-projet. » (WF-IND-0020) The lines of a subproject alone,
    # those of none under `unassigned`, the project the two; the scope is named in the context.
    clock(date(2026, 10, 15))
    named = subproject(site.api, site.stage, "SP-1", "Poste de commande")
    task = site.task("Câblage", NOV_DEC)
    site.material(task, "1200", subproject_id=named)
    site.material(task, "300")
    site.referenced()
    whole = projection(site, "reference_budget")
    inside = projection(site, "reference_budget", subproject_id=named)
    outside = projection(site, "reference_budget", subproject_id="unassigned")
    assert (whole["total"], inside["total"], outside["total"]) == ("1500.00", "1200.00", "300.00")
    assert (whole["context"]["scope"], inside["context"]["scope"]) == ("project", named)
    assert outside["context"]["scope"] == "unassigned"
    assert months(inside["monthly_totals"]) == [("2026-11", "572.73"), ("2026-12", "627.27")]
    other = subproject(site.api, site.stage, "SP-2", "Essais")
    nothing = projection(site, "reference_budget", subproject_id=other)
    assert (nothing["total"], nothing["monthly_totals"], nothing["cost_types"]) == ("0.00", [], [])


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_subproject_the_project_does_not_have_is_refused_on_its_parameter(site: Site) -> None:
    # « un sous-projet que le projet n'a pas, ou un identifiant mal formé » (contract): 422, the
    # parameter designated by `UNKNOWN_SUBPROJECT`.
    referenced_with(site)
    # Only the hyphenated form is an identifier of the contract: `UUID` also reads the others.
    known = str(subproject(site.api, site.stage, "SP-1", "Poste de commande"))
    forms = (
        known.replace("-", ""),
        "{" + known + "}",
        "urn:uuid:" + known,
        str(uuid4()),
        "not-an-identifier",
    )
    for bad in forms:
        answer = asked(site, "reference_budget", subproject_id=bad)
        assert faults(answer) == [("/query/subproject_id", "UNKNOWN_SUBPROJECT", {})], bad
        assert answer.status_code == 422


# --- The bases and their refusals, as the plan of workload ----------------------------------------


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_project_without_a_reference_lacks_the_basis_of_the_reference_and_names_its_state(
    site: Site,
) -> None:
    # Refused as the plan of workload is: 409, the state of the project named with its enumeration.
    site.material(site.task("Câblage", NOV_DEC), "1200")
    assert refusal(asked(site, "reference_budget")) == (
        409,
        STATE_FORBIDS,
        {"state": "pricing", "state_enum": "ProjectState"},
    )
    assert asked(site, "current_remaining").status_code == 200


@pytest.mark.requirement("WF-DEV-0100-A")
def test_the_remaining_of_a_marked_revision_needs_a_revision_that_is_marked(site: Site) -> None:
    # `marked_remaining` without a marked revision — absent, unknown, or the revision in progress —
    # is refused on `/query/revision_id`, no empty projection in its place.
    referenced_with(site)
    current = _current(site)["revision_id"]
    for query in ({}, {"revision_id": uuid4()}, {"revision_id": current}):
        answer = asked(site, "marked_remaining", **query)
        assert faults(answer) == [("/query/revision_id", "VALIDATION_FAILED", {})], query
        assert answer.status_code == 422


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_marked_revision_is_computed_when_read_on_its_own_tasks_at_its_marking_date(
    site: Site, clock: Clock
) -> None:
    # Propre à l'US : « pour une révision marquée, la projection est calculée à la lecture, non
    # conservée au marquage ». Marked on 15 October, its remaining is spread from that day over the
    # whole of its task; the current revision then moves the task, and the marked one is read as
    # it was, whenever it is read: nothing is stored.
    clock(date(2026, 10, 15))
    site.material(site.task("Câblage", NOV_DEC), "1200")
    current = site.referenced()
    marked = site.tree.revision["revision_id"]
    moved = next(each for each in current.items() if each["kind"] == "task")
    delay = {"start": {"date": "2027-01-04"}, "finish": {"date": "2027-01-29"}}
    current.changed(moved, scheduling_mode="manual", **delay)
    clock(date(2031, 6, 1))
    body = projection(site, "marked_remaining", revision_id=marked)
    assert months(body["monthly_totals"]) == [("2026-11", "572.73"), ("2026-12", "627.27")]
    context = body["context"]
    assert (context["revision_id"], context["revision_status"]) == (marked, "marked")
    assert context["computed_at"] == "2026-10-15T09:00:00Z"
    assert context["is_stored"] is False
    now = projection(site, "current_remaining")
    assert [month for month, _ in months(now["monthly_totals"])] == ["2031-06"]


# --- The rates ------------------------------------------------------------------------------------


def _refused_for_rates(site: Site, basis: str, **query: Any) -> None:
    """Check the projection refused 422 `HOURLY_RATE_MISSING`, the labour category named once."""
    answer = asked(site, basis, **query)
    assert answer.status_code == 422, answer.text
    problem = answer.json()
    assert problem["code"] == "HOURLY_RATE_MISSING"
    assert problem.get("fields") is None
    (named,) = problem["params"]["missing_rates"]
    assert (named["cost_category_id"], named["year"]) == (str(site.costs.labour), YEAR)
    assert named["label"] == "Ingénierie"


@pytest.mark.requirement("WF-DEV-0010-A")
@pytest.mark.parametrize(
    ("basis", "case"),
    [
        (basis, case)
        for basis in ("reference_budget", "marked_remaining", "current_remaining")
        for case in ("plain", "outside_subproject", "two_lines")
    ]
    # On the others the task is set completed on the revision in progress, after the marking.
    + [("current_remaining", "nothing_left")],
)
def test_a_labour_category_without_a_rate_refuses_the_projection_and_names_it(
    site: Site, clock: Clock, basis: str, case: str
) -> None:
    # « Le refus énumère les catégories de coût sans taux horaire pour l'année de référence. »
    # (#3565) The projection has meaning only complete, on any basis: the rate of the engineering
    # withdrawn from the reference (the marking keeps its own, which a trigger forbids touching), a
    # line of labour without one is refused 422 `HOURLY_RATE_MISSING`, without field, the category
    # and its year named once. Every line of the revision is looked at, those out of the subproject
    # filter and those with nothing left too.
    clock(date(2026, 10, 15))
    query: dict[str, Any] = {}
    if case == "outside_subproject":
        named = subproject(site.api, site.stage, "SP-1", "Poste de commande")
        site.material(site.task("Câblage", NOV_DEC), "1200", subproject_id=named)
        site.labour(site.task("Pose", NOV_DEC), "100")
        query["subproject_id"] = named
    else:
        site.material(site.task("Câblage", NOV_DEC), "1200")
        site.labour(site.task("Pose", NOV_DEC), "100")
    if case == "two_lines":
        site.labour(site.task("Réglage", NOV_DEC), "50")
    marked = site.tree.revision["revision_id"]
    unrate(site)
    current = site.referenced()
    if basis == "marked_remaining":
        query["revision_id"] = marked
    if case == "nothing_left":
        task = next(
            each
            for each in current.items()
            if each["kind"] == "task" and each["task"]["label"] == "Pose"
        )
        before = site.plan("current_remaining")["monthly_totals"]
        set_progress(site.stage, task["node_id"], "completed", date(2026, 11, 10))
        clock(date(2026, 11, 12))
        # No hour is left on the line, by the workload: the refusal comes from the rate withdrawn
        # alone.
        assert before != []
        assert site.plan("current_remaining")["monthly_totals"] == []
    _refused_for_rates(site, basis, **query)


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_project_without_a_line_has_an_empty_projection_at_nought(
    site: Site, clock: Clock
) -> None:
    clock(date(2026, 10, 15))
    body = projection(site, "current_remaining")
    assert (body["total"], body["monthly_totals"], body["cost_types"]) == ("0.00", [], [])
