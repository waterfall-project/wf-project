# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The registries of the extensions, filled in every process that needs them (#2180; EP-06).

A registry is filled at the import of the interface of the module that registers: a process that
never imports it holds a registry without its part, and copies a revision without its tasks, or
designates a reference without asking for them, in silence. Each entry point — the API
(``create_app``), the worker (``handlers``), the loader of the witness (``load_witness``) — is
imported in a process of its own, and its registries compared with those of a process that imports
every module of the core and of the witness: none lacks an extension that a module registers — the
worker those of the estimate included, which it imports from US-1500/L2 on (EP-07, "Le worker"),
those of the actual costs, which it imports from US-1610/L2 on (EP-09, "Le worker"), and those of
the indicators, which it imports from US-1670/L1 on (EP-10, "Le worker"). What the socles of EP-06,
EP-07, EP-09 and EP-10 register is named, so that the comparison is never between two empty lists.

How each registry acts is in ``test_registries_revisions`` (the closing, the marking, the
designation, the merge) and ``test_registries_extensions`` (the rest).
"""

import json
import subprocess
import sys

import pytest

from waterfall.core.revisions.interface import (
    CLOSING_STAGES,
)

# Each entry point, by the module that holds it.
ENTRY_POINTS = {
    "api": "waterfall.api.app",
    "worker": "waterfall.worker.main",
    "loader": "waterfall.witness.main",
}
# The registries only the loader of the witness reads.
WITNESS = "witness."
# What a process writes: the entries of each of its registries, each named by where it lives.
DUMP = """
import dataclasses, importlib, json, pkgutil, sys

from waterfall.platform.registry import registries


def named(entry):
    if isinstance(entry, str):
        return entry
    if isinstance(entry, tuple):
        return ":".join(named(part) for part in entry)
    if dataclasses.is_dataclass(entry):
        parts = ", ".join(named(getattr(entry, field.name)) for field in dataclasses.fields(entry))
        return f"{type(entry).__qualname__}({parts})"
    return f"{entry.__module__}.{getattr(entry, '__qualname__', type(entry).__qualname__)}"


for name in sys.argv[1:]:
    if name.endswith(".*"):
        package = importlib.import_module(name[:-2])
        for found in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            importlib.import_module(found.name)
    else:
        importlib.import_module(name)
held = {name: [named(entry) for entry in entries] for name, entries in registries().items()}
print(json.dumps(held))
"""
# The registry whose order of registration does not count across its stages (#2470).
CLOSING = "revisions.closing"
# The registries whose order of registration does not count at all: a format and an exporter are
# found by their kind, which has one at most — the actual costs, which the planning neither imports
# nor is imported by, register theirs before or after the planning's, as a process imports them.
BY_KIND = {"exchanges.formats", "exchanges.exporters"}
# Every registry of the core and of the witness EP-04, EP-06, EP-07, EP-08, EP-09 and EP-10 declare.
DECLARED = {
    "revisions.copy",
    "revisions.tasks_and_lines",
    "revisions.main_task",
    "revisions.indicators",
    "revisions.marking",
    "revisions.designation",
    "revisions.rate_update",
    "cost_settings.employment",
    CLOSING,
    "resource_settings.idle_task_guard",
    "resource_settings.recalculation",
    "projects.attachments",
    "projects.opening_main",
    "projects.estimate_facts",
    "projects.cost_facts",
    "planning.facets",
    "planning.open_lines",
    "planning.zeroed_at",
    "planning.physical_progress",
    "exchanges.formats",
    "exchanges.exporters",
    "witness.revision_fillers",
    "estimate.coverage",
    # EP-08 (US-2550/L1): the parts of a merge, and its end (US-2560/L1, #3946), the kinds of
    # entry another module undoes; what follows the counter of an own estimate (US-2570/L1), who
    # owns the provision lines a deletion or an import moves (US-2580/L1).
    "revisions.merge",
    "revisions.merge_end",
    "history.undoable",
    "revisions.own_estimate_counted",
    "planning.provision_owners",
    # EP-08: the update of a differential, its end (US-3050/L3); what risks designate (US-3060/L4).
    "revisions.rebase",
    "revisions.rebase_end",
    "projects.risk_designations",
}
PLANNING = "waterfall.core.planning.interface"
# What EP-06 registers (US-1380/L1, US-1390/L2), the copy of the nodes after the structures', and
# their redating after them.
REGISTERED = {
    "revisions.copy": [
        "waterfall.core.revisions.interface.structures.copy_structures",
        f"{PLANNING}.copying.copy_nodes",
        f"{PLANNING}.reference.redate_copy",
    ],
    "revisions.main_task": [f"{PLANNING}.borne_lines.structures_have_task"],
    "revisions.tasks_and_lines": [f"tasks:{PLANNING}.nodes.revision_has_tasks"],
    "resource_settings.idle_task_guard": [f"{PLANNING}.reference.tasks_left_idle"],
    "resource_settings.recalculation": [f"{PLANNING}.reference.reschedule_current_structures"],
    "projects.attachments": [
        (
            f"Attachments({PLANNING}.work_breakdown.work_breakdown_item_cited, "
            f"{PLANNING}.work_breakdown.detach_work_breakdown_item, "
            f"{PLANNING}.work_breakdown.hold_work_breakdown_items, "
            f"{PLANNING}.work_breakdown.share_work_breakdown_revision)"
        )
    ],
    "projects.opening_main": [f"{PLANNING}.skeleton.opening_main_with_tasks"],
    CLOSING: [
        "history:waterfall.core.history.interface.closing.close_history",
        f"content:{PLANNING}.closing.delete_nodes",
    ],
    "exchanges.formats": [f"ms_project_schedule:{PLANNING}.msproject.MsProjectFormat"],
    "exchanges.exporters": [
        f"ms_project_schedule:{PLANNING}.msproject.MsProjectExporter",
        f"task_tree_image:{PLANNING}.task_tree.TaskTreeExporter",
    ],
    "witness.revision_fillers": ["waterfall.witness.tasks.fill"],
}
ESTIMATE = "waterfall.core.estimate.interface"
CORE = "waterfall.core.estimate"
# The hooks of the facet of the lines, in the order of ``FacetHooks`` (US-1490/L3).
LINE_HOOKS = (
    f"{CORE}.reading.read_lines",
    f"{CORE}.copying.copy_lines",
    f"{ESTIMATE}.facet.delete_lines",
    f"{ESTIMATE}.facet.line_calendars",
    f"{ESTIMATE}.facet.line_roles",
    f"{CORE}.writing.create_line",
    f"{ESTIMATE}.facet.snapshot_lines",
    f"{ESTIMATE}.facet.restore_lines",
    f"{ESTIMATE}.facet.reinflate_lines",
    f"{CORE}.reading.totals_of",
    f"{CORE}.reading.filter_lines",
    f"{CORE}.reading.sort_lines",
    f"{ESTIMATE}.facet.line_dependencies",
    f"{ESTIMATE}.facet.judge_moved_lines",
    f"{CORE}.pasting.judge_line_cell",
    f"{CORE}.pasting.write_line_cell",
    "waterfall.core.cost_settings.records.share_natures",
    f"{CORE}.reading.line_columns",
    f"{CORE}.tallying.line_tallies",
    f"{CORE}.tallying.line_provisions",
    f"{CORE}.grafting.judge_grafted_lines",
    f"{CORE}.grafting.graft_lines",
    # The inert fields of a line (US-2250), a tuple, its names joined.
    "estimate_line.label:estimate_line.payment_delay_days:estimate_line.subproject_id",
)
# What the estimate answers the projects of its lines (US-1490/L4), in the order of
# ``EstimateFacts``.
FACTS = (
    f"{ESTIMATE}.employment.subproject_is_cited",
    f"{ESTIMATE}.employment.subproject_is_estimated",
    f"{ESTIMATE}.employment.subproject_estimate_lines",
    f"{ESTIMATE}.employment.forget_subproject",
    f"{ESTIMATE}.contributors.roles_employed",
    f"{ESTIMATE}.contributors.marked_revision_has_lines",
    f"{ESTIMATE}.rates.reinflate_project",
    f"{ESTIMATE}.rates.hold_revision",
)
# What the socle of EP-07 registers without effect (US-1490/L1), after the planning's, and the
# facet and the question of the lines US-1490/L3 registers; the registries of EP-07 come with
# their stories (decisions of 2026-11-08, #2370): the employment and the facts of the lines with
# US-1490/L4, the marking, the designation and the rates written with US-1500/L2.
REGISTERED_BY_EP07 = {
    "planning.facets": [f"estimate_line:FacetHooks({', '.join(LINE_HOOKS)})"],
    "revisions.tasks_and_lines": [f"lines:{ESTIMATE}.lines.revision_has_lines"],
    "revisions.copy": [f"{CORE}.keeping.copy_rates"],
    "revisions.rate_update": [f"{CORE}.keeping.rate_update_offered"],
    CLOSING: [f"content:{CORE}.keeping.close_rates"],
    "resource_settings.idle_task_guard": [f"{ESTIMATE}.calendars.idle_tasks_for_role_calendar"],
    "exchanges.formats": [f"estimate:{ESTIMATE}.excel.EstimateFormat"],
    "exchanges.exporters": [f"estimate:{ESTIMATE}.excel.EstimateExporter"],
    "witness.revision_fillers": ["waterfall.witness.estimate_lines.fill"],
    "cost_settings.employment": [
        f"{ESTIMATE}.employment.category_is_employed:{CORE}.repricing.reprice_after_rate"
    ],
    "projects.estimate_facts": [f"EstimateFacts({', '.join(FACTS)})"],
    "revisions.marking": [f"{ESTIMATE}.rates.keep_images"],
    "revisions.designation": [f"{ESTIMATE}.rates.refresh_budgeted"],
}
COSTS = "waterfall.core.costs.interface"
# What the socle of EP-09 registers without effect (US-1580/L1), each in the order it acts: the
# formats and the exporter of the remaining to commit and of the actual costs, by their kind; and
# what the actual costs answer the projects of a subproject (US-1610/L3), in the order of
# ``CostFacts``; and the own lines that hold a summary task open, which the estimate tells the
# planning (US-1590/L1), and when they were set to nought (US-1650/L2, #2803).
REGISTERED_BY_EP09 = {
    "projects.cost_facts": [
        (
            f"CostFacts({COSTS}.subprojects.subproject_has_actual_costs, "
            f"{COSTS}.subprojects.impute_waiting_lines)"
        )
    ],
    "exchanges.formats": [
        f"actual_costs:{COSTS}.actual_costs.ActualCostsFormat",
        f"remaining:{ESTIMATE}.remaining_excel.RemainingFormat",
    ],
    "exchanges.exporters": [f"remaining:{ESTIMATE}.remaining_excel.RemainingExporter"],
    "planning.open_lines": [f"{ESTIMATE}.kanban.open_lines"],
    "planning.zeroed_at": [f"{ESTIMATE}.kanban.zeroed_lines"],
}
RISKS = "waterfall.core.risks.following"
RISKS_CORE = "waterfall.core.risks"
# What the risks register (US-2570/L1): the copy of their evaluations after the copies of the rows
# they name, their deletion at an abandonment before the content of the revision, and what follows
# the counter of an own estimate; and what names the risks of the provision lines a deletion or an
# import moves, and follows them (US-2580/L1); the shares of the reserve a designation writes, and
# the coverage of the remaining to commit (US-2610/L1).
REGISTERED_BY_EP08 = {
    "estimate.coverage": [f"{RISKS_CORE}.interface.coverage.risk_coverage_of"],
    "revisions.designation": [f"{RISKS_CORE}.sharing.write_shares"],
    "revisions.copy": [f"{RISKS}.copy_evaluations"],
    CLOSING: [f"evaluations:{RISKS}.close_evaluations"],
    "revisions.own_estimate_counted": [f"{RISKS}.follow_own_estimate"],
    "planning.provision_owners": [
        f"ProvisionOwners({RISKS}.name_provision_owners, {RISKS}.follow_provision_lines)"
    ],
}
INDICATORS = "waterfall.core.indicators.interface"
# What the socle of EP-10 registers (US-1660/L1): what a marking keeps of the indicators, which
# US-1670/L1 fills; and the physical progress of the summaries a reading gives (US-1680).
REGISTERED_BY_EP10 = {
    "revisions.indicators": [f"{INDICATORS}.storing.store_indicators"],
    "planning.physical_progress": [f"{INDICATORS}.physical_progress.physical_progress"],
}


def before(*socles: dict[str, list[str]]) -> dict[str, set[str]]:
    """Give the entries the socles before one register, by registry."""
    held: dict[str, set[str]] = {}
    for socle in socles:
        for name, entries in socle.items():
            held.setdefault(name, set()).update(entries)
    return held


def as_run(name: str, entries: list[str]) -> list[str]:
    """Give the entries of a registry in the order they act.

    The closings run stage by stage whatever the order of the imports (``closers``), each stage in
    the order of its registrations: a process that imports the planning before the history holds
    the same closings, which run in the same order. The formats and the exporters are found by
    their kind, in any order.
    """
    if name in BY_KIND:
        return sorted(entries)
    if name != CLOSING:
        return entries
    return sorted(entries, key=lambda entry: CLOSING_STAGES.index(entry.split(":")[0]))


def registered_in(*modules: str) -> dict[str, list[str]]:
    """Give the registries of a process that imports these modules alone, by name, as they act."""
    result = subprocess.run(
        [sys.executable, "-c", DUMP, *modules],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    held: dict[str, list[str]] = json.loads(result.stdout)
    return {name: as_run(name, entries) for name, entries in held.items()}


@pytest.fixture(scope="module")
def everything() -> dict[str, list[str]]:
    """Give the registries of a process that imports every module of the core and the witness."""
    return registered_in("waterfall.core.*", "waterfall.witness.*")


def test_every_registry_holds_what_the_socle_of_ep06_registers(
    everything: dict[str, list[str]],
) -> None:
    assert set(everything) == DECLARED
    later = before(REGISTERED_BY_EP08)
    for name, entries in REGISTERED.items():
        held = [entry for entry in everything[name] if entry not in later.get(name, set())]
        if name in BY_KIND:
            assert set(entries) <= set(held), name
        else:
            assert held[: len(entries)] == entries, name


def test_every_registry_holds_what_the_socle_of_ep07_registers_after_the_planning(
    everything: dict[str, list[str]],
) -> None:
    # The extensions of the estimate, each after those of EP-06 in its registry; the marking and the
    # designation filled by US-1500/L2.
    others = before(REGISTERED, REGISTERED_BY_EP09, REGISTERED_BY_EP08)
    for name, entries in REGISTERED_BY_EP07.items():
        held = [entry for entry in everything[name] if entry not in others.get(name, set())]
        assert held == entries, name


def test_every_registry_holds_what_the_socle_of_ep09_registers_after_the_estimate(
    everything: dict[str, list[str]],
) -> None:
    # The extensions of the remaining to commit and of the actual costs, beside those of EP-06 and
    # EP-07; the remaining of the review before is no copy of its own: the copy of the lines writes
    # it (US-2240/L2), and the copy of the rates comes last. The risks answer the coverage
    # (``REGISTERED_BY_EP08``).
    others = before(REGISTERED, REGISTERED_BY_EP07, REGISTERED_BY_EP08)
    for name, entries in REGISTERED_BY_EP09.items():
        held = [entry for entry in everything[name] if entry not in others.get(name, set())]
        assert held == entries, name
    copies = everything["revisions.copy"]
    assert copies[copies.index(f"{RISKS}.copy_evaluations") - 1] == f"{CORE}.keeping.copy_rates"


def test_every_registry_holds_what_the_socle_of_ep10_registers_after_the_others(
    everything: dict[str, list[str]],
) -> None:
    # The indicators keep their part of a marking, beside the socles before them, first: the
    # portfolio keeps its own after (test_registries_portfolio). They alone answer the physical
    # progress of the summaries (US-1680).
    others = before(REGISTERED, REGISTERED_BY_EP07, REGISTERED_BY_EP08, REGISTERED_BY_EP09)
    for name, entries in REGISTERED_BY_EP10.items():
        held = [entry for entry in everything[name] if entry not in others.get(name, set())]
        assert held[: len(entries)] == entries, name


def test_every_registry_holds_what_the_risks_register_after_the_estimate(
    everything: dict[str, list[str]],
) -> None:
    # The evaluations are copied after the structures, the nodes and the lines whose copies they
    # name, last; deleted at an abandonment before the nodes and the structures, in their stage of
    # their own; and the risks alone follow the counter of an own estimate (US-2570/L1).
    others = before(REGISTERED, REGISTERED_BY_EP07, REGISTERED_BY_EP09, REGISTERED_BY_EP10)
    for name, entries in REGISTERED_BY_EP08.items():
        held = [entry for entry in everything[name] if entry not in others.get(name, set())]
        assert held == entries, name
    assert everything["revisions.copy"][-1] == f"{RISKS}.copy_evaluations"
    closings = everything[CLOSING]
    assert closings.index(f"evaluations:{RISKS}.close_evaluations") < closings.index(
        f"content:{PLANNING}.closing.delete_nodes"
    )


@pytest.mark.parametrize("entry_point", sorted(ENTRY_POINTS))
def test_each_entry_point_holds_every_extension_of_the_registries_it_reads(
    entry_point: str, everything: dict[str, list[str]]
) -> None:
    # The API and the worker read no registry of the witness; the loader reads them all. The worker
    # imports the interface of the estimate (US-1500/L2): nothing lacks, its marking keeps images;
    # that of the actual costs (US-1610/L2): it analyses and applies an extraction, and the import
    # of an estimate it applies asks whether a subproject bears costs; and that of the indicators
    # (US-1670/L1): its markings keep the indicators, as the API's and the loader's.
    held = registered_in(ENTRY_POINTS[entry_point])
    read = {
        name: entries
        for name, entries in everything.items()
        if entry_point == "loader" or not name.startswith(WITNESS)
    }
    assert {name: held.get(name) for name in read} == read
    assert held["projects.cost_facts"] == REGISTERED_BY_EP09["projects.cost_facts"]
    assert f"actual_costs:{COSTS}.actual_costs.ActualCostsFormat" in held["exchanges.formats"]
    assert held["revisions.indicators"][:1] == REGISTERED_BY_EP10["revisions.indicators"]
    assert held["planning.physical_progress"] == REGISTERED_BY_EP10["planning.physical_progress"]


def test_the_planning_then_the_estimate_take_their_part_of_a_merge_and_the_planning_its_end(
    everything: dict[str, list[str]],
) -> None:
    # What the planning and the estimate find of a merge, the planning's first, whose plan the
    # estimate reads; what the planning judges at its end, once (US-2560/L1, #3946).
    assert everything["revisions.merge"] == [
        f"{PLANNING}.merging.merge_tasks",
        f"{ESTIMATE}.merging.merge_lines",
    ]
    assert everything["revisions.merge_end"] == [f"{PLANNING}.merging.merge_end"]


def test_the_planning_then_the_estimate_take_their_part_of_an_update_and_the_planning_its_end(
    everything: dict[str, list[str]],
) -> None:
    # What the planning and the estimate find of the update of a differential, the planning's
    # first, whose plan the estimate reads; what the planning judges at its end, once, with the
    # calendars the estimate hands it (US-3050/L3).
    assert everything["revisions.rebase"] == [
        f"{PLANNING}.rebasing.rebase_tasks",
        f"{ESTIMATE}.rebasing.rebase_lines",
    ]
    assert everything["revisions.rebase_end"] == [f"{PLANNING}.rebasing.rebase_end"]
