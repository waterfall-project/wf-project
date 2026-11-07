// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { ProjectFacts } from "./project-facts";

/** The six states of the table of the specification (3.3.2): code, then label in each language. */
const SPEC_STATES = [
  ["created", "Créé", "Created"],
  ["pricing", "Chiffrage", "Pricing"],
  ["in_progress", "En cours", "In progress"],
  ["completed", "Terminé", "Completed"],
  ["lost", "Perdu", "Lost"],
  ["abandoned", "Abandonné", "Abandoned"],
] as const;

describe("the facts at the head of a project", () => {
  it.each(["fr", "en"] as const)(
    "write the label of each of the six states of the table of the specification, in %s [WF-CYC-0010-A]",
    (locale) => {
      const project = example("project") as components["schemas"]["Project"];
      for (const [state, fr, en] of SPEC_STATES) {
        const { unmount } = render(
          <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
            <ProjectFacts project={{ ...project, state }} />
          </NextIntlClientProvider>,
        );
        const term = screen.getByText(locale === "fr" ? "État" : "State");
        expect(within(term.parentElement ?? document.body).getByRole("img")).toHaveAccessibleName(
          locale === "fr" ? fr : en,
        );
        unmount();
      }
    },
  );
});
