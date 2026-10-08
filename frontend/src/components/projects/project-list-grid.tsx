// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the list of projects, the home (#522): for each project the
 * user may open, its label, a link that opens it, its code, its state by its badge (#523), and
 * when it was last modified. The same dense grid as the other lists, read only — the home creates
 * nothing here —: every column sorts by the column of the contract of the same name, the server
 * sorting, filtering and searching on the label (`listProjects`); the totals row says how many
 * projects the server retained (`meta.total`), never a count of the page.
 *
 * Neither server nor client: the page reads the sortable columns to check the address, the grid
 * the rest.
 */
import type { components, operations } from "@/api/generated/schema";
import { type GridConfig, sortColumns } from "@/components/grid/columns";
import { LocalTime } from "@/components/local-time";
import { ProjectLabelCell } from "@/components/portfolio/portfolio-cells";

import { ProjectStateBadge } from "./project-state-badge";

/** A project, as the contract gives it. */
type Project = components["schemas"]["Project"];

/**
 * A project of the list, as the page hands it to the grid: the fields its columns read, never the
 * whole project — its commands, its audit — which the grid does not show.
 */
export interface ListedProjectRow {
  readonly project_id: string;
  readonly label: string;
  readonly code: string | null;
  readonly state: Project["state"];
  readonly updated_at: string;
}

/** Where a page stands in the projects the server retained: their number, the totals row's. */
export type ListedProjectPage = components["schemas"]["PaginationMeta"];

/** The column of the contract the server sorts the projects by. */
export type ListedProjectSort = NonNullable<
  NonNullable<operations["listProjects"]["parameters"]["query"]>["sort_by"]
>;

/** The fields of a project the grid reads. */
export function listedProject(project: Project): ListedProjectRow {
  return {
    project_id: project.project_id,
    label: project.label,
    code: project.code ?? null,
    state: project.state,
    updated_at: project.audit.updated_at,
  };
}

/** The grid of the list of projects. */
export const PROJECT_LIST_GRID: GridConfig<ListedProjectRow, ListedProjectSort, ListedProjectPage> =
  {
    key: "projects",
    name: "projects",
    searched: true,
    rowKey: (project) => project.project_id,
    columns: [
      {
        key: "label",
        label: "label",
        format: "text",
        width: 320,
        pinned: true,
        contract: "label",
        value: (project) => project.label,
        render: (project) => <ProjectLabelCell id={project.project_id} label={project.label} />,
      },
      {
        key: "code",
        label: "code",
        format: "text",
        width: 120,
        contract: "code",
        value: (project) => project.code,
      },
      {
        key: "state",
        label: "state",
        format: "text",
        width: 136,
        contract: "state",
        value: (project) => project.state,
        render: (project) => <ProjectStateBadge state={project.state} className="max-w-full" />,
      },
      {
        key: "updated_at",
        label: "updatedAt",
        format: "text",
        width: 168,
        contract: "updated_at",
        value: (project) => project.updated_at,
        render: (project) => <LocalTime value={project.updated_at} />,
      },
    ],
  };

/** The columns of the contract the grid of the list of projects sorts by. */
export const PROJECT_LIST_SORT_COLUMNS = sortColumns(PROJECT_LIST_GRID);
