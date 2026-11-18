# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals of the abandonment of a differential and of a registration on it (US-2550/L2).

The conception of EP-08 writes into the contract the abandonment of a differential not merged
(``deleteCostStructure``, WF-REV-0100) and the refusal of a registration for tracking on a
structure other than the main one (``setNodeTracking``, #2497). Their refusals have each the
example that shows it, drawn from the witness:

- ``structure_delete_main_refused.json``, the main structure of the current revision 102
  abandoned: refused by ``unmerged_amendment_exists``, the structure not being a differential not
  merged;
- ``structure_delete_revision_marked.json``, the amendment 2 of the marked reference 101
  abandoned: refused by ``revision_draft``, as its ``delete`` command said beforehand
  (``structures_amendments``);
- ``structure_delete_stale.json``, the amendment 2 of the current revision sent with a counter
  older than the one it bears (``structures``): refused, its counter named;
- ``node_tracking_amendment_refused.json``, the design review of the amendment 2 registered to a
  timeline: refused by ``main_structure``.

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext
from wftools.mockgestures import TRACKED_TASK
from wftools.mockids import universe
from wftools.mockrefusals import REFERENCE, stale, state_refused
from wftools.mockwitness import fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

MAIN_CORRELATION, MARKED_CORRELATION = universe(1957), universe(1958)
STALE_CORRELATION, TRACKING_CORRELATION = universe(1959), universe(1960)
"""The correlations of the refusals of the differentials (US-2550/L2)."""

MAIN, AMENDMENT = universe(201), universe(203)
"""The main structure and the amendment 2 of the current revision 102 (``structures``)."""


def _structure(name: str, structure_id: str) -> JsonObject:
    """Return a structure as an example of listCostStructures lists it."""
    [found] = [
        each
        for each in cast("list[JsonObject]", fixture(name))
        if each["structure_id"] == structure_id
    ]
    return found


def _reference_name() -> str:
    """Return the version name of the marked revision 101, from the revisions written by hand."""
    revisions = cast("list[JsonObject]", fixture("revisions")["items"])
    [revision] = [each for each in revisions if each["revision_id"] == REFERENCE]
    return str(revision["version_name"])


def examples() -> dict[str, JsonObject]:
    """Return the refusals of the differentials, by file name."""
    reference = _reference_name()
    main, amendment = _structure("structures", MAIN), _structure("structures", AMENDMENT)
    label, counter = str(amendment["label"]), cast("int", amendment["lock_version"])
    task = next(row.label for row in mockcore.current() if row.number == TRACKED_TASK)
    return {
        "structure_delete_main_refused.json": mocktext.example(
            f"La « {main['label']} » de la révision courante du témoin abandonnée : elle existe "
            f"autant que sa révision, et seul un différentiel non fusionné s'abandonne — sa liste "
            f"de commandes ne le propose pas (delete) ; refusée par la condition qui manque, "
            f"unmerged_amendment_exists ; rien n'est supprimé (WF-REV-0100).",
            state_refused("unmerged_amendment_exists", MAIN_CORRELATION),
        ),
        "structure_delete_revision_marked.json": mocktext.example(
            f"Le différentiel « {label} » de la révision « {reference} », marquée, abandonné : "
            f"sa commande delete le disait d'avance (structures_amendments) ; refusé par la "
            f"condition qui manque, revision_draft ; rien n'est supprimé (WF-REV-0100, "
            f"WF-DAT-0020, WF-IHM-0090).",
            state_refused("revision_draft", MARKED_CORRELATION),
        ),
        "structure_delete_stale.json": mocktext.example(
            f"Le différentiel « {label} » de la révision courante abandonné avec le compteur "
            f"{counter - 1}, quand la structure porte {counter} — une saisie l'a écrite depuis la "
            f"lecture de l'écran — : refusé, le compteur courant rendu, et rien n'est supprimé ; "
            f"l'écran propose de relire (WF-IHM-0110).",
            stale(counter, STALE_CORRELATION),
        ),
        "node_tracking_amendment_refused.json": mocktext.example(
            f"La « {task} » du différentiel « {label} » inscrite à une chronologie : une "
            f"inscription est celle d'une tâche de la structure principale, celle qui s'exécute "
            f"et se suit, et le nœud d'un différentiel ne nomme pas task.tracking dans ses champs "
            f"saisissables ; refusée par la condition qui manque, main_structure ; rien n'est "
            f"écrit (WF-PLA-0060, WF-REV-0100, #2497).",
            state_refused("main_structure", TRACKING_CORRELATION),
        ),
    }
