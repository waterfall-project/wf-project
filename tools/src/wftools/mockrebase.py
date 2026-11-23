# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of the amendment 2 from the main structure, and the refusals (US-3050/L1, #4034).

The amendment 2 of the current revision is up to date (``structures``). A declared variant, the
suite of entries made today on the main structure, puts it out of date: the four writes the main
structure's examples say — the task created in manual mode under the installation
(``node_created_manual``), the wiring of the cabinets renamed (``task_renamed``), the hours of the
connection of the terminal blocks entered (``estimate_line_updated``), the line of the terminal
blocks deleted (``node_deleted``) — and, declared here, the line of the commissioning
re-estimated, which the amendment designates at its own hours. The report of its update
presents one difference of each sort: the task added, the label and the hours updated, the line
removed, and the hours of the commissioning kept by the differential (`kept`, ``fields``):

- ``structure_rebase_report.json``, that report, which nothing refuses;
- ``structure_rebase_report_refused.json``, its refused variant: the main structure has besides
  made the mounting follow the commissioning, withdrawing the link the other way, which the
  amendment withdraws too; carried into the differential, where the commissioning follows the
  resumed trials, which follow the mounting, it closes a loop (`LINK_CYCLE`), each task named by
  its node in the differential;
- ``structure_rebased.json``, the amendment once updated: up to date, its counter advanced;
- ``structure_rebase_link_cycle.json``, the update confirmed on the refused variant: 422;
- ``structure_rebase_stale.json``, the update confirmed after a new entry of the main structure;
- ``structure_rebase_up_to_date_refused.json``, the update of the amendment as ``structures``
  lists it, up to date: refused by ``structure_out_of_date``;
- ``merge_out_of_date_refused.json``, the merge of the amendment out of date: refused by
  ``structure_up_to_date``.

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockamendment, mockcore, mocktext
from wftools.mockamendment import LABEL, own_id
from wftools.mockids import universe
from wftools.mocknonworking import CREATED_LABEL, CREATED_MANUAL
from wftools.mockrefusals import stale, state_refused
from wftools.mockwitness import N, lineage_id
from wftools.mockwrites import LABOUR_HOURS, RENAMED

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

UP_TO_DATE_CORRELATION, STALE_CORRELATION = universe(1961), universe(1962)
CYCLE_CORRELATION, MERGE_CORRELATION = universe(1963), universe(1964)
"""The correlations of the refusals of the update and of the merge out of date (US-3050/L1)."""

COMMISSIONING_REESTIMATED = Decimal(96)
"""The hours the main structure re-estimates the line of the commissioning to, declared: the
amendment designates its own (``mockamendment.COMMISSIONING_HOURS``)."""

MAIN_WRITES = 5
"""The writes of the main structure since the base of the amendment, each advancing its counter."""

RELINKING_WRITES = 2
"""The writes of the refused variant besides: the predecessors of the mounting, of the
commissioning."""

CYCLE = (N.MOUNTING, N.TESTS_RESUMED, N.COMMISSIONING)
"""The loop the refused variant closes, in the order of the plan, each preceding the next."""


def node_labels() -> dict[int, str]:
    """Return the labels of the nodes of the differential, by their number in the witness."""
    labels = {row.number: row.label for row in mockcore.current()}
    labels[N.TESTS_RESUMED] = mockamendment.TESTS_RESUMED.label
    return labels


def difference(change: str, target: str, number: int, label: str, fields: list[str]) -> JsonObject:
    """Return a node of the main structure as the report names it (`ImportDifference`).

    An addition carries its lineage in the main structure, under which it enters the differential.
    """
    return {
        "change": change,
        "target": target,
        "lineage_id": lineage_id(number),
        "label": label,
        "predecessor_label": None,
        "fields": cast("list[JsonValue]", fields),
    }


def counters() -> tuple[int, int]:
    """Return the counters the report reads: the main structure after its writes, the amendment."""
    main = cast("int", mockamendment.structure("main")["lock_version"])
    return main + MAIN_WRITES, cast("int", mockamendment.structure("amendment")["lock_version"])


def report() -> JsonObject:
    """Return what getStructureRebaseReport answers of the amendment 2 out of date (#4034)."""
    labels = node_labels()
    main, amendment = counters()
    differences: list[JsonValue] = [
        difference("added", "task", CREATED_MANUAL, CREATED_LABEL, []),
        difference("updated", "task", N.WIRING, RENAMED, ["label"]),
        difference("updated", "estimate_line", N.LABOUR, labels[N.LABOUR], ["hours"]),
        difference("removed", "estimate_line", N.BLOCKS, labels[N.BLOCKS], []),
        difference(
            "kept", "estimate_line", N.COMMISSIONING_LINE, labels[N.COMMISSIONING_LINE], ["hours"]
        ),
    ]
    return {
        "main_structure_lock_version": main,
        "structure_lock_version": amendment,
        "differences": differences,
        "refusals": [],
        "severity": None,
        "provision_amount": None,
    }


def cycle() -> JsonObject:
    """Return the loop the refused variant closes, each task by its node in the differential."""
    labels = node_labels()
    return {"cycle": [{"node_id": own_id(number), "label": labels[number]} for number in CYCLE]}


def report_refused() -> JsonObject:
    """Return the report of the refused variant: the link added, the loop it closes."""
    labels = node_labels()
    applicable = report()
    link: JsonObject = {
        "change": "added",
        "target": "link",
        "lineage_id": lineage_id(N.MOUNTING),
        "label": labels[N.MOUNTING],
        "predecessor_label": labels[N.COMMISSIONING],
        "fields": [],
    }
    differences = cast("list[JsonValue]", applicable["differences"])
    return {
        **applicable,
        "main_structure_lock_version": cast("int", applicable["main_structure_lock_version"])
        + RELINKING_WRITES,
        "differences": [*differences[:1], link, *differences[1:]],
        "refusals": [{"code": "LINK_CYCLE", "params": cycle()}],
    }


def rebased() -> JsonObject:
    """Return the amendment 2 once updated: up to date, its counter advanced by the update."""
    amendment = mockamendment.structure("amendment")
    return {**amendment, "lock_version": cast("int", amendment["lock_version"]) + 1}


def examples() -> dict[str, JsonObject]:
    """Return the examples of the update of the amendment 2, by file name."""
    labels = node_labels()
    read, refused = report(), report_refused()
    main, amendment = counters()
    after = rebased()
    hours = mocktext.amount(mockamendment.COMMISSIONING_HOURS, 0)
    writes = (
        f"la « {CREATED_LABEL} » créée sous l'« {labels[N.INSTALLATION]} » "
        f"(node_created_manual), la « {labels[N.WIRING]} » renommée « {RENAMED} » "
        f"(task_renamed), la charge du « {labels[N.LABOUR]} » portée à "
        f"{mocktext.amount(LABOUR_HOURS, 0)} h (estimate_line_updated), la ligne « "
        f"{labels[N.BLOCKS]} » supprimée (node_deleted), et la ligne « "
        f"{labels[N.COMMISSIONING_LINE]} » réestimée à "
        f"{mocktext.amount(COMMISSIONING_REESTIMATED, 0)} h"
    )
    cycle_said = mocktext.listed([f"« {labels[number]} »" for number in CYCLE])
    return {
        "structure_rebase_report.json": mocktext.example(
            f"Variante déclarée, la suite d'écritures faites aujourd'hui dans la structure "
            f"principale de la révision courante : {writes}. Le différentiel « {LABEL} », à jour "
            f"jusque-là (structures), est en retard, et le compte rendu préalable de sa mise à "
            f"jour présente ce qu'elle y reporterait : la tâche ajoutée, sous sa lignée, à sa "
            f"place ; le libellé et la charge modifiés ; la ligne retirée. La charge de la ligne "
            f"« {labels[N.COMMISSIONING_LINE]} », que l'avenant porte à {hours} h, est gardée "
            f"et signalée (kept, ses champs) : la fusion lui donnera ces {hours} h pour "
            f"référence, et la principale gardera sa réestimation (WF-REV-0050). Aucun motif de "
            f"refus : la confirmation est offerte, qui renverra les compteurs lus — celui de la "
            f"principale, {main}, et celui du différentiel, {amendment} (WF-REV-0100, "
            f"WF-IHM-0110, #4034).",
            read,
        ),
        "structure_rebase_report_refused.json": mocktext.example(
            f"Variante déclarée de structure_rebase_report : la structure principale a de plus "
            f"fait suivre le « {labels[N.MOUNTING]} » à la « {labels[N.COMMISSIONING]} », la "
            f"liaison inverse retirée — que l'avenant retire aussi, et qui ne se signale donc "
            f"pas. Reportée dans le différentiel, où la « {labels[N.COMMISSIONING]} » suit la "
            f"« {labels[N.TESTS_RESUMED]} », qui suit le « {labels[N.MOUNTING]} », la liaison "
            f"ajoutée fermerait une boucle : le motif la refuse, les tâches nommées par leur nœud "
            f"dans le différentiel et leur libellé, {cycle_said}, chacune précédant la suivante ; "
            f"la confirmation n'est pas offerte. L'utilisateur retire la liaison fautive du "
            f"différentiel, puis relance (WF-PLA-0030, WF-REV-0100, #4034).",
            refused,
        ),
        "structure_rebased.json": mocktext.example(
            f"Le différentiel « {LABEL} » mis à jour, la confirmation du compte rendu "
            f"structure_rebase_report reçue avec ses compteurs : ce que la principale a reçu est "
            f"écrit dans le différentiel, ce qu'il désigne est inchangé, et il est à jour — sa "
            f"commande rebase n'a plus rien à reprendre (structure_out_of_date) ; son compteur "
            f"passe à {after['lock_version']}. La structure principale n'est pas écrite "
            f"(WF-REV-0100, #4034).",
            after,
        ),
        "structure_rebase_link_cycle.json": mocktext.example(
            f"La mise à jour du différentiel « {LABEL} » confirmée sur le compte rendu de "
            f"structure_rebase_report_refused, qui la refusait : la liaison reportée fermerait "
            f"une boucle dans le différentiel, {cycle_said} ; refusée par le premier motif du "
            f"compte rendu, ses paramètres repris ; rien n'est écrit (WF-PLA-0030, #4034).",
            {
                "code": "LINK_CYCLE",
                "status": 422,
                "params": cycle(),
                "correlation_id": CYCLE_CORRELATION,
            },
        ),
        "structure_rebase_stale.json": mocktext.example(
            f"La mise à jour du différentiel « {LABEL} » confirmée avec les compteurs de "
            f"structure_rebase_report, la structure principale écrite une fois de plus depuis "
            f"sa lecture : le compte rendu est périmé, rien n'est écrit, et le compteur courant "
            f"du différentiel, l'objet que le chemin nomme, est rendu ; l'écran propose de "
            f"relire le compte rendu (WF-IHM-0110, #4034).",
            stale(amendment, STALE_CORRELATION),
        ),
        "structure_rebase_up_to_date_refused.json": mocktext.example(
            f"Le compte rendu de la mise à jour du différentiel « {LABEL} » demandé tel que "
            f"`structures` le liste, à jour : sa base est la structure principale telle qu'elle "
            f"est, et il n'a rien à en reprendre — sa commande rebase le disait d'avance ; "
            f"refusé par la condition qui manque, structure_out_of_date, comme la mise à jour "
            f"elle-même ; rien n'est écrit (WF-REV-0100, WF-IHM-0090, #4034).",
            state_refused("structure_out_of_date", UP_TO_DATE_CORRELATION),
        ),
        "merge_out_of_date_refused.json": mocktext.example(
            f"La fusion du différentiel « {LABEL} » demandée après les écritures de la structure "
            f"principale de structure_rebase_report, qui l'ont mis en retard : la fusion "
            f"n'applique que ce qu'il désigne, et l'exige à jour ; elle ne le met pas à jour "
            f"elle-même. Refusée, le compte rendu comme la confirmation, par la condition qui "
            f"manque, structure_up_to_date, nommée après celles de la fusion ; rien n'est "
            f"fusionné. L'écran offre la mise à jour (rebase, WF-REV-0050, #4034).",
            state_refused("structure_up_to_date", MERGE_CORRELATION),
        ),
    }
