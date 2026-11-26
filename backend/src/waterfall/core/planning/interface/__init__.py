# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning (FBS-4.3) offers to the API, the worker, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-06,
"Modules") is declared from US-1380/L1 on: it raises ``NotImplementedError`` naming the story that
fills it, but for those a registry calls before (the copy, the closing, the questions of the
revisions, the resource settings and the work breakdown), without effect until then. A name a
story adds besides joins the import of its file, below the comment that names it. Another module
imports them from here, never from the file; the engine (``scheduling``, US-1390/L1) is a
subpackage of its own.

The planning fills, at the import of this interface, the registries of the modules below it
(EP-06, "Les points d'extension"): the copy of a revision, the question of its tasks and its
closing (the revisions), the guard of the idle tasks and the recalculation (the resource
settings), the tasks attached to the work breakdown (the projects), the format and the exporters
of its kinds (the exchanges). The entry points that copy, designate, close a revision, change the
reference or run an exchange — the API, the worker, the loader of the witness — import it, by what
they serve or explicitly (#2180).
"""

# ``closing`` (US-1380/L1; US-1380/L2): the nodes of a revision abandoned.
# The registries the planning fills.
from waterfall.core.exchanges.interface import register_exporter, register_format

# Beside the interface (US-1380/L2): the calendar applicable to a task, what a reading of the tree
# retains, a duration and an instant of the engine, the frame of a write, the nodes as read.
from waterfall.core.planning.calendars import (
    Applicable as Applicable,
)

# Beside the interface (US-2340/L1): the constants of the units of the installation, which the
# difference of two durations of a comparison is counted by (``Duration.less``).
from waterfall.core.planning.dating import (
    constants_of as constants_of,
)
from waterfall.core.planning.entries import (
    ENTRIES as ENTRIES,
)
from waterfall.core.planning.filters import (
    NodeFilters as NodeFilters,
)

# ``borne_lines`` (US-2570/L1; US-2580/L1; US-2590/L2): the tasks a risk names, the provision line
# it asks for, brings back and moves, and the module that owns the lines a deletion or an import
# moves (EP-08).
from waterfall.core.planning.interface.borne_lines import (
    TaskNamed as TaskNamed,
)
from waterfall.core.planning.interface.borne_lines import (
    bearing_of as bearing_of,
)
from waterfall.core.planning.interface.borne_lines import (
    create_borne_line as create_borne_line,
)
from waterfall.core.planning.interface.borne_lines import (
    delete_borne_line as delete_borne_line,
)
from waterfall.core.planning.interface.borne_lines import (
    first_task as first_task,
)
from waterfall.core.planning.interface.borne_lines import (
    move_borne_line as move_borne_line,
)
from waterfall.core.planning.interface.borne_lines import (
    recreate_borne_line as recreate_borne_line,
)
from waterfall.core.planning.interface.borne_lines import (
    structures_have_task as structures_have_task,
)
from waterfall.core.planning.interface.borne_lines import (
    task_of as task_of,
)
from waterfall.core.planning.interface.borne_lines import (
    task_of_lineage as task_of_lineage,
)
from waterfall.core.planning.interface.closing import (
    delete_nodes as delete_nodes,
)
from waterfall.core.planning.interface.closing import (
    delete_structure_nodes as delete_structure_nodes,
)

# ``closing`` (US-2590/L2): the nodes of a structure kept whole, and written back.
from waterfall.core.planning.interface.closing import (
    restore_structure_nodes as restore_structure_nodes,
)
from waterfall.core.planning.interface.closing import (
    structure_node_ids as structure_node_ids,
)
from waterfall.core.planning.interface.closing import (
    structure_nodes as structure_nodes,
)

# ``copying`` (US-1380/L2; moved out of ``nodes`` and written as one statement a table by
# US-2240/L2): the copy of the nodes of a revision opened from a marked one.
from waterfall.core.planning.interface.copying import (
    copy_links as copy_links,
)
from waterfall.core.planning.interface.copying import (
    copy_nodes as copy_nodes,
)
from waterfall.core.planning.interface.copying import (
    copy_structure_nodes as copy_structure_nodes,
)

# ``differential_deletion`` (US-2550/L4): a differential abandoned.
from waterfall.core.planning.interface.differential_deletion import (
    abandon_differential as abandon_differential,
)

# ``facets`` (US-1380/L1; read by US-1380/L2; completed by US-1490/L3, US-2260/L3, US-2280/L1,
# US-2400/L1): the facets of a node other than the task (EP-07).
from waterfall.core.planning.interface.facets import (
    Amounts as Amounts,
)
from waterfall.core.planning.interface.facets import (
    BearingTask as BearingTask,
)
from waterfall.core.planning.interface.facets import (
    CellRefusal as CellRefusal,
)
from waterfall.core.planning.interface.facets import (
    CellsJudged as CellsJudged,
)
from waterfall.core.planning.interface.facets import (
    CellsPasted as CellsPasted,
)
from waterfall.core.planning.interface.facets import (
    FacetColumns as FacetColumns,
)
from waterfall.core.planning.interface.facets import (
    FacetCreation as FacetCreation,
)
from waterfall.core.planning.interface.facets import (
    FacetGraft as FacetGraft,
)
from waterfall.core.planning.interface.facets import (
    FacetHooks as FacetHooks,
)
from waterfall.core.planning.interface.facets import (
    FacetRead as FacetRead,
)
from waterfall.core.planning.interface.facets import (
    FacetState as FacetState,
)
from waterfall.core.planning.interface.facets import (
    FacetWrite as FacetWrite,
)
from waterfall.core.planning.interface.facets import (
    LineSort as LineSort,
)
from waterfall.core.planning.interface.facets import (
    RepricedBeyondColumnError as RepricedBeyondColumnError,
)
from waterfall.core.planning.interface.facets import (
    Tally as Tally,
)
from waterfall.core.planning.interface.facets import (
    calendar_of as calendar_of,
)
from waterfall.core.planning.interface.facets import (
    calendars_of as calendars_of,
)
from waterfall.core.planning.interface.facets import (
    facets as facets,
)
from waterfall.core.planning.interface.facets import (
    named_calendars as named_calendars,
)
from waterfall.core.planning.interface.facets import (
    refused_at as refused_at,
)
from waterfall.core.planning.interface.facets import (
    register_facet as register_facet,
)

# ``grafts`` (US-2620/L1; US-2620/L2): the tasks of a structure grafted into another (EP-08).
from waterfall.core.planning.interface.grafts import (
    Graft as Graft,
)
from waterfall.core.planning.interface.grafts import (
    Grafted as Grafted,
)
from waterfall.core.planning.interface.grafts import (
    graft as graft,
)
from waterfall.core.planning.interface.grafts import (
    release_origin as release_origin,
)

# ``indicator_stamps`` (US-1660/L3; US-1720/L2): what the key of the cache of the indicators reads.
from waterfall.core.planning.interface.indicator_stamps import (
    ContentStamp as ContentStamp,
)
from waterfall.core.planning.interface.indicator_stamps import (
    revision_content_stamp as revision_content_stamp,
)

# ``indicator_tasks`` (US-1660/L3): the tasks of a revision as the indicators read them.
from waterfall.core.planning.interface.indicator_tasks import (
    IndicatorTask as IndicatorTask,
)
from waterfall.core.planning.interface.indicator_tasks import (
    tasks_for_indicators as tasks_for_indicators,
)

# ``kept_readings`` (US-2270/L1): the reading of a structure of a marked revision, kept.
from waterfall.core.planning.interface.kept_readings import (
    KeptReading as KeptReading,
)
from waterfall.core.planning.interface.kept_readings import (
    keep_reading as keep_reading,
)
from waterfall.core.planning.interface.kept_readings import (
    kept_reading as kept_reading,
)

# ``lines`` (US-1380/L1; US-1490/L3, L4; US-1550/L3): the lines of a task, their place, their
# writes, where they stand, their counters, the write of an import, for EP-07.
from waterfall.core.planning.interface.lines import (
    FacetChange as FacetChange,
)
from waterfall.core.planning.interface.lines import (
    LineJudged as LineJudged,
)
from waterfall.core.planning.interface.lines import (
    LinesWrite as LinesWrite,
)
from waterfall.core.planning.interface.lines import (
    NodeRow as NodeRow,
)
from waterfall.core.planning.interface.lines import (
    bearers_of as bearers_of,
)
from waterfall.core.planning.interface.lines import (
    bearing_tasks as bearing_tasks,
)
from waterfall.core.planning.interface.lines import (
    create_line_node as create_line_node,
)
from waterfall.core.planning.interface.lines import (
    judge_bearer as judge_bearer,
)
from waterfall.core.planning.interface.lines import (
    judge_line_creation as judge_line_creation,
)
from waterfall.core.planning.interface.lines import (
    line_nodes_of as line_nodes_of,
)
from waterfall.core.planning.interface.lines import (
    lineages_of as lineages_of,
)
from waterfall.core.planning.interface.lines import (
    lines_of as lines_of,
)
from waterfall.core.planning.interface.lines import (
    lines_of_revision as lines_of_revision,
)
from waterfall.core.planning.interface.lines import (
    lines_of_structure as lines_of_structure,
)
from waterfall.core.planning.interface.lines import (
    lines_of_structures as lines_of_structures,
)
from waterfall.core.planning.interface.lines import (
    new_line_node as new_line_node,
)
from waterfall.core.planning.interface.lines import (
    node_revisions as node_revisions,
)
from waterfall.core.planning.interface.lines import (
    node_rows as node_rows,
)
from waterfall.core.planning.interface.lines import (
    node_versions as node_versions,
)
from waterfall.core.planning.interface.lines import (
    outside_bases as outside_bases,
)
from waterfall.core.planning.interface.lines import (
    revision_bears as revision_bears,
)
from waterfall.core.planning.interface.lines import (
    revision_lines as revision_lines,
)
from waterfall.core.planning.interface.lines import (
    structures_of as structures_of,
)
from waterfall.core.planning.interface.lines import (
    write_facet as write_facet,
)
from waterfall.core.planning.interface.lines import (
    write_line_node as write_line_node,
)
from waterfall.core.planning.interface.lines import (
    write_lines as write_lines,
)

# ``loading`` (US-1480/L2; US-1570/L2): the tasks and the lines of the witness, a revision's tree
# reconciled with them.
from waterfall.core.planning.interface.loading import (
    DatesDisagreeing as DatesDisagreeing,
)
from waterfall.core.planning.interface.loading import (
    LineNodeLoad as LineNodeLoad,
)
from waterfall.core.planning.interface.loading import (
    LinkLoad as LinkLoad,
)
from waterfall.core.planning.interface.loading import (
    ParentAbsentError as ParentAbsentError,
)
from waterfall.core.planning.interface.loading import (
    ParentageLoopError as ParentageLoopError,
)
from waterfall.core.planning.interface.loading import (
    TaskLoad as TaskLoad,
)
from waterfall.core.planning.interface.loading import (
    TasksLoad as TasksLoad,
)
from waterfall.core.planning.interface.loading import (
    load_line_nodes as load_line_nodes,
)
from waterfall.core.planning.interface.loading import (
    load_tasks as load_tasks,
)

# ``merging`` (US-2560/L1): the part of the planning in the merge of a differential, its end, and
# where the lines stand for the estimate's; the nodes of the lines it writes, and the merge of the
# witness (US-2560/L2); the tasks whose lines a merge writes, told by the estimate (US-3100/L1).
from waterfall.core.planning.interface.merging import (
    MergedLine as MergedLine,
)
from waterfall.core.planning.interface.merging import (
    MergedLines as MergedLines,
)
from waterfall.core.planning.interface.merging import (
    lines_in_order as lines_in_order,
)
from waterfall.core.planning.interface.merging import (
    load_merge as load_merge,
)
from waterfall.core.planning.interface.merging import (
    merge_bearing as merge_bearing,
)
from waterfall.core.planning.interface.merging import (
    merge_end as merge_end,
)
from waterfall.core.planning.interface.merging import (
    merge_lines_worked as merge_lines_worked,
)
from waterfall.core.planning.interface.merging import (
    merge_tasks as merge_tasks,
)
from waterfall.core.planning.interface.merging import (
    merged_lines as merged_lines,
)
from waterfall.core.planning.interface.merging import (
    place_merged_lines as place_merged_lines,
)

# ``milestone_dates`` (US-1660/L3; US-1710): the dates of the milestones in the revisions.
from waterfall.core.planning.interface.milestone_dates import (
    milestone_forecasts as milestone_forecasts,
)
from waterfall.core.planning.interface.milestone_dates import (
    tracked_milestones as tracked_milestones,
)

# ``msproject`` (US-1380/L1; US-1430/L3, L4): the format and the exporter of MS Project.
from waterfall.core.planning.interface.msproject import (
    MS_PROJECT_EXPORTER as MS_PROJECT_EXPORTER,
)
from waterfall.core.planning.interface.msproject import (
    MS_PROJECT_FORMAT as MS_PROJECT_FORMAT,
)
from waterfall.core.planning.interface.node_deletion import (
    delete_node as delete_node,
)

# ``nodes`` (US-1380/L1; US-1380/L2, L3; US-1480/L2; US-1450/L5): the nodes of a structure.
from waterfall.core.planning.interface.nodes import (
    CreationJudged as CreationJudged,
)
from waterfall.core.planning.interface.nodes import (
    Dependencies as Dependencies,
)
from waterfall.core.planning.interface.nodes import (
    DependencyRow as DependencyRow,
)
from waterfall.core.planning.interface.nodes import (
    Ground as Ground,
)
from waterfall.core.planning.interface.nodes import (
    InstantSent as InstantSent,
)
from waterfall.core.planning.interface.nodes import (
    NodeCreation as NodeCreation,
)
from waterfall.core.planning.interface.nodes import (
    NodeList as NodeList,
)
from waterfall.core.planning.interface.nodes import (
    NodeMoving as NodeMoving,
)
from waterfall.core.planning.interface.nodes import (
    RowResolution as RowResolution,
)
from waterfall.core.planning.interface.nodes import (
    TaskEntry as TaskEntry,
)
from waterfall.core.planning.interface.nodes import (
    apply_cell as apply_cell,
)
from waterfall.core.planning.interface.nodes import (
    computed_value_dependencies as computed_value_dependencies,
)
from waterfall.core.planning.interface.nodes import (
    create_node as create_node,
)
from waterfall.core.planning.interface.nodes import (
    describe_row as describe_row,
)
from waterfall.core.planning.interface.nodes import (
    judge_cell as judge_cell,
)
from waterfall.core.planning.interface.nodes import (
    judge_creation as judge_creation,
)
from waterfall.core.planning.interface.nodes import (
    list_nodes as list_nodes,
)
from waterfall.core.planning.interface.nodes import (
    move_nodes as move_nodes,
)
from waterfall.core.planning.interface.nodes import (
    read_defaults as read_defaults,
)
from waterfall.core.planning.interface.nodes import (
    resolve_row_number as resolve_row_number,
)
from waterfall.core.planning.interface.nodes import (
    revision_has_tasks as revision_has_tasks,
)
from waterfall.core.planning.interface.nodes import (
    traced as traced,
)
from waterfall.core.planning.interface.nodes import (
    traced_creation as traced_creation,
)
from waterfall.core.planning.interface.nodes import (
    update_task_facet as update_task_facet,
)
from waterfall.core.planning.interface.nodes import (
    write_cell as write_cell,
)
from waterfall.core.planning.interface.nodes import (
    write_creation as write_creation,
)

# ``open_lines`` (US-1590/L1; US-1650/L2): the own lines that hold a summary task open, and when
# they were set to nought, which the estimate tells.
from waterfall.core.planning.interface.open_lines import (
    OpenLines as OpenLines,
)
from waterfall.core.planning.interface.open_lines import (
    ZeroedAt as ZeroedAt,
)
from waterfall.core.planning.interface.open_lines import (
    held_open as held_open,
)
from waterfall.core.planning.interface.open_lines import (
    register_open_lines as register_open_lines,
)
from waterfall.core.planning.interface.open_lines import (
    register_zeroed_at as register_zeroed_at,
)
from waterfall.core.planning.interface.open_lines import (
    zeroed_at as zeroed_at,
)

# ``paste`` (US-1380/L1; US-1450/L2): the paste of a block of cells.
from waterfall.core.planning.interface.paste import (
    PasteApplied as PasteApplied,
)
from waterfall.core.planning.interface.paste import (
    PasteBlock as PasteBlock,
)
from waterfall.core.planning.interface.paste import (
    PasteConfirmation as PasteConfirmation,
)
from waterfall.core.planning.interface.paste import (
    PastePlanned as PastePlanned,
)
from waterfall.core.planning.interface.paste import (
    PasteRefusal as PasteRefusal,
)
from waterfall.core.planning.interface.paste import (
    apply_paste as apply_paste,
)
from waterfall.core.planning.interface.paste import (
    preview_paste as preview_paste,
)

# ``physical_progress`` (US-1660/L3; US-1680): the physical progress of the summary tasks.
from waterfall.core.planning.interface.physical_progress import (
    PhysicalProgress as PhysicalProgress,
)
from waterfall.core.planning.interface.physical_progress import (
    PhysicalShare as PhysicalShare,
)
from waterfall.core.planning.interface.physical_progress import (
    ProgressTask as ProgressTask,
)
from waterfall.core.planning.interface.physical_progress import (
    SummariesAsked as SummariesAsked,
)
from waterfall.core.planning.interface.physical_progress import (
    earnable_amounts as earnable_amounts,
)
from waterfall.core.planning.interface.physical_progress import (
    physical_progress_of as physical_progress_of,
)
from waterfall.core.planning.interface.physical_progress import (
    register_physical_progress as register_physical_progress,
)

# ``predecessors`` (US-1380/L1; US-1390/L2): the predecessors of a task.
from waterfall.core.planning.interface.predecessors import (
    PredecessorSent as PredecessorSent,
)
from waterfall.core.planning.interface.predecessors import (
    PredecessorsEntry as PredecessorsEntry,
)
from waterfall.core.planning.interface.predecessors import (
    set_predecessors as set_predecessors,
)

# ``progress`` (US-1380/L1; US-1410; US-1580/L2; US-1590/L1): the state of a task, its completion
# by the re-estimate that sets its last open line to nought (``write_remaining``), the gestures of
# a card of the Kanban (``progress_commands``).
from waterfall.core.planning.interface.progress import (
    KanbanCommand as KanbanCommand,
)
from waterfall.core.planning.interface.progress import (
    KanbanCommandAvailability as KanbanCommandAvailability,
)
from waterfall.core.planning.interface.progress import (
    KanbanCondition as KanbanCondition,
)
from waterfall.core.planning.interface.progress import (
    ProgressEntry as ProgressEntry,
)
from waterfall.core.planning.interface.progress import (
    ProgressLoad as ProgressLoad,
)
from waterfall.core.planning.interface.progress import (
    RemainingChange as RemainingChange,
)
from waterfall.core.planning.interface.progress import (
    TaskProgress as TaskProgress,
)
from waterfall.core.planning.interface.progress import (
    load_progress as load_progress,
)
from waterfall.core.planning.interface.progress import (
    progress_commands as progress_commands,
)
from waterfall.core.planning.interface.progress import (
    set_task_progress as set_task_progress,
)
from waterfall.core.planning.interface.progress import (
    write_remaining as write_remaining,
)

# ``rebased`` (US-3050/L4): a differential updated from the main structure, and for the witness.
from waterfall.core.planning.interface.rebased import (
    load_rebase as load_rebase,
)
from waterfall.core.planning.interface.rebased import (
    rebase_differential as rebase_differential,
)

# ``rebasing`` (US-3050/L3): the part of the planning in the update of a differential, its end,
# what a structure designates, and where the lines stand for the estimate's.
from waterfall.core.planning.interface.rebasing import (
    Gap as Gap,
)
from waterfall.core.planning.interface.rebasing import (
    LinesPlaced as LinesPlaced,
)
from waterfall.core.planning.interface.rebasing import (
    RebasedLines as RebasedLines,
)
from waterfall.core.planning.interface.rebasing import (
    RebasedTask as RebasedTask,
)
from waterfall.core.planning.interface.rebasing import (
    designated as designated,
)
from waterfall.core.planning.interface.rebasing import (
    hand_calendars as hand_calendars,
)
from waterfall.core.planning.interface.rebasing import (
    place_rebased_lines as place_rebased_lines,
)
from waterfall.core.planning.interface.rebasing import (
    rebase_end as rebase_end,
)
from waterfall.core.planning.interface.rebasing import (
    rebase_tasks as rebase_tasks,
)
from waterfall.core.planning.interface.rebasing import (
    rebased_lines as rebased_lines,
)

# ``reference`` (US-1380/L1; US-1390/L2): what the planning answers to the reference.
from waterfall.core.planning.interface.reference import (
    redate_copy as redate_copy,
)
from waterfall.core.planning.interface.reference import (
    reschedule_current_structures as reschedule_current_structures,
)
from waterfall.core.planning.interface.reference import (
    tasks_left_idle as tasks_left_idle,
)

# ``skeleton`` (US-1380/L1; US-1460): the skeleton engendered from the work breakdown.
from waterfall.core.planning.interface.skeleton import (
    generate_skeleton as generate_skeleton,
)
from waterfall.core.planning.interface.skeleton import (
    opening_main_with_tasks as opening_main_with_tasks,
)

# ``snapshots`` (US-1380/L1; US-1380/L2, US-1450/L2): the snapshots the history keeps, restored.
from waterfall.core.planning.interface.snapshots import (
    UndoDone as UndoDone,
)
from waterfall.core.planning.interface.snapshots import (
    redo_last_undo as redo_last_undo,
)
from waterfall.core.planning.interface.snapshots import (
    restore as restore,
)
from waterfall.core.planning.interface.snapshots import (
    snapshot as snapshot,
)
from waterfall.core.planning.interface.snapshots import (
    undo_last_change as undo_last_change,
)

# ``structures`` (US-2650/L1): a differential of the witness opened under its identifiers.
from waterfall.core.planning.interface.structures import (
    DifferentialLoad as DifferentialLoad,
)

# ``structures`` (US-3070/L3): the own estimate of a risk opened whole, with its base; copied again
# for the witness.
from waterfall.core.planning.interface.structures import (
    OwnEstimateOpening as OwnEstimateOpening,
)

# ``structures`` (US-1380/L1; US-1380/L2, US-1390/L2): the dates, the start and the label.
from waterfall.core.planning.interface.structures import (
    StructureChange as StructureChange,
)
from waterfall.core.planning.interface.structures import (
    load_differential as load_differential,
)
from waterfall.core.planning.interface.structures import (
    load_own_estimate_again as load_own_estimate_again,
)
from waterfall.core.planning.interface.structures import (
    open_differential as open_differential,
)
from waterfall.core.planning.interface.structures import (
    open_own_estimate as open_own_estimate,
)
from waterfall.core.planning.interface.structures import (
    reschedule as reschedule,
)
from waterfall.core.planning.interface.structures import (
    structure_state as structure_state,
)
from waterfall.core.planning.interface.structures import (
    update_cost_structure as update_cost_structure,
)

# ``task_tree`` (US-1380/L1; US-1440/L2): the exporter of the image of the task tree.
from waterfall.core.planning.interface.task_tree import (
    TASK_TREE_EXPORTER as TASK_TREE_EXPORTER,
)

# ``timelines`` (US-1380/L1; US-1400/L1): the named timelines of a project.
from waterfall.core.planning.interface.timelines import (
    TimelineView as TimelineView,
)
from waterfall.core.planning.interface.timelines import (
    create_timeline as create_timeline,
)
from waterfall.core.planning.interface.timelines import (
    delete_timeline as delete_timeline,
)
from waterfall.core.planning.interface.timelines import (
    list_timelines as list_timelines,
)
from waterfall.core.planning.interface.timelines import (
    load_timeline as load_timeline,
)
from waterfall.core.planning.interface.timelines import (
    timelines_present as timelines_present,
)

# ``tracking`` (US-1380/L1; US-1400/L2): the inscriptions of a task.
from waterfall.core.planning.interface.tracking import (
    TrackingChange as TrackingChange,
)
from waterfall.core.planning.interface.tracking import (
    TrackingLoad as TrackingLoad,
)
from waterfall.core.planning.interface.tracking import (
    TrackingSent as TrackingSent,
)
from waterfall.core.planning.interface.tracking import (
    load_tracking as load_tracking,
)
from waterfall.core.planning.interface.tracking import (
    set_node_tracking as set_node_tracking,
)

# ``work_breakdown`` (US-1380/L1; US-1380/L3): the tasks attached to the work breakdown.
from waterfall.core.planning.interface.work_breakdown import (
    detach_work_breakdown_item as detach_work_breakdown_item,
)
from waterfall.core.planning.interface.work_breakdown import (
    hold_work_breakdown_items as hold_work_breakdown_items,
)
from waterfall.core.planning.interface.work_breakdown import (
    share_work_breakdown_revision as share_work_breakdown_revision,
)
from waterfall.core.planning.interface.work_breakdown import (
    work_breakdown_item_cited as work_breakdown_item_cited,
)
from waterfall.core.planning.interface.work_breakdown import (
    work_package_lines as work_package_lines,
)

# Beside the interface (US-2580/L1): what names the risk of a provision line and follows its report.
from waterfall.core.planning.provisioning import (
    ProvisionOwner as ProvisionOwner,
)
from waterfall.core.planning.provisioning import (
    ProvisionOwners as ProvisionOwners,
)
from waterfall.core.planning.provisioning import (
    register_provision_owners as register_provision_owners,
)

# Beside the interface (US-1530; US-2220/L2): a structure read whole, and what a reading's filters
# retain of it; a reading of a structure, its nodes as flat records, which the API writes the body
# of ``listNodes`` from, and a node as it is read made a record (``record_of``, with the views).
from waterfall.core.planning.reading import (
    NodeRecords as NodeRecords,
)
from waterfall.core.planning.reading import (
    StructureRead as StructureRead,
)
from waterfall.core.planning.reading import (
    list_records as list_records,
)
from waterfall.core.planning.reading import (
    read_structure as read_structure,
)

# Beside the interface: what a write of the tree hands the replay of the engine (#2492).
from waterfall.core.planning.rescheduling import (
    Holding as Holding,
)

# Beside the interface (US-1570/L5, #2549): a calendar of a week and its count of the hours of work,
# which the estimate spreads a line on.
from waterfall.core.planning.scheduling import (
    Calendar as Calendar,
)
from waterfall.core.planning.scheduling import (
    Duration as Duration,
)
from waterfall.core.planning.scheduling import (
    DurationUnit as DurationUnit,
)
from waterfall.core.planning.scheduling import (
    UnitConstants as UnitConstants,
)
from waterfall.core.planning.scheduling import (
    WorkInstant as WorkInstant,
)
from waterfall.core.planning.scheduling import (
    weekly_calendar as weekly_calendar,
)
from waterfall.core.planning.views import (
    ConflictView as ConflictView,
)
from waterfall.core.planning.views import (
    FacetRecord as FacetRecord,
)
from waterfall.core.planning.views import (
    NodeRecord as NodeRecord,
)
from waterfall.core.planning.views import (
    NodeView as NodeView,
)
from waterfall.core.planning.views import (
    PredecessorView as PredecessorView,
)
from waterfall.core.planning.views import (
    ScheduleView as ScheduleView,
)
from waterfall.core.planning.views import (
    TaskRecord as TaskRecord,
)
from waterfall.core.planning.views import (
    TaskView as TaskView,
)
from waterfall.core.planning.views import (
    TrackingView as TrackingView,
)
from waterfall.core.planning.views import (
    record_of as record_of,
)
from waterfall.core.planning.writing import (
    InflationView as InflationView,
)
from waterfall.core.planning.writing import (
    NodesWritten as NodesWritten,
)
from waterfall.core.planning.writing import (
    Place as Place,
)
from waterfall.core.planning.writing import (
    StructureTotals as StructureTotals,
)
from waterfall.core.planning.writing import (
    Writer as Writer,
)
from waterfall.core.projects.interface import (
    Attachments,
    register_attachments,
    register_opening_main_question,
)
from waterfall.core.resource_settings.interface import (
    register_idle_task_guard,
    register_recalculation,
)
from waterfall.core.revisions.interface import (
    register_closing,
    register_copy,
    register_main_task_question,
    register_merge,
    register_merge_end,
    register_rebase,
    register_rebase_end,
    register_tasks_and_lines,
)

# The registrations, once, at the import: the copy of the nodes after the structures', whose
# module this one imports first, and their redating after them; the nodes deleted after the
# history, by the stage of their part; its part of a merge, before the estimate's, and the end of
# a merge, judged on the structure all the parts leave (US-2560/L1); likewise for the update of a
# differential (US-3050/L3).
register_copy(copy_nodes)
register_copy(redate_copy)
register_tasks_and_lines("tasks", revision_has_tasks)
register_closing("content", delete_nodes)
register_idle_task_guard(tasks_left_idle)
register_recalculation(reschedule_current_structures)
register_attachments(
    Attachments(
        work_breakdown_item_cited,
        detach_work_breakdown_item,
        hold_work_breakdown_items,
        share_work_breakdown_revision,
    )
)
register_opening_main_question(opening_main_with_tasks)
register_main_task_question(structures_have_task)
register_format("ms_project_schedule", MS_PROJECT_FORMAT)
register_exporter("ms_project_schedule", MS_PROJECT_EXPORTER)
register_exporter("task_tree_image", TASK_TREE_EXPORTER)
register_merge(merge_tasks)
register_merge_end(merge_end)
register_rebase(rebase_tasks)
register_rebase_end(rebase_end)
