# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The questions on the main structure of a revision to open, combined by AND (#4004).

``opening_main_with_tasks`` (projects) and ``main_structure_has_task`` (revisions) combine the
questions registered the same way: all must retain a project, and none registered retains none. The
registries are replaced for the test by registries of its own, and given back by ``monkeypatch``.

The tests cite no requirement: how the questions combine is a detail of realisation (#4004), which
no Vérif of an exigence judges.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.projects.interface import opening_main_with_tasks
from waterfall.core.revisions.interface import main_structure_has_task
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Collection

    import pytest

OPENING = "waterfall.core.projects.interface.skeleton._OPENING_MAIN"
MAIN_TASK = "waterfall.core.revisions.interface.reference._MAIN_TASK"
FIRST, SECOND, THIRD = (UUID(int=each) for each in (1, 2, 3))
NO_SESSION: Any = None


def keeping(*kept: UUID) -> Any:
    """Give a question that retains the projects named among those it is given."""

    def question(_session: object, project_ids: Collection[UUID]) -> frozenset[UUID]:
        return frozenset(project_ids) & frozenset(kept)

    return question


def answering(*, value: bool) -> Any:
    """Give a question on a main structure that always answers ``value``."""

    def question(_session: object, _selection: object) -> bool:
        return value

    return question


def test_no_project_is_retained_while_no_question_is_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(OPENING, Registry[Any]())
    assert opening_main_with_tasks(NO_SESSION, [FIRST, SECOND]) == frozenset()


def test_the_projects_retained_are_those_every_question_retains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    questions = Registry[Any]()
    questions.register(keeping(FIRST, SECOND))
    questions.register(keeping(SECOND, THIRD))
    monkeypatch.setattr(OPENING, questions)
    assert opening_main_with_tasks(NO_SESSION, [FIRST, SECOND, THIRD]) == {SECOND}
    assert opening_main_with_tasks(NO_SESSION, [FIRST]) == frozenset()


def test_a_main_structure_has_a_task_when_every_question_says_so_and_never_when_none_is_asked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MAIN_TASK, Registry[Any]())
    assert main_structure_has_task(NO_SESSION, FIRST, SECOND) is False
    for answers in ([True, True], [True, False]):
        questions = Registry[Any]()
        for value in answers:
            questions.register(answering(value=value))
        monkeypatch.setattr(MAIN_TASK, questions)
        assert main_structure_has_task(NO_SESSION, FIRST, SECOND) is all(answers)
