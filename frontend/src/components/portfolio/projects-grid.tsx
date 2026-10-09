// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the projects of the portfolio in the page: the dense grid, given its configuration
 * here, on the side of the browser — a configuration reads the rows by functions, which never
 * cross from a server component to a client one. The page hands it data only: the projects of a
 * page of `getPortfolioProjects`, where the page stands, what the address asked and the settings
 * the session read. Read only: nothing is entered in the portfolio (WF-PTF-0030).
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import {
  PROJECT_GRID,
  type ProjectPage,
  type ProjectRow,
  type ProjectSortColumn,
} from "./portfolio-grid";

/** What the grid of the projects shows. */
export interface ProjectsGridProps {
  readonly projects: readonly ProjectRow[];
  /** Where the page stands in the projects retained, whose number the totals row says. */
  readonly page: ProjectPage;
  readonly query: GridQuery<ProjectSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the projects of the portfolio, its totals row the number retained. */
export function ProjectsGrid({ projects, page, query, preferences }: ProjectsGridProps) {
  const t = useTranslations("portfolio.projects");
  return (
    <DenseGrid
      config={PROJECT_GRID}
      rows={projects}
      totals={page}
      totalsCaption={(retained) => t("retained", { count: retained.total })}
      query={query}
      preferences={preferences}
    />
  );
}
