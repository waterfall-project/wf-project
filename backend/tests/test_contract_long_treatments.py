# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""No long treatment is reachable by an endpoint that answers after having run it (WF-ARC-0090).

What the contract says of the operations that start a treatment the worker runs: the analysis and
the application of an import, the marking, the export, the backup, the reading of the accounts, the
restoration. Each answers 202 and the reference of a task, or answers without having started
anything (the two operations whose 200 is named below), and no request that is not a read answers
a task by another status. What the service does is tried where each treatment is: the endpoints do
not run the work (``test_worker``), and the worker runs it (the files of each treatment).
"""

from typing import TYPE_CHECKING, NamedTuple

import pytest

from waterfall.platform.tasks import CONTRACT_KINDS

if TYPE_CHECKING:
    from jsonschema_path import SchemaPath
    from openapi_core import OpenAPI

# The operations that start each treatment, by the kind of task they deposit.
STARTED_BY = {
    "import_analysis": ("openImport", "setImportDurationRule"),
    "import_apply": ("applyImport",),
    "revision_mark": ("markRevision", "exitProject"),
    "export": ("requestExport",),
    "backup": ("startBackup",),
    "identity_sync": ("startIdentitySync",),
    "restore": ("startRestore",),
}
# The operations that answer 200 besides: the rule sent is the one the report holds (nothing is
# analysed again), and the exit of a project that carries no revision to mark (nothing is marked).
ANSWERING_WITHOUT_STARTING = {"setImportDurationRule", "exitProject"}
# The operations that answer 202 and are not in the list above, with why: their treatment is not
# one of those this file closes (WF-ARC-0090 names the imports, the marking, the exports, the
# backups, the reading of the accounts and the restoration), and the files of their own EPIC try it.
STARTING_ELSEWHERE = {
    "mergeCostStructure": "structure_merge",
    "declareRiskOccurrence": "risk_occurrence",
}
SUCCESSES = {"200", "202"}
METHODS = {"get", "put", "post", "delete", "patch"}
# What a body carries when it is a task, or when it gives the last one of what it reads.
TASK = {"task_id", "task"}


class Operation(NamedTuple):
    """An operation of the contract: its method, its path, and its node of the specification."""

    method: str
    path: str
    node: SchemaPath


def operations_of(contract: OpenAPI) -> dict[str, Operation]:
    """Give each operation of the contract by its identifier."""
    found: dict[str, Operation] = {}
    for path, item in (contract.spec / "paths").items():
        for method, operation in item.items():
            if method in METHODS:
                found[(operation / "operationId").read_value()] = Operation(
                    method, str(path), operation
                )
    return found


def properties_of(schema: SchemaPath) -> set[str]:
    """Give the names of the properties a schema declares, those of its ``allOf`` included."""
    names: set[str] = set()
    if "properties" in schema:
        names |= set(map(str, (schema / "properties").keys()))
    if "allOf" in schema:
        for part in schema / "allOf":
            names |= properties_of(part)
    return names


def carries_a_task(answer: SchemaPath) -> bool:
    """Say whether the body an answer declares is a task, or names the last one of what it gives."""
    if "content" not in answer:
        return False
    return any(
        properties_of(content / "schema") & TASK
        for media_type, content in (answer / "content").items()
        if media_type == "application/json" and "schema" in content
    )


def successes_of(operation: SchemaPath) -> dict[str, SchemaPath]:
    """Give the answers of an operation that succeed, by status."""
    answers = (operation / "responses").items()
    return {str(status): answer for status, answer in answers if str(status).startswith("2")}


def started_by() -> list[tuple[str, str]]:
    """List each operation that starts a treatment, with the kind of task it deposits."""
    return [(kind, name) for kind, names in STARTED_BY.items() for name in names]


@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.parametrize(("kind", "name"), started_by())
def test_an_operation_that_starts_a_long_treatment_answers_202_and_the_reference_of_its_task(
    contract: OpenAPI, kind: str, name: str
) -> None:
    # « Aucun de ces traitements n'est joignable par un endpoint qui répondrait après l'avoir
    # exécuté. » : analysis and application of an import, marking, export, backup, reading of the
    # accounts, restoration. The answer that starts the treatment is the 202 of the reference of
    # the task, whose ``kind`` the contract lists; any other success starts nothing.
    successes = successes_of(operations_of(contract)[name].node)
    assert kind in CONTRACT_KINDS  # the kind of the list; its link to ``name`` is tried below
    assert "202" in successes
    assert carries_a_task(successes["202"])
    assert set(successes) <= SUCCESSES
    if "200" in successes:
        assert name in ANSWERING_WITHOUT_STARTING


def kinds_of_examples(answer: SchemaPath) -> set[str]:
    """Give the kinds of task the examples of an answer show, the task nested in an import too."""
    kinds: set[str] = set()
    content = answer / "content" / "application/json"
    if "examples" not in content:
        return kinds
    for _, example in (content / "examples").items():  # noqa: PERF102 (a path has no values())
        value = (example / "value").read_value()
        task = value if "task_id" in value else value.get("task")
        if task:
            kinds.add(task["kind"])
    return kinds


@pytest.mark.requirement("WF-ARC-0090-A")
def test_every_operation_of_the_contract_that_answers_202_is_listed_or_set_apart_with_its_reason(
    contract: OpenAPI,
) -> None:
    # « Aucun de ces traitements n'est joignable par un endpoint qui répondrait après l'avoir
    # exécuté. » : the list of the operations that start a treatment is not closed by hand. Each
    # operation of the contract that answers 202 is in ``STARTED_BY`` or in ``STARTING_ELSEWHERE``,
    # and neither lists an operation that answers no 202. The kind a listed operation starts is
    # read in the examples of its 202, which the contract writes: the kind of the task, or of the
    # task an import holds. The contract states no other link from an operation to a kind (its
    # description of ``kind`` names them in prose), so an operation without example is refused.
    listed = {name: kind for kind, name in started_by()} | STARTING_ELSEWHERE
    answering = {
        name: operation
        for name, operation in operations_of(contract).items()
        if "202" in successes_of(operation.node)
    }
    assert set(answering) == set(listed)
    assert not set(STARTING_ELSEWHERE) & {name for _, name in started_by()}
    for name, operation in answering.items():
        shown = kinds_of_examples(successes_of(operation.node)["202"])
        assert shown, name
        assert listed[name] in shown, (name, shown)
        assert shown <= set(CONTRACT_KINDS), name


@pytest.mark.requirement("WF-ARC-0090-A")
def test_no_operation_of_the_contract_answers_a_task_by_another_status_than_202(
    contract: OpenAPI,
) -> None:
    # « Aucun de ces traitements n'est joignable par un endpoint qui répondrait après l'avoir
    # exécuté. » : a request that is not a read answers the task it deposited at 202, never at
    # another status that would say the work done. The one exception reads the task of an import
    # that is as it was: the rule sent is the one its report holds, and nothing is analysed again.
    answering: dict[str, list[str]] = {}
    for name, operation in operations_of(contract).items():
        if operation.method == "get":
            continue
        other = [
            status
            for status, answer in successes_of(operation.node).items()
            if status != "202" and carries_a_task(answer)
        ]
        if other:
            answering[name] = other
    assert answering == {"setImportDurationRule": ["200"]}
    assert {kind for kind, _ in started_by()} <= set(CONTRACT_KINDS)
