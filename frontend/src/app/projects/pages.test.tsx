// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type FakeAnswers, fakeClient, type Problem } from "@/test/fixtures";

import ProjectPage from "./[projectId]/page";
import RevisionPage from "./[projectId]/revisions/[revisionId]/page";
import ProjectsPage from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NOT_FOUND: { readonly problem: Problem } = { problem: { code: "NOT_FOUND", status: 404 } };

beforeEach(() => {
  server.answers = {
    "GET /projects": "projects",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
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
    const page = await ProjectPage({ params: Promise.resolve({ projectId: PROJECT }) });
    const html = renderToStaticMarkup(page);
    expect(html).toContain("<h1>Modernisation du poste de commande</h1>");
    expect(html).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}"`);
    expect(html).toContain(">Référence</a>");
  });

  it("shows the nodes of the main structure, one row each", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(await RevisionPage({ params }));
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
    const html = renderToStaticMarkup(await RevisionPage({ params }));
    expect(html).toContain("<tbody></tbody>");
  });

  it("renders nothing when the API refuses", async () => {
    server.answers = {
      "GET /projects": NOT_FOUND,
      "GET /projects/{project_id}": NOT_FOUND,
      "GET /projects/{project_id}/revisions": NOT_FOUND,
    };
    expect(renderToStaticMarkup(await ProjectsPage())).toBe("<main><ul></ul></main>");
    const page = await ProjectPage({ params: Promise.resolve({ projectId: PROJECT }) });
    expect(renderToStaticMarkup(page)).toBe("<main><h1></h1><ul></ul></main>");
  });
});
