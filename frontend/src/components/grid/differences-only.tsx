// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * « Écarts seulement » (US-0700), above the grid of a differential and the grid of the comparison
 * of two revisions: the button that retains the differences alone, pressed when the address names
 * all three (`difference-filter.ts`). A server component that hands the browser's button its text
 * and its state.
 */
import { useTranslations } from "next-intl";

import { type DifferenceValue, isDifferencesOnly } from "./difference-filter";
import { DifferenceFilterToggle } from "./difference-filter-toggle";

/** Render the button « Écarts seulement », pressed when `filter` retains every difference. */
export function DifferencesOnly({
  filter,
  offered = true,
}: {
  readonly filter: readonly DifferenceValue[] | undefined;
  /** Whether the structure read bears differences: a differential does, no other structure. */
  readonly offered?: boolean;
}) {
  const t = useTranslations("grid.differenceFilter");
  return offered ? (
    <DifferenceFilterToggle label={t("label")} pressed={isDifferencesOnly(filter)} />
  ) : null;
}
