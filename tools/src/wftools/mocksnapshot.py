# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a marked revision of the witness conserves of the reference: its snapshot (US-0701/L2).

`getRevision` renders, for a marked revision, the values of the reference its structures employ,
frozen at its marking (`RevisionSnapshot`, WF-REV-0030): the resource roles of its labour lines,
the calendars of these roles and the default one, that of a task without a labour line
(WF-PLA-0010), the cost categories of its lines, and the hourly rate of each labour category it
employs for its reference year — each the image of the object, without the commands a reading of
today adds (`EmployedReference`). The reference 101 and the offer 100 are those the list of the
revisions written by hand names (``revisions``), each with the snapshot of the structure it
marked (``mockhistory``): ``revision_marked`` and ``revision_offer`` are never written by hand. No
object of the reference changed since the installation, so that the image of each is the object
read today, its commands left out.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockhistory, mocktext
from wftools.mockstructure import LABOUR_RATES, money
from wftools.mockwitness import by_identifier, default_calendar, fixture

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from wftools.mockstructure import JsonObject, JsonValue

COMMANDS = "available_commands"
"""What a reading of today adds to the image of an object of the reference (WF-IHM-0090)."""


def _image(entry: JsonObject) -> JsonValue:
    return {key: value for key, value in entry.items() if key != COMMANDS}


def employed_reference(
    rows: Iterable[mockcore.Row],
    rates: Mapping[str, Decimal],
    year: int,
    categories: Iterable[JsonValue],
) -> JsonObject:
    """Return the values of the reference a structure employs, as its revision conserves them."""
    lines = [
        cast("JsonObject", row.node["estimate_line"])
        for row in rows
        if row.kind == mockcore.ESTIMATE_LINE
    ]
    employed = {str(line["resource_role_id"]) for line in lines}
    roles = [
        role
        for role in by_identifier("resource_roles", "resource_role_id")
        if role["resource_role_id"] in employed
    ]
    calendars = {str(role["calendar_id"]) for role in roles} | {default_calendar().calendar_id}
    used = {str(line["cost_category_id"]) for line in lines}
    return {
        "resource_roles": [_image(role) for role in roles],
        "calendars": [
            _image(calendar)
            for calendar in by_identifier("calendars", "calendar_id")
            if calendar["calendar_id"] in calendars
        ],
        "cost_categories": sorted(
            (
                _image(category)
                for category in cast("Iterable[JsonObject]", categories)
                if category["cost_category_id"] in used
            ),
            key=lambda image: str(cast("JsonObject", image)["cost_category_id"]),
        ),
        "hourly_rates": [
            {"cost_category_id": category, "year": year, "amount": money(rates[category])}
            for category in sorted(rates)
            if category in used
        ],
    }


def _listed(revision: str) -> JsonObject:
    """Return a marked revision as the list written by hand names it."""
    [found] = [each for each in fixture("revisions")["items"] if each["revision_id"] == revision]
    return cast("JsonObject", found)


def revisions(categories: Iterable[JsonValue]) -> dict[str, JsonObject]:
    """Return the reference and the offer as getRevision reads them, with their snapshot."""
    known = list(categories)
    reference, offer = _listed(mockhistory.REFERENCE), _listed(mockhistory.OFFER)
    return {
        "revision_marked": {
            **reference,
            "snapshot": {
                "employed_reference": employed_reference(
                    mockhistory.reference_rows(),
                    LABOUR_RATES,
                    cast("int", reference["reference_year"]),
                    known,
                )
            },
        },
        "revision_offer": {
            **offer,
            "snapshot": {
                "employed_reference": employed_reference(
                    mockhistory.offer_rows(),
                    mockhistory.offer_rates(),
                    cast("int", offer["reference_year"]),
                    known,
                )
            },
        },
    }


def _said(revision: JsonObject) -> str:
    """Say what a snapshot conserves: its roles, its calendars, its categories, its rates."""
    snapshot = cast("JsonObject", cast("JsonObject", revision["snapshot"])["employed_reference"])
    rates = cast("list[JsonObject]", snapshot["hourly_rates"])
    return (
        f"son instantané conserve les {len(cast('list[JsonValue]', snapshot['resource_roles']))} "
        f"rôles de ses lignes de main-d'œuvre, "
        f"{len(cast('list[JsonValue]', snapshot['calendars']))} calendriers — les leurs et "
        f"celui par défaut —, les {len(cast('list[JsonValue]', snapshot['cost_categories']))} "
        f"catégories de ses lignes et les taux horaires de {rates[0]['year']} de ses "
        f"{len(rates)} catégories de main-d'œuvre, "
        + mocktext.listed([mocktext.amount(Decimal(str(rate["amount"]))) for rate in rates])
        + " (WF-REV-0030)"
    )


def examples(found: Mapping[str, JsonObject]) -> dict[str, JsonObject]:
    """Return the reference and the offer read by getRevision (``revisions``), by file name."""
    marked, offer = found["revision_marked"], found["revision_offer"]
    return {
        "revision_marked.json": mocktext.example(
            "La révision de référence du projet, marquée : aucune de ses commandes de "
            f"modification n'est disponible ; {_said(marked)}.",
            marked,
        ),
        "revision_offer.json": mocktext.example(
            "L'offre v1.0 du projet, marquée le 15 décembre 2025 pendant le chiffrage, avant "
            "l'état En cours : son marquage n'a conservé que le total du devis (WF-REV-0020, "
            "WF-DAT-0040) ; créée en 2025, elle porte l'année de référence 2025 (WF-REV-0060) ; "
            f"{_said(offer)}.",
            offer,
        ),
    }
