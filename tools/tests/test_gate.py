# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the gate that decides the outcome of the chain."""

import json
from collections.abc import Mapping

import pytest

from wftools import gate


def run(monkeypatch: pytest.MonkeyPatch, needs: Mapping[str, Mapping[str, object]]) -> int:
    """Run the gate on these job results."""
    monkeypatch.setenv("NEEDS", json.dumps(needs))
    return gate.main()


def test_successes_and_skips_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    needs = {"changes": {"result": "success"}, "spec": {"result": "skipped"}}
    assert run(monkeypatch, needs) == 0


@pytest.mark.parametrize("result", ["failure", "cancelled"])
def test_a_failed_or_cancelled_job_fails(monkeypatch: pytest.MonkeyPatch, result: str) -> None:
    needs = {"changes": {"result": "success"}, "spec": {"result": result}}
    assert run(monkeypatch, needs) == 1


def test_failures_are_named(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    run(monkeypatch, {"repo": {"result": "failure"}, "spec": {"result": "cancelled"}})
    assert "failed: repo, spec" in capsys.readouterr().err


def test_nothing_to_judge_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEEDS", raising=False)
    assert gate.main() == 1
