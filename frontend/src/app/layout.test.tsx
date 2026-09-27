// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import RootLayout, { metadata } from "./layout";

describe("RootLayout", () => {
  it("renders a page inside the document", () => {
    const html = renderToStaticMarkup(
      <RootLayout>
        <p>page</p>
      </RootLayout>,
    );
    expect(html).toContain('<html lang="fr">');
    expect(html).toContain("<body><p>page</p></body>");
  });

  it("titles the document with the product", () => {
    expect(metadata.title).toBe("Waterfall");
  });
});
