# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exit of the witness, its code refused, and the quality of whom reads it (US-0701/L9).

The review of the contract before the freeze (D-01, D-02, D-06, D-07) and its minors J-18 and
L-25, on examples drawn from those written by hand:

- ``project_exit_abandoning.json`` and ``project_exit_marking.json``, the two bodies of
  ``exitProject`` for the witness, which bears the revision 102 in progress: the one abandons it,
  and the exit answers the project (``project_completed``, written by hand, which says so); the
  other marks it under a version name no marked revision bears, and the exit answers the task of
  the marking (``task_exit_mark_queued.json``), the exit applied when it succeeds (WF-CYC-0090,
  WF-ARC-0090); ``project_exit_revision_required.json``, the exit sent without the fate of the
  revision in progress, refused; ``project_exit_version_name_required.json`` and
  ``project_exit_version_name_taken.json``, the exit that marks it without a version name, or
  under one a marked revision bears already, refused as ``markRevision`` refuses them;
- ``project_code_invalid.json``, a project created under a code that bears a slash, the one
  separator of the WBS element that bears it (WF-CRE-0020);
- ``project_participant.json``, the witness read by a participant who holds the permissions of its
  project manager: the commands reserved to the project managers listed unavailable, the quality
  named (WF-IHM-0090, WF-PRJ-0060); ``project_rescue.json``, the witness read, in a counterfactual
  variant where the account of its one project manager is deactivated, by a non-contributor who
  holds the permission of the settings of the project and « consulter tous les projets »: the
  entry of a project manager open to him alone, every other command naming his quality
  (WF-PRJ-0060); ``contributors_without_active_manager.json``, the list he reads with its counter,
  and ``contributors_set_by_rescuer.json``, the list he writes, a participant passed project
  manager;
- ``project_background_task_running.json``, the witness read while the marking of its current
  revision runs (``revision_marking``): the commands a background task would make stale — the
  entry of the work breakdown, the exits the witness lists, the occurrence of a risk and the
  imports that would write in the revision — unavailable, ``no_background_task_running`` missing
  after their conditions of state; the others, its contributors, its timelines, its actual costs
  and its attributes among them, as the witness
  lists them (WF-IHM-0090, WF-PLA-0170, WF-CYC-0090; #1142, point 5, US-0660/L2).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from wftools import mocktext
from wftools.mockids import universe
from wftools.mocklists import CONTRIBUTOR_KINDS, display_name
from wftools.mockwitness import fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

EXIT_TASK = universe(955)
"""The task of the marking an exit of the witness starts (`exitProject`, 202)."""

REQUIRED_CORRELATION, CODE_CORRELATION = universe(1606), universe(1607)
NAME_REQUIRED_CORRELATION, NAME_TAKEN_CORRELATION = universe(1608), universe(1609)
"""The correlations of the refusals of the module."""

TAKEN_NAME = "Référence"
"""A version name a marked revision of the witness bears already, the 101 (WF-REV-0020)."""

VERSION_NAME = "Clôture"
"""The version name the exit that marks gives the revision in progress, which no marked revision
of the witness bears (WF-REV-0020)."""

INVALID_CODE = "PRJ-003/A"
"""A project code that bears a slash, which the WBS element would read as a subproject."""

RESERVED = frozenset(
    {
        "update",
        "update_win_probability",
        "update_work_breakdown",
        "manage_contributors",
        "complete",
        "lose",
        "abandon",
        "declare_risk_occurrence",
        "exclude_cost_lines",
    }
)
"""The commands of a project reserved to its project managers: the settings of the project
(FBS-4.2 — its attributes, its work breakdown, its contributors) and the structuring actions of
the catalogue a project carries — the exits, the occurrence of a risk, the exclusion of a line
of cost (WF-PRJ-0060, WF-ADM-0100)."""

SUSPENDED = frozenset(
    {
        "update_work_breakdown",
        "complete",
        "lose",
        "abandon",
        "declare_risk_occurrence",
        "import_planning",
        "import_estimate",
        "import_remaining",
    }
)
"""The commands of a project a background task that writes in its current revision or freezes it
suspends (`CommandCondition`, `no_background_task_running`): the entry of the work breakdown,
which withdraws the attachment of its tasks (WF-PLA-0170), the three exits, whose fate would mark
or abandon it (WF-CYC-0090), the occurrence of a risk, which merges in it (WF-RIS-0060), and the
imports that would write in it (WF-INTF-0090). Its attributes, its contributors, its timelines,
the opening of a revision, the actual costs and the exclusion of a line write nothing in it."""

BACKGROUND = "no_background_task_running"

PARTICIPANT = universe(306)
"""Inès Roux, participant of the witness for its piloting, who holds the role « Pilotage de
projet »: every permission of a project manager on the project, none of its quality."""

DEACTIVATED_MANAGER = universe(301)
"""Camille Martin, the one project manager of the witness, deactivated in the variant."""

RESCUER = universe(302)
"""Dominique Bernard, manager, a non-contributor, who would hold « Direction de projet » too in
the variant: the settings of the project and « consulter tous les projets »."""


def _witness_version() -> JsonValue:
    """Return the counter of the witness as read, which its exit carries (WF-IHM-0110)."""
    return cast("JsonObject", fixture("project"))["lock_version"]


def exit_abandoning() -> JsonObject:
    """Return the exit of the witness to completed that abandons its revision in progress."""
    return {
        "to_state": "completed",
        "confirmed": True,
        "reason": None,
        "current_revision": {"action": "abandon"},
        "lock_version": _witness_version(),
    }


def exit_marking() -> JsonObject:
    """Return the exit of the witness to completed that marks its revision in progress."""
    return {
        "to_state": "completed",
        "confirmed": True,
        "reason": None,
        "current_revision": {
            "action": "mark",
            "version_name": VERSION_NAME,
            "description": "La révision en cours, marquée à la sortie du projet.",
        },
        "lock_version": _witness_version(),
    }


EXIT_SUBMITTED = "2026-06-03T14:05:30Z"
"""When the exit puts its marking in the queue: within the minute of the write of today, at an
instant no other task of the universe is submitted at (`test_mockuniverse`)."""


def exit_mark_queued() -> JsonObject:
    """Return the task of the marking the exit starts: a marking of today, a task of its own."""
    return {
        **cast("JsonObject", fixture("task_mark_queued")),
        "task_id": EXIT_TASK,
        "submitted_at": EXIT_SUBMITTED,
    }


def _refusal(
    pointer: str, code: str, correlation: str, params: JsonObject | None = None
) -> JsonObject:
    """Return a 422 that names one field by its motive, and the parameters of that motive."""
    field: JsonObject = {"pointer": pointer, "code": code}
    if params is not None:
        field["params"] = params
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [field],
        "correlation_id": correlation,
    }


def name_taken(pointer: str, correlation: str) -> JsonObject:
    """Return the 409 of a version name a marked revision bears already, as `markRevision`.

    The field named by its pointer: the exit, the marking and the merge each name theirs.
    """
    [holder] = [
        each
        for each in cast("list[JsonObject]", fixture("revisions")["items"])
        if each["version_name"] == TAKEN_NAME
    ]
    return {
        "code": "ALREADY_EXISTS",
        "status": 409,
        "fields": [
            {
                "pointer": pointer,
                "code": "ALREADY_EXISTS",
                "params": {"conflicting_object_id": holder["revision_id"]},
            }
        ],
        "correlation_id": correlation,
    }


def _commands(project: JsonObject) -> list[JsonObject]:
    return cast("list[JsonObject]", project["available_commands"])


def _lacking(command: JsonObject, qualities: list[str]) -> JsonObject:
    """Return a command unavailable for these qualities, named before its conditions of state."""
    missing = cast("list[str]", command["missing_conditions"])
    return {
        **command,
        "is_available": False,
        "missing_conditions": cast("list[JsonValue]", [*qualities, *missing]),
    }


def _with_commands(project: JsonObject, commands: list[JsonObject]) -> JsonObject:
    return {**project, "available_commands": cast("list[JsonValue]", commands)}


def read_by_participant() -> JsonObject:
    """Return the witness as its participant reads it: the reserved commands lack her quality.

    The quality comes before the conditions of state (`CommandCondition`); the other commands are
    those of the project manager.
    """
    project = cast("JsonObject", fixture("project"))
    return _with_commands(
        project,
        [
            _lacking(each, ["is_project_manager"]) if each["command"] in RESERVED else each
            for each in _commands(project)
        ],
    )


def read_by_rescuer() -> JsonObject:
    """Return the witness as the non-contributor who may enter a project manager reads it.

    `manage_contributors` available, the one write open to him (WF-PRJ-0060); every other
    command his permissions would give him lacks his quality of contributor, and that of project
    manager when it is reserved, before its conditions of state (WF-IHM-0090).
    """
    project = cast("JsonObject", fixture("project"))

    def lacking(each: JsonObject) -> JsonObject:
        if each["command"] == "manage_contributors":
            return {**each, "is_available": True, "missing_conditions": []}
        reserved = ["is_project_manager"] if each["command"] in RESERVED else []
        return _lacking(each, ["is_contributor", *reserved])

    return _with_commands(project, [lacking(each) for each in _commands(project)])


def read_during_marking() -> JsonObject:
    """Return the witness as read while the marking of its current revision runs.

    Each suspended command lacks ``no_background_task_running`` after its conditions of state,
    as the revision being marked lists its own (``revision_marking``); the counter of the project
    is unchanged, the marking writing nothing in it.
    """
    project = cast("JsonObject", fixture("project"))

    def suspended(each: JsonObject) -> JsonObject:
        missing = cast("list[str]", each["missing_conditions"])
        return {
            **each,
            "is_available": False,
            "missing_conditions": cast("list[JsonValue]", [*missing, BACKGROUND]),
        }

    return _with_commands(
        project,
        [suspended(each) if each["command"] in SUSPENDED else each for each in _commands(project)],
    )


def _contributors() -> list[JsonObject]:
    return cast("list[JsonObject]", fixture("contributors")["items"])


def without_active_manager() -> JsonObject:
    """Return the contributors of the witness once its one project manager is deactivated."""
    return {
        "items": cast(
            "list[JsonValue]",
            [
                {**each, "is_active": False} if each["user_id"] == DEACTIVATED_MANAGER else each
                for each in _contributors()
            ],
        ),
        "lock_version": fixture("contributors")["lock_version"],
    }


def set_by_rescuer() -> JsonObject:
    """Return the list the rescuer writes: the participant of the piloting passed project manager.

    Rendered whole, the project managers first, each kind in the order of the list read, which
    ranges them by name; with its next counter.
    """
    read = without_active_manager()
    rows = [
        {**each, "kind": "project_manager"} if each["user_id"] == PARTICIPANT else each
        for each in cast("list[JsonObject]", read["items"])
    ]
    ranged = [row for kind in CONTRIBUTOR_KINDS for row in rows if row["kind"] == kind]
    return {
        "items": cast("list[JsonValue]", ranged),
        "lock_version": cast("int", read["lock_version"]) + 1,
    }


def _name(user_id: str) -> str:
    [row] = [each for each in _contributors() if each["user_id"] == user_id]
    return str(row["display_name"])


def _account_name(user_id: str) -> str:
    """Return the name of an account that is no contributor of the witness, from the accounts."""
    users = cast("list[JsonObject]", fixture("users")["items"])
    [row] = [each for each in users if each["user_id"] == user_id]
    return display_name(row)


def examples() -> dict[str, JsonObject]:
    """Return the exit of the witness, its code refused and its readings, by file."""
    manager, participant = _name(DEACTIVATED_MANAGER), _name(PARTICIPANT)
    rescuer = _account_name(RESCUER)
    variant = (
        f"Variante contrefactuelle : le compte de {manager}, seule cheffe de projet du projet "
        f"témoin, désactivé, et {rescuer}, manager, qui n'en est pas contributeur, "
        f"portant aussi le rôle « Direction de projet » — la permission du paramétrage du projet "
        f"et « consulter tous les projets »"
    )
    return {
        "project_exit_abandoning.json": mocktext.example(
            "La sortie du projet témoin vers Terminé, confirmée sans motif, qui abandonne sa "
            "révision en cours, la 102, dans la même opération : appliquée dans la requête, elle "
            "rend le projet (project_completed) ; après la sortie, le projet n'a plus de révision "
            "en cours, et ses indicateurs se lisent dans sa dernière révision marquée, la "
            "« Référence » 101 (WF-CYC-0090, WF-REV-0010).",
            exit_abandoning(),
        ),
        "project_exit_marking.json": mocktext.example(
            f"La sortie du projet témoin vers Terminé, confirmée sans motif, qui marque sa "
            f"révision en cours, la 102, sous le nom de version « {VERSION_NAME} », qu'aucune "
            f"révision marquée ne porte : le marquage calcule ses indicateurs et se confie au "
            f"worker, la sortie rend la tâche (task_exit_mark_queued) et s'applique quand elle "
            f"réussit ; après la sortie, le projet n'a plus de révision en cours, et ses "
            f"indicateurs se lisent dans sa dernière révision marquée, « {VERSION_NAME} » "
            f"(WF-CYC-0090, WF-REV-0020, WF-ARC-0090).",
            exit_marking(),
        ),
        "task_exit_mark_queued.json": mocktext.example(
            f"Le marquage de la révision 102 sous « {VERSION_NAME} », que la sortie du projet "
            f"témoin demandée aujourd'hui à 14 h 05 a mis en file (project_exit_marking) : il n'a "
            f"pas encore commencé, et le projet reste en cours, sa révision en cours avec lui, "
            f"ses trois sorties indisponibles, no_background_task_running manquante ; la sortie "
            f"s'appliquera quand le marquage réussira, et rien si la tâche échoue (WF-CYC-0090, "
            f"WF-ARC-0090).",
            exit_mark_queued(),
        ),
        "project_exit_revision_required.json": mocktext.example(
            "La sortie du projet témoin vers Terminé, confirmée sans le sort de sa révision en "
            "cours : refusée, le champ désigné, la sortie n'étant appliquée qu'avec le choix de "
            "la marquer ou de l'abandonner ; rien n'est écrit (WF-CYC-0090).",
            _refusal("/current_revision", "VALUE_REQUIRED", REQUIRED_CORRELATION),
        ),
        "project_exit_version_name_required.json": mocktext.example(
            "La sortie du projet témoin vers Terminé, confirmée, qui marque sa révision en cours "
            "sans nom de version : refusée, le champ désigné, le marquage ne se faisant pas "
            "sans nom, comme `markRevision` ; rien n'est écrit (WF-CYC-0090, WF-REV-0020).",
            _refusal("/current_revision/version_name", "VALUE_REQUIRED", NAME_REQUIRED_CORRELATION),
        ),
        "project_exit_version_name_taken.json": mocktext.example(
            f"La sortie du projet témoin vers Terminé, confirmée, qui marque sa révision en cours "
            f"sous « {TAKEN_NAME} », le nom que la révision marquée 101 porte déjà : refusée, "
            f"le champ désigné et la révision qui le porte nommée, comme `markRevision` ; rien "
            f"n'est écrit (WF-CYC-0090, WF-REV-0020).",
            name_taken("/current_revision/version_name", NAME_TAKEN_CORRELATION),
        ),
        "project_code_invalid.json": mocktext.example(
            f"Un projet créé sous le code « {INVALID_CODE} » : refusé, le code désigné, la barre "
            f"oblique étant le seul séparateur de l'élément d'OTP, qui porte le code projet "
            f"suivi du code sous-projet ; rien n'est écrit (WF-PRJ-0010, WF-CRE-0020).",
            _refusal(
                "/code",
                "PROJECT_CODE_INVALID",
                CODE_CORRELATION,
                {"forbidden_characters": ["/"]},
            ),
        ),
        "project_participant.json": mocktext.example(
            f"Le projet témoin lu par {participant}, participante pour le pilotage, qui porte "
            f"toutes les permissions de sa cheffe de projet : les commandes réservées aux chefs "
            f"de projet — le paramétrage, ses contributeurs, les sorties, la survenance d'un "
            f"risque, l'exclusion d'une ligne de coût — sont présentées indisponibles en nommant "
            f"sa qualité, avant leurs conditions d'état ; les autres, la saisie, lui restent "
            f"(WF-IHM-0090, WF-PRJ-0060, WF-ADM-0100).",
            read_by_participant(),
        ),
        "project_rescue.json": mocktext.example(
            f"{variant} : il lit le projet, dont il peut inscrire un chef de projet "
            f"(manage_contributors), la seule saisie ouverte à un non-contributeur ; toute autre "
            f"commande que ses permissions lui donneraient est présentée indisponible en nommant "
            f"sa qualité de contributeur, et de chef de projet pour une commande réservée "
            f"(WF-PRJ-0060, WF-IHM-0090).",
            read_by_rescuer(),
        ),
        "contributors_without_active_manager.json": mocktext.example(
            f"{variant} : la liste qu'il lit avec son compteur, que « consulter tous les projets » "
            f"lui ouvre ; {manager}, cheffe de projet, y reste, signalée désactivée, et aucun chef "
            f"de projet n'a de compte actif (WF-PRJ-0060, WF-ADM-0060).",
            without_active_manager(),
        ),
        "contributors_set_by_rescuer.json": mocktext.example(
            f"{variant} : la liste qu'il enregistre, {participant} passée cheffe de projet, les "
            f"autres gardés tels qu'il les a lus — la seule saisie ouverte à un non-contributeur ; "
            f"rendue entière, les chefs de projet d'abord, avec sa version suivante. La liste "
            f"redevient celle de ses chefs de projet (WF-PRJ-0060, WF-IHM-0110).",
            set_by_rescuer(),
        ),
        "project_background_task_running.json": mocktext.example(
            "Le projet témoin lu pendant que court le marquage de sa révision en cours, la 102 "
            "(revision_marking) : les commandes que ce traitement de fond rendrait caduques — la "
            "saisie du lotissement, qui retirerait le rattachement de tâches que le marquage "
            "fige, les sorties, dont le sort marquerait ou abandonnerait la révision, la "
            "déclaration d'un risque survenu et les imports, qui y écriraient — sont présentées "
            "indisponibles en nommant la condition manquante, aucun traitement de fond en cours, "
            "après leurs conditions d'état ; ses attributs, ses contributeurs, ses chronologies "
            "et ses coûts réels restent disponibles, et la saisie du lotissement aboutit une "
            "fois le marquage fini (WF-IHM-0090, WF-PLA-0170, WF-CYC-0090, WF-IHM-0080).",
            read_during_marking(),
        ),
    }
