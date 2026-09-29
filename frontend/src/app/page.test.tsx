// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SCREEN } from "@/components/shell/page-header";
import { CATALOGUES } from "@/i18n/catalogues";

import HomePage from "./page";

describe("HomePage", () => {
  it("names the product, from the catalogue", () => {
    const html = renderToStaticMarkup(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        <HomePage />
      </NextIntlClientProvider>,
    );
    // In the template of a dense screen, its heading with an icon.
    expect(html).toMatch(new RegExp(`^<main class="${SCREEN.dense}">`));
    expect(html).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true".*<\/svg>Waterfall<\/h1>/);
  });
});
