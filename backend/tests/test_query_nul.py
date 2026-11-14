# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A NUL character in a free parameter of a query is refused on its parameter (US-1980, #2891).

PostgreSQL refuses a text that holds the NUL character: one that reached it would be a 500. The
free parameters of the service's queries that are read as bare ``str`` are listed below, each
with the route that reads it; ``%00`` is sent to each, on a real database, and every one answers
422 ``VALIDATION_FAILED`` at ``/query/<parameter>``. A parameter whose value is analysed against
a closed list, a closed pattern or a form (a kind, a state, a bound) refuses it by that analysis
and stays a bare ``str``; one whose pattern lets the character through (``sort_by`` of
``listActualCosts``, after ``passthrough.``) is ``Text``, refused by its type, and is tried with
a value the pattern accepts (``passthrough.%00``). Only ``code`` of ``listOrgNodes`` reached the
base before (#2233); the parameters of type ``Text`` (``search``, ``code``, ``actions``…) are
tried by the tests of their routes. The bounds of ``listNodes`` are those the route reads
(``DECIMAL_BOUNDS``…), so a bound added to it is tried at once.
"""

from typing import TYPE_CHECKING, Any

import pytest
from nodes_support import Tree, mark, opened
from projects_support import PROJECTS, Person, Scene, contribute, person
from projects_support import scene as make_scene

from waterfall.api.nodes import DECIMAL_BOUNDS, MONEY_BOUNDS, PERIODS, WHOLE_BOUNDS
from waterfall.core.access_roles.predefined import ADMINISTRATOR, MANAGER, PROJECT_MANAGER

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

NUL = "%00"

# The routes, by the name the cases give them: the operation, then its path under the project
# (``None`` for a route out of the projects).
ROUTES = {
    "listNodes": "{structure}/nodes",
    "compareRevisions": "{project}/revisions/comparison?from_revision_id={revision}"
    "&to_revision_id={revision}",
    "listProjects": PROJECTS,
    "listContributors": "{project}/contributors",
    "getWorkBreakdown": "{project}/work-breakdown",
    "listRevisions": "{project}/revisions",
    "getEstimateIndicators": "{project}/estimate-indicators",
    "listActualCosts": "{project}/actual-costs",
    "getHourlyRateGrid": "/api/v1/reference/hourly-rates?rate_year=2026",
    "listResourceRoles": "/api/v1/reference/resource-roles",
}


def bounds(columns: tuple[str, ...], ends: tuple[str, str]) -> list[str]:
    """Give the two bounds of each column."""
    return [f"{column}_{end}" for column in columns for end in ends]


NODE_LISTS = ["kinds", "progress", "scheduling_mode", "origin_risk_ids", "fields"]
NODE_BOUNDS = [
    *bounds((*DECIMAL_BOUNDS, *MONEY_BOUNDS, *WHOLE_BOUNDS), ("min", "max")),
    *bounds(PERIODS, ("from", "to")),
]
COMPARED = ["difference", *NODE_LISTS, *NODE_BOUNDS]


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def reader(stage: Scene, database: Database, realm: TestRealm) -> Person:
    """Give a contributor of the project who holds every permission, whatever its quality."""
    every = {*ADMINISTRATOR, *PROJECT_MANAGER, *MANAGER}
    who = person(database, realm, *sorted(every), name="Alix")
    contribute(database, stage.project["project_id"], who, "contributor")
    return who


@pytest.fixture
def paths(api: ContractClient, stage: Scene) -> dict[str, str]:
    """Give the path of each route, on a project whose revision is marked: a real one to read."""
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    mark(stage, revision)
    project = f"{PROJECTS}/{stage.project['project_id']}"
    return {
        route: template.format(
            project=project, structure=tree.path, revision=revision["revision_id"]
        )
        for route, template in ROUTES.items()
    }


def refuse(
    api: ContractClient, reader: Person, path: str, parameter: str, value: str = NUL
) -> None:
    """Check a route reads on its own, and refuses the NUL character at the parameter (422)."""
    assert api.get(path, headers=reader.headers).status_code == 200
    joined = "&" if "?" in path else "?"
    refused = api.get(f"{path}{joined}{parameter}={value}", headers=reader.headers)
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "VALIDATION_FAILED"
    assert [field["pointer"] for field in refused.json()["fields"]] == [f"/query/{parameter}"]


def parameters(*names: str) -> Any:
    """Give the parameters of a route as the cases of a test."""
    return pytest.mark.parametrize("parameter", names)


# One test per requirement: the tool that counts them reads the marks on the tests.
@pytest.mark.requirement("WF-PLA-0080-A")
@parameters(*NODE_LISTS, *NODE_BOUNDS)
def test_listing_nodes_refuses_a_nul_character_in_a_bare_text_parameter(
    api: ContractClient, reader: Person, paths: dict[str, str], parameter: str
) -> None:
    refuse(api, reader, paths["listNodes"], parameter)


@pytest.mark.requirement("WF-REV-0080-A")
@parameters(*COMPARED)
def test_comparing_revisions_refuses_a_nul_character_in_a_bare_text_parameter(
    api: ContractClient, reader: Person, paths: dict[str, str], parameter: str
) -> None:
    refuse(api, reader, paths["compareRevisions"], parameter)


@pytest.mark.requirement("WF-IHM-0130-A")
def test_listing_projects_refuses_a_nul_character_in_the_states(
    api: ContractClient, reader: Person, paths: dict[str, str]
) -> None:
    refuse(api, reader, paths["listProjects"], "states")


@pytest.mark.requirement("WF-PRJ-0060-A")
@parameters("kinds", "sort_by")
def test_listing_contributors_refuses_a_nul_character_in_a_bare_text_parameter(
    api: ContractClient, reader: Person, paths: dict[str, str], parameter: str
) -> None:
    refuse(api, reader, paths["listContributors"], parameter)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_the_work_breakdown_refuses_a_nul_character_in_the_kinds(
    api: ContractClient, reader: Person, paths: dict[str, str]
) -> None:
    refuse(api, reader, paths["getWorkBreakdown"], "kinds")


@pytest.mark.requirement("WF-REV-0070-A")
def test_listing_revisions_refuses_a_nul_character_in_the_status(
    api: ContractClient, reader: Person, paths: dict[str, str]
) -> None:
    refuse(api, reader, paths["listRevisions"], "status")


@pytest.mark.requirement("WF-IND-0020-A")
def test_the_estimate_indicators_refuse_a_nul_character_in_the_scope(
    api: ContractClient, reader: Person, paths: dict[str, str]
) -> None:
    refuse(api, reader, paths["getEstimateIndicators"], "scope")


@pytest.mark.requirement("WF-CRE-0040-A")
@parameters("subproject_id", "sort_by")
def test_listing_actual_costs_refuses_a_nul_character_in_a_bare_text_parameter(
    api: ContractClient, reader: Person, paths: dict[str, str], parameter: str
) -> None:
    # ``sort_by`` has a pattern that lets the character through after ``passthrough.``: it is
    # ``Text``, refused by its type (``passthrough.%00``), not by the pattern.
    value = "passthrough.%00" if parameter == "sort_by" else NUL
    refuse(api, reader, paths["listActualCosts"], parameter, value)


@pytest.mark.requirement("WF-REF-0050-A")
@parameters("rate_min", "rate_max", "sort_by")
def test_the_hourly_rate_grid_refuses_a_nul_character_in_a_bare_text_parameter(
    api: ContractClient, reader: Person, paths: dict[str, str], parameter: str
) -> None:
    refuse(api, reader, paths["getHourlyRateGrid"], parameter)


@pytest.mark.requirement("WF-REF-0090-A")
@parameters("monthly_hours_min", "monthly_hours_max", "headcount_min", "headcount_max")
def test_listing_resource_roles_refuses_a_nul_character_in_a_bound(
    api: ContractClient, reader: Person, paths: dict[str, str], parameter: str
) -> None:
    refuse(api, reader, paths["listResourceRoles"], parameter)
