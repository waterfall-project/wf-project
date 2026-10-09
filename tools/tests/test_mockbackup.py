# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the examples of the deposit of a backup, its restoration and the accounts it concerns.

They try the coherence of the fixtures against each other and against the contract, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import math
import re
from typing import Any

import pytest

from wftools import REPOSITORY, mockwitness

_SCHEMAS = REPOSITORY / "docs/api/components"
_DEPOSITS = ("chunked_upload", "chunked_upload_part")
"""The two states of an open deposit: nothing received, then the first two parts."""


def _enumeration(file: str, name: str) -> list[str]:
    """Return the values of a string enumeration of the contract, in the order it lists them."""
    text = (_SCHEMAS / file).read_text(encoding="utf-8")
    block = text.split(f"\n{name}:\n", 1)[1].split("\n\n", 1)[0]
    after = block.split("  enum:\n", 1)[1]
    return re.findall(r"^    - (\w+)$", after, flags=re.MULTILINE)


def _part_size_bounds() -> tuple[int, int]:
    """Return the smallest and the largest `part_size_bytes` the schema of a deposit admits."""
    text = (_SCHEMAS / "schemas/exchanges.yaml").read_text(encoding="utf-8")
    block = text.split("    part_size_bytes:\n", 1)[1].split("    part_count:", 1)[0]
    low = re.search(r"minimum: (\d+)", block)
    high = re.search(r"maximum: (\d+)", block)
    assert low is not None
    assert high is not None
    return int(low.group(1)), int(high.group(1))


def _deposit(name: str) -> dict[str, Any]:
    """Return an open deposit of the universe."""
    value: dict[str, Any] = mockwitness.fixture(name)
    return value


@pytest.mark.parametrize("name", _DEPOSITS)
def test_a_deposit_is_cut_into_the_parts_its_size_and_its_part_size_say(name: str) -> None:
    deposit = _deposit(name)
    smallest, largest = _part_size_bounds()
    assert smallest <= deposit["part_size_bytes"] <= largest
    assert deposit["part_count"] == math.ceil(deposit["size_bytes"] / deposit["part_size_bytes"])
    received = deposit["received_parts"]
    assert received == sorted(set(received))
    assert all(1 <= number <= deposit["part_count"] for number in received)


def test_the_part_size_is_bounded_by_what_the_front_carries() -> None:
    # The bound of the body of a server action of the front, that of the imports: 10 Mio.
    assert _part_size_bounds() == (5 * 1024 * 1024, 10 * 1024 * 1024)


def test_the_completed_deposit_is_the_file_that_was_opened() -> None:
    opened = _deposit("chunked_upload")
    completed = mockwitness.fixture("chunked_upload_completed")
    assert completed["size_bytes"] == opened["size_bytes"]
    assert completed["filename"] == opened["filename"]
    assert completed["purpose"] == "external_backup"


def test_the_incomplete_deposit_names_the_parts_the_deposit_lacks() -> None:
    deposit = _deposit("chunked_upload_part")
    lacking = sorted(set(range(1, deposit["part_count"] + 1)) - set(deposit["received_parts"]))
    refused = mockwitness.fixture("chunked_upload_incomplete")
    assert refused["code"] == "STATE_FORBIDS_OPERATION"
    assert refused["params"] == {"missing_parts": lacking}


def test_a_part_of_the_wrong_size_is_refused_with_the_size_the_deposit_expects() -> None:
    deposit = _deposit("chunked_upload")
    refused = mockwitness.fixture("chunked_upload_part_size_mismatch")
    assert refused["code"] == "VALIDATION_FAILED"
    [field] = refused["fields"]
    assert field["pointer"] == "/body"
    assert field["code"] in _enumeration("common.yaml", "ErrorCode")
    assert field["params"] == {
        "minimum": deposit["part_size_bytes"],
        "maximum": deposit["part_size_bytes"],
    }


def test_the_skipped_accounts_of_a_read_are_told_by_a_code_of_the_catalogue() -> None:
    text = (_SCHEMAS / "schemas/platform.yaml").read_text(encoding="utf-8")
    report = text.split("\nIdentitySyncReport:\n", 1)[1].split("\n\n", 1)[0]
    assert "code: { $ref: ../common.yaml#/ErrorCode }" in report
    assert "LAST_ADMINISTRATOR" in _enumeration("common.yaml", "ErrorCode")


def test_the_restoration_refused_for_a_newer_backup_names_the_two_versions() -> None:
    task = mockwitness.fixture("task_restore_backup_newer_version")
    assert task["kind"] == "restore"
    assert task["status"] == "failed"
    problem = task["problem"]
    assert problem["code"] == "BACKUP_FROM_NEWER_VERSION"
    assert problem["code"] in _enumeration("common.yaml", "ErrorCode")
    params = problem["params"]
    installed = mockwitness.fixture("system_status")["version"]
    assert params["installed_version"] == installed

    def release(version: str) -> tuple[int, ...]:
        return tuple(int(part) for part in version.split("."))

    assert release(params["backup_version"]) > release(params["installed_version"])


@pytest.mark.parametrize(
    ("name", "condition"),
    [
        ("password_link_not_local", "is_local_account"),
        ("password_link_deactivated", "is_active_account"),
    ],
)
def test_the_link_refused_to_an_account_names_a_condition_of_the_contract(
    name: str, condition: str
) -> None:
    refused = mockwitness.fixture(name)
    assert refused["code"] == "STATE_FORBIDS_OPERATION"
    assert refused["params"] == {"missing_condition": condition}
    assert condition in _enumeration("schemas/projects.yaml", "CommandCondition")
