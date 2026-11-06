# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the natures of cost share: the examples, the sessions.

The examples are the files of the witness that the faux back serves (``fixtures/api``): the
service loaded with them answers the same lists, to the columns of audit and the counters, and to
the commands, which depend on what the service knows of each object (EP-05, "Les tests du back").
"""

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

from support import WITNESS

if TYPE_CHECKING:
    from support import ContractClient

TYPES = "/api/v1/reference/cost-types"
ME = "/api/v1/me"
LABOUR = UUID("01926f3a-7c00-7000-8000-000000000461")
NON_LABOUR = UUID("01926f3a-7c00-7000-8000-000000000462")
PROVISION = UUID("01926f3a-7c00-7000-8000-000000000463")
# What the service does not write the way the example says: the dates and the authors (the loading
# is the platform's, at its instant), the counters, and the commands.
UNSHARED = {"audit", "lock_version", "available_commands"}


def example(name: str) -> dict[str, Any]:
    """Read the value of an example of the contract, a file of the witness."""
    document = json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))
    return document["value"]


def shown(item: dict[str, Any]) -> dict[str, Any]:
    """Give an object as the examples and the service agree on it."""
    return {name: value for name, value in item.items() if name not in UNSHARED}


def caller_id(api: ContractClient, headers: dict[str, str]) -> str:
    """Give the identifier of the account a session belongs to."""
    return api.get(ME, headers=headers).json()["user_id"]


def new_type(api: ContractClient, headers: dict[str, str], code: str, kind: str = "labor") -> Any:
    """Create a nature by the API, and give it as it is answered."""
    response = api.post(TYPES, headers=headers, json={"code": code, "label": code, "kind": kind})
    assert response.status_code == 201
    return response.json()


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def pointers(response: Any) -> list[tuple[str, str, dict[str, Any]]]:
    """Give, of a refusal, each field refused: where, why, and the parameters of the reason."""
    return [
        (each["pointer"], each["code"], each.get("params", {}))
        for each in response.json()["fields"]
    ]


def commands(item: dict[str, Any]) -> list[tuple[str, bool, list[str]]]:
    """Give the commands of an object as (command, available, conditions lacking)."""
    return [
        (each["command"], each["is_available"], each["missing_conditions"])
        for each in item["available_commands"]
    ]


def deactivate(api: ContractClient, headers: dict[str, str], item: dict[str, Any]) -> Any:
    """Deactivate a nature at the version it was read at."""
    sent = {"is_active": False, "lock_version": item["lock_version"]}
    return api.put(f"{TYPES}/{item['cost_type_id']}/activation", headers=headers, json=sent)
