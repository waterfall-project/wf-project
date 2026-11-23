// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { OccurredCost, type RiskCoverage, RiskCoverageSummary } from "./risk-coverage";

/** The coverage of the witness, the lines merged by the occurrence of 752 reestimated (#2002). */
const REESTIMATED = example("risk_coverage_reestimated") as RiskCoverage;

/** A component of the coverage, in English. */
function show(node: ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {node}
    </NextIntlClientProvider>,
  );
}

describe("the cost of the occurred risks and their reestimated cost", () => {
  it("shows the reestimated of the occurred apart from their cost at occurrence, each beside its own amount [WF-RIS-0050-A]", () => {
    expect(REESTIMATED.occurred_cost).not.toBe(REESTIMATED.occurred_reestimated);
    show(<OccurredCost coverage={REESTIMATED} />);
    const reestimated = screen.getByText("Reestimated cost of the occurred risks (information)");
    expect(reestimated.parentElement?.textContent).toContain("300.00");
    expect(reestimated.parentElement?.textContent).not.toContain("200.00");
    const cost = screen.getByText("200.00");
    expect(cost.parentElement?.textContent).not.toContain("300.00");
  });

  it("leaves the coverage variance as the server computed it, the reestimated being no term of it [WF-RIS-0050-A]", () => {
    show(<RiskCoverageSummary coverage={REESTIMATED} />);
    expect(screen.getByText("349,860.00")).toBeTruthy();
    const field = screen.getByText("Cost of the occurred risks").closest("div");
    expect(field).not.toBeNull();
    expect(within(field as HTMLElement).getByText("200.00")).toBeTruthy();
    expect(within(field as HTMLElement).getByText("300.00")).toBeTruthy();
  });
});
