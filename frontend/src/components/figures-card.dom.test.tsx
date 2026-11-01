// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import type { CalculationContext } from "@/components/context/indicator";
import { ComputedTotal } from "@/components/computed-amount";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { ProvisionSummary } from "@/components/risks/provision-totals";
import { RiskCoverageSummary } from "@/components/risks/risk-coverage";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { FiguresCard, FiguresGrid, FiguresList } from "./figures-card";

type Totals = Parameters<typeof ProvisionSummary>[0]["totals"];
type Coverage = Parameters<typeof RiskCoverageSummary>[0]["coverage"];

/** Render in a language, as the shell hands its texts to a screen. */
function renderIn(locale: Locale, ui: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {ui}
    </NextIntlClientProvider>,
  );
}

describe("a card of figures", () => {
  it("is a region named by its title, its figures a list of terms read as a name then its value", () => {
    renderIn(
      "en",
      <FiguresGrid>
        <FiguresCard title="Totals">
          <FiguresList>
            <ComputedTotal name="Identified" amount="500000.00" />
            <ComputedTotal name="Occurred" amount="60.00" />
          </FiguresList>
        </FiguresCard>
      </FiguresGrid>,
    );
    const card = screen.getByRole("region", { name: "Totals" });
    expect(within(card).getByRole("heading", { name: "Totals" })).toBeTruthy();
    const terms = within(card).getAllByRole("term");
    expect(terms.map((term) => term.textContent)).toEqual(["Identified", "Occurred"]);
    expect(within(card).getAllByRole("definition")).toHaveLength(2);
  });

  it("says the date its figures are computed at when the answer has a context, and none otherwise", () => {
    const context: CalculationContext = {
      revision_id: "01926f3a-7c00-7000-8000-000000000102",
      computed_at: "2026-06-03T14:05:00Z",
      scope: "project",
      revision_status: "draft",
      is_stored: false,
    };
    const { container } = renderIn(
      "fr",
      <FiguresGrid>
        <FiguresCard title="Dated" context={context}>
          <p>x</p>
        </FiguresCard>
        <FiguresCard title="Undated">
          <p>y</p>
        </FiguresCard>
      </FiguresGrid>,
    );
    const dated = screen.getByRole("region", { name: "Dated" });
    expect(dated.querySelector("time")?.getAttribute("datetime")).toBe("2026-06-03T14:05:00Z");
    expect(screen.getByRole("region", { name: "Undated" }).querySelector("time")).toBeNull();
    expect(container.querySelectorAll("time")).toHaveLength(1);
  });
});

describe("the cards of the risks", () => {
  it("shows the three totals — identified, occurred, dismissed — and the general total in a card, the reserve of the reference in the card of the coverage beside it [WF-RIS-0040-A]", async () => {
    const risks = example("risks") as { totals: Totals };
    const coverage = example("risk_coverage") as Coverage;
    const { container } = renderIn(
      "en",
      <FiguresGrid>
        <ProvisionSummary totals={risks.totals} />
        <RiskCoverageSummary coverage={coverage} />
      </FiguresGrid>,
    );
    const provisions = screen.getByRole("region", { name: "Provisions of the risks retained" });
    expect(
      within(provisions)
        .getAllByRole("term")
        .map((term) => term.textContent),
    ).toEqual(["Identified risks", "Occurred risks", "Dismissed risks", "General total"]);
    const covered = screen.getByRole("region", { name: "Risk coverage" });
    expect(within(covered).getAllByRole("term")[0]?.textContent).toBe("Risk reserve");
    expect(within(provisions).queryByText("Risk reserve")).toBeNull();
    await expectAccessible(container);
  });
});
