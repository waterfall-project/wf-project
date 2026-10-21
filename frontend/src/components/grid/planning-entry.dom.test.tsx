// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  held,
  type Problem,
} from "@/test/fixtures";

import type { NodeList, NodeSortColumn } from "./nodes";
import { breakdownItems, type WorkBreakdownReading } from "./planning-attachment";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The cells of a task entered in the grid of the planning (US-0470): what each sends to
// `updateTaskFacet`, which cells the node lets be entered, and where the cursor goes.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
const TASK =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task";
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The tasks of the studies: the summary « Études », the details completed and the review that
// follows them, both automatic, the desks in manual mode, the milestone of reception, the design
// file; and the core of the witness, its « Mise en service » automatic.
const planning = example("nodes_planning") as NodeList;
const nested = example("nodes_nested") as NodeList;
const breakdown = breakdownItems(example("work_breakdown") as WorkBreakdownReading);

/** The index of a row of a list, by the label of its task. */
function rowOf(list: NodeList, label: string): number {
  return list.items.findIndex((node) => node.task?.label === label);
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(answers, { hold: () => hold });
  server.client = client;
  return client;
}

/** The grid of the planning over the nodes given, entered unless said otherwise. */
function grid(
  nodes: NodeList,
  {
    locale = "fr",
    editable = true,
  }: { readonly locale?: Locale; readonly editable?: boolean } = {},
) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable={editable}
        editable={editable}
        breakdown={editable ? breakdown : undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row, by its index, and of a column, by its key. */
function cellAt(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** Enter a cell from the keyboard, as F2 does, and give back the field it opens, if any. */
async function enter(row: number, column: string): Promise<HTMLElement | null> {
  await act(async () => {
    cellAt(row, column).focus();
    await Promise.resolve();
  });
  await userEvent.keyboard("{F2}");
  return within(screen.getByRole("treegrid")).queryByRole("textbox");
}

/** Enter a cell that takes an entry, and give back the field it opens. */
async function entered(row: number, column: string): Promise<HTMLElement> {
  const field = await enter(row, column);
  if (field === null) {
    throw new Error(`no entry in the cell ${column} of the row ${row.toString()}`);
  }
  return field;
}

/** Type a text in place of what the field of a cell holds, and validate it by Enter. */
async function retype(field: HTMLElement, text: string) {
  await userEvent.clear(field);
  await userEvent.type(field, `${text}{Enter}`);
}

/** The bodies of the writes of a task the grid sent, with the node each wrote. */
function written(client: FakeClient) {
  return client.calls
    .filter((call) => call.route === TASK)
    .map((call) => ({ node: call.path.split("/").at(-2), body: call.body }));
}

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the cells of a task entered in the grid of the planning", () => {
  it("traverses the dates an automatic task computes, never entering them, and enters those of a manual task [WF-PLA-0020-A]", async () => {
    // Les dates d'une tâche en mode automatique ne sont pas saisissables: the server names them in
    // `computed_fields`, and the cells refuse the entry; Tab from the duration goes past them.
    serve({});
    render(grid(planning));
    const review = rowOf(planning, "Revue de conception");
    expect(await enter(review, "start")).toBeNull();
    expect(cellAt(review, "start")).toHaveAccessibleName(/Calculé/);
    const duration = await entered(review, "duration");
    // The duration starts from its value and the suffix of its unit, as the cell writes it.
    expect(duration).toHaveValue("10\u00a0j");
    await userEvent.keyboard("{Tab}");
    expect(cellAt(review, "work_breakdown")).toHaveFocus();
    // The desks, in manual mode: the server names their dates among the fields they accept.
    const desks = rowOf(planning, "Pupitres opérateurs");
    expect(await enter(desks, "start")).toHaveValue("02/03/2026");
  });

  it("sets a task manual, then enters its dates, each write carrying the version the last answered [WF-PLA-0020-A]", async () => {
    // En mode manuel, l'utilisateur saisit ses dates: once the mode answered, the dates the server
    // computed are entered, the hours of the day kept.
    const client = serve({
      [TASK]: ["task_mode_changed", "task_dates_entered", "task_dates_entered"],
    });
    render(grid(nested));
    const commissioning = rowOf(nested, "Mise en service");
    const node = nested.items[commissioning]?.node_id;
    expect(await enter(commissioning, "start")).toBeNull();
    await act(async () => {
      cellAt(commissioning, "scheduling_mode").focus();
      await Promise.resolve();
    });
    await userEvent.keyboard("{Enter}");
    const mode = screen.getByRole("combobox", { name: "Mode de planification" });
    expect(mode).toHaveValue("automatic");
    fireEvent.change(mode, { target: { value: "manual" } });
    await userEvent.keyboard("{Enter}");
    expect(
      await within(cellAt(commissioning, "scheduling_mode")).findByRole("img", { name: "Manuel" }),
    ).toBeInTheDocument();
    const start = await entered(commissioning, "start");
    expect(start).toHaveValue("21/12/2026");
    await retype(start, "04/01/2027");
    expect(await within(cellAt(commissioning, "finish")).findByText("15/01/2027")).toBeVisible();
    await retype(await entered(commissioning, "finish"), "16/01/2027");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(3);
    });
    expect(written(client)).toEqual([
      { node, body: { scheduling_mode: "manual", lock_version: 1 } },
      { node, body: { start: { date: "2027-01-04", hours: "0" }, lock_version: 2 } },
      { node, body: { finish: { date: "2027-01-16", hours: "8" }, lock_version: 3 } },
    ]);
  });

  it.each([
    { locale: "fr", month: "1 m", minute: "1 min" },
    { locale: "en", month: "1 mo", minute: "1 min" },
  ] as const)(
    "reads « 1 m » as a month and « 1 min » as a minute in the cell of a duration, in $locale [WF-PLA-0160-A]",
    async ({ locale, month, minute }) => {
      // « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des langues de
      // l'interface: each sent in its unit, and shown pending with the suffix of the language.
      const hold = held();
      const horizon = example("task_horizon_exceeded") as Problem & { readonly status: 422 };
      const client = serve({ [TASK]: { problem: horizon } }, hold.until);
      render(grid(planning, { locale }));
      const details = rowOf(planning, "Études de détail");
      const review = rowOf(planning, "Revue de conception");
      await retype(await entered(details, "duration"), "1 m");
      await retype(await entered(review, "duration"), "1 min");
      await vi.waitFor(() => {
        expect(written(client)).toHaveLength(2);
      });
      expect(written(client).map(({ body }) => body)).toEqual([
        { duration: { value: "1", unit: "mo" }, lock_version: 1 },
        { duration: { value: "1", unit: "min" }, lock_version: 1 },
      ]);
      expect(cellAt(details, "duration")).toHaveTextContent(month);
      expect(cellAt(review, "duration")).toHaveTextContent(minute);
      hold.release();
    },
  );

  it("writes the label and the description, emptied to none, each alone with the version read", async () => {
    const client = serve({ [TASK]: ["task_description_entered", "task_description_entered"] });
    render(grid(planning));
    const file = rowOf(planning, "Dossier de conception");
    const node = planning.items[file]?.node_id;
    await retype(await entered(file, "description"), "Plans");
    expect(
      await within(cellAt(file, "description")).findByText(/^Plans, schémas et nomenclatures/),
    ).toBeVisible();
    // Emptied, the description is none.
    await userEvent.clear(await entered(file, "description"));
    await userEvent.keyboard("{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(2);
    });
    expect(written(client)).toEqual([
      { node, body: { description: "Plans", lock_version: 1 } },
      { node, body: { description: null, lock_version: 2 } },
    ]);
    // A label is never left blank: the entry stays open, saying why.
    const label = await entered(file, "label");
    await userEvent.clear(label);
    await userEvent.keyboard("{Enter}");
    expect(screen.getByText("Cette cellule ne peut pas rester vide.")).toBeInTheDocument();
    expect(written(client)).toHaveLength(2);
  });

  it("enters only the fields the node names, and none in a grid read only", async () => {
    serve({});
    const { rerender } = render(grid(planning));
    // The summary computes its duration and takes no mode; the milestone takes no duration.
    const summary = rowOf(planning, "Études");
    const milestone = rowOf(planning, "Réception des études");
    expect(await enter(summary, "duration")).toBeNull();
    expect(cellAt(summary, "scheduling_mode")).toHaveAttribute("aria-readonly", "true");
    expect(cellAt(milestone, "duration")).toHaveAttribute("aria-readonly", "true");
    expect(cellAt(milestone, "label")).not.toHaveAttribute("aria-readonly");
    rerender(grid(planning, { editable: false }));
    expect(cellAt(milestone, "label")).toHaveAttribute("aria-readonly", "true");
    expect(cellAt(milestone, "description")).toHaveAttribute("aria-readonly", "true");
  });

  it("goes on to the next row once the last cell of a row is validated, writing nothing unchanged", async () => {
    // Libellé, description, mode, durée, rattachement: Tab along the row, the computed dates
    // traversed; validated, the last places the cursor on the row below, at the cell the row was
    // started from.
    const client = serve({});
    render(grid(planning));
    const details = rowOf(planning, "Études de détail");
    await enter(details, "label");
    for (const column of ["description", "scheduling_mode", "duration", "work_breakdown"]) {
      await userEvent.keyboard("{Tab}");
      expect(cellAt(details, column)).toHaveFocus();
      await userEvent.keyboard("{Enter}");
    }
    await userEvent.keyboard("{Tab}");
    expect(cellAt(details + 1, "label")).toHaveFocus();
    expect(written(client)).toEqual([]);
  });

  it("says at its cell the refusal of a date the server computes, by the reason of its field", async () => {
    const problem = example("task_date_computed_refused") as Problem & { readonly status: 422 };
    serve({ [TASK]: { problem } });
    render(grid(planning));
    const desks = rowOf(planning, "Pupitres opérateurs");
    await retype(await entered(desks, "finish"), "30/04/2026");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cette valeur est calculée : elle ne se saisit pas.",
    );
    expect(cellAt(desks, "finish")).toHaveAttribute("aria-invalid", "true");
    expect(cellAt(desks, "finish")).toHaveTextContent("24/04/2026");
  });
});
