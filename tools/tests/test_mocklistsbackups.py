# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the readings of the list of the backups (#588).

They try the rules of sort, filter and commands the fake back applies on rows made for them, and
the examples against the list written by hand and the contract they illustrate — not the Vérif of
a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »). Split from
``test_mocklists.py`` at the reprise of main after EP-03, which brought it over its bound.
"""

import json
import re
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockdata, mocklists
from wftools.mockwitness import fixture

type Row = dict[str, Any]


@pytest.fixture(scope="module")
def lists() -> dict[str, Any]:
    """Read the examples of the lists back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mocklists.examples().items()
    }


def _enumeration(schema: str, name: str) -> list[str]:
    """Return the values of an enumeration of the contract, in its order."""
    text = (REPOSITORY / "docs/api/components/schemas" / schema).read_text(encoding="utf-8")
    found = re.search(rf"^{name}:\n(?:[ \t].*\n)*?\s+enum: \[([^\]]*)\]", text, re.MULTILINE)
    assert found is not None
    return [value.strip() for value in found.group(1).split(",")]


def _ids(rows: list[Row], key: str) -> list[str]:
    return [row[key] for row in rows]


def _backup(identifier: str, taken: str, size: int, state: tuple[str, str], *, kept: bool) -> Row:
    """Return a backup, `state` its verification and origin, its commands as the contract says."""
    verification, origin = state
    mark = "release" if kept else "retain"
    verified = [] if verification == "passed" else ["backup_verified"]
    return {
        "backup_id": identifier,
        "taken_at": taken,
        "size_bytes": size,
        "verification": verification,
        "is_retained": kept,
        "scope": "database",
        "origin": origin,
        "available_commands": [
            {"command": mark, "is_available": True, "missing_conditions": []},
            {"command": "download", "is_available": not verified, "missing_conditions": verified},
            {"command": "restore", "is_available": not verified, "missing_conditions": verified},
        ],
    }


BACKUPS: list[Row] = [
    _backup("b4", "2026-06-30T22:00:00Z", 400, ("pending", "scheduled"), kept=False),
    _backup("b3", "2026-06-03T01:00:00Z", 300, ("passed", "scheduled"), kept=False),
    _backup("b2", "2026-05-31T22:00:00Z", 350, ("failed", "scheduled"), kept=True),
    _backup("b1", "2026-01-30T17:45:00Z", 100, ("passed", "manual"), kept=True),
]
"""Backups around June in Paris, from 2026-05-31T22:00Z included to 2026-06-30T22:00Z excluded."""


def test_the_orders_of_the_backups_follow_the_enumerations_of_the_contract() -> None:
    assert list(mocklists.BACKUP_ORIGINS) == _enumeration("platform.yaml", "BackupOrigin")
    assert list(mocklists.BACKUP_VERIFICATIONS) == _enumeration(
        "platform.yaml", "BackupVerification"
    )
    # The conditions are listed one a line: the block of the enumeration names the one lacked.
    text = (REPOSITORY / "docs/api/components/schemas/projects.yaml").read_text(encoding="utf-8")
    conditions = text.split("\nCommandCondition:\n", 1)[1].split("\n\n", 1)[0]
    assert f"\n    - {mocklists.RUNNING_BACKUP}\n" in conditions


def test_the_period_of_the_backups_retains_the_instants_taken_from_included_to_excluded() -> None:
    start, end = mocklists.BACKUP_PERIOD
    # b2 at the very start is in, b4 at the very end is out.
    assert _ids(mocklists.taken_within(BACKUPS, start, end), "backup_id") == ["b3", "b2"]
    assert _ids(mocklists.taken_within(BACKUPS, end, None), "backup_id") == ["b4"]
    assert mocklists.taken_within(BACKUPS, start, start) == []
    with pytest.raises(ValueError, match="before it starts"):
        mocklists.taken_within(BACKUPS, end, start)


def test_the_backups_are_filtered_by_their_origin_and_their_marking() -> None:
    assert _ids(mocklists.of_origins(BACKUPS, ("manual",)), "backup_id") == ["b1"]
    assert _ids(mocklists.of_origins(BACKUPS, ()), "backup_id") == ["b4", "b3", "b2", "b1"]
    with pytest.raises(ValueError, match="no origin of a backup"):
        mocklists.of_origins(BACKUPS, ("nightly",))
    assert _ids(mocklists.marked(BACKUPS, retained=True), "backup_id") == ["b2", "b1"]
    assert _ids(mocklists.marked(BACKUPS, retained=False), "backup_id") == ["b4", "b3"]


def test_the_columns_of_the_backups_sort_as_the_contract_says() -> None:
    def sorted_ids(column: str, *, descending: bool = False) -> list[str]:
        return _ids(
            mocklists.ordered(BACKUPS, mocklists.BACKUP_KEYS[column], descending=descending),
            "backup_id",
        )

    assert sorted_ids("size_bytes") == ["b1", "b3", "b2", "b4"]
    assert sorted_ids("taken_at", descending=True) == ["b4", "b3", "b2", "b1"]
    # The enumerations in their order: pending, passed, failed; manual, scheduled. A tie keeps the
    # order of the list without sort.
    assert sorted_ids("verification") == ["b4", "b3", "b1", "b2"]
    assert sorted_ids("origin") == ["b1", "b4", "b3", "b2"]
    # The backups marked to be kept first in the ascending order.
    assert sorted_ids("is_retained") == ["b2", "b1", "b4", "b3"]


def test_a_reader_sees_no_command_and_a_running_backup_withholds_the_restoration() -> None:
    for backup in mocklists.without_commands(BACKUPS):
        assert backup["available_commands"] == []
    [first, *_, last] = mocklists.while_backup_runs(BACKUPS)
    commands = cast("list[Row]", first["available_commands"])
    by_command = {each["command"]: each for each in commands}
    # The restoration of an unverified backup lacks the verification and the running backup.
    assert by_command["restore"] == {
        "command": "restore",
        "is_available": False,
        "missing_conditions": ["backup_verified", "no_backup_running"],
    }
    assert by_command["download"]["missing_conditions"] == ["backup_verified"]
    assert by_command["retain"]["is_available"] is True
    [restore] = [
        each
        for each in cast("list[Row]", last["available_commands"])
        if each["command"] == "restore"
    ]
    assert restore == {
        "command": "restore",
        "is_available": False,
        "missing_conditions": ["no_backup_running"],
    }
    # Nothing else changes: the backups themselves are as they were.
    assert [{k: v for k, v in b.items() if k != "available_commands"} for b in BACKUPS] == [
        {k: v for k, v in b.items() if k != "available_commands"}
        for b in mocklists.while_backup_runs(BACKUPS)
    ]


def test_the_readings_of_the_backups_follow_their_parameters(lists: dict[str, Any]) -> None:
    written = fixture("backups")["items"]
    assert [row["available_commands"] for row in lists["backups_reader"]["items"]] == [
        [] for _ in written
    ]
    during = lists["backups_during_backup"]["items"]
    assert len(during) == len(written)
    for row in during:
        [restore] = [each for each in row["available_commands"] if each["command"] == "restore"]
        assert restore["is_available"] is False
        assert "no_backup_running" in restore["missing_conditions"]
    manual = lists["backups_manual"]
    assert [row["origin"] for row in manual["items"]] == ["manual"]
    assert manual["meta"]["total"] == 1
    kept = lists["backups_retained"]
    assert kept["items"] == [row for row in written if row["is_retained"] is True]
    period = lists["backups_period"]
    # June in Paris: the backups of 1, 2 and 3 June, the most recent first.
    assert [row["taken_at"][:10] for row in period["items"]] == [
        "2026-06-03",
        "2026-06-02",
        "2026-06-01",
    ]
    by_size = lists["backups_by_size"]["items"]
    sizes = [row["size_bytes"] for row in by_size]
    assert sizes == sorted(sizes)
    assert by_size[0]["origin"] == "manual"
    for name in ("backups_reader", "backups_manual", "backups_retained", "backups_period"):
        assert lists[name]["meta"]["total"] == len(lists[name]["items"]), name
