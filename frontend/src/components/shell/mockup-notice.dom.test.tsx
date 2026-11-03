// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { MockupNotice } from "./mockup-notice";

const LOCALES = ["fr", "en"] as const;

describe("MockupNotice (US-0760)", () => {
  it.each(LOCALES)(
    "dit les filtres non appliqués, en une seule note, sur une liste (%s)",
    (locale) => {
      render(
        <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
          <MockupNotice lists />
        </NextIntlClientProvider>,
      );
      const notes = screen.getAllByRole("note");
      expect(notes).toHaveLength(1);
      expect(notes[0]?.textContent).toContain(CATALOGUES[locale].mockup.notKept);
      expect(notes[0]?.textContent).toContain(CATALOGUES[locale].mockup.notFiltered);
    },
  );

  it.each(LOCALES)("ne dit que l'écriture sans `lists` (%s)", (locale) => {
    render(
      <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
        <MockupNotice />
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("note").textContent).not.toContain(
      CATALOGUES[locale].mockup.notFiltered,
    );
  });
});
