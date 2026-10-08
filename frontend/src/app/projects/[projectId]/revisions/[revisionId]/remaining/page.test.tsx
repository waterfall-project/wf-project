// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { nodeFieldNames } from "@/components/grid/nodes";
import { REMAINING_FIELDS } from "@/components/grid/remaining";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import RemainingPage, { generateMetadata } from "./page";

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
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => SCREEN,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const INDICATORS = "GET /projects/{project_id}/remaining-indicators";
const REVISION_READ = "GET /projects/{project_id}/revisions/{revision_id}";

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

/** The screen of the remaining to commit at the query given. */
async function remainingAt(search: Record<string, string> = {}) {
  return html(
    await RemainingPage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve(search),
    }),
  );
}

/** The query of the call of a route, as the client serialized it. */
function queryOf(route: string): Record<string, string> | undefined {
  const call = server.clients.flatMap((client) => client.calls).find((c) => c.route === route);
  return call === undefined ? undefined : Object.fromEntries(call.query);
}

/** The opening tag of the cell of a row, by its index among the rows, and of a column. */
function cellTag(page: string, row: number, column: string): string {
  const tags = page.match(/<td\b[^>]*>/g) ?? [];
  const found = tags.find(
    (tag) =>
      tag.includes(`data-row="${row.toString()}"`) && tag.includes(`data-column="${column}"`),
  );
  if (found === undefined) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The section a page names, from its opening tag to its end. */
function section(page: string, name: string): string {
  const start = page.indexOf(`<section aria-label="${name}"`);
  return start < 0 ? "" : page.slice(start, page.indexOf("</section>", start));
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    [REVISION_READ]: "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes_estimate",
    [INDICATORS]: "remaining_indicators",
  };
});

describe("the screen of the remaining to commit", () => {
  it("names its function in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toBe(
      "Estimate to complete · Modernisation du poste de commande — Waterfall",
    );
  });

  it("reads the lines of the tasks started alone, the fields its grid shows, for the sub-project its banner shows alone, said to restrict the grid alone [WF-IHM-0020-A]", async () => {
    // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres — the sub-project, by
    // which the nodes are read and not the indicators, the chip saying so (#459); the date, which
    // no read of the screen takes, is not shown (#302).
    const page = await remainingAt({ subproject_id: SUBPROJECT, as_of: "2026-05-31" });
    const { fields, ...query } = queryOf(NODES) ?? {};
    expect(query).toEqual({ progress: "started", subproject_id: SUBPROJECT });
    expect(fields?.split(",").sort()).toEqual(nodeFieldNames(REMAINING_FIELDS).sort());
    const banner = page.slice(0, page.indexOf("</section>"));
    expect(text(banner)).toContain("Subproject: SP-CMD — Poste de commande, on the grid only");
    expect(text(banner)).not.toContain("Calculation date");
    expect(queryOf(INDICATORS)).toEqual({ revision_id: REVISION });
  });

  it("asks the tasks not started too when the address asks them, their lines then entered, and offers to show the started alone again [WF-RAE-0040-A]", async () => {
    // Les tâches non démarrées n'apparaissent qu'à la demande, et sont alors modifiables : a link
    // of the head asks them, and the lines of the mounting on site, not started, take a
    // re-estimation of their figures.
    const page = await remainingAt({ subproject_id: SUBPROJECT });
    expect(page).toContain(
      `href="${SCREEN}?subproject_id=${SUBPROJECT}&amp;progress=not_started%2Cstarted"`,
    );
    expect(text(page)).toContain("Show the tasks not started too");

    server.clients = [];
    server.answers = { ...server.answers, [NODES]: "nodes_installation" };
    const shown = await remainingAt({ progress: "not_started,started", sort_by: "label" });
    expect(queryOf(NODES)?.progress).toBe("not_started,started");
    // The wiring on site, the first line of the mounting: its effort and its quantity entered.
    expect(cellTag(shown, 2, "hours")).not.toContain("aria-readonly");
    expect(cellTag(shown, 2, "quantity")).not.toContain("aria-readonly");
    expect(cellTag(shown, 2, "reestimated_amount")).toContain('aria-readonly="true"');
    expect(text(shown)).toContain("Show the started tasks only");
    expect(shown).toContain(`href="${SCREEN}?sort_by=label"`);

    // A state the contract does not know is not asked: the tasks started.
    server.clients = [];
    await remainingAt({ progress: "half_done" });
    expect(queryOf(NODES)?.progress).toBe("started");
  });

  it("shows the indicators of the remaining to commit as the server gives them, dated, its deviations signed [WF-RAE-0020-A]", async () => {
    // Les écarts sont présents et signés. La couverture des risques présente la réserve de
    // référence, les provisions restantes, le coût des risques survenus et l'écart de couverture.
    const summary = section(await remainingAt(), "Remaining to commit indicators");
    expect(summary).toMatch(/Computed on <time dateTime="2026-06-03T14:05:00Z"/);
    expect(text(summary)).toContain(
      "Remaining to commit 21,234.56 Margin on the reference budget -6,100.00 " +
        "Deviation from the previous review -100,210.00 By nature of cost",
    );
    // Each amount bears the one mark of a computed value.
    expect(summary.match(/aria-label="Computed"/g)).toHaveLength(7);
    expect(text(summary)).toContain("Débours: 1,434.56 (6.76%)");
    expect(text(summary)).toContain(
      "Risk reserve 910.00 Remaining provisions 500.00 Cost of the occurred risks 200.00 Coverage variance 210.00",
    );
  });

  it("signals the sub-project over its budget in the zone the server classes it in, the others not, the deviations signed [WF-RAE-0020-A]", async () => {
    // Les écarts sont présents et signés. Un sous-projet dont le coût réel augmenté du reste à
    // engager dépasse son budget est signalé par la couleur, les autres non.
    // The remaining to commit just after the re-estimate made today: the control station, its
    // invoice of 2,400 beyond the estimate of its lines, still over its budget.
    server.answers = { ...server.answers, [INDICATORS]: "remaining_indicators_over_budget" };
    const markup = section(await remainingAt(), "Remaining to commit indicators");
    const summary = text(markup);
    expect(summary).toContain("Poste de commande: 20,334.56, margin -2,200.00");
    expect(summary).toContain("No subproject: 700.00, margin -3,700.00");
    // Each by the zone the server gives it, named: the whole without sub-project is over its
    // budget too, the invoice of the studies and the purchases under unknown codes beyond it.
    expect(
      [...markup.matchAll(/role="img" aria-label="(Alert|Nominal|Watch)"/g)].map((m) => m[1]),
    ).toEqual(["Alert", "Nominal", "Alert"]);
    // The margin on the reference budget, in the sense of the balances: 200 more of it.
    expect(summary).toContain("Margin on the reference budget -5,900.00");
    expect(summary).toContain("Deviation from the previous review -100,410.00");
  });

  it("says the indicators unavailable when the API does not find them, the grid shown", async () => {
    server.answers = {
      ...server.answers,
      [INDICATORS]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const page = await remainingAt();
    expect(text(page)).toContain("The remaining to commit indicators are unavailable.");
    expect(page).toContain('aria-label="Remaining to commit grid"');
  });

  it("leads to the Kanban of the start of the tasks, in the same context", async () => {
    const page = await remainingAt({ subproject_id: SUBPROJECT });
    expect(page).toContain(
      `href="/projects/${PROJECT}/revisions/${REVISION}/kanban?subproject_id=${SUBPROJECT}"`,
    );
    expect(text(page)).toContain("Kanban — task start");
  });

  it("places undo and redo in the remaining to commit of a revision in progress, and none in that of a marked one, whose marking nothing undoes [WF-IHM-0110-A]", async () => {
    // Aucune commande n'annule un marquage : the grid of a marked revision enters nothing.
    const open = await remainingAt();
    expect(open).toContain('aria-label="Undo"');
    expect(open).toContain('aria-label="Redo"');

    server.clients = [];
    server.answers = { ...server.answers, [REVISION_READ]: "revision_marked" };
    const marked = await remainingAt();
    expect(marked).not.toContain('aria-label="Undo"');
    expect(marked).not.toMatch(/<td(?![^>]*aria-readonly)[^>]*data-column=/);
  });
});
