// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { estimateGrid } from "@/components/grid/estimate";
import type { EstimateGridProps } from "@/components/grid/estimate-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import { filtersOf, menuText } from "@/test/filter-menu";
import { type FakeAnswers, type FakeClient, fakeClient, held } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import EstimatePage from "./page";

const server = vi.hoisted(
  (): {
    answers: FakeAnswers;
    clients: FakeClient[];
    hold?: (route: string) => Promise<unknown> | undefined;
  } => ({ answers: {}, clients: [] }),
);

vi.mock("@/api/server", () => ({
  serverClient: () => {
    const client = fakeClient(server.answers, {
      hold: (route) => server.hold?.(route),
    });
    server.clients.push(client);
    return client;
  },
}));
// The grid is not rendered: the page is read for what it asks and what it hands its grid.
const grids = vi.hoisted((): { estimate: EstimateGridProps[] } => ({ estimate: [] }));
vi.mock("@/components/grid/estimate-grid", () => ({
  EstimateGrid: (props: EstimateGridProps) => {
    grids.estimate.push(props);
    return props.treeFilters;
  },
}));
// The session of the contract, some of its permissions withdrawn for a test.
const withdrawn = vi.hoisted(() => ({ permissions: [] as string[] }));
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
            permissions: session.permissions.filter(
              (permission) => !withdrawn.permissions.includes(permission),
            ),
          };
    },
  };
});
// The filter by a lot or a post reads the address the browser shows.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
// The lot of the witness and its post, as its work breakdown names them.
const LOT = "01926f3a-7c00-7000-8000-000000000711";
const ITEM = "01926f3a-7c00-7000-8000-000000000712";

/** The query the page asked a list of the reference with, by the end of its route. */
function queryOf(end: string): URLSearchParams | undefined {
  return server.clients.flatMap((client) => client.calls).find((call) => call.route.endsWith(end))
    ?.query;
}

/** The markup of the estimate of the witness revision for the session given. */
async function estimatePage(
  session: "me" | "me_estimator" | "me_manager",
  search: Record<string, string> = {},
): Promise<string> {
  server.answers = { ...server.answers, "GET /me": session };
  const page = await EstimatePage({
    params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    searchParams: Promise.resolve(search),
  });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>,
  );
}

/** Read the estimate of the witness revision for the session given; its grid as handed. */
async function estimateFor(session: "me" | "me_estimator") {
  await estimatePage(session);
  return grids.estimate.at(-1);
}

beforeEach(() => {
  withdrawn.permissions = [];
  grids.estimate = [];
  server.clients = [];
  delete server.hold;
  server.answers = {
    "GET /reference/settings": "reference_settings",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": "nodes",
    "GET /projects/{project_id}/estimate-indicators": "estimate_indicators",
    "GET /projects/{project_id}/estimate-indicators/missing-rates": "missing_rates_none",
    "GET /reference/cost-categories": "volume/cost_categories",
    "GET /reference/resource-roles": "resource_roles",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/work-breakdown": "work_breakdown",
    "GET /projects/{project_id}/risks": "risks",
  };
});

describe("the grid of the estimate, entered as the structure lists it", () => {
  const STRUCTURES = "GET /projects/{project_id}/revisions/{revision_id}/structures";

  it("hands the grid read only on the main structure of a project in progress, and entered on a project in pricing [WF-DEV-0050-A]", async () => {
    // Sur un projet En cours, la grille de devis de la structure principale ne propose aucune
    // saisie ni aucune commande d'écriture : the structure lists `edit_estimate` unavailable
    // (`project_before_in_progress`), and the planning available besides, which opens nothing of the
    // estimate. The front reads the structure, it deduces no phase from the project.
    const inProgress = await estimateFor("me");
    expect(inProgress?.editable).toBe(false);
    // Handed so, the grid takes no entry and no paste: every cell reads `aria-readonly`.
    const readOnly = estimateGrid(estimateReference());
    expect(readOnly.columns.filter((column) => column.entry !== undefined)).toEqual([]);
    expect(readOnly.paste).toBeUndefined();
    server.answers = { ...server.answers, [STRUCTURES]: "structures_without_tasks" };
    const inPricing = await estimateFor("me");
    expect([inPricing?.editable, inPricing?.tasksEditable]).toEqual([true, true]);
  });

  it.each([
    {
      kind: "the amendment 2, a differential",
      structure: "01926f3a-7c00-7000-8000-000000000203",
      version: 2,
    },
    {
      kind: "the own estimate of a risk",
      structure: "01926f3a-7c00-7000-8000-000000000204",
      version: 1,
    },
  ])(
    "hands the grid entered on $kind the address names, at its version, the project in progress",
    async ({ structure, version }) => {
      // The differential and the own estimate of a risk list `edit_estimate` available whatever
      // the state of the project (`structures`): their estimate is entered where the main one is not.
      await estimatePage("me", { structure });
      const grid = grids.estimate.at(-1);
      expect(grid?.structure.structure_id).toBe(structure);
      expect([grid?.editable, grid?.tasksEditable]).toEqual([true, true]);
      expect(grid?.structureVersion).toBe(version);
    },
  );

  it("presents neither the duration nor the predecessors of a task, which the planning enters [WF-DEV-0050-A]", () => {
    // La grille de devis ne propose la saisie ni de la durée ni des prédécesseurs d'une tâche :
    // the entered grid has no such column.
    const unwritten = () => Promise.reject(new Error("nothing is written here"));
    const entered = estimateGrid(estimateReference(), {
      line: unwritten,
      task: unwritten,
      paste: { preview: unwritten, apply: unwritten, span: () => [], name: () => "" },
    });
    const keys: string[] = entered.columns.map((column) => column.key);
    expect(keys).not.toContain("duration");
    expect(keys).not.toContain("predecessors");
    expect(keys).toContain("label");
  });
});

describe("the reference data the estimate is entered from", () => {
  it("hands the grid the type of the cost of each category, by which a line is created from an expense or a role [WF-DEV-0020-A]", async () => {
    const grid = await estimateFor("me");
    const kinds = new Set(grid?.reference.categories?.map(({ kind }) => kind));
    expect(kinds).toEqual(new Set(["labor", "non_labor", "provision"]));
  });

  it("asks the active ones alone of a session that only reads the cost and resource settings, which the contract keeps for the permission to modify them [WF-REF-0150-A]", async () => {
    // The consultation alone: the permissions to read kept, those to modify withdrawn. The fake back
    // answers the deactivated ones whatever is asked, so the request of the page is what is proved.
    withdrawn.permissions = ["cost_settings.write", "resource_settings.write"];
    const grid = await estimateFor("me");
    expect(queryOf("/cost-categories")?.has("include_inactive")).toBe(false);
    expect(queryOf("/resource-roles")?.has("include_inactive")).toBe(false);
    expect(grid?.reference.roles).toBeDefined();
  });

  it("asks the deactivated categories and roles with the permissions of the reference that keep them", async () => {
    const grid = await estimateFor("me");
    expect(queryOf("/cost-categories")?.get("include_inactive")).toBe("true");
    expect(queryOf("/resource-roles")?.get("include_inactive")).toBe("true");
    expect(grid?.reference.roles?.some(({ active }) => !active)).toBe(true);
  });

  it("asks only the active ones of a part of the reference the session may not modify, and still enters the estimate on them (#351) [WF-REF-0150-A]", async () => {
    // The estimator reads the cost settings without modifying them, and has no resource settings:
    // the contract would refuse him the deactivated ones (403), and he enters on the active ones.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures_estimator",
    };
    const grid = await estimateFor("me_estimator");
    expect(queryOf("/cost-categories")?.has("include_inactive")).toBe(false);
    expect(queryOf("/resource-roles")?.has("include_inactive")).toBe(false);
    expect(grid?.reference.roles).toBeDefined();
    // The lines, not the label of a task, which is the planning's.
    expect([grid?.editable, grid?.tasksEditable]).toEqual([true, false]);
  });
});

describe("the way from the estimate to the imports and exports (#521)", () => {
  it("leads a costing engineer who does not read the planning to the screen of the imports, the import of an estimate listed", async () => {
    const page = await estimatePage("me_estimator");
    expect(page).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}/exchanges"`);
    expect(page).toContain("Imports and exports");
  });

  it("leads there too when the import is listed unavailable, which that screen presents with what it lacks (WF-IHM-0090)", async () => {
    // The import of an estimate listed unavailable, lacking `may_create_revision`.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing_estimator",
    };
    expect(await estimatePage("me_estimator")).toContain("/exchanges");
  });

  it("offers no way there when the project lists no import of an estimate", async () => {
    // A manager reads the estimate, and may import nothing: the project lists him no command.
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_reader" };
    expect(await estimatePage("me_manager")).not.toContain("/exchanges");
  });
});

describe("the link of the estimate to the workload (#1069)", () => {
  const WORKLOAD = `/projects/${PROJECT}/revisions/${REVISION}/workload`;

  it("opens the workload on the reference budget once the project is in progress, and on the remaining of the revision under way while it is priced [WF-DEV-0070-A]", async () => {
    expect(await estimatePage("me")).toContain(`href="${WORKLOAD}?basis=reference_budget"`);
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing_estimator",
    };
    expect(await estimatePage("me_estimator")).toContain(
      `href="${WORKLOAD}?basis=current_remaining"`,
    );
  });

  it("keeps the context of the address, and adds the basis to it [WF-DEV-0070-A]", async () => {
    const page = await estimatePage("me", { as_of: "2026-03-16" });
    expect(page).toContain(`href="${WORKLOAD}?as_of=2026-03-16&amp;basis=reference_budget"`);
  });
});

describe("the shares of the estimate (#626)", () => {
  it("says a share too small to show below the smallest shown, never « 0% »", async () => {
    // The estimate the offer v1.0 kept at its marking: its work package, 2,080.15 of 70,313,565.61,
    // the server gives a share of « 0.00003 », to its first significant digit (EP-14/L42o).
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/estimate-indicators": "estimate_indicators_breakdown",
    };
    const page = (await estimatePage("me"))
      .replace(/<[^>]+>/g, " ")
      .replace(/&lt;/g, "<")
      .replace(/\s+/g, " ");
    expect(page).toContain("By work package Computed on Lot 1 €2,080.15 (<0.01%)");
    expect(page).toContain("Computed on No subproject €70,313,565.61 (100%)");
  });
});

describe("the filter of the estimate by a lot or a post", () => {
  it("offers the lots and the posts of the work breakdown read whole, named by their kind", async () => {
    const page = await estimatePage("me");
    expect(menuText(page, "Work package or order item")).toBe("All work packages and order items");
    // The lot, then its post, in the order of the work breakdown, which the menu of the bar lists.
    expect(filtersOf(grids.estimate.at(-1)).breakdown?.items.map((item) => item.id)).toEqual([
      LOT,
      ITEM,
    ]);
    expect(queryOf("/work-breakdown")?.toString()).toBe("");
  });

  it("asks the server for the subtree of the lot the address names, the indicators of the whole project, and says it restricts the grid alone", async () => {
    const page = await estimatePage("me", { work_package_id: LOT });
    expect(queryOf("/nodes")?.get("work_package_id")).toBe(LOT);
    expect(queryOf("/estimate-indicators")?.has("work_package_id")).toBe(false);
    // The grid reads its totals anew, those of the structure a write answers not being its own.
    expect(grids.estimate.at(-1)?.filters).toMatchObject({ work_package_id: LOT });
    expect(menuText(page, "Work package or order item")).toBe("Work package: Lot 1");
    expect(page).toContain("Work package: Lot 1, on the grid only");
    expect(page).toContain(
      'aria-label="Remove the filter “Work package: Lot 1, on the grid only”"',
    );
  });

  it("opens without the filter when the API refuses the work breakdown, the grid read whole", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/work-breakdown": {
        problem: { code: "VALIDATION_FAILED", status: 422 },
      },
    };
    const page = await estimatePage("me");
    expect(page).not.toContain("Work package or order item");
    expect(queryOf("/nodes")?.has("work_package_id")).toBe(false);
    expect(grids.estimate).not.toHaveLength(0);
  });
});

describe("« Écarts seulement » on the grid of the estimate [WF-REV-0100-A]", () => {
  const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
  const RISK = "01926f3a-7c00-7000-8000-000000000204";
  const ALL = "added,removed,modified";
  const BUTTON =
    /<button[^>]*aria-pressed="(true|false)"[^>]*>(?:(?!<\/button>).)*Differences only(?:<\/span>)?<\/button>/;

  it("passes the differences to the server on a differential, presses the button and says in the banner it restricts the grid alone", async () => {
    const page = await estimatePage("me", { structure: AMENDMENT, difference: ALL });
    expect(queryOf("/nodes")?.get("difference")).toBe(ALL);
    expect(BUTTON.exec(page)?.[1]).toBe("true");
    expect(page).toContain("Differences only, on the grid only");
    expect(grids.estimate.at(-1)?.filters.difference).toEqual(["added", "removed", "modified"]);
  });

  it("offers it unpressed on a differential the address names no differences of", async () => {
    const page = await estimatePage("me", { structure: AMENDMENT });
    expect(BUTTON.exec(page)?.[1]).toBe("false");
    expect(queryOf("/nodes")?.has("difference")).toBe(false);
  });

  it("neither offers, nor sends, nor says it on the main structure and on the own estimate of a risk", async () => {
    for (const search of [{ difference: ALL }, { structure: RISK, difference: ALL }]) {
      server.clients = [];
      const page = await estimatePage("me", search);
      expect(queryOf("/nodes")?.has("difference")).toBe(false);
      expect(page).not.toContain("Differences only");
    }
  });
});

describe("the estimate served by the service", () => {
  it("shows no note of the mock-up: what the grid writes is kept, and its reads are filtered by the server (US-1560)", async () => {
    const page = await estimatePage("me");
    expect(page).not.toContain('role="note"');
    expect(page).not.toContain("Filters, search, sort and pages are ignored");
  });
});

describe("the filter of the estimate on the rows a risk occurred merged", () => {
  const OCCURRED = "01926f3a-7c00-7000-8000-000000000752";
  const IDENTIFIED = "01926f3a-7c00-7000-8000-000000000751";
  const RISKS = "GET /projects/{project_id}/risks";

  it("offers « Coming from a risk » and the risks occurred of the project alone, never one identified [WF-RIS-0060-A]", async () => {
    const page = await estimatePage("me");
    expect(menuText(page, "Origin")).toBe("All rows");
    expect(filtersOf(grids.estimate.at(-1)).origin?.risks.map((risk) => risk.id)).toEqual([
      OCCURRED,
    ]);
    expect(page).not.toContain(IDENTIFIED);
    expect(queryOf("/risks")?.getAll("states")).toEqual(["occurred"]);
    expect(queryOf("/nodes")?.has("is_from_risk")).toBe(false);
    expect(queryOf("/nodes")?.has("origin_risk_ids")).toBe(false);
  });

  it("asks the server for the rows of any risk when the address says so, and shows it chosen [WF-RIS-0060-A]", async () => {
    const page = await estimatePage("me", { is_from_risk: "true" });
    expect(queryOf("/nodes")?.get("is_from_risk")).toBe("true");
    expect(grids.estimate.at(-1)?.filters).toMatchObject({ is_from_risk: true });
    expect(menuText(page, "Origin")).toBe("Coming from a risk");
  });

  it("asks the server for the rows of the risk the address names, and hands the grid its label to name it by [WF-RIS-0060-A]", async () => {
    const page = await estimatePage("me", { origin_risk_ids: OCCURRED });
    expect(queryOf("/nodes")?.get("origin_risk_ids")).toBe(OCCURRED);
    expect(queryOf("/nodes")?.has("is_from_risk")).toBe(false);
    expect(grids.estimate.at(-1)?.origins).toEqual({
      [OCCURRED]: "Retard de livraison des armoires",
    });
    expect(menuText(page, "Origin")).toBe("Retard de livraison des armoires");
  });

  it("reads no value that is no identifier, as if the address named nothing [WF-RIS-0060-A]", async () => {
    await estimatePage("me", { origin_risk_ids: "not-an-identifier" });
    expect(queryOf("/nodes")?.has("origin_risk_ids")).toBe(false);
  });

  /** The nodes the page asked for, the filter on a risk or not. */
  const NODE_ROUTE =
    "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";

  it("keeps the page, unfiltered and the filter lifted, when the session lists no risk and the server finds the one named unknown [WF-RIS-0060-A]", async () => {
    server.answers = {
      ...server.answers,
      [RISKS]: { problem: { code: "NOT_FOUND", status: 404 } },
      [NODE_ROUTE]: [
        {
          problem: {
            code: "VALIDATION_FAILED",
            status: 422,
            fields: [{ pointer: "/query/origin_risk_ids/0", code: "UNKNOWN_RISK" }],
          },
        },
        "nodes",
      ],
    };
    const page = await estimatePage("me", { origin_risk_ids: OCCURRED });
    const asked = server.clients
      .flatMap((client) => client.calls)
      .filter((call) => call.route === NODE_ROUTE);
    expect(asked.map((call) => call.query.has("origin_risk_ids"))).toEqual([true, false]);
    expect(grids.estimate.at(-1)?.filters).not.toHaveProperty("origin_risk_ids");
    expect(menuText(page, "Origin")).toBe("All rows");
    expect(filtersOf(grids.estimate.at(-1)).origin?.risks).toEqual([]);
  });

  it("falls into error, the nodes read once, when the server refuses the rows for another cause than an unknown risk [WF-RIS-0060-A]", async () => {
    server.answers = {
      ...server.answers,
      [RISKS]: { problem: { code: "NOT_FOUND", status: 404 } },
      [NODE_ROUTE]: {
        problem: {
          code: "VALIDATION_FAILED",
          status: 422,
          fields: [{ pointer: "/query/origin_risk_ids/0", code: "VALUE_OUT_OF_RANGE" }],
        },
      },
    };
    await expect(estimatePage("me", { origin_risk_ids: OCCURRED })).rejects.toThrow();
    expect(
      server.clients.flatMap((client) => client.calls).filter((call) => call.route === NODE_ROUTE),
    ).toHaveLength(1);
  });

  it("reads the rows with the risks occurred, not after them, when the address names no risk [WF-RIS-0060-A]", async () => {
    // #1955: the list of the risks is held; the rows are asked for all the same.
    const NODES_ROUTE_END = "/nodes";
    const answer = held();
    server.hold = (route) => (route === RISKS ? answer.until : undefined);
    const loaded = estimatePage("me");
    try {
      await vi.waitFor(() => {
        expect(queryOf("/risks")).toBeDefined();
      });
      await vi.waitFor(() => {
        expect(queryOf(NODES_ROUTE_END)).toBeDefined();
      });
    } finally {
      answer.release();
    }
    await loaded;
  });

  it("opens with « Coming from a risk » alone when the project has no risks to read to it", async () => {
    server.answers = {
      ...server.answers,
      [RISKS]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const page = await estimatePage("me");
    expect(menuText(page, "Origin")).toBe("All rows");
    expect(filtersOf(grids.estimate.at(-1)).origin?.risks).toEqual([]);
  });
});
