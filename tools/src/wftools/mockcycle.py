# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of the witness while the designation of its reference is still open (US-0490/L2).

« La désignation manuelle est proposée tant que le projet n'a ni coût réel ni révision marquée
depuis la dernière désignation, et refusée au-delà » (WF-REV-0040). Today the witness has received
actual costs and marked the revision 101 since the offer was designated: no revision of
``revisions`` offers the designation. ``revisions_designation_open`` reads the history at an
earlier instant of the chronology, ``READ_AT``, on 15 January 2026 a minute before the order is
received and the offer designated (``mockwitness.ORDER_RECEIVED``): no designation has happened,
no actual cost has arrived, and the offer v1.0, marked on 15 December, lists the designation
available.

Nothing is written by hand here. The offer is the one ``revisions`` lists, at the same version,
its designation alone available; the revision 101, then in progress, is the one
``rate_update_applied`` answers, at the same version — the last write it had received. The offer
is so rendered at its version with one content. So is the 101: ``draft`` at its version 2 here
and in ``rate_update_applied``, its marking bearing one version more, 3, in ``revisions`` and
``revisions_marked`` (#421, #1352).
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import TYPE_CHECKING, cast

from wftools import mocktext
from wftools.mockhistory import OFFER
from wftools.mockwitness import ORDER_RECEIVED, fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

DESIGNATION = "designate_reference"
READ_AT = datetime.combine(ORDER_RECEIVED.on, time(10, 59), UTC)
"""The instant the history is read at: a minute before the order is received and the offer
designated, after the update of the rates the revision 101 received last."""


def _with_designation_open(revision: JsonObject) -> JsonObject:
    """Return a marked revision whose designation is offered, nothing missing to it."""
    commands = cast("list[JsonObject]", revision["available_commands"])
    return {
        **revision,
        "available_commands": [
            {**each, "is_available": True, "missing_conditions": []}
            if each["command"] == DESIGNATION
            else each
            for each in commands
        ],
    }


def revisions_designation_open() -> JsonObject:
    """Return what listRevisions answers at ``READ_AT``, before the offer is designated.

    The revision 101, opened on 12 January, then the offer v1.0, from the most recent to the
    oldest; the revision 102 is not opened yet.
    """
    [offer] = [each for each in fixture("revisions")["items"] if each["revision_id"] == OFFER]
    current = cast("JsonObject", fixture("rate_update_applied"))
    items: list[JsonValue] = [current, _with_designation_open(offer)]
    return {"items": items, "meta": {"limit": 50, "offset": 0, "total": len(items)}}


def examples() -> dict[str, JsonObject]:
    """Return the revisions of the witness while its designation is open, by file name."""
    return {
        "revisions_designation_open.json": mocktext.example(
            f"Les révisions du projet témoin le {mocktext.day(READ_AT.date())} à "
            f"{READ_AT.hour} h {READ_AT.minute:02d}, juste avant la réception de la commande et "
            f"la désignation de {ORDER_RECEIVED.at.hour} h : un instant antérieur de la même "
            f"chronologie. L'offre v1.0, marquée le 15 décembre pendant le chiffrage, propose sa "
            f"désignation comme référence, disponible : aucune désignation n'a encore eu lieu, et "
            f"le projet n'a reçu aucun coût réel (WF-REV-0040). La révision 101, en cours depuis "
            f"le 12 janvier, telle que l'a laissée la mise à jour des taux (rate_update_applied), "
            f"attend son marquage pour être désignée ; la révision courante 102 n'est pas encore "
            f"ouverte. La désignation qui suit est reference_designated. L'offre est celle que "
            f"liste revisions, à la même version, sa désignation seule changée ; la 101, "
            f"brouillon à sa version 2, voit son marquage porter la version 3 (#421, #1352).",
            revisions_designation_open(),
        ),
    }
