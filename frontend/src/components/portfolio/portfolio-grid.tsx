// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the projects of the portfolio (WF-PTF-0040): for each project
 * of the perimeter, its label, which opens it, its code, its state, its reference budget — or, in
 * pricing, its current estimate and its probability of winning —, the projection of its project
 * manager and its variance to the reference budget, its indices with their zone, and the date of
 * its last marked revision. The same dense grid as the other lists, read only: nothing is entered
 * in the portfolio (WF-PTF-0030). Every column sorts by the column of the contract of the same
 * name, the server sorting, filtering and searching on the label; the totals row says how many
 * projects the server retained (`meta.total`), never a count of the page.
 */
import type { components, operations } from "@/api/generated/schema";
import { type GridConfig, sortColumns } from "@/components/grid/columns";

import { IndexCell, MarkedCell, ProjectLabelCell, ProjectStateCell } from "./portfolio-cells";

/** A project of the portfolio, as the contract gives it. */
export type ProjectRow = components["schemas"]["PortfolioProjectRow"];

/** Where a page stands in the projects the server retained: their number, the totals row's. */
export type ProjectPage = components["schemas"]["PaginationMeta"];

/** The column of the contract the server sorts the projects by. */
export type ProjectSortColumn = NonNullable<
  NonNullable<operations["getPortfolioProjects"]["parameters"]["query"]>["sort_by"]
>;

/** The grid of the projects of the portfolio. */
export const PROJECT_GRID: GridConfig<ProjectRow, ProjectSortColumn, ProjectPage> = {
  key: "portfolio_projects",
  name: "portfolioProjects",
  searched: true,
  rowKey: (project) => project.project_id,
  columns: [
    {
      key: "label",
      label: "label",
      format: "text",
      width: 280,
      pinned: true,
      sortBy: "label",
      value: (project) => project.label,
      render: (project) => <ProjectLabelCell id={project.project_id} label={project.label} />,
    },
    {
      key: "code",
      label: "code",
      format: "text",
      width: 96,
      sortBy: "code",
      value: (project) => project.code,
    },
    {
      key: "state",
      label: "state",
      format: "text",
      width: 112,
      sortBy: "state",
      value: (project) => project.state,
      render: (project) => <ProjectStateCell state={project.state} />,
    },
    {
      key: "reference_budget",
      label: "referenceBudget",
      format: "money",
      width: 136,
      sortBy: "reference_budget",
      value: (project) => project.reference_budget,
    },
    {
      key: "current_estimate",
      label: "currentEstimate",
      format: "money",
      width: 136,
      sortBy: "current_estimate",
      value: (project) => project.current_estimate,
    },
    {
      key: "win_probability",
      label: "winProbability",
      format: "percent",
      width: 104,
      sortBy: "win_probability",
      value: (project) => project.win_probability,
    },
    {
      key: "project_manager_projection",
      label: "projectManagerProjection",
      format: "money",
      width: 136,
      sortBy: "project_manager_projection",
      value: (project) => project.project_manager_projection,
    },
    {
      key: "delta_to_reference",
      label: "deltaToReference",
      format: "money",
      width: 128,
      sortBy: "delta_to_reference",
      value: (project) => project.delta_to_reference,
    },
    {
      key: "cost_index",
      label: "costIndex",
      format: "decimal",
      width: 112,
      sortBy: "cost_index",
      value: (project) => project.cost_index?.value.value,
      render: (project) => <IndexCell index={project.cost_index} />,
    },
    {
      key: "schedule_index",
      label: "scheduleIndex",
      format: "decimal",
      width: 112,
      sortBy: "schedule_index",
      value: (project) => project.schedule_index?.value.value,
      render: (project) => <IndexCell index={project.schedule_index} />,
    },
    {
      key: "last_marked_at",
      label: "lastMarkedAt",
      format: "text",
      width: 168,
      sortBy: "last_marked_at",
      value: (project) => project.last_marked_at,
      render: (project) => <MarkedCell at={project.last_marked_at} />,
    },
  ],
};

/** The columns of the contract the grid of the projects sorts by. */
export const PROJECT_SORT_COLUMNS = sortColumns(PROJECT_GRID);
