// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import ProjectPage, { generateMetadata as projectMetadata } from "./[projectId]/page";
import RevisionPage from "./[projectId]/revisions/[revisionId]/page";
import ProjectsPage, { generateMetadata as projectsMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const NO_SEARCH = Promise.resolve({});
const BANNER = '<section aria-label="Reading context"';

/** A page in English, as the shell hands it its texts. */
function inEnglish(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  server.answers = {
    "GET /session": "session",
    "GET /projects": "projects",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": "nodes",
  };
});

describe("the witness path", () => {
  it("lists the projects, each a link to its page", async () => {
    const html = renderToStaticMarkup(await ProjectsPage());
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

  it("shows an empty grid when the structures cannot be read", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/structures": NOT_FOUND,
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(
      inEnglish(await RevisionPage({ params, searchParams: NO_SEARCH })),
    );
    expect(html).toContain("<tbody></tbody>");
  });

  it("renders nothing when the API refuses", async () => {
    server.answers = {
      "GET /projects": NOT_FOUND,
      "GET /projects/{project_id}": NOT_FOUND,
      "GET /projects/{project_id}/revisions": NOT_FOUND,
    };
    expect(renderToStaticMarkup(await ProjectsPage())).toBe("<main><ul></ul></main>");
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    expect(renderToStaticMarkup(inEnglish(page))).toBe("<main><h1></h1><ul></ul></main>");
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
    expect(html).toContain('<dt class="text-muted-foreground">Project</dt>');
    expect(html).toContain('<dd class="font-medium">Modernisation du poste de commande</dd>');
  });

  it("names the project and the revision on the grid of a revision [WF-IHM-0020-A]", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const search = Promise.resolve({ subproject_id: "unassigned" });
    const html = renderToStaticMarkup(
      inEnglish(await RevisionPage({ params, searchParams: search })),
    );
    expect(html.startsWith(BANNER)).toBe(true);
    expect(html).toContain('<dd class="font-medium">Current revision</dd>');
    expect(html).toContain(">Subproject: No subproject<");
    expect(html).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}"`);
  });

  it("shows no banner on the grid of a revision the API does not find", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(
      inEnglish(await RevisionPage({ params, searchParams: NO_SEARCH })),
    );
    expect(html.startsWith("<main><table>")).toBe(true);
  });
});
