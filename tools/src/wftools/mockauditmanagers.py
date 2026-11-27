# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The project managers in the journal of audit: registered, removed, changed (US-2980, #4127).

``setContributors`` inscribes, for each line of the list it writes, the registration of a project
manager (``project_manager_add``), the removal of one (``project_manager_remove``), and the change
of capacity of a contributor to or from project manager (``project_manager_change``); a participant
registered or removed is no inscription (WF-SEC-0030, WF-PRJ-0060). The object is the contributor,
by the identifier and the name of its account; the project, the witness.

Three readings of the journal of the witness, each headed by the inscriptions of the writes of
today: the list Camille Martin writes today (``contributors_set``), Inès Roux made project manager;
the rescue of the project, a variant, whose account of Camille Martin is deactivated
(``contributors_without_active_manager``), Dominique Bernard, no contributor, registering Sacha
Lefèvre as project manager — a liberty, the rescue of the contract promoting Inès Roux
(``contributors_set_by_rescuer``) —; and the list Camille Martin writes after the one of today, a
variant that removes Inès Roux. Each inscription read from two lists is what the service inscribes
for them (``changes``). Numbered apart from the journal and from every other example. Nothing here
reads the clock.
"""

from typing import TYPE_CHECKING, cast

from wftools import mockproject, mocktext
from wftools.mockaudit import Inscription, display_name, journal, numbered, page
from wftools.mockwitness import TODAY, fixture

if TYPE_CHECKING:
    from datetime import datetime

    from wftools.mockstructure import JsonObject

CHANGED = 131
"""The number of the inscription of the list written today, and of its request: past those of the
variants of the administration and of the restore (``mockauditadmin``)."""

ADDED = 132
"""The number of the inscription of the rescue, and of its request."""

REMOVED = 133
"""The number of the inscription of the removal of Inès Roux, and of its request."""

MANAGER = "project_manager"

RESCUED = "Sacha Lefèvre"
"""The account the rescue registers as project manager: active, proposed by the workshop of the
wiring (``contributor_suggestions``), and no contributor of the witness before."""

WITHDRAWN = "Inès Roux"
"""The project manager the variant removes, made one by the list written today."""

REMOVED_AT = TODAY
"""The instant of the removal: today, as the list it follows, inscribed after it."""


def changes(before: list[JsonObject], after: list[JsonObject]) -> list[tuple[str, str]]:
    """Return what a list written inscribes, as the service does: an action and an account each.

    In the order of the list written, then the lines it removes by their account: a
    line new as project manager, ``project_manager_add``; a line kept whose capacity changes,
    ``project_manager_change``; a project manager removed, ``project_manager_remove``.
    """
    held = {cast("str", line["user_id"]): line["kind"] for line in before}
    kept = {cast("str", line["user_id"]) for line in after}
    found: list[tuple[str, str]] = []
    for line in after:
        user = cast("str", line["user_id"])
        if user not in held:
            if line["kind"] == MANAGER:
                found.append(("project_manager_add", user))
        elif held[user] != line["kind"]:
            found.append(("project_manager_change", user))
    found.extend(
        ("project_manager_remove", user)
        for user, kind in sorted(held.items())
        if user not in kept and kind == MANAGER
    )
    return found


def _rescuer() -> JsonObject:
    """Return the rescuer of the witness as an actor names it (``mockproject.RESCUER``)."""
    [user] = [each for each in fixture("users")["items"] if each["user_id"] == mockproject.RESCUER]
    return {"kind": "user", "user_id": user["user_id"], "display_name": display_name(user)}


def _inscribed(
    before: list[JsonObject], after: list[JsonObject], actor: JsonObject, at: datetime
) -> Inscription:
    """Return the one inscription a list written makes, on the witness, by its author."""
    users = {each["user_id"]: each for each in fixture("users")["items"]}
    [(action, user)] = changes(before, after)
    return Inscription(
        at, actor, action, "contributor", user, display_name(users[user]), on_witness=True
    )


def _rescued_read() -> list[JsonObject]:
    """Return the list the rescue reads, which the same command writes: read in memory."""
    return cast("list[JsonObject]", mockproject.without_active_manager()["items"])


def _items(name: str) -> list[JsonObject]:
    return cast("list[JsonObject]", fixture(name)["items"])


def _written_today() -> Inscription:
    """Return the change the list written today makes, by Camille Martin (``contributors_set``)."""
    witness = cast("JsonObject", fixture("project")["audit"]["created_by"])
    return _inscribed(_items("contributors"), _items("contributors_set"), witness, TODAY)


def _rescue() -> list[JsonObject]:
    """Return the list the rescue writes: the list read, ``RESCUED`` added project manager."""
    [rescued] = [each for each in fixture("users")["items"] if display_name(each) == RESCUED]
    line: JsonObject = {
        "user_id": rescued["user_id"],
        "display_name": RESCUED,
        "kind": MANAGER,
        "is_active": True,
    }
    return [*_rescued_read(), line]


def _removed() -> list[JsonObject]:
    """Return the list written after the one of today: ``WITHDRAWN`` removed, the rest kept."""
    return [each for each in _items("contributors_set") if each["display_name"] != WITHDRAWN]


def _of_witness(head: list[JsonObject]) -> JsonObject:
    """Return the journal of the witness, the inscriptions of the variant at its head."""
    witness = [event for event in journal() if event["project"] is not None]
    return page([*head, *witness])


def examples() -> dict[str, JsonObject]:
    """Return the three readings of the journal of the witness, by file name."""
    changed = numbered(CHANGED, CHANGED, _written_today())
    added = numbered(
        ADDED,
        ADDED,
        _inscribed(
            _rescued_read(),
            _rescue(),
            _rescuer(),
            TODAY,
        ),
    )
    removed = numbered(
        REMOVED,
        REMOVED,
        _inscribed(_items("contributors_set"), _removed(), _written_today().actor, REMOVED_AT),
    )
    return {
        "audit_events_manager_changed.json": mocktext.example(
            "Le journal d'audit du projet témoin (project_id) juste après la liste des "
            "contributeurs que Camille Martin enregistre aujourd'hui à 14 h 05 "
            "(contributors_set) : en tête, le changement de qualité d'Inès Roux, passée cheffe "
            "de projet, l'objet étant la contributrice, par son compte et son nom ; Sacha "
            "Lefèvre, inscrit participant par la même liste, n'est pas inscrit au journal, qui "
            "ne garde que les chefs de projet ; puis les inscriptions d'avant elle (WF-SEC-0030, "
            "WF-PRJ-0060).",
            _of_witness([changed]),
        ),
        "audit_events_manager_added.json": mocktext.example(
            "Variante contrefactuelle : le journal d'audit du projet témoin (project_id) juste "
            "après son sauvetage, le compte de Camille Martin, seule cheffe de projet, désactivé "
            "(contributors_without_active_manager). Dominique Bernard, qui n'en est pas "
            f"contributeur, y inscrit {RESCUED} chef de projet aujourd'hui à 14 h 05, la liste "
            "lue gardée telle quelle — une liberté de cette variante : le sauvetage du contrat "
            "fait d'Inès Roux la cheffe de projet (contributors_set_by_rescuer). L'inscription "
            "du chef de projet en tête, puis celles d'avant elle (WF-SEC-0030, WF-PRJ-0060).",
            _of_witness([added]),
        ),
        "audit_events_manager_removed.json": mocktext.example(
            "Variante contrefactuelle : le journal d'audit du projet témoin (project_id) après "
            "deux listes des contributeurs enregistrées aujourd'hui par Camille Martin : celle "
            "qui fait d'Inès Roux une cheffe de projet (contributors_set), puis celle qui la "
            "retire de la liste, à 14 h 05 toutes deux. Le retrait "
            "de la cheffe de projet en tête, puis le changement de qualité qui l'a faite "
            "cheffe de projet, puis les inscriptions d'avant elles (WF-SEC-0030, WF-PRJ-0060).",
            _of_witness([removed, changed]),
        ),
    }
