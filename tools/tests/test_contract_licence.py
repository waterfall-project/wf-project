# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The licence the contract declares is the one ``REUSE.toml`` gives its file (#2285; WF-QUA-0010)."""

import re
import tomllib
from typing import Any

import pytest
import yaml

from wftools import REPOSITORY

CONTRACT = "docs/api/openapi.yaml"


def covers(pattern: str, path: str) -> bool:
    """Tell whether a REUSE glob covers a path: ``**`` crosses folders, ``*`` does not."""
    expression = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return re.fullmatch(expression, path) is not None


def licence_of(path: str) -> str:
    """Read the SPDX identifier ``REUSE.toml`` gives a file: the last annotation that covers it."""
    annotations: list[dict[str, Any]] = tomllib.loads(
        (REPOSITORY / "REUSE.toml").read_text(encoding="utf-8")
    )["annotations"]
    found = [
        each["SPDX-License-Identifier"]
        for each in annotations
        if any(
            covers(glob, path)
            for glob in ([each["path"]] if isinstance(each["path"], str) else each["path"])
        )
    ]
    assert found, f"no annotation of REUSE.toml covers {path}"
    return str(found[-1])


@pytest.mark.requirement("WF-QUA-0010")
def test_the_licence_the_contract_declares_is_the_one_reuse_gives_its_file() -> None:
    declared = yaml.safe_load((REPOSITORY / CONTRACT).read_text(encoding="utf-8"))["info"]["license"]
    assert declared["identifier"] == licence_of(CONTRACT)
