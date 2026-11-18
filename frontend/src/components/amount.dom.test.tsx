// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CurrencyProvider } from "@/currency/context";
import { CATALOGUES } from "@/i18n/catalogues";

import { Amount } from "./amount";

/** The amount in French, under the currency of the installation (none when unknown). */
function shown(currency: string | undefined, value = "1234.5", signed = false): string {
  const { container } = render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <CurrencyProvider currency={currency}>
        <Amount value={value} signed={signed} />
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

  it("writes a plus in front of a positive amount when it is signed, as the columns of difference do [WF-IHM-0150-A]", () => {
    expect(shown("EUR", "1234.5", true)).toMatch(/^\+1\s234,50\s€$/);
  });

  it("writes nothing more in front of zero nor of a negative amount when it is signed [WF-IHM-0150-A]", () => {
    expect(shown("EUR", "0", true)).toMatch(/^0,00\s€$/);
    expect(shown("EUR", "-12.5", true)).toMatch(/^[-−]12,50\s€$/);
  });
});
