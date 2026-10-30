# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals the contract declared without a code, a condition nor an example (US-0702/L2).

The review of the contract before the freeze (`docs/api/2026-10-28-contrat-avant-gel.md`) found
refusals that said neither their code, nor their condition, nor had an example. Each now has the
three, on the examples written by hand and the core of the witness:

- a state refused by its condition, as the object says it beforehand (README, « Conventions »):
  the exit of the witness completed today, and its loss while in progress
  (``project_exit_terminal``, ``project_exit_lost_in_progress``, D-03); the marking, the abandon
  and a differential opened on the reference, the marked revision 101
  (``mark_revision_marked``, ``revision_abandon_marked``, ``structure_create_revision_marked``,
  E-12 to E-14); a revision opened on the offer while an import creates it
  (``revision_create_background_running``, E-13); the deletion of the wiring of the cabinets,
  started, and of the last task that would bear a provision (``node_delete_started_refused``,
  ``node_delete_last_provision_task_refused``, F-04, H-05); an inscription on the reference
  (``node_tracking_marked_refused``, F-11); a line of actual cost excluded on the witness completed
  (``actual_cost_scope_terminal``, I-06); the result of a task that has not succeeded
  (``task_result_not_succeeded``, A-05);
- a version name already borne, refused on its field, by the marking and the merge as by the exit
  (``mark_version_name_taken``, ``merge_version_name_taken``, E-05, E-12);
- a field refused by its motive: the confirmation of the exit missing
  (``project_exit_unconfirmed``, D-03), a predecessor sent twice (``predecessors_duplicate``,
  F-03), an inscription to a timeline without one or with one of another project
  (``node_tracking_timeline_required``, ``node_tracking_timeline_unknown``, F-11);
- the deactivated objects of three lists of the reference asked for without the permission that
  modifies them (``*_inactive_forbidden``, C-01);
- and the answer the deletion of a task bearing a provision gives, which the witness cannot give —
  the one task that bears a provision is started — on a variant of its core
  (``node_deleted_provision_moved``, F-04, L-11).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext
from wftools.mockgestures import TRACKED_TASK
from wftools.mockids import universe
from wftools.mockproject import TAKEN_NAME, name_taken
from wftools.mockrefusals import REFERENCE, field_refused, problem, state_refused
from wftools.mockstructure import described
from wftools.mockwitness import CONTROL_STATION, CORE, N, Task, fixture
from wftools.mockwitnessrisks import IDENTIFIED, REGISTER
from wftools.mockwrites import amended, totals_said, written

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

TERMINAL_CORRELATION, LOST_CORRELATION, UNCONFIRMED_CORRELATION = (
    universe(1638),
    universe(1639),
    universe(1640),
)
"""The correlations of the refusals of the exit (D-03)."""

MARKED_CORRELATION, MARK_NAME_CORRELATION, MERGE_NAME_CORRELATION = (
    universe(1641),
    universe(1642),
    universe(1643),
)
ABANDON_CORRELATION, STRUCTURE_CORRELATION, OPENING_CORRELATION = (
    universe(1644),
    universe(1645),
    universe(1646),
)
"""The correlations of the refusals of the revisions and their structures (E-05, E-12 to E-14)."""

DUPLICATE_CORRELATION, STARTED_CORRELATION, LAST_TASK_CORRELATION = (
    universe(1647),
    universe(1648),
    universe(1649),
)
TRACKING_CORRELATION, TIMELINE_REQUIRED_CORRELATION, TIMELINE_UNKNOWN_CORRELATION = (
    universe(1650),
    universe(1651),
    universe(1652),
)
"""The correlations of the refusals of the common tree (F-03, F-04, F-11)."""

SCOPE_CORRELATION, RESULT_CORRELATION = universe(1653), universe(1654)
ORG_NODES_CORRELATION, CALENDARS_CORRELATION, COST_TYPES_CORRELATION = (
    universe(1655),
    universe(1656),
    universe(1657),
)
"""The correlations of the refusals of the actual costs, the tasks and the reference."""

DUPLICATED_ON, DUPLICATED = N.COMMISSIONING, N.MOUNTING
"""The commissioning, given the mounting for predecessor twice (WF-PLA-0030)."""

STARTED = N.WIRING
"""The wiring of the cabinets, started, whose deletion is refused (WF-PLA-0070)."""

LAST_TASK = N.INSTALLATION
"""The installation on site, not started: the last task of the main structure in the variant
where its deletion would leave the provision of a risk without a task (WF-RIS-0010)."""

RESOURCE_SETTINGS, COST_SETTINGS = "resource_settings.write", "cost_settings.write"
"""The permissions that modify the parameters of resources and of costs (WF-ADM-0100)."""


def _labels() -> dict[int, str]:
    """Return the labels of the nodes of the core of the witness, by their number."""
    return {row.number: row.label for row in mockcore.current()}


def _project(name: str) -> JsonObject:
    return cast("JsonObject", fixture(name))


def _forbidden(permission: str, correlation: str) -> JsonObject:
    """Return the 403 of a permission missing, the permission named (WF-ADM-0110)."""
    return {
        "code": "PERMISSION_MISSING",
        "status": 403,
        "params": {"missing_permission": permission},
        "correlation_id": correlation,
    }


def provisions_without_task() -> list[JsonValue]:
    """Return the risks whose line of provision the current revision bears, still identified.

    By their identifier and their label, in the order of the register (WF-RIS-0010).
    """
    return [
        {"risk_id": universe(risk.number), "label": risk.label}
        for risk in REGISTER
        if risk.provision_line is not None and risk.last.state == IDENTIFIED
    ]


def last_provision_task_refused() -> JsonObject:
    """Return the refusal of a deletion that would leave the provisions without a task."""
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "at_least_one_task", "risks": provisions_without_task()},
        "correlation_id": LAST_TASK_CORRELATION,
    }


def provision_readings() -> tuple[JsonObject, JsonObject]:
    """Return the structure read before and after the deletion of a task bearing a provision.

    A counterfactual variant of the core: the mounting on site, not started, bears the line of
    provision of the risk 751 alone, instead of its own lines (the witness bears it on a task
    that is started). Deleted, the mounting leaves the line, which passes on its parent task, the
    installation; the commissioning, which followed it, loses its link (WF-PLA-0070, WF-RIS-0010).
    """
    [provision] = [
        each
        for task in CONTROL_STATION.children
        for each in task.lines
        if each.number == N.PROVISION
    ]

    def bearing(each: Task) -> Task:
        if each.number == N.WIRING:
            return replace(each, lines=tuple(kept for kept in each.lines if kept != provision))
        if each.number == N.MOUNTING:
            return replace(each, lines=(provision,))
        return each

    def deleting(each: Task) -> Task:
        if each.number == N.INSTALLATION:
            kept = tuple(child for child in each.children if child.number != N.MOUNTING)
            return replace(each, children=kept, lines=(provision,))
        if each.number == N.COMMISSIONING:
            return replace(each, links=())
        return each

    bearing_core = amended(CORE, task=bearing)
    return (
        mockcore.whole(mockcore.current(described(bearing_core))),
        mockcore.whole(mockcore.current(described(amended(bearing_core, task=deleting)))),
    )


def node_deleted_provision_moved() -> JsonObject:
    """Return what deleteNode answers for a task, not started, that bears a line of provision."""
    before, after = provision_readings()
    return written(
        before, after, [universe(N.PROVISION)], deleted=[universe(N.MOUNTING)], structure_version=2
    )


def examples() -> dict[str, JsonObject]:
    """Return the refusals declared without a code, a condition nor an example, by file."""
    return {
        **_exit_examples(),
        **_revision_examples(),
        **_tree_examples(),
        **_other_examples(),
        **_moved_examples(),
    }


def _exit_examples() -> dict[str, JsonObject]:
    witness, completed = _project("project"), _project("project_completed")
    return {
        "project_exit_terminal.json": mocktext.example(
            f"L'abandon demandé du projet témoin, « {completed['label']} », terminé aujourd'hui "
            f"(project_completed) : aucune transition ne part d'un état terminal, et le projet "
            f"n'en liste plus aucune ; refusé par la condition qui manque, project_not_terminal ; "
            f"rien n'est écrit (WF-CYC-0080, WF-CYC-0100, WF-IHM-0090).",
            state_refused("project_not_terminal", TERMINAL_CORRELATION),
        ),
        "project_exit_lost_in_progress.json": mocktext.example(
            f"La perte déclarée du projet témoin, « {witness['label']} », en cours : un projet ne "
            f"se déclare perdu que depuis Chiffrage, et la commande lose n'est plus listée dès En "
            f"cours ; refusée par la condition qui manque, project_in_pricing ; rien n'est écrit "
            f"(WF-CYC-0060, WF-CYC-0080, WF-IHM-0090).",
            state_refused("project_in_pricing", LOST_CORRELATION),
        ),
        "project_exit_unconfirmed.json": mocktext.example(
            "La sortie du projet témoin vers Terminé envoyée sans sa confirmation, confirmed "
            "faux : la sortie est irréversible et la confirmation la garde ; refusée sans "
            "paramètre, comme une restauration non confirmée ; rien n'est écrit (WF-CYC-0090, "
            "WF-CYC-0080).",
            problem("CONFIRMATION_REQUIRED", 400, UNCONFIRMED_CORRELATION),
        ),
    }


def _reference_name() -> str:
    """Return the version name of the marked revision 101, from the revisions written by hand."""
    revisions = cast("list[JsonObject]", fixture("revisions")["items"])
    [revision] = [each for each in revisions if each["revision_id"] == REFERENCE]
    return str(revision["version_name"])


def _revision_examples() -> dict[str, JsonObject]:
    reference, offer = _reference_name(), _project("project_pricing")
    return {
        "mark_revision_marked.json": mocktext.example(
            f"Le marquage demandé de la révision « {reference} », déjà marquée (revision_marked) : "
            f"une révision marquée ne se modifie plus, et sa commande mark le disait d'avance ; "
            f"refusé par la condition qui manque, revision_draft ; rien n'est écrit (WF-REV-0020, "
            f"WF-DAT-0020, WF-IHM-0090).",
            state_refused("revision_draft", MARKED_CORRELATION),
        ),
        "mark_version_name_taken.json": mocktext.example(
            f"Le marquage de la révision en cours du témoin, la 102, sous « {TAKEN_NAME} », le nom "
            f"que la révision marquée 101 porte déjà : refusé, le champ désigné et la révision qui "
            f"le porte nommée ; rien n'est mis en file (WF-REV-0020).",
            name_taken("/version_name", MARK_NAME_CORRELATION),
        ),
        "merge_version_name_taken.json": mocktext.example(
            f"La fusion de l'avenant 2 dans la révision en cours du témoin, confirmée sous "
            f"« {TAKEN_NAME} », le nom que la révision marquée 101 porte déjà : la fusion marque "
            f"la révision, comme tout marquage ; refusée au dépôt, le champ désigné et la "
            f"révision qui le porte nommée, rien n'est mis en file (WF-REV-0050, WF-REV-0020).",
            name_taken("/version_name", MERGE_NAME_CORRELATION),
        ),
        "revision_abandon_marked.json": mocktext.example(
            f"L'abandon demandé de la révision « {reference} », marquée : seule la révision en "
            f"cours s'abandonne, et la commande abandon de la révision marquée le disait "
            f"d'avance ; refusé par la condition qui manque, revision_draft ; rien n'est supprimé "
            f"(WF-REV-0010, WF-DAT-0020, WF-IHM-0090).",
            state_refused("revision_draft", ABANDON_CORRELATION),
        ),
        "structure_create_revision_marked.json": mocktext.example(
            f"Un différentiel ouvert sur la révision « {reference} », marquée : sa commande "
            f"create_structure le disait d'avance ; refusé par la condition qui manque, "
            f"revision_draft ; rien n'est créé (WF-REV-0100, WF-DAT-0020, WF-IHM-0090).",
            state_refused("revision_draft", STRUCTURE_CORRELATION),
        ),
        "revision_create_background_running.json": mocktext.example(
            f"Variante contrefactuelle de l'offre en chiffrage, « {offer['label']} », sans "
            f"révision en cours : une révision ouverte pendant que l'application d'un import de "
            f"devis crée elle-même sa révision en cours, invisible jusqu'à sa fin. Refusée par la "
            f"condition que la commande create_revision dit manquer, no_background_task_running ; "
            f"rien n'est créé (WF-REV-0010, WF-INTF-0090, WF-IHM-0090).",
            state_refused("no_background_task_running", OPENING_CORRELATION),
        ),
    }


def _tree_examples() -> dict[str, JsonObject]:
    labels, reference = _labels(), _reference_name()
    risks = [f"« {cast('JsonObject', risk)['label']} »" for risk in provisions_without_task()]
    return {
        "predecessors_duplicate.json": mocktext.example(
            f"La « {labels[DUPLICATED_ON]} » donnée à suivre deux fois le "
            f"« {labels[DUPLICATED]} », une fin-début et une début-début : deux tâches ne sont "
            f"reliées que par une liaison au plus ; la seconde est refusée sur son champ, à son "
            f"rang ; rien n'est écrit (WF-PLA-0030).",
            field_refused(
                "/predecessors/1/predecessor_node_id",
                "DUPLICATE_PREDECESSOR",
                DUPLICATE_CORRELATION,
            ),
        ),
        "node_delete_started_refused.json": mocktext.example(
            f"La suppression demandée du « {labels[STARTED]} », démarré : une tâche démarrée ou "
            f"terminée ne peut pas être supprimée ; refusée par la condition qui manque, "
            f"task_not_started, l'écran renvoyant à la mise à zéro de son reste à engager ; rien "
            f"n'est supprimé (WF-PLA-0070, WF-IHM-0090).",
            state_refused("task_not_started", STARTED_CORRELATION),
        ),
        "node_delete_last_provision_task_refused.json": mocktext.example(
            f"Variante contrefactuelle de la structure principale du témoin, réduite à "
            f"l'« {labels[LAST_TASK]} », non démarrée, qui porte la provision de "
            f"{mocktext.listed(risks)} : la supprimer laisserait la provision sans tâche où se "
            f"ranger ; refusée en nommant le risque, rien n'est supprimé (WF-RIS-0010, "
            f"WF-PLA-0070).",
            last_provision_task_refused(),
        ),
        "node_tracking_marked_refused.json": mocktext.example(
            f"La « {labels[TRACKED_TASK]} » inscrite à une chronologie sur la structure "
            f"principale de la révision « {reference} », marquée : son inscription relève de la "
            f"saisie du planning, que la structure dit indisponible ; refusée par la condition qui "
            f"manque, revision_draft ; rien n'est écrit (WF-PLA-0060, WF-DAT-0020).",
            state_refused("revision_draft", TRACKING_CORRELATION),
        ),
        "node_tracking_timeline_required.json": mocktext.example(
            f"La « {labels[TRACKED_TASK]} » envoyée avec une entrée timeline sans chronologie : "
            f"une inscription à une chronologie la nomme ; refusée sur le champ de l'entrée ; rien "
            f"n'est écrit (WF-PLA-0060, WF-PLA-0140).",
            field_refused(
                "/entries/0/timeline_id", "VALUE_REQUIRED", TIMELINE_REQUIRED_CORRELATION
            ),
        ),
        "node_tracking_timeline_unknown.json": mocktext.example(
            f"La « {labels[TRACKED_TASK]} » inscrite à une chronologie d'un autre projet : seules "
            f"les chronologies du projet portent ses tâches ; refusée sur le champ de l'entrée, "
            f"comme une chronologie que le serveur n'a pas ; rien n'est écrit (WF-PLA-0060, "
            f"WF-PLA-0140).",
            field_refused(
                "/entries/0/timeline_id", "UNKNOWN_TIMELINE", TIMELINE_UNKNOWN_CORRELATION
            ),
        ),
    }


def _moved_examples() -> dict[str, JsonObject]:
    labels = _labels()
    moved = node_deleted_provision_moved()
    return {
        "node_deleted_provision_moved.json": mocktext.example(
            f"La suppression du « {labels[N.MOUNTING]} », non démarré, variante contrefactuelle "
            f"du témoin où il porte seul la ligne de provision « {labels[N.PROVISION]} » du "
            f"risque 751 : la ligne n'est pas emportée, elle passe sous sa tâche parente, "
            f"« {labels[N.INSTALLATION]} », et est rendue écrite dans nodes, une version de "
            f"plus ; le risque voit sa tâche de provision changer, et son compteur avec elle, "
            f"que lit getRisk. {totals_said(moved)}, inchangés, et le compteur de la "
            f"structure, passé à 2 (WF-PLA-0070, WF-RIS-0010, WF-IHM-0110).",
            moved,
        ),
    }


def _other_examples() -> dict[str, JsonObject]:
    completed = _project("project_completed")
    return {
        "actual_cost_scope_terminal.json": mocktext.example(
            f"Une ligne de coût réel du projet témoin, « {completed['label']} », exclue du "
            f"périmètre suivi après sa clôture (project_completed) : ses coûts réels sont en "
            f"lecture seule, et sa commande exclude_cost_lines le disait d'avance ; refusée par la "
            f"condition qui manque, project_not_terminal ; rien n'est écrit (WF-CYC-0100, "
            f"WF-CRE-0030, WF-IHM-0090).",
            state_refused("project_not_terminal", SCOPE_CORRELATION),
        ),
        "task_result_not_succeeded.json": mocktext.example(
            "Le résultat de l'export demandé aujourd'hui, téléchargé alors que sa tâche est encore "
            "en file (task_export_queued) : une tâche qui n'a pas abouti n'a pas de fichier ; "
            "refusé par la condition qui manque, task_succeeded ; le front suit la tâche "
            "(WF-ARC-0090, WF-IHM-0080).",
            state_refused("task_succeeded", RESULT_CORRELATION),
        ),
        "org_nodes_inactive_forbidden.json": mocktext.example(
            "L'arbre d'organisation demandé avec include_inactive par une session qui ne peut pas "
            "modifier les paramètres de ressources : les nœuds désactivés restent sous cette "
            "permission, refusée en la nommant ; rien n'est lu (WF-REF-0150, WF-ADM-0100).",
            _forbidden(RESOURCE_SETTINGS, ORG_NODES_CORRELATION),
        ),
        "calendars_inactive_forbidden.json": mocktext.example(
            "Les calendriers demandés avec is_active=false par une session qui ne peut pas "
            "modifier les paramètres de ressources : les calendriers désactivés restent sous "
            "cette permission, refusée en la nommant ; rien n'est lu (WF-REF-0150, WF-ADM-0100).",
            _forbidden(RESOURCE_SETTINGS, CALENDARS_CORRELATION),
        ),
        "cost_types_inactive_forbidden.json": mocktext.example(
            "Les natures de coût demandées avec include_inactive par une session qui ne peut pas "
            "modifier les paramètres de coûts : les natures désactivées restent sous cette "
            "permission, refusée en la nommant ; rien n'est lu (WF-REF-0150, WF-ADM-0100).",
            _forbidden(COST_SETTINGS, COST_TYPES_CORRELATION),
        ),
    }
