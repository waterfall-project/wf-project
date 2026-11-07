# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of the witness, written for the loader of the tasks (US-1480/L1).

``witness_tasks.json``, beside the examples under ``fixtures/api/`` (the directory the service
``witness`` of the Compose mounts), as ``project_state_transitions.json`` is for the projects
(``wftools.mockchronology``): for each revision of PRJ-001 — the offer 100, the reference 101 and
the revision in progress 102 —, its tasks by lineage, as the structure of the witness
(``wftools.mockcore``, ``mockstructure``, ``mockhistory``) holds them, and the planning start of
that structure. The back reads the file with a model of its own and never imports ``wftools``; the
slice of the tasks (EP-06) reconciles with it, by lineage, the tasks the copy of a revision gave
it, and the dates are those the engine computes: the computed becomes the expected (EP-06,
« Le chargeur du témoin »).

The value is ``{"revisions": [...], "tasks": [...]}``. A revision is ``{"revision", "read_on",
"planning_start_on", "task_count"}``: its number, the day its progress and its dates are read at
(the day it was marked, today for the revision in progress), the planning start of its structure
(WF-PLA-0020) and how many tasks the file gives it. ``tasks`` lists, revision after revision, each
in the order of the plan — a task before its subordinates, so that a parent is always met first;
a predecessor may come later. A task is:

- ``revision``, ``node_id``, ``lineage_id``: the revision it belongs to, its identifier there and
  its lineage, which is what the revisions share;
- ``parent_lineage_id`` (``null`` for a root of the structure) and ``position``, its rank among its
  siblings from 1, counted as the contract reads ``Node.position``, the lines of a task before its
  subordinates (the lines are EP-07's: a rank may skip those a task bears);
- ``label``, ``description`` (``null`` without), ``is_summary``, ``is_milestone``;
- ``scheduling_mode`` (``automatic`` | ``manual``), ``duration`` (``{"value", "unit"}``, as kept),
  ``start`` and ``finish`` (``{"date", "hours"}``, as the engine computes them);
- ``order_item_id`` and ``work_package_id``: the post or the lot of the work breakdown it bears,
  ``null`` for a task bearing none;
- ``predecessors``: ``{"predecessor_lineage_id", "link_type", "lag": {"value", "unit"}}``;
- ``progress`` (``not_started`` | ``started`` | ``completed``), ``started_on`` and ``completed_on``
  (a date, or ``null``);
- ``inscriptions``: ``{"kind": "timeline" | "milestone_tracking", "timeline_id"}``, ``timeline_id``
  being ``null`` for the time/time tracking.

No address and no label of a real project is here: the labels are the witness's, fictitious.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockhistory, mocktext, mockwitness

if TYPE_CHECKING:
    from datetime import date

    from wftools.mockstructure import JsonObject, JsonValue

NAME = "witness_tasks.json"
"""The file the tasks are written to, under ``fixtures/api/``."""

OFFER, REFERENCE, CURRENT = 100, 101, 102
"""The numbers of the revisions of the witness, as the chronology writes them."""


def _structures() -> dict[int, tuple[date, list[mockcore.Row]]]:
    """Return the structure of each revision, with the day it is read at."""
    return {
        OFFER: (mockwitness.OFFER_MARKED.on, mockhistory.offer_rows()),
        REFERENCE: (mockwitness.AMENDMENT_MERGED.on, mockhistory.reference_rows()),
        CURRENT: (mockcore.READ_ON, mockcore.current()),
    }


def _task(revision: int, row: mockcore.Row, lineages: dict[str, str]) -> JsonObject:
    """Return a task of a revision, from the node the structure emits for it."""
    node = row.node
    facet = cast("JsonObject", node["task"])
    entries = cast("list[JsonObject]", node.get("predecessors", []))
    parent = node["parent_id"]
    return {
        "revision": revision,
        "node_id": node["node_id"],
        "lineage_id": node["lineage_id"],
        "parent_lineage_id": None if parent is None else lineages[cast("str", parent)],
        "position": node["position"],
        "label": facet["label"],
        "description": facet.get("description"),
        "is_summary": facet["is_summary"],
        "is_milestone": facet["is_milestone"],
        "scheduling_mode": facet["scheduling_mode"],
        "duration": facet["duration"],
        "start": facet["start"],
        "finish": facet["finish"],
        "order_item_id": facet.get("order_item_id"),
        "work_package_id": facet.get("work_package_id"),
        "predecessors": [
            {
                "predecessor_lineage_id": lineages[cast("str", entry["predecessor_node_id"])],
                "link_type": entry["link_type"],
                "lag": entry["lag"],
            }
            for entry in entries
        ],
        "progress": facet["progress"],
        "started_on": facet.get("started_on"),
        "completed_on": facet.get("completed_on"),
        "inscriptions": facet.get("tracking", []),
    }


def tasks() -> JsonObject:
    """Return the tasks of the three revisions of the witness, and the planning start."""
    revisions: list[JsonValue] = []
    found: list[JsonValue] = []
    for revision, (read_on, rows) in _structures().items():
        own = [row for row in rows if row.kind == mockcore.TASK]
        lineages = {
            cast("str", row.node["node_id"]): cast("str", row.node["lineage_id"]) for row in own
        }
        found.extend(_task(revision, row, lineages) for row in own)
        revisions.append(
            {
                "revision": revision,
                "read_on": read_on.isoformat(),
                "planning_start_on": mockwitness.PLANNING_START.isoformat(),
                "task_count": len(own),
            }
        )
    return {"revisions": revisions, "tasks": found}


def examples() -> dict[str, JsonObject]:
    """Return the tasks of the witness, by file."""
    return {
        NAME: mocktext.example(
            "Les tâches du projet témoin par révision, pour le chargeur des tâches : celles des "
            "révisions 100, 101 et 102 de PRJ-001, chacune par sa lignée, dans l'ordre du plan — "
            "son parent par sa lignée, son rang, sa facette (libellé, mode, durée, dates que le "
            "moteur calcule, poste ou lot qu'elle porte), ses liaisons par la lignée de leur "
            "prédécesseur, son état et ses dates de démarrage et de terminaison, ses inscriptions "
            "aux chronologies et au suivi temps/temps — et la date de début de planning de chaque "
            "structure (WF-PLA-0020, WF-PLA-0060, WF-PLA-0130, WF-QUA-0040-A). Lues par "
            "`waterfall-api load-witness` sans importer `wftools`.",
            tasks(),
        )
    }
