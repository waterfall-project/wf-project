// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configurations of the three dense grids of the settings of a project (FBS-4.2, #301): its
 * work breakdown (FBS-4.2.1), its sub-projects and its contributors. Three grids on one screen, each
 * with the key of its settings in the account (WF-ADM-0040) and its own names in the address
 * (`prefixedAddress`), under which its page asks the API by the names of the contract.
 *
 * - The work breakdown is a tree, as its order was entered (WF-PRJ-0020): each order item, its work
 *   packages under it, their deliverables under them. It sorts by no column (`sorts: false`) — the
 *   order is the one entered, as `getWorkBreakdown` gives it —, folds and unfolds as the grids of
 *   the tasks do (`GridTree.parent`, `fold.tsx`), and is not searched: the operation has no search.
 * - The sub-projects, each by the code the ERP knows it by, and whether actual costs are charged to
 *   it (WF-PRJ-0050), searched by the server on their code and their label. The contract sorts them
 *   by no column: the grid sorts none, in the order the server gives.
 * - The contributors, the project manager told from the others, and whether their account is still
 *   active (WF-PRJ-0060), filtered by capacity (`kinds`). The contract neither searches nor sorts
 *   them: the grid does neither.
 *
 * What the contract lacks for these flat tables — the sort of the sub-projects, the search and the
 * sort of the contributors — is #536, for EP-02/L42. The volumes of §4.6.2 — ten sub-projects,
 * fifty contributors a project — hold in one page, which the contract does not page.
 *
 * Neither server nor client: the page reads the keys and the names; the grids, in the browser, the
 * rest — the functions that read a row never cross to the server.
 */
import { User, UserCog } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { GridConfig } from "@/components/grid/columns";
import { prefixedAddress } from "@/components/grid/query";
import { ActiveState } from "@/components/reference/section";

import { ICON } from "./project-tables";

/** A sub-project, as the contract gives it. */
export type Subproject = components["schemas"]["Subproject"];

/** A contributor of a project, as the contract gives it. */
export type Contributor = components["schemas"]["Contributor"];

/** The work breakdown of a project, as the contract gives it. */
export type WorkBreakdown = components["schemas"]["WorkBreakdown"];

/** The capacity of a contributor, as the contract names it. */
export type ContributorKind = components["schemas"]["ContributorKind"];

/** What a row of the work breakdown is: an order item, a work package, a deliverable. */
export type BreakdownKind = "orderItem" | "workPackage" | "deliverable";

/** A row of the tree of the work breakdown, with the identity of the row it is under. */
export interface BreakdownRow {
  readonly id: string;
  readonly parent: string | null;
  readonly level: number;
  readonly kind: BreakdownKind;
  readonly label: string;
}

/** The keys of the settings of the three grids in the account: stable. */
export const BREAKDOWN_GRID_KEY = "work_breakdown";
export const SUBPROJECT_GRID_KEY = "subprojects";
export const CONTRIBUTOR_GRID_KEY = "contributors";

/** The names of each grid in the address: those of the contract, after its prefix. */
export const BREAKDOWN_ADDRESS = prefixedAddress("breakdown_");
export const SUBPROJECT_ADDRESS = prefixedAddress("subproject_");
export const CONTRIBUTOR_ADDRESS = prefixedAddress("contributor_");

/** The capacities the contributors are restricted to, in the address: `kinds` of the contract. */
export const CONTRIBUTOR_KINDS = "contributor_kinds";

/**
 * Every capacity of the contract, in the order of its enumeration: one the contract adds fails the
 * type check until it is here.
 */
const EVERY_KIND: Readonly<Record<ContributorKind, number>> = {
  project_manager: 0,
  contributor: 1,
};

/** The capacities a contributor may have, in the order of the contract. */
export const KINDS = Object.keys(EVERY_KIND) as readonly ContributorKind[];

/**
 * The rows of the tree of a work breakdown, in the order it was entered: each order item, then each
 * of its work packages, each followed by its deliverables.
 */
export function breakdownRows(breakdown: WorkBreakdown): BreakdownRow[] {
  return breakdown.order_items.flatMap((item): BreakdownRow[] => [
    {
      id: item.order_item_id,
      parent: null,
      level: 1,
      kind: "orderItem",
      label: item.label,
    },
    ...item.work_packages.flatMap((workPackage): BreakdownRow[] => [
      {
        id: workPackage.work_package_id,
        parent: item.order_item_id,
        level: 2,
        kind: "workPackage",
        label: workPackage.label,
      },
      ...workPackage.deliverables.map((deliverable): BreakdownRow => ({
        id: deliverable.deliverable_id,
        parent: workPackage.work_package_id,
        level: 3,
        kind: "deliverable",
        label: deliverable.label,
      })),
    ]),
  ]);
}

/** What a row of the work breakdown is, in words. */
function BreakdownKindCell({ row }: { readonly row: BreakdownRow }) {
  const t = useTranslations("projectLists.workBreakdown");
  return t(row.kind);
}

/** The grid of the work breakdown: a tree in the order entered, which folds. */
export const BREAKDOWN_GRID: GridConfig<BreakdownRow, never, null> = {
  key: BREAKDOWN_GRID_KEY,
  name: "workBreakdown",
  address: BREAKDOWN_ADDRESS,
  sorts: false,
  searched: false,
  rowKey: (row) => row.id,
  tree: {
    level: (row) => row.level,
    nature: () => null,
    emphasis: (row) => (row.kind === "orderItem" ? "strong" : undefined),
    parent: (row) => row.parent,
  },
  columns: [
    {
      key: "label",
      label: "label",
      format: "text",
      width: 420,
      pinned: true,
      value: (row) => row.label,
    },
    {
      key: "kind",
      label: "breakdownKind",
      format: "text",
      width: 130,
      value: (row) => row.kind,
      render: (row) => <BreakdownKindCell row={row} />,
    },
  ],
};

/** Whether actual costs are charged to a sub-project, in words. */
function ActualCosts({ subproject }: { readonly subproject: Subproject }) {
  const t = useTranslations("projectLists.subprojects");
  return t(subproject.has_actual_costs ? "charged" : "notCharged");
}

/** The grid of the sub-projects, searched by the server. */
export const SUBPROJECT_GRID: GridConfig<Subproject, never, null> = {
  key: SUBPROJECT_GRID_KEY,
  name: "subprojects",
  address: SUBPROJECT_ADDRESS,
  sorts: false,
  searched: true,
  rowKey: (subproject) => subproject.subproject_id,
  columns: [
    {
      key: "code",
      label: "erpCode",
      format: "text",
      width: 130,
      pinned: true,
      value: (subproject) => subproject.code,
    },
    {
      key: "label",
      label: "label",
      format: "text",
      width: 320,
      value: (subproject) => subproject.label,
    },
    {
      key: "actual_costs",
      label: "actualCosts",
      format: "text",
      width: 130,
      value: (subproject) => (subproject.has_actual_costs ? "charged" : "none"),
      render: (subproject) => <ActualCosts subproject={subproject} />,
    },
  ],
};

/** The name of the account of a contributor, after the icon of a person. */
function ContributorName({ contributor }: { readonly contributor: Contributor }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <User aria-hidden="true" className={ICON} />
      {contributor.display_name}
    </span>
  );
}

/** The capacity of a contributor in words, the project manager marked by an icon besides them. */
function Capacity({ contributor }: { readonly contributor: Contributor }) {
  const t = useTranslations("enums.ContributorKind");
  return contributor.kind === "project_manager" ? (
    <span className="inline-flex items-center gap-1.5">
      <UserCog aria-hidden="true" className={ICON} />
      {t(contributor.kind)}
    </span>
  ) : (
    t(contributor.kind)
  );
}

/** The grid of the contributors, filtered by capacity by the server. */
export const CONTRIBUTOR_GRID: GridConfig<Contributor, never, null> = {
  key: CONTRIBUTOR_GRID_KEY,
  name: "contributors",
  address: CONTRIBUTOR_ADDRESS,
  sorts: false,
  searched: false,
  rowKey: (contributor) => contributor.user_id,
  columns: [
    {
      key: "name",
      label: "name",
      format: "text",
      width: 240,
      pinned: true,
      value: (contributor) => contributor.display_name,
      render: (contributor) => <ContributorName contributor={contributor} />,
    },
    {
      key: "kind",
      label: "contributorKind",
      format: "text",
      width: 180,
      value: (contributor) => contributor.kind,
      render: (contributor) => <Capacity contributor={contributor} />,
    },
    {
      key: "account",
      label: "account",
      format: "text",
      width: 140,
      value: (contributor) => (contributor.is_active ? "active" : "inactive"),
      render: (contributor) => <ActiveState active={contributor.is_active} />,
    },
  ],
};
