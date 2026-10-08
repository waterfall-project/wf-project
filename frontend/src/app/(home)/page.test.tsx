// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient, Unreachable } from "@/api/client";
import { SignedOut } from "@/api/problem";
import type { ProjectListGridProps } from "@/components/projects/project-list-view";
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
// The grid renders as it would, and keeps what its page handed it.
const grids = vi.hoisted((): { props: ProjectListGridProps[] } => ({ props: [] }));
vi.mock("@/components/projects/project-list-view", async (original) => {
  const actual = await original<typeof import("@/components/projects/project-list-view")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    ProjectListGrid: (props: ProjectListGridProps) => {
      grids.props.push(props);
      return createElement(actual.ProjectListGrid, props);
    },
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
/** Every state of the contract, as the home asks them when its address names none. */
const EVERY_STATE = "created,pricing,in_progress,completed,lost,abandoned";
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
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
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
  grids.props = [];
  server.clients = [];
  server.unreachable = false;
  server.answers = {
    "GET /session": "session",
    "GET /projects": "projects",
    "GET /reference/readiness": "reference_readiness",
  };
});

describe("the home, the list of projects", () => {
  it("hands the grid the projects in the order of the server, each with its code, its state and when it was modified", async () => {
    const html = await home();
    expect(html.startsWith(`<main data-fill="" class="${SCREEN.dense} min-h-0">`)).toBe(true);
    expect(html).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Projects<\/h1>/);
    expect(html).toMatch(/role="grid"[^>]*aria-label="List of projects"/);
    const [grid] = grids.props;
    expect(grid?.projects).toEqual([
      {
        project_id: PROJECT,
        label: "Modernisation du poste de commande",
        code: "PRJ-001",
        state: "in_progress",
        updated_at: "2026-02-02T09:00:00Z",
      },
      expect.objectContaining({ code: "PRJ-002", state: "pricing" }),
    ]);
    expect(grid?.page).toEqual({ limit: 50, offset: 0, total: 2 });
    expect(text(html)).toContain("2 projects");
  });

  it("asks every state when the address names none, and the states, the sort, the search and the page it holds", async () => {
    await home();
    expect(listQuery()).toEqual({ is_contributor: "true", states: EVERY_STATE });
    server.clients = [];
    await home({
      states: "lost,pricing,unknown",
      sort_by: "updated_at",
      sort_order: "desc",
      search: "poste",
      offset: "50",
    });
    expect(listQuery()).toEqual({
      is_contributor: "true",
      states: "pricing,lost",
      sort_by: "updated_at",
      sort_order: "desc",
      search: "poste",
      offset: "50",
    });
    expect(grids.props.at(-1)?.query).toEqual({
      sort: { column: "updated_at", order: "desc" },
      search: "poste",
    });
  });

  it("offers the filter by state, every state pressed when the address names none", async () => {
    const html = await home();
    expect(html).toMatch(/role="group" aria-label="Filter by state"/);
    expect(html).toMatch(/aria-pressed="true"[^>]*>.*?Every state/);
    const pressed = await home({ states: "pricing" });
    expect(pressed).toMatch(/aria-pressed="false"[^>]*>.*?Every state/);
  });

  it("is filtered on the projects the user contributes to, by the filter of the contract, shown with the link that lifts it", async () => {
    const html = await home();
    expect(html).toMatch(/<section aria-label="Filter of the list"/);
    expect(text(html)).toContain("Projects you contribute to Show all projects");
    expect(links(html)[0]).toBe("/?is_contributor=false");
  });

  it("keeps the states, the sort and the search when the filter is lifted, back to the first page", async () => {
    const html = await home({ states: "pricing", sort_by: "code", offset: "50" });
    expect(links(html)[0]).toBe("/?states=pricing&sort_by=code&is_contributor=false");
  });

  it("shows the filter without the link that lifts it to a session that may not read every project (#522)", async () => {
    // A contributor without « consulter tous les projets » would see the same list lifted: the
    // link would promise what it does not do (WF-ADM-0110).
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
    const html = await home();
    expect(text(html)).toContain("Projects you contribute to");
    expect(text(html)).not.toContain("Show all projects");
    expect(links(html)).not.toContain("/?is_contributor=false");
  });

  it("stays filtered, without either link, for a session that may not read every project, whatever the address says (#522)", async () => {
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
    const html = await home({ is_contributor: "false" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: EVERY_STATE });
    expect(text(html)).toContain("Projects you contribute to");
    expect(text(html)).not.toContain("Show all projects");
    expect(text(html)).not.toContain("Show only my projects");
    const filter = html.slice(html.indexOf('aria-label="Filter of the list"'));
    expect(filter.slice(0, filter.indexOf("</section>"))).not.toContain("<a ");
  });

  it("lists every project the user may read once the filter is lifted, and offers it again: a filter, never a restriction of reading", async () => {
    const html = await home({ is_contributor: "false" });
    expect(listQuery()).toEqual({ states: EVERY_STATE });
    expect(text(html)).toContain("Show only my projects");
    expect(text(html)).not.toContain("Projects you contribute to");
    expect(links(html)[0]).toBe("/");
    expect(grids.props[0]?.projects.map((project) => project.project_id)).toContain(PROJECT);
  });

  it("asks the page its address holds, and offers none before the first nor after the last", async () => {
    await home({ offset: "50" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: EVERY_STATE, offset: "50" });
    server.clients = [];
    await home({ offset: "-3" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: EVERY_STATE });
    // The two projects of the example are the whole list: no way through pages.
    const html = await home();
    expect(html).not.toContain('aria-label="Pages of the projects"');
  });

  it("titles the tab with the list of projects", async () => {
    expect((await generateMetadata()).title).toBe("Projects — Waterfall");
  });
});

describe("the empty states of the home", () => {
  it("says the user contributes to no project when the filter empties the list, which the filter shown lifts, once", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await home();
    expect(text(html)).toMatch(
      /^Projects Projects you contribute to Show all projects Every state .* You contribute to no project\.$/,
    );
    expect(links(html)).toEqual(["/?is_contributor=false"]);
    expect(html).not.toContain('role="grid"');
  });

  it.each([
    [{ states: "lost" }, { states: "lost" }],
    [{ search: "x" }, { search: "x" }],
  ])(
    "keeps the grid of a list its states or its search empty, to change them, and never says the user contributes to no project (%o)",
    async (address, asked) => {
      server.answers = { ...server.answers, "GET /projects": "projects_empty" };
      const html = await home(address);
      expect(listQuery()).toMatchObject(asked);
      expect(html).toMatch(/role="grid"[^>]*aria-label="List of projects"/);
      expect(text(html)).not.toContain("You contribute to no project");
      expect(grids.props[0]?.projects).toEqual([]);
    },
  );

  it("says there is no project when the list is empty unfiltered", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await home({ is_contributor: "false" });
    expect(text(html)).toMatch(/^Projects Show only my projects Every state .* No project\.$/);
  });

  it("names each prerequisite an incomplete reference lacks, and leads to where it is provided", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await home();
    expect(text(html)).toMatch(
      /^Projects Projects you contribute to Show all projects Incomplete reference data No project can be created until the common reference data has: a default calendar with working hours an active cost category Every state/,
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
      new RegExp(
        `^<main data-fill="" class="${SCREEN.dense} min-h-0">.*?</h1>.*?<section aria-label="[^"]+"`,
      ),
    );
    expect(html.match(/<h1/g)).toHaveLength(1);
    expect(text(html)).toBe(
      "Projects Show only my projects Incomplete reference data No project can be created until the common reference data has: " +
        "a default calendar with working hours an active cost category " +
        "Every state Created Pricing In progress Completed Lost Abandoned No project.",
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
