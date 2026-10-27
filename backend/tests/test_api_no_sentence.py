# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""No answer of the API carries a sentence meant for its reader (WF-ARC-0110).

The answers of every operation the service serves are read in the contract, its references
followed, down to each text they hold. A text is a code when the contract says its values — an
enumeration, a form (``format``), a pattern from end to end —, or it is a datum a person entered,
or that the front itself wrote, each named below with what it is. A text of any other kind would be
a sentence the API words in one language for its reader: the test fails on it. Every answer the
tests of the service read is checked against the contract (``ContractClient``), which refuses a
property its schema does not declare, where openapi-core validates an object without closing it:
what the contract does not hold, no answer holds.
"""

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.routing import APIRoute
from support import CONTRACT
from test_contract_declarations import Contract

from waterfall.api.app import create_app
from waterfall.api.authentication import Services

# The forms that make a text a code, an identifier, an instant or an address.
FORMS = {"uuid", "date", "date-time", "uri", "email", "binary", "byte"}

# The texts the answers hold that are data, not sentences, by the schema and the property that
# hold them: a property of the same name elsewhere is not one of them.
DATA = {
    # The label a person gave an object, kept as it was: a role, a node, the object of an
    # inscription of the journal and its revision, a role before it was renamed.
    "AccessRole.label": "a label",
    "AuditAccessRole.label": "a label",
    "AuditObject.label": "a label",
    "AuditProject.label": "a label",
    "AuditRevision.label": "a label",
    "AuditParams.previous_label": "a label",
    "UserAccount.access_role_labels": "labels",
    "UserAccount.org_node_label": "a label",
    # The name of a person, as her account holds it, and as it is shown.
    "UserAccount.last_name": "a name",
    "UserAccount.first_name": "a name",
    "ActorRef.display_name": "a name",
    "AuditActorFacet.display_name": "a name",
    # The code a person gave a project, and the code of a function of the FBS.
    "AuditProject.code": "a code",
    "Permission.fbs_code": "a code",
    # What the front writes in the preferences of a grid: the names of its columns and the values
    # of its filters, as its address writes them.
    "GridPreferences.sort.column": "a name of the front",
    "GridPreferences.hidden_columns": "names of the front",
    "GridPreferences.known_columns": "names of the front",
    "GridPreferences.filters[*]": "values of the front",
    # The field of a request a refusal points at, and the address of a result to download.
    "FieldProblem.pointer": "a JSON pointer",
    "BackgroundTaskRef.result_url": "an address",
    # What a reading of the provider left as it was — an account as it is today, a person as the
    # provider holds her, by her identifier there —, and the addresses of the accounts removed.
    "IdentitySyncSkipped.subject": "an identifier of the provider",
    "IdentitySyncSkipped.last_name": "a name",
    "IdentitySyncSkipped.first_name": "a name",
    "IdentitySyncSkipped.email": "an address",
    "IdentitySyncReport.removed": "addresses",
    # The name of a file deposited, as the person chose it (#350).
    "ChunkedUpload.filename": "a name of a file",
    "FileUpload.filename": "a name of a file",
}
# The objects the answers hold whose properties the contract does not close: the parameters of a
# refusal, and of each field it refuses, which name its condition by codes and values. Any other
# — ``AuditParams`` reopened — fails the test.
OPEN = {"Problem.params", "FieldProblem.params"}


class Texts:
    """The texts an answer of the contract may hold, by the schema and property that hold them."""

    def __init__(self, contract: Contract) -> None:
        self.contract = contract
        self.free: set[str] = set()
        self.open: set[str] = set()

    def walk(self, node: Any, base: Path, name: str, seen: frozenset[tuple[Path, int]]) -> None:
        """Note each text of a schema that is no code, and each object left open.

        ``name`` qualifies a property by the schema that holds it — the last reference followed,
        ``AuditObject.label`` — or by the property that holds an inline schema in turn.
        """
        if isinstance(node, dict) and "$ref" in node:
            reference = cast("str", cast("dict[str, Any]", node)["$ref"])
            owner = reference.rpartition("/")[2]
        else:
            owner = name
        found, base = self.contract.follow(node, base)
        if not isinstance(found, dict):
            return
        schema = cast("dict[str, Any]", found)
        if (base, id(schema)) in seen:
            return
        seen |= {(base, id(schema))}
        for part in ("allOf", "anyOf", "oneOf"):
            for each in cast("list[Any]", schema.get(part) or []):
                self.walk(each, base, owner, seen)
        for named, below in cast("dict[str, Any]", schema.get("properties") or {}).items():
            self.walk(below, base, f"{owner}.{named}", seen)
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict):
            self.walk(extra, base, f"{owner}[*]", seen)
        elif extra is True:
            self.open.add(owner)
        if "items" in schema:
            self.walk(schema["items"], base, name, seen)
        types = schema.get("type")
        if types == "string" or (isinstance(types, list) and "string" in types):
            coded = "enum" in schema or "const" in schema or schema.get("format") in FORMS
            if not coded and not str(schema.get("pattern", "")).startswith("^"):
                self.free.add(name)


def served(services: Services) -> set[str]:
    """Name the operations the application serves."""
    found: set[str] = set()
    for included in create_app(services).routes:
        router = getattr(included, "original_router", None)
        for route in cast("list[Any]", router.routes) if router else [included]:
            if isinstance(route, APIRoute) and route.operation_id:
                found.add(route.operation_id)
    return found


@pytest.mark.requirement("WF-ARC-0110-A")
def test_no_answer_of_the_api_carries_a_sentence_meant_for_its_reader(services: Services) -> None:
    # « Aucune réponse de l'API ne contient de phrase destinée à l'utilisateur » : each text of
    # each answer of each operation served, success and refusal, is a code or a datum.
    contract = Contract(CONTRACT)
    texts = Texts(contract)
    serving = served(services)
    operations = [each for each in contract.operations() if each[0] in serving]
    assert {each[0] for each in operations} == serving
    for name, operation, _, base in operations:
        for status, answer in cast("dict[str, Any]", operation["responses"]).items():
            described, place = contract.follow(answer, base)
            for media in cast("dict[str, Any]", described.get("content") or {}).values():
                if "schema" in media:
                    texts.walk(media["schema"], place, f"{name} {status}", frozenset())
    assert texts.free == DATA.keys()
    assert texts.open == OPEN
