// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LAST_CONTEXT_COOKIE } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import RootLayout, { generateMetadata } from "./layout";

const server = vi.hoisted(() => ({
  client: undefined as FakeClient | undefined,
  acceptLanguage: "",
  cookie: undefined as string | undefined,
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": server.acceptLanguage })),
  cookies: () =>
    Promise.resolve({
      get: (name: string) =>
        name === LAST_CONTEXT_COOKIE && server.cookie !== undefined
          ? { name, value: server.cookie }
          : undefined,
    }),
}));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
// The home page: the address the navigation reads, as the router of Next would give it.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;
const LAST =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102/risks";

/** A request from a browser asking for a language, by an account and its session. */
function request(acceptLanguage: string, answers: FakeAnswers = {}) {
  server.client = fakeClient({
    "GET /me": "me",
    "GET /session": "session",
    "GET /installation": "installation",
    ...answers,
  });
  server.acceptLanguage = acceptLanguage;
}

/** The document the layout renders around a page. */
async function page(): Promise<string> {
  return renderToStaticMarkup(await RootLayout({ children: <p>page</p> }));
}

beforeEach(() => {
  server.cookie = undefined;
});

describe("RootLayout", () => {
  it("renders a page inside the shell, in English for a browser asking for English [WF-INTF-0160-A]", async () => {
    request("en-US,en;q=0.9");
    const html = await page();
    expect(html).toMatch(/^<html lang="en" class="font-geist-sans"><head><\/head><body>/);
    expect(html).toMatch(/<label for="[^"]+">Language<\/label>/);
    expect(html).toContain('<option value="default" selected="">Browser language</option>');
    expect(html).toContain("<p>page</p>");
  });

  it("renders in French for a browser asking for French [WF-INTF-0160-A]", async () => {
    request("fr-FR,fr;q=0.9");
    const html = await page();
    expect(html).toMatch(/^<html lang="fr"/);
    expect(html).toMatch(/<label for="[^"]+">Langue<\/label>/);
  });

  it("lets the workstation decide the mode of an account that follows it", async () => {
    request("fr");
    const html = await page();
    expect(html).not.toContain("data-theme");
    expect(html).toContain('<option value="default" selected="">Réglage du poste</option>');
    expect(html).toContain(
      '<source srcSet="/waterfall_logo-dark.svg" media="(prefers-color-scheme: dark)"/>',
    );
  });

  it("forces the mode the account chose on the whole document", async () => {
    request("fr", { "GET /me": "me_dark" });
    const html = await page();
    expect(html).toMatch(/^<html lang="fr" data-theme="dark"/);
    expect(html).toContain('<option value="dark" selected="">Sombre</option>');
    expect(html).toContain('<source srcSet="/waterfall_logo-dark.svg" media="all"/>');
  });

  it("offers the functions of the session, and leads back to the project the cookie kept", async () => {
    request("fr");
    server.cookie = `${LAST}?as_of=2026-05-31`;
    const html = await page();
    expect(html).toContain('<nav aria-label="Fonctions"');
    expect(html).toContain('href="/portfolio/projects"');
    expect(html).toContain(`href="${LAST}?as_of=2026-05-31"><svg`);
    expect(html).toContain("Retour au projet</a>");
  });

  it("leads nowhere from a cookie that names no project", async () => {
    request("fr");
    server.cookie = "https://elsewhere.example/";
    expect(await page()).not.toContain("Retour au projet");
  });

  it("offers neither selectors nor functions without a session: the browser decides", async () => {
    request("en", { "GET /me": UNAUTHORIZED, "GET /session": UNAUTHORIZED });
    const html = await page();
    expect(html).toMatch(/^<html lang="en" class="font-geist-sans">/);
    expect(html).not.toContain("<select");
    expect(html).not.toContain("<nav");
    expect(html).toContain('alt="Waterfall"');
    expect(html).toContain("<p>page</p>");
  });

  it("titles the document with the product, from the catalogue", async () => {
    request("en");
    expect((await generateMetadata()).title).toBe("Waterfall");
  });
});
