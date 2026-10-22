# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the cycle of the revisions and the amendments of the witness (K4, EP-15/US-0490).

The examples of the writes of the cycle — a revision created, the reference designated, the rates
updated, an amendment opened, a merge queued — are written by hand in the chronology of the
witness, and the refusals the commands of a revision say in advance: these tests date them and
hold them to the readings they follow. They try the simplifications of the fake back, not the
Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
from datetime import timedelta
from typing import Any

import pytest

from wftools import mockhistory, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import AMENDMENT_MERGED, ORDER_RECEIVED, TODAY

WITNESS = universe(1)


@pytest.fixture(scope="module")
def examples() -> dict[str, Any]:
    """Read the examples of the universe, by the name of their file."""
    return {
        path.name: json.loads(path.read_text(encoding="utf-8"))["value"]
        for path in sorted(mockwitness.FIXTURES.glob("*.json"))
    }


# --- The cycle of the revisions and the amendments (K4, EP-15/US-0490, US-0510) -----------------

_TODAY = mockhistory.stamp(TODAY)
_DESIGNATION = "designate_reference"


def test_the_revision_created_is_the_one_the_project_created_today_reads() -> None:
    # createRevision answers the revision 103 opened at 14 h 05 on the project created at the same
    # hour, the one its readings show, at its first version.
    created = mockwitness.fixture("revision_created")
    assert created == mockwitness.fixture("revision_without_tasks")
    opened = mockwitness.fixture("project_revision_opened")
    assert opened["current_revision_id"] == created["revision_id"]
    assert created["project_id"] == mockwitness.fixture("project_created")["project_id"]
    assert (created["audit"]["created_at"], created["audit"]["updated_at"]) == (_TODAY, _TODAY)
    assert (created["status"], created["lock_version"]) == ("draft", 1)


def test_the_offer_is_designated_at_the_order_and_the_project_passes_in_progress() -> None:
    # The offer v1.0, marked in pricing, designated reference at the order received: the project
    # passes in progress at that instant, which its transitions and the journal say (WF-CYC-0030,
    # WF-REV-0040); its version is behind the one it bears today.
    designated, today = (mockwitness.fixture(name) for name in ("reference_designated", "project"))
    at = mockhistory.stamp(ORDER_RECEIVED.instant)
    assert (designated["project_id"], designated["state"]) == (WITNESS, "in_progress")
    assert designated["reference_revision_id"] == mockhistory.OFFER
    assert designated["current_revision_id"] == mockhistory.REFERENCE
    assert designated["audit"]["updated_at"] == at
    # Version 5 at the designation; the merge of the amendment 1 and the opening of the current
    # revision bring it to 7, the one it bears today.
    assert (designated["lock_version"], today["lock_version"]) == (5, 7)
    created, _ = mockhistory.REVISIONS[mockhistory.REFERENCE]
    _, marked = mockhistory.REVISIONS[mockhistory.OFFER]
    assert marked is not None
    assert marked.instant < created.instant < ORDER_RECEIVED.instant
    transitions = mockwitness.fixture("state_transitions")
    assert ("in_progress", at) in [(each["to_state"], each["occurred_at"]) for each in transitions]
    journal = mockwitness.fixture("audit_events")["items"]
    assert any(
        (each["action"], each["object"]["object_id"], each["occurred_at"])
        == ("reference_designate", mockhistory.OFFER, at)
        for each in journal
    )


def test_the_rates_are_accepted_from_the_reference_in_progress_before_its_marking() -> None:
    # C-362: the update, still proposed from the revision in progress, is accepted on the revision
    # 101 a quarter of an hour after its opening, for the categories its proposal presents; the
    # version it leaves is the one its marked readings keep.
    applied = mockwitness.fixture("rate_update_applied")
    marked = mockwitness.fixture("revision_marked")
    assert applied["revision_id"] == marked["revision_id"] == mockhistory.REFERENCE
    assert applied["reference_year"] == mockwitness.fixture("rate_update")["target_year"]
    # Opened at its first version, the revision 101 passes to 2 by the update, which its marked
    # readings keep.
    assert (applied["lock_version"], marked["lock_version"]) == (2, 2)
    commands = {each["command"]: each for each in applied["available_commands"]}
    assert commands["designate_reference"]["missing_conditions"] == ["revision_marked"]
    assert commands["merge_structure"]["missing_conditions"] == ["unmerged_amendment_exists"]
    assert commands["create_structure"]["is_available"]


def test_the_amendment_2_is_opened_in_the_reference_while_the_amendment_1_is_open() -> None:
    # createCostStructure answers the amendment 2 at its first version, not merged, in the
    # revision 101, while the amendment 1 is open there: the two differentials the readings of 101
    # list, the amendment 1 merged since, which marks it, the amendment 2 still not, which the
    # current revision took over (WF-REV-0100, #1211).
    created = mockwitness.fixture("amendment_created")
    amendments = {
        each["structure_id"]: each
        for each in mockwitness.fixture("structures_amendments")
        if each["kind"] == "amendment"
    }
    listed = amendments.pop(created["structure_id"])
    [first] = amendments.values()
    assert (created["revision_id"], created["kind"]) == (mockhistory.REFERENCE, "amendment")
    assert first["revision_id"] == listed["revision_id"] == mockhistory.REFERENCE
    assert created["label"] == listed["label"]
    assert (created["is_merged"], listed["is_merged"], first["is_merged"]) == (False, False, True)
    assert created["lock_version"] == listed["lock_version"]
    assert all(each["is_available"] for each in created["available_commands"])
    journal = mockwitness.fixture("audit_events")["items"]
    merge = mockhistory.stamp(AMENDMENT_MERGED.instant)
    assert any(
        (each["action"], each["object"]["label"], each["occurred_at"])
        == ("amendment_merge", first["label"], merge)
        for each in journal
    )
    [taken_over] = [
        each
        for each in mockwitness.fixture("structures")
        if each["kind"] == "amendment" and not each["is_merged"]
    ]
    assert (taken_over["revision_id"], taken_over["label"]) == (
        mockhistory.CURRENT,
        created["label"],
    )


def test_the_merge_of_the_amendment_2_is_queued_today_or_refused_stale() -> None:
    # The amendment 2, the differential of the current revision left to merge (#791): its merge
    # confirmed today is queued; confirmed with the counter of a report read before an entry, it is
    # refused with the counter the differential bears.
    queued = mockwitness.fixture("task_merge_queued")
    stale = mockwitness.fixture("merge_report_stale")
    assert (queued["kind"], queued["status"]) == ("structure_merge", "queued")
    # The sequel of a write of today, minutes after it, at an instant of its own.
    later = mockhistory.stamp(TODAY + timedelta(minutes=10))
    assert _TODAY < queued["submitted_at"] <= later
    [amendment] = [
        each
        for each in mockwitness.fixture("structures")
        if each["kind"] == "amendment" and not each["is_merged"]
    ]
    assert amendment["revision_id"] == mockhistory.CURRENT
    assert stale["params"] == {"expected_lock_version": amendment["lock_version"]}
    report = mockwitness.fixture("structure_merge_report")
    assert report["amendment_lock_version"] == amendment["lock_version"]


# --- The commands of a draft revision (#1102, #1211) -------------------------------------------


def _command(revision: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the availability of a command a revision lists, by its name."""
    [found] = [each for each in revision["available_commands"] if each["command"] == name]
    return found


@pytest.mark.parametrize(
    ("readings", "listed"),
    [
        (
            ("revision.json", "revision_marking.json", "revision_importing.json"),
            "structures.json",
        ),
        (("revision_without_tasks.json",), "structures_without_tasks.json"),
    ],
    ids=["current", "without_tasks"],
)
def test_a_revision_offers_the_merge_iff_it_bears_a_differential_not_merged(
    examples: dict[str, Any], readings: tuple[str, ...], listed: str
) -> None:
    # `merge_structure` misses `unmerged_amendment_exists` when no differential of the revision
    # is left to merge (#1102): the readings of a draft revision say what its `structures` lists —
    # the current revision bears the amendment 2, the revision opened on the project created today
    # none. The opening of a differential misses neither: several coexist (WF-REV-0100, #1211).
    first = examples[readings[0]]
    unmerged = any(
        each["kind"] == "amendment" and not each["is_merged"]
        for each in examples[listed]
        if each["revision_id"] == first["revision_id"]
    )
    assert unmerged is (readings[0] == "revision.json")
    drafts = [
        *(examples[name] for name in readings),
        *(
            each
            for each in examples["revisions.json"]["items"]
            if each["revision_id"] == first["revision_id"]
        ),
    ]
    for revision in drafts:
        assert revision["revision_id"] == first["revision_id"]
        merge = _command(revision, "merge_structure")
        create = _command(revision, "create_structure")
        assert ("unmerged_amendment_exists" in merge["missing_conditions"]) is not unmerged
        assert "unmerged_amendment_exists" not in create["missing_conditions"]
    # Without a background task running, nothing else is missing: the merge is offered if and
    # only if a differential is left to merge, the opening of another whether one is or not.
    for revision in (examples[readings[0]], *drafts[len(readings) :]):
        assert _command(revision, "merge_structure")["is_available"] is unmerged
        create = _command(revision, "create_structure")
        assert (create["is_available"], create["missing_conditions"]) == (True, [])
    # During a marking or an import, the background task alone is missing to the opening.
    for revision in drafts[1 : len(readings)]:
        missing = _command(revision, "create_structure")["missing_conditions"]
        assert missing == ["no_background_task_running"]


def test_the_designation_of_the_current_revision_misses_its_marking_then_its_correction(
    examples: dict[str, Any],
) -> None:
    # `designate_reference` lists its conditions in the order its 409 refuses by: the current
    # revision 102 is not marked, and the designation no longer corrects itself, the witness
    # having received actual costs and marked the revision 101 since the offer was designated
    # (WF-REV-0040); the revision opened on the project created today misses neither.
    current = [
        *(
            examples[name]
            for name in ("revision.json", "revision_marking.json", "revision_importing.json")
        ),
        *(
            each
            for each in examples["revisions.json"]["items"]
            if each["revision_id"] == mockhistory.CURRENT
        ),
    ]
    assert len(current) == 4
    for revision in current:
        missing = _command(revision, "designate_reference")["missing_conditions"]
        assert missing[:2] == ["revision_marked", "reference_correctable"]
    marked = _command(examples["revision_marked.json"], "designate_reference")
    assert marked["missing_conditions"] == ["reference_correctable"]
    created = _command(examples["revision_created.json"], "designate_reference")
    assert "reference_correctable" not in created["missing_conditions"]


def test_the_history_read_before_the_designation_offers_it_on_one_marked_revision_alone(
    examples: dict[str, Any],
) -> None:
    # revisions_designation_open (US-0490/L2): the history on 15 January, the order received and
    # the offer not yet designated, before any actual cost — the one example where a marked
    # revision lists the designation available, for the screen that offers it. Exactly one does,
    # the offer v1.0, nothing missing; the revision 101, then in progress, misses its marking.
    items = examples["revisions_designation_open.json"]["items"]
    offered = [
        each
        for each in items
        if each["status"] == "marked" and _command(each, "designate_reference")["is_available"]
    ]
    assert [each["revision_id"] for each in offered] == [mockhistory.OFFER]
    [offer] = offered
    assert _command(offer, "designate_reference")["missing_conditions"] == []
    assert offer["is_reference"] is False
    assert [each["revision_id"] for each in items] == [mockhistory.REFERENCE, mockhistory.OFFER]
    current = _command(items[0], "designate_reference")
    assert (current["is_available"], current["missing_conditions"]) == (False, ["revision_marked"])
    # An earlier instant of the chronology: no designation yet, and no actual cost.
    assert all(ORDER_RECEIVED.instant < each.instant for each in mockwitness.COST_IMPORTS)
    # A revision at one version has one content (#421): the offer is the one revisions lists, its
    # designation aside, and the 101 the one the update of the rates left.
    [listed] = [
        each
        for each in examples["revisions.json"]["items"]
        if each["revision_id"] == mockhistory.OFFER
    ]
    assert {**offer, "available_commands": None} == {**listed, "available_commands": None}
    others = [
        [each for each in revision["available_commands"] if each["command"] != _DESIGNATION]
        for revision in (offer, listed)
    ]
    assert others[0] == others[1]
    assert items[0] == examples["rate_update_applied.json"]
