// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
// L'export du Gantt (US-0530) : sur toute son étendue au niveau choisi, la teinte et la légende
// des jours chômés, le niveau des heures travaillées ; le test du titre, du projet, de la révision
// et de la date de calcul cite WF-IHM-0130-A, les autres n'ont pas d'exigence propre.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { NodeList, NodeSortColumn } from "@/components/grid/nodes";
import { PlanningGrid } from "@/components/grid/planning-grid";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { exportGanttPng, type GanttColours, ganttOverflow } from "./gantt-image";
import { ganttLayout } from "./layout";

const server = vi.hoisted((): { client: (ApiClient & FakeClient) | undefined } => ({
  client: undefined,
}));
vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The studies of the witness, without their lines (`nodes_planning`), and when they were calculated.
const planning = example("nodes_planning") as NodeList;
const SCHEDULED_AT = planning.meta.scheduled_at;
const TASKS = planning.items.filter((item) => item.task !== null && item.task !== undefined);
const PROJECT = "Modernisation du poste de commande";

/** What a canvas was asked to draw: its calls and the properties set, and its size when taken. */
interface Drawn {
  readonly calls: [string, unknown[]][];
  readonly sets: [string, unknown][];
  taken?: readonly [number, number];
}

const canvases = vi.hoisted(() => ({
  drawn: [] as Drawn[],
  of: new WeakMap<HTMLCanvasElement, Drawn>(),
  files: [] as string[],
  revoked: [] as string[],
  blank: false,
}));

/** A context of a canvas that records what it is asked: the simulated document paints none. */
function recorder(drawn: Drawn): CanvasRenderingContext2D {
  const state: Record<string, unknown> = {};
  return new Proxy(state, {
    get: (_, key) => {
      const name = String(key);
      if (name in state) {
        return state[name];
      }
      return (...args: unknown[]) => {
        drawn.calls.push([name, args]);
        if (name === "measureText") {
          return { width: String(args[0]).length * 6 };
        }
        return name === "createPattern" ? { setTransform: () => undefined } : undefined;
      };
    },
    set: (_, key, value) => {
      drawn.sets.push([String(key), value]);
      state[String(key)] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
}

/** Render the grid of the planning, its Gantt given the hours of a day and its provenance. */
function renderPlanning(hoursPerDay: number | undefined = 8, nodes: NodeList = planning) {
  const rendered = render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{}}
        query={NO_QUERY}
        preferences={undefined}
        gantt={{
          hoursPerDay,
          exported: {
            provenance: { project: PROJECT, code: "PRJ-001", revision: "Révision en cours" },
            scheduledAt: SCHEDULED_AT,
          },
        }}
      />
    </NextIntlClientProvider>,
  );
  // The colours of the hatching, as the document would show its tokens.
  const fill = document.querySelector<SVGElement>('[data-probe="day-off"]');
  const mark = document.querySelector<SVGElement>('[data-probe="day-off-mark"]');
  fill?.style.setProperty("fill", "rgb(1, 2, 3)");
  mark?.style.setProperty("stroke", "rgb(4, 5, 6)");
  return rendered;
}

/** The header of the Gantt, the last of the grid. */
function ganttHeader(): HTMLElement {
  const header = screen.getAllByRole("columnheader").at(-1);
  if (header === undefined) {
    throw new Error("no header");
  }
  return header;
}

/** Zoom in by the button of the header of the Gantt, so many times. */
async function zoomIn(times: number) {
  for (let step = 0; step < times; step += 1) {
    await userEvent.click(within(ganttHeader()).getByRole("button", { name: "Zoom avant" }));
  }
}

/** The image drawn: the canvas whose picture was taken. */
function image(): Drawn {
  const taken = canvases.drawn.filter((drawn) => drawn.taken !== undefined);
  const [drawn, ...others] = taken;
  if (drawn === undefined || others.length > 0) {
    throw new Error(`${String(taken.length)} images taken, not one`);
  }
  return drawn;
}

/** What a canvas wrote. */
function texts(drawn: Drawn): string[] {
  return drawn.calls.filter(([name]) => name === "fillText").map(([, args]) => String(args[0]));
}

beforeEach(() => {
  window.sessionStorage.clear();
  canvases.drawn = [];
  canvases.files = [];
  canvases.revoked = [];
  canvases.blank = false;
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1400);
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(function context(
    this: HTMLCanvasElement,
  ) {
    const drawn: Drawn = { calls: [], sets: [] };
    canvases.drawn.push(drawn);
    canvases.of.set(this, drawn);
    return recorder(drawn);
  });
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(function taken(
    this: HTMLCanvasElement,
    callback: BlobCallback,
  ) {
    const drawn = canvases.of.get(this);
    if (drawn !== undefined) {
      drawn.taken = [this.width, this.height];
    }
    callback(canvases.blank ? null : new Blob(["png"], { type: "image/png" }));
  });
  vi.stubGlobal("URL", {
    createObjectURL: () => "blob:png",
    revokeObjectURL: (url: string) => {
      canvases.revoked.push(url);
    },
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function saved(
    this: HTMLAnchorElement,
  ) {
    canvases.files.push(this.download);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("the export of the Gantt", () => {
  it("draws its whole extent at the level chosen, named after the project, the revision and the date of calculation [WF-IHM-0130-A]", async () => {
    renderPlanning();
    // The weeks over their days: 61 days of 24 points, the drawing wider than its column.
    await zoomIn(1);
    await userEvent.click(within(ganttHeader()).getByRole("button", { name: "Exporter en PNG" }));
    expect(canvases.files).toEqual(["gantt-PRJ-001.png"]);
    // The object address of the picture is released once the file is saved.
    expect(canvases.revoked).toEqual(["blob:png"]);
    // Twice as dense as the screen: the drawing and its margins, the head of two lines, the axis,
    // a row for each task, the legend.
    const drawn = image();
    expect(drawn.taken).toEqual([2 * (1464 + 32), 2 * (72 + 36 + TASKS.length * 28 + 24 + 16)]);
    const written = texts(drawn);
    expect(written.slice(0, 2)).toEqual([
      `Diagramme de Gantt — ${PROJECT}`,
      `Révision : Révision en cours · Calculé le ${formatTimestamp(SCHEDULED_AT, "fr")}`,
    ]);
    // The axis as the header writes it, the weeks over their days.
    const axis = [...ganttHeader().querySelectorAll("text")].map((text) => text.textContent);
    expect(axis).toContain("9 mars 2026");
    expect(written.slice(2, -1)).toEqual(axis);
    expect(written.at(-1)).toBe("Jour chômé : aucune heure de travail au calendrier de la tâche");
  });

  it("hatches the days off as the screen does, in the tokens of the charter", async () => {
    renderPlanning();
    await zoomIn(1);
    await userEvent.click(within(ganttHeader()).getByRole("button", { name: "Exporter en PNG" }));
    // The tile of the hatching: six points of the tint, a stroke of one and a half of the mark.
    const tile = canvases.drawn.find((drawn) =>
      drawn.sets.some(([name, value]) => name === "fillStyle" && value === "rgb(1, 2, 3)"),
    );
    expect(tile?.sets).toContainEqual(["strokeStyle", "rgb(4, 5, 6)"]);
    expect(tile?.sets).toContainEqual(["lineWidth", 1.5]);
    expect(tile?.calls).toContainEqual(["fillRect", [0, 0, 6, 6]]);
    // The image fills the bands of the days off, and the swatch of its legend, with it.
    const patterns = image().calls.filter(([name]) => name === "createPattern");
    expect(patterns).toHaveLength(2);
  });

  it("zooms down to the worked hours of a day, numbered, and draws them twice as dense while a canvas holds them", async () => {
    renderPlanning();
    await zoomIn(2);
    expect(within(ganttHeader()).getByRole("button", { name: "Zoom avant" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    // Twenty points an hour: every other hour is written, from the first of the day.
    const lower = [...ganttHeader().querySelectorAll("text")].map((text) => text.textContent);
    expect(lower).toEqual(expect.arrayContaining(["1", "3", "5", "7"]));
    expect(lower).not.toContain("2");
    await userEvent.click(within(ganttHeader()).getByRole("button", { name: "Exporter en PNG" }));
    expect(image().taken?.[0]).toBe(2 * (61 * 8 * 20 + 32));
  });

  it("draws a day of twenty-four hours as dense as the screen, a canvas twice as dense being too wide", async () => {
    renderPlanning(24);
    await zoomIn(2);
    await userEvent.click(within(ganttHeader()).getByRole("button", { name: "Exporter en PNG" }));
    expect(image().taken?.[0]).toBe(61 * 24 * 20 + 32);
  });

  it("is exported from the menu of a cell too, which the keyboard reaches", async () => {
    renderPlanning(undefined);
    const cell = document.querySelector<HTMLElement>('td[data-column="gantt"]');
    fireEvent.contextMenu(cell ?? document.body, { clientX: 300, clientY: 200 });
    const menu = await screen.findByRole("menu");
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Exporter en PNG" }));
    expect(canvases.files).toEqual(["gantt-PRJ-001.png"]);
    // Fitted to the project: the width of its column, which the header of the grid measures.
    expect(image().taken?.[0]).toBeGreaterThan(0);
  });

  it("is drawn only within the bounds of a canvas, its legend and a long head counted", () => {
    expect(ganttOverflow(1000, 1000, true)).toBeUndefined();
    // Too long: 1 200 rows of 28 points pass 32 767.
    expect(ganttOverflow(1000, 1200, false)).toBe("height");
    // Too wide, at the hours of years.
    expect(ganttOverflow(40_000, 10, false)).toBe("width");
    // Each side within, the whole too large.
    expect(ganttOverflow(20_000, 900, true)).toBe("area");
  });

  it("is unavailable, saying how to bring it back, when its rows pass the height of a canvas", async () => {
    // 1 200 rows of tasks, each a copy of the first: fitted to the project, no zoom changes a height.
    const [first] = TASKS;
    const many: NodeList = {
      ...planning,
      items: Array.from({ length: 1200 }, (_, index) => ({
        ...first,
        node_id: `01926f3a-7c00-7000-8000-${String(index).padStart(12, "0")}`,
      })) as NodeList["items"],
    };
    renderPlanning(8, many);
    const button = within(ganttHeader()).getByRole("button", { name: "Exporter en PNG" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(button);
    expect(canvases.files).toEqual([]);
    // The remedy of the bound passed: fold, not zoom out.
    await userEvent.hover(button);
    const why = "L’image serait trop haute pour le navigateur : pliez des récapitulatives.";
    expect((await screen.findAllByText(why)).length).toBeGreaterThan(0);
    const cell = document.querySelector<HTMLElement>('td[data-column="gantt"]');
    fireEvent.contextMenu(cell ?? document.body, { clientX: 300, clientY: 200 });
    const item = within(await screen.findByRole("menu")).getByRole("menuitem", {
      name: "Exporter en PNG",
    });
    expect(item).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(item);
    expect(canvases.files).toEqual([]);
  });

  it("saves nothing when the head, measured, makes an image no canvas holds, though it was judged to", () => {
    // 1 160 rows hold with the head usually written; a project name of many lines does not.
    const rows = Array.from({ length: 1160 }, (_, index) => ({ node_id: String(index) }));
    const drawing = {
      rows,
      layout: ganttLayout(rows),
      width: 1000,
      lower: [],
      upper: [],
      labels: { upper: [], lower: [] },
      dayWidth: 1,
      legend: undefined,
    };
    expect(ganttOverflow(1000, rows.length, false)).toBeUndefined();
    const colours: GanttColours = {
      text: "",
      grid: "",
      mark: "",
      background: "",
      font: "sans-serif",
      critical: "",
      primary: "",
      dayOff: "",
      dayOffMark: "",
    } as GanttColours;
    const long = Array.from({ length: 400 }, () => "projet").join(" ");
    const refused = { title: long, subtitle: "révision", fileName: "g.png" };
    expect(exportGanttPng(drawing, colours, refused)).toBe(false);
    expect(canvases.files).toEqual([]);
    const usual = { title: "Gantt", subtitle: "révision", fileName: "g.png" };
    expect(exportGanttPng(drawing, colours, usual)).toBe(true);
    expect(canvases.files).toEqual(["g.png"]);
  });

  it("saves no file when the canvas gives no picture", async () => {
    canvases.blank = true;
    renderPlanning();
    await userEvent.click(within(ganttHeader()).getByRole("button", { name: "Exporter en PNG" }));
    expect(canvases.files).toEqual([]);
  });

  it("says that the numbers of the lower row are worked hours, on the screen and in the image", async () => {
    renderPlanning();
    await zoomIn(2);
    const note = "Échelle en heures travaillées, numérotées dans la journée";
    expect(within(ganttHeader()).getByRole("img", { name: note })).toBeInTheDocument();
    await userEvent.click(within(ganttHeader()).getByRole("button", { name: "Exporter en PNG" }));
    expect(texts(image())[1]).toContain(note);
  });
});
