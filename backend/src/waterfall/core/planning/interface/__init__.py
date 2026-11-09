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
from waterfall.core.planning.filters import (
    NodeFilters as NodeFilters,
)
from waterfall.core.planning.interface.closing import (
    delete_nodes as delete_nodes,
)

# ``facets`` (US-1380/L1; read by US-1380/L2; completed by US-1490/L3): the facets of a node
# other than the task (EP-07).
from waterfall.core.planning.interface.facets import (
    Amounts as Amounts,
)
from waterfall.core.planning.interface.facets import (
    BearingTask as BearingTask,
)
from waterfall.core.planning.interface.facets import (
    FacetCreation as FacetCreation,
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
    register_facet as register_facet,
)

# ``lines`` (US-1380/L1; US-1490/L3, L4): the lines of a task, their place, their writes, where
# they stand, for EP-07.
from waterfall.core.planning.interface.lines import (
    FacetChange as FacetChange,
)
from waterfall.core.planning.interface.lines import (
    NodeRow as NodeRow,
)
from waterfall.core.planning.interface.lines import (
    bearers_of as bearers_of,
)
from waterfall.core.planning.interface.lines import (
    create_line_node as create_line_node,
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
    node_revisions as node_revisions,
)
from waterfall.core.planning.interface.lines import (
    node_rows as node_rows,
)
from waterfall.core.planning.interface.lines import (
    revision_bears as revision_bears,
)
from waterfall.core.planning.interface.lines import (
    structures_of as structures_of,
)
from waterfall.core.planning.interface.lines import (
    write_facet as write_facet,
)

# ``msproject`` (US-1380/L1; US-1430/L3, L4): the format and the exporter of MS Project.
from waterfall.core.planning.interface.msproject import (
    MS_PROJECT_EXPORTER as MS_PROJECT_EXPORTER,
)
from waterfall.core.planning.interface.msproject import (
    MS_PROJECT_FORMAT as MS_PROJECT_FORMAT,
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
    copy_nodes as copy_nodes,
)
from waterfall.core.planning.interface.nodes import (
    create_node as create_node,
)
from waterfall.core.planning.interface.nodes import (
    delete_node as delete_node,
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
    load_task as load_task,
)
from waterfall.core.planning.interface.nodes import (
    move_nodes as move_nodes,
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

# ``progress`` (US-1380/L1; US-1410): the state of a task.
from waterfall.core.planning.interface.progress import (
    ProgressEntry as ProgressEntry,
)
from waterfall.core.planning.interface.progress import (
    ProgressLoad as ProgressLoad,
)
from waterfall.core.planning.interface.progress import (
    load_progress as load_progress,
)
from waterfall.core.planning.interface.progress import (
    set_task_progress as set_task_progress,
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
    opening_with_tasks as opening_with_tasks,
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

# ``structures`` (US-1380/L1; US-1380/L2, US-1390/L2): the dates, the start and the label.
from waterfall.core.planning.interface.structures import (
    StructureChange as StructureChange,
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
    work_breakdown_item_cited as work_breakdown_item_cited,
)
from waterfall.core.planning.interface.work_breakdown import (
    work_package_lines as work_package_lines,
)
from waterfall.core.planning.rescheduling import (
    Holding as Holding,
)
from waterfall.core.planning.scheduling import (
    Duration as Duration,
)
from waterfall.core.planning.scheduling import (
    WorkInstant as WorkInstant,
)
from waterfall.core.planning.views import (
    ConflictView as ConflictView,
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
    TaskView as TaskView,
)
from waterfall.core.planning.views import (
    TrackingView as TrackingView,
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
    register_opening_question,
)
from waterfall.core.resource_settings.interface import (
    register_idle_task_guard,
    register_recalculation,
)
from waterfall.core.revisions.interface import (
    register_closing,
    register_copy,
    register_tasks_and_lines,
)

# The registrations, once, at the import: the copy of the nodes after the structures', whose
# module this one imports first, and their redating after them; the nodes deleted after the
# history, by the stage of their part.
register_copy(copy_nodes)
register_copy(redate_copy)
register_tasks_and_lines("tasks", revision_has_tasks)
register_closing("content", delete_nodes)
register_idle_task_guard(tasks_left_idle)
register_recalculation(reschedule_current_structures)
register_attachments(Attachments(work_breakdown_item_cited, detach_work_breakdown_item))
register_opening_question(opening_with_tasks)
register_format("ms_project_schedule", MS_PROJECT_FORMAT)
register_exporter("ms_project_schedule", MS_PROJECT_EXPORTER)
register_exporter("task_tree_image", TASK_TREE_EXPORTER)
