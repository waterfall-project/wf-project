// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CurrencyProvider } from "@/currency/context";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { type EstimateIndicators, EstimateSummary, type MissingRates } from "./estimate-summary";

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderAt(large: boolean, indicators: EstimateIndicators | undefined) {
  vi.stubGlobal(
    "matchMedia",
    (query: string): MediaQueryList =>
      ({
        matches: large,
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList,
  );
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <CurrencyProvider currency="EUR">
        <EstimateSummary
          indicators={indicators}
          missingRates={example("missing_rates_none") as MissingRates}
          permissions={[]}
          currency="EUR"
        />
      </CurrencyProvider>
    </NextIntlClientProvider>,
  );
}

describe("the summary of the estimate in a narrow window", () => {
  const indicators = example("estimate_indicators") as EstimateIndicators;

  it("folds the cards below 1024 points, the summary naming them [WF-IHM-0100-A]", () => {
    const { container } = renderAt(false, indicators);
    const details = container.querySelector("details");
    expect(details).not.toBeNull();
    expect(details?.open).toBe(false);
    expect(screen.getByText(CATALOGUES.en.estimateSummary.fold)).toBeVisible();
    expect(screen.getAllByRole("region", { hidden: true })[0]).not.toBeVisible();
  });

  it("leaves the cards open from 1024 points [WF-IHM-0100-A]", () => {
    const { container } = renderAt(true, indicators);
    expect(container.querySelector("details")?.open).toBe(true);
    expect(screen.getAllByRole("region")[0]).toBeVisible();
  });

  it("says the indicators unavailable outside the fold [WF-IHM-0020]", () => {
    const { container } = renderAt(false, undefined);
    expect(screen.getByText(CATALOGUES.en.estimateSummary.unavailable)).toBeVisible();
    expect(container.querySelector("details")).toBeNull();
  });
});
