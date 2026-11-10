# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line reestimated, set to zero, marked (US-1580/L2).

``setLineRemaining`` on the main structure of the current revision of a project In progress, its
reference written, marked and designated through the service (``remaining_support``): the figures
of ``reestimated_amount_basis`` written, the re-estimated amount recomputed, the budget, the lineage
and the remaining before the review left as they are, the mark and the reason kept; the last open
line of a task set to nought completes it, by the planning, at the date sent; the conditions named
in their order, the counter, the rights, the entry of the history, two re-estimates at once; and
the remaining to commit of a revision, at the state of its tasks (``remaining_of_revision``). Every
answer is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import YEAR, Costing, Lines, costing
from history_support import undo
from nodes_support import Tree, entries, faults, mark, opened, refusal, set_progress, signed_in
from planning_support import DAY
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, review_marked, task_named
from sqlalchemy import delete, select, update

from waterfall.core.cost_settings.interface import set_hourly_rate
from waterfall.core.cost_settings.tables import HourlyRate
from waterfall.core.estimate.interface import remaining_of_revision
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.projects.tables import Project
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MILESTONE = {"duration": {"value": "0", "unit": "d"}}
READ = "remaining.read"
WRITE = "remaining.write"
BASIS = "reestimated_amount_basis"
JUNE_THIRD = "2026-06-03"
LATER = datetime(YEAR + 1, 1, 12, 10, tzinfo=UTC)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated 65.00 for the year."""
    return costing(stage.database)


@pytest.fixture
def review(api: ContractClient, stage: Scene, costs: Costing) -> Review:
    """Give the project In progress, its tasks and their lines.

    The wiring, its supplies at 100 and its labour at 100 hours; the tests and their bench at 50;
    the acceptance, a milestone, and its report at 10.
    """

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        lines.made(wiring, **material(costs, "Fournitures", "100"))
        lines.made(wiring, **labour(costs, "Raccordement", "100"))
        tests = tree.made("Essais")
        lines.made(tests, **material(costs, "Banc", "50"))
        acceptance = tree.made("Réception", task=MILESTONE)
        lines.made(acceptance, **material(costs, "Procès-verbal", "10"))

    return in_progress(api, stage, build)


def material(costs: Costing, label: str, amount: str) -> dict[str, Any]:
    """Give a line of material: one at the amount said."""
    return {
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }


def labour(costs: Costing, label: str, hours: str) -> dict[str, Any]:
    """Give a labour line of the role of the scene: one engineer for the hours said."""
    return {"label": label, "quantity": "1", "resource_role_id": str(costs.role), "hours": hours}


def reestimate(tree: Tree, line: dict[str, Any], who: Any = None, **body: Any) -> Any:
    """Send a re-estimate of a line at the counter read; give the answer."""
    sent = {"lock_version": line["lock_version"], **body}
    headers = (who or tree.stage.manager).headers
    return tree.api.put(
        f"{tree.path}/nodes/{line['node_id']}/remaining", headers=headers, json=sent
    )


def reestimated(tree: Tree, line: dict[str, Any], **body: Any) -> dict[str, Any]:
    """Send a re-estimate that must be accepted; give what is answered."""
    answer = reestimate(tree, line, **body)
    assert answer.status_code == 200, answer.text
    return answer.json()


def zero(tree: Tree, label: str, **body: Any) -> Any:
    """Set the line of a label to nought, its quantity at 0; give the answer."""
    return reestimate(tree, line_named(tree, label), **{BASIS: {"quantity": "0"}, **body})


def missing(answer: Any) -> str:
    """Give the condition a refusal of 409 names, after checking its code."""
    status, code, params = refusal(answer)
    assert (status, code) == (409, "STATE_FORBIDS_OPERATION"), answer.text
    return params["missing_condition"]


def remaining_of(stage: Scene, revision: dict[str, Any]) -> tuple[Decimal, dict[UUID, Decimal]]:
    """Read the remaining to commit of a revision, total and by line, by the interface."""
    with stage.database.transaction() as session:
        held = remaining_of_revision(
            session, UUID(stage.project["project_id"]), UUID(revision["revision_id"])
        )
    return held.total, dict(held.by_line)


# --- The re-estimate -----------------------------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0010-A")
def test_a_line_budgeted_at_100_reestimated_at_120_carries_the_remaining_from_100_to_120(
    review: Review,
) -> None:
    # « La réestimation à 120 d'une ligne budgétée à 100 sur une tâche non démarrée, saisie depuis
    # la grille, porte le reste à engager de 100 à 120. »
    tree = review.tree
    line = line_named(tree, "Fournitures")
    before = tree.read().json()["totals"]
    assert line["estimate_line"]["budgeted_amount"] == "100.00"
    written = reestimated(tree, line, **{BASIS: {"unit_disbursement": "120"}})
    [node] = written["nodes"]
    facet = node["estimate_line"]
    assert (facet["budgeted_amount"], facet["reestimated_amount"]) == ("100.00", "120.00")
    assert facet["unit_disbursement"] == "120.00"
    assert (node["lineage_id"], node["lock_version"]) == (
        line["lineage_id"],
        line["lock_version"] + 1,
    )
    assert facet["previous_reestimated_amount"] is None
    assert Decimal(written["totals"]["reestimated_amount"]) == (
        Decimal(before["reestimated_amount"]) + 20
    )
    assert written["totals"]["budgeted_amount"] == before["budgeted_amount"]
    [wiring] = written["ancestors"]
    assert wiring["task"]["progress"] == "not_started"
    assert line_named(tree, "Fournitures")["estimate_line"]["reestimated_amount"] == "120.00"


@pytest.mark.requirement("WF-RAE-0040-A")
def test_80_hours_on_a_line_budgeted_at_100_give_80_times_the_rate_and_no_amount_is_entered(
    review: Review, stage: Scene
) -> None:
    # « La saisie d'une charge de 80 heures sur une ligne de quantité 1 budgétée à 100 heures donne
    # un montant réestimé de 80 fois le taux, projeté sur l'année de consommation de la ligne
    # (WF-DEV-0030) ; le montant n'est pas saisissable. » The task falls in the year of the rate.
    tree = review.tree
    line = line_named(tree, "Raccordement")
    assert line["estimate_line"]["budgeted_amount"] == "6500.00"
    for amount in ({"reestimated_amount": "5200.00"}, {BASIS: {"reestimated_amount": "5200.00"}}):
        sent = {BASIS: {"hours": "80"}, **amount} if BASIS not in amount else amount
        pointer = "/reestimated_amount" if BASIS not in amount else f"/{BASIS}/reestimated_amount"
        assert faults(reestimate(tree, line, **sent)) == [(pointer, "FIELD_NOT_ACCEPTED", {})]
    facet = reestimated(tree, line, **{BASIS: {"hours": "80"}})["nodes"][0]["estimate_line"]
    assert (facet["hours"], facet["quantity"]) == ("80", "1")
    assert facet["reestimated_amount"] == "5200.00"
    assert facet["consumption_year"] == DAY.year
    with stage.database.transaction() as session:
        marked = session.scalar(
            select(EstimateLine.reestimated_at).where(EstimateLine.node_id == UUID(line["node_id"]))
        )
    assert marked is not None


@pytest.mark.requirement("WF-RAE-0040-A")
@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_figure_the_line_does_not_accept_or_below_nought_is_refused_and_writes_nothing(
    review: Review,
) -> None:
    # A disbursement for a labour line, hours for another, are refused (``FIELD_NOT_ACCEPTED``),
    # a figure below nought (``VALUE_OUT_OF_RANGE``), each under the object that sends it.
    tree = review.tree
    labour_line, supplies = line_named(tree, "Raccordement"), line_named(tree, "Fournitures")
    answer = reestimate(tree, labour_line, **{BASIS: {"unit_disbursement": "10"}})
    assert faults(answer) == [(f"/{BASIS}/unit_disbursement", "FIELD_NOT_ACCEPTED", {})]
    answer = reestimate(tree, supplies, **{BASIS: {"hours": "10"}})
    assert faults(answer) == [(f"/{BASIS}/hours", "FIELD_NOT_ACCEPTED", {})]
    answer = reestimate(tree, supplies, **{BASIS: {"quantity": "-1"}})
    assert faults(answer) == [(f"/{BASIS}/quantity", "VALUE_OUT_OF_RANGE", {"minimum": 0})]
    assert line_named(tree, "Fournitures") == supplies
    assert line_named(tree, "Raccordement") == labour_line


@pytest.mark.requirement("WF-DEV-0010-A")
def test_a_labour_line_whose_category_has_no_rate_any_more_is_refused_naming_it(
    review: Review, stage: Scene, costs: Costing
) -> None:
    # A computation the line would need without an hourly rate is refused (``HOURLY_RATE_MISSING``,
    # F-09): the rate the revision keeps and that of the reference withdrawn around the service.
    tree = review.tree
    line = line_named(tree, "Raccordement")
    with stage.owner.begin() as connection:
        connection.execute(
            delete(RevisionRate).where(
                RevisionRate.revision_id == UUID(tree.revision["revision_id"]),
                RevisionRate.cost_category_id == costs.labour,
            )
        )
        connection.execute(delete(HourlyRate).where(HourlyRate.cost_category_id == costs.labour))
    status, code, params = refusal(reestimate(tree, line, **{BASIS: {"hours": "80"}}))
    assert (status, code) == (422, "HOURLY_RATE_MISSING")
    assert [each["cost_category_id"] for each in params["missing_rates"]] == [str(costs.labour)]
    assert line_named(tree, "Raccordement")["estimate_line"]["hours"] == "100"


@pytest.mark.requirement("WF-RAE-0040-A")
def test_the_reason_sent_is_kept_with_the_line_read_and_overwritten_by_the_next(
    review: Review,
) -> None:
    # #2420: the reason of the last re-estimate, read with the line; one sending none leaves none.
    tree = review.tree
    reason = "Revue de novembre : fournitures négociées"
    written = reestimated(tree, line_named(tree, "Fournitures"), **{BASIS: {}}, reason=reason)
    assert written["nodes"][0]["estimate_line"]["remaining_reason"] == reason
    line = line_named(tree, "Fournitures")
    assert line["estimate_line"]["remaining_reason"] == reason
    # Only what is sent changes: an empty basis marks the line at its figures.
    assert line["estimate_line"]["reestimated_amount"] == "100.00"
    reestimated(tree, line, **{BASIS: {"unit_disbursement": "90"}})
    assert line_named(tree, "Fournitures")["estimate_line"]["remaining_reason"] is None


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_re_estimate_at_a_stale_counter_or_of_a_node_that_is_no_line_is_refused(
    review: Review, stage: Scene
) -> None:
    tree = review.tree
    line = line_named(tree, "Fournitures")
    reestimated(tree, line, **{BASIS: {"unit_disbursement": "110"}})
    answer = reestimate(tree, line, **{BASIS: {"unit_disbursement": "130"}})
    assert refusal(answer) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": line["lock_version"] + 1},
    )
    task = task_named(tree, "Câblage")
    for node in (task, {"node_id": str(uuid4()), "lock_version": 1}):
        assert refusal(reestimate(tree, node, **{BASIS: {}}))[:2] == (404, "NOT_FOUND")
    del stage


# --- The completion by the remaining set to nought ---------------------------------------------


@pytest.mark.requirement("WF-RAE-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_all_the_lines_of_a_task_not_started_set_to_nought_complete_it_started_on_that_day(
    review: Review,
) -> None:
    # « La saisie d'un reste à engager nul sur toutes les lignes d'une tâche non démarrée la
    # termine, avec une date de démarrage égale à sa date de terminaison. » The first line set to
    # nought ignores the date; the last one completes the task, which goes through the started
    # state, and both are written.
    tree = review.tree
    first = zero(tree, "Fournitures", completed_on=JUNE_THIRD)
    assert first.status_code == 200, first.text
    assert [node["kind"] for node in first.json()["nodes"]] == ["estimate_line"]
    assert task_named(tree, "Câblage")["task"]["progress"] == "not_started"
    last = zero(tree, "Raccordement", completed_on=JUNE_THIRD)
    assert last.status_code == 200, last.text
    # In the order of the plan: the task, then its line.
    task, line = last.json()["nodes"]
    assert (task["kind"], line["kind"]) == ("task", "estimate_line")
    assert line["estimate_line"]["reestimated_amount"] == "0.00"
    assert (task["task"]["progress"], task["task"]["started_on"], task["task"]["completed_on"]) == (
        "completed",
        JUNE_THIRD,
        JUNE_THIRD,
    )
    read = task_named(tree, "Câblage")
    assert (read["task"]["progress"], read["lock_version"]) == ("completed", task["lock_version"])


@pytest.mark.requirement("WF-RAE-0040-A")
def test_a_completion_without_its_date_is_refused_naming_the_task_and_writes_nothing(
    review: Review,
) -> None:
    tree = review.tree
    supplies = line_named(tree, "Banc")
    answer = zero(tree, "Banc")
    task = task_named(tree, "Essais")
    assert faults(answer) == [
        ("/completed_on", "COMPLETION_DATE_REQUIRED", {"task_node_id": task["node_id"]})
    ]
    assert line_named(tree, "Banc") == supplies
    assert task["task"]["progress"] == "not_started"


@pytest.mark.requirement("WF-RAE-0040-A")
@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_milestone_completed_by_its_line_and_a_started_task_keeps_its_start(
    review: Review, stage: Scene
) -> None:
    # A milestone goes straight to completed, its start that same date (WF-PLA-0130); a started
    # task keeps its start, which the completion may not precede.
    tree = review.tree
    answer = zero(tree, "Procès-verbal", completed_on=JUNE_THIRD)
    assert answer.status_code == 200, answer.text
    milestone = answer.json()["nodes"][0]["task"]
    assert (milestone["progress"], milestone["started_on"], milestone["completed_on"]) == (
        "completed",
        JUNE_THIRD,
        JUNE_THIRD,
    )
    tests = task_named(tree, "Essais")
    set_progress(stage, tests["node_id"], "started", DAY)
    early = zero(tree, "Banc", completed_on=JUNE_THIRD)
    assert faults(early) == [("/completed_on", "VALUE_OUT_OF_RANGE", {"minimum": DAY.isoformat()})]
    done = zero(tree, "Banc", completed_on=DAY.isoformat()).json()["nodes"][0]["task"]
    assert (done["started_on"], done["completed_on"]) == (DAY.isoformat(), DAY.isoformat())


@pytest.mark.requirement("WF-RAE-0040-A")
def test_a_line_of_a_completed_task_is_refused_and_its_entry_says_so(review: Review) -> None:
    # « La modification d'une ligne portée par une tâche terminée est refusée. »
    tree = review.tree
    assert zero(tree, "Procès-verbal", completed_on=JUNE_THIRD).status_code == 200
    line = line_named(tree, "Procès-verbal")
    assert line["estimate_line"]["remaining_entry"] == {
        "is_available": False,
        "missing_conditions": ["task_not_completed"],
    }
    assert missing(reestimate(tree, line, **{BASIS: {"unit_disbursement": "5"}})) == (
        "task_not_completed"
    )


# --- The conditions in their order -------------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0040-A")
@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_project_not_in_progress_refuses_the_entry_after_the_line_names_its_task(
    review: Review, stage: Scene
) -> None:
    # « Sur un projet qui n'est pas En cours, la grille ne propose ni création ni suppression » :
    # ``edit_remaining`` asks the project In progress; the condition of the line comes first.
    tree = review.tree
    assert zero(tree, "Procès-verbal", completed_on=JUNE_THIRD).status_code == 200
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    open_line, closed = line_named(tree, "Banc"), line_named(tree, "Procès-verbal")
    assert missing(reestimate(tree, open_line, **{BASIS: {}})) == "project_in_progress"
    assert missing(reestimate(tree, closed, **{BASIS: {}})) == "task_not_completed"


@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_background_task_a_marked_revision_and_a_terminal_project_refuse_the_entry(
    api: ContractClient, review: Review, stage: Scene
) -> None:
    tree = review.tree
    assert zero(tree, "Procès-verbal", completed_on=JUNE_THIRD).status_code == 200
    open_line, closed = line_named(tree, "Banc"), line_named(tree, "Procès-verbal")
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v2.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    assert missing(reestimate(tree, open_line, **{BASIS: {}})) == "no_background_task_running"
    assert missing(reestimate(tree, closed, **{BASIS: {}})) == "task_not_completed"
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    assert missing(reestimate(tree, open_line, **{BASIS: {}})) == "project_in_progress"


@pytest.mark.requirement("WF-DAT-0020-A")
@pytest.mark.requirement("WF-CYC-0100-A")
def test_a_marked_revision_and_a_terminal_project_refuse_the_entry_after_the_line(
    review: Review, stage: Scene
) -> None:
    tree = review.tree
    assert zero(tree, "Procès-verbal", completed_on=JUNE_THIRD).status_code == 200
    open_line, closed = line_named(tree, "Banc"), line_named(tree, "Procès-verbal")
    review_marked(stage, tree.revision, "v2.0")
    assert missing(reestimate(tree, open_line, **{BASIS: {}})) == "revision_draft"
    assert missing(reestimate(tree, closed, **{BASIS: {}})) == "task_not_completed"
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    assert missing(reestimate(tree, open_line, **{BASIS: {}})) == "project_not_terminal"


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_line_is_reestimated_by_a_contributor_who_may_write_the_remaining(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    tree = review.tree
    line = line_named(tree, "Fournitures")
    body: dict[str, Any] = {BASIS: {}}
    reading = person(stage.database, realm, READ, "planning.read")
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    assert refusal(reestimate(tree, line, reading, **body)) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": WRITE},
    )
    seeing = person(stage.database, realm, READ, WRITE, "all_projects_read")
    assert refusal(reestimate(tree, line, seeing, **body))[:2] == (403, "NOT_CONTRIBUTOR")
    assert refusal(reestimate(tree, line, stage.outsider, **body))[:2] == (404, "NOT_FOUND")
    assert reestimate(tree, line, stage.participant, **body).status_code == 200


# --- The history, two re-estimates at once ------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_completion_by_the_remaining_is_kept_with_its_task_and_undone_whole(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    tree = review.tree
    writer = signed_in(stage, realm)
    first = reestimate(tree, line_named(tree, "Fournitures"), writer, **{BASIS: {}})
    assert first.status_code == 200, first.text
    line = line_named(tree, "Banc")
    task = task_named(tree, "Essais")
    answer = reestimate(tree, line, writer, **{BASIS: {"quantity": "0"}}, completed_on=JUNE_THIRD)
    assert answer.status_code == 200, answer.text
    alone, whole = entries(stage)
    # The task enters the entry only when it is written.
    assert (alone.kind, len(alone.before)) == ("remaining", 1)
    assert whole.kind == "remaining"
    assert whole.node_ids == [UUID(line["node_id"]), UUID(task["node_id"])]
    assert [each["rows"]["task"] for each in whole.before][1]["progress"] == "not_started"
    undone = undo(tree, writer)
    assert undone.status_code == 200, undone.text
    assert task_named(tree, "Essais")["task"]["progress"] == "not_started"
    restored = line_named(tree, "Banc")["estimate_line"]
    assert (restored["quantity"], restored["reestimated_amount"]) == ("1", "50.00")


@pytest.mark.requirement("WF-IHM-0110-A")
def test_two_re_estimates_of_a_line_at_once_are_written_one_after_the_other(
    review: Review,
) -> None:
    tree = review.tree
    line = line_named(tree, "Fournitures")
    with ThreadPoolExecutor(2) as pool:
        pending = [
            pool.submit(reestimate, tree, line, **{BASIS: {"unit_disbursement": amount}})
            for amount in ("110", "130")
        ]
        answers = [each.result() for each in pending]
    assert sorted(answer.status_code for answer in answers) == [200, 412]
    [won] = [answer for answer in answers if answer.status_code == 200]
    read = line_named(tree, "Fournitures")
    assert read["estimate_line"] == won.json()["nodes"][0]["estimate_line"]
    assert read["lock_version"] == line["lock_version"] + 1


# --- The remaining to commit of a revision ------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0010-A")
def test_the_remaining_sums_the_started_task_reestimated_and_the_one_not_started_but_not_the_done(
    review: Review, stage: Scene
) -> None:
    # « Sur un projet dont une tâche est terminée, une démarrée et une non démarrée, le reste à
    # engager vaut la somme des deux dernières, la démarrée pour son montant réestimé et l'autre
    # pour son montant de référence projeté » ; the provisions are EP-08's, none here.
    tree = review.tree
    wiring, acceptance = task_named(tree, "Câblage"), task_named(tree, "Réception")
    set_progress(stage, wiring["node_id"], "started", DAY)
    set_progress(stage, acceptance["node_id"], "completed", DAY)
    reestimated(tree, line_named(tree, "Raccordement"), **{BASIS: {"hours": "80"}})
    total, by_line = remaining_of(stage, tree.revision)
    expected = {
        UUID(line_named(tree, label)["node_id"]): Decimal(amount)
        for label, amount in (("Fournitures", "100.00"), ("Raccordement", "5200.00"))
    } | {UUID(line_named(tree, "Banc")["node_id"]): Decimal("50.00")}
    assert by_line == expected
    assert total == Decimal("5350.00")
    # A marked revision is read at the state of its tasks: the reference, all not started.
    total, by_line = remaining_of(stage, review.reference)
    assert (total, len(by_line)) == (Decimal("6660.00"), 4)


@pytest.mark.requirement("WF-RAE-0050-A")
def test_a_task_estimated_in_a_review_raises_the_remaining_and_leaves_the_reference_budget(
    review: Review, stage: Scene, costs: Costing
) -> None:
    # « Après ajout d'une tâche chiffrée en revue périodique, le reste à engager et la projection
    # du chef de projet augmentent de son montant ; le budget de référence […] inchangé. » The
    # projection and the index are EP-10's.
    tree = review.tree
    total, _ = remaining_of(stage, tree.revision)
    budget = tree.read().json()["totals"]["budgeted_amount"]
    added = tree.made("Reprise des borniers")
    created = review.lines.made(added, **material(costs, "Borniers", "300"))
    assert created["nodes"][0]["estimate_line"]["budgeted_amount"] == "0.00"
    after, _ = remaining_of(stage, tree.revision)
    assert after == total + Decimal("300.00")
    assert tree.read().json()["totals"]["budgeted_amount"] == budget


@pytest.mark.requirement("WF-RAE-0010-A")
def test_a_line_not_reestimated_counts_its_amount_at_the_rate_of_the_year_its_revision_accepted(
    api: ContractClient, stage: Scene, costs: Costing, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Dans une révision créée en 2027 où le taux de 2027 d'une catégorie a été accepté, une tâche
    # non démarrée dont une ligne relève de cette catégorie compte pour sa charge au taux de 2027,
    # et non au taux de 2026 corrigé d'une année d'inflation. » The update is EP-07's
    # (``applyRateUpdate``); the remaining counts the re-estimated amount it priced.
    first = Tree(api, stage, opened(api, stage))
    Lines(first).made(first.made("Câblage"), **labour(costs, "Raccordement", "10"))
    mark(stage, first.revision)
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(inflation_rate=Decimal("0.03"))
        )
    with stage.database.transaction() as session:
        set_hourly_rate(
            session, (costs.labour, YEAR + 1), Decimal("70.00"), None, Act(None, utc_now())
        )
    monkeypatch.setattr("waterfall.api.revisions.utc_now", lambda: LATER)
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/revisions",
        headers=stage.manager.headers,
        json={"apply_rate_update": True},
    )
    assert answer.status_code == 201, answer.text
    tree = Tree(api, stage, answer.json())
    line = line_named(tree, "Raccordement")["estimate_line"]
    assert line["base_amount"] == "700.00"
    total, _ = remaining_of(stage, answer.json())
    assert total == Decimal(line["reestimated_amount"])
