// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a test reads of the filters a page hands the bar of its grid (#2916/L6): the choice a menu
 * says on its closed button, in the markup of the page, and what the page gives `TreeFilters`.
 */
import type { ReactElement, ReactNode } from "react";

import type { TreeFiltersProps } from "@/components/grid/tree-filters";

/** What the closed menu of a label says of its choice; none when the page has no such menu. */
export function menuText(page: string, label: string): string | undefined {
  for (const match of page.matchAll(
    /<button[^>]*aria-haspopup="dialog"[^>]*>((?:(?!<\/button>).)*)<\/button>/g,
  )) {
    const text = (match[1] ?? "")
      .replace(/<[^>]*>/g, "")
      .replace(/\s+/g, " ")
      .trim();
    if (text.startsWith(label)) {
      return text.slice(label.length).trim();
    }
  }
  return undefined;
}

/** What the page gave `TreeFilters` for the bar of its grid. */
export function filtersOf(
  grid: { readonly treeFilters?: ReactNode } | undefined,
): TreeFiltersProps {
  return (grid?.treeFilters as ReactElement<TreeFiltersProps> | undefined)?.props ?? {};
}
