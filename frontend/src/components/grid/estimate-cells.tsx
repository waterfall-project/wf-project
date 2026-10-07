// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the estimate that show more than a value formatted: the mark of a line
 * that employs a deactivated object of the reference data — a category, a role or a nature
 * deactivated since (WF-REF-0010) —, which the server says (`uses_inactive_object`). It is a mark
 * of its own, an icon named by the catalogue, never a zone of the scale of signals, which the
 * front never deduces (`Signal`, WF-ARC-0020); the grid deduces nothing from the lists of the
 * reference data either.
 */
"use client";

import { ToggleLeft } from "lucide-react";
import { useTranslations } from "next-intl";

import type { EstimateNode } from "./estimate";

/** Render the mark of a line that employs a deactivated object; nothing for the others. */
export function InactiveObjectCell({ node }: { readonly node: EstimateNode }) {
  const t = useTranslations("estimateGrid");
  if (node.estimate_line?.uses_inactive_object !== true) {
    return null;
  }
  return (
    <ToggleLeft role="img" aria-label={t("usesInactiveObject")} className="inline size-3.5">
      <title>{t("usesInactiveObject")}</title>
    </ToggleLeft>
  );
}
