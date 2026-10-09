// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lists of the settings of a project (FBS-4.2, US-0210), each a dense grid under its title
 * (#301), in the order the server gave it: its work breakdown, each order item with its work
 * packages and their deliverables, a tree that folds (WF-PRJ-0020); its sub-projects, each by the
 * code the ERP knows it by, and whether actual costs are charged to it (WF-PRJ-0050), searched,
 * sorted and filtered on their actual costs by the server; its contributors, the project manager
 * told from the others, and whether their account is still active (WF-PRJ-0060), searched, sorted
 * and filtered on their capacity and on the state of their account by the server. Each filter is a
 * choice that only changes the address, under the name of the contract after the prefix of its grid
 * (`ValuesFilter`, `ChoiceFilter`). Each list is a section under its title —
 * named by `aria-label`, never by an identifier of `useId`, which a server component may share with
 * a client one of the shell (#251) —; a list says it is empty only when nothing narrows it: a
 * search or a filter that retains nothing keeps its grid, to be changed. Nothing is offered to
 * create or modify: those forms belong to the epic of their domain.
 */
import { FolderTree, ListTree, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import { ChoiceFilter } from "@/components/grid/choice-filter";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { ValuesFilter } from "@/components/grid/values-filter";

import { ListSection } from "./project-tables";
import { SettingsGrid } from "./settings-grid";
import {
  breakdownRows,
  type Contributor,
  CONTRIBUTOR_ACTIVE,
  CONTRIBUTOR_KINDS,
  type ContributorKind,
  type ContributorSort,
  KINDS,
  type Subproject,
  SUBPROJECT_ACTUAL_COSTS,
  type SubprojectSort,
  type WorkBreakdown,
} from "./settings-grids";

/** What a grid of the settings asks and keeps: the query of its address, its settings. */
interface Shown<Sort extends string> {
  readonly query: GridQuery<Sort>;
  readonly preferences: GridPreferences | undefined;
}

/** A grid the address asks nothing of, its settings read from none. */
export const UNASKED: Shown<never> = {
  query: { sort: undefined, search: undefined },
  preferences: undefined,
};

/** The value a filter on a boolean column shows chosen: none, every row. */
function chosenFlag(flag: boolean | undefined): string | undefined {
  return flag === undefined ? undefined : String(flag);
}

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
  readonly shown?: Shown<never>;
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

/**
 * The sub-projects of a project, each by its code, its label, and its actual costs; filtered on
 * whether actual costs are charged to them, as the address asks it.
 */
export function SubprojectList({
  subprojects,
  actualCosts,
  shown = UNASKED,
}: {
  readonly subprojects: readonly Subproject[];
  /**
   * Whether the address retains the sub-projects charged with actual costs, or the others; none,
   * all.
   */
  readonly actualCosts?: boolean | undefined;
  readonly shown?: Shown<SubprojectSort>;
}) {
  const t = useTranslations("projectLists.subprojects");
  const empty =
    subprojects.length === 0 && shown.query.search === undefined && actualCosts === undefined;
  return (
    <ListSection title={t("title")} icon={FolderTree} empty={empty ? t("none") : undefined}>
      <ChoiceFilter
        name={SUBPROJECT_ACTUAL_COSTS}
        label={t("actualCostsFilter")}
        every={t("everyActualCosts")}
        choices={[
          { value: "true", text: t("withActualCosts") },
          { value: "false", text: t("withoutActualCosts") },
        ]}
        chosen={chosenFlag(actualCosts)}
      />
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
 * account is active; filtered by the capacities and the state of the accounts the address names.
 */
export function ContributorList({
  contributors,
  kinds = [],
  active,
  shown = UNASKED,
}: {
  readonly contributors: readonly Contributor[];
  /** The capacities the address restricts the contributors to; none, every one. */
  readonly kinds?: readonly ContributorKind[];
  /** Whether the address retains the active accounts, or the deactivated ones; none, all. */
  readonly active?: boolean | undefined;
  readonly shown?: Shown<ContributorSort>;
}) {
  const t = useTranslations("projectLists.contributors");
  const named = useTranslations("enums.ContributorKind");
  const empty =
    contributors.length === 0 &&
    kinds.length === 0 &&
    active === undefined &&
    shown.query.search === undefined;
  return (
    <ListSection title={t("title")} icon={Users} empty={empty ? t("none") : undefined}>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <ValuesFilter
          name={CONTRIBUTOR_KINDS}
          label={t("kindFilter")}
          every={t("everyKind")}
          values={KINDS.map((kind) => ({ value: kind, text: named(kind) }))}
          chosen={kinds}
        />
        <ChoiceFilter
          name={CONTRIBUTOR_ACTIVE}
          label={t("accountFilter")}
          every={t("everyAccount")}
          choices={[
            { value: "true", text: t("activeAccounts") },
            { value: "false", text: t("inactiveAccounts") },
          ]}
          chosen={chosenFlag(active)}
        />
      </div>
      <SettingsGrid
        kind="contributors"
        rows={contributors}
        query={shown.query}
        preferences={shown.preferences}
      />
    </ListSection>
  );
}
