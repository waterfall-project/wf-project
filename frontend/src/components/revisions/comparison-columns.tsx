// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the comparison of two revisions (US-0500, FBS-4.1): the label of
 * each node, indented by its level and marked by the icon of its kind, and what changes of it, each
 * column with its definition — which the grid and the help of its screen both read (US-0670/L5,
 * #1434).
 *
 * Neither server nor client: the grid renders it in the browser; `help/read.ts` reads its columns
 * on the server, their titles and definitions only.
 */
import { Calculator, ClipboardList, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { GridConfig } from "@/components/grid/columns";
import type { NodeSortColumn, NodeTotals } from "@/components/grid/nodes";
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
    <span className="flex flex-wrap gap-1">
      {changes.map((change) => (
        <Badge key={change} variant="outline">
          {name(change)}
        </Badge>
      ))}
    </span>
  );
}

/** The grid of the comparison: read only, in the order of the plan, marked by the server. */
export const COMPARISON_GRID: GridConfig<ComparisonRow, NodeSortColumn, NodeTotals> = {
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
      help: "nodes.label",
      format: "text",
      width: 360,
      pinned: true,
      value: (row) => row.task?.label ?? row.estimate_line?.label,
    },
    {
      key: "changes",
      label: "changes",
      help: "comparison.changes",
      format: "text",
      width: 280,
      value: () => undefined,
      render: (row) => <Changes changes={row.changes} />,
    },
  ],
};
