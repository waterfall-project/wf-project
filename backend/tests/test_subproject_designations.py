# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The deletion of a subproject a risk designates for its provision, through the service (#4208).

A risk dismissed in the current revision keeps no provision line: the deletion of the subproject it
designated is admitted and sets its designation to null, its counter advanced and its audit naming
the author of the deletion (``deleteSubproject``, #732). An identified one bears it by its provision
line, which refuses the deletion naming it, as any line of the current revision does. A risk of a
marked revision that designates it cites it: refused by ``subproject_not_cited``, never a failure
of the key of the evaluation. The undoing of an entry that would give the subproject back is
refused by ``restored_subproject_exists``, not as a conflict with the deletion. The project is
costed through the service (``risks_support``), without the witness. Every answer is checked
against the contract (``ContractClient``).
"""

from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, costing
from nodes_support import mark, refusal, signed_in
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import RISK_LABEL, Costed, Risks, costed, occur

if TYPE_CHECKING:
    from projects_support import Person
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

CONDITION = "STATE_FORBIDS_OPERATION"


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


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def deleted(risks: Risks, subproject_id: str) -> Any:
    """Delete a subproject at its first counter, as the manager does; give the answer."""
    path = f"{risks.base}/subprojects/{subproject_id}"
    return risks.api.delete(path, headers=risks.headers, params={"lock_version": 0})


def deletion_lacks(risks: Risks, subproject_id: str) -> list[str]:
    """Read what the command ``delete`` of a subproject lacks, as the list gives it."""
    listed = risks.api.get(f"{risks.base}/subprojects", headers=risks.headers)
    assert listed.status_code == 200, listed.text
    [item] = [each for each in listed.json() if each["subproject_id"] == subproject_id]
    return next(
        command["missing_conditions"]
        for command in item["available_commands"]
        if command["command"] == "delete"
    )


def dismissed_by(risks: Risks, who: Person, subproject_id: str) -> dict[str, Any]:
    """Declare a risk whose provision designates a subproject, dismissed by a contributor."""
    risk = risks.declared_costed(provision_subproject_id=subproject_id)
    answer = risks.review(risks.risk(risk), who, state="dismissed")
    assert answer.status_code == 201, answer.text
    dismissed = answer.json()
    assert (dismissed["provision_node_id"], dismissed["provision_subproject_id"]) == (
        None,
        subproject_id,
    )
    return dismissed


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_subproject_a_dismissed_risk_designates_is_deleted_and_the_designation_set_to_null(
    risks: Risks, stage: Scene, who: Person
) -> None:
    # « La suppression d'un sous-projet non référencé le retire de la base » : a dismissed risk
    # bears no line, and its designation does not keep the subproject (#4208, which answered 500).
    # The designation goes to null, the counter of the risk advances, its audit names the manager
    # who deleted the subproject, not the contributor who dismissed it (#732).
    sub = risks.subproject("LOT-Z")
    dismissed = dismissed_by(risks, who, sub)
    assert deletion_lacks(risks, sub) == []
    assert deleted(risks, sub).status_code == 204
    after = risks.risk(dismissed)
    assert (after["provision_subproject_id"], after["provision_subproject_label"]) == (None, None)
    assert after["state"] == "dismissed"
    assert after["lock_version"] == dismissed["lock_version"] + 1
    assert after["audit"]["updated_by"]["user_id"] == str(stage.manager.user_id)
    listed = risks.api.get(f"{risks.base}/subprojects", headers=risks.headers).json()
    assert [each["subproject_id"] for each in listed] == []


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_subproject_an_identified_risk_designates_is_kept_by_its_provision_line(
    risks: Risks, project: Costed
) -> None:
    # « Celle d'un sous-projet que portent des lignes de devis de la révision en cours est refusée
    # et nomme ces lignes » : the provision line of an identified risk bears the subproject it
    # designates; the refusal names it, by the label the risk gives it, and the designation stays.
    sub = risks.subproject("LOT-Z")
    risk = risks.declared_costed(provision_subproject_id=sub)
    assert deletion_lacks(risks, sub) == ["subproject_without_estimate_lines"]
    status, code, params = refusal(deleted(risks, sub))
    assert (status, code, params["missing_condition"]) == (
        409,
        CONDITION,
        "subproject_without_estimate_lines",
    )
    assert [(line["node_id"], line["label"]) for line in params["estimate_lines"]] == [
        (risk["provision_node_id"], f"Provision — {RISK_LABEL}")
    ]
    assert params["estimate_lines"][0]["structure_id"] == str(project.structure_id)
    kept = risks.risk(risk)
    assert (kept["provision_subproject_id"], kept["lock_version"]) == (sub, risk["lock_version"])


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_subproject_an_occurred_risk_designates_is_deleted_and_the_designation_set_to_null(
    risks: Risks, project: Costed, stage: Scene
) -> None:
    # « La suppression d'un sous-projet non référencé le retire de la base » : an occurred risk
    # bears no provision line, as a dismissed one; its designation goes to null, and the constraint
    # of the provision of an identified risk (``provision_when_identified``) is not touched.
    sub = risks.subproject("LOT-Z")
    risk = risks.declared_costed(provision_subproject_id=sub)
    occur(stage, risk["risk_id"], project.revision_id)
    assert deletion_lacks(risks, sub) == []
    assert deleted(risks, sub).status_code == 204
    after = risks.risk(risk)
    assert (after["state"], after["provision_subproject_id"]) == ("occurred", None)
    assert after["lock_version"] == risk["lock_version"] + 1
    assert after["audit"]["updated_by"]["user_id"] == str(stage.manager.user_id)


@pytest.mark.requirement("WF-DAT-0080-A")
def test_two_risks_designating_a_subproject_are_both_written_by_its_deletion(
    risks: Risks, stage: Scene, who: Person
) -> None:
    # « La suppression d'un sous-projet non référencé le retire de la base » : each risk that
    # designated it is written once, its counter advanced by one, its audit naming the manager.
    sub = risks.subproject("LOT-Z")
    first, second = dismissed_by(risks, who, sub), dismissed_by(risks, who, sub)
    assert deleted(risks, sub).status_code == 204
    for dismissed in (first, second):
        after = risks.risk(dismissed)
        assert after["provision_subproject_id"] is None
        assert after["lock_version"] == dismissed["lock_version"] + 1
        assert after["audit"]["updated_by"]["user_id"] == str(stage.manager.user_id)


@pytest.mark.requirement("WF-DAT-0080-A")
@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_subproject_a_risk_of_a_marked_revision_designates_is_refused_as_cited(
    risks: Risks, project: Costed, stage: Scene, who: Person
) -> None:
    # « Celle d'un sous-projet référencé par une révision marquée est refusée » : the dismissed risk
    # of the marked revision bears no line, its evaluation designates the subproject; the deletion
    # is refused by ``subproject_not_cited``, never a failure of its key (#4208), and the marked
    # revision keeps the designation. A current revision made by copy of it designates the
    # subproject too: the refusal comes before the designation is set to null, which stays, its
    # counter unmoved.
    sub = risks.subproject("LOT-Z")
    dismissed = dismissed_by(risks, who, sub)
    mark(stage, {"revision_id": str(project.revision_id)})
    assert risks.declare().status_code == 201
    before = risks.risk(dismissed)["lock_version"]
    assert deletion_lacks(risks, sub) == ["subproject_not_cited"]
    assert refusal(deleted(risks, sub)) == (
        409,
        CONDITION,
        {"missing_condition": "subproject_not_cited"},
    )
    for revision_id in (project.revision_id, None):
        kept = risks.risk(dismissed, revision_id)
        assert (kept["provision_subproject_id"], kept["lock_version"]) == (sub, before)


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-DAT-0080-A")
def test_an_undoing_that_would_give_back_a_designation_set_to_null_is_refused_as_restoring_it(
    risks: Risks, who: Person
) -> None:
    # #732: the dismissal undone would bring the provision line back on the subproject deleted
    # since. The deletion advanced the counter of the risk and carried it to the stacks: the entry
    # is no conflict (``UNDO_CONFLICT``), it is refused by ``restored_subproject_exists``, and
    # nothing is undone.
    sub = risks.subproject("LOT-Z")
    dismissed = dismissed_by(risks, who, sub)
    assert deleted(risks, sub).status_code == 204
    path = f"{risks.base}/revisions/{risks.project.revision_id}/undo"
    assert refusal(risks.api.post(path, headers=who.headers)) == (
        409,
        CONDITION,
        {"missing_condition": "restored_subproject_exists"},
    )
    after = risks.risk(dismissed)
    assert (after["state"], after["provision_node_id"], after["provision_subproject_id"]) == (
        "dismissed",
        None,
        None,
    )
    assert after["lock_version"] == dismissed["lock_version"] + 1
