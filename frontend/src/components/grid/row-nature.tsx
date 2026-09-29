// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The nature of a row of a structure, shown by its icon (charter, guide « Charte graphique »):
 * a summary task, a milestone, a task, a line of the estimate — read from the node as the API
 * gives it, its kind and the flags of its task, never deduced from its figures. The icon bears
 * the name of the nature: in a dense grid it stands alone in its cell.
 */
import { ClipboardList, Diamond, Folder, type LucideIcon, Receipt } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";

/** The nature of a row. */
export type RowNature = "summary" | "milestone" | "task" | "estimateLine";

/** A node of a structure, as the API reads it. */
type Node = components["schemas"]["Node"];

const ICONS: Readonly<Record<RowNature, LucideIcon>> = {
  summary: Folder,
  milestone: Diamond,
  task: ClipboardList,
  estimateLine: Receipt,
};

/** The nature of a node, from its kind and the flags of its task. */
export function rowNature(node: Node): RowNature {
  if (node.kind === "estimate_line") {
    return "estimateLine";
  }
  if (node.task?.is_summary === true) {
    return "summary";
  }
  return node.task?.is_milestone === true ? "milestone" : "task";
}

/** Render the icon of the nature of a row, named for it. */
export function RowNatureIcon({ node }: { readonly node: Node }) {
  const t = useTranslations("rowNature");
  const nature = rowNature(node);
  const Icon = ICONS[nature];
  return (
    <Icon role="img" aria-label={t(nature)} className="size-4 shrink-0 text-muted-foreground" />
  );
}
