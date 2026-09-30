// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient, Unreachable } from "@/api/client";
import { SignedOut } from "@/api/problem";
import { SCREEN } from "@/components/shell/page-header";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import HomePage, { generateMetadata } from "./page";

const server = vi.hoisted(
  (): { answers: FakeAnswers; clients: FakeClient[]; unreachable: boolean } => ({
    answers: {},
    clients: [],
    unreachable: false,
  }),
);

vi.mock("@/api/server", () => ({
  serverClient: () => {
    if (server.unreachable) {
      return createApiClient({
        address: "http://unreachable.invalid",
        fetch: () => Promise.reject(new TypeError("fetch failed")),
      });
    }
    const client = fakeClient(server.answers);
    server.clients.push(client);
    return client;
  },
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** The addresses the links of a page lead to. */
function links(markup: string): string[] {
  return [...markup.matchAll(/href="([^"]*)"/g)].map(
    (match) => match[1]?.replaceAll("&amp;", "&") ?? "",
  );
}

/** A page in English, as the shell hands it its texts. */
function inEnglish(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>
  );
}

/** The home in English, at an address whose query is given. */
async function home(search: Record<string, string> = {}): Promise<string> {
  const page = await HomePage({ searchParams: Promise.resolve(search) });
  return renderToStaticMarkup(inEnglish(page));
}

/** What the home asked of the list of projects. */
function listQuery(): Record<string, string> {
  const call = server.clients
    .flatMap((client) => client.calls)
    .find((each) => each.route === "GET /projects");
  return Object.fromEntries(call?.query ?? []);
}

beforeEach(() => {
  server.clients = [];
  server.unreachable = false;
  server.answers = {
    "GET /session": "session",
    "GET /projects": "projects",
    "GET /reference/readiness": "reference_readiness",
  };
});

describe("the home, the list of projects", () => {
  it("lists the projects in the order of the server, each a link to its page, with its code and its state", async () => {
    const html = await home();
    expect(html.startsWith(`<main class="${SCREEN.dense}">`)).toBe(true);
    expect(html).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Projects<\/h1>/);
    expect(html).toMatch(/<table[^>]*aria-label="List of projects">/);
    expect(links(html)).toContain(`/projects/${PROJECT}`);
    expect(text(html)).toContain(
      "Project Code State Modernisation du poste de commande PRJ-001 In progress Extension de la ligne d&#x27;essais PRJ-002 Pricing 2 projects",
    );
  });

  it("is filtered on the projects the user contributes to, by the filter of the contract, shown with the link that lifts it", async () => {
    const html = await home();
    expect(listQuery()).toEqual({ is_contributor: "true" });
    expect(html).toMatch(/<section aria-label="Filter of the list"/);
    expect(text(html)).toContain("Projects you contribute to Show all projects");
    expect(links(html)[0]).toBe("/?is_contributor=false");
  });

  it("lists every project the user may read once the filter is lifted, and offers it again: a filter, never a restriction of reading", async () => {
    const html = await home({ is_contributor: "false" });
    expect(listQuery()).toEqual({});
    expect(text(html)).toContain("Show only my projects");
    expect(text(html)).not.toContain("Projects you contribute to");
    expect(links(html)[0]).toBe("/");
    expect(links(html)).toContain(`/projects/${PROJECT}`);
  });

  it("asks the page its address holds, and offers none before the first nor after the last", async () => {
    await home({ offset: "50" });
    expect(listQuery()).toEqual({ is_contributor: "true", offset: "50" });
    server.clients = [];
    await home({ offset: "-3" });
    expect(listQuery()).toEqual({ is_contributor: "true" });
    // The two projects of the example are the whole list: no way through pages.
    const html = await home();
    expect(html).not.toContain('aria-label="Pages of the list"');
  });

  it("titles the tab with the list of projects", async () => {
    expect((await generateMetadata()).title).toBe("Projects — Waterfall");
  });
});

describe("the empty states of the home", () => {
  it("lifts the contributor filter when it is what empties the list", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await home();
    expect(text(html)).toBe(
      "Projects Projects you contribute to Show all projects You contribute to no project. Show all projects",
    );
    expect(links(html)).toEqual(["/?is_contributor=false", "/?is_contributor=false"]);
    expect(html).not.toContain("<table");
  });

  it("says there is no project when the list is empty unfiltered", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await home({ is_contributor: "false" });
    expect(text(html)).toBe("Projects Show only my projects No project.");
  });

  it("names each prerequisite an incomplete reference lacks, and leads to where it is provided", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await home();
    expect(text(html)).toMatch(
      /^Projects Projects you contribute to Show all projects Incomplete reference data No project can be created until the common reference data has: a default calendar with working hours an active cost category Project/,
    );
    expect(links(html).slice(1, 3)).toEqual(["/reference/resources", "/reference/costs"]);
  });

  it("names the prerequisites without a link to a function the session may not read", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": UNAUTHORIZED,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await home();
    expect(text(html)).toContain("a default calendar with working hours an active cost category");
    expect(links(html)).not.toContain("/reference/costs");
  });

  it("says nothing of a complete reference", async () => {
    expect(text(await home())).not.toContain("reference data");
  });

  it("guides a new installation to its reference before saying there is no project, under the one title of the screen", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects": "projects_empty",
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await home({ is_contributor: "false" });
    // The heading of the screen first, then the notice of the reference under it.
    expect(html).toMatch(
      new RegExp(`^<main class="${SCREEN.dense}">.*?</h1>.*?<section aria-labelledby="[^"]+"`),
    );
    expect(html.match(/<h1/g)).toHaveLength(1);
    expect(text(html)).toBe(
      "Projects Show only my projects Incomplete reference data No project can be created until the common reference data has: " +
        "a default calendar with working hours an active cost category No project.",
    );
  });

  it("never says the list is empty when the API refuses it for want of a session: it leads to the sign-in page", async () => {
    server.answers = { ...server.answers, "GET /projects": UNAUTHORIZED };
    await expect(home()).rejects.toBeInstanceOf(SignedOut);
  });

  it("never says there is no project when the API cannot be reached: it is announced", async () => {
    server.unreachable = true;
    await expect(home()).rejects.toBeInstanceOf(Unreachable);
  });
});
