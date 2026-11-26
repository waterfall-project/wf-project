# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference set, ``waterfall-api load-reference`` (US-2950/L1; WF-QUA-0040-A).

The draw first, without a base: the same seed gives the same set, the reference reaches the volumes
of table 13 with the witness's objects, and no address, no label, names anything real. Then the
command, on a copy of the witness: it starts from the witness, writes through the interfaces — a
rule of a module refuses what it would refuse from the API —, and two engenderings, one of them
stopped and taken up, give the same identifying data.

The full set — three hundred projects — takes minutes: the command is tried here on the witness and
three projects drawn, and on one project of each life, which the draw of the full set reaches; the
volumes of the reference are the full ones.
"""

import re
from dataclasses import replace
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from support import WITNESS
from witness_template import TEMPLATE, cloned

from waterfall.core.cost_settings.tables import CostCategory, HourlyRate
from waterfall.core.costs.tables import CostLine
from waterfall.core.planning.tables import Node
from waterfall.core.projects.interface import Viewer
from waterfall.core.projects.tables import Contributor, Project
from waterfall.core.resource_settings.tables import OrgNode, ResourceRole
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.tables import Risk
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import WitnessSettings
from waterfall.witness import reference_load
from waterfall.witness.description import Witness
from waterfall.witness.main import main
from waterfall.witness.portfolio import default_week
from waterfall.witness.reference_draw import (
    ACCOUNTS,
    CATEGORIES,
    DIRECTIONS,
    FIRST_NAMES,
    LAST_NAMES,
    NODES,
    PROJECTS,
    RATE_YEARS,
    ROLES,
    SERVICES,
    TRADES,
    Draw,
    draw_reference,
)
from waterfall.witness.reference_projects import (
    CLOSED,
    LIVES,
    SITES,
    WORKS,
    draw_project,
    manager_of,
    numbers_of,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from sqlalchemy.orm import Session
    from support import Logs

    from waterfall.witness.portfolio import Week
    from waterfall.witness.portfolio_slice import Project as Described
    from waterfall.witness.reference_draw import Base, Reference

REQUIREMENT = "WF-QUA-0040-A"
STORY = "US-2950"
DOMAIN = "@waterfall.test"
# The projects of the portfolio the command is tried with: the witness's eight (PRJ-002, held in
# ``created``, is not of them) and four drawn, the closed ones drawn between them in addition.
TRIED = 12
WITNESS_PORTFOLIO = 8
TRIED_NUMBERS = numbers_of(TRIED - WITNESS_PORTFOLIO)


def described() -> Witness:
    return Witness(WITNESS, Act(None, utc_now()))


def base() -> Base:
    return reference_load.read_base(described())


def drawn_projects(base_: Base, count: int = PROJECTS) -> list[Described]:
    reference = draw_reference(base_)
    return [
        draw_project(number, base_, reference) for number in numbers_of(count - base_.portfolio)
    ]


@pytest.mark.requirement(REQUIREMENT)
def test_two_draws_of_the_set_give_the_same_reference_and_the_same_projects() -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. »: the draw
    # reads the seed alone; a project does not depend on how many others are asked.
    first, second = base(), base()
    assert draw_reference(first) == draw_reference(second)
    assert drawn_projects(first) == drawn_projects(second)
    assert drawn_projects(first, 600)[: len(drawn_projects(first))] == drawn_projects(first)
    assert Draw("x", 1).below(10**9) == Draw("x", 1).below(10**9) != Draw("x", 2).below(10**9)


@pytest.mark.story(STORY)
def test_the_reference_drawn_and_the_witness_hold_the_volumes_of_table_13() -> None:
    # The set starts from the witness: its categories and its grid of fifteen years, and the nodes,
    # the roles and the accounts it lacks drawn up to forty, a hundred and fifty, five hundred.
    witness, held = described(), base()
    reference = draw_reference(held)
    categories = witness.read(
        reference_load.cost_categories.FILE, reference_load.cost_categories.CostCategories
    )
    counted = (held.nodes, held.roles, held.accounts, held.projects, held.portfolio)
    assert counted == (6, 5, 5, 12, 8)
    assert len(reference.nodes) + held.nodes == NODES == 40
    assert len(reference.roles) + held.roles == ROLES == 150
    assert len(reference.accounts) + held.accounts == ACCOUNTS == 500
    assert len(categories.items) == CATEGORIES == 200
    assert len(held.rated) == 28
    assert RATE_YEARS == 15
    # The projects "in the portfolio", in pricing and in progress, the witness's counted, are three
    # hundred; the closed ones, lost, abandoned, completed, come in addition.
    drawn = drawn_projects(held)
    closed = [each for each in drawn if _life(each) in CLOSED]
    assert len(drawn) - len(closed) + held.portfolio == PROJECTS == 300
    assert 0 < len(closed) < len(drawn)
    # Every code is unique, every role attached to a node drawn and a rated category of labour.
    assert len({each.code for each in reference.nodes}) == len(reference.nodes)
    assert len({each.code for each in reference.roles}) == len(reference.roles)
    services = {each.node_id for each in reference.nodes if each.parent_id is not None}
    assert {each.node_id for each in reference.roles} <= services
    assert {each.category_id for each in reference.roles} <= set(held.rated)
    assert len({each.email for each in reference.accounts}) == len(reference.accounts)


@pytest.mark.requirement(REQUIREMENT)
def test_the_set_drawn_holds_no_real_address_and_no_real_label_of_project() -> None:
    # « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. »: every address in
    # the domain reserved to the tests, every label composed of a kind of work, a star and a number.
    held = base()
    reference = draw_reference(held)
    assert all(each.email.endswith(DOMAIN) for each in reference.accounts)
    projects = drawn_projects(held)
    _assert_names_of_the_closed_lists(
        [each.label for each in reference.nodes],
        [each.label for each in reference.roles],
        [(each.last_name, each.first_name) for each in reference.accounts],
        [None if each.project.client is None else each.project.client.root for each in projects],
    )
    composed = re.compile(
        rf"^({'|'.join(map(re.escape, WORKS))}) ({'|'.join(map(re.escape, SITES))}) (\d+)$"
    )
    for number, each in enumerate(projects, start=1):
        matched = composed.match(each.project.label)
        assert matched is not None, each.project.label
        assert int(matched.group(3)) == number
        assert each.project.client is None or each.project.client.root.startswith("Client fictif ")


@pytest.mark.story(STORY)
def test_the_projects_drawn_take_every_life_within_the_years_the_grid_rates() -> None:
    # The six lives, every instant before November 2026 and every task in a rated year; a project
    # that ran has its reference, a manager among the accounts of the set.
    held = base()
    reference = draw_reference(held)
    projects = drawn_projects(held)
    lives = {_life(each) for each in projects}
    assert lives == {"pricing", "offered", "lost", "abandoned", "in_progress", "completed"}
    assert len(LIVES) == 6
    accounts = {each.user_id for each in reference.accounts}
    for number, each in enumerate(projects, start=1):
        instants = [each.created_at, *(move.occurred_at.root for move in each.transitions)]
        for revision in each.revisions:
            instants.extend(
                at for at in (revision.opened_at, revision.marked_at, revision.abandoned_at) if at
            )
        assert max(instants) < datetime(2026, 11, 1, tzinfo=UTC)
        for task in each.tasks:
            facet = task.node.task
            assert facet is not None
            assert facet.finish is not None
            assert date(2024, 1, 1) <= facet.finish.date.root <= date(2026, 12, 31)
        assert manager_of(number, reference) in accounts
        assert (each.reference_revision_id is not None) == (
            _life(each) in {"in_progress", "completed"}
        )
        _assert_tasks_follow_the_reviews(each)


def _assert_tasks_follow_the_reviews(project: Described) -> None:
    """Check a task is finished only before the last review marked, or by a completed project.

    A project in progress keeps a task open; a task not begun by the last review is not finished.
    """
    life = _life(project)
    reviewed = max(
        (each.marked_at for each in project.revisions if each.marked_at is not None), default=None
    )
    if life not in {"in_progress", "completed"}:
        assert all(each.started_on is None and each.completed_on is None for each in project.tasks)
        return
    assert reviewed is not None
    if life == "completed":
        assert all(each.completed_on is not None for each in project.tasks)
    else:
        assert any(each.completed_on is None for each in project.tasks)
    for task in project.tasks:
        if task.completed_on is not None:
            assert task.started_on is not None
            assert task.completed_on <= reviewed.date()


def _assert_names_of_the_closed_lists(
    nodes: Iterable[str],
    roles: Iterable[str],
    names: Iterable[tuple[str, str]],
    clients: Iterable[str | None],
) -> None:
    """No label of a node, of a role or of a client, no name, outside the lists the draw closes.

    The third sentence of the requirement: what a set holds is drawn from lists of fictitious words.
    """

    def one_of(words: Iterable[str]) -> str:
        return "|".join(map(re.escape, words))

    services = rf"({one_of(SERVICES)}) ({one_of(DIRECTIONS)}) \d\d"
    for label in nodes:
        assert re.fullmatch(rf"Direction ({one_of(DIRECTIONS)})|{services}", label), label
    for label in roles:
        assert re.fullmatch(rf"({one_of(TRADES)}) \d{{3}}", label), label
    for last_name, first_name in names:
        assert first_name in FIRST_NAMES
        assert last_name in LAST_NAMES
    for client in clients:
        assert client is None or re.fullmatch(r"Client fictif \d\d", client), client


def _life(project: Described) -> str:
    states = [move.to_state.value for move in project.transitions]
    if states[-1] == "pricing":
        return "offered" if project.revisions[0].marked_at else "pricing"
    return states[-1]


# The command, on a copy of the witness.


def settings(url: str) -> WitnessSettings:
    return WitnessSettings(database_url=SecretStr(url), witness_path=str(WITNESS))


def settings_at(url: str, witness_path: Path) -> WitnessSettings:
    return WitnessSettings(database_url=SecretStr(url), witness_path=str(witness_path))


def identifying(database: Database) -> dict[str, list[tuple[object, ...]]]:
    """Give what identifies the objects of the platform: identifiers, codes, labels, names."""
    queries = {
        "org_node": select(OrgNode.id, OrgNode.code, OrgNode.label, OrgNode.parent_id),
        "resource_role": select(
            ResourceRole.id, ResourceRole.code, ResourceRole.label, ResourceRole.cost_category_id
        ),
        "user_account": select(
            UserAccount.id, UserAccount.last_name, UserAccount.first_name, UserAccount.email
        ),
        "project": select(Project.id, Project.code, Project.label, Project.client, Project.state),
        "contributor": select(
            Contributor.project_id, Contributor.user_account_id, Contributor.kind
        ),
        "revision": select(
            Revision.id, Revision.project_id, Revision.status, Revision.version_name
        ),
        "node": select(Node.id, Node.lineage_id, Node.kind, Node.revision_id),
        "risk": select(Risk.id),
        "cost_line": select(CostLine.id, CostLine.document_number, CostLine.amount),
    }
    with database.transaction() as session:
        return {
            name: sorted(tuple(str(value) for value in row) for row in session.execute(query))
            for name, query in queries.items()
        }


def count(database: Database, model: Any) -> int:
    with database.transaction() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


@pytest.mark.story(STORY)
def test_the_set_starts_from_the_witness_and_reaches_the_volumes_of_its_reference(
    witness: Database, service_database_url: str, logs: Logs
) -> None:
    # The witness held, the command writes nothing of it, then the reference and three projects.
    before = identifying(witness)
    assert reference_load.load_reference(settings(service_database_url), TRIED) == 0
    after = identifying(witness)
    for name, rows in before.items():
        assert set(rows) <= set(after[name]), name
    # Nothing the platform holds beside the witness's is outside the lists the draw closes.
    new = {name: set(after[name]) - set(before[name]) for name in after}
    _assert_names_of_the_closed_lists(
        [row[2] for row in new["org_node"]],
        [row[2] for row in new["resource_role"]],
        [(row[1], row[2]) for row in new["user_account"]],
        [None if row[3] == "None" else row[3] for row in new["project"]],
    )
    assert count(witness, OrgNode) == NODES
    assert count(witness, ResourceRole) == ROLES
    assert count(witness, UserAccount) == ACCOUNTS
    assert count(witness, Project) == 12 + len(TRIED_NUMBERS)
    with witness.transaction() as session:
        held_in_portfolio = session.scalar(
            select(func.count()).where(Project.state.in_(("pricing", "in_progress")))
        )
    assert held_in_portfolio == TRIED
    with witness.transaction() as session:
        years = set(session.scalars(select(HourlyRate.year).distinct()))
        categories = session.scalar(select(func.count()).select_from(CostCategory))
        emails = list(session.scalars(select(UserAccount.email)))
    assert len(years) == RATE_YEARS
    # The two hundred of the witness, and the provision the bootstrap writes beside them.
    assert categories == CATEGORIES + 1
    assert all(each is not None and each.endswith(DOMAIN) for each in emails)
    assert [record["projects"] for record in logs.named("reference.loaded")] == [len(TRIED_NUMBERS)]


@pytest.mark.requirement(REQUIREMENT)
def test_two_engenderings_one_stopped_and_taken_up_give_the_same_identifying_data(
    witness: Database,
    service_database_url: str,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    logs: Logs,
) -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. »: on two copies
    # of the witness, the set loaded at once on one; on the other, stopped at its second project —
    # the first kept, its own transaction — then taken up where it stopped.
    assert reference_load.load_reference(settings(service_database_url), TRIED) == 0
    first = identifying(witness)
    template = request.config.stash[TEMPLATE]
    written = reference_load.write_project

    def failing(session: Session, act: Act, project: Described, who: tuple[Viewer, Week]) -> None:
        if project.code == "REF-0002":
            message = "the machine stopped"
            raise RuntimeError(message)
        written(session, act, project, who)

    with cloned(template, request.getfixturevalue("process_database_url")) as url:
        other = template.as_service(url)
        monkeypatch.setattr(reference_load, "write_project", failing)
        assert reference_load.load_reference(settings(other), TRIED) == 1
        assert [record["project"] for record in logs.named("reference.failed")] == ["REF-0002"]
        second = Database(create_database_engine(other))
        try:
            assert count(second, Project) == 13  # the witness's twelve and REF-0001
            monkeypatch.setattr(reference_load, "write_project", written)
            logs.clear()
            assert reference_load.load_reference(settings(other), TRIED) == 0
            loaded = logs.named("reference.loaded")
            assert [(each["reference"], each["projects"], each["held"]) for each in loaded] == [
                (False, len(TRIED_NUMBERS) - 1, 1)
            ]
            assert identifying(second) == first
        finally:
            second.dispose()


def combination(project: Described) -> tuple[str, int, int, bool]:
    """Give what the draw varies: life, revisions, risks, and whether the project has 8 tasks."""
    return (_life(project), len(project.revisions), len(project.risks), len(project.tasks) == 8)


def tranche(held: Base) -> dict[tuple[str, int, int, bool], int]:
    """Give, of each combination the draw of the full set produces, the number of its first project.

    A life, a number of revisions — from one review to six for a project in progress —, none or two
    risks (each with its own estimate), eight tasks or fewer: about fifty of the three hundred.
    """
    found: dict[tuple[str, int, int, bool], int] = {}
    for number, each in enumerate(drawn_projects(held), start=1):
        found.setdefault(combination(each), number)
    return found


@pytest.mark.story(STORY)
def test_a_tranche_of_projects_covering_every_combination_of_the_draw_is_written_by_the_rules(
    witness: Database,
) -> None:
    # The rules of the modules, applied to the projects the draw produces, not to a few of them: one
    # project for each combination of life, reviews (one to six), risks (none to two), own estimate
    # and eight tasks the full set holds, accepted as the API accepts them, and written once only.
    # About fifty projects, a minute or less: the full set, three hundred, is loaded by the command.
    described_, held = described(), base()
    reference = draw_reference(held)
    chosen = tranche(held)
    covered = list(chosen)
    assert {each[0] for each in covered} == {name for name, _ in LIVES}
    assert {each[1] for each in covered if each[0] == "in_progress"} == set(range(3, 9))
    assert {each[2] for each in covered} == {0, 1, 2}
    assert {True, False} == {each[3] for each in covered}
    week = default_week(described_)
    with (
        logging_context(correlation_id="reference-lives"),
        witness.transaction() as session,
    ):
        assert reference_load.write_reference(session, described_, reference)
        for number in sorted(chosen.values()):
            project = draw_project(number, held, reference)
            who = (Viewer(manager_of(number, reference), ()), week)
            assert reference_load.write_drawn_project(described_, project, who, session)
            assert not reference_load.write_drawn_project(described_, project, who, session)
        states = {
            row.code: row.state for row in session.execute(select(Project.code, Project.state))
        }
        assert (session.scalar(select(func.count()).select_from(Risk)) or 0) > 0
    assert {states[f"REF-{number:04d}"] for number in chosen.values()} == {
        "pricing",
        "lost",
        "abandoned",
        "in_progress",
        "completed",
    }


@pytest.mark.story(STORY)
def test_a_rule_of_a_module_refuses_a_role_drawn_and_the_reference_is_not_written(
    witness: Database, service_database_url: str, monkeypatch: pytest.MonkeyPatch, logs: Logs
) -> None:
    # Through the interfaces, never by an INSERT: a role drawn under the code of a role of the
    # witness is refused by the rule of the roles (409), and nothing of the reference stays.
    reference = reference_load.draw_reference(base())
    first = reference.roles[0]
    changed = replace(reference, roles=(replace(first, code="AUTOM"), *reference.roles[1:]))

    def drawn(_: Base) -> Reference:
        return changed

    monkeypatch.setattr(reference_load, "draw_reference", drawn)
    assert reference_load.load_reference(settings(service_database_url), TRIED) == 1
    refused = logs.named("reference.refused")
    assert [(each["code"], each["project"]) for each in refused] == [("ALREADY_EXISTS", None)]
    assert count(witness, OrgNode) == 6
    assert count(witness, Project) == 12


@pytest.mark.story(STORY)
def test_the_command_loads_the_witness_then_refuses_fewer_projects_than_it_holds(
    witness: Database,
    service_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("WATERFALL_DATABASE_URL", service_database_url)
    monkeypatch.setenv("WATERFALL_WITNESS_PATH", str(WITNESS))
    assert main(["load-reference", "--projects", "7"]) == 2
    assert "--projects: 7 is fewer than the 8 projects of the witness in the portfolio" in (
        capsys.readouterr().err
    )
    assert count(witness, OrgNode) == 6
    with pytest.raises(SystemExit) as stopped:
        main(["load-reference", "--projects", "many"])
    assert stopped.value.code == 2


@pytest.mark.story(STORY)
def test_the_command_stops_with_the_witness_when_the_witness_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WATERFALL_DATABASE_URL", "postgresql://nowhere/waterfall")
    monkeypatch.setenv("WATERFALL_WITNESS_PATH", str(tmp_path / "absent"))
    assert main(["load-reference"]) == 2


@pytest.mark.story(STORY)
def test_a_description_the_witness_lacks_ends_the_command_with_a_log_not_a_trace(
    tmp_path: Path, logs: Logs
) -> None:
    # The description read before the platform is touched: a file absent, a provision lacking, and
    # the command ends (1) with ``reference.failed``, as any failure of the set does.
    unreadable = settings_at("postgresql://nowhere/waterfall", tmp_path / "absent")
    assert reference_load.load_reference(unreadable, PROJECTS) == 1
    assert [each["project"] for each in logs.named("reference.failed")] == [None]
