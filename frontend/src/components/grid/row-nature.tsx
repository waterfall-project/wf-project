// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The nature of a row of a structure, shown by its icon (charter, guide « Charte graphique »):
 * a summary task, a task, a milestone; a line of labour, of disbursement, of provision — read
 * from the node as the API gives it, its kind and its flags, never deduced from its figures.
 * A line is a provision when the API says its amount is computed from a risk (`is_computed`),
 * and labour when it names a resource role, which the contract requires of a labour category
 * and forbids to the others (WF-DEV-0020). The icon bears the name of the nature: in a dense
 * grid it stands alone before the label.
 */
import {
  ClipboardList,
  Diamond,
  Folder,
  type LucideIcon,
  Receipt,
  ShieldAlert,
  User,
} from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";

/** What the nature of a node is read from: its kind, and the flags of its facet. */
interface NatureOf {
  readonly kind: components["schemas"]["NodeKind"];
  readonly task?: Pick<components["schemas"]["TaskFacet"], "is_summary" | "is_milestone"> | null;
  readonly estimate_line?: Pick<
    components["schemas"]["EstimateLineFacet"],
    "is_computed" | "resource_role_id"
  > | null;
}

/** The icon of each nature of a row: a nature added without one breaks the typing. */
export const ROW_NATURE_ICONS = {
  summary: Folder,
  task: ClipboardList,
  milestone: Diamond,
  labour: User,
  disbursement: Receipt,
  provision: ShieldAlert,
} as const satisfies Readonly<Record<string, LucideIcon>>;

/** The nature of a row. */
export type RowNature = keyof typeof ROW_NATURE_ICONS;

/** The nature of a line of the estimate, from the flags of its facet. */
function lineNature(line: NatureOf["estimate_line"]): RowNature {
  if (line?.is_computed === true) {
    return "provision";
  }
  return line?.resource_role_id === undefined || line.resource_role_id === null
    ? "disbursement"
    : "labour";
}

/**
 * The nature of a node: its kind tells a task from a line, the flags of its facet the rest —
 * a facet the API left out has none raised.
 */
export function rowNature(node: NatureOf): RowNature {
  if (node.kind === "estimate_line") {
    return lineNature(node.estimate_line);
  }
  if (node.task?.is_summary === true) {
    return "summary";
  }
  return node.task?.is_milestone === true ? "milestone" : "task";
}

/** Render the icon of the nature of a row, named for it. */
export function RowNatureIcon({ node }: { readonly node: NatureOf }) {
  const t = useTranslations("rowNature");
  const nature = rowNature(node);
  const Icon = ROW_NATURE_ICONS[nature];
  return (
    <Icon role="img" aria-label={t(nature)} className="size-3.5 shrink-0 text-muted-foreground" />
  );
}
