# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The header of each format keeps its refusal when parsed and raises it when judged (US-3190/L2).

``parse_header`` runs before the lock of the project and gives the refusal of a file that is no
workbook, no planning, instead of raising it; ``judge_header`` raises it under the lock, with the
same parameters.
"""

from typing import TYPE_CHECKING, Any

import pytest
from actual_costs_import_support import declare
from projects_support import scene as make_scene

from waterfall.core.costs.interface import ACTUAL_COSTS_FORMAT
from waterfall.core.estimate.interface import ESTIMATE_FORMAT, REMAINING_FORMAT
from waterfall.core.planning.interface import MS_PROJECT_FORMAT
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.mark.story("US-3190")
@pytest.mark.parametrize(
    ("form", "expected_format"),
    [
        (MS_PROJECT_FORMAT, "ms_project_schedule"),
        (ESTIMATE_FORMAT, "estimate"),
        (REMAINING_FORMAT, "remaining"),
        (ACTUAL_COSTS_FORMAT, "actual_costs"),
    ],
)
def test_the_four_formats_keep_the_refusal_of_a_head_they_parse_and_raise_it_when_they_judge(
    form: Any,
    expected_format: str,
    api: ContractClient,
    owner: Engine,
    database: Database,
    realm: TestRealm,
) -> None:
    make_scene(api, owner, database, realm)
    declare(database)
    parsed = form.parse_header(b"neither a workbook nor a planning")
    assert isinstance(parsed, UnprocessableError)
    assert parsed.__traceback__ is None
    with database.transaction() as session, pytest.raises(UnprocessableError) as raised:
        form.judge_header(session, parsed)
    assert raised.value.code == "FILE_FORMAT_UNREADABLE"
    assert raised.value.params["expected_format"] == expected_format
    assert raised.value.params == parsed.params
