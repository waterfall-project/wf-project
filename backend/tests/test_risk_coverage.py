# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve for risks and the coverage of the project through the service (US-2610/L1).

``getProjectRiskCoverage`` and the ``coverage`` of ``getRemainingIndicators``, which answer the
same figures (WF-RAE-0020): the reserve the reference conserves, written when a revision becomes the
reference and moved by nothing after (M-01), the provisions left of the risks identified in the
revision read, the cost at occurrence of the occurred, their signed variance, the re-estimated
amount of the lines that came from them beside, outside the variance (#1761, #2002); a revision
marked as its marking kept it (WF-DAT-0040). The provisions the remaining to commit counts
(WF-RAE-0010). Every answer is checked against the contract (``ContractClient``).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from nodes_support import mark, put_risk, set_progress
from projects_support import Scene, designate
from projects_support import scene as make_scene
from risks_support import MAKING, Costed, Risks, costed, occur
from sqlalchemy import func, select, update

from waterfall.api.scopes import kept_document
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import ReferenceDesignated
from waterfall.core.revisions.interface.shared import inscribe_revision
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.covering import conserved_coverage
from waterfall.core.risks.sharing import write_shares
from waterfall.core.risks.tables import RiskReferenceShare
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database

# The figures of a coverage, in the order of the contract: the reserve, the provisions left, the
# cost of the occurred, their reestimated, the variance.
Figures = tuple[str, str, str, str, str]


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@pytest.fixture
def risks(api: ContractClient, project: Costed) -> Risks:
    """Give the risks of the project costed."""
    return Risks(api, project)


@dataclass(frozen=True)
class Reading:
    """What the coverage of a project is read with."""

    risks: Risks

    def answer(self, revision_id: object = None) -> Any:
        """Read the coverage as the manager does, the revision named or the one picked."""
        query = "" if revision_id is None else f"?revision_id={revision_id}"
        return self.risks.api.get(
            f"{self.risks.base}/risks/coverage{query}", headers=self.risks.headers
        )

    def body(self, revision_id: object = None) -> dict[str, Any]:
        """Read the coverage, which must answer; give its body."""
        answer = self.answer(revision_id)
        assert answer.status_code == 200, answer.text
        return answer.json()

    def figures(self, revision_id: object = None) -> Figures:
        """Give the five figures of the coverage."""
        return figures(self.body(revision_id))

    def remaining(self, revision_id: object = None) -> dict[str, Any]:
        """Read the indicators of the remaining to commit."""
        query = "" if revision_id is None else f"?revision_id={revision_id}"
        answer = self.risks.api.get(
            f"{self.risks.base}/remaining-indicators{query}", headers=self.risks.headers
        )
        assert answer.status_code == 200, answer.text
        return answer.json()

    def budget(self) -> Decimal:
        """Give the budget of the reference: the budgets of the subprojects of the remaining."""
        return sum(
            (Decimal(each["budget"]) for each in self.remaining()["by_subproject"]), Decimal(0)
        )

    def estimate(self) -> Decimal:
        """Give the total of the estimate of the revision read, the provisions included."""
        answer = self.risks.api.get(
            f"{self.risks.base}/estimate-indicators", headers=self.risks.headers
        )
        assert answer.status_code == 200, answer.text
        return Decimal(answer.json()["total"]["value"])


def figures(body: dict[str, Any]) -> Figures:
    """Give the five figures of a coverage, or of the ``coverage`` of the remaining to commit."""
    return (
        body["reserve"],
        body["remaining_provisions"],
        body["occurred_cost"],
        body["occurred_reestimated"],
        body["coverage_variance"],
    )


@pytest.fixture
def reading(risks: Risks) -> Reading:
    """Give what reads the coverage of the project."""
    return Reading(risks)


def declare(risks: Risks, revision_id: object, label: str, probability: str, amount: str) -> Any:
    """Declare a risk in a revision, its own estimate at an amount; give the risk read."""
    risk = risks.declared(probability, label)
    risks.costed_at(risk, revision_id, amount)
    return risks.risk(risk, revision_id)


def mark_and_designate(risks: Risks, revision_id: object) -> None:
    """Mark a revision and designate it the reference, as the manager does."""
    mark(risks.stage, {"revision_id": str(revision_id)}, label=f"v{len(marked_names(risks)) + 1}.0")
    designate(risks.api, risks.stage, {"revision_id": str(revision_id)})


def marked_names(risks: Risks) -> list[str]:
    """Give the labels of the revisions marked so far."""
    answer = risks.api.get(f"{risks.base}/revisions", headers=risks.headers)
    assert answer.status_code == 200, answer.text
    return [each["version_name"] for each in answer.json()["items"] if each["version_name"]]


def dismiss(risks: Risks, risk: dict[str, Any]) -> None:
    """Dismiss a risk in the current revision, by a review at the counter read."""
    current = risks.risk(risk)
    risks.reviewed(current, state="dismissed")


def making_of(project: Costed, revision_id: object) -> UUID:
    """Give the task of the making in a revision, as copied."""
    with project.stage.owner.begin() as connection:
        found = connection.scalar(
            select(Task.node_id)
            .join(Node, Node.id == Task.node_id)
            .where(Node.revision_id == revision_id, Task.label == MAKING)
        )
    assert found is not None
    return found


def refer_as_a_merge(
    project: Costed, previous: UUID, revision_id: UUID, at: datetime | None = None
) -> None:
    """Make a marked revision the reference after another, as the merge of an amendment does.

    The designation is no command here — the project has been marked since the last one, and the
    command refuses it (WF-REV-0040) —: the merge marks a revision and has the designation follow
    (``register_designation``), whose parts are called the same way.
    """
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(Revision).where(Revision.id == previous).values(is_reference=False)
        )
        connection.execute(
            update(Revision).where(Revision.id == revision_id).values(is_reference=True)
        )
        connection.execute(
            update(Project)
            .where(Project.id == project.project_id)
            .values(reference_revision_id=revision_id)
        )
    with logging_context(correlation_id="merge"), project.stage.database.transaction() as session:
        designation = ReferenceDesignated(
            session,
            project.project_id,
            revision_id,
            utc_now() if at is None else at,
            None,
            previous,
            corrects=False,
        )
        write_shares(designation)
        # The designation inscribes itself in the journal after its parts, as the command does.
        revision = session.get(Revision, revision_id)
        assert revision is not None
        act = Act(None, designation.at)
        inscribe_revision(session, revision, "reference_designate", revision.version_name, act)


def share_rows(stage: Scene, revision_id: object) -> dict[UUID, Decimal]:
    """Give the shares written for a revision, by risk."""
    with stage.owner.begin() as connection:
        rows = connection.execute(
            select(RiskReferenceShare.risk_id, RiskReferenceShare.provision_amount).where(
                RiskReferenceShare.revision_id == revision_id
            )
        )
        return dict(rows.all())


# --- The examples, without occurrence nor amendment --------------------------------------------


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_project_costed_at_1000_with_a_risk_of_200_at_30_percent_has_a_reserve_of_60(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # « Sur un projet chiffré à 1 000 portant un risque de gravité 200 à 30 %, le devis totalise
    # 1 060, le budget de référence 1 000 et la réserve 60. »
    declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    assert reading.estimate() == Decimal("1060.00")
    mark_and_designate(risks, project.revision_id)
    following = risks.revision()
    assert reading.estimate() == Decimal("1060.00")
    assert reading.budget() == Decimal("1000.00")
    assert reading.figures(following["revision_id"]) == (
        "60.00",
        "60.00",
        "0.00",
        "0.00",
        "0.00",
    )


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_second_risk_of_40_raises_the_reserve_to_100_and_dismissing_it_leaves_it_and_the_budget(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # « … un second risque de provision 40 présent dans la référence porte la réserve à 100 ;
    # l'écarter fait passer les provisions restantes de 40 à 0 sans toucher le budget de
    # référence. »
    # Without an occurrence: the first risk is dismissed first, then the second, whose 40 are left.
    first = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    second = declare(risks, project.revision_id, "Panne de la grue", "0.1", "400.00")
    assert second["provision_amount"] == "40.00"
    mark_and_designate(risks, project.revision_id)
    risks.revision()
    assert reading.figures() == ("100.00", "100.00", "0.00", "0.00", "0.00")
    dismiss(risks, first)
    assert reading.figures() == ("100.00", "40.00", "0.00", "0.00", "60.00")
    dismiss(risks, second)
    assert reading.figures() == ("100.00", "0.00", "0.00", "0.00", "100.00")
    assert reading.budget() == Decimal("1000.00")


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_risk_identified_after_the_reference_of_a_null_reserve_is_a_variance_of_minus_30(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # « Sur un projet dont la réserve est nulle et sans risque survenu, un risque identifié après
    # la référence, de provision 30, porte les provisions restantes à 30 et l'écart de couverture
    # à -30. »
    mark_and_designate(risks, project.revision_id)
    following = UUID(risks.revision()["revision_id"])
    assert reading.figures() == ("0.00", "0.00", "0.00", "0.00", "0.00")
    declare(risks, following, "Retard du fournisseur", "0.3", "100.00")
    assert reading.figures() == ("0.00", "30.00", "0.00", "0.00", "-30.00")


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_completion_of_the_tasks_of_an_occurred_risk_changes_neither_cost_nor_variance(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # The occurrence is emulated (``occur``, ``put_risk``): the example of the Vérif, on the real
    # occurrence, is that of test_risk_coverage_merged.py (US-2610/L2).
    # « La terminaison des tâches issues d'un risque survenu ne change ni le coût des survenus ni
    # l'écart de couverture. » The task of the making stands for the one the occurrence merged; the
    # lines it bears are reestimated beside the cost at occurrence, never in the variance (#1761).
    risk = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    mark_and_designate(risks, project.revision_id)
    following = UUID(risks.revision()["revision_id"])
    task = str(making_of(project, following))
    occur(project.stage, risk["risk_id"], following)
    put_risk(project.stage, task, UUID(risk["risk_id"]))
    before = reading.figures()
    assert before == ("60.00", "0.00", "200.00", "400.00", "-140.00")
    set_progress(project.stage, task, "completed", date(2026, 6, 3))
    assert reading.figures() == before


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_reestimation_of_the_lines_of_an_occurred_risk_is_beside_its_cost_not_in_the_variance(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # The occurrence is emulated (``occur``, ``put_risk``): the example of the Vérif, on the real
    # occurrence, is that of test_risk_coverage_merged.py (US-2610/L2).
    # The variant of the contract (``risk_coverage_reestimated``, #2002): the lines that came from
    # the occurred risk are reestimated at 300 against 400, their cost at occurrence 200 stays, and
    # the variance with it.
    risk = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    mark_and_designate(risks, project.revision_id)
    following = UUID(risks.revision()["revision_id"])
    task = making_of(project, following)
    occur(project.stage, risk["risk_id"], following)
    put_risk(project.stage, str(task), UUID(risk["risk_id"]))
    before = reading.figures()
    with project.stage.owner.begin() as connection:
        lines = select(Node.id).where(Node.parent_id == task)
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id.in_(lines))
            .values(reestimated_amount=Decimal("300.00"))
        )
    after = reading.figures()
    assert (before[2], before[3], before[4]) == ("200.00", "400.00", "-140.00")
    assert (after[2], after[3], after[4]) == ("200.00", "300.00", "-140.00")
    assert after[3] != after[2]


# --- The reserve, kept ------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_reserve_is_written_at_the_designation_and_moved_by_nothing_after(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # The occurrence is emulated (``occur``, ``put_risk``): the example of the Vérif, on the real
    # occurrence, is that of test_risk_coverage_merged.py (US-2610/L2).
    # « … la réserve est conservée par la révision de référence au moment où elle le devient […] et
    # ne change plus : ni un réexamen, ni un écart, ni une survenance, ni une saisie dans un devis
    # propre ne la déplacent (M-01). »
    first = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    second = declare(risks, project.revision_id, "Panne de la grue", "0.1", "400.00")
    mark_and_designate(risks, project.revision_id)
    following = UUID(risks.revision()["revision_id"])
    assert reading.body()["reserve"] == "100.00"
    # An own estimate entered: the provision of the first risk goes from 60 to 90.
    risks.costed_at(first, following, "100.00")
    assert risks.risk(first)["provision_amount"] == "90.00"
    assert reading.figures() == ("100.00", "130.00", "0.00", "0.00", "-30.00")
    # A review that confirms it at another probability.
    risks.reviewed(risks.risk(second), probability="0.5")
    assert reading.body()["reserve"] == "100.00"
    # An occurrence, and a dismissal.
    occur(project.stage, first["risk_id"], following)
    assert reading.body()["reserve"] == "100.00"
    dismiss(risks, second)
    assert reading.body()["reserve"] == "100.00"
    listed = risks.api.get(f"{risks.base}/risks", headers=risks.headers).json()
    assert listed["totals"]["reserve"] == "100.00"


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_new_reference_keeps_the_provision_of_the_risks_that_left_the_identified_state(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # The occurrence and the merge are emulated (``occur``, ``refer_as_a_merge``): the example of
    # the Vérif, on the real ones, is that of test_risk_coverage_merged.py (US-2610/L2).
    # « … la réserve de la nouvelle référence conserve la provision que portaient dans la précédente
    # les risques survenus ou écartés avant elle, et s'augmente de celle des risques identifiés
    # qu'elle porte » : the first risk occurred and the second dismissed keep their 60 and 40; a
    # third, identified at 50, adds to them.
    first = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    second = declare(risks, project.revision_id, "Panne de la grue", "0.1", "400.00")
    mark_and_designate(risks, project.revision_id)
    following = UUID(risks.revision()["revision_id"])
    occur(project.stage, first["risk_id"], following)
    dismiss(risks, second)
    third = declare(risks, following, "Grève des transporteurs", "0.5", "100.00")
    assert third["provision_amount"] == "50.00"
    before = share_rows(project.stage, project.revision_id)
    assert sorted(before.values()) == [Decimal("40.00"), Decimal("60.00")]
    mark(project.stage, {"revision_id": str(following)}, label="v2.0")
    refer_as_a_merge(project, project.revision_id, following)
    shares = share_rows(project.stage, following)
    assert shares == {
        UUID(first["risk_id"]): Decimal("60.00"),
        UUID(second["risk_id"]): Decimal("40.00"),
        UUID(third["risk_id"]): Decimal("50.00"),
    }
    again = risks.revision()
    assert reading.figures(again["revision_id"])[:3] == ("150.00", "50.00", "200.00")
    # The provisions the register reads of the occurred and the dismissed are those shares (H-03).
    by_label = {
        each["label"]: each["provision_amount"]
        for each in risks.api.get(f"{risks.base}/risks", headers=risks.headers).json()["items"]
    }
    assert by_label["Retard du fournisseur"] == "60.00"
    assert by_label["Panne de la grue"] == "40.00"


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_designation_that_corrects_the_previous_one_writes_the_shares_again(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # The designation corrected (WF-REV-0040): no revision was marked since, so the revision named
    # replaces the reference, whose shares go; the reserve is that of the new one.
    first = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    mark(project.stage, {"revision_id": str(project.revision_id)}, label="v1.0")
    following = UUID(risks.revision()["revision_id"])
    risks.costed_at(first, following, "100.00")
    mark(project.stage, {"revision_id": str(following)}, label="v2.0")
    designate(risks.api, project.stage, {"revision_id": str(following)})
    assert share_rows(project.stage, following) == {UUID(first["risk_id"]): Decimal("90.00")}
    designate(risks.api, project.stage, {"revision_id": str(project.revision_id)})
    assert share_rows(project.stage, following) == {}
    assert share_rows(project.stage, project.revision_id) == {
        UUID(first["risk_id"]): Decimal("60.00")
    }
    risks.revision()
    assert reading.body()["reserve"] == "60.00"


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_project_without_a_reference_has_no_reserve(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # « sans révision de référence, la réserve et l'écart sont ce que le contrat dit » : a reserve
    # of nought, and the variance of what the risks identified still weigh.
    declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    assert reading.figures() == ("0.00", "60.00", "0.00", "0.00", "-60.00")


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_marked_revision_keeps_the_figures_of_its_risks_and_reads_the_reserve_of_the_reference(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # « La couverture d'une révision marquée est conservée à son marquage […] et rendue telle
    # quelle », sauf la réserve, que la référence conserve : v1.0 marquée puis désignée — le chemin
    # normal — rend, des deux lectures de la couverture, la réserve de 60 que le registre rend, et
    # les grandeurs des risques que son marquage a conservées, qu'une saisie postérieure ne change
    # pas.
    first = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    mark_and_designate(risks, project.revision_id)
    kept = reading.body(project.revision_id)
    assert figures(kept) == ("60.00", "60.00", "0.00", "0.00", "0.00")
    assert kept["context"]["revision_status"] == "marked"
    assert kept["context"]["is_stored"] is True
    assert figures(reading.remaining(project.revision_id)["coverage"]) == figures(kept)
    registry = risks.api.get(
        f"{risks.base}/risks?revision_id={project.revision_id}", headers=risks.headers
    ).json()
    assert registry["totals"]["reserve"] == kept["reserve"] == "60.00"
    # A later entry in the current revision moves neither the figures kept nor the reserve.
    following = UUID(risks.revision()["revision_id"])
    risks.costed_at(first, following, "100.00")
    assert reading.body()["reserve"] == "60.00"
    assert reading.figures(project.revision_id) == figures(kept)
    assert figures(reading.remaining(project.revision_id)["coverage"]) == figures(kept)


MALFORMED: list[dict[str, Any]] = [
    {"remaining_provisions": None, "occurred_cost": "0.00"},
    {"remaining_provisions": "0.00", "occurred_cost": None},
    {"remaining_provisions": "n/a", "occurred_cost": "0.00"},
    {"remaining_provisions": "0.00", "occurred_cost": "NaN"},
    {"remaining_provisions": "0.00", "occurred_cost": "Infinity"},
    {"remaining_provisions": [1, 2, 3], "occurred_cost": "0.00"},
]


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.parametrize("coverage", [None, {}, {"reserve": "0.00"}, *MALFORMED])
def test_a_marked_revision_whose_document_kept_no_coverage_gets_it_computed_at_the_reading(
    risks: Risks,
    project: Costed,
    reading: Reading,
    monkeypatch: pytest.MonkeyPatch,
    coverage: dict[str, Any] | None,
) -> None:
    # A document kept before the coverage entered it, or without its figures (#4183), is no 500: the
    # revision is read as one whose marking kept nothing, the coverage computed at the reading,
    # ``is_stored`` false, by both readings alike. A row of a marked revision is never written (the
    # trigger refuses it): the document the readings find is the one damaged.
    declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    mark_and_designate(risks, project.revision_id)
    kept = kept_document

    def damaged(*asked: Any) -> dict[str, Any] | None:
        found = kept(*asked)
        if found is None:
            return None
        without = {name: each for name, each in found.items() if name != "coverage"}
        return without if coverage is None else {**without, "coverage": coverage}

    monkeypatch.setattr("waterfall.api.risk_coverage.kept_document", damaged)
    monkeypatch.setattr("waterfall.api.remaining_indicators.kept_document", damaged)
    body = reading.body(project.revision_id)
    assert figures(body) == ("60.00", "60.00", "0.00", "0.00", "0.00")
    assert body["context"]["is_stored"] is False
    assert figures(reading.remaining(project.revision_id)["coverage"]) == figures(body)


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.parametrize("kept", [None, {}, *MALFORMED])
def test_the_conserved_coverage_of_a_malformed_document_is_none_without_any_patch(
    project: Costed, kept: dict[str, Any] | None
) -> None:
    # The figures null or not decimal are no 500 (#4183): the function itself answers none, so that
    # the caller computes the coverage at the reading, whatever route reaches it.
    with project.stage.database.transaction() as session:
        assert conserved_coverage(session, project.project_id, kept) is None


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.parametrize("kept", MALFORMED)
def test_a_malformed_document_is_judged_before_the_reserve_is_read(
    monkeypatch: pytest.MonkeyPatch, kept: dict[str, Any]
) -> None:
    # The reserve costs a query, made for nothing on a document that gives no coverage (#4258).
    def forbidden(*_: object) -> None:
        raise AssertionError("the reserve was read")

    monkeypatch.setattr("waterfall.core.risks.covering._reserve", forbidden)
    assert conserved_coverage(cast("Session", None), UUID(int=1), kept) is None


@pytest.mark.requirement("WF-RIS-0050-A")
def test_two_designations_at_the_same_instant_take_the_shares_of_the_previous_reference(
    risks: Risks, project: Costed
) -> None:
    # The shares taken are those of the reference the designation replaces (``previous_id``),
    # whatever the instants (the loader of the witness imposes them): two designations at the same
    # one, the second takes the share the first conserved for a risk occurred since. The order of
    # the journal, which a correction needs, is proved by the test below. The occurrence and the
    # merge are emulated (``occur``, ``refer_as_a_merge``): the example of the Vérif, on the real
    # ones, is that of test_risk_coverage_merged.py (US-2610/L2).
    first = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    mark_and_designate(risks, project.revision_id)
    following = UUID(risks.revision()["revision_id"])
    occur(project.stage, first["risk_id"], following)
    mark(project.stage, {"revision_id": str(following)}, label="v2.0")
    at = utc_now()
    refer_as_a_merge(project, project.revision_id, following, at)
    assert share_rows(project.stage, following) == {UUID(first["risk_id"]): Decimal("60.00")}
    again = UUID(risks.revision()["revision_id"])
    mark(project.stage, {"revision_id": str(again)}, label="v3.0")
    refer_as_a_merge(project, following, again, at)
    assert share_rows(project.stage, again) == {UUID(first["risk_id"]): Decimal("60.00")}


@pytest.mark.requirement("WF-RIS-0050-A")
@pytest.mark.parametrize("same_instant", [False, True])
def test_a_correction_takes_the_shares_of_the_reference_designated_last_before_the_corrected(
    risks: Risks, project: Costed, monkeypatch: pytest.MonkeyPatch, same_instant: bool
) -> None:
    # The reference replaced by a correction being gone, the shares come from the reference
    # designated last among the others, by the order of the journal (``_reference_before``), not by
    # instants. Z, designated by the command, conserves 60 for the risk; A, made the reference by a
    # merge (``refer_as_a_merge``, emulated and inscribed), 90 (its estimate was raised); the risk
    # occurred in M, marked before B, which the next merge makes the reference after A. M is then
    # designated by the command, which corrects B (no mark since): M takes the 90 of A, designated
    # last before B, not the 60 of Z. With ``same_instant``, Z, A and B are designated at one
    # instant, the order of the journal alone telling A from Z. The instant is an hour on, so that
    # no mark comes after it and the designation stays correctable.
    at = utc_now() + timedelta(hours=1)
    with monkeypatch.context() as patch:
        if same_instant:
            patch.setattr("waterfall.api.lifecycle.utc_now", lambda: at)
        risk = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
        mark_and_designate(risks, project.revision_id)
    held_by_a = UUID(risks.revision()["revision_id"])
    risks.costed_at(risk, held_by_a, "100.00")
    mark(project.stage, {"revision_id": str(held_by_a)}, label="v2.0")
    corrected_to = UUID(risks.revision()["revision_id"])
    occur(project.stage, risk["risk_id"], corrected_to)
    mark(project.stage, {"revision_id": str(corrected_to)}, label="v3.0")
    merged = UUID(risks.revision()["revision_id"])
    occur(project.stage, risk["risk_id"], merged)
    mark(project.stage, {"revision_id": str(merged)}, label="v4.0")
    instant = at if same_instant else None
    refer_as_a_merge(project, project.revision_id, held_by_a, instant)
    assert share_rows(project.stage, held_by_a) == {UUID(risk["risk_id"]): Decimal("90.00")}
    refer_as_a_merge(project, held_by_a, merged, instant)
    assert share_rows(project.stage, merged) == {UUID(risk["risk_id"]): Decimal("90.00")}
    designate(risks.api, project.stage, {"revision_id": str(corrected_to)})
    assert share_rows(project.stage, merged) == {}
    assert share_rows(project.stage, corrected_to) == {UUID(risk["risk_id"]): Decimal("90.00")}


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_coverage_of_the_remaining_to_commit_is_the_one_of_the_risk_coverage(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # The occurrence is emulated (``occur``, ``put_risk``): the example of the Vérif, on the real
    # occurrence, is that of test_risk_coverage_merged.py (US-2610/L2).
    # « La couverture des risques présente la réserve de référence, les provisions restantes, le
    # coût des risques survenus et l'écart de couverture. » The coverage of
    # ``getRemainingIndicators`` and ``getProjectRiskCoverage``, a risk occurred and one identified.
    first = declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "200.00")
    declare(risks, project.revision_id, "Panne de la grue", "0.1", "400.00")
    mark_and_designate(risks, project.revision_id)
    following = UUID(risks.revision()["revision_id"])
    occur(project.stage, first["risk_id"], following)
    put_risk(project.stage, str(making_of(project, following)), UUID(first["risk_id"]))
    body = reading.body()
    assert figures(body) == ("100.00", "40.00", "200.00", "400.00", "-140.00")
    assert figures(reading.remaining()["coverage"]) == figures(body)
    assert body["context"]["revision_id"] == str(following)
    assert body["context"]["revision_status"] == "draft"


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_coverage_of_a_revision_of_no_project_is_not_found(reading: Reading) -> None:
    # A revision that is none of the project's: 404, as every reading of a revision.
    assert reading.answer("01926f3a-7c00-7000-8000-0000000fffff").status_code == 404


# --- The provisions of the remaining to commit ----------------------------------------------------


def lines_not_completed(project: Costed) -> Decimal:
    """Sum the reestimated amounts of the lines of the tasks not completed, provisions included."""
    with project.stage.owner.begin() as connection:
        held = connection.scalar(
            select(func.sum(EstimateLine.reestimated_amount))
            .join(Node, Node.id == EstimateLine.node_id)
            .join(Task, Task.node_id == Node.parent_id)
            .where(Node.structure_id == project.structure_id, Task.progress != "completed")
        )
    return held or Decimal(0)


@pytest.mark.requirement("WF-RAE-0010-A")
def test_dismissing_a_risk_of_40_lowers_the_remaining_by_40_and_identifying_one_raises_it(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # « Écarter un risque de provision 40 diminue le reste à engager de 40 ; en identifier un
    # nouveau l'augmente de sa provision. » And the provision counts once: 1 040, not 1 080.
    risk = declare(risks, project.revision_id, "Panne de la grue", "0.1", "400.00")
    assert risk["provision_amount"] == "40.00"
    assert Decimal(reading.remaining()["total"]) == Decimal("1040.00")
    dismiss(risks, risk)
    assert Decimal(reading.remaining()["total"]) == Decimal("1000.00")
    declare(risks, project.revision_id, "Retard du fournisseur", "0.3", "100.00")
    assert Decimal(reading.remaining()["total"]) == Decimal("1030.00")


@pytest.mark.requirement("WF-RAE-0010-A")
def test_the_remaining_is_the_reestimated_amounts_of_the_tasks_not_completed_provisions_included(
    risks: Risks, project: Costed, reading: Reading
) -> None:
    # « Le reste à engager égale la somme des montants réestimés courants des lignes des tâches non
    # terminées, hors lignes de provision, plus les provisions des risques identifiés » : the
    # provision of 40 is under the study, the making is completed.
    declare(risks, project.revision_id, "Panne de la grue", "0.1", "400.00")
    set_progress(project.stage, str(project.tasks[MAKING]), "completed", date(2026, 6, 3))
    assert lines_not_completed(project) == Decimal("640.00")
    assert Decimal(reading.remaining()["total"]) == lines_not_completed(project)
