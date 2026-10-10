// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lists of the settings of a project (FBS-4.2, US-0210), each a dense grid under its title
 * (#301), in the order the server gave it: its work breakdown, each order item with its work
 * packages and their deliverables, a tree that folds (WF-PRJ-0020), searched and filtered on its
 * kinds by the server; its sub-projects, each by the code the ERP knows it by, and whether actual
 * costs are charged to it (WF-PRJ-0050), searched, sorted and filtered on their actual costs by the
 * server; its contributors, the project manager told from the others, and whether their account is
 * still active (WF-PRJ-0060), searched, sorted and filtered on their capacity and on the state of
 * their account by the server. Each filter is a choice that only changes the address, under the
 * name of the contract after the prefix of its grid (`ValuesFilter`, `ChoiceFilter`). Each list is
 * a section under its title — named by `aria-label`, never by an identifier of `useId`, which a
 * server component may share with a client one of the shell (#251) —; a list says it is empty only
 * when nothing narrows it: a search or a filter that retains nothing keeps its grid, to be changed.
 * The sub-projects are created, modified and deleted as the project lists `update`
 * (`subproject-commands.tsx`), the list of the contributors written as it lists
 * `manage_contributors` (`contributor-commands.tsx`, EP-02/L44b); the work breakdown is read only.
 */
import { FolderTree, ListTree, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import type { CommandOffer } from "@/components/commands/offer";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { ValuesFilter } from "@/components/grid/values-filter";
import { listReads } from "@/components/reference/address";
import { ListBody, ReferenceSection } from "@/components/reference/section";

import {
  ContributorCommands,
  type ContributorEditing,
  ContributorHead,
} from "./contributor-commands";
import { ListSection } from "./project-tables";
import { SettingsGrid } from "./settings-grid";
import {
  BREAKDOWN_KIND_FILTER,
  type BreakdownKind,
  BREAKDOWN_KINDS,
  breakdownRows,
  type Contributor,
  CONTRIBUTOR_ACTIVE,
  CONTRIBUTOR_KINDS,
  type ContributorKind,
  type ContributorSort,
  KINDS,
  type Subproject,
  SUBPROJECT_ACTUAL_COSTS,
  SUBPROJECT_ADDRESS,
  type SubprojectSort,
  type WorkBreakdown,
} from "./settings-grids";
import { SubprojectCommands, SubprojectDialog, SubprojectHead } from "./subproject-commands";

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
 * The note of a work breakdown read partial, naming what narrows it as the address sets it: the
 * search, the filter by kind, or both.
 */
function partialNote(
  search: string | undefined,
  kinds: readonly BreakdownKind[],
): "partial" | "partialSearch" | "partialKinds" {
  if (search !== undefined && kinds.length === 0) {
    return "partialSearch";
  }
  return search === undefined && kinds.length > 0 ? "partialKinds" : "partial";
}

/**
 * The work breakdown of a project, as its order was entered (WF-PRJ-0020): a tree of its order
 * items, each with its work packages under it, and their deliverables under them; searched on its
 * labels and filtered on its kinds by the server. Read partial — without a counter, as the server
 * reads it filtered —, the order items and the work packages that hold an element retained show
 * without the rest they hold, which the list says; and a partial reading that retains nothing keeps
 * its grid, to be changed.
 */
export function WorkBreakdownList({
  breakdown,
  project,
  kinds = [],
  shown = UNASKED,
}: {
  readonly breakdown: WorkBreakdown;
  /** The project whose work breakdown it is. */
  readonly project: string;
  /** The kinds the address restricts the work breakdown to; none, every one. */
  readonly kinds?: readonly BreakdownKind[];
  readonly shown?: Shown<never>;
}) {
  const t = useTranslations("projectLists.workBreakdown");
  const named = useTranslations("enums.WorkBreakdownKind");
  const items = breakdown.order_items.length;
  // The server says the reading partial — filtered — by giving it no counter.
  const partial = breakdown.lock_version === null;
  return (
    <ListSection
      title={t("title")}
      icon={ListTree}
      empty={items === 0 && !partial ? t("none") : undefined}
    >
      <ValuesFilter
        name={BREAKDOWN_KIND_FILTER}
        label={t("kindFilter")}
        every={t("everyKind")}
        values={BREAKDOWN_KINDS.map((kind) => ({ value: kind, text: named(kind) }))}
        chosen={kinds}
      />
      {partial ? (
        <p className="text-sm text-muted-foreground">{t(partialNote(shown.query.search, kinds))}</p>
      ) : null}
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

/** The parameters of the address the sub-projects read, their filter among them. */
const SUBPROJECT_READS = listReads(SUBPROJECT_ADDRESS, SUBPROJECT_ACTUAL_COSTS);

/**
 * The sub-projects of a project, each by its code, its label, and its actual costs; filtered on
 * whether actual costs are charged to them, as the address asks it; and, for the project they are
 * of, their commands as it lists `update` (`editing`).
 */
export function SubprojectList({
  subprojects,
  actualCosts,
  shown = UNASKED,
  editing,
}: {
  readonly subprojects: readonly Subproject[];
  /**
   * Whether the address retains the sub-projects charged with actual costs, or the others; none,
   * all.
   */
  readonly actualCosts?: boolean | undefined;
  readonly shown?: Shown<SubprojectSort>;
  /** The project, and the command `update` it lists: absent, nothing is offered. */
  readonly editing?: { readonly project: string; readonly offer: CommandOffer | undefined };
}) {
  const t = useTranslations("projectLists.subprojects");
  const empty =
    subprojects.length === 0 && shown.query.search === undefined && actualCosts === undefined;
  return (
    // Keyed by the project: an answer of the server never outlives its project.
    <SubprojectCommands key={editing?.project} project={editing?.project}>
      <ReferenceSection
        title={t("title")}
        icon={FolderTree}
        commands={<SubprojectHead offer={editing?.offer} />}
      >
        <ListBody
          empty={empty ? t("none") : undefined}
          reads={SUBPROJECT_READS}
          filters={
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
          }
          grid={
            <SettingsGrid
              kind="subprojects"
              rows={subprojects}
              editable={editing?.offer !== undefined}
              query={shown.query}
              preferences={shown.preferences}
            />
          }
          dialog={<SubprojectDialog />}
        />
      </ReferenceSection>
    </SubprojectCommands>
  );
}

/**
 * The contributors of a project, each by the name of their account, their capacity — the project
 * manager marked by an icon besides its name, readable without colour —, and whether their
 * account is active; filtered by the capacities and the state of the accounts the address names;
 * and, for the project they are of, the modification of the list as it lists `manage_contributors`
 * (`editing`).
 */
export function ContributorList({
  contributors,
  kinds = [],
  active,
  shown = UNASKED,
  editing,
}: {
  readonly contributors: readonly Contributor[];
  /** The capacities the address restricts the contributors to; none, every one. */
  readonly kinds?: readonly ContributorKind[];
  /** Whether the address retains the active accounts, or the deactivated ones; none, all. */
  readonly active?: boolean | undefined;
  readonly shown?: Shown<ContributorSort>;
  readonly editing?: ContributorEditing;
}) {
  const t = useTranslations("projectLists.contributors");
  const named = useTranslations("enums.ContributorKind");
  const empty =
    contributors.length === 0 &&
    kinds.length === 0 &&
    active === undefined &&
    shown.query.search === undefined;
  return (
    <ContributorCommands key={editing?.project} editing={editing}>
      <ListSection title={t("title")} icon={Users} empty={empty ? t("none") : undefined}>
        <ContributorHead />
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
    </ContributorCommands>
  );
}
