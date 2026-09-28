// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { type FakeClient, fakeClient } from "@/test/fixtures";

import RootLayout, { generateMetadata } from "./layout";

const server = vi.hoisted(() => ({
  client: undefined as FakeClient | undefined,
  acceptLanguage: "",
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": server.acceptLanguage })),
}));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));

/** A request from a browser asking for a language, by an account that follows it. */
function request(acceptLanguage: string) {
  server.client = fakeClient({ "GET /me": "me", "GET /installation": "installation" });
  server.acceptLanguage = acceptLanguage;
}

describe("RootLayout", () => {
  it("renders a page inside the shell, in English for a browser asking for English [WF-INTF-0160-A]", async () => {
    request("en-US,en;q=0.9");
    const html = renderToStaticMarkup(await RootLayout({ children: <p>page</p> }));
    expect(html).toMatch(/^<html lang="en"><head><\/head><body><header>/);
    expect(html).toMatch(/<label for="[^"]+">Language<\/label>/);
    expect(html).toContain('<option value="default" selected="">Browser language</option>');
    expect(html).toContain("<p>page</p></body></html>");
  });

  it("renders in French for a browser asking for French [WF-INTF-0160-A]", async () => {
    request("fr-FR,fr;q=0.9");
    const html = renderToStaticMarkup(await RootLayout({ children: <p>page</p> }));
    expect(html).toMatch(/^<html lang="fr">/);
    expect(html).toMatch(/<label for="[^"]+">Langue<\/label>/);
  });

  it("offers no language to choose without a session: the browser decides", async () => {
    const unauthorized = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;
    server.client = fakeClient({ "GET /me": unauthorized });
    server.acceptLanguage = "en";
    const html = renderToStaticMarkup(await RootLayout({ children: <p>page</p> }));
    expect(html).toBe(
      '<html lang="en"><head></head><body><header></header><p>page</p></body></html>',
    );
  });

  it("titles the document with the product, from the catalogue", async () => {
    request("en");
    expect((await generateMetadata()).title).toBe("Waterfall");
  });
});
