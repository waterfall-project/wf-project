# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chronology of the witness, written for the loader of the projects (US-0990/L1).

``project_state_transitions.json``, beside the examples under ``fixtures/api/`` (the directory the
service ``witness`` of the Compose mounts): the events of ``mockwitness.CHRONOLOGY``, in their
order, each with its instant and what it writes in the slice of the projects. The back reads the
file and never imports ``wftools``; the slice of the projects (EP-04) imposes each instant on what
it writes (WF-CYC-0130).

The value is ``{"events": [...]}``; an event is ``{"sequence", "occurred_at", "what", "writes"}``.
``sequence`` counts from 1 in the order of the instants, ``occurred_at`` is the instant in universal
time (``2026-06-03T14:05:00Z``), ``what`` the label of the event and ``writes`` the list of what
the slice writes at that instant, in the order it writes it. A write is
``{"kind": …, "project": …}`` with ``project`` the code of the project it writes into
(``PRJ-001``, read from the example ``project.json``), and:

- ``project_created``: the project, in the state Created;
- ``revision_opened``, ``revision``: the revision opened;
- ``revision_marked``, ``revision``, ``version_name``: the revision marked under that name;
- ``designation_attempted``, ``revision``: the designation of a reference, which succeeds once the
  tasks and the lines are loaded; the project moves to In progress by the code entered next;
- ``rate_update_applied``, ``revision``, ``cost_category_ids``: the update of the rates accepted
  from the revision in progress for the labour categories named, those the proposal presents
  (``applyRateUpdate``, WF-REV-0060, C-362);
- ``code_entered``, ``code``: the code of the project entered (``PRJ-001``);
- ``state_transition``, ``from``, ``to``: the project changes state, by what is written before it
  (the opening of the offer: Created to Pricing; the code entered, once the reference is
  designated: Pricing to In progress).

An event the slice does not write (the installation, the entries of risks and of costs, the
imports; EP-06 to EP-09) has no write, and keeps its place: the order and the instants are the
chronology's.

The writes are exactly those the design of EP-04 lists for the loader (« L'amorçage et le
chargeur »), in that order: the revision 100 opened (Created to Pricing), its marking « v1.0 », the
101 opened, the designation of 100, the code entered, the 101 marked « Référence », the 102
opened; and, from EP-07 (« Le chargeur du témoin », US-1570/L1), the update
of the rates of 2026 accepted on the 101 a quarter of an hour after its opening, for the two labour
categories the offer employs. The witness abandons no revision, and the form has no kind of
abandon: the abandon of a revision is in the journey of the cycle, played by L2. The code entered
is written in the event of the order received, after the designation and before the event of the
marking of the 101, and the project moves to In progress by it (US-1570/L3, #2700).

The chronology dates PRJ-001 alone (``project_created``). PRJ-002 has no instant here: L2 creates
PRJ-002 and PRJ-001 from ``projects.json`` before the events, and the events write into PRJ-001.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wftools import mocktext, mockwitness
from wftools.mockstructure import LABOUR_RATES

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue
    from wftools.mockwitness import Event

NAME = "project_state_transitions.json"
"""The file the chronology is written to, under ``fixtures/api/``."""

OFFER = 100
REFERENCE = 101
CURRENT = 102
"""The revisions of the witness: the offer, the reference, and the revision in progress."""

RATED = tuple(sorted(LABOUR_RATES))
"""The labour categories whose rates of 2026 the update accepts on the 101: both the offer employs,
the ones the proposal presents (``rate_update``)."""

OFFER_VERSION = "Offre v1.0"
REFERENCE_VERSION = "Référence"
"""The names under which the offer and the reference are marked."""


def _writes() -> dict[Event, list[JsonObject]]:
    """Return what the slice writes, at each event it writes at, into the witness project."""
    code = mockwitness.fixture("project")["code"]
    into: JsonObject = {"project": code}
    return {
        mockwitness.CREATED: [{"kind": "project_created", **into}],
        mockwitness.OFFER_OPENED: [
            {"kind": "revision_opened", **into, "revision": OFFER},
            {"kind": "state_transition", **into, "from": "created", "to": "pricing"},
        ],
        mockwitness.OFFER_MARKED: [
            {
                "kind": "revision_marked",
                **into,
                "revision": OFFER,
                "version_name": OFFER_VERSION,
            }
        ],
        mockwitness.RISKS_IDENTIFIED: [{"kind": "revision_opened", **into, "revision": REFERENCE}],
        mockwitness.RATES_UPDATED: [
            {
                "kind": "rate_update_applied",
                **into,
                "revision": REFERENCE,
                "cost_category_ids": list(RATED),
            }
        ],
        mockwitness.ORDER_RECEIVED: [
            {"kind": "designation_attempted", **into, "revision": OFFER},
            {"kind": "code_entered", **into, "code": code},
            {"kind": "state_transition", **into, "from": "pricing", "to": "in_progress"},
        ],
        mockwitness.AMENDMENT_MERGED: [
            {
                "kind": "revision_marked",
                **into,
                "revision": REFERENCE,
                "version_name": REFERENCE_VERSION,
            }
        ],
        mockwitness.RISK_751_REVIEWED: [{"kind": "revision_opened", **into, "revision": CURRENT}],
    }


def instant(event: Event) -> str:
    """Write the instant of an event as the contract does: universal time, ``Z``."""
    return event.instant.strftime("%Y-%m-%dT%H:%M:%SZ")


def chronology() -> JsonObject:
    """Return the events of the witness, in the order of the chronology."""
    writes = _writes()
    events: list[JsonValue] = [
        {
            "sequence": number,
            "occurred_at": instant(event),
            "what": event.what,
            "writes": list(writes.get(event, [])),
        }
        for number, event in enumerate(mockwitness.CHRONOLOGY, start=1)
    ]
    return {"events": events}


def examples() -> dict[str, JsonObject]:
    """Return the chronology of the witness, by file."""
    return {
        NAME: mocktext.example(
            "La chronologie du témoin, chaque événement à son instant, dans l'ordre, avec ce que "
            "la tranche des projets écrit à cet instant : le projet créé, les révisions 100, 101 "
            "et 102 ouvertes, la mise à jour des taux de 2026 acceptée sur la 101 pour ses deux "
            "catégories de main-d'œuvre (WF-REV-0060), l'offre et la référence marquées, la "
            "désignation de l'offre 100, le code saisi, les transitions, dont le passage En cours "
            "(WF-CYC-0130). Chaque écriture nomme son projet, PRJ-001 : PRJ-002 n'est pas datée "
            "ici, le chargeur crée PRJ-002 et PRJ-001 depuis `projects.json` avant les "
            "événements, et `project_created` date PRJ-001. Lue par `waterfall-api load-witness` "
            "sans importer `wftools`.",
            chronology(),
        )
    }
