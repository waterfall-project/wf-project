// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CurrencyProvider } from "@/currency/context";
import { CATALOGUES } from "@/i18n/catalogues";

import { PENDING_DAY, useChipKit } from "./chip-kit";

// What the chips of the filters of a flat table are made of (WF-IHM-0130, #2916): a period told in
// the days of the workstation once the browser knows them, the bounds of a column of figures in
// each of their kinds.

const FROM = "2026-03-01T00:00:00.000Z";
const TO = "2026-03-06T00:00:00.000Z";

/** Every chip a kit builds, told in a paragraph each. */
function Told({ build }: { readonly build: (kit: ReturnType<typeof useChipKit>) => void }) {
  const kit = useChipKit();
  build(kit);
  return kit.chips.map((chip) => <p key={chip.key}>{chip.value}</p>);
}

function inFrench(build: (kit: ReturnType<typeof useChipKit>) => void, currency?: string) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <CurrencyProvider currency={currency}>
        <Told build={build} />
      </CurrencyProvider>
    </NextIntlClientProvider>
  );
}

describe("the chips of a period before the browser", () => {
  it.each(["day", "instant"] as const)(
    "tell no bound of a period of %s, whose zone the server does not know [WF-IHM-0130-A]",
    (kind) => {
      const html = renderToStaticMarkup(
        inFrench((kit) => {
          kit.period("period", "Date", kind, { from: FROM, to: TO });
        }),
      );
      expect(html).toBe(`<p>du ${PENDING_DAY} au ${PENDING_DAY}</p>`);
    },
  );

  it("tells a period of days of planning as it is, whatever the zone [WF-IHM-0130-A]", () => {
    const html = renderToStaticMarkup(
      inFrench((kit) => {
        kit.period("period", "Pièces", "date", { from: "2026-04-01", to: undefined });
      }),
    );
    expect(html).toBe("<p>depuis le 1 avr. 2026</p>");
  });
});

describe("the chips of the bounds of a column of figures", () => {
  /** The chips of some bounds, told in the browser. */
  function told(
    kind: "bytes" | "money" | "decimal",
    bounds: { min?: string; max?: string },
    currency?: string,
  ): string {
    const { container } = render(
      inFrench((kit) => {
        kit.bounds("size", "Taille", kind, { min: bounds.min, max: bounds.max });
      }, currency),
    );
    return (container.textContent ?? "").replace(/\s/g, " ");
  }

  it("tell a size in bytes by its unit, an amount with its currency, a decimal as it is [WF-IHM-0130-A]", () => {
    expect(told("bytes", { min: "1024", max: "2097152" })).toBe("de 1 kilooctet à 2 mégaoctets");
    expect(told("money", { min: "10.5", max: "20" }, "EUR")).toBe("de 10,50 € à 20,00 €");
    expect(told("decimal", { min: "1.25", max: "3" })).toBe("de 1,25 à 3");
  });

  it("tell a side alone, the least or the most [WF-IHM-0130-A]", () => {
    expect(told("decimal", { min: "2" })).toBe("2 au moins");
    expect(told("decimal", { max: "9" })).toBe("9 au plus");
    expect(told("decimal", {})).toBe("");
  });
});
