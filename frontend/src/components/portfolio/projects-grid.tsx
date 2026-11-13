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
import type { ReactNode } from "react";

import { useChipKit } from "@/components/grid/chip-kit";
import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { type AlertZone, ZONES } from "./address";
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
  /** The zones of the indices the address restricts the projects to, told as a chip under the bar. */
  readonly zones?: readonly AlertZone[] | undefined;
  /** The filters of the screen, which the bar folds into its panel (#2916); none, no panel. */
  readonly panel?: ReactNode;
}

/** Render the grid of the projects of the portfolio, its totals row the number retained. */
export function ProjectsGrid({
  projects,
  page,
  query,
  preferences,
  zones,
  panel,
}: ProjectsGridProps) {
  const t = useTranslations();
  const kit = useChipKit();
  kit.values(
    ZONES,
    t("portfolio.projects.zoneChip"),
    (zones ?? []).map((zone) => t(`enums.AlertZone.${zone}`)),
  );
  return (
    <DenseGrid
      config={PROJECT_GRID}
      rows={projects}
      totals={page}
      totalsCaption={(retained) => t("portfolio.projects.retained", { count: retained.total })}
      query={query}
      preferences={preferences}
      filtering={panel === undefined ? undefined : { panel, chips: kit.chips }}
    />
  );
}
