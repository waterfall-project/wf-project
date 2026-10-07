// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the remaining to commit that show more than a value formatted: the mark
 * of a task started whose finish is past the date of calculation (WF-RAE-0040), which the server
 * says (`finish_overdue`) — never deduced here from the finish and a date. It is a mark of its own,
 * an icon named by the catalogue, never a zone of the scale of signals, which the server alone
 * gives (`Signal`, WF-ARC-0020).
 */
"use client";

import { CalendarX2 } from "lucide-react";
import { useTranslations } from "next-intl";

/** Render the mark of a task whose finish is past; nothing for the others, nor for a line. */
export function OverdueCell({
  node,
}: {
  readonly node: { readonly task?: { readonly finish_overdue: boolean } | null };
}) {
  const t = useTranslations("remainingGrid");
  if (node.task?.finish_overdue !== true) {
    return null;
  }
  return (
    <CalendarX2 role="img" aria-label={t("finishOverdue")} className="inline size-3.5">
      <title>{t("finishOverdue")}</title>
    </CalendarX2>
  );
}
