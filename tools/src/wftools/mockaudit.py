# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit of the universe, engendered from its chronology (EP-02/L42, #516).

Each inscription is an action WF-SEC-0030 names that the universe has already done: read from the
chronology of the witness (``mockwitness``) — the offer marked, then designated reference, the
amendment 1 merged, the occurrence of 752, the imports of actual costs applied, the reception of
the customer excluded from the tracked scope — and from the examples written by hand that say when
each account, each access role and each backup came to be (``users``, ``access_roles``,
``backups``). Nothing is invented that another example does not say. An actor is read from an
audit only where that audit was last updated by the action inscribed — the marking of the offer,
the merge for the reference, the occurrence of 752 —; the designation of the offer and the
exclusion of the reception of the customer, which an audit updated since does not date, are the
gestures of the witness's actor, the project's creator, as the chronology of the witness has
them; an import is by the actor its journal names; what the platform does by itself is by the
platform. A label is the one the object bears in its example, and an object that lives in a
revision names it — the risk that occurred, the amendment merged; the lines of cost and the imports
of actual costs live in the project. And the immediate sequel of the exit of the witness from its
lifecycle, confirmed today (``project_completed``).

What the same command writes — the risks of ``mockhistory``, the journal of the imports of
``mockcosts`` — is read in memory, never from its file, so that one run reaches its fixed point;
only examples written by hand are read from the disk. The answers of ``listAuditEvents`` are
written from the one journal: the whole of it, the latest first; its second page of ten; the
journal of the witness; that journal after its exit, and after the estimate imported this morning
is applied; a filter that retains nothing; the journal
sorted by author; the inscriptions of one correlation; and a search on the label of the object.
The answer of ``listAuditFacets`` is read from the same journal: its authors and its projects
(#550). Nothing here reads the clock.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from wftools import mockcosts, mockhistory, mocktext
from wftools.mockhistory import stamp
from wftools.mockids import AUDIT_EVENTS, CORRELATIONS, hex_identifier, identifier, universe
from wftools.mocktext import PAGE
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    COSTS,
    JOURNAL,
    OCCURRED,
    ORDER_RECEIVED,
    REGISTER,
    TODAY,
    fixture,
)

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

SECOND_PAGE = 10
"""The size of the page of the example that reads the journal page by page."""

PLATFORM: JsonObject = {"kind": "platform"}
"""The actor of what the platform does by itself: a scheduled backup, an account it creates."""


@dataclass(frozen=True, slots=True)
class Inscription:
    """An action of the journal, before it is numbered: when, by whom, what, on what, where.

    ``joined`` says that the inscription was produced by the same request as the one before it,
    under its correlation: the marking and the designation a merge of an amendment produces.
    ``revision`` is the revision the object lives in, by its identifier and its version name.
    """

    at: datetime
    actor: JsonObject
    action: str
    kind: str
    object_id: str
    label: str | None
    on_witness: bool = False
    joined: bool = False
    revision: tuple[str, str | None] | None = None


def display_name(user: JsonObject) -> str:
    """Return the name an account displays: its first name, then its last name."""
    return f"{user['first_name']} {user['last_name']}"


def _witness_actor() -> JsonObject:
    """Return the actor of the gestures on the witness: the creator of the project."""
    return cast("JsonObject", fixture("project")["audit"]["created_by"])


def _instant(text: str) -> datetime:
    """Return an instant as the examples write it, in universal time."""
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _revisions() -> list[Inscription]:
    """Return the markings and the designations of the reference, from the revisions.

    The offer, marked, then designated reference with the order; the reference in force, marked
    and designated by the merge of the amendment 1, which the merge inscribes first, on the
    structure of the amendment, the three at one instant and under one correlation (WF-REV-0050).
    The marking and the merge by the one who last changed the revision, as its audit says, last
    changed by them; the designation of the offer, which its audit does not date, by the actor of
    the witness.
    """
    revisions = {each["revision_id"]: each for each in fixture("revisions")["items"]}
    offer, reference = revisions[universe(100)], revisions[universe(101)]
    [amendment] = [
        each
        for each in fixture("structures_amendments")
        if each["kind"] == "amendment" and each["is_merged"]
    ]

    def on(revision: JsonObject, action: str, at: datetime, *, joined: bool) -> Inscription:
        audit = cast("JsonObject", revision["audit"])
        return Inscription(
            at,
            cast("JsonObject", audit["updated_by"]),
            action,
            "revision",
            cast("str", revision["revision_id"]),
            cast("str", revision["version_name"]),
            joined=joined,
        )

    merged = AMENDMENT_MERGED.instant
    lived = revisions[amendment["revision_id"]]
    return [
        on(offer, "revision_mark", _instant(offer["marked_at"]), joined=False),
        Inscription(
            ORDER_RECEIVED.instant,
            _witness_actor(),
            "reference_designate",
            "revision",
            offer["revision_id"],
            offer["version_name"],
        ),
        Inscription(
            merged,
            reference["audit"]["updated_by"],
            "amendment_merge",
            "cost_structure",
            amendment["structure_id"],
            amendment["label"],
            revision=(lived["revision_id"], lived["version_name"]),
        ),
        on(reference, "revision_mark", merged, joined=True),
        on(reference, "reference_designate", merged, joined=True),
    ]


def _witness() -> list[Inscription]:
    """Return the actions on the witness: its markings, its reference, its amendment, its risk.

    Then the imports of actual costs applied, each by the import of the exchanges that applied it,
    under the name of its file and by the actor its journal names; and the lines excluded from
    the tracked scope, by the actor of the witness. The occurrence by the one the audit of the
    risk names, last updated by it, in the current revision, where it merges its own estimate
    (WF-RIS-0060); the imports of actual costs and the lines of cost live in the project, in no
    revision (WF-INTF-0090, WF-CRE-0010). The register and the journal of the imports are those
    the same command writes, read in memory.
    """
    register = mockhistory.readings()["risks"]
    risks = {
        cast("str", each["risk_id"]): each for each in cast("list[JsonObject]", register["items"])
    }
    imports = {each["import_id"]: each for each in fixture("imports")["items"]}
    journal = {
        cast("str", each["cost_import_id"]): each
        for each in cast("list[JsonObject]", mockcosts.journal()["items"])
    }
    current = _current_revision()
    found = _revisions()
    found.extend(
        Inscription(
            risk.last.at,
            cast(
                "JsonObject",
                cast("JsonObject", risks[universe(risk.number)]["audit"])["updated_by"],
            ),
            "risk_occurrence",
            "risk",
            universe(risk.number),
            risk.label,
            revision=current,
        )
        for risk in REGISTER
        if risk.last.state == OCCURRED
    )
    for applied in JOURNAL:
        exchange = imports[hex_identifier(applied.exchange)]
        found.append(
            Inscription(
                applied.event.instant,
                cast("JsonObject", journal[hex_identifier(applied.number)]["actor"]),
                "import_apply",
                "import",
                exchange["import_id"],
                exchange["filename"],
            )
        )
    found.extend(
        Inscription(
            line.excluded[0],
            _witness_actor(),
            "cost_line_exclude",
            "cost_line",
            hex_identifier(line.number),
            line.document,
        )
        for line in COSTS
        if line.excluded is not None
    )
    return [replace(each, on_witness=True) for each in found]


def _current_revision() -> tuple[str, str | None]:
    """Return the revision in progress of the witness, the one an occurrence merges into.

    By its identifier and its version name, which a revision in progress does not have yet.
    """
    current = fixture("project")["current_revision_id"]
    [revision] = [each for each in fixture("revisions")["items"] if each["revision_id"] == current]
    return cast("str", revision["revision_id"]), cast("str | None", revision["version_name"])


def _accounts() -> list[Inscription]:
    """Return the access roles created, the accounts created, those deactivated since.

    Each when and by whom its audit says: what the platform created — at the installation, from
    the directory, at a first sign-in by the provider of identity — by the platform. The roles
    come first, before the accounts that hold them. An account inactive was deactivated at its
    last update (WF-ADM-0060). And the roles given to an account after its creation: those
    created after it (``_given``). An update of an account by its holder alone — the preferences
    of its display, which ``updateMyPreferences`` writes — is no inscription: WF-SEC-0030 names
    the accounts an administrator creates and modifies, not what a user chooses for himself.
    """
    found = [
        Inscription(
            _instant(role["audit"]["created_at"]),
            role["audit"]["created_by"],
            "access_role_create",
            "access_role",
            role["access_role_id"],
            role["label"],
        )
        for role in fixture("access_roles")
    ]
    for user in fixture("users")["items"]:
        name = display_name(user)
        audit = user["audit"]
        found.append(
            Inscription(
                _instant(audit["created_at"]),
                audit["created_by"],
                "user_create",
                "user",
                user["user_id"],
                name,
            )
        )
        if not user["is_active"]:
            found.append(
                Inscription(
                    _instant(audit["updated_at"]),
                    audit["updated_by"],
                    "user_deactivate",
                    "user",
                    user["user_id"],
                    name,
                )
            )
    return [*found, *_given()]


def _given() -> list[Inscription]:
    """Return the roles given to an account that held them only once they were created.

    An account created before one of its roles was given its roles once the last of them came
    to be — at the earliest, which is when the examples let it be — by the one who created that
    role: the first administrator composing the roles of the installation and taking one.
    """
    roles = {role["access_role_id"]: role for role in fixture("access_roles")}
    found: list[Inscription] = []
    for user in fixture("users")["items"]:
        held = [roles[role]["audit"] for role in user["access_role_ids"]]
        last = max(held, key=lambda audit: audit["created_at"], default=None)
        if last is not None and last["created_at"] > user["audit"]["created_at"]:
            found.append(
                Inscription(
                    _instant(last["created_at"]),
                    last["created_by"],
                    "user_access_roles_set",
                    "user",
                    user["user_id"],
                    display_name(user),
                )
            )
    return found


def _backuper() -> JsonObject:
    """Return the one active account that may start a backup: its author (WF-ADM-0100)."""
    roles = {
        role["access_role_id"]
        for role in fixture("access_roles")
        if "backups.write" in role["permissions"]
    }
    [user] = [
        each
        for each in fixture("users")["items"]
        if each["is_active"] and roles & set(each["access_role_ids"])
    ]
    return {
        "kind": "user",
        "user_id": user["user_id"],
        "display_name": display_name(user),
    }


def _backups() -> list[Inscription]:
    """Return the backups of the list, each at its date: the scheduled ones by the platform."""
    backuper = _backuper()
    return [
        Inscription(
            _instant(backup["taken_at"]),
            PLATFORM if backup["origin"] == "scheduled" else backuper,
            "backup",
            "backup",
            backup["backup_id"],
            None,
        )
        for backup in fixture("backups")["items"]
    ]


def inscriptions() -> list[Inscription]:
    """Return the actions of the universe up to today, in the order they were inscribed.

    By their instant; those of one instant — the installation creating its accounts and its
    roles — in the order of the examples that say them.
    """
    found = [*_accounts(), *_witness(), *_backups()]
    return sorted(found, key=lambda each: each.at)


def exit_today() -> Inscription:
    """Return the exit of the witness from its lifecycle, confirmed today (`project_completed`)."""
    project = fixture("project_completed")
    return Inscription(
        _instant(project["audit"]["updated_at"]),
        project["audit"]["updated_by"],
        "project_exit",
        "project",
        project["project_id"],
        project["label"],
        on_witness=True,
    )


def _event(number: int, request: int, inscription: Inscription) -> JsonObject:
    """Return an inscription as the journal reads it (`AuditEvent`), numbered in its order.

    Its correlation is that of the request that produced it, numbered in the order of the
    requests: the inscriptions of one request share it.
    """
    project = fixture("project")
    return {
        "audit_event_id": identifier(AUDIT_EVENTS, number),
        "occurred_at": stamp(inscription.at),
        "actor": inscription.actor,
        "action": inscription.action,
        "object": {
            "kind": inscription.kind,
            "object_id": inscription.object_id,
            "label": inscription.label,
            "revision": (
                None
                if inscription.revision is None
                else {"revision_id": inscription.revision[0], "label": inscription.revision[1]}
            ),
        },
        "project": (
            {
                "project_id": project["project_id"],
                "code": project["code"],
                "label": project["label"],
            }
            if inscription.on_witness
            else None
        ),
        "correlation_id": identifier(CORRELATIONS, request),
    }


def import_applied_today() -> Inscription:
    """Return the application of the estimate imported this morning, which succeeds today.

    The import of the estimate of the « Poste de commande », analysed this morning
    (`import_analysed`), confirmed today and applied by its task, which succeeds at 14 h 08 min 30 s
    (`task_import_succeeded`): the instant of the inscription is the one the task succeeded at. By
    the account of the witness, which confirmed it; in the revision in progress, where an import
    of an estimate applies (WF-INTF-0090).
    """
    imported = fixture("import_analysed")
    task = fixture("task_import_succeeded")
    user = fixture("me")
    return Inscription(
        _instant(task["finished_at"]),
        {"kind": "user", "user_id": user["user_id"], "display_name": display_name(user)},
        "import_apply",
        "import",
        imported["import_id"],
        imported["filename"],
        on_witness=True,
        revision=_current_revision(),
    )


def _sequels() -> tuple[Inscription, ...]:
    """Return the actions that take effect just after today, each the sequel of a write of today.

    Each is read alone, a variant of the journal: the exit of the witness and the application of
    the estimate do not follow one another — a project completed takes no import (WF-CYC-0100).
    """
    return exit_today(), import_applied_today()


EXIT, IMPORT = range(2)
"""The sequels by their rank in ``_sequels``, which numbers them apart from one another."""


def journal(*, sequel: int | None = None) -> list[JsonObject]:
    """Return the journal, numbered in the order of inscription, the latest first.

    Two inscriptions of one instant come in the order they were inscribed, reversed. A sequel —
    an action that takes effect just after today, by its rank — is inscribed last, by a request of
    its own; its number and its request's follow those of the sequels before it, so that two
    variants never give one identifier to two inscriptions.
    """
    found = inscriptions()
    events: list[JsonObject] = []
    request = 0
    for number, each in enumerate(found, start=1):
        request += 0 if each.joined else 1
        events.append(_event(number, request, each))
    if sequel is not None:
        events.append(_event(len(found) + 1 + sequel, request + 1 + sequel, _sequels()[sequel]))
    return events[::-1]


def _page(events: list[JsonObject], limit: int = PAGE, offset: int = 0) -> JsonObject:
    """Return a page of the answer of listAuditEvents."""
    return {
        "items": cast("list[JsonValue]", events[offset : offset + limit]),
        "meta": {"limit": limit, "offset": offset, "total": len(events)},
    }


def _of_witness(events: list[JsonObject]) -> list[JsonObject]:
    return [event for event in events if event["project"] is not None]


def _text(event: JsonObject, column: str) -> str | None:
    """Return the text an inscription shows in a column the journal sorts as text, or none."""
    if column == "actor":
        return cast("str | None", cast("JsonObject", event["actor"]).get("display_name"))
    if column == "object_label":
        return cast("str | None", cast("JsonObject", event["object"])["label"])
    if column == "project":
        project = cast("JsonObject | None", event["project"])
        return None if project is None else cast("str", project["code"])
    return cast("str", event[column])


TEXT_COLUMNS = ("actor", "object_label", "project", "correlation_id")
"""The columns of the journal sorted as text (`sort_by`): the author by the name it displays, the
label of the object, the project by its code, the correlation."""


def sorted_by(
    events: list[JsonObject], column: str, *, descending: bool = False
) -> list[JsonObject]:
    """Return the journal sorted by a text column, as listAuditEvents sorts it (`sort_by`, #550).

    Compared by code point, whatever the language of the reader; an inscription without a value —
    the platform, which displays no name, a backup, which has no label, an inscription without a
    project — after the others in the ascending order, before them in the descending one. Two
    inscriptions of one value keep the order of the journal without sort, whichever the
    direction: the sort is stable.
    """
    if column not in TEXT_COLUMNS:
        message = f"{column} is no text column of the journal"
        raise ValueError(message)
    valued = sorted(
        (each for each in events if _text(each, column) is not None),
        key=lambda each: cast("str", _text(each, column)),
        reverse=descending,
    )
    empty = [each for each in events if _text(each, column) is None]
    return [*empty, *valued] if descending else [*valued, *empty]


def facets(events: list[JsonObject]) -> JsonObject:
    """Return the authors and the projects the journal names (`listAuditFacets`, #550).

    Each account that wrote an inscription once, under the name its latest inscription displays —
    the one it displays today, which no account of the universe has changed since —, by that name
    compared by code point, then by its identifier; each project of an inscription once, under the
    code and the label of its latest inscription, by its code, then by its identifier. The
    journal reads the latest first. The platform is no author here: `actor_kind` keeps it.
    """
    actors: dict[str, JsonObject] = {}
    projects: dict[str, JsonObject] = {}
    for event in events:
        actor = cast("JsonObject", event["actor"])
        if actor["kind"] == "user":
            author = cast("str", actor["user_id"])
            actors.setdefault(author, {"user_id": author, "display_name": actor["display_name"]})
        project = cast("JsonObject | None", event["project"])
        if project is not None:
            projects.setdefault(cast("str", project["project_id"]), dict(project))
    return {
        "actors": cast(
            "list[JsonValue]",
            sorted(actors.values(), key=lambda each: (each["display_name"], each["user_id"])),
        ),
        "projects": cast(
            "list[JsonValue]",
            sorted(projects.values(), key=lambda each: (each["code"], each["project_id"])),
        ),
    }


SEARCHED = "Coûts-Réels-2026-05"
"""The text of the example that searches the labels of the objects: two files of actual costs,
written in another case than theirs and without its accents, which a search does not tell apart."""


def searched(events: list[JsonObject], text: str) -> list[JsonObject]:
    """Return the inscriptions whose object's label holds the text (`search`).

    Whatever the case and the accents of either, as every search (`mocktext.holds`).

    A backup, which has no label, is retained by no search.
    """
    return [
        event
        for event in events
        if (label := cast("str | None", cast("JsonObject", event["object"])["label"])) is not None
        and mocktext.holds(label, text)
    ]


def _merged(events: list[JsonObject]) -> list[JsonObject]:
    """Return the inscriptions of the request that merged the amendment 1, of one correlation."""
    [merge] = [event for event in events if event["action"] == "amendment_merge"]
    return [event for event in events if event["correlation_id"] == merge["correlation_id"]]


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the journal of audit, by file name."""
    events = journal()
    witness = _of_witness(events)
    exited = _of_witness(journal(sequel=EXIT))
    imported = _of_witness(journal(sequel=IMPORT))
    day = mocktext.day(TODAY.date())
    counted = mocktext.count(len(events))
    return {
        "audit_events.json": mocktext.example(
            f"Le journal d'audit de l'installation le {day}, les inscriptions les plus récentes "
            f"d'abord, {counted} en tout : les sauvegardes planifiées, par la plateforme, et "
            f"celle que {_backuper()['display_name']} a lancée, les imports de coûts réels "
            f"appliqués, l'exclusion d'une ligne de coût, la survenance du risque 752, la fusion "
            f"de l'avenant 1, qui marque la révision de référence et la désigne, la désignation de "
            f"l'offre comme référence et son marquage, les "
            f"comptes créés ou désactivés, les rôles d'habilitation créés, ceux de "
            f"l'installation par la plateforme, et les rôles que le premier administrateur "
            f"s'est attribués. Chaque inscription a sa date, son auteur, son action, l'objet "
            f"sous le libellé qu'il portait et le projet s'il y en a un (WF-SEC-0030).",
            _page(events),
        ),
        "audit_events_page.json": mocktext.example(
            f"La deuxième page du journal d'audit du {day}, lu {SECOND_PAGE} par "
            f"{SECOND_PAGE} : les inscriptions {SECOND_PAGE + 1} à {2 * SECOND_PAGE} sur "
            f"{counted} (WF-SEC-0030).",
            _page(events, SECOND_PAGE, SECOND_PAGE),
        ),
        "audit_events_project.json": mocktext.example(
            f"Le journal d'audit du projet témoin le {day} (project_id), les inscriptions les "
            f"plus récentes d'abord : les imports de coûts réels appliqués, l'exclusion de la "
            f"réception du client du périmètre suivi, la survenance du retard de livraison des "
            f"armoires, la fusion de l'avenant 1 avec le marquage et la désignation de la "
            f"révision de référence qu'elle produit, sous une seule corrélation, la désignation "
            f"de l'offre comme référence et son marquage (WF-SEC-0030).",
            _page(witness),
        ),
        "audit_events_exited.json": mocktext.example(
            f"Le journal d'audit du projet témoin juste après sa sortie du cycle de vie, "
            f"confirmée le {day} à 14 h 05 (project_completed) : la sortie en tête, puis les "
            f"mêmes inscriptions qu'avant elle. Le journal d'un projet terminé se lit par le "
            f"même filtre, aussi longtemps que les projets sont conservés (WF-SEC-0030).",
            _page(exited),
        ),
        "audit_events_import_applied.json": mocktext.example(
            f"Le journal d'audit du projet témoin juste après l'application de l'import du devis "
            f"du Poste de commande (import_analysed), confirmée le {day} et aboutie à 14 h 08 min "
            f"30 s (task_import_succeeded) : l'application en tête, par Camille Martin, avec la "
            f"révision en cours où elle s'écrit, qui n'a pas encore de nom de version "
            f"(WF-INTF-0090) ; puis les mêmes inscriptions qu'avant elle (WF-SEC-0030).",
            _page(imported),
        ),
        "audit_events_empty.json": mocktext.example(
            f"Les restaurations du journal d'audit le {day} (actions=restore) : la plateforme "
            f"n'a jamais été restaurée, et la liste est vide (WF-SEC-0030).",
            _page([event for event in events if event["action"] == "restore"]),
        ),
        **_readings(events, day),
    }


def _readings(events: list[JsonObject], day: str) -> dict[str, JsonObject]:
    """Return the readings of the journal that sort it, filter it, and name its facets (#550)."""
    by_actor_events = sorted_by(events, "actor")
    by_label = sorted_by(events, "object_label")
    merged = _merged(events)
    found = facets(events)
    authors = ", ".join(
        cast("str", cast("JsonObject", each)["display_name"])
        for each in cast("list[JsonValue]", found["actors"])
    )
    return {
        "audit_events_by_actor.json": mocktext.example(
            f"Le journal d'audit du {day} trié par auteur, croissant (sort_by=actor) : les "
            f"comptes par leur nom affiché, comparé caractère par caractère dans l'ordre des "
            f"points de code Unicode — ici {authors} —, puis la plateforme, qui n'a pas de nom, "
            f"après eux ; les inscriptions d'un même auteur dans l'ordre du journal sans tri, les "
            f"plus récentes d'abord (WF-SEC-0030, WF-IHM-0060).",
            _page(by_actor_events),
        ),
        "audit_events_by_object_label.json": mocktext.example(
            f"Le journal d'audit du {day} trié par libellé de l'objet, croissant "
            f"(sort_by=object_label) : les libellés comparés caractère par caractère dans "
            f"l'ordre des points de code Unicode — les majuscules avant les minuscules, "
            f"« Référence » après « Retard de livraison des armoires », « é » (U+00E9) venant "
            f"après « e » (U+0065) et toute lettre non accentuée —, puis les sauvegardes, qui "
            f"n'en ont pas, dans l'ordre du journal sans tri (WF-SEC-0030, WF-IHM-0060).",
            _page(by_label),
        ),
        "audit_events_correlation.json": mocktext.example(
            f"Les inscriptions de la requête qui a fusionné l'avenant 1 (correlation_id) : la "
            f"fusion, le marquage de la révision « Référence » et sa désignation comme référence, "
            f"{mocktext.count(len(merged))} inscriptions d'un même instant ; la fusion nomme la "
            f"révision où vit le différentiel, « Référence » (WF-SEC-0030, WF-OBS-0020, "
            f"WF-IHM-0130).",
            _page(merged),
        ),
        "audit_events_search.json": mocktext.example(
            f"Les inscriptions dont l'objet porte « {SEARCHED} » dans son libellé (search) : "
            f"l'application des imports de coûts réels de mai, retenus quels que soient la casse "
            f"et les accents, "
            f"et qui ne vivent dans aucune révision (WF-SEC-0030, WF-IHM-0130, WF-INTF-0090, "
            f"WF-CRE-0010).",
            _page(searched(events, SEARCHED)),
        ),
        "audit_facets.json": mocktext.example(
            f"Les auteurs et les projets du journal d'audit du {day} (listAuditFacets) : les "
            f"comptes auteurs d'au moins une inscription, par nom affiché, désactivés compris ; "
            f"ici la seule autrice, {authors}. Et le projet témoin, seul projet du journal. "
            f"Lisibles sous la seule permission de consulter le journal (WF-SEC-0030, "
            f"WF-ADM-0100, WF-IHM-0130).",
            found,
        ),
    }
