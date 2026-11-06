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
the slice writes at that instant, in the order it writes it. A write is ``{"kind": …}`` with:

- ``project_created``: the project, in the state Created;
- ``revision_opened``, ``revision``: the revision opened;
- ``revision_marked``, ``revision``, ``version_name``: the revision marked under that name;
- ``designation_attempted``, ``revision``, ``refused``: the designation of a reference, and the
  refusal it is met with on a structure without a task (``no_task``);
- ``code_entered``: the code of the project entered;
- ``state_transition``, ``from``, ``to``: the project changes state.

An event the slice does not write (the installation, the entries of risks and of costs, the
imports; EP-06 to EP-09) has no write, and keeps its place: the order and the instants are the
chronology's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wftools import mocktext, mockwitness

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue
    from wftools.mockwitness import Event

NAME = "project_state_transitions.json"
"""The file the chronology is written to, under ``fixtures/api/``."""

OFFER = 100
REFERENCE = 101
CURRENT = 102
"""The revisions of the witness: the offer, the reference, and the revision in progress."""

OFFER_VERSION = "v1.0"
REFERENCE_VERSION = "Référence"
"""The names under which the offer and the reference are marked."""

_WRITES: dict[Event, list[JsonObject]] = {
    mockwitness.CREATED: [{"kind": "project_created"}],
    mockwitness.OFFER_OPENED: [
        {"kind": "revision_opened", "revision": OFFER},
        {"kind": "state_transition", "from": "created", "to": "costing"},
    ],
    mockwitness.OFFER_MARKED: [
        {"kind": "revision_marked", "revision": OFFER, "version_name": OFFER_VERSION}
    ],
    mockwitness.RISKS_IDENTIFIED: [{"kind": "revision_opened", "revision": REFERENCE}],
    mockwitness.ORDER_RECEIVED: [
        {"kind": "designation_attempted", "revision": OFFER, "refused": "no_task"},
        {"kind": "code_entered"},
    ],
    mockwitness.AMENDMENT_MERGED: [
        {"kind": "revision_marked", "revision": REFERENCE, "version_name": REFERENCE_VERSION}
    ],
    mockwitness.RISK_751_REVIEWED: [{"kind": "revision_opened", "revision": CURRENT}],
}
"""What the slice writes at each event of the chronology that it writes anything at."""


def instant(event: Event) -> str:
    """Write the instant of an event as the contract does: universal time, ``Z``."""
    return event.instant.strftime("%Y-%m-%dT%H:%M:%SZ")


def chronology() -> JsonObject:
    """Return the events of the witness, in the order of the chronology."""
    events: list[JsonValue] = [
        {
            "sequence": number,
            "occurred_at": instant(event),
            "what": event.what,
            "writes": list(_WRITES.get(event, [])),
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
            "et 102 ouvertes, l'offre et la référence marquées, la désignation tentée et refusée "
            "faute de tâches, le code saisi, les transitions (WF-CYC-0130). Lue par "
            "`waterfall-api load-witness` sans importer `wftools`.",
            chronology(),
        )
    }
