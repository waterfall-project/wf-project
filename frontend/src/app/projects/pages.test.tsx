// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient, Unreachable } from "@/api/client";
import { SignedOut, UnexpectedAnswer } from "@/api/problem";
import { SESSION_REQUIRED_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import ProjectPage, { generateMetadata as projectMetadata } from "./[projectId]/page";
import RevisionPage from "./[projectId]/revisions/[revisionId]/page";
import ProjectsPage, { generateMetadata as projectsMetadata } from "./page";

const server = vi.hoisted(
  (): {
    answers: FakeAnswers;
    clients: FakeClient[];
    unreachable: boolean;
    structures: (() => Response) | undefined;
  } => ({
    answers: {},
    clients: [],
    unreachable: false,
    structures: undefined,
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
    const structures = server.structures;
    if (structures !== undefined) {
      // An answer the contract does not declare for the structures — a failure of the
      // service, a page of a gateway —; the project and the revision from their examples.
      return createApiClient({
        address: "http://api.invalid",
        fetch: (request) => {
          const path = new URL(request.url).pathname;
          if (path.endsWith("/structures")) {
            return Promise.resolve(structures());
          }
          const name = /\/revisions\/[^/]+$/.test(path) ? "revision" : "project";
          return Promise.resolve(Response.json(example(name)));
        },
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
// The project in pricing, without a revision (`project_pricing.json`).
const PRICING = "01926f3a-7c00-7000-8000-000000000002";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const NO_SEARCH = Promise.resolve({});
const BANNER = '<section aria-label="Reading context"';
const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** A page in English, as the shell hands it its texts. */
function inEnglish(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  server.clients = [];
  server.unreachable = false;
  server.structures = undefined;
  server.answers = {
    "GET /session": "session",
    "GET /projects": "projects",
    "GET /reference/readiness": "reference_readiness",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": "nodes",
  };
});

describe("the witness path", () => {
  it("lists the projects, each a link to its page", async () => {
    const html = renderToStaticMarkup(inEnglish(await ProjectsPage({ searchParams: NO_SEARCH })));
    expect(html).toContain(`<a href="/projects/${PROJECT}">Modernisation du poste de commande</a>`);
    expect(html).toContain("Extension de la ligne d&#x27;essais");
  });

  it("shows a project and links to its revisions", async () => {
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(html).toContain("<h1>Modernisation du poste de commande</h1>");
    expect(html).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}"`);
    expect(html).toContain(">Référence</a>");
  });

  it("shows the nodes of the main structure, one row each", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(
      inEnglish(await RevisionPage({ params, searchParams: NO_SEARCH })),
    );
    expect(html.match(/<tr /g)).toHaveLength(4);
    expect(html).toContain(
      '<tr data-kind="estimate_line"><td>3</td><td>Ingénierie de détail</td></tr>',
    );
  });

  it("is not found when the API does not find the structures of the revision", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/structures": NOT_FOUND,
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("never shows an empty grid on a failure of the service: the screen of failure names it by its correlation identifier", async () => {
    server.structures = () =>
      Response.json(
        { code: "INTERNAL_ERROR", status: 500, correlation_id: "req-7f3a" },
        { status: 500, headers: { "content-type": "application/problem+json" } },
      );
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const page = RevisionPage({ params, searchParams: NO_SEARCH });
    await expect(page).rejects.toBeInstanceOf(UnexpectedAnswer);
    await expect(page).rejects.toMatchObject({
      operation: "listCostStructures",
      digest: "WATERFALL_CORRELATION;req-7f3a",
    });
  });

  it("never shows an empty grid when a gateway says the service is down: the API is out of reach", async () => {
    server.structures = () => new Response("<html>Bad gateway</html>", { status: 502 });
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toBeInstanceOf(
      Unreachable,
    );
  });

  it("is not found at an address that names no revision, before the API is asked", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: "a.b" });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
    expect(server.clients.flatMap((client) => client.calls)).toEqual([]);
  });

  it("is not found for a project the API does not find, as the other screens of a project", async () => {
    server.answers = {
      "GET /session": "session",
      "GET /projects/{project_id}": NOT_FOUND,
      "GET /projects/{project_id}/revisions": NOT_FOUND,
    };
    const page = ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });

  it("titles the tab with the screen, and with the project read", async () => {
    expect((await projectsMetadata()).title).toBe("Projects — Waterfall");
    const params = Promise.resolve({ projectId: PROJECT });
    expect((await projectMetadata({ params })).title).toBe(
      "Projects · Modernisation du poste de commande — Waterfall",
    );
  });
});

describe("the banner of the reading context on the witness path", () => {
  it("names the project on the page of a project [WF-IHM-0020-A]", async () => {
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(html.startsWith(BANNER)).toBe(true);
    expect(text(html)).toMatch(
      /^Project Modernisation du poste de commande Modernisation du poste de commande Référence/,
    );
  });

  it("names the project and the revision on the grid of a revision [WF-IHM-0020-A]", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const search = Promise.resolve({ subproject_id: "unassigned" });
    const html = renderToStaticMarkup(
      inEnglish(await RevisionPage({ params, searchParams: search })),
    );
    expect(html.startsWith(BANNER)).toBe(true);
    expect(text(html)).toMatch(
      /^Project Modernisation du poste de commande Revision Current revision Draft Subproject: No subproject 1 Études/,
    );
    expect(html).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}"`);
  });

  it("is not found for a revision the API does not find, as the other screens of a project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("does not swallow an answer other than not found, and leaves it to the screen of failure", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": UNAUTHORIZED };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      operation: "getProject",
      digest: SESSION_REQUIRED_DIGEST,
    });
  });
});

/** The list of projects in English, at an address whose query is given. */
async function projectsPage(search: Record<string, string> = {}): Promise<string> {
  const page = await ProjectsPage({ searchParams: Promise.resolve(search) });
  return renderToStaticMarkup(inEnglish(page));
}

/** The addresses the links of a page lead to. */
function links(markup: string): string[] {
  return [...markup.matchAll(/href="([^"]*)"/g)].map((match) => match[1] ?? "");
}

describe("the empty states of the shell", () => {
  it("says there is no project, on the example of an empty list", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await projectsPage();
    expect(text(html)).toBe("No project.");
    expect(html).not.toContain("<ul");
  });

  it("lifts the contributor filter when it is what empties the list", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await projectsPage({ is_contributor: "true" });
    expect(text(html)).toBe("You contribute to no project. Show all projects");
    expect(links(html)).toEqual(["/projects"]);
    const list = server.clients
      .flatMap((client) => client.calls)
      .find((call) => call.route === "GET /projects");
    expect(list?.query.get("is_contributor")).toBe("true");
  });

  it("asks the whole list when the address holds no filter", async () => {
    await projectsPage();
    const list = server.clients
      .flatMap((client) => client.calls)
      .find((call) => call.route === "GET /projects");
    expect(list?.query.has("is_contributor")).toBe(false);
  });

  it("names each prerequisite an incomplete reference lacks, and leads to where it is provided", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await projectsPage();
    expect(text(html)).toMatch(
      /^Incomplete reference data No project can be created until the common reference data has: a default calendar with working hours an active cost category Modernisation/,
    );
    expect(links(html).slice(0, 2)).toEqual(["/reference/resources", "/reference/costs"]);
  });

  it("names the prerequisites without a link to a function the session may not read", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": UNAUTHORIZED,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await projectsPage();
    expect(text(html)).toContain("a default calendar with working hours an active cost category");
    expect(links(html)).not.toContain("/reference/costs");
  });

  it("says nothing of a complete reference", async () => {
    expect(text(await projectsPage())).not.toContain("reference data");
  });

  it("says a project has no revision yet, on the example of an empty history, and leads to its revisions", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PRICING }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(text(html)).toContain(
      "Extension de la ligne d&#x27;essais This project has no revision yet. Go to the revisions of the project",
    );
    expect(links(html)).toContain(`/projects/${PRICING}/revisions`);
    expect(html).not.toContain("<ul");
  });

  it("does not offer the way to the revisions to a session that may not read them", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": UNAUTHORIZED,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PRICING }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(text(html)).toContain("This project has no revision yet.");
    expect(text(html)).not.toContain("Go to the revisions of the project");
    expect(links(html)).not.toContain(`/projects/${PRICING}/revisions`);
  });

  it("guides a new installation to its reference before saying there is no project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects": "projects_empty",
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await projectsPage();
    expect(html).toMatch(/^<main><section aria-labelledby="[^"]+"/);
    expect(text(html)).toBe(
      "Incomplete reference data No project can be created until the common reference data has: " +
        "a default calendar with working hours an active cost category No project.",
    );
    expect(links(html)).toEqual(["/reference/resources", "/reference/costs"]);
  });

  it("is not found for a revision its address carries that the API does not find", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
    };
    const page = ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: Promise.resolve({ revision_id: REVISION }),
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });

  it("is not found at an address that names no project, before the API is asked", async () => {
    const page = ProjectPage({
      params: Promise.resolve({ projectId: "a.b" }),
      searchParams: NO_SEARCH,
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(server.clients.flatMap((client) => client.calls)).toEqual([]);
  });

  it("never says the list is empty when the API refuses it for want of a session: it leads to the sign-in page", async () => {
    server.answers = { ...server.answers, "GET /projects": UNAUTHORIZED };
    await expect(ProjectsPage({ searchParams: NO_SEARCH })).rejects.toBeInstanceOf(SignedOut);
  });

  it("never says there is no project or no revision when the API cannot be reached: it is announced", async () => {
    server.unreachable = true;
    await expect(ProjectsPage({ searchParams: NO_SEARCH })).rejects.toBeInstanceOf(Unreachable);
    const page = ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    await expect(page).rejects.toBeInstanceOf(Unreachable);
  });
});
