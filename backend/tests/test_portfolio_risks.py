# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks of the portfolio, read on the service at a past date (``getPortfolioRisks``; US-2730).

The projects of the fabrics (``portfolio_support``): the documents ``portfolio_risks`` and
``remaining`` their markings kept are set to the risks and the coverages of the sentence under test,
as a marking of EP-08 would have kept them, and the reserve the references conserve is written
beside them; the view is then read at 3 June 2026, which reads what the markings kept. The current
day, on real risks, is read by ``test_portfolio_risks_day``. Every answer is validated against the
contract by the client of the tests.
"""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from portfolio_support import OFFER, READ_ON, REVIEW, Portfolio, portfolio
from project_rows import risk_row
from projects_support import Person, Scene, contribute, person
from projects_support import scene as make_scene
from risks_support import share_row
from sqlalchemy import insert, text, update

from waterfall.core.cost_settings.interface import (
    SettingsChange,
    read_reference_settings,
    write_reference_settings,
)
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.risks.tables import Risk, RiskReferenceShare
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

RISKS = "/api/v1/portfolio/risks"
ALL = "states=in_progress,pricing,completed"
AT = f"as_of={READ_ON}"
D = Decimal
RUNNING, OFFER_LABEL, COMPLETED = (
    "Rénovation de la ligne 3",
    "Extension du dépôt",
    "Poste de livraison",
)


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def risk(number: int, label: str, state: str, amounts: tuple[str, str, str]) -> dict[str, Any]:
    """Give a risk as the document of a marking keeps it; its identifier is its number.

    ``amounts`` are its probability, its severity and its provision.
    """
    probability, severity, provision = amounts
    occurred = state == "occurred"
    return {
        "risk_id": str(UUID(int=number)),
        "label": label,
        "probability": probability,
        "severity": severity,
        "provision_amount": provision,
        "state": state,
        "occurrence_cost": severity if occurred else None,
        "occurred_reestimated_amount": severity if occurred else None,
    }


def keep(owner: Engine, revision_id: UUID, kind: str, document: dict[str, Any]) -> None:
    """Set a document a marking kept to the one of the sentence under test, as a superuser.

    A marked revision is immutable: the trigger that says so is set aside. The document must exist.
    """
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        done = connection.execute(
            update(RevisionIndicator)
            .where(
                RevisionIndicator.revision_id == revision_id,
                RevisionIndicator.kind == kind,
                RevisionIndicator.scope == "project",
            )
            .values(document=document)
        )
    assert done.rowcount == 1, f"no document {kind} kept by {revision_id}"


def conserve(owner: Engine, project_id: UUID, reference_id: UUID, number: int, share: str) -> None:
    """Write the share a risk bears in the reference of a project: its reserve, the sum of them."""
    identifier = UUID(int=10_000 + number)
    with owner.begin() as connection:
        connection.execute(insert(Risk).values(**risk_row(project_id, id=identifier)))
        row = share_row(project_id, identifier, reference_id, provision_amount=D(share))
        connection.execute(insert(RiskReferenceShare).values(**row))


def coverage_of(reserve: str, left: str, cost: str, reestimated: str) -> dict[str, str]:
    """Give the five figures of a coverage kept."""
    variance = D(reserve) - (D(left) + D(cost))
    return {
        "reserve": reserve,
        "remaining_provisions": left,
        "occurred_cost": cost,
        "occurred_reestimated": reestimated,
        "coverage_variance": f"{variance:.2f}",
    }


def kept_remaining(owner: Engine, revision_id: UUID, figures: dict[str, str]) -> None:
    """Set the coverage of the document ``remaining`` a marking kept, its other keys unchanged."""
    with owner.connect() as connection:
        held = connection.scalar(
            text(
                "SELECT document FROM revision_indicator "
                "WHERE revision_id = :revision AND kind = 'remaining' AND scope = 'project'"
            ),
            {"revision": revision_id},
        )
    assert held is not None
    keep(owner, revision_id, "remaining", {**held, "coverage": figures})


def plant(owner: Engine, fabrics: Portfolio) -> None:
    """Keep the risks and the coverages of the three projects of the sentences below.

    The project In progress holds a risk identified (provision 60), one occurred (40, its cost at
    occurrence 300, its lines re-estimated to 350) and one dismissed (25), on a base of 1 000; the
    offer one risk identified, severity 500 at 50 %, provision 250, on its estimate of 2 000; the
    project Completed one identified, 20 on a base of 500. The references conserve 850 and 100.
    """
    running = fabrics.in_progress.marked[REVIEW][0]
    keep(
        owner,
        running,
        "portfolio_risks",
        {
            "base": "1000.00",
            "risks": [
                risk(1, "Retard du fournisseur", "identified", ("0.3000", "200.00", "60.00")),
                risk(2, "Panne de la grue", "occurred", ("0.4000", "300.00", "40.00")),
                risk(3, "Gel des sols", "dismissed", ("0.2000", "50.00", "25.00")),
            ],
        },
    )
    keep(
        owner,
        fabrics.offer.marked[OFFER][0],
        "portfolio_risks",
        {
            "base": "2000.00",
            "risks": [risk(4, "Retard de livraison", "identified", ("0.5000", "500.00", "250.00"))],
        },
    )
    completed = fabrics.completed.marked[REVIEW][0]
    keep(
        owner,
        completed,
        "portfolio_risks",
        {
            "base": "500.00",
            "risks": [risk(5, "Défaut de la dalle", "identified", ("0.2000", "100.00", "20.00"))],
        },
    )
    kept_remaining(owner, running, coverage_of("0.00", "60.00", "300.00", "350.00"))
    kept_remaining(owner, completed, coverage_of("0.00", "20.00", "0.00", "0.00"))
    for project, number, share in (
        (fabrics.in_progress, 1, "850.00"),
        (fabrics.completed, 2, "100.00"),
    ):
        conserve(owner, project.project_id, project.marked[OFFER][0], number, share)


def read(api: ContractClient, who: Person, query: str = "") -> dict[str, Any]:
    """Read the risks as the person given does; the contract judges the answer."""
    answer = api.get(f"{RISKS}{query}", headers=who.headers)
    assert answer.status_code == 200, answer.text
    body: dict[str, Any] = answer.json()
    return body


def bounds(stage: Scene, probability: tuple[str, ...], severity: tuple[str, ...]) -> None:
    """Set the bounds of the matrix, as ``updateReferenceSettings`` does, its zones as they were."""
    with stage.database.transaction() as session:
        held = read_reference_settings(session)
        matrix = replace(
            held.risk_matrix,
            probability_bounds=tuple(D(each) for each in probability),
            severity_bounds=tuple(D(each) for each in severity),
        )
        change = SettingsChange(risk_matrix=matrix)
        write_reference_settings(session, change, held.lock_version, Act(None, utc_now()))


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_total_is_the_sum_of_the_identified_provisions_an_offer_in_pricing_counting_unweighted(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # « Le total des provisions identifiées égale la somme des provisions des risques identifiés des
    # projets du périmètre. » : 60 of the project In progress, 250 of the offer — at 40 % it would
    # weigh 100, and counts for 250 —, 20 of the one Completed in the period: 330. The occurred
    # (40) and the dismissed (25) are no provision identified.
    plant(owner, fabrics)
    body = read(api, fabrics.stage.reader, f"?{AT}&{ALL}")
    assert body["scope"]["project_count"] == 3
    assert body["scope"]["states"] == ["in_progress", "pricing", "completed"]
    assert body["identified_total"] == "330.00"
    # By default, the projects In progress alone: the offer and the completed project stay out of
    # the total, as they stay out of the count.
    default = read(api, fabrics.stage.reader, f"?{AT}")
    assert default["scope"]["project_count"] == 1
    assert default["identified_total"] == "60.00"
    only = read(api, fabrics.stage.reader, f"?{AT}&states=pricing")
    assert only["identified_total"] == "250.00"
    assert [each["project_label"] for each in only["heaviest"]] == [OFFER_LABEL]


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_the_heaviest_are_the_risks_of_greatest_provision_each_with_its_project_and_can_open(
    api: ContractClient, fabrics: Portfolio, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # Propre à l'US : « les risques les plus lourds sont les dix premiers par provision, tous
    # projets confondus, chacun avec son projet et can_open » : the three identified risks, the
    # heavier first; the reader who holds ``all_projects_read`` opens every project, an account
    # that holds the permission of the view and contributes to one project opens that one only.
    plant(owner, fabrics)
    expected = [
        (str(UUID(int=4)), OFFER_LABEL, "250.00"),
        (str(UUID(int=1)), RUNNING, "60.00"),
        (str(UUID(int=5)), COMPLETED, "20.00"),
    ]
    every = read(api, fabrics.stage.reader, f"?{AT}&{ALL}")
    assert [
        (each["risk_id"], each["project_label"], each["provision_amount"])
        for each in every["heaviest"]
    ] == expected
    assert {each["can_open"] for each in every["heaviest"]} == {True}
    assert every["heaviest"][1]["project_id"] == str(fabrics.in_progress.project_id)
    assert every["heaviest"][1]["label"] == "Retard du fournisseur"
    narrow = person(database, realm, "portfolio_risks.read", name="Zoé")
    contribute(database, str(fabrics.in_progress.project_id), narrow, "contributor")
    body = read(api, narrow, f"?{AT}&{ALL}")
    assert {each["project_label"]: each["can_open"] for each in body["heaviest"]} == {
        OFFER_LABEL: False,
        RUNNING: True,
        COMPLETED: False,
    }
    # The matrix names the project of each point and says the same.
    assert {each["project_label"]: each["can_open"] for each in body["matrix"]["points"]} == {
        OFFER_LABEL: False,
        RUNNING: True,
        COMPLETED: False,
    }
    # Every risk stays listed to the one who cannot open its project: only the link is withheld.
    assert body["identified_total"] == every["identified_total"]


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_matrix_counts_each_identified_risk_once_in_the_cell_of_its_levels_on_its_own_base(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # « La matrice compte chaque risque identifié une fois. » : three identified risks, three
    # cells; the offer's, 500 at 50 %, is at 25 % of its base of 2 000 — not at 50 % of the 1 000
    # of the other projects —; the occurred and the dismissed are counted in no cell.
    plant(owner, fabrics)
    matrix = read(api, fabrics.stage.reader, f"?{AT}&{ALL}")["matrix"]
    cells = {
        (each["probability_level"], each["severity_level"]): (each["count"], each["zone"])
        for each in matrix["cells"]
    }
    assert sum(count for count, _ in cells.values()) == 3
    assert cells[(2, 4)] == (1, "watch")
    assert cells[(3, 4)] == (1, "alert")
    assert cells[(1, 4)] == (1, "watch")
    assert [each["state"] for each in matrix["points"]] == ["identified"] * 3
    by_label = {each["label"]: each for each in matrix["points"]}
    offer = by_label["Retard de livraison"]
    assert (offer["severity_amount"], offer["provision_amount"], offer["zone"]) == (
        "500.00",
        "250.00",
        "alert",
    )
    assert offer["severity_ratio"] == {"is_computable": True, "value": "0.25", "reason": None}
    assert offer["probability"] == "0.5"
    assert offer["project_label"] == OFFER_LABEL
    # The totals count every risk of the documents once, each in its state, the reserve beside.
    assert matrix["totals"] == {
        "identified": "330.00",
        "occurred": "40.00",
        "dismissed": "25.00",
        "total": "395.00",
        "reserve": "950.00",
    }
    assert [each["level"] for each in matrix["probability_levels"]] == [1, 2, 3, 4]
    assert [(each["lower"], each["upper"]) for each in matrix["severity_levels"]][-1] == (
        "0.1",
        None,
    )


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_matrix_is_classed_on_the_bounds_of_the_day_not_on_those_of_the_marking(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # « … la vue classe chaque risque à la lecture, sur les bornes de ce jour » (EP-11, « Ce que le
    # cadrage décide ») : the bounds of probability moved to 10, 20 and 30 % put the risk of the
    # project In progress, at 30 %, at the fourth level instead of the second, the document kept
    # unchanged.
    plant(owner, fabrics)
    before = read(api, fabrics.stage.reader, f"?{AT}")["matrix"]
    assert {
        (each["probability_level"], each["severity_level"])
        for each in before["cells"]
        if each["count"]
    } == {(2, 4)}
    bounds(fabrics.stage, ("0.1", "0.2", "0.3"), ("0.01", "0.05", "0.1"))
    after = read(api, fabrics.stage.reader, f"?{AT}")["matrix"]
    assert {
        (each["probability_level"], each["severity_level"])
        for each in after["cells"]
        if each["count"]
    } == {(4, 4)}
    assert [each["upper"] for each in after["probability_levels"]] == ["0.1", "0.2", "0.3", None]
    assert after["points"][0]["probability"] == before["points"][0]["probability"]


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_reserve_and_the_variance_are_the_sums_of_the_projects_in_progress_and_completed(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # « La réserve agrégée est la somme des réserves des projets en cours et terminés du périmètre,
    # et l'écart de couverture agrégé la différence des sommes. » : reserves 850 and 100, provisions
    # left 60 and 20, costs at occurrence 300 and 0: 950, 80, 300, and 950 - (80 + 300) = 570. The
    # offer In pricing is in the scope and adds nothing: no reference, no reserve.
    plant(owner, fabrics)
    body = read(api, fabrics.stage.reader, f"?{AT}&{ALL}")
    assert body["coverage"] == {
        "reserve": "950.00",
        "remaining_provisions": "80.00",
        "occurred_cost": "300.00",
        "occurred_reestimated": "350.00",
        "coverage_variance": "570.00",
    }
    assert body["matrix"]["totals"]["reserve"] == body["coverage"]["reserve"]
    # The scope without the offer gives the same coverage.
    without = read(api, fabrics.stage.reader, f"?{AT}&states=in_progress,completed")
    assert without["coverage"] == body["coverage"]


@pytest.mark.requirement("WF-PTF-0090-A")
def test_a_project_completed_in_the_period_counts_in_the_reserve_and_the_variance(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # « Un projet terminé inclus dans le périmètre compte dans la réserve agrégée et dans l'écart de
    # couverture agrégé. » : the project completed on 15 April, in the default period of the 3 June,
    # adds its reserve of 100 and its variance of 80 to the 850 and the 490 of the project In
    # progress; asked for the projects In progress alone, the aggregates are theirs; a period that
    # ends before the completion leaves it out.
    plant(owner, fabrics)
    asked = f"?{AT}&states=in_progress,completed"
    both = read(api, fabrics.stage.reader, asked)["coverage"]
    running = read(api, fabrics.stage.reader, f"?{AT}")["coverage"]
    assert (running["reserve"], running["coverage_variance"]) == ("850.00", "490.00")
    assert (both["reserve"], both["coverage_variance"]) == ("950.00", "570.00")
    early = read(api, fabrics.stage.reader, f"{asked}&from=2026-01-01&to=2026-04-01")
    assert early["coverage"] == running
    assert early["scope"]["project_count"] == 1
    assert early["scope"]["from"] == "2026-01-01"


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_the_reestimated_amount_is_the_sum_of_the_lines_apart_from_the_cost_of_the_occurred(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # Propre à l'US : « la couverture rend, à côté du coût des survenus, la somme des réestimés des
    # lignes qui en sont issues » (#2002) : the project whose occurred risk cost 300 has its lines
    # re-estimated to 350; the coverage says 300 and 350, and its variance counts the 300.
    plant(owner, fabrics)
    coverage = read(api, fabrics.stage.reader, f"?{AT}")["coverage"]
    assert coverage["occurred_cost"] == "300.00"
    assert coverage["occurred_reestimated"] == "350.00"
    assert coverage["coverage_variance"] == f"{D('850.00') - D('60.00') - D('300.00')}"


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_at_a_past_date_a_coverage_the_marking_kept_incomplete_is_computed_on_the_revision(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # Propre à l'US : « à une date passée, la vue lit les risques que les révisions marquées ont
    # conservés » : a marking whose coverage lacks a figure is computed on the revision, as the
    # register of the project does — here nothing left, nothing occurred, the reserve conserved —,
    # and a revision that kept no document ``remaining`` adds none (the offer is out of it).
    plant(owner, fabrics)
    running = fabrics.in_progress.marked[REVIEW][0]
    kept_remaining(owner, running, {"reserve": "1.00", "remaining_provisions": "60.00"})
    body = read(api, fabrics.stage.reader, f"?{AT}")
    assert body["coverage"]["reserve"] == "850.00"
    assert body["coverage"]["occurred_cost"] == "0.00"
    assert body["coverage"]["coverage_variance"] == "850.00"
    # Every one of the documents is read: the identified total is still the kept one.
    assert body["identified_total"] == "60.00"


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_a_scope_with_no_risk_gives_nought_everywhere_and_the_matrix_with_its_sixteen_cells(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # The fabrics hold no risk: nothing identified, nothing heaviest, the matrix empty but whole,
    # a coverage and outcomes of nought.
    body = read(api, fabrics.stage.reader, f"?{AT}")
    assert body["identified_total"] == "0.00"
    assert body["heaviest"] == []
    assert len(body["matrix"]["cells"]) == 16
    assert body["matrix"]["points"] == []
    assert set(body["coverage"].values()) == {"0.00"}
    assert body["period_outcome"] == {"occurred_provisions": "0.00", "dismissed_provisions": "0.00"}


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_the_view_is_read_under_its_permission_and_refuses_an_inverted_period(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US : « la lecture est sous portfolio_risks.read » : the project manager, who does
    # not read the portfolio, does not see the view (404), an anonymous caller is refused (401); the
    # reader reads it; the period is refused as every view of the portfolio does (422, designated);
    # the contract of the view takes no node.
    stage = fabrics.stage
    assert api.get(RISKS, headers=stage.manager.headers).status_code == 404
    assert api.get(RISKS).status_code == 401
    assert api.get(RISKS, headers=stage.reader.headers).status_code == 200
    inverted = api.get(f"{RISKS}?from=2026-03-31&to=2026-01-01", headers=stage.reader.headers)
    assert inverted.status_code == 422
    assert [(each["pointer"], each["code"]) for each in inverted.json()["fields"]] == [
        ("/query/to", "VALUE_OUT_OF_RANGE")
    ]
