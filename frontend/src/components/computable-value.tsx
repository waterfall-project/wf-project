// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A value that may not be computable (`Computable`): shown by the format the caller gives it, or
 * said not computable and why — never zero, never invented (WF-IHM-0030, WF-ARC-0020). Neutral to
 * the screens that use it: the portfolio, the remaining to commit, the estimate.
 */
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";

type Computable = components["schemas"]["Computable"];

/** A value that may not be computable: shown by `format`, or said not computable and why. */
export function ComputableValue({
  value,
  format,
}: {
  readonly value: Computable;
  readonly format: (value: string) => ReactNode;
}) {
  const t = useTranslations();
  const computed = value.is_computable ? (value.value ?? null) : null;
  if (computed !== null) {
    return format(computed);
  }
  const reason = value.reason ?? null;
  return reason === null
    ? t("indicator.notComputable")
    : t("projectIndicators.notComputable", { reason: t(`enums.NotComputableReason.${reason}`) });
}
