# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs of the witness, written for the loader of the costs (US-1650/L1).

``witness_costs.json``, beside the examples under ``fixtures/api/`` (the directory the service
``witness`` of the Compose mounts), as ``witness_lines.json`` is for the lines
(``wftools.mockwitnesslines``): the imports of costs of PRJ-001 and the lines of cost they brought,
as ``wftools.mockwitnesscosts`` describes them, ``mockcosts`` computes what follows from them and
``mockexchanges`` presents their reports. The back reads the file with a model of its own and never
imports ``wftools``; the slice of the costs (EP-09, US-1650/L2) loads each import at the instant of
its event of the chronology (``project_state_transitions.json``), through the interfaces of the
exchanges and of the costs, and the amounts and imputations are those the service computes: the
computed becomes the expected (EP-09, « Le chargeur du témoin »).

The value is ``{"imports": [...], "lines": [...]}``. An import, in the order of the journal, is:

- ``cost_import_id``: its identifier in the journal of the costs, the one the event
  ``cost_import_applied`` of the chronology names;
- ``imported_at``: the instant it was applied, that of its event;
- ``import_id``: the import of the exchanges that applied it, with ``filename``, as
  ``imports.json`` lists it;
- ``period_from``, ``period_to``: the period it extracted, each bound possibly ``null``;
- ``kept_columns``: the columns of the file it kept, in the order of its lines;
- ``report``: its report as its analysis presented it, before it was applied (``ImportReport``);
- ``created_count``, ``updated_count``, ``unchanged_count``, ``rejected_count``: its counts, those
  of the journal (``cost_imports.json``).

A line is:

- ``cost_line_id``, ``document_number``, ``document_item``, ``document_date``, ``amount``: its
  identifier, its document, its item (``null`` without), its date of document and its signed
  amount, a string;
- ``subproject_code``, ``subproject_id``: the code its element of the work breakdown structure
  carries, and the subproject it is imputed to (``null`` when the project has none of that code,
  WF-CRE-0020);
- ``passthrough``: the columns kept of the file, by their names;
- ``created_by_cost_import_id``, ``updated_by_cost_import_ids``: the import that brought it, and
  those that brought it again, updated, in their order (WF-CRE-0010);
- ``excluded``: ``null``, or ``{"excluded_at", "reason"}`` when it was taken out of the tracked
  scope (WF-CRE-0030).

No address and no label of a real project is here: the suppliers and the documents are the
witness's, fictitious.
"""

from typing import TYPE_CHECKING, cast

from wftools import mockcosts, mockexchanges, mocktext
from wftools.mockhistory import stamp
from wftools.mockids import hex_identifier
from wftools.mockstructure import money
from wftools.mockwitness import fixture
from wftools.mockwitnesscosts import JOURNAL, CostImport, CostLine

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

NAME = "witness_costs.json"
"""The file the costs are written to, under ``fixtures/api/``."""


def import_id(entry: CostImport) -> str:
    """Return the identifier of an import in the journal of the costs."""
    return hex_identifier(entry.number)


def exchange_id(entry: CostImport) -> str:
    """Return the identifier of the import of the exchanges that applied an import."""
    return hex_identifier(entry.exchange)


def expired_exchange_id() -> str:
    """Return the identifier of the extraction of April replayed, analysed and expired.

    The only import of costs of the exchanges that was not applied (``imports.json``); the journal
    keeps nothing of it.
    """
    [expired] = [
        item["import_id"]
        for item in fixture("imports")["items"]
        if item["kind"] == "actual_costs" and item["status"] == "expired"
    ]
    return cast("str", expired)


def _filenames() -> dict[str, str]:
    return {item["import_id"]: item["filename"] for item in fixture("imports")["items"]}


def _import(entry: CostImport) -> JsonObject:
    created, updated, unchanged, rejected = mockcosts.counts(entry)
    brought = [line for line in mockcosts.lines() if entry in line.imports]
    start, end = entry.period
    return {
        "cost_import_id": import_id(entry),
        "imported_at": stamp(entry.event.instant),
        "import_id": exchange_id(entry),
        "filename": _filenames()[exchange_id(entry)],
        "period_from": None if start is None else start.isoformat(),
        "period_to": None if end is None else end.isoformat(),
        "kept_columns": cast("list[JsonValue]", mockcosts.passthrough_columns(brought)),
        "report": mockexchanges.cost_report(entry),
        "created_count": created,
        "updated_count": updated,
        "unchanged_count": unchanged,
        "rejected_count": rejected,
    }


def _line(line: CostLine) -> JsonObject:
    excluded: JsonValue = None
    if line.excluded is not None:
        excluded = {"excluded_at": stamp(line.excluded[0]), "reason": line.excluded[1]}
    read = mockcosts.cost_line(line)
    return {
        "cost_line_id": mockcosts.cost_line_id(line.number),
        "document_number": line.document,
        "document_item": line.item,
        "document_date": line.on.isoformat(),
        "amount": money(line.amount),
        "subproject_code": line.code,
        "subproject_id": read["subproject_id"],
        "passthrough": read["passthrough"],
        "created_by_cost_import_id": import_id(line.imports[0]),
        "updated_by_cost_import_ids": [import_id(each) for each in line.imports[1:]],
        "excluded": excluded,
    }


def costs() -> JsonObject:
    """Return the imports of costs of the witness and the lines they brought."""
    imports = sorted(JOURNAL, key=lambda each: each.event.instant)
    return {
        "imports": [_import(entry) for entry in imports],
        "lines": [_line(line) for line in mockcosts.lines()],
    }


def examples() -> dict[str, JsonObject]:
    """Return the costs of the witness, by file."""
    return {
        NAME: mocktext.example(
            "Les coûts réels du projet témoin pour le chargeur des coûts : les cinq imports du "
            "journal de PRJ-001, chacun par son identifiant, l'import des échanges qui l'a "
            "appliqué, son fichier, sa période, ses colonnes conservées, son compte rendu tel que "
            "son analyse le présenta et ses comptes ; et chaque ligne de coût, par sa pièce, son "
            "poste, sa date, son montant, son code de sous-projet, ses colonnes conservées, "
            "l'import qui l'a apportée, ceux qui l'ont mise à jour et son exclusion du périmètre "
            "suivi (WF-CRE-0010, WF-CRE-0020, WF-CRE-0030, WF-CRE-0050, WF-QUA-0040-A). Les "
            "montants et les imputations sont ceux que le service calcule. Lu par "
            "`waterfall-api load-witness` sans importer `wftools`.",
            costs(),
        )
    }
