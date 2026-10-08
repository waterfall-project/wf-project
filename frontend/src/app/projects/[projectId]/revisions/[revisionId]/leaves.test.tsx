// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { leafOf } from "@/navigation/functions";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import EstimatePage from "./estimate/page";
import PlanningPage from "./planning/page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const PARAMS = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
const SEARCH = Promise.resolve({ subproject_id: SUBPROJECT });
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";

/** A page in English, as the shell hands it its texts. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>,
  );
}

/** The address each link of a page leads to, by the text of the link. */
function links(markup: string): Record<string, string> {
  return Object.fromEntries(
    [...markup.matchAll(/<a [^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/g)].map((match) => [
      (match[2] ?? "").replace(/<[^>]*>/g, "").trim(),
      (match[1] ?? "").replaceAll("&amp;", "&"),
    ]),
  );
}

/** The name of a leaf of the table, in English. */
function nameOf(code: string): string {
  const [, key = ""] = leafOf(code).label.split(".");
  return CATALOGUES.en.functions[key as keyof typeof CATALOGUES.en.functions];
}

/** The address of a leaf of a revision of the witness, the sub-project filtered carried on. */
function leafHref(segment: string): string {
  return `/projects/${PROJECT}/revisions/${REVISION}/${segment}?subproject_id=${SUBPROJECT}`;
}

beforeEach(() => {
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes",
    "GET /projects/{project_id}/estimate-indicators": "estimate_indicators",
    "GET /projects/{project_id}/estimate-indicators/missing-rates": "missing_rates_none",
    "GET /reference/cost-categories": "volume/cost_categories",
    "GET /reference/resource-roles": "resource_roles",
    "GET /projects/{project_id}/subprojects": "subprojects",
  };
});

describe("the leaves with a screen of their own", () => {
  it("are led to from the head of the planning, each by its name, in the same context: the timelines, the imports and exports, the task tree", async () => {
    server.answers = { ...server.answers, [NODES]: "nodes_planning" };
    const found = links(html(await PlanningPage({ params: PARAMS, searchParams: SEARCH })));
    expect([
      found[nameOf("FBS-4.3.1")],
      found[nameOf("FBS-4.3.4")],
      found[nameOf("FBS-4.3.5")],
    ]).toEqual([leafHref("timelines"), leafHref("exchanges"), leafHref("task-tree")]);
  });

  it("is led to from the head of the estimate, by its name, in the same context: the workload of the project", async () => {
    const found = links(html(await EstimatePage({ params: PARAMS, searchParams: SEARCH })));
    expect(found[nameOf("FBS-4.4.4")]).toBe(leafHref("workload"));
  });
});
