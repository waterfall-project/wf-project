// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the comparison of two revisions (US-0500, FBS-4.1): the dense grid of the structures,
 * read only, on the nodes `compareRevisions` renders — the tree of the revision compared, each
 * node with the mark of its difference from the revision of base, the nodes removed at the place
 * they had. A column of marks heads it (`GridConfig.difference`), `+`, `-` and `M` doubled by the
 * colour of the row, as the grid of a differential bears them; then the number of the node, its
 * label indented by its level and marked by the icon of its kind, and what changes of it
 * (`changes`), named as the server names it. The front pairs nothing, sums nothing and orders
 * nothing (WF-ARC-0020): the order is the plan's, no header sorts, nothing is searched, and the
 * totals are those of the answer. The page hands it data only; its functions live here, on the side
 * of the browser.
 */
"use client";

import { Calculator, ClipboardList, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridConfig } from "@/components/grid/columns";
import type { NodeSortColumn, NodeTotals } from "@/components/grid/nodes";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { Badge } from "@/components/ui/badge";

import { COMPARISON_KEY, type ComparisonRow } from "./comparison-rows";

type NodeKind = components["schemas"]["NodeKind"];

/** The icon of each kind of node: a task, a line of the estimate. */
const KIND_ICONS: Readonly<Record<NodeKind, LucideIcon>> = {
  task: ClipboardList,
  estimate_line: Calculator,
};

/** The icon of the kind of a node, named for it; nothing when `fields` left the kind out. */
function KindIcon({ kind }: { readonly kind: NodeKind | undefined }) {
  const name = useTranslations("enums.NodeKind");
  if (kind === undefined) {
    return null;
  }
  const Icon = KIND_ICONS[kind];
  return (
    <Icon role="img" aria-label={name(kind)} className="size-3.5 shrink-0 text-muted-foreground" />
  );
}

/** What changes of a node, each change named as the server names it; nothing for a node that keeps. */
function Changes({ changes }: { readonly changes: ComparisonRow["changes"] }) {
  const name = useTranslations("enums.NodeChange");
  return (
    <span className="flex gap-1">
      {changes.map((change) => (
        <Badge key={change} variant="outline">
          {name(change)}
        </Badge>
      ))}
    </span>
  );
}

/** The grid of the comparison: read only, in the order of the plan, marked by the server. */
const COMPARISON_GRID: GridConfig<ComparisonRow, NodeSortColumn, NodeTotals> = {
  key: COMPARISON_KEY,
  name: "comparison",
  searched: false,
  sorts: false,
  rowKey: (row) => row.node_id,
  rowNumber: (row) => row.row_number,
  difference: (row) => row.difference,
  tree: {
    level: (row) => row.level,
    nature: (row) => <KindIcon kind={row.kind} />,
  },
  columns: [
    {
      key: "label",
      label: "label",
      format: "text",
      width: 360,
      pinned: true,
      value: (row) => row.task?.label ?? row.estimate_line?.label,
    },
    {
      key: "changes",
      label: "changes",
      format: "text",
      width: 280,
      value: () => undefined,
      render: (row) => <Changes changes={row.changes} />,
    },
  ],
};

/** What the grid asks of the address: nothing, it sorts and searches nothing. */
const UNASKED: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };

/** What the grid of the comparison shows. */
export interface ComparisonGridProps {
  /** The nodes of the comparison, in the order of the plan, as the grid reads them. */
  readonly rows: readonly ComparisonRow[];
  /** The totals of the revision compared, as the server computes them. */
  readonly totals: NodeTotals;
  /** The settings of the grid the session read, if any. */
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the comparison of two revisions. */
export function ComparisonGrid({ rows, totals, preferences }: ComparisonGridProps) {
  const t = useTranslations("estimateGrid");
  return (
    <DenseGrid
      config={COMPARISON_GRID}
      rows={rows}
      totals={totals}
      totalsCaption={(counted) =>
        t("totals", { tasks: counted.task_count, lines: counted.estimate_line_count })
      }
      query={UNASKED}
      preferences={preferences}
    />
  );
}
