# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The example of a line refused for want of working hours is read by the generated model.

``import_estimate_task_without_hours`` is the one example of ``ImportRejection.params`` that
names roles and a task by their lineage (#768): the model of the contract must take it whole, the
roles and the task typed, nothing left to the open part of ``ProblemParams``.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from waterfall.api.contract.models import Import, ProblemImportedTask, ProblemResourceRole

pytestmark = pytest.mark.requirement("WF-ARC-0110-A")

EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "api"
    / "import_estimate_task_without_hours.json"
)


def test_the_model_reads_the_roles_and_the_task_of_the_rejected_line_typed() -> None:
    value: dict[str, Any] = json.loads(EXAMPLE.read_text(encoding="utf-8"))["value"]
    imported = Import.model_validate(value)
    assert imported.report is not None
    [rejection] = imported.report.rejected
    assert rejection.code.value == "TASK_WITHOUT_WORKING_HOURS"
    params = rejection.params
    assert params is not None
    assert params.resource_roles is not None
    assert all(isinstance(role, ProblemResourceRole) for role in params.resource_roles)
    assert params.tasks is not None
    assert all(isinstance(task, ProblemImportedTask) for task in params.tasks)
    assert params.model_extra == {}
    assert json.loads(imported.model_dump_json(exclude_unset=True)) == value
