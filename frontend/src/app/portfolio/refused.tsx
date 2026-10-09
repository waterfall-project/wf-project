// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A view of the portfolio whose period the server refuses (422, `PortfolioPeriodRefused`, EP-02/L42f):
 * an end before the start, the rule of every period of the contract, `params.minimum` the start
 * given. The view is not read: its title stands without a perimeter retained, the perimeter of the
 * address stays to be changed — the end said at its field, the start named, as the actual costs say
 * it —, and a sentence stands for the figures. Any other answer follows the rule of the reads.
 */
import "server-only";

import { useTranslations } from "next-intl";

import { type Answer, readOrRefused } from "@/api/problem";
import { type PeriodRefusals, refusedPeriod } from "@/components/grid/period";
import type { Perimeter, Takes } from "@/components/portfolio/address";
import { type NodeChoice, PerimeterBar } from "@/components/portfolio/perimeter";
import { PortfolioHeader, type PortfolioFunction } from "@/components/portfolio/portfolio-header";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { Screen } from "@/components/shell/page-header";

/** The refusal of a period the server cannot apply (422). */
const PERIOD_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/** A view read, or the sides of its period the server refused. */
export type ViewRead<T> =
  | { readonly kind: "read"; readonly data: T }
  | { readonly kind: "refused"; readonly refused: PeriodRefusals | undefined };

/** Read a view of the portfolio, or the period the server refuses of it. */
export async function readView<T>(
  operation: string,
  call: () => Promise<Answer<T>>,
): Promise<ViewRead<T>> {
  const read = await readOrRefused(operation, PERIOD_REFUSED, call);
  return read.kind === "read"
    ? { kind: "read", data: read.data }
    : { kind: "refused", refused: refusedPeriod(read.problem.fields ?? []) };
}

/** Render a view of the portfolio whose period the server refused, its perimeter kept. */
export function RefusedView({
  fn,
  perimeter,
  refused,
  takes,
  nodes,
}: {
  readonly fn: PortfolioFunction;
  readonly perimeter: Perimeter;
  readonly refused: PeriodRefusals | undefined;
  readonly takes?: Takes;
  readonly nodes?: readonly NodeChoice[];
}) {
  const t = useTranslations("portfolio");
  return (
    <Screen density={FUNCTION_DENSITY[fn]}>
      <PortfolioHeader fn={fn} scope={undefined} />
      <PerimeterBar
        perimeter={perimeter}
        refused={refused}
        {...(takes === undefined ? {} : { takes })}
        {...(nodes === undefined ? {} : { nodes })}
      />
      <p className="text-sm text-destructive">{t("periodRefused")}</p>
    </Screen>
  );
}
