// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { type Computable, ComputedIndicator } from "./indicator";

type ProjectIndicators = components["schemas"]["ProjectIndicators"];

// The indicators of the project at the date of the example: no actual cost yet.
const INDICATORS = example("project_indicators") as ProjectIndicators;
const COMPUTED_AT = "2026-03-16T14:05:00Z";

/** A value the example holds. */
function held<T>(value: T | undefined): T {
  if (value === undefined) {
    throw new Error("The example lacks the value");
  }
  return value;
}

const PHYSICAL_PROGRESS = held(INDICATORS.physical_progress);

/** An indicator of the example, in a page of a language. */
function page(label: string, value: Computable, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <ComputedIndicator label={label} value={value} context={INDICATORS.context} />
    </NextIntlClientProvider>
  );
}

describe("an indicator", () => {
  const original = process.env.TZ;

  beforeEach(() => {
    process.env.TZ = "America/Los_Angeles";
  });

  afterEach(() => {
    process.env.TZ = original;
  });

  it("bears the date it is computed at, in the local time of the workstation [WF-IHM-0020-A]", async () => {
    // Un indicateur affiché porte sa date de calcul.
    const { container } = render(page("Avancement physique", PHYSICAL_PROGRESS));
    expect(screen.getByRole("term")).toHaveTextContent("Avancement physique");
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual([
      "0,25",
      "Calculé le 16 mars 2026, 07:05",
    ]);
    const time = container.querySelector("time");
    expect(time).toHaveAttribute("datetime", COMPUTED_AT);
    expect(INDICATORS.context.computed_at).toBe(COMPUTED_AT);
    await expectAccessible(container);
  });

  it("shows a cost index without actual cost as not computable, with its reason and its date [WF-IND-0010-A]", async () => {
    // Un indice de coût sans coût réel est affiché non calculable.
    const { container } = render(page("Cost index", INDICATORS.cost_index.value, "en"));
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual([
      "Not computable",
      "Aucun coût réel à la date de calcul : le dénominateur de l’indice est nul.",
      "Computed on Mar 16, 2026, 7:05 AM",
    ]);
    expect(container).not.toHaveTextContent(/\b0\b|∞|Infinity|NaN/);
    await expectAccessible(container);
  });

  it("says a value is missing rather than make one up, when the API leaves it out", () => {
    render(page("Avancement financier", { is_computable: true, value: null }));
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual([
      "Non calculable",
      "Calculé le 16 mars 2026, 07:05",
    ]);
  });

  it("leaves the date to the browser, which knows the time zone of the workstation", () => {
    const markup = renderToString(page("Avancement physique", PHYSICAL_PROGRESS));
    expect(markup).toContain(`Calculé le <time dateTime="${COMPUTED_AT}"></time>`);
  });
});
