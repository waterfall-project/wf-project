# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An ``offset`` beyond the bound of the contract is refused on every paginated list (US-1960).

The common parameter ``Offset`` of the contract is at most ``2147483647``, the bound of
``LockVersion`` (#2778): beyond it, a list answers 422 ``VALIDATION_FAILED`` at ``/query/offset``,
and never reaches the base. The paginated lists are those of the contract, every operation that
carries a query parameter ``offset``, and not a list written here: a list the service serves and
that refused nothing would be named by the test. An operation the contract declares and the
service does not serve yet (``listRisks``, ``getPortfolioProjects``) is left out, and is tried as
soon as it is served. The bounds the service declares are held to those of the contract apart
(``test_contract_declarations``); this test plays the refusal on each list, on a real database.
"""

from typing import TYPE_CHECKING, Any, cast

import pytest
from projects_support import Person, Scene, contribute, person
from projects_support import scene as make_scene
from support import operations

from waterfall.api.queries import GREATEST_OFFSET
from waterfall.core.access_roles.predefined import ADMINISTRATOR, MANAGER, PROJECT_MANAGER

if TYPE_CHECKING:
    from fastapi import FastAPI
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

METHODS = ("get", "put", "post", "patch", "delete")
# The value of each parameter that a paginated list requires, by its name, besides ``offset``. A
# list that requires another one fails the test by its name, to be given here.
REQUIRED = {"rate_year": "2026"}


def parameters(contract: OpenAPI, path: str, method: str) -> list[dict[str, Any]]:
    """Give the parameters of an operation, those of its path item included, references read."""
    item = contract.spec / "paths" / path
    found: list[dict[str, Any]] = []
    for owner in (item, item / method):
        with owner.open() as content:
            count = len(content.get("parameters", []))
        for index in range(count):
            with (owner / "parameters" / index).open() as parameter:
                found.append(dict(parameter))
    return found


def paginated(contract: OpenAPI) -> dict[str, list[dict[str, Any]]]:
    """Name each operation of the contract that takes ``offset`` in its query: its parameters."""
    paths = contract.spec / "paths"
    with paths.open() as content:
        names = list(content)
    found: dict[str, list[dict[str, Any]]] = {}
    for path in names:
        item = paths / path
        for method in METHODS:
            if method not in item:
                continue
            taken = parameters(contract, path, method)
            if any(each["in"] == "query" and each["name"] == "offset" for each in taken):
                with (item / method).open() as operation:
                    found[str(operation["operationId"])] = taken
    return found


def served(api: ContractClient) -> dict[str, set[str]]:
    """Give the query parameters of each operation the service serves, by its identifier."""
    described = cast("FastAPI", api.client.app).openapi()
    return {
        operation["operationId"]: {
            each["name"] for each in operation.get("parameters", []) if each["in"] == "query"
        }
        for item in described["paths"].values()
        for operation in item.values()
    }


def address(contract: OpenAPI, operation: str, taken: list[dict[str, Any]], project: str) -> str:
    """Write the address of a list: its project in its path, the parameters it requires given."""
    _, path = operations(contract)[operation]
    path = path.replace("{project_id}", project)
    asked: list[str] = []
    for each in taken:
        if each["in"] == "query" and each.get("required") and each["name"] != "offset":
            assert each["name"] in REQUIRED, f"{operation} requires {each['name']}: give it"
            asked.append(f"{each['name']}={REQUIRED[each['name']]}")
    assert "{" not in path, f"{operation}: a path parameter to give ({path})"
    return f"{path}?{'&'.join(asked)}" if asked else path


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


def refusal(api: ContractClient, reader: Person, path: str) -> str | None:
    """Tell what is wrong with a list and its ``offset``: nothing, ``None``.

    The list reads; at the bound, it gives an empty page at that rank; beyond it, it refuses the
    parameter alone, by its range and its bound.
    """
    joined = "&" if "?" in path else "?"
    read = api.get(path, headers=reader.headers)
    if read.status_code != 200:
        return f"read: {read.status_code} {read.text}"
    at_bound = api.get(f"{path}{joined}offset={GREATEST_OFFSET}", headers=reader.headers)
    if at_bound.status_code != 200 or at_bound.json()["meta"]["offset"] != GREATEST_OFFSET:
        return f"at the bound: {at_bound.status_code} {at_bound.text}"
    beyond = api.get(f"{path}{joined}offset={GREATEST_OFFSET + 1}", headers=reader.headers)
    if beyond.status_code != 422:
        return f"beyond the bound: {beyond.status_code} {beyond.text}"
    problem = cast("dict[str, Any]", beyond.json())
    faults = cast("list[dict[str, Any]]", problem["fields"])
    fields = [
        (
            fault["pointer"],
            fault["code"],
            cast("dict[str, Any]", fault.get("params") or {}).get("maximum"),
        )
        for fault in faults
    ]
    if problem["code"] != "VALIDATION_FAILED" or fields != [
        ("/query/offset", "VALUE_OUT_OF_RANGE", GREATEST_OFFSET)
    ]:
        return f"beyond the bound: {problem}"
    return None


def test_every_paginated_list_refuses_an_offset_beyond_the_bound_of_the_contract(
    api: ContractClient, contract: OpenAPI, stage: Scene, reader: Person
) -> None:
    lists = paginated(contract)
    service = served(api)
    # The bound written here is the one of the common parameter ``Offset``, read where it is used.
    maxima = {
        each["schema"]["maximum"]
        for taken in lists.values()
        for each in taken
        if each["in"] == "query" and each["name"] == "offset"
    }
    assert maxima == {GREATEST_OFFSET}
    # The reverse: a list the service serves with an ``offset`` is a list of the contract.
    outside = sorted(name for name, taken in service.items() if "offset" in taken)
    assert [name for name in outside if name not in lists] == []
    tried = sorted(set(lists) & set(service))
    # The lists of the contract, by its common parameter: fourteen served when US-1960 was written.
    assert len(tried) >= 14, tried
    assert [name for name in tried if "offset" not in service[name]] == []
    project = str(stage.project["project_id"])
    found = {
        name: refusal(api, reader, address(contract, name, lists[name], project)) for name in tried
    }
    assert {name: wrong for name, wrong in found.items() if wrong is not None} == {}
