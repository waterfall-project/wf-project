# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The examples of the minors of the review of the 2026-10-31 on the revisions and structures.

The author decided on the 2026-11-07 to give each refusal of the revisions and of their structures
that the contract declared without an example the example that shows it, drawn from the witness:

- ``comparison_revision_draft.json``, the reference 101 compared with the current revision 102,
  not marked: refused by ``revision_marked`` (``compareRevisions``, WF-REV-0080);
- ``mark_restore_running.json``, the marking of the current revision 102 asked while a restore is
  queued: refused by ``no_restore_running`` (``markRevision``, WF-ADM-0160);
- ``reference_designate_unconfirmed.json``, a designation of the reference sent without its
  confirmation: ``CONFIRMATION_REQUIRED``, without a parameter, like the exit
  (``designateReferenceRevision``);
- ``structure_update_revision_marked.json``, ``structure_update_stale.json`` and
  ``structure_label_updated.json``, the label of a structure written on the marked reference, with
  a stale counter on the amendment 2, and accepted on it (``updateCostStructure``, WF-REV-0100);
- ``undo_background_running.json`` and ``redo_background_running.json``, an undo and a redo asked
  while the current revision is being marked: refused by ``no_background_task_running``
  (``undoLastChange``, ``redoLastUndo``, WF-IHM-0110).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from typing import TYPE_CHECKING, cast

from wftools import mockamendmentwrites, mocktext
from wftools.mockids import universe
from wftools.mockrefusals import REFERENCE, problem, stale, state_refused
from wftools.mockwitness import fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

COMPARISON_CORRELATION, MARK_RESTORE_CORRELATION = universe(1950), universe(1951)
UNCONFIRMED_CORRELATION, STRUCTURE_MARKED_CORRELATION = universe(1952), universe(1953)
STRUCTURE_STALE_CORRELATION = universe(1954)
UNDO_RUNNING_CORRELATION, REDO_RUNNING_CORRELATION = universe(1955), universe(1956)
"""The correlations of the refusals of the revisions and their structures (2026-11-07)."""

AMENDMENT = universe(203)
"""The amendment 2 of the current revision, the differential whose label is written."""

RELABELLED = "Avenant 2 — reprise des essais usine et site"
"""The label the amendment 2 receives (``structure_label_updated``)."""


def _reference_name() -> str:
    """Return the version name of the marked revision 101, from the revisions written by hand."""
    revisions = cast("list[JsonObject]", fixture("revisions")["items"])
    [revision] = [each for each in revisions if each["revision_id"] == REFERENCE]
    return str(revision["version_name"])


def _amendment() -> JsonObject:
    """Return the amendment 2 as the structures of the current revision list it."""
    [found] = [
        each
        for each in cast("list[JsonObject]", fixture("structures"))
        if each["structure_id"] == AMENDMENT
    ]
    return found


def structure_label_updated() -> JsonObject:
    """Return what updateCostStructure answers to the label of the amendment 2 alone.

    A label re-dates no task and changes no amount: no node written, re-dated or re-inflated, the
    totals of the differential unchanged, and its counter one further (``NodesWritten``).
    """
    return {
        "nodes": [],
        "ancestors": [],
        "rescheduled": [],
        "reinflated": [],
        "totals": mockamendmentwrites.reading()["totals"],
        "structure_lock_version": cast("int", _amendment()["lock_version"]) + 1,
    }


def examples() -> dict[str, JsonObject]:
    """Return the examples of the revisions and their structures, by file name."""
    reference, amendment = _reference_name(), _amendment()
    label, counter = str(amendment["label"]), cast("int", amendment["lock_version"])
    return {
        "comparison_revision_draft.json": mocktext.example(
            f"La révision « {reference} », marquée, comparée à la révision courante du témoin, la "
            f"102, en brouillon : seules deux révisions marquées se comparent, la révision "
            f"courante changeant encore sous son lecteur ; refusée par la condition qui manque, "
            f"revision_marked ; rien n'est lu (WF-REV-0080, WF-DAT-0020).",
            state_refused("revision_marked", COMPARISON_CORRELATION),
        ),
        "mark_restore_running.json": mocktext.example(
            "Le marquage de la révision courante du témoin, la 102, demandé pendant que la "
            "restauration de la plateforme est en file (task_restore_queued) : la restauration "
            "remplace la base où le marquage s'écrirait, et la commande mark le disait d'avance ; "
            "refusé par la condition qui manque, no_restore_running ; rien n'est mis en file "
            "(WF-ADM-0160, WF-REV-0020, WF-IHM-0090).",
            state_refused("no_restore_running", MARK_RESTORE_CORRELATION),
        ),
        "reference_designate_unconfirmed.json": mocktext.example(
            "La désignation de la référence du projet envoyée sans sa confirmation, confirmed "
            "faux : refusée sans paramètre, comme la sortie (project_exit_unconfirmed) et la "
            "restauration ; la référence ne change pas, et rien n'est écrit (WF-REV-0040, "
            "WF-CYC-0030).",
            problem("CONFIRMATION_REQUIRED", 400, UNCONFIRMED_CORRELATION),
        ),
        "structure_update_revision_marked.json": mocktext.example(
            f"Le libellé de la structure principale de la révision « {reference} », marquée, "
            f"modifié : sa commande edit_planning le disait d'avance ; refusé par la condition qui "
            f"manque, revision_draft ; rien n'est écrit (WF-REV-0100, WF-DAT-0020, WF-IHM-0090).",
            state_refused("revision_draft", STRUCTURE_MARKED_CORRELATION),
        ),
        "structure_update_stale.json": mocktext.example(
            f"Le libellé du différentiel « {label} » envoyé avec le compteur {counter - 1}, quand "
            f"la structure porte {counter} — une saisie l'a écrite depuis la lecture de l'écran — "
            f": refusé, le compteur courant rendu, et rien n'est écrit ; l'écran propose de relire "
            f"(WF-IHM-0110).",
            stale(counter, STRUCTURE_STALE_CORRELATION),
        ),
        "structure_label_updated.json": mocktext.example(
            f"Le différentiel « {label} » renommé « {RELABELLED} », sa date de début de planning "
            f"inchangée : aucune tâche n'est redatée et aucun montant ne bouge — nodes, "
            f"rescheduled, reinflated et ancestors vides, les totaux du différentiel inchangés —, "
            f"et le compteur de la structure passe de {counter} à {counter + 1} ; l'écriture "
            f"entre dans l'historique de l'auteur (structure_update) (WF-REV-0100, WF-IHM-0110).",
            structure_label_updated(),
        ),
        "undo_background_running.json": mocktext.example(
            "Une annulation demandée sur la révision courante du témoin pendant son marquage, "
            "traitement qui la fige : refusée par la condition qui manque, "
            "no_background_task_running, avant tout autre refus ; rien n'est défait "
            "(WF-IHM-0110, WF-ARC-0090).",
            state_refused("no_background_task_running", UNDO_RUNNING_CORRELATION),
        ),
        "redo_background_running.json": mocktext.example(
            "Un rétablissement demandé sur la révision courante du témoin pendant son marquage, "
            "traitement qui la fige : refusé par la condition qui manque, "
            "no_background_task_running, comme l'annulation ; rien n'est rétabli (WF-IHM-0110, "
            "WF-ARC-0090).",
            state_refused("no_background_task_running", REDO_RUNNING_CORRELATION),
        ),
    }
