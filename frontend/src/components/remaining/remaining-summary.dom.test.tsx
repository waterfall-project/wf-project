// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CurrencyProvider } from "@/currency/context";
import { CATALOGUES } from "@/i18n/catalogues";

import { RemainingSummary } from "./remaining-summary";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the summary of the remaining to commit in a narrow window", () => {
  it("says the indicators unavailable outside the fold, where the notice stays in view [WF-IHM-0020]", () => {
    vi.stubGlobal(
      "matchMedia",
      (query: string): MediaQueryList =>
        ({
          matches: false,
          media: query,
          addEventListener: () => undefined,
          removeEventListener: () => undefined,
        }) as unknown as MediaQueryList,
    );
    const { container } = render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <CurrencyProvider currency="EUR">
          <RemainingSummary indicators={undefined} currency="EUR" />
        </CurrencyProvider>
      </NextIntlClientProvider>,
    );
    const notice = screen.getByText(CATALOGUES.en.remainingSummary.unavailable);
    expect(notice).toBeVisible();
    expect(notice.closest("details")).toBeNull();
    expect(container.querySelector("details")).toBeNull();
  });
});
