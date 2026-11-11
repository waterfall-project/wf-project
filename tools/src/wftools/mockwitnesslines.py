# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The estimate lines of the witness, written for the loader of the lines (US-1570/L1).

``witness_lines.json``, beside the examples under ``fixtures/api/`` (the directory the service
``witness`` of the Compose mounts), as ``witness_tasks.json`` is for the tasks
(``wftools.mockwitnesstasks``): for each revision of PRJ-001 — the offer 100, the reference 101 and
the revision in progress 102 —, its estimate lines by lineage, as the structure of the witness
(``wftools.mockcore``, ``mockstructure``, ``mockhistory``) holds them. The back reads the file
with a model of its own and never imports ``wftools``; the slice of the lines (EP-07, US-1570/L2)
reconciles with it, by lineage, the lines the copy of a revision gave it, after the slice of the
tasks has written the tasks that bear them, and the amounts are those the service computes: the
computed becomes the expected (EP-07, « Le chargeur du témoin »).

The value is ``{"revisions": [...], "lines": [...]}``. A revision is ``{"revision",
"line_count"}``: its number and how many lines the file gives it. ``lines`` lists, revision after
revision, each in the order of the plan. A line is:

- ``revision``, ``node_id``, ``lineage_id``: the revision it belongs to, its identifier there and
  its lineage, which is what the revisions share;
- ``task_lineage_id``: the lineage of the task that bears it, which ``witness_tasks.json`` gives
  for the same revision;
- ``position``: its rank among the lines of that task, from 1 — the lines of a task come before
  its subordinates, so that it is also its rank among its siblings, as the contract reads
  ``Node.position``;
- the facet entered, as ``EstimateLineWrite`` carries it: ``label``, ``cost_category_id``,
  ``resource_role_id`` (``null`` but for labour), ``quantity``, ``hours`` (``null`` but for
  labour), ``unit_disbursement`` (``null`` for labour), ``payment_delay_days`` and
  ``subproject_id`` (``null`` without).

Nothing computed is there: neither the amounts — the budget is fixed by the lineage, the base and
the re-estimate by the rates and the dates of the revision (« Le calcul des montants ») — nor the
year of consumption. Nor the lines of provision, which the declaration of a risk creates, never an
entry (WF-RIS-0010): they are EP-08's, with the risks. The lines the occurrence of a risk merged
into the revision in progress are there, as any other line it bears.

No address and no label of a real project is here: the labels are the witness's, fictitious.
"""

from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockhistory, mocktext

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

NAME = "witness_lines.json"
"""The file the lines are written to, under ``fixtures/api/``."""

OFFER, REFERENCE, CURRENT = 100, 101, 102
"""The numbers of the revisions of the witness, as the chronology writes them."""

ENTERED = (
    "label",
    "cost_category_id",
    "resource_role_id",
    "quantity",
    "hours",
    "unit_disbursement",
    "payment_delay_days",
    "subproject_id",
)
"""The fields of the facet of a line that an entry gives it (``EstimateLineWrite``)."""


def _structures() -> dict[int, list[mockcore.Row]]:
    """Return the structure of each revision of the witness, as its tasks are read."""
    return {
        OFFER: mockhistory.offer_rows(),
        REFERENCE: mockhistory.reference_rows(),
        CURRENT: mockcore.current(),
    }


def _line(revision: int, row: mockcore.Row, lineages: dict[str, str]) -> JsonObject:
    """Return a line of a revision, from the node the structure emits for it."""
    node = row.node
    facet = cast("JsonObject", node["estimate_line"])
    return {
        "revision": revision,
        "node_id": node["node_id"],
        "lineage_id": node["lineage_id"],
        "task_lineage_id": lineages[cast("str", node["parent_id"])],
        "position": node["position"],
        **{key: facet[key] for key in ENTERED},
    }


def lines() -> JsonObject:
    """Return the lines of the three revisions of the witness, provisions left out."""
    revisions: list[JsonValue] = []
    found: list[JsonValue] = []
    for revision, rows in _structures().items():
        lineages = {
            cast("str", row.node["node_id"]): cast("str", row.node["lineage_id"])
            for row in rows
            if row.kind == mockcore.TASK
        }
        own = [
            _line(revision, row, lineages)
            for row in rows
            if row.kind == mockcore.ESTIMATE_LINE and not mockhistory.is_provision(row)
        ]
        found.extend(own)
        revisions.append({"revision": revision, "line_count": len(own)})
    return {"revisions": revisions, "lines": found}


def examples() -> dict[str, JsonObject]:
    """Return the lines of the witness, by file."""
    return {
        NAME: mocktext.example(
            "Les lignes de devis du projet témoin par révision, pour le chargeur des lignes : "
            "celles des révisions 100, 101 et 102 de PRJ-001, chacune par sa lignée, dans l'ordre "
            "du plan — la lignée de la tâche qui la porte, son rang parmi les lignes de cette "
            "tâche, sa facette saisie (libellé, catégorie, rôle, quantité, charge, débours, délai "
            "de paiement, sous-projet) —, sans les montants, que le service calcule, ni les lignes "
            "de provision, que la déclaration d'un risque crée (WF-DEV-0020, WF-QUA-0040-A). Lues "
            "par `waterfall-api load-witness` sans importer `wftools`.",
            lines(),
        )
    }
