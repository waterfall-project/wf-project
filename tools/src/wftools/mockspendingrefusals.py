# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals of the projection of spending (``getProjectSpending``, US-2050/L1, #3565).

``spending_rate_missing.json``: the projection asked while the electrical engineering, the category
of the role of a line of labour, would have no hourly rate for the reference year of the revision
read. It has meaning only complete: the refusal is that of an entry of a line, ``missing_rates``
naming the category without a field, on a correlation of its own (WF-DEV-0010, WF-DEV-0100).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from wftools import mocktext
from wftools.mockids import universe
from wftools.mockrefusals import rate_missing
from wftools.mockstructure import REFERENCE_YEAR, JsonObject

RATE_CORRELATION = universe(1874)
"""The correlation of the projection refused for a missing rate."""


def examples() -> dict[str, JsonObject]:
    """Return the refusals of the projection of spending, by file name."""
    return {
        "spending_rate_missing.json": mocktext.example(
            f"La projection de dépenses demandée sur le reste à engager de la révision en cours "
            f"quand l'ingénierie électrique, la catégorie du rôle d'une ligne de main-d'œuvre, "
            f"n'a pas de taux horaire pour {REFERENCE_YEAR}, l'année de référence de la révision : "
            f"la projection n'a de sens que complète, le refus nomme la catégorie, sans champ ; "
            f"rien n'est projeté (WF-DEV-0010, WF-DEV-0100).",
            rate_missing(RATE_CORRELATION),
        ),
    }
