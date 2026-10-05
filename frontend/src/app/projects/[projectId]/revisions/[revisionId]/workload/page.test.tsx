// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UnexpectedAnswer } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import WorkloadPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

// One client for the whole of a page, made at its first call.
vi.mock("@/api/server", () => ({
  serverClient: () => {
    const made = server.clients.at(-1);
    if (made !== undefined) {
      return made;
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
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const MARKED = "01926f3a-7c00-7000-8000-000000000101";
const ORG_NODE = "01926f3a-7c00-7000-8000-000000000471";
const WORKLOAD_ROUTE = "GET /projects/{project_id}/workload";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render in English, as the shell hands its texts to a screen. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {page}
    </NextIntlClientProvider>,
  );
}

/** What Next hands the screen of the workload, at the query given. */
function at(search: Record<string, string> = {}) {
  return {
    params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    searchParams: Promise.resolve(search),
  };
}

/** The query of the call of a route, as the client serialized it. */
function queryOf(route: string): Record<string, string> | undefined {
  const call = server.clients.flatMap((client) => client.calls).find((c) => c.route === route);
  return call === undefined ? undefined : Object.fromEntries(call.query);
}

/** The options of a list of the page, by the name of its parameter. */
function options(page: string, name: string): (string | undefined)[] {
  const select = new RegExp(`<select[^>]*name="${name}"[^>]*>(.*?)</select>`).exec(page);
  return [...(select?.[1] ?? "").matchAll(/<option[^>]*>(.*?)<\/option>/g)].map((m) => m[1]);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    [WORKLOAD_ROUTE]: "workload",
    "GET /reference/org-nodes": "org_nodes",
    "GET /projects/{project_id}/revisions": "revisions_marked",
  };
});

describe("the screen of the workload of a project", () => {
  it("names its function in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toMatch(/^Workload/);
  });

  it("shows its reading context above the workload, asked on the remaining of the revision under way unless the address names another basis [WF-DEV-0070-A]", async () => {
    const page = text(html(await WorkloadPage(at())));
    expect(queryOf(WORKLOAD_ROUTE)).toEqual({ basis: "current_remaining" });
    expect(page).toMatch(/Modernisation du poste de commande.*Workload/);
    expect(page).toContain(
      "Basis: Remaining of the current revision — revision “Current revision”",
    );
    // Its chart under its caption, with the command of its export and its date of calculation.
    expect(page).toContain("Load by role and by month Export as PNG Computed on");
  });

  it("asks the workload on the marked revision and the node of organisation chosen, the server filtering, and names the revision the API read [WF-DEV-0070-A]", async () => {
    server.answers = { ...server.answers, [WORKLOAD_ROUTE]: "workload_marked_remaining" };
    const page = text(
      html(
        await WorkloadPage(
          at({ basis: "marked_remaining", workload_revision: MARKED, org_node_id: ORG_NODE }),
        ),
      ),
    );
    expect(queryOf(WORKLOAD_ROUTE)).toEqual({
      basis: "marked_remaining",
      revision_id: MARKED,
      org_node_id: ORG_NODE,
    });
    expect(queryOf("GET /projects/{project_id}/revisions")).toEqual({ status: "marked" });
    // The revision the API says it read, named from the marked revisions the screen read.
    expect(page).toContain("Basis: Remaining of a marked revision — revision “Référence”");
  });

  it("sends no marked revision with another basis, and offers the three bases, the marked revisions and the nodes, the choice keeping the other parameters [WF-DEV-0070-A]", async () => {
    server.answers = { ...server.answers, [WORKLOAD_ROUTE]: "workload_reference_budget" };
    const page = html(
      await WorkloadPage(
        at({ basis: "reference_budget", workload_revision: MARKED, as_of: "2026-03-16" }),
      ),
    );
    expect(queryOf(WORKLOAD_ROUTE)).toEqual({ basis: "reference_budget" });
    expect(options(page, "basis")).toEqual([
      "Budget of the reference revision",
      "Remaining of a marked revision",
      "Remaining of the current revision",
    ]);
    expect(options(page, "workload_revision")).toEqual(["Référence", "Offre v1.0"]);
    expect(options(page, "org_node_id")).toEqual([
      "All nodes",
      "Direction technique",
      "Bureau d&#x27;études électricité (Direction technique)",
      "Atelier de câblage (Bureau d&#x27;études électricité)",
      "Service des achats (Direction technique)",
    ]);
    expect(page).toContain('type="hidden" name="as_of" value="2026-03-16"');
    expect(page).not.toContain('type="hidden" name="basis"');
    // Each field named by its label.
    expect(page).toContain('<label data-slot="label" class');
    expect(page).toMatch(/for="workload-basis"[^>]*>Basis<\/label>/);
    expect(page).toMatch(/<select[^>]*id="workload-basis"/);
  });

  it("offers only the revision under way on a project without a reference revision [WF-DEV-0070-A]", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_pricing" };
    const page = html(await WorkloadPage(at()));
    expect(options(page, "basis")).toEqual(["Remaining of the current revision"]);
    expect(page).not.toContain('name="workload_revision"');
  });

  it("does not offer the marked revisions as a basis when the project has none", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = html(await WorkloadPage(at()));
    expect(options(page, "basis")).toEqual([
      "Budget of the reference revision",
      "Remaining of the current revision",
    ]);
  });

  it("says the workload unavailable on a project without a reference revision, and why, the choice left [WF-DEV-0070-A]", async () => {
    server.answers = {
      ...server.answers,
      [WORKLOAD_ROUTE]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } },
    };
    const page = text(html(await WorkloadPage(at({ basis: "reference_budget" }))));
    expect(page).toContain(
      "The workload is not available on this basis: the project has no reference revision, and only the current revision is one.",
    );
    // The banner and the choice stay, the chart is gone.
    expect(page).toContain("Modernisation du poste de commande");
    expect(page).toContain("Organisation node All nodes");
    expect(page).not.toContain("Load by role and by month");
  });

  it.each([
    [
      [{ pointer: "/query/revision_id", code: "VALIDATION_FAILED" }],
      "The workload is not available on this basis: the marked revision asked for is missing, or is not marked.",
    ],
    [
      [{ pointer: "/query/org_node_id", code: "VALIDATION_FAILED" }],
      "The workload is not available: the organisation node asked for does not exist.",
    ],
    [[], "The workload is not available: the API refuses what is asked."],
    [
      [{ pointer: "/constructor", code: "VALIDATION_FAILED" }],
      "The workload is not available: the API refuses what is asked.",
    ],
    [
      // A field of a body, not the parameter of the query.
      [{ pointer: "/revision_id", code: "VALIDATION_FAILED" }],
      "The workload is not available: the API refuses what is asked.",
    ],
    [
      [
        { pointer: "/query/revision_id", code: "VALIDATION_FAILED" },
        { pointer: "/query/org_node_id", code: "VALIDATION_FAILED" },
      ],
      "The workload is not available: the API refuses what is asked.",
    ],
  ] as const)(
    "says the workload unavailable on a parameter the API refuses, by what its envelope points at: %j",
    async (fields, sentence) => {
      server.answers = {
        ...server.answers,
        [WORKLOAD_ROUTE]: {
          problem: { code: "VALIDATION_FAILED", status: 422, fields: [...fields] },
        },
      };
      const page = text(
        html(
          await WorkloadPage(
            at({ basis: "marked_remaining", workload_revision: REVISION, org_node_id: "x" }),
          ),
        ),
      );
      expect(queryOf(WORKLOAD_ROUTE)).toEqual({
        basis: "marked_remaining",
        revision_id: REVISION,
        org_node_id: "x",
      });
      expect(page).toContain(sentence);
    },
  );

  it("does not take a refusal of the same status for another reason as one of the basis", async () => {
    server.answers = {
      ...server.answers,
      [WORKLOAD_ROUTE]: { problem: { code: "ALREADY_EXISTS", status: 409 } },
    };
    await expect(WorkloadPage(at())).rejects.toBeInstanceOf(UnexpectedAnswer);
  });

  it("is not found when the API does not find the project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(WorkloadPage(at())).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });
});
