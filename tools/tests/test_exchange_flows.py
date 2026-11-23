# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The closed list of the exchanges: the contract against the table of the flows (WF-INTF-0150).

Waterfall exchanges data of a project with external systems only by the flows FLX-01 to FLX-07 of
the table of the flows (§3.1.2); the exported images and the backups are the only exchanges outside
it. The functions of exchange of the contract are confronted with that table, read from the
projection of the specification:

- the operations that deposit or render a file — a body or an answer whose schema is a binary
  string, a part of a form included — are those ``CARRIERS`` classifies, no more, no fewer: the
  import or the export of data of a project, a backup, or a picture that is no data of a project;
- each kind of import (``ImportRequest.kind``) and of export (``ExportRequest.kind``) is a flow of
  the table, of its sense, whose requirement the operation that opens it cites — or, for an export,
  an image that WF-INTF-0150 names out of the table; each flow of a file of the table is served by
  one of them;
- each use of an upload (``FileUploadPurpose``) is an import or a backup;
- no operation of the portfolio deposits or renders a file.
"""

import re
from functools import cache
from typing import TYPE_CHECKING, Any, cast

import pytest
import yaml

from wftools import REPOSITORY, projection

if TYPE_CHECKING:
    from pathlib import Path

INTF = "WF-INTF-0150-A"
API = REPOSITORY / "docs" / "api"
METHODS = ("get", "put", "post", "patch", "delete")
IMPORT, EXPORT, BACKUP, NO_PROJECT_DATA = "import", "export", "backup", "no project data"

# Each operation that deposits or renders a file, and what it carries.
CARRIERS: dict[str, frozenset[str]] = {
    # The file of an import, or of a backup to restore, by its use (``FileUploadPurpose``).
    "uploadFile": frozenset({IMPORT, BACKUP}),
    # A chunk of a backup to restore (WF-ADM-0160).
    "uploadChunk": frozenset({BACKUP}),
    # The file an export produced, of the kind of the export (``ExportKind``).
    "getBackgroundTaskResult": frozenset({EXPORT}),
    # A backup of the platform (WF-ADM-0150).
    "downloadBackup": frozenset({BACKUP}),
    # The picture of a user, which belongs to no project: not an exchange of data of a project.
    "putMyAvatar": frozenset({NO_PROJECT_DATA}),
    "getUserAvatar": frozenset({NO_PROJECT_DATA}),
}
# The use of an upload, and what it carries.
PURPOSES = {"import": IMPORT, "external_backup": BACKUP}
# Each kind of import and of export, and its flow; the image of the task tree, out of the table.
IMPORTS = {
    "ms_project_schedule": "FLX-01",
    "estimate": "FLX-03",
    "remaining": "FLX-05",
    "actual_costs": "FLX-07",
}
EXPORTS = {
    "ms_project_schedule": "FLX-02",
    "estimate": "FLX-04",
    "remaining": "FLX-06",
    "task_tree_image": "WF-PLA-0120",
}
SENSES = {IMPORT: "Entrant", EXPORT: "Sortant"}
# The words by which the description of ``openImport`` and of ``requestExport`` names each kind,
# and by which that of a backup operation names the backup: the requirement is the one in the
# parentheses that follow them.
NAMES = {
    "ms_project_schedule": "MS Project schedule",
    "estimate": "estimate",
    "remaining": "remaining to commit",
    "actual_costs": "actual costs",
    "task_tree_image": "image of the task tree",
}
BACKUPS = {
    "downloadBackup": ("copy outside the platform", "WF-ADM-0150"),
    "uploadChunk": ("backup to restore", "WF-ADM-0160"),
}

_FLOW = re.compile(r"FLX-\d{2}")
_REQUIREMENT = re.compile(r"WF-[A-Z]+-\d{4}")
# A row of the tables of the flows: flow, source, destination, sense, mode of exchange, frequency.
_CELLS = 6


def flows(text: str) -> dict[str, tuple[str, str]]:
    """Return each flow of a file of the tables of the flows: its sense and its requirement.

    A flow of the screens (« IHM ») or out of the scope cites no requirement: it is left out, as
    the rows of the other tables that name a flow (§4.6.2, its stages).
    """
    found: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        cells = [each.strip() for each in line.strip().strip("|").split("|")]
        if not line.startswith("| FLX-") or len(cells) != _CELLS:
            continue
        flow, cited = _FLOW.match(cells[0]), _REQUIREMENT.findall(cells[4])
        if flow is not None and len(cited) == 1:
            found[flow.group()] = (cells[3], cited[0])
    return found


def out_of_the_table(body: str) -> dict[str, frozenset[str]]:
    """Return the requirements of the exported images and of the backups.

    WF-INTF-0150 names them: « Les images exportées (…) et les sauvegardes (…) ».
    """
    found: dict[str, frozenset[str]] = {}
    for kind, words in ((EXPORT, "images exportées"), (BACKUP, "sauvegardes")):
        named = re.search(rf"{words} \(([^)]*)\)", body)
        assert named is not None, words
        found[kind] = frozenset(_REQUIREMENT.findall(named.group(1)))
    return found


type Json = dict[str, Any]


@cache
def _load(path: Path) -> object:
    """Read a file of the contract once."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _resolved(value: Json, base: Path) -> tuple[Json, Path]:
    """Follow the ``$ref`` of a part of the file ``base`` to the part it designates, and its file.

    The file of a part is what its own references are relative to.
    """
    while "$ref" in value:
        location, _, pointer = cast("str", value["$ref"]).partition("#")
        path = (base.parent / location).resolve() if location else base
        target: Any = _load(path)
        for step in filter(None, pointer.split("/")):
            target = target[step.replace("~1", "/").replace("~0", "~")]
        value, base = cast("Json", target), path
    return value, base


def _binary(schema: Json, base: Path) -> bool:
    """Tell whether the schema of a body is a file: a binary string, or a form with one."""
    schema, base = _resolved(schema, base)
    if schema.get("type") == "string" and schema.get("format") == "binary":
        return True
    properties = cast("dict[str, Json]", schema.get("properties", {}))
    return any(_resolved(each, base)[0].get("format") == "binary" for each in properties.values())


def carries_a_file(operation: Json, base: Path) -> bool:
    """Tell whether an operation of the file ``base`` deposits or renders a file.

    Its body or one of its answers has a content whose schema is a file; the schemas of JSON are
    not searched further, a file being a body, never a property of a document.
    """
    bodies = [operation.get("requestBody"), *cast("Json", operation.get("responses", {})).values()]
    for body in bodies:
        if body is None:
            continue
        resolved, file = _resolved(cast("Json", body), base)
        for media in cast("dict[str, Json]", resolved.get("content", {})).values():
            if "schema" in media and _binary(cast("Json", media["schema"]), file):
                return True
    return False


def operations(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    """Return each operation of the files of paths of a contract, by its identifier."""
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted((root / "paths").glob("*.yaml")):
        items = cast("dict[str, dict[str, Any]]", yaml.safe_load(path.read_text("utf-8")) or {})
        for item in items.values():
            for method in METHODS:
                if method in item:
                    found[item[method]["operationId"]] = (path, item[method])
    return found


def file_operations(root: Path) -> set[str]:
    """Return the operations of a contract that deposit or render a file."""
    return {
        name
        for name, (path, operation) in operations(root).items()
        if carries_a_file(operation, path)
    }


def enumeration(name: str) -> list[str]:
    """Return the values of an enumeration of the schemas of the exchanges."""
    schemas = yaml.safe_load((API / "components/schemas/exchanges.yaml").read_text("utf-8"))
    return cast("list[str]", schemas[name]["enum"])


def names_with(description: str, words: str, cited: str) -> bool:
    """Tell whether the description cites the requirement in the parentheses that follow the words.

    ``MS Project schedule (WF-INTF-0040)``: the requirement is attached to the passage that names
    the kind, not found anywhere in the description. The contract states it in prose, not in a
    field: the link is the parentheses after the words, with no full stop between them.
    """
    pattern = rf"{re.escape(words)}[^().]*\((?:[^)]*[ ,])?{re.escape(cited)}\b"
    return re.search(pattern, description, re.IGNORECASE) is not None


def requirement_of_intf_0150() -> projection.Requirement:
    return next(each for each in projection.read() if each.identifier == INTF)


@pytest.mark.requirement("WF-INTF-0150-A")
def test_the_operations_that_deposit_or_render_a_file_are_those_the_list_classifies() -> None:
    assert file_operations(API) == set(CARRIERS)


@pytest.mark.requirement("WF-INTF-0150-A")
def test_each_import_and_export_is_a_flow_of_the_table_its_operation_cites_the_requirement_of() -> (
    None
):
    table = flows(projection.PROJECTION.read_text(encoding="utf-8"))
    images = out_of_the_table(requirement_of_intf_0150().body)[EXPORT]
    found = operations(API)
    assert enumeration("ExchangeKind") == list(IMPORTS)
    assert enumeration("ExportKind") == list(EXPORTS)
    for kind, kinds, opening in (
        (IMPORT, IMPORTS, "openImport"),
        (EXPORT, EXPORTS, "requestExport"),
    ):
        description = found[opening][1]["description"]
        for each, target in kinds.items():
            cited = target
            if target in images:
                assert kind == EXPORT, each
            else:
                sense, cited = table[target]
                assert sense == SENSES[kind], each
            assert names_with(description, NAMES[each], cited), (opening, each, cited)


@pytest.mark.requirement("WF-INTF-0150-A")
def test_every_flow_of_a_file_of_the_table_is_served_by_one_import_or_export() -> None:
    table = flows(projection.PROJECTION.read_text(encoding="utf-8"))
    served = [*IMPORTS.values(), *(each for each in EXPORTS.values() if each.startswith("FLX"))]
    assert sorted(served) == sorted(table) == [f"FLX-0{n}" for n in range(1, 8)]


@pytest.mark.requirement("WF-INTF-0150-A")
def test_the_uses_of_an_upload_are_an_import_or_a_backup_and_backups_cite_their_requirement() -> (
    None
):
    backups = out_of_the_table(requirement_of_intf_0150().body)[BACKUP]
    assert enumeration("FileUploadPurpose") == list(PURPOSES)
    assert frozenset(PURPOSES.values()) == CARRIERS["uploadFile"]
    found = operations(API)
    backing = {name for name, carried in CARRIERS.items() if carried == frozenset({BACKUP})}
    assert backing - {"uploadFile"} == set(BACKUPS)
    for name, (words, cited) in BACKUPS.items():
        assert cited in backups, name
        assert names_with(found[name][1]["description"], words, cited), name


@pytest.mark.requirement("WF-INTF-0150-A")
def test_a_requirement_cited_elsewhere_in_the_description_does_not_name_the_kind() -> None:
    description = (
        "Estimate (WF-INTF-0100). An MS Project schedule is read. Remaining (WF-INTF-0120)."
    )
    assert names_with(description, "estimate", "WF-INTF-0100")
    assert names_with(description, "remaining", "WF-INTF-0120")
    assert not names_with(description, "MS Project schedule", "WF-INTF-0040")
    assert not names_with(description, "MS Project schedule", "WF-INTF-0100")
    assert not names_with(description, "estimate", "WF-INTF-0120")


@pytest.mark.requirement("WF-INTF-0150-A")
def test_a_picture_out_of_the_list_is_the_picture_of_a_user_and_of_no_project() -> None:
    found = operations(API)
    pictures = [name for name, carried in CARRIERS.items() if NO_PROJECT_DATA in carried]
    assert pictures == ["putMyAvatar", "getUserAvatar"]
    for name in pictures:
        assert found[name][0].stem in {"me", "access"}, name
        assert "avatar" in yaml.safe_dump(found[name][1]).lower(), name


@pytest.mark.requirement("WF-INTF-0150-A")
def test_no_operation_of_the_portfolio_deposits_or_renders_a_file() -> None:
    portfolio = {
        name for name, (path, _) in operations(API).items() if path.name == "portfolio.yaml"
    }
    assert len(portfolio) == 8
    assert portfolio.isdisjoint(file_operations(API))


@pytest.mark.requirement("WF-INTF-0150-A")
def test_an_operation_that_deposits_or_renders_a_file_is_found_by_reference_or_in_a_form(
    tmp_path: Path,
) -> None:
    (tmp_path / "paths").mkdir()
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "responses.yaml").write_text(
        "File:\n  content:\n    text/csv:\n      schema: { type: string, format: binary }\n"
        "Json:\n  content:\n    application/json:\n      schema: { type: object }\n",
        encoding="utf-8",
    )
    (tmp_path / "paths" / "portfolio.yaml").write_text(
        "/a:\n  get:\n    operationId: exportPortfolio\n"
        "    responses:\n      '200': { $ref: ../components/responses.yaml#/File }\n"
        "/b:\n  post:\n    operationId: importPortfolio\n    requestBody:\n      content:\n"
        "        multipart/form-data:\n          schema:\n            properties:\n"
        "              file: { type: string, format: binary }\n"
        "    responses:\n      '200': { $ref: ../components/responses.yaml#/Json }\n"
        "/c:\n  get:\n    operationId: getPortfolio\n"
        "    responses:\n      '200': { $ref: ../components/responses.yaml#/Json }\n",
        encoding="utf-8",
    )
    assert file_operations(tmp_path) == {"exportPortfolio", "importPortfolio"}


@pytest.mark.requirement("WF-INTF-0150-A")
def test_the_flows_of_a_file_are_read_from_the_table_those_of_the_screens_left_out() -> None:
    text = (
        "| FLX-01 Planning | MS Project | Waterfall | Entrant | Fichier (WF-INTF-0040) | Libre |\n"
        "| FLX-08 Coûts | SAP | Excel | Hors périmètre | Extraction ERP, hors Waterfall | Revue |\n"
        "| FLX-09 Planning | Chef de projet | Waterfall | Entrant | IHM | En continu |\n"
    )
    assert flows(text) == {"FLX-01": ("Entrant", "WF-INTF-0040")}
    body = "Les images exportées (WF-IHM-0130, WF-PLA-0120) et les sauvegardes (WF-ADM-0150) …"
    assert out_of_the_table(body) == {
        EXPORT: frozenset({"WF-IHM-0130", "WF-PLA-0120"}),
        BACKUP: frozenset({"WF-ADM-0150"}),
    }
