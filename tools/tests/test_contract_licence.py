# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The licence the contract declares is the one ``REUSE.toml`` gives its file (#2285)."""

import re
import tomllib
from typing import Any

import yaml

from wftools import REPOSITORY

CONTRACT = "docs/api/openapi.yaml"


def covers(pattern: str, path: str) -> bool:
    """Tell whether a REUSE glob covers a path: ``**/`` is any folders, even none, ``*`` none."""
    expression = (
        re.escape(pattern)
        .replace(r"\*\*/", "(?:.*/)?")
        .replace(r"\*\*", ".*")
        .replace(r"\*", "[^/]*")
    )
    return re.fullmatch(expression, path) is not None


def licence_in(annotations: list[dict[str, Any]], path: str) -> str:
    """Pick the SPDX identifier of a file among annotations: ``override`` wins, else the last.

    REUSE lets an annotation whose precedence is ``override`` beat any other, wherever it stands;
    otherwise the last annotation covering the file decides. ``aggregate``, which would add
    licences, is not handled: the contract is covered by one licence.
    """
    found = [
        each
        for each in annotations
        if any(
            covers(glob, path)
            for glob in ([each["path"]] if isinstance(each["path"], str) else each["path"])
        )
    ]
    assert found, f"no annotation of REUSE.toml covers {path}"
    overriding = [each for each in found if each.get("precedence") == "override"]
    return str((overriding or found)[-1]["SPDX-License-Identifier"])


def licence_of(path: str) -> str:
    """Read the SPDX identifier ``REUSE.toml`` gives a file."""
    annotations: list[dict[str, Any]] = tomllib.loads(
        (REPOSITORY / "REUSE.toml").read_text(encoding="utf-8")
    )["annotations"]
    return licence_in(annotations, path)


def test_an_override_annotation_beats_a_later_one() -> None:
    annotations = [
        {"path": "docs/api/**", "SPDX-License-Identifier": "A", "precedence": "override"},
        {"path": "**/*.yaml", "SPDX-License-Identifier": "B", "precedence": "closest"},
    ]
    assert licence_in(annotations, "docs/api/openapi.yaml") == "A"
    assert licence_in(annotations[1:], "docs/api/openapi.yaml") == "B"


# No requirement covers the licence of the contract: the test cites none.
def test_the_licence_the_contract_declares_is_the_one_reuse_gives_its_file() -> None:
    contract = yaml.safe_load((REPOSITORY / CONTRACT).read_text(encoding="utf-8"))
    declared = contract["info"]["license"]
    assert declared["identifier"] == licence_of(CONTRACT)
