# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The list of the projects (US-0920; WF-IHM-0120, WF-IHM-0130, WF-CYC-0010), through the service.

``listProjects`` on projects created through the service and put in a state, a code or a date
around it, every answer checked against the contract: what a caller may open, the states, the
search, the period, the sort and the pages.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from sqlalchemy import event
from projects_support import (
    PROJECTS,
    Person,
    Scene,
    contribute,
    create,
    person,
    put_in_state,
)
from projects_support import scene as make_scene

from waterfall.core.access_roles.predefined import PROJECT_MANAGER

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

STATES = ["created", "pricing", "in_progress", "completed", "lost", "abandoned"]
EVERY_STATE = f"states={','.join(STATES)}"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def listed(api: ContractClient, who: Person, query: str = "") -> dict[str, Any]:
    """Read the list as ``who`` does, with the query; give the body of a 200."""
    answer = api.get(f"{PROJECTS}?{query}", headers=who.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def labels(body: dict[str, Any]) -> list[str]:
    """Give the labels of a page, in its order."""
    return [item["label"] for item in body["items"]]


def at(stage: Scene, project: dict[str, Any], day: int) -> None:
    """Set the instant of the last change of a project, around the service."""
    moment = datetime(2026, 3, day, 10, tzinfo=UTC)
    put_in_state(stage.owner, project["project_id"], project["state"], updated_at=moment)


@pytest.mark.requirement("WF-IHM-0120-A")
def test_a_contributor_of_two_projects_sees_them_and_lifting_the_filter_shows_what_it_may_open(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # « Un contributeur de deux projets les voit à sa connexion ; la levée du filtre montre aussi
    # les projets qu'il peut ouvrir sans en être contributeur, et aucun autre. » : the reader holds
    # « consulter tous les projets », contributes to two of three projects; the outsider contributes
    # to one and may open no other.
    first = create(api, stage.manager, label="Un")
    second = create(api, stage.manager, label="Deux")
    other = person(stage.database, realm, *PROJECT_MANAGER)
    third = create(api, other, label="Trois")
    for project in (first, second):
        contribute(stage.database, project["project_id"], stage.reader, "contributor")
    contribute(stage.database, third["project_id"], stage.outsider, "contributor")
    mine = listed(api, stage.reader, f"{EVERY_STATE}&is_contributor=true")
    assert sorted(labels(mine)) == ["Deux", "Un"]
    assert mine["meta"]["total"] == 2
    every = listed(api, stage.reader, EVERY_STATE)
    assert sorted(labels(every)) == [
        "Deux",
        "Modernisation du poste de commande",
        "Trois",
        "Un",
    ]
    only = listed(api, stage.outsider, EVERY_STATE)
    assert labels(only) == ["Trois"]
    assert listed(api, stage.outsider, f"{EVERY_STATE}&is_contributor=true") == only
    assert labels(listed(api, other, EVERY_STATE)) == ["Trois"]
    # A caller that contributes to nothing and sees nothing is given the empty list.
    nobody = person(stage.database, realm, "project_settings.read")
    assert listed(api, nobody, EVERY_STATE) == {
        "items": [],
        "meta": {"limit": 50, "offset": 0, "total": 0, "states": STATES},
    }


@pytest.mark.requirement("WF-ADM-0110-A")
def test_the_list_is_refused_as_an_unknown_object_to_a_session_that_may_not_consult(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    blind = person(stage.database, realm, "planning.read")
    answer = api.get(PROJECTS, headers=blind.headers)
    assert (answer.status_code, answer.json()["code"]) == (404, "NOT_FOUND")
    assert api.get(PROJECTS).status_code == 401


@pytest.mark.requirement("WF-CYC-0010-A")
def test_without_states_the_projects_in_progress_alone_are_listed(
    api: ContractClient, stage: Scene
) -> None:
    empty = listed(api, stage.manager)
    assert (empty["items"], empty["meta"]["states"], empty["meta"]["total"]) == (
        [],
        ["in_progress"],
        0,
    )
    put_in_state(stage.owner, stage.project["project_id"], "in_progress")
    default = listed(api, stage.manager)
    assert labels(default) == [stage.project["label"]]
    assert default["items"][0]["state"] == "in_progress"
    assert default["meta"] == {"limit": 50, "offset": 0, "total": 1, "states": ["in_progress"]}


@pytest.mark.requirement("WF-CYC-0010-A")
@pytest.mark.parametrize("state", ["created", "lost", "abandoned"])
def test_a_state_a_request_names_is_kept_whatever_the_rule_of_the_portfolio(
    api: ContractClient, stage: Scene, state: str
) -> None:
    # #1749: a project Created, Lost or Abandoned is kept when its state is named; the states the
    # list keeps are said in the order of the cycle of life, whatever the order they were asked in.
    put_in_state(stage.owner, stage.project["project_id"], state)
    kept = listed(api, stage.manager, f"states={state}")
    assert labels(kept) == [stage.project["label"]]
    assert kept["items"][0]["state"] == state
    assert kept["meta"]["states"] == [state]
    assert listed(api, stage.manager, "states=in_progress")["items"] == []
    named = listed(api, stage.manager, f"states={state},in_progress,created")
    assert named["meta"]["states"] == [s for s in STATES if s in {state, "in_progress", "created"}]
    assert named["meta"]["total"] == 1


@pytest.mark.requirement("WF-CYC-0010-A")
def test_the_list_proposes_only_the_six_states_of_the_cycle_of_life(
    api: ContractClient, stage: Scene
) -> None:
    for query in ("states=archived", "states=", "states=created,,pricing"):
        answer = api.get(f"{PROJECTS}?{query}", headers=stage.manager.headers)
        assert answer.status_code == 422
        assert [field["pointer"] for field in answer.json()["fields"]] == ["/query/states"]
    kept = listed(api, stage.manager, EVERY_STATE)
    assert kept["meta"]["states"] == STATES


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_search_holds_on_the_label_and_on_the_code_without_regard_to_case_or_accents(
    api: ContractClient, stage: Scene
) -> None:
    coded = create(api, stage.manager, label="Extension de la ligne", code="PRJ-002")
    create(api, stage.manager, label="Rénovation du hall")
    assert labels(listed(api, stage.manager, f"{EVERY_STATE}&search=renovation")) == [
        "Rénovation du hall"
    ]
    assert labels(listed(api, stage.manager, f"{EVERY_STATE}&search=prj-002")) == [coded["label"]]
    assert labels(listed(api, stage.manager, f"{EVERY_STATE}&search=ligne")) == [coded["label"]]
    # A percent sign and an underscore are letters like another.
    assert listed(api, stage.manager, f"{EVERY_STATE}&search=%25")["items"] == []


@pytest.mark.requirement("WF-IHM-0130-A")
def test_a_project_renamed_is_found_by_its_new_label_alone(
    api: ContractClient, stage: Scene
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    renamed = api.patch(
        path, headers=stage.manager.headers, json={"label": "Lorient", "lock_version": 0}
    )
    assert renamed.status_code == 200
    assert labels(listed(api, stage.manager, f"{EVERY_STATE}&search=lorient")) == ["Lorient"]
    assert listed(api, stage.manager, f"{EVERY_STATE}&search=modernisation")["items"] == []


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_period_holds_on_the_last_change_its_start_included_and_its_end_excluded(
    api: ContractClient, stage: Scene
) -> None:
    march_2 = create(api, stage.manager, label="Deux")
    march_5 = create(api, stage.manager, label="Cinq")
    at(stage, march_2, 2)
    at(stage, march_5, 5)
    between = f"{EVERY_STATE}&from=2026-03-02T10:00:00Z&to=2026-03-05T10:00:00Z"
    assert labels(listed(api, stage.manager, between)) == ["Deux"]
    including = f"{EVERY_STATE}&from=2026-03-05T10:00:00Z&to=2026-03-06T00:00:00Z"
    assert labels(listed(api, stage.manager, including)) == ["Cinq"]
    # The days of a reader in Paris, as the instants the screen draws from them.
    paris = f"{EVERY_STATE}&from=2026-03-01T23:00:00%2B01:00&to=2026-03-03T00:00:00%2B01:00"
    assert labels(listed(api, stage.manager, paris)) == ["Deux"]
    empty = f"{EVERY_STATE}&from=2026-03-05T10:00:00Z&to=2026-03-05T10:00:00Z"
    assert listed(api, stage.manager, empty)["meta"]["total"] == 0


@pytest.mark.requirement("WF-IHM-0130-A")
def test_a_period_whose_end_precedes_its_start_is_refused_naming_the_start(
    api: ContractClient, stage: Scene
) -> None:
    query = "from=2026-03-05T10:00:00Z&to=2026-03-02T10:00:00Z"
    answer = api.get(f"{PROJECTS}?{query}", headers=stage.manager.headers)
    assert (answer.status_code, answer.json()["code"]) == (422, "VALIDATION_FAILED")
    [field] = answer.json()["fields"]
    assert (field["pointer"], field["code"]) == ("/query/to", "VALUE_OUT_OF_RANGE")
    assert datetime.fromisoformat(field["params"]["minimum"]) == datetime(
        2026, 3, 5, 10, tzinfo=UTC
    )
    malformed = api.get(f"{PROJECTS}?from=yesterday", headers=stage.manager.headers)
    assert [(f["pointer"], f["code"]) for f in malformed.json()["fields"]] == [
        ("/query/from", "DATE_INVALID")
    ]


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_list_sorts_on_each_column_in_both_directions_and_breaks_ties_by_identifier(
    api: ContractClient, stage: Scene
) -> None:
    # The label and the code in the order of the code points, a project without code after the
    # others in the ascending order; the state in the order of the cycle of life.
    zeta = create(api, stage.manager, label="Zeta", code="B-2")
    alpha = create(api, stage.manager, label="alpha", code="A-1")
    beta = create(api, stage.manager, label="Beta")
    put_in_state(stage.owner, zeta["project_id"], "completed")
    put_in_state(stage.owner, beta["project_id"], "pricing")
    every = EVERY_STATE

    def order(column: str, direction: str) -> list[str]:
        return labels(
            listed(api, stage.manager, f"{every}&sort_by={column}&sort_order={direction}")
        )

    model = stage.project["label"]
    assert order("label", "asc") == ["Beta", model, "Zeta", "alpha"]
    assert order("label", "desc") == ["alpha", "Zeta", model, "Beta"]
    assert order("code", "asc")[:2] == ["alpha", "Zeta"]
    assert order("code", "desc")[-2:] == ["Zeta", "alpha"]
    assert set(order("code", "asc")[2:]) == {"Beta", model}
    states = [
        item["state"] for item in listed(api, stage.manager, f"{every}&sort_by=state")["items"]
    ]
    assert states == sorted(states, key=STATES.index)
    assert [
        i["state"]
        for i in listed(api, stage.manager, f"{every}&sort_by=state&sort_order=desc")["items"]
    ] == sorted(states, key=STATES.index, reverse=True)
    assert alpha["code"] == "A-1"


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_list_without_a_sort_puts_the_projects_changed_last_first_and_pages_do_not_overlap(
    api: ContractClient, stage: Scene
) -> None:
    made = [create(api, stage.manager, label=f"Projet {number}") for number in range(5)]
    for number, project in enumerate(made):
        at(stage, project, number + 2)
    at(stage, stage.project, 1)
    everything = labels(listed(api, stage.manager, EVERY_STATE))
    assert everything == [f"Projet {number}" for number in (4, 3, 2, 1, 0)] + [
        stage.project["label"]
    ]
    # The same instant: the identifier breaks the tie, in the ascending order.
    for project in made:
        at(stage, project, 9)
    tied = listed(api, stage.manager, f"{EVERY_STATE}&limit=5")
    identifiers = [UUID(item["project_id"]) for item in tied["items"]]
    assert identifiers == sorted(UUID(project["project_id"]) for project in made)
    everything = labels(listed(api, stage.manager, EVERY_STATE))
    pages = [
        listed(api, stage.manager, f"{EVERY_STATE}&limit=4&offset={offset}") for offset in (0, 4, 8)
    ]
    assert [len(page["items"]) for page in pages] == [4, 2, 0]
    assert [page["meta"]["total"] for page in pages] == [6, 6, 6]
    assert [label for page in pages for label in labels(page)] == everything
    assert pages[1]["meta"] == {"limit": 4, "offset": 4, "total": 6, "states": STATES}


@pytest.mark.requirement("WF-IHM-0090-A")
def test_each_project_of_the_list_carries_the_commands_its_reader_holds(
    api: ContractClient, stage: Scene
) -> None:
    body = listed(api, stage.participant, EVERY_STATE)
    [item] = body["items"]
    conditions = {
        each["command"]: each["missing_conditions"] for each in item["available_commands"]
    }
    assert conditions["update"] == ["is_project_manager"]
    assert conditions["create_revision"] == []
    reading = listed(api, stage.reader, EVERY_STATE)["items"][0]
    assert reading["available_commands"] == []


def _statements(stage: Scene, api: ContractClient) -> int:
    """Count the statements the service sends to the database to answer one list."""
    sent: list[str] = []

    def count(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    event.listen(stage.database.engine, "before_cursor_execute", count)
    try:
        listed(api, stage.manager, EVERY_STATE)
    finally:
        event.remove(stage.database.engine, "before_cursor_execute", count)
    return len(sent)


@pytest.mark.requirement("WF-CYC-0010-A")
def test_the_list_sends_as_many_statements_to_the_database_for_n_projects_as_for_twice_as_many(
    api: ContractClient, stage: Scene
) -> None:
    for number in range(2):
        create(api, stage.manager, label=f"Projet {number}")
    small = _statements(stage, api)
    for number in range(2, 6):
        create(api, stage.manager, label=f"Projet {number}")
    assert len(listed(api, stage.manager, EVERY_STATE)["items"]) == 7
    assert _statements(stage, api) == small
