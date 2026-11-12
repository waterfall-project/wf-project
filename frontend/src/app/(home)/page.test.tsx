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
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";
import { queryOfCall } from "@/test/queries";

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
// The session of the contract, the sizes of pages its account keeps set for a test.
const kept = vi.hoisted(
  (): {
    grids: Record<string, { page_size?: number; filters?: Record<string, string> }>;
    permissions: string[] | undefined;
    roles: string[] | undefined;
  } => ({
    grids: {},
    permissions: undefined,
    roles: undefined,
  }),
);
vi.mock("@/session/request", async (original) => {
  const actual = await original<typeof import("@/session/request")>();
  return {
    ...actual,
    requestSession: async () => {
      const session = await actual.requestSession();
      return session === undefined
        ? undefined
        : {
            ...session,
            ...(kept.permissions === undefined
              ? {}
              : { permissions: kept.permissions as typeof session.permissions }),
            ...(kept.roles === undefined ? {} : { access_role_ids: kept.roles }),
            display_preferences: {
              ...session.display_preferences,
              grids: { ...session.display_preferences?.grids, ...kept.grids },
            },
          };
    },
  };
});
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
/** Every state of the contract, as the home asks them for `states=all`. */
const EVERY_STATE = "created,pricing,in_progress,completed,lost,abandoned";
/** The states the home asks when its address names none and the account kept none. */
const DEFAULT_STATES = "created,pricing,in_progress";
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
  return queryOfCall(call?.query ?? []);
}

beforeEach(() => {
  kept.grids = {};
  kept.permissions = undefined;
  kept.roles = undefined;
  grids.props = [];
  server.clients = [];
  server.unreachable = false;
  server.answers = {
    "GET /me": "me",
    "GET /projects": "projects",
    "GET /reference/readiness": "reference_readiness",
  };
});

describe("the home of an account that cannot read any project [WF-IHM-0120] #2915", () => {
  /** Whether the home asked the API for the list of projects. */
  function askedList(): boolean {
    return server.clients.some((client) =>
      client.calls.some((call) => call.route === "GET /projects"),
    );
  }

  it("lists the projects for an account that holds project_settings.read [WF-IHM-0120-A]", async () => {
    const html = await home();
    expect(askedList()).toBe(true);
    expect(text(html)).not.toContain("No project to open");
  });

  it("says that the account opens no project and leads to the functions it holds, without reading the list [WF-IHM-0120-A]", async () => {
    server.answers = { ...server.answers, "GET /me": "me_auditor" };
    const html = await home();
    expect(askedList()).toBe(false);
    expect(html).toMatch(/<h1[^>]*>.*No project to open<\/h1>/);
    expect(text(html)).toContain("Your account cannot open any project");
    expect(links(html)).toContain("/admin/audit-log");
    expect(links(html)).not.toContain("/admin/users");
    expect(text(html)).not.toContain("no role yet");
  });

  it("keeps stating the prerequisites the reference data lacks, linked when the account may read them, without reading the list [WF-IHM-0120-A]", async () => {
    kept.permissions = ["cost_settings.read"];
    server.answers = {
      ...server.answers,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await home();
    expect(askedList()).toBe(false);
    expect(text(html)).toContain("Incomplete reference data");
    expect(links(html)).toContain("/reference/costs");
  });

  it("does not say a role is missing to an account that holds functions of a project only, nor one that holds a command [WF-IHM-0120-A]", async () => {
    for (const permissions of [["planning.read"], ["all_projects_read"]]) {
      kept.permissions = permissions;
      const html = await home();
      expect(askedList()).toBe(false);
      expect(text(html)).toContain("exercised in a project, but it cannot open any project");
      expect(text(html)).not.toContain("no role yet");
      expect(links(html)).toEqual([]);
    }
  });

  it("says that the account has no role yet when it carries no access role [WF-IHM-0120-A]", async () => {
    kept.roles = [];
    kept.permissions = [];
    const html = await home();
    expect(text(html)).toContain("no role yet");
  });

  it("leads to the portfolio and the reference data an account holds [WF-IHM-0120-A]", async () => {
    kept.permissions = ["portfolio_projects.read", "cost_settings.read"];
    const html = await home();
    expect(links(html)).toEqual(
      expect.arrayContaining(["/portfolio/projects", "/reference/costs"]),
    );
  });

  it("says that the account has no role yet when it holds no function at all [WF-IHM-0120-A]", async () => {
    server.answers = { ...server.answers, "GET /me": "me_without_roles" };
    const html = await home();
    expect(askedList()).toBe(false);
    expect(text(html)).toContain(
      "Your account has no role yet. An administrator must give you one",
    );
    expect(links(html)).toEqual([]);
  });
});

describe("the home, the list of projects", () => {
  it("hands the grid the projects in the order of the server, each with its code, its state and when it was modified", async () => {
    const html = await home();
    expect(html.startsWith(`<main data-fill="" class="${SCREEN.dense} min-h-0">`)).toBe(true);
    expect(html).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Projects<\/h1>/);
    expect(html).toMatch(/role="grid"[^>]*aria-label="List of projects"/);
    const [grid] = grids.props;
    // The order of the server, unsorted: the projects modified most recently first.
    expect(grid?.projects).toEqual([
      expect.objectContaining({ code: "PRJ-002", state: "pricing" }),
      {
        project_id: PROJECT,
        label: "Modernisation du poste de commande",
        code: "PRJ-001",
        state: "in_progress",
        updated_at: "2026-02-02T09:00:00Z",
      },
    ]);
    expect(grid?.page).toMatchObject({ limit: 50, offset: 0, total: 2 });
    expect(text(html)).toContain("2 projects");
  });

  it("asks Created, Pricing and In progress when the address names no state, every state for `states=all`, and the states, the sort, the search and the page it holds [WF-IHM-0130]", async () => {
    await home();
    expect(listQuery()).toEqual({ is_contributor: "true", states: DEFAULT_STATES });
    server.clients = [];
    await home({ states: "all" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: EVERY_STATE });
    server.clients = [];
    await home({
      states: "lost,pricing,unknown",
      sort_by: "updated_at",
      sort_order: "desc",
      search: "poste",
      offset: "50",
      limit: "25",
    });
    expect(listQuery()).toEqual({
      is_contributor: "true",
      states: "pricing,lost",
      sort_by: "updated_at",
      sort_order: "desc",
      search: "poste",
      offset: "50",
      limit: "25",
    });
    expect(grids.props.at(-1)?.query).toEqual({
      sort: { column: "updated_at", order: "desc" },
      search: "poste",
      size: 25,
    });
  });

  it("says the filter by default while it applies, with Created, Pricing and In progress pressed, and lifts it by « Every state » [WF-IHM-0130]", async () => {
    const html = await home();
    // The menu of the states, closed, says how many it retains (`CheckMenu`, #2916); the chip of the
    // filter by default says which, and that they are the default.
    expect(text(html)).toContain("Filter by state 3 selected");
    expect(text(html)).toContain("State: Created, Pricing, In progress (by default)");
  });

  it("reads the project created today on the home by default, the example of the contract the fake back serves [WF-IHM-0130]", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_with_created" };
    const html = await home();
    expect(listQuery()).toEqual({ is_contributor: "true", states: DEFAULT_STATES });
    const [grid] = grids.props;
    expect(grid?.projects.map((each) => [each.code, each.state])).toEqual([
      [null, "created"],
      ["PRJ-002", "pricing"],
      ["PRJ-001", "in_progress"],
    ]);
    expect(text(html)).toContain("3 projects");
  });

  it("keeps the states the account kept over the states by default, whatever they are [WF-IHM-0060-A]", async () => {
    kept.grids = { projects: { filters: { states: "pricing" } } };
    const html = await home();
    expect(listQuery()).toEqual({ is_contributor: "true", states: "pricing" });
    expect(text(html)).not.toContain("(by default)");
  });

  it("presses every state, and says no default, for `states=all` [WF-IHM-0130]", async () => {
    const html = await home({ states: "all" });
    expect(text(html)).not.toContain("(by default)");
    expect(text(html)).toContain("Filter by state Every state");
  });

  it("takes the states the account kept when the address names none, and the address over them [WF-IHM-0060-A]", async () => {
    kept.grids = { projects: { filters: { states: "pricing,in_progress,completed" } } };
    const html = await home();
    expect(listQuery()).toEqual({
      is_contributor: "true",
      states: "pricing,in_progress,completed",
    });
    expect(text(html)).not.toContain("(by default)");
    server.clients = [];
    kept.grids = { projects: { filters: { states: "all" } } };
    await home();
    expect(listQuery()).toEqual({ is_contributor: "true", states: EVERY_STATE });
    server.clients = [];
    await home({ states: "lost" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: "lost" });
  });

  it("presses in the filter by state the states the address names: the address is the truth of the filter", async () => {
    const html = await home({ states: "pricing" });
    expect(text(html)).toContain("Filter by state Pricing");
  });

  it("asks the period of the last modification the address holds, two instants as it names them, back to the first page", async () => {
    // March in Paris: from the start of 1 March, included, to the start of 1 April, excluded.
    const from = "2026-02-28T23:00:00.000Z";
    const to = "2026-03-31T22:00:00.000Z";
    server.answers = { ...server.answers, "GET /projects": "projects_period" };
    const html = await home({ from, to, offset: "50" });
    expect(listQuery()).toEqual({
      is_contributor: "true",
      states: DEFAULT_STATES,
      from,
      to,
      offset: "50",
    });
    expect(html).toMatch(/<form aria-label="Modification period"/);
    // Only the browser knows its time zone: the days show, and the period is sent, once hydrated.
    expect(html.match(/<input[^>]*type="date"[^>]*value=""/g)).toHaveLength(2);
    const period = html.slice(html.indexOf('<form aria-label="Modification period"'));
    // No button to press: the period is sent on Enter and on leaving it (#2916).
    expect(period.slice(0, period.indexOf("</form>"))).not.toContain("<button");
    expect(grids.props[0]?.projects.map((project) => project.code)).toEqual(["PRJ-002"]);
    // A bound that is no instant — a day alone, a 30 February — is not asked: the API would
    // refuse it.
    server.clients = [];
    await home({ from: "2026-03-01", to: "2026-02-30T00:00:00Z" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: DEFAULT_STATES });
  });

  it("says at its field the end of a period the server refuses for preceding its start, the list unread and the filters kept", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects": {
        problem: example("projects_period_inverted") as Problem & { status: 422 },
      },
    };
    const from = "2026-03-31T22:00:00.000Z";
    const to = "2026-02-28T23:00:00.000Z";
    const html = await home({ from, to, states: "pricing" });
    expect(listQuery()).toMatchObject({ from, to });
    expect(html).not.toContain('role="grid"');
    expect(grids.props).toEqual([]);
    expect(text(html)).toContain("The list is not read: the server refuses the period asked.");
    // The end refused, said at its field; the start the server names is said by its local day
    // once hydrated (`period-filter.dom.test.tsx`), the start left as it is.
    const fields = html.match(/<input[^>]*type="date"[^>]*>/g) ?? [];
    expect(fields).toHaveLength(2);
    expect(fields[0]).not.toContain("aria-invalid");
    expect(fields[1]).toContain('aria-invalid="true"');
    const described = /aria-describedby="([^"]+)"/.exec(fields[1] ?? "")?.[1];
    expect(html).toContain(
      `<p id="${described ?? ""}" class="text-xs text-destructive">The end of the period may not precede its start.</p>`,
    );
    // The states of the address stay pressed, to be changed.
    expect(text(html)).toContain("Filter by state Pricing");
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
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const html = await home();
    expect(text(html)).toContain("Projects you contribute to");
    expect(text(html)).not.toContain("Show all projects");
    expect(links(html)).not.toContain("/?is_contributor=false");
  });

  it("stays filtered, without either link, for a session that may not read every project, whatever the address says (#522)", async () => {
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const html = await home({ is_contributor: "false" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: DEFAULT_STATES });
    expect(text(html)).toContain("Projects you contribute to");
    expect(text(html)).not.toContain("Show all projects");
    expect(text(html)).not.toContain("Show only my projects");
    const filter = html.slice(html.indexOf('aria-label="Filter of the list"'));
    expect(filter.slice(0, filter.indexOf("</section>"))).not.toContain("<a ");
  });

  it("lists every project the user may read once the filter is lifted, and offers it again: a filter, never a restriction of reading", async () => {
    const html = await home({ is_contributor: "false", states: "all" });
    expect(listQuery()).toEqual({ states: EVERY_STATE });
    expect(text(html)).toContain("Show only my projects");
    expect(text(html)).not.toContain("Projects you contribute to");
    expect(links(html)[0]).toBe("/?states=all");
    expect(grids.props[0]?.projects.map((project) => project.project_id)).toContain(PROJECT);
  });

  it("asks the page its address holds, and offers none before the first nor after the last", async () => {
    await home({ offset: "50" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: DEFAULT_STATES, offset: "50" });
    server.clients = [];
    await home({ offset: "-3" });
    expect(listQuery()).toEqual({ is_contributor: "true", states: DEFAULT_STATES });
    // The two projects of the example are the whole list: no way through pages.
    const html = await home();
    expect(html).not.toContain('aria-label="Pages of the projects"');
  });

  it("offers the creation of a project to a session that holds its permission [WF-ADM-0100-A]", async () => {
    const html = await home();
    expect(html).toMatch(/<button[^>]*>(?:(?!<\/button>).)*Create a project<\/button>/);
  });

  it("shows no note of the mock-up, whatever the session: the service filters, sorts and pages the list (US-0920, #1004)", async () => {
    expect(await home()).not.toMatch(/role="note"|Mock-up/);
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    expect(await home()).not.toMatch(/role="note"|Mock-up/);
  });

  it("shows every state when the address lifts the filter, the six states being offered by the menu itself [WF-CYC-0010-A]", async () => {
    // The six states, and no other, are listed by the menu once open (`project-list.dom.test.tsx`).
    const html = await home({ states: "all" });
    expect(text(html)).toContain("Filter by state Every state");
  });

  it("presents the creation of a project unavailable while the minimum reference data is incomplete, which the server would refuse", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await home();
    const create =
      /<button[^>]*aria-disabled="true"[^>]*aria-describedby="([^"]+)"[^>]*>(?:(?!<\/button>).)*Create a project<\/button>/.exec(
        html,
      );
    expect(create).not.toBeNull();
    expect(html).toContain(`id="${create?.[1] ?? ""}"`);
  });

  it("offers no creation of a project to a session without its permission [WF-ADM-0100-A]", async () => {
    // Un utilisateur sans la permission de créer un projet n'en crée pas.
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const html = await home();
    expect(text(html)).not.toContain("Create a project");
  });

  it("titles the tab with the list of projects", async () => {
    expect((await generateMetadata()).title).toBe("Projects — Waterfall");
  });
});

describe("the empty states of the home", () => {
  it("says the user contributes to no project when the filter empties the list, which the filter shown lifts, once", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await home({ states: "all" });
    expect(text(html)).toMatch(
      /^Projects Help Create a project Projects you contribute to Show all projects Filter by state Every state .* You contribute to no project\.$/,
    );
    expect(links(html)).toEqual(["/?states=all&is_contributor=false"]);
    expect(html).not.toContain('role="grid"');
  });

  it.each([
    [{ states: "lost" }, { states: "lost" }],
    [{}, { states: DEFAULT_STATES }],
    [{ search: "x" }, { search: "x" }],
    [{ to: "2025-01-31T23:00:00.000Z" }, { to: "2025-01-31T23:00:00.000Z" }],
  ])(
    "keeps the grid of a list its states, its period or its search empty, to change them, and never says the user contributes to no project (%o)",
    async (address, asked) => {
      server.answers = { ...server.answers, "GET /projects": "projects_empty" };
      const html = await home(address);
      expect(listQuery()).toMatchObject(asked);
      expect(html).toMatch(/role="grid"[^>]*aria-label="List of projects"/);
      expect(text(html)).not.toContain("You contribute to no project");
      expect(grids.props[0]?.projects).toEqual([]);
    },
  );

  it("keeps an empty grid, the badge of the states by default and the menu of the states, when the states by default retain no project and the address names none (WF-IHM-0130)", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await home({ is_contributor: "false" });
    expect(listQuery()).toEqual({ states: DEFAULT_STATES });
    expect(html).toMatch(/role="grid"[^>]*aria-label="List of projects"/);
    expect(text(html)).toContain("State: Created, Pricing, In progress (by default)");
    expect(text(html)).toContain("Filter by state 3 selected");
    expect(text(html)).not.toContain("No project.");
    expect(grids.props[0]?.projects).toEqual([]);
  });

  it("says there is no project when the list is empty unfiltered", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await home({ is_contributor: "false", states: "all" });
    expect(text(html)).toMatch(
      /^Projects Help Create a project Show only my projects Filter by state Every state .* No project\.$/,
    );
  });

  // A new installation, which lacks the labour category and the role alone, its calendar by default
  // bootstrapped (WF-EXP-0020, EP-14/L42s); then a reference whose one category of provision for
  // risks, PRV-001, was deactivated (EP-14/L42p).
  it.each([
    [
      "reference_readiness_incomplete",
      "an active labour category an active resource role",
      ["/reference/costs", "/reference/resources"],
    ],
    [
      "reference_readiness_without_provision",
      "an active category of provision for risks",
      ["/reference/costs"],
    ],
  ] as const)(
    "names each prerequisite an incomplete reference lacks, and leads to where it is provided (%s) [WF-IHM-0120-A] [WF-CYC-0120-A]",
    async (readiness, missing, provided) => {
      // Sur une installation au référentiel incomplet, l'accueil nomme les prérequis manquants et
      // mène au référentiel.
      server.answers = { ...server.answers, "GET /reference/readiness": readiness };
      const html = await home({ states: "all" });
      expect(text(html)).toMatch(
        new RegExp(
          `^Projects Help Create a project The minimum reference data is incomplete\\. Projects you contribute to Show all projects Incomplete reference data No project can be created until the common reference data has: ${missing} Filters Columns`,
        ),
      );
      expect(links(html).slice(1, 1 + provided.length)).toEqual(provided);
    },
  );

  it("names the prerequisites without a link to a function the session may not read", async () => {
    server.answers = {
      ...server.answers,
      "GET /me": UNAUTHORIZED,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await home();
    expect(text(html)).toContain("an active labour category an active resource role");
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
    const html = await home({ is_contributor: "false", states: "all" });
    // The heading of the screen first, then the notice of the reference under it.
    expect(html).toMatch(
      new RegExp(
        `^<main data-fill="" class="${SCREEN.dense} min-h-0">.*?</h1>.*?<section aria-label="[^"]+"`,
      ),
    );
    expect(html.match(/<h1/g)).toHaveLength(1);
    expect(text(html)).toBe(
      "Projects Help Create a project The minimum reference data is incomplete. Show only my projects " +
        `Incomplete reference data No project can be created until the common reference data has: ` +
        "an active labour category an active resource role " +
        "Filter by state Every state Modification period From To No project.",
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

describe("the home, the size of the pages of the list of projects", () => {
  it.each([
    ["no preference", {}, "50"],
    ["a page size of 25", { limit: "25" }, "25"],
  ])("sends %s as the limit of its reading [WF-IHM-0060-A]", async (_name, search, limit) => {
    await home(search);
    const call = server.clients
      .flatMap((client) => client.calls)
      .find((each) => each.route === "GET /projects");
    expect(Object.fromEntries(call?.query ?? []).limit).toBe(limit);
  });

  it("reads the page size kept by the account when the address asks none [WF-IHM-0060-A]", async () => {
    kept.grids = { projects: { page_size: 25 } };
    await home({});
    const call = server.clients
      .flatMap((client) => client.calls)
      .find((each) => each.route === "GET /projects");
    expect(Object.fromEntries(call?.query ?? []).limit).toBe("25");
  });
});
