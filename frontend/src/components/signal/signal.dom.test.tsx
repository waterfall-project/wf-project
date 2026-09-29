// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";

import { type AlertZone, Signal, type SignalProps } from "./signal";

// The zones of the contract, as the catalogues name them; `make catalogs` holds the two lists
// equal.
const ZONES = Object.keys(CATALOGUES.fr.enums.AlertZone) as AlertZone[];
type Variant = NonNullable<SignalProps["variant"]>;

const VARIANTS: readonly Variant[] = ["label", "icon"];
const LOCALES: readonly Locale[] = ["fr", "en"];

/** A signal of a zone, in a page of a language. */
function page(zone: AlertZone, variant: Variant, locale: Locale) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <Signal zone={zone} variant={variant} />
    </NextIntlClientProvider>
  );
}

/**
 * What a signal shows once its colour is gone: its shape, its name, and its markup stripped
 * of all that is not seen — its classes, and so its colour; its name for assistive
 * technologies and for the pointer (`aria-*`, `role`, `title`).
 */
function uncoloured(zone: AlertZone, variant: Variant, locale: Locale) {
  const { container, unmount } = render(page(zone, variant, locale));
  const signal = container.firstElementChild;
  if (signal === null) {
    throw new Error(`No signal for ${zone}`);
  }
  const name = signal.textContent || (signal.getAttribute("aria-label") ?? "");
  const copy = signal.cloneNode(true) as Element;
  for (const element of [copy, ...copy.querySelectorAll("*")]) {
    for (const attribute of [...element.getAttributeNames()]) {
      if (/^(class|style|role|title|aria-.*)$/.test(attribute)) {
        element.removeAttribute(attribute);
      }
    }
  }
  const shape = copy.querySelector("svg")?.innerHTML ?? "";
  unmount();
  return { seen: copy.outerHTML, shape, name };
}

/** Whether the values of a list are all different. */
function allDistinct(values: readonly string[]): boolean {
  return new Set(values).size === values.length && values.every((value) => value !== "");
}

describe("a signal", () => {
  it("shows the zone the API gave by its shape, its name and its token", () => {
    const { container } = render(
      <>
        {ZONES.map((zone) => (
          <NextIntlClientProvider key={zone} locale="fr" messages={CATALOGUES.fr}>
            <Signal zone={zone} />
          </NextIntlClientProvider>
        ))}
      </>,
    );
    const signals = [...container.children];
    expect(signals.map((signal) => signal.textContent)).toEqual(["Nominal", "Vigilance", "Alerte"]);
    ZONES.forEach((zone, at) => {
      expect(signals[at]).toHaveClass(`text-signal-${zone}`);
      expect(signals[at]?.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    });
  });

  it("gives its icon alone a name, for a dense grid or a matrix", () => {
    render(page("watch", "icon", "en"));
    const signal = screen.getByRole("img", { name: "Watch" });
    expect(signal).toHaveAttribute("title", "Watch");
    expect(signal).toHaveClass("text-signal-watch");
    expect(signal).toHaveTextContent("");
    expect(signal.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it.each(LOCALES)("names each zone in %s from the catalogue", (locale) => {
    for (const zone of ZONES) {
      const { unmount } = render(page(zone, "icon", locale));
      expect(screen.getByRole("img")).toHaveAccessibleName(
        CATALOGUES[locale].enums.AlertZone[zone],
      );
      unmount();
    }
  });

  it.each(VARIANTS)(
    "leaves each signal identifiable in a grey copy, as %s [WF-IHM-0070-A]",
    (variant) => {
      // Une copie d'écran en niveaux de gris laisse identifier chaque signalement : a grey
      // copy keeps the shape and the name, and each zone has its own of both.
      for (const locale of LOCALES) {
        const signals = ZONES.map((zone) => uncoloured(zone, variant, locale));
        expect(allDistinct(signals.map((signal) => signal.shape))).toBe(true);
        expect(signals.map((signal) => signal.name)).toEqual(
          ZONES.map((zone) => CATALOGUES[locale].enums.AlertZone[zone]),
        );
        expect(allDistinct(signals.map((signal) => signal.name))).toBe(true);
      }
    },
  );

  it.each(VARIANTS)(
    "never tells two zones apart by the colour alone, as %s [WF-IHM-0070-A]",
    (variant) => {
      // Aucun écran ne distingue deux états par la seule couleur : with every class — and so
      // every colour — taken away, and every name that is not seen, no two zones look alike.
      const seen = ZONES.map((zone) => uncoloured(zone, variant, "fr").seen);
      expect(allDistinct(seen)).toBe(true);
    },
  );

  it.each(VARIANTS)("breaks no rule of accessibility, as %s", async (variant) => {
    const { container } = render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        {ZONES.map((zone) => (
          <Signal key={zone} zone={zone} variant={variant} />
        ))}
      </NextIntlClientProvider>,
    );
    await expectAccessible(container);
  });
});
