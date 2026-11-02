# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contributors of the witness once an account is anonymised today (#870).

An anonymised account has no name any more (WF-ADM-0060), and the contract renders none nor any
sentence in its place (WF-ARC-0110): `Contributor.display_name` is null, as `ActorRef.display_name`
is. ``contributors_anonymized.json`` reads the list of the witness (``contributors``) once the
accounts that ``users_anonymized`` anonymises today are: their rows say no name, and the list
without sort, by kind then by name, ranges them after the others of their kind, as a sort ranges a
row without value after the others in the ascending order (``mocklists.ordered``). Nothing else
changes: the anonymisation writes the account, not the list, whose counter stays.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from wftools import mocktext
from wftools.mocklists import CONTRIBUTOR_KINDS, contributor_list, ordered
from wftools.mockwitness import fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject


def anonymized_contributors(contributors: JsonObject) -> list[JsonObject]:
    """Return the contributors once the accounts ``users_anonymized`` lists are anonymised."""
    anonymized = {
        cast("str", each["user_id"])
        for each in cast("list[JsonObject]", fixture("users_anonymized")["items"])
        if each["anonymized_at"] is not None
    }
    rows = [
        {**each, "display_name": None} if each["user_id"] in anonymized else each
        for each in cast("list[JsonObject]", contributors["items"])
    ]
    return [
        row
        for kind in CONTRIBUTOR_KINDS
        for row in ordered(
            (each for each in rows if each["kind"] == kind),
            lambda row: None if row["display_name"] is None else 0,
        )
    ]


def _names(rows: list[JsonObject]) -> str:
    """Say contributors by the name of their account."""
    return mocktext.listed([str(row["display_name"]) for row in rows])


def examples() -> dict[str, JsonObject]:
    """Return the contributors of the witness once an account is anonymised, by file name."""
    contributors = fixture("contributors")
    people = cast("list[JsonObject]", contributors["items"])
    anonymized = anonymized_contributors(contributors)
    named = [each for each in anonymized if each["display_name"] is not None]
    nameless = {str(each["user_id"]) for each in anonymized if each["display_name"] is None}
    gone = _names([each for each in people if each["user_id"] in nameless])
    return {
        "contributors_anonymized.json": mocktext.example(
            f"Les contributeurs du projet, le compte de « {gone} », désactivé depuis son "
            f"inscription, anonymisé aujourd'hui (users_anonymized) : son nom affiché est nul, "
            f"que le front présente sous le libellé neutre de son catalogue — l'API ne rend ni "
            f"son nom ni une phrase —, et il vient après les autres contributeurs, "
            f"{_names(named)}, la liste sans tri rangeant les comptes par leur nom ; il reste "
            f"listé et signalé. L'anonymisation écrit le compte, non la liste, dont le compteur "
            f"ne change pas (WF-ADM-0060, WF-ARC-0110, #870).",
            contributor_list(contributors, anonymized, filtered=False),
        ),
    }
