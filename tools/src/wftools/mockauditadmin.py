# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Two variants of the journal of audit, each a reading of its own (#961, WF-ADM-0160).

The administration of the accounts and the roles of today, each write a request of its own: the
roles created, modified and deleted, the accounts created, given their roles, modified,
reactivated, and the link that sets a password (``administration``). And the journal of today in
an installation that, this morning, created a project, reinstated a line of actual cost in the
tracked scope, then restored the backup of 2 June (``restored``): the restore heads it, dated at
its end, and the project created after the backup no longer exists, its inscription naming it
without leading to it (WF-ADM-0190). Both are numbered apart from the journal and from every
other example. Nothing here reads the clock.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from wftools import mocktext
from wftools.mockaudit import (
    PLATFORM,
    Inscription,
    display_name,
    journal,
    numbered,
    page,
    role_named,
)
from wftools.mockhistory import stamp
from wftools.mockids import hex_identifier, universe
from wftools.mockwitness import TODAY, fixture
from wftools.mockwitnesscosts import COSTS

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

ADMINISTERED = 101
"""The number of the first inscription of the administration of today, and of its first request.

Past the journal, its sequels and the variants of the journal written by hand
(``audit_events_anonymized_*``): the administration is a variant of its own, whose identifiers and
correlations no other example gives (#961)."""

RESTORED = 121
"""The number of the first inscription of the variant of the restore, and of its first request:
past those of the administration."""

ACCOUNT_FIELDS = ("last_name", "first_name", "email", "org_node_id")
"""The fields of an account a modification names, in the order of the account (`AuditUserField`):
its identity, and its attachment to a node of the organisation (#1739)."""

ATTACHED_NODE = "Bureau d'études électricité"
"""The node of the organisation the administration attaches the account of Léa Garnier to, once she
holds her first role: a modification of her attachment alone no example of updateUser answers, a
liberty of that variant (#1739)."""

WITHDRAWN = ("cost_settings.write", "resource_settings.write")
"""The permissions the modification of the administration withdraws from « Manager », in the order
of the catalogue: those of the writing of the settings of costs and resources, which it holds."""


DIRECTORY_LAST_NAME = "Vidal-Roux"
"""The last name the directory gives the person whose address Noé Vidal holds, which the
attachment of the administration gives his account: a liberty of that variant (#707, #961)."""


def _updater(example: JsonObject) -> JsonObject:
    """Return the one who last updated an example, the author of the write it answers."""
    return cast("JsonObject", cast("JsonObject", example["audit"])["updated_by"])


def _account(user: JsonObject, action: str, actor: JsonObject, params: JsonObject) -> Inscription:
    """Return an action of today on an account, under the name it displays once it is done."""
    identifier = cast("str", user["user_id"])
    return Inscription(TODAY, actor, action, "user", identifier, display_name(user), params=params)


def _administered_roles() -> list[Inscription]:
    """Return the roles the administration of today creates and modifies.

    « Contrôle de gestion » composed from its label alone, without any permission
    (`access_role_created`), then saved as it is, which changes nothing of it; « Manager » renamed
    « Responsable d'équipe » (`access_role_renamed`) and given the modification of the planning
    (`access_role_updated`) by the same modification, which withdraws from it the writing of the
    settings of costs and resources (``WITHDRAWN``). That combined modification is a variant no
    example of updateAccessRole answers: each of them renames or changes the permissions, never
    both. Its state after is written here, and what it grants and withdraws is read from it as
    the service reads it, in the order of the catalogue. Each by the one who last updated the
    example it is read from.
    """
    created = fixture("access_role_created")
    renamed = fixture("access_role_renamed")
    updated = fixture("access_role_updated")
    roles = {role["access_role_id"]: role for role in fixture("access_roles")}
    before = cast("list[str]", roles[renamed["access_role_id"]]["permissions"])
    after = [code for code in cast("list[str]", updated["permissions"]) if code not in WITHDRAWN]

    def role(action: str, changed: JsonObject, params: JsonObject) -> Inscription:
        return Inscription(
            TODAY,
            _updater(changed),
            action,
            "access_role",
            cast("str", changed["access_role_id"]),
            cast("str", changed["label"]),
            params=params,
        )

    return [
        role("access_role_create", created, {"permissions": created["permissions"]}),
        role(
            "access_role_update",
            created,
            {"permissions_granted": [], "permissions_withdrawn": []},
        ),
        role(
            "access_role_update",
            renamed,
            {
                "previous_label": roles[renamed["access_role_id"]]["label"],
                "permissions_granted": [code for code in after if code not in before],
                "permissions_withdrawn": [code for code in before if code not in after],
            },
        ),
    ]


def _administered_accounts() -> list[Inscription]:
    """Return the accounts the administration of today creates, modifies and takes roles from.

    Léa Garnier created a local account (`user_created`), born without a role (#1731), then
    given her first role, « Chiffreur », by setUserAccessRoles, a request of its own after the
    creation: a first attribution no example of setUserAccessRoles answers, a liberty of this
    variant; then attached to a node of the organisation (``ATTACHED_NODE``), a modification of
    her attachment alone no example of updateUser answers, a liberty of this variant (#1739);
    the name of Lucas Petit corrected (`user_renamed`); Noé Vidal, as the list of the accounts has
    him, attached by the platform to the person of the directory who holds his address, under the
    name the directory gives him (``DIRECTORY_LAST_NAME``), from the directory from now on (#707):
    an attachment no example answers, a liberty of this variant; Inès Roux deprived of her one role
    (`user_access_roles_cleared`). Each write read from an example by the one who last updated it.
    """
    created = fixture("user_created")
    renamed = fixture("user_renamed")
    cleared = fixture("user_access_roles_cleared")
    users = {user["user_id"]: user for user in fixture("users")["items"]}
    roles = {role["access_role_id"]: role for role in fixture("access_roles")}
    [first] = [role for role in roles.values() if role["label"] == "Chiffreur"]
    [noe] = [user for user in users.values() if display_name(user) == "Noé Vidal"]
    [node] = [each for each in fixture("org_nodes") if each["label"] == ATTACHED_NODE]
    attached = {**noe, "last_name": DIRECTORY_LAST_NAME}
    placed = {**created, "org_node_id": node["org_node_id"]}
    actor = _updater(created)

    def changed(after: JsonObject, before: JsonObject | None = None) -> list[JsonValue]:
        earlier = users[after["user_id"]] if before is None else before
        return [name for name in ACCOUNT_FIELDS if after[name] != earlier[name]]

    held = cast("list[str]", users[cleared["user_id"]]["access_role_ids"])
    return [
        _account(created, "user_create", actor, {"origin": created["origin"]}),
        _account(
            created,
            "user_access_roles_set",
            actor,
            {"access_roles_granted": [role_named(first)], "access_roles_withdrawn": []},
        ),
        _account(placed, "user_update", actor, {"fields": changed(placed, created)}),
        _account(
            renamed,
            "user_update",
            _updater(renamed),
            {"fields": changed(renamed)},
        ),
        _account(
            attached, "user_update", PLATFORM, {"fields": changed(attached), "attached": True}
        ),
        _account(
            cleared,
            "user_access_roles_set",
            _updater(cleared),
            {
                "access_roles_granted": [],
                "access_roles_withdrawn": [
                    role_named(roles[role])
                    for role in held
                    if role not in cleared["access_role_ids"]
                ],
            },
        ),
    ]


def _closing() -> list[Inscription]:
    """Return the last writes of the administration of today, after those it reads from examples.

    The link that sets the password of Léa Garnier, which the administration asks to hand it to
    her by another channel (``password_setup_link``, a liberty of this variant: that example is
    Camille Martin's link); Alix Moreau reactivated (``user_reactivated``); and « Contrôle de
    gestion », which nobody holds, deleted (``access_role_created``). The link, the reactivation
    and the deletion say nothing more than their object (`AuditParams`).
    """
    created = fixture("user_created")
    reactivated = fixture("user_reactivated")
    role = fixture("access_role_created")
    actor = _updater(created)
    return [
        _account(created, "password_link_create", actor, {}),
        _account(reactivated, "user_reactivate", _updater(reactivated), {}),
        Inscription(
            TODAY,
            _updater(role),
            "access_role_delete",
            "access_role",
            cast("str", role["access_role_id"]),
            cast("str", role["label"]),
        ),
    ]


def administration() -> list[JsonObject]:
    """Return the administration of the accounts and the roles of today, the latest first.

    A variant of the journal, each write of today on an account or a role a request of its own,
    at the instant of today. Numbered from ``ADMINISTERED``, its requests too.
    """
    events: list[JsonObject] = []
    request = ADMINISTERED - 1
    found = [*_administered_roles(), *_administered_accounts(), *_closing()]
    for number, each in enumerate(found, start=ADMINISTERED):
        request += 0 if each.joined else 1
        events.append(numbered(number, request, each))
    return events[::-1]


RESTORED_BACKUP = universe(906)
"""The backup the variant restores, that of 2 June, verified (``backups``)."""

VANISHED = universe(9)
"""The project the variant creates this morning, after the backup it then restores: no project of
the universe bears its identifier, and after the restore none does."""

VANISHED_LABEL = "Rénovation de l'éclairage de l'atelier"
"""The label of that project, which its inscription keeps; still created, it has no code yet."""

REINSTATED = "FA-2026-0295"
"""The line of actual cost the variant reinstates in the tracked scope: the one the witness
excluded (``cost_line_exclude``)."""

_CREATED_AT = datetime(2026, 6, 3, 9, 15, tzinfo=UTC)
_REINSTATED_AT = datetime(2026, 6, 3, 10, 0, tzinfo=UTC)
_RESTORED_AT = datetime(2026, 6, 3, 11, 40, tzinfo=UTC)
"""The instants of the variant this morning: the project created, the line reinstated, and the
end of the restore, which dates its inscription (`AuditEvent.occurred_at`)."""


def _restored_today() -> list[JsonObject]:
    """Return the inscriptions the variant adds to the journal of today, the latest first.

    The restore by Camille Martin, the one account that may restore the platform, on the backup of
    2 June, dated at its end, the date of the backup in its parameters (WF-ADM-0160); the line
    reinstated on the witness, which exists still; the project created this morning, after the
    backup: it no longer exists, and its inscription names it by its label, without a code it did
    not have yet, and leads to it no more (`can_open` false, WF-ADM-0190).
    """
    project = fixture("project")
    actor = cast("JsonObject", project["audit"]["created_by"])
    [line] = [each for each in COSTS if each.document == REINSTATED]
    backups = {each["backup_id"]: each for each in fixture("backups")["items"]}
    witness: JsonObject = {
        "project_id": project["project_id"],
        "code": project["code"],
        "label": project["label"],
        "can_open": True,
    }
    vanished: JsonObject = {
        "project_id": VANISHED,
        "code": None,
        "label": VANISHED_LABEL,
        "can_open": False,
    }
    found: list[tuple[Inscription, JsonObject | None]] = [
        (
            Inscription(_CREATED_AT, actor, "project_create", "project", VANISHED, VANISHED_LABEL),
            vanished,
        ),
        (
            Inscription(
                _REINSTATED_AT,
                actor,
                "cost_line_reinstate",
                "cost_line",
                hex_identifier(line.number),
                line.document,
            ),
            witness,
        ),
        (
            Inscription(
                _RESTORED_AT,
                actor,
                "restore",
                "backup",
                RESTORED_BACKUP,
                None,
                params={"backup_taken_at": backups[RESTORED_BACKUP]["taken_at"]},
            ),
            None,
        ),
    ]
    events: list[JsonObject] = []
    for number, (each, where) in enumerate(found, start=RESTORED):
        events.append({**numbered(number, number, each), "project": where})
    return events[::-1]


def restored() -> list[JsonObject]:
    """Return the journal of today after the restore of the variant, the latest first.

    What the journal of the universe inscribes today, kept through the restore — the backup of the
    night, the import of actual costs of this morning —, and what the variant adds: read back
    before the databases are replaced and written again after them (WF-ADM-0160).
    """
    today = stamp(datetime.combine(TODAY.date(), datetime.min.time(), tzinfo=UTC))
    kept = [each for each in journal() if cast("str", each["occurred_at"]) >= today]
    return sorted(
        [*_restored_today(), *kept],
        key=lambda each: cast("str", each["occurred_at"]),
        reverse=True,
    )


def examples() -> dict[str, JsonObject]:
    """Return the two variants of the journal, by file name."""
    return {
        "audit_events_administration.json": mocktext.example(
            "Variante : le journal d'audit depuis aujourd'hui à 14 h 05 (from), après "
            "l'administration des comptes et des rôles d'habilitation qui s'y fait, chaque "
            "écriture par une requête à elle, les plus récentes d'abord. Par Camille Martin, "
            "« Contrôle de gestion » créé sans permission, puis enregistré sans rien changer ; "
            "« Manager » renommé « Responsable d'équipe », doté de la modification de la "
            "planification et privé de celle des paramètres de coûts et de ressources par une "
            "même modification, qu'aucun exemple d'updateAccessRole ne répond ; le "
            "compte local de Léa Garnier créé sans rôle, puis doté de son premier rôle, "
            "« Chiffreur », par une attribution à elle : une première attribution qu'aucun "
            "exemple de setUserAccessRoles ne répond, puis rattachée au nœud "
            f"« {ATTACHED_NODE} », une modification du seul rattachement qu'aucun exemple "
            "d'updateUser ne répond ; le nom de Lucas "
            "Petit corrigé ; Inès Roux privée de son seul rôle ; le lien de fixation du mot de "
            "passe de Léa Garnier demandé, pour le lui remettre par un autre canal ; Alix Moreau "
            "réactivée (user_reactivated) ; « Contrôle de gestion », que personne ne porte, "
            "supprimé. Par la plateforme, Noé Vidal "
            "rattaché à la personne de l'annuaire qui porte son adresse, sous le nom qu'elle lui "
            f"donne, « {DIRECTORY_LAST_NAME} », et venu de l'annuaire désormais : un "
            "rattachement qu'aucun exemple ne répond. Chaque inscription dit ce "
            "que l'action a fait, en codes, en identifiants et en libellés du moment, que le "
            "lecteur lit dans sa langue (WF-SEC-0030, WF-ARC-0110).",
            page(administration()),
        ),
        "audit_events_restored.json": mocktext.example(
            "Variante contrefactuelle : le journal d'audit depuis le 3 juin 2026 à 0 h (from), "
            "dans une installation où Camille Martin aurait, ce matin, créé le projet "
            f"« {VANISHED_LABEL} », réintégré au périmètre suivi la ligne {REINSTATED}, puis "
            "restauré la plateforme depuis la sauvegarde du 2 juin. L'inscription de la "
            "restauration en tête, datée de sa fin, 11 h 40, la date de la sauvegarde remise en "
            "place dans ses paramètres ; les inscriptions absentes du journal restauré relues "
            "avant le remplacement des bases et réinscrites après lui ; le projet créé après la "
            "sauvegarde, qui n'existe plus, nommé par son libellé, sans le code qu'il n'avait "
            "pas encore, et sans mener à lui (WF-ADM-0160, WF-ADM-0190, WF-SEC-0030).",
            page(restored()),
        ),
    }
