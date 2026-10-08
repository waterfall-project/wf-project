// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lists of the settings of a project (FBS-4.2, US-0210), each a dense grid under its title
 * (#301), in the order the server gave it: its work breakdown, each order item with its work
 * packages and their deliverables, a tree that folds (WF-PRJ-0020); its sub-projects, each by the
 * code the ERP knows it by, and whether actual costs are charged to it (WF-PRJ-0050), searched by
 * the server; its contributors, the project manager told from the others, and whether their account
 * is still active (WF-PRJ-0060), filtered by capacity. Each list is a section under its title —
 * named by `aria-label`, never by an identifier of `useId`, which a server component may share with
 * a client one of the shell (#251) —; a list says it is empty only when nothing narrows it: a
 * search or a filter that retains nothing keeps its grid, to be changed. Nothing is offered to
 * create or modify: those forms belong to the epic of their domain.
 */
import { FolderTree, ListTree, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { ValuesFilter } from "@/components/grid/values-filter";

import { ListSection } from "./project-tables";
import { SettingsGrid } from "./settings-grid";
import {
  breakdownRows,
  type Contributor,
  CONTRIBUTOR_KINDS,
  type ContributorKind,
  KINDS,
  type Subproject,
  type WorkBreakdown,
} from "./settings-grids";

/** What a grid of the settings asks and keeps: the query of its address, its settings. */
interface Shown {
  readonly query: GridQuery<never>;
  readonly preferences: GridPreferences | undefined;
}

/** A grid that neither searches nor sorts, its settings read from none. */
export const UNASKED: Shown = {
  query: { sort: undefined, search: undefined },
  preferences: undefined,
};

/**
 * The work breakdown of a project, as its order was entered (WF-PRJ-0020): a tree of its order
 * items, each with its work packages under it, and their deliverables under them.
 */
export function WorkBreakdownList({
  breakdown,
  project,
  shown = UNASKED,
}: {
  readonly breakdown: WorkBreakdown;
  /** The project whose work breakdown it is. */
  readonly project: string;
  readonly shown?: Shown;
}) {
  const t = useTranslations("projectLists.workBreakdown");
  const items = breakdown.order_items.length;
  return (
    <ListSection title={t("title")} icon={ListTree} empty={items === 0 ? t("none") : undefined}>
      <SettingsGrid
        kind="workBreakdown"
        rows={breakdownRows(breakdown)}
        project={project}
        items={items}
        query={shown.query}
        preferences={shown.preferences}
      />
    </ListSection>
  );
}

/** The sub-projects of a project, each by its code, its label, and its actual costs. */
export function SubprojectList({
  subprojects,
  shown = UNASKED,
}: {
  readonly subprojects: readonly Subproject[];
  readonly shown?: Shown;
}) {
  const t = useTranslations("projectLists.subprojects");
  const empty = subprojects.length === 0 && shown.query.search === undefined;
  return (
    <ListSection title={t("title")} icon={FolderTree} empty={empty ? t("none") : undefined}>
      <SettingsGrid
        kind="subprojects"
        rows={subprojects}
        query={shown.query}
        preferences={shown.preferences}
      />
    </ListSection>
  );
}

/**
 * The contributors of a project, each by the name of their account, their capacity — the project
 * manager marked by an icon besides its name, readable without colour —, and whether their
 * account is active; filtered by the capacities the address names.
 */
export function ContributorList({
  contributors,
  kinds = [],
  shown = UNASKED,
}: {
  readonly contributors: readonly Contributor[];
  /** The capacities the address restricts the contributors to; none, every one. */
  readonly kinds?: readonly ContributorKind[];
  readonly shown?: Shown;
}) {
  const t = useTranslations("projectLists.contributors");
  const named = useTranslations("enums.ContributorKind");
  const empty = contributors.length === 0 && kinds.length === 0;
  return (
    <ListSection title={t("title")} icon={Users} empty={empty ? t("none") : undefined}>
      <ValuesFilter
        name={CONTRIBUTOR_KINDS}
        label={t("kindFilter")}
        every={t("everyKind")}
        values={KINDS.map((kind) => ({ value: kind, text: named(kind) }))}
        chosen={kinds}
      />
      <SettingsGrid
        kind="contributors"
        rows={contributors}
        query={shown.query}
        preferences={shown.preferences}
      />
    </ListSection>
  );
}
