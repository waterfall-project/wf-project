# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the merge that fails on a loop or the horizon, and of one without a current revision.

EP-16/US-0640/L3, #788 and #790. They try the examples written by hand for these cases against the
witness they speak of and against the contract: the failure of `mergeCostStructure` and its report
naming the tasks of a loop of links or the task beyond the horizon, the command `merge_structure`
of the last marked revision of a project without a current revision, the report that says the
merge creates that revision, and the refusal once a revision is in progress — not the Vérif of a
requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from typing import Any

import pytest

from wftools import REPOSITORY, mockhistory
from wftools.mockids import universe
from wftools.mockwitness import AMENDMENT_MERGED, RISK_751_REVIEWED, N, fixture

PATHS = REPOSITORY / "docs" / "api" / "paths"
SCHEMAS = REPOSITORY / "docs" / "api" / "components" / "schemas"

REPORTS = (
    "structure_merge_report",
    "structure_merge_report_started_task",
    "structure_merge_report_refused",
    "structure_merge_report_provision_moved",
    "structure_merge_report_link_cycle",
    "structure_merge_report_horizon_exceeded",
    "structure_merge_report_without_current_revision",
)
"""Every example of `getStructureMergeReport`, in the order of the contract."""


def _operation(name: str, file: str = "revisions.yaml") -> str:
    """Return the text of an operation of the contract, from its identifier to the next one."""
    text = (PATHS / file).read_text(encoding="utf-8")
    return text.split(f"operationId: {name}\n", 1)[1].split("operationId:", 1)[0]


def _core() -> dict[str, dict[str, Any]]:
    """Return the tasks of the core of the witness, by their node."""
    return {node["node_id"]: node for node in fixture("nodes_core")["items"] if node.get("task")}


def _named(number: int) -> dict[str, Any]:
    """Return how a refusal names a task of the main structure: its node and its label."""
    node = universe(number)
    return {"node_id": node, "label": _core()[node]["task"]["label"]}


def _command(revision: dict[str, Any], name: str) -> tuple[bool, list[str]]:
    [command] = [each for each in revision["available_commands"] if each["command"] == name]
    return command["is_available"], command["missing_conditions"]


def test_every_report_before_a_merge_says_whether_the_merge_creates_the_current_revision() -> None:
    schema = (SCHEMAS / "revisions.yaml").read_text(encoding="utf-8")
    block = schema.split("\nStructureMergeReport:\n", 1)[1].split("\n\n", 1)[0]
    assert "- creates_current_revision" in block.split("properties:", 1)[0]
    report = _operation("getStructureMergeReport")
    for name in REPORTS:
        assert f"fixtures/api/{name}.json" in report, name
        creates = fixture(name)["creates_current_revision"]
        assert creates is (name == "structure_merge_report_without_current_revision"), name


@pytest.mark.parametrize(
    ("name", "code", "params"),
    [
        (
            "link_cycle",
            "LINK_CYCLE",
            {"cycle": [_named(N.FACTORY_ACCEPTANCE), _named(N.MOUNTING), _named(N.COMMISSIONING)]},
        ),
        ("horizon_exceeded", "PROJECT_HORIZON_EXCEEDED", {"task": _named(N.COMMISSIONING)}),
    ],
)
def test_a_merge_that_would_close_a_loop_or_pass_the_horizon_fails_as_its_report_says(
    name: str, code: str, params: dict[str, Any]
) -> None:
    # #788: WF-REV-0050 cites WF-PLA-0030 and WF-PLA-0150 among the motives that refuse a merge;
    # the task of the merge fails without merging anything, naming the tasks as its report does,
    # each by its node of the main structure and its label (WF-IHM-0080).
    task, report = fixture(f"task_merge_{name}"), fixture(f"structure_merge_report_{name}")
    assert (task["kind"], task["status"], task["result_url"]) == ("structure_merge", "failed", None)
    assert task["problem"] == {"code": code, "status": 422, "params": params}
    assert report["refusals"] == [{"code": code, "params": params}]
    assert (report["completed_tasks"], report["creates_current_revision"]) == ([], False)
    [main] = [each for each in fixture("structures") if each["kind"] == "main"]
    assert report["main_structure_lock_version"] == main["lock_version"]
    assert f"fixtures/api/task_merge_{name}.json" in _operation("getBackgroundTask", "system.yaml")
    assert f"`task_merge_{name}`" in _operation("mergeCostStructure")


def test_the_loop_is_named_from_its_first_task_in_the_plan_each_preceding_the_next() -> None:
    # The link the differential adds is named by its successor, whose predecessors bear it; the
    # loop it closes runs from the task first in the order of the plan, each preceding the next,
    # and a loop leaves the dates without a computation: the horizon is not judged beside it.
    report = fixture("structure_merge_report_link_cycle")
    [link] = report["differences"]
    factory, commissioning = (_core()[universe(n)] for n in (N.FACTORY_ACCEPTANCE, N.COMMISSIONING))
    assert (link["change"], link["target"], link["lineage_id"]) == (
        "added",
        "link",
        factory["lineage_id"],
    )
    assert (link["label"], link["predecessor_label"]) == (
        factory["task"]["label"],
        commissioning["task"]["label"],
    )
    [refusal] = report["refusals"]
    rows = [_core()[each["node_id"]]["row_number"] for each in refusal["params"]["cycle"]]
    assert rows[0] == min(rows)
    # The loop of the merge is the one the entry of the same predecessor closes (setPredecessors).
    assert refusal["params"]["cycle"] == fixture("predecessors_cycle_refused")["params"]["cycle"]


def test_the_task_beyond_the_horizon_is_the_one_that_finishes_last() -> None:
    # « Une saisie, un import ou une fusion qui la porterait au-delà est refusé, et le refus nomme
    # la tâche en cause » (WF-PLA-0150): for a merge, the task of the merged structure that
    # finishes last, but the summaries, which take their dates from their subordinates
    # (WF-PLA-0040) — the commissioning, a leaf, lengthened by the differential beyond any other.
    report = fixture("structure_merge_report_horizon_exceeded")
    [lengthened] = report["differences"]
    commissioning = _core()[universe(N.COMMISSIONING)]
    assert (lengthened["change"], lengthened["lineage_id"], lengthened["fields"]) == (
        "updated",
        commissioning["lineage_id"],
        ["duration"],
    )
    assert not commissioning["task"]["is_summary"]
    installation = _core()[universe(N.INSTALLATION)]
    assert installation["task"]["is_summary"]
    # Its summary finishes with it, and is not the task named.
    assert installation["task"]["finish"] == commissioning["task"]["finish"]


def test_the_last_marked_revision_offers_the_merge_while_the_project_has_no_current_one() -> None:
    # #790, WF-REV-0050 : « Lorsque le projet ne comporte pas de révision en cours, elle en crée une
    # au préalable ». The reference read on 1 February, marked by the merge of the amendment 1,
    # the day before the review of 751 opens the revision 102: an earlier instant of the chronology,
    # the reference the last marked revision, bearing the amendment 2 not merged.
    offered, marked = fixture("revision_marked_merge_offered"), fixture("revision_marked")
    assert offered["revision_id"] == marked["revision_id"] == mockhistory.REFERENCE
    assert offered["marked_at"] == mockhistory.stamp(AMENDMENT_MERGED.instant)
    assert AMENDMENT_MERGED.instant < RISK_751_REVIEWED.instant
    marked_at = {
        each["revision_id"]: each["marked_at"]
        for each in fixture("revisions")["items"]
        if each["status"] == "marked"
    }
    assert max(marked_at, key=lambda revision: marked_at[revision]) == mockhistory.REFERENCE
    assert _command(offered, "merge_structure") == (True, [])
    # Today the revision 102 is in progress: on the reference, the merge lacks its draft alone.
    assert _command(marked, "merge_structure") == (False, ["revision_draft"])
    others = [
        each for each in offered["available_commands"] if each["command"] != "merge_structure"
    ]
    assert others == [
        each for each in marked["available_commands"] if each["command"] != "merge_structure"
    ]
    assert {key: value for key, value in offered.items() if key != "available_commands"} == {
        key: value for key, value in marked.items() if key != "available_commands"
    }
    assert "fixtures/api/revision_marked_merge_offered.json" in _operation("getRevision")


def test_the_report_of_a_merge_without_current_revision_says_it_creates_it_then_refused_today() -> (
    None
):
    # The report read on the reference that day says the merge creates the current revision by
    # copy, merges into it and marks it; its differences are those of the amendment 2, which the
    # revision 102 took over with it. Today, a revision being in progress, the merge asked on the
    # reference is refused by the condition its command lacks, nothing merged, no revision created.
    report = fixture("structure_merge_report_without_current_revision")
    today = fixture("structure_merge_report")
    assert report["creates_current_revision"] is True
    assert report["differences"] == today["differences"]
    assert (report["completed_tasks"], report["refusals"]) == ([], [])
    refused = fixture("merge_revision_marked_refused")
    _, missing = _command(fixture("revision_marked"), "merge_structure")
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": missing[0]}
    for operation in ("getStructureMergeReport", "mergeCostStructure"):
        assert "fixtures/api/merge_revision_marked_refused.json" in _operation(operation)


def test_a_merge_creating_the_revision_is_refused_without_revisions_write_by_a_409() -> None:
    # WF-REV-0050: the command lists may_create_revision to a session that cannot create the
    # current revision, and the merge is refused by the condition the command names, as the imports
    # and declare_risk are: a 409, not a 403.
    refused = fixture("merge_may_create_revision_refused")
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": "may_create_revision"}
    assert "fixtures/api/merge_may_create_revision_refused.json" in _operation("mergeCostStructure")
