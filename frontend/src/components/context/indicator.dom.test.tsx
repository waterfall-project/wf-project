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

import { type Computable, ComputedIndicator, type IndicatorLabel } from "./indicator";

type ProjectIndicators = components["schemas"]["ProjectIndicators"];

// The indicators of the project at the date of the example; those the reference kept at its
// marking, before any actual cost, for the values that cannot be computed.
const INDICATORS = example("project_indicators") as ProjectIndicators;
const MARKED = example("project_indicators_marked") as ProjectIndicators;
const COMPUTED_AT = "2026-06-03T14:05:00Z";

/** A value the example holds. */
function held<T>(value: T | undefined): T {
  if (value === undefined) {
    throw new Error("The example lacks the value");
  }
  return value;
}

const PHYSICAL_PROGRESS = held(INDICATORS.physical_progress);

/** An indicator of an example, under the context of the same example, in a language. */
function page(
  label: IndicatorLabel,
  value: Computable,
  locale: Locale = "fr",
  context: ProjectIndicators["context"] = INDICATORS.context,
) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <ComputedIndicator indicator={label} value={value} context={context} />
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
    const { container } = render(page("indicator.names.physicalProgress", PHYSICAL_PROGRESS));
    expect(screen.getByRole("term")).toHaveTextContent("Avancement physique");
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual([
      "82,96\u00a0%",
      "Calculé le 3 juin 2026, 07:05",
    ]);
    const time = container.querySelector("time");
    expect(time).toHaveAttribute("datetime", COMPUTED_AT);
    expect(INDICATORS.context.computed_at).toBe(COMPUTED_AT);
    await expectAccessible(container);
  });

  it("leaves its date to what holds it and shows the date of the same context, once for all", () => {
    render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        <ComputedIndicator
          indicator="indicator.names.physicalProgress"
          value={PHYSICAL_PROGRESS}
          context={INDICATORS.context}
          date="held"
        />
      </NextIntlClientProvider>,
    );
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual(["82.96%"]);
  });

  it("shows a cost index without actual cost as not computable, with its reason and its date", async () => {
    const { container } = render(
      page("indicator.names.costIndex", MARKED.cost_index.value, "en", MARKED.context),
    );
    expect(screen.getByRole("term")).toHaveTextContent("Cost index");
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual([
      "Not computable",
      "No actual cost at the calculation date.",
      "Computed on 1 Feb 2026, 01:00",
    ]);
    expect(container).not.toHaveTextContent(/\b0\b|∞|Infinity|NaN/);
    await expectAccessible(container);
  });

  it("says why a value cannot be computed in the language of the interface, from the code the API gives", () => {
    const projection = MARKED.projections.at_observed_rate;
    expect(projection.reason).toBe("no_actual_cost");
    render(page("indicator.names.projectionAtObservedRate", projection, "fr", MARKED.context));
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual([
      "Non calculable",
      "Aucun coût réel à la date de calcul.",
      "Calculé le 1 févr. 2026, 01:00",
    ]);
  });

  it("says a value is missing rather than make one up, when the API leaves it out", () => {
    render(page("indicator.names.financialProgress", { is_computable: true, value: null }));
    expect(screen.getAllByRole("definition").map((item) => item.textContent)).toEqual([
      "Non calculable",
      "Calculé le 3 juin 2026, 07:05",
    ]);
  });

  it("leaves the date to the browser, which knows the time zone of the workstation", () => {
    const markup = renderToString(page("indicator.names.physicalProgress", PHYSICAL_PROGRESS));
    expect(markup).toContain(`Calculé le <time dateTime="${COMPUTED_AT}"></time>`);
  });

  it("shows a progress as a percentage, and an index as the decimal the API gave", () => {
    const quarter = { is_computable: true, value: "0.125", reason: null };
    render(page("indicator.names.budgetConsumption", quarter, "en"));
    render(page("indicator.names.scheduleIndex", INDICATORS.schedule_index.value, "en"));
    expect(
      screen
        .getAllByRole("definition")
        .map((item) => item.textContent)
        .filter((text) => !text.startsWith("Computed")),
    ).toEqual(["12.5%", "0.9879"]);
  });
});
