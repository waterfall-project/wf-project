# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planning start of a structure moved a week earlier (US-0701/L2, #1602, E-01).

« Une tâche en mode automatique sans prédécesseur commence à la date de début de planning ;
avancer cette date d'une semaine l'avance d'autant, ainsi que ses successeurs automatiques »
(WF-PLA-0020). `updateCostStructure` writes the planning start of a structure and answers as any
write of the grids (`NodesWritten`): here the difference between two readings of the main
structure of the witness, before and after (``wftools.mockwrites.written``), never written by
hand. Today the witness has started tasks, whose state the generator reads from their dates: the
date moved, they would change state. The write is so read in a declared variant, on
``ADVANCED_ON``, before any task starts by its dates; ``wftools.mockdata`` writes it under
``fixtures/api/volume/``, the whole structure of a thousand tasks being redated.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext, mockwitness
from wftools.mockstructure import described
from wftools.mockwrites import written

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

ADVANCED_ON = date(2026, 2, 20)
"""The day of the variant that advances the planning start of the main structure: the risk 752
merged that afternoon, the studies not begun, no task started but those declared (WF-PLA-0130)."""

ADVANCED_BY = timedelta(weeks=1)
"""How far the planning start moves earlier: from Monday 2 March to Monday 23 February 2026."""

REDATED = ("rescheduled", "ancestors", "reinflated")
"""What a planning start moved renders of the structure, besides its totals (`NodesWritten`)."""


def reading(start: date = mockwitness.PLANNING_START) -> list[mockcore.Row]:
    """Return the main structure the variant reads on ADVANCED_ON, from a planning start."""
    return mockcore.core(described(), ADVANCED_ON, previous=mockcore.REFERENCE, start=start)


def planning_start_advanced() -> JsonObject:
    """Return what updateCostStructure answers when the planning start moves a week earlier.

    Every task in automatic mode without a predecessor starts on the new date, its automatic
    successors a week earlier with it, the tasks in manual mode where they were (Vérif of
    WF-PLA-0020). The write writes no node: the structure itself, its counter one further.
    """
    before = mockcore.whole(reading())
    after = mockcore.whole(reading(mockwitness.PLANNING_START - ADVANCED_BY))
    return written(before, after, [])


def example() -> JsonObject:
    """Return the planning start of the main structure advanced a week, as its example."""
    answer = planning_start_advanced()
    was = mockwitness.PLANNING_START
    counted = {key: mocktext.count(len(cast("list[JsonValue]", answer[key]))) for key in REDATED}
    return mocktext.example(
        f"Variante contrefactuelle déclarée : le {mocktext.day(ADVANCED_ON)}, le devis propre du "
        "risque 752 fusionné et aucune tâche encore démarrée par ses dates, la date de début de "
        "planning de la structure principale du témoin, aux volumes du §4.6.2, avancée d'une "
        f"semaine, du {mocktext.day(was)} au {mocktext.day(was - ADVANCED_BY)}. Chaque tâche "
        "automatique sans prédécesseur commence à la nouvelle date, et ses successeurs "
        "automatiques une semaine plus tôt avec elle ; les tâches en mode manuel ne bougent pas : "
        f"{counted['rescheduled']} tâches redatées (rescheduled), {counted['ancestors']} "
        f"récapitulatives recalculées (ancestors), et {counted['reinflated']} lignes et tâches "
        "dont l'année de consommation change (reinflated). L'écriture ne porte sur aucun nœud "
        "(nodes vide) ; le compteur de la structure avance (WF-PLA-0020, WF-REV-0100).",
        answer,
    )
