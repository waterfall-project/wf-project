// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CurrencyProvider } from "@/currency/context";
import { CATALOGUES } from "@/i18n/catalogues";

import { Amount } from "./amount";

/** The amount in French, under the currency of the installation (none when unknown). */
function shown(currency: string | undefined): string {
  const { container } = render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <CurrencyProvider currency={currency}>
        <Amount value="1234.5" />
      </CurrencyProvider>
    </NextIntlClientProvider>,
  );
  return container.textContent;
}

describe("an amount", () => {
  it("closes with the currency of the installation [WF-REF-0140-A]", () => {
    expect(shown("EUR")).toMatch(/^1\s234,50\s€$/);
  });

  it("is shown bare when the currency of the installation is unknown [WF-REF-0140-A]", () => {
    expect(shown(undefined)).toMatch(/^1\s234,50$/);
  });
});
