# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals of one form each: a state refused by its condition, a catalogue without dead codes.

The review of the contract before the freeze (`docs/api/2026-10-28-contrat-avant-gel.md`, D-05,
J-01, J-02) and the decision of the author of the 2026-10-28: a terminal project and a marked
revision are refused everywhere by 409 ``STATE_FORBIDS_OPERATION`` and their missing condition,
never by a 403 (US-0702/L1):

- ``timeline_create_terminal.json``, a timeline created on the witness completed today
  (``project_completed``), refused by ``project_not_terminal``, as ``manage_timelines`` says it
  beforehand — and ``timeline_delete_terminal``, written by hand (#803), refused alike;
- ``node_create_marked_refused.json`` and ``skeleton_marked_refused.json``, a task created and the
  skeleton generated on the reference, the marked revision 101, refused by ``revision_draft``,
  the condition the revision names for its entries (``revision_marked``).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from wftools import mocktext
from wftools.mockids import universe
from wftools.mockwitness import CREATED_TIMELINE, fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

TIMELINE_CORRELATION, NODE_CORRELATION, SKELETON_CORRELATION = (
    universe(1610),
    universe(1611),
    universe(1612),
)
"""The correlations of the refusals of a state."""

REFERENCE = universe(101)
"""The reference of the witness, its marked revision 101."""


def state_refused(condition: str, correlation: str) -> JsonObject:
    """Return the refusal of a command a state makes unavailable: its missing condition named."""
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": condition},
        "correlation_id": correlation,
    }


def _reference() -> str:
    """Return the version name of the marked revision 101, from the revisions written by hand."""
    revisions = cast("list[JsonObject]", fixture("revisions")["items"])
    [revision] = [each for each in revisions if each["revision_id"] == REFERENCE]
    return str(revision["version_name"])


def examples() -> dict[str, JsonObject]:
    """Return the refusals of a state, by file."""
    project = cast("JsonObject", fixture("project_completed"))
    reference = _reference()
    _, timeline = CREATED_TIMELINE
    return {
        "timeline_create_terminal.json": mocktext.example(
            f"Une chronologie « {timeline} » créée sur le projet témoin, « {project['label']} », "
            f"terminé aujourd'hui (project_completed) : refusée par la condition que sa commande "
            f"manage_timelines dit manquer, project_not_terminal, comme toute écriture d'un "
            f"projet terminal ; rien n'est créé (WF-CYC-0100, WF-PLA-0140, WF-IHM-0090).",
            state_refused("project_not_terminal", TIMELINE_CORRELATION),
        ),
        "node_create_marked_refused.json": mocktext.example(
            f"Une tâche créée sur la structure principale de la révision « {reference} », "
            f"marquée (revision_marked) : refusée par la condition que la révision dit manquer à "
            f"ses saisies, revision_draft, une révision marquée ne se modifiant plus ; rien n'est "
            f"créé (WF-DAT-0020, WF-IHM-0090).",
            state_refused("revision_draft", NODE_CORRELATION),
        ),
        "skeleton_marked_refused.json": mocktext.example(
            f"La génération du squelette de planning demandée sur la révision « {reference} », "
            f"marquée (revision_marked) : refusée par la seule condition que sa commande "
            f"generate_skeleton dit manquer, revision_draft ; rien n'est écrit (WF-DAT-0020, "
            f"WF-PRJ-0030, WF-IHM-0090).",
            state_refused("revision_draft", SKELETON_CORRELATION),
        ),
    }
