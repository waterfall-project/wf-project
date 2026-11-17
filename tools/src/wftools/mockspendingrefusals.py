# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals of the projection of spending (``getProjectSpending``, US-2050/L1, #3565).

``spending_rate_missing.json``: the projection asked while the electrical engineering, the category
of the role of a line of labour, would have no hourly rate for the reference year of the revision
read. It has meaning only complete: the refusal is that of an entry of a line, ``missing_rates``
naming the category without a field, on a correlation of its own (WF-DEV-0010, WF-DEV-0100).

``spending_no_reference.json``: the same projection on the reference budget of the project in
pricing, which has no reference revision yet; ``spending_revision_refused.json``: on the
re-estimated amounts of a marked revision named by ``revision_id`` when the one named is the
current revision, in draft; ``spending_subproject_unknown.json``: filtered on a subproject the
project does not have (WF-DEV-0100, WF-IND-0020; #3627).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from wftools import mocktext
from wftools.mockids import universe
from wftools.mockrefusals import field_refused, rate_missing
from wftools.mockstructure import REFERENCE_YEAR, JsonObject
from wftools.mockwitness import fixture

RATE_CORRELATION = universe(1874)
"""The correlation of the projection refused for a missing rate."""
NO_REFERENCE_CORRELATION = universe(1871)
"""The correlation of the projection on the reference budget refused without a reference."""
REVISION_CORRELATION = universe(1872)
"""The correlation of the projection refused on the current revision named as a marked one."""
SUBPROJECT_CORRELATION = universe(1873)
"""The correlation of the projection refused on a subproject the project does not have."""


def examples() -> dict[str, JsonObject]:
    """Return the refusals of the projection of spending, by file name."""
    offer = fixture("project_pricing")
    return {
        "spending_no_reference.json": mocktext.example(
            "La projection de dépenses demandée sur le budget de référence de l'extension de la "
            "ligne d'essais, en chiffrage, état que le refus nomme, avec "
            "son énumération : sans révision de référence, la base de la référence est absente "
            "(WF-DEV-0100).",
            {
                "code": "STATE_FORBIDS_OPERATION",
                "status": 409,
                "params": {"state": offer["state"], "state_enum": "ProjectState"},
                "correlation_id": NO_REFERENCE_CORRELATION,
            },
        ),
        "spending_revision_refused.json": mocktext.example(
            "La projection de dépenses demandée sur les montants réestimés d'une révision marquée, "
            "nommée par revision_id, quand la révision nommée est la révision courante, en "
            "brouillon : le paramètre est refusé, désigné par /query/revision_id (WF-DEV-0100).",
            field_refused("/query/revision_id", "VALIDATION_FAILED", REVISION_CORRELATION),
        ),
        "spending_subproject_unknown.json": mocktext.example(
            "La projection de dépenses filtrée sur un sous-projet que le projet n'a pas : le "
            "paramètre subproject_id est refusé, désigné par /query/subproject_id (WF-DEV-0100, "
            "WF-IND-0020).",
            field_refused("/query/subproject_id", "UNKNOWN_SUBPROJECT", SUBPROJECT_CORRELATION),
        ),
        "spending_rate_missing.json": mocktext.example(
            f"La projection de dépenses demandée sur le reste à engager de la révision en cours "
            f"quand l'ingénierie électrique, la catégorie du rôle d'une ligne de main-d'œuvre, "
            f"n'a pas de taux horaire pour {REFERENCE_YEAR}, l'année de référence de la révision : "
            f"la projection n'a de sens que complète, le refus nomme la catégorie, sans champ ; "
            f"rien n'est projeté (WF-DEV-0010, WF-DEV-0100).",
            rate_missing(RATE_CORRELATION),
        ),
    }
