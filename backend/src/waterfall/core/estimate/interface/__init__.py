# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the estimate (FBS-4.4) offers to the API, the worker, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-07,
"Modules") is declared from US-1490/L1 on: it raises ``NotImplementedError`` naming the story that
fills it, but for those a registry calls before, without effect until then. A name a story adds
besides joins the import of its file, below the comment that names it. Another module imports them
from here, never from the file; the pure computations — the amount of a line (``pricing``) and the
spreading of a load (``spreading``) — are subpackages of their own, whose names other modules read
here.

The estimate fills, at the import of this interface, the registries of the modules below it
(EP-07, "Les points d'extension"), none of which imports it. The socle registers without effect
what the registries of EP-04 and EP-06 call — the copy and the closing of a revision, the guard
of the idle tasks, the format and the exporter ``estimate`` —; US-1490/L3 registers the facet
``estimate_line`` (``register_facet``), whose hooks the planning asks for every line it reads,
creates, copies, snapshots, restores and redates, and the question of the lines
(``register_tasks_and_lines``); US-1500/L1 fills the copy and the closing of the rates, and
registers the question of their proposal (``register_rate_update``); the registries EP-07
declares (``register_marking``, ``register_designation``, ``register_employment``,
``register_estimate_facts``) by the stories that fill them (decisions of 2026-11-08, #2370):
US-1490/L4 the employment of the categories and the facts of the lines the projects ask, whose
roles employed and pricing again of a project come with US-1540 and US-1500. The entry points that
copy, mark, designate or close a revision, change the reference or run an exchange — the API, the
worker from US-1500 on, the loader of the witness —
import it, by what they serve or explicitly (#2180).
"""

# The registry of the cost settings the estimate fills (US-1490/L4); the others below.
from waterfall.core.cost_settings.interface import register_employment

# ``calendars`` (US-1490/L1; US-1500): the calendars of the roles, which a change must not idle.
# ``entries`` (US-1490/L3): what a write sends of a line.
from waterfall.core.estimate.entries import (
    LineEntry as LineEntry,
)
from waterfall.core.estimate.interface.calendars import (
    idle_tasks_for_role_calendar as idle_tasks_for_role_calendar,
)

# ``comparison`` (US-1490/L1; US-1530): the comparison of two revisions.
from waterfall.core.estimate.interface.comparison import (
    compare_revisions as compare_revisions,
)

# ``contributors`` (US-1490/L1; US-1540): the roles the lines employ.
from waterfall.core.estimate.interface.contributors import (
    roles_employed as roles_employed,
)

# ``employment`` (US-1490/L1; US-1490/L4): what the lines employ of the reference and the project.
from waterfall.core.estimate.interface.employment import (
    category_is_employed as category_is_employed,
)
from waterfall.core.estimate.interface.employment import (
    subproject_estimate_lines as subproject_estimate_lines,
)
from waterfall.core.estimate.interface.employment import (
    subproject_is_cited as subproject_is_cited,
)
from waterfall.core.estimate.interface.employment import (
    subproject_is_estimated as subproject_is_estimated,
)

# ``excel`` (US-1490/L1; US-1550): the format and the exporter of the workbook of an estimate.
from waterfall.core.estimate.interface.excel import (
    ESTIMATE_EXPORTER as ESTIMATE_EXPORTER,
)
from waterfall.core.estimate.interface.excel import (
    ESTIMATE_FORMAT as ESTIMATE_FORMAT,
)
from waterfall.core.estimate.interface.excel import (
    EstimateExporter as EstimateExporter,
)
from waterfall.core.estimate.interface.excel import (
    EstimateFormat as EstimateFormat,
)
from waterfall.core.estimate.interface.excel import (
    sheet_name as sheet_name,
)

# ``facet`` (US-1490/L1; US-1490/L3): the facet estimate line, as the planning asks it.
from waterfall.core.estimate.interface.facet import (
    LINE_FACET as LINE_FACET,
)
from waterfall.core.estimate.interface.facet import (
    copy_lines as copy_lines,
)
from waterfall.core.estimate.interface.facet import (
    create_line as create_line,
)
from waterfall.core.estimate.interface.facet import (
    delete_lines as delete_lines,
)
from waterfall.core.estimate.interface.facet import (
    judge_line_cell as judge_line_cell,
)
from waterfall.core.estimate.interface.facet import (
    judge_moved_lines as judge_moved_lines,
)
from waterfall.core.estimate.interface.facet import (
    line_calendars as line_calendars,
)
from waterfall.core.estimate.interface.facet import (
    line_dependencies as line_dependencies,
)
from waterfall.core.estimate.interface.facet import (
    line_filters as line_filters,
)
from waterfall.core.estimate.interface.facet import (
    line_sort as line_sort,
)
from waterfall.core.estimate.interface.facet import (
    line_totals as line_totals,
)
from waterfall.core.estimate.interface.facet import (
    read_lines as read_lines,
)
from waterfall.core.estimate.interface.facet import (
    reinflate_lines as reinflate_lines,
)
from waterfall.core.estimate.interface.facet import (
    restore_lines as restore_lines,
)
from waterfall.core.estimate.interface.facet import (
    snapshot_lines as snapshot_lines,
)

# ``indicators`` (US-1490/L1; US-1510): the indicators of an estimate and the rates it lacks.
from waterfall.core.estimate.interface.indicators import (
    estimate_indicators as estimate_indicators,
)
from waterfall.core.estimate.interface.indicators import (
    missing_rates as missing_rates,
)

# ``lines`` (US-1490/L1; US-1490/L3, US-1570): a line changed, the question of the designation.
from waterfall.core.estimate.interface.lines import (
    load_lines as load_lines,
)
from waterfall.core.estimate.interface.lines import (
    revision_has_lines as revision_has_lines,
)
from waterfall.core.estimate.interface.lines import (
    update_line as update_line,
)

# ``rates`` (US-1490/L1; US-1500): the rates of a revision and what it keeps of the reference.
from waterfall.core.estimate.interface.rates import (
    apply_rate_update as apply_rate_update,
)
from waterfall.core.estimate.interface.rates import (
    keep_images as keep_images,
)
from waterfall.core.estimate.interface.rates import (
    rate_update_proposal as rate_update_proposal,
)
from waterfall.core.estimate.interface.rates import (
    refresh_budgeted as refresh_budgeted,
)
from waterfall.core.estimate.interface.rates import (
    reinflate_project as reinflate_project,
)

# ``workload`` (US-1490/L1; US-1520): the workload of an estimate.
from waterfall.core.estimate.interface.workload import (
    workload as workload,
)

# ``keeping`` (US-1500/L1): the rates a revision keeps, their copy, proposal and update.
from waterfall.core.estimate.keeping import (
    RateProposal as RateProposal,
)
from waterfall.core.estimate.keeping import (
    RateUpdate as RateUpdate,
)
from waterfall.core.estimate.keeping import (
    close_rates as close_rates,
)
from waterfall.core.estimate.keeping import (
    copy_rates as copy_rates,
)
from waterfall.core.estimate.keeping import (
    rate_update_offered as rate_update_offered,
)

# ``reading`` (US-1490/L3): the lines as ``listNodes`` reads them, and what it filters.
from waterfall.core.estimate.reading import (
    LineFilters as LineFilters,
)
from waterfall.core.estimate.reading import (
    LineView as LineView,
)

# ``spreading`` (US-1520/L1): the planned value, which EP-10 reads.
from waterfall.core.estimate.spreading import (
    PlannedLine as PlannedLine,
)
from waterfall.core.estimate.spreading import (
    planned_value as planned_value,
)

# The registries the estimate fills.
from waterfall.core.exchanges.interface import register_exporter, register_format
from waterfall.core.planning.interface import register_facet
from waterfall.core.projects.interface import EstimateFacts, register_estimate_facts
from waterfall.core.resource_settings.interface import register_idle_task_guard
from waterfall.core.revisions.interface import (
    register_closing,
    register_copy,
    register_rate_update,
    register_tasks_and_lines,
)

# The registrations, once, at the import, each without effect until its story: the facet of the
# lines, whose copy the planning makes with its nodes; the copy of the rates after the planning's,
# whose interface the facet imports first, then the lines priced at them; the rates of a revision
# abandoned deleted after its nodes, in the stage of its content; whether the proposal of the
# rates of a revision presents a category (US-1500/L1); the categories and the subprojects the
# lines employ.
register_facet("estimate_line", LINE_FACET)
register_tasks_and_lines("lines", revision_has_lines)
register_copy(copy_rates)
register_rate_update(rate_update_offered)
register_closing("content", close_rates)
register_employment(category_is_employed)
register_estimate_facts(
    EstimateFacts(
        subproject_is_cited,
        subproject_is_estimated,
        subproject_estimate_lines,
        roles_employed,
        reinflate_project,
    )
)
register_idle_task_guard(idle_tasks_for_role_calendar)
register_format("estimate", ESTIMATE_FORMAT)
register_exporter("estimate", ESTIMATE_EXPORTER)
