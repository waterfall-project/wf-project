// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import HomePage from "./page";

describe("HomePage", () => {
  it("names the product, from the catalogue", () => {
    const html = renderToStaticMarkup(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        <HomePage />
      </NextIntlClientProvider>,
    );
    expect(html).toBe("<main><h1>Waterfall</h1></main>");
  });
});
