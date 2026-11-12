# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A NUL character in a free parameter of a query is refused on its parameter (US-1980, #2891).

PostgreSQL refuses a text that holds the NUL character: one that reached it would be a 500. The
free parameters of the service's queries that are read as bare ``str`` are listed below, each
with the route that reads it; ``%00`` is sent to each, on a real database, and every one answers
422 ``VALIDATION_FAILED`` at ``/query/<parameter>`` — a parameter whose value is analysed against
a closed list or a pattern (a kind, a state, a bound) refuses it by that analysis, before any
query, and stays a bare ``str``. Only ``code`` of ``listOrgNodes`` reached the base (#2233); the
parameters of type ``Text`` (``search``, ``code``, ``actions``…) are tried by the tests of
their routes.
"""

from typing import TYPE_CHECKING, Any

import pytest
from nodes_support import Tree, mark, opened
from projects_support import PROJECTS, Person, Scene, contribute, person
from projects_support import scene as make_scene

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


def case(route: str, parameter: str, requirement: str) -> Any:
    """Give a case: a parameter of a route, under the requirement of the operation."""
    return pytest.param(
        route, parameter, marks=pytest.mark.requirement(requirement), id=f"{route}-{parameter}"
    )


NODES = "WF-PLA-0080-A"
BOUNDS = (
    "duration_min",
    "total_float_max",
    "unit_disbursement_min",
    "consumption_year_max",
    "start_from",
    "completed_on_to",
)
CASES = [
    *(
        case("listNodes", name, NODES)
        for name in ("kinds", "progress", "scheduling_mode", "origin_risk_ids", "fields", *BOUNDS)
    ),
    *(
        case("compareRevisions", name, "WF-REV-0080-A")
        for name in ("difference", "kinds", "progress", "fields", "duration_min", "start_from")
    ),
    case("listProjects", "states", "WF-IHM-0130-A"),
    case("listContributors", "kinds", "WF-PRJ-0060-A"),
    case("getWorkBreakdown", "kinds", "WF-PRJ-0020-A"),
    case("listRevisions", "status", "WF-REV-0010-A"),
    case("getEstimateIndicators", "scope", "WF-IND-0020-A"),
    case("listActualCosts", "subproject_id", "WF-CRE-0040-A"),
    *(case("getHourlyRateGrid", name, "WF-REF-0050-A") for name in ("rate_min", "rate_max")),
    *(
        case("listResourceRoles", name, "WF-REF-0090-A")
        for name in ("monthly_hours_min", "monthly_hours_max", "headcount_min", "headcount_max")
    ),
]


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


@pytest.mark.parametrize(("route", "parameter"), CASES)
def test_a_nul_character_in_a_bare_text_parameter_is_refused_on_that_parameter(
    api: ContractClient, reader: Person, paths: dict[str, str], route: str, parameter: str
) -> None:
    # The route reads on its own without the parameter; with ``%00`` it is refused (422), at the
    # parameter, never a failure of the database (500).
    path = paths[route]
    assert api.get(path, headers=reader.headers).status_code == 200
    joined = "&" if "?" in path else "?"
    refused = api.get(f"{path}{joined}{parameter}={NUL}", headers=reader.headers)
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "VALIDATION_FAILED"
    assert [field["pointer"] for field in refused.json()["fields"]] == [f"/query/{parameter}"]
