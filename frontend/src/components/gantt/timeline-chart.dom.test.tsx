// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { ChartOption } from "@/components/chart/chart";
import { WRITE_DELAY } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import type { TimelineTask } from "./timeline";
import { TimelineChart } from "./timeline-chart";

// The server of Next, as far as the frieze needs it: the preferences it records.
const server = vi.hoisted((): { client: (ApiClient & FakeClient) | undefined } => ({
  client: undefined,
}));
vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

/** What the instance out of the screen was handed for the exported image. */
const canvas = vi.hoisted(() => ({ options: [] as unknown[] }));

// The image is drawn on a canvas, which the simulated document does not paint: an instance in its
// place records what it is asked to draw.
vi.mock("echarts/core", async (actual) => {
  const echarts = await actual<typeof import("echarts/core")>();
  return {
    ...echarts,
    init: (...args: Parameters<typeof echarts.init>) => {
      if (args[2]?.renderer !== "canvas") {
        return echarts.init(...args);
      }
      return {
        setOption: (option: unknown) => canvas.options.push(option),
        getDataURL: () => "data:image/png;base64,iVBORw0KGgo=",
        dispose: () => undefined,
      };
    },
  };
});

const STEERING = "01926f3a-7c00-7000-8000-000000001000";
const PROJECT = "Modernisation du poste de commande";
const READ_AT = "2026-06-03T08:30:00Z";

/** The rows of the studies and of the control station of the core, by their number in the plan. */
function rows(...numbers: number[]): TimelineTask[] {
  const items = (example("nodes_core") as { items: TimelineTask[] }).items;
  return numbers.map((number) => {
    const row = items.find((item) => item.row_number === number);
    if (row === undefined) {
      throw new Error(`no row ${String(number)} in nodes_core`);
    }
    return row;
  });
}

// The studies, the detailed studies, the design review, the reception of the studies — a
// milestone —, the design file and the control station. Stacked in the order of the plan: the
// studies in the first lane, the detailed studies and the design review in the second, the design
// file — which overlaps the studies and the detailed studies — in the third, the control station in
// the first, after the studies.
const STUDIES = rows(1, 2, 5, 6, 7, 8);

/** Render the frieze of the steering committee over tasks, the lanes kept given. */
function renderFrieze(
  tasks: readonly TimelineTask[] = STUDIES,
  kept?: Readonly<Record<string, number>>,
) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TimelineChart
        name="Comité de pilotage"
        timeline={STEERING}
        tasks={tasks}
        kept={kept}
        provenance={{ project: PROJECT, code: "PRJ-001", revision: "Révision en cours" }}
        readAt={READ_AT}
        scope="timelines:test"
      />
    </NextIntlClientProvider>,
  );
}

/** The frieze, the one stop of the keyboard. */
function frieze(): HTMLElement {
  return screen.getByRole("group", {
    name: /^Frise de la chronologie «\s+Comité de pilotage\s+»$/,
  });
}

/** The rectangle of a task, by the start of its name. */
function rectangle(label: string): HTMLElement {
  return screen.getByRole("img", { name: new RegExp(`^${label}, du `) });
}

/** The lanes the frieze recorded, in the order it recorded them. */
function recorded(): unknown[] {
  return (server.client?.calls ?? [])
    .filter((call) => call.route === "PATCH /me/preferences")
    .map((call) => (call.body as { timelines?: Record<string, unknown> }).timelines?.[STEERING]);
}

/** The node of a task of the core, by its number in the plan. */
function node(number: number): string {
  return rows(number)[0]?.node_id ?? "";
}

beforeEach(() => {
  window.sessionStorage.clear();
  canvas.options = [];
  server.client = fakeClient({ "PATCH /me/preferences": "preferences_timeline_lanes" });
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1000);
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the frieze of a timeline", () => {
  // aucune exigence : propre à l'US (US-0530, la frise et ses couloirs).
  it("draws each task as a rectangle named by its task, its dates and its lane, its name cut short and whole in its tooltip", () => {
    renderFrieze();
    expect(rectangle("Études")).toHaveAccessibleName(
      "Études, du 02/03/2026 au 24/04/2026, couloir 1",
    );
    expect(rectangle("Études de détail")).toHaveAccessibleName(
      "Études de détail, du 02/03/2026 au 10/04/2026, couloir 2",
    );
    expect(rectangle("Revue de conception")).toHaveAccessibleName(/couloir 2$/);
    expect(rectangle("Dossier de conception")).toHaveAccessibleName(/couloir 3$/);
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 1$/);
    // The name is cut short by the rectangle, and whole in its tooltip.
    const named = rectangle("Dossier de conception");
    expect(named).toHaveClass("truncate");
    expect(named).toHaveAttribute("title", "Dossier de conception");
    expect(named).toHaveTextContent("Dossier de conception");
  });

  it("draws a milestone as a line across the frieze, named by its task and its date, written at its foot", () => {
    renderFrieze();
    const milestone = screen.getByRole("img", {
      name: "Réception des études, jalon le 24/04/2026",
    });
    expect(milestone.querySelector("line")).not.toBeNull();
    expect(milestone).toHaveTextContent("Réception des études");
    expect(milestone).toHaveTextContent("24/04/2026");
  });

  it("keeps the lanes the account placed the rectangles in, and stacks the others around them", () => {
    renderFrieze(STUDIES, { [node(8)]: 1 });
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 2$/);
    expect(rectangle("Études de détail")).toHaveAccessibleName(/couloir 2$/);
  });

  it("moves a rectangle down by Alt and the down arrow, past a lane where it would overlap, and records the lanes shown after a pause", async () => {
    const user = userEvent.setup();
    renderFrieze();
    // After the zoom in and out and the export — the automatic layout is already shown.
    for (let press = 0; press < 4; press += 1) {
      await user.tab();
    }
    expect(frieze()).toHaveFocus();
    // The left and right arrows go from rectangle to rectangle: the third is the design review.
    await user.keyboard("{ArrowRight}{ArrowRight}");
    expect(frieze()).toHaveAttribute("aria-activedescendant", rectangle("Revue de conception").id);
    // The third lane holds the design file, which it overlaps: it goes to the empty one below.
    await user.keyboard("{Alt>}{ArrowDown}{/Alt}");
    expect(rectangle("Revue de conception")).toHaveAccessibleName(/couloir 4$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Revue de conception » est dans le couloir 4.",
    );
    // Nothing else moved.
    expect(rectangle("Études de détail")).toHaveAccessibleName(/couloir 2$/);
    await waitFor(
      () => {
        expect(recorded()).toEqual([
          {
            lanes: {
              [node(5)]: 3,
              [node(1)]: 0,
              [node(2)]: 1,
              [node(7)]: 2,
              [node(8)]: 0,
            },
          },
        ]);
      },
      { timeout: WRITE_DELAY * 4 },
    );
  });

  it("refuses by the keyboard a lane where the rectangle would overlap another, says it, and moves nothing", async () => {
    renderFrieze();
    frieze().focus();
    fireEvent.keyDown(frieze(), { key: "ArrowRight" });
    // The detailed studies overlap the studies, in the only lane above.
    fireEvent.keyDown(frieze(), { key: "ArrowUp", altKey: true });
    expect(rectangle("Études de détail")).toHaveAccessibleName(/couloir 2$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Études de détail » chevaucherait « Études » dans le couloir 1 : elle reste dans le couloir 2.",
    );
    // The first lane is the top: nothing goes above it.
    fireEvent.keyDown(frieze(), { key: "Home" });
    fireEvent.keyDown(frieze(), { key: "ArrowUp", altKey: true });
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Études » est déjà dans le premier couloir.",
    );
    await new Promise((resolve) => setTimeout(resolve, WRITE_DELAY * 2));
    expect(recorded()).toEqual([]);
  });

  it("moves a rectangle by dragging it to another lane with the mouse, and refuses a drop where it would overlap", () => {
    renderFrieze();
    const file = rectangle("Dossier de conception");
    // The drawing starts at the top of the window in the simulated document: a lane is 32 points.
    fireEvent.pointerDown(file, { button: 0, pointerId: 1, clientY: 2 * 32 + 10 });
    fireEvent.pointerMove(file, { pointerId: 1, clientY: 32 + 10 });
    // Over the second lane, where it would overlap the detailed studies: the drop is refused.
    expect(file).toHaveClass("border-destructive");
    fireEvent.pointerUp(file, { pointerId: 1, clientY: 32 + 10 });
    expect(rectangle("Dossier de conception")).toHaveAccessibleName(/couloir 3$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Dossier de conception » chevaucherait « Études de détail » dans le couloir 2",
    );
    // The control station, dropped in the second lane, fits there.
    const station = rectangle("Poste de commande");
    fireEvent.pointerDown(station, { button: 0, pointerId: 2, clientY: 10 });
    fireEvent.pointerMove(station, { pointerId: 2, clientY: 32 + 10 });
    fireEvent.pointerUp(station, { pointerId: 2, clientY: 32 + 10 });
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 2$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Poste de commande » est dans le couloir 2.",
    );
  });

  it("gives back the automatic layout, which the account forgets", async () => {
    const user = userEvent.setup();
    renderFrieze(STUDIES, { [node(8)]: 1 });
    await user.click(screen.getByRole("button", { name: "Disposition automatique" }));
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 1$/);
    expect(screen.getByRole("button", { name: "Disposition automatique" })).toBeDisabled();
    await waitFor(
      () => {
        expect(recorded()).toEqual([null]);
      },
      { timeout: WRITE_DELAY * 4 },
    );
  });

  it("has a name, names each rectangle and milestone, and gives a reading as a table [WF-IHM-0100-A]", async () => {
    const { container } = renderFrieze();
    expect(screen.getByRole("figure", { name: "Comité de pilotage" })).toContainElement(frieze());
    const table = screen.getByRole("table", { name: "Lecture en table" });
    const lines = within(table)
      .getAllByRole("row")
      .map((row) => [...row.querySelectorAll("td, th")].map((cell) => cell.textContent));
    expect(lines).toEqual([
      ["N°", "Libellé", "Début", "Fin", "Couloir"],
      ["1", "Études", "02/03/2026", "24/04/2026", "1"],
      ["2", "Études de détail", "02/03/2026", "10/04/2026", "2"],
      ["5", "Revue de conception", "13/04/2026", "24/04/2026", "2"],
      ["6", "Réception des études", "24/04/2026", "24/04/2026", "Jalon"],
      ["7", "Dossier de conception", "09/04/2026", "15/04/2026", "3"],
      ["8", "Poste de commande", "04/05/2026", "30/06/2026", "1"],
    ]);
    await expectAccessible(container);
  });
});

describe("the export of the frieze", () => {
  it("draws a PNG image of the frieze as it is laid out, with the name of the timeline, the project, the revision and the date of the reading [WF-PLA-0140-A]", async () => {
    // L'export produit un fichier PNG de la chronologie affichée.
    const user = userEvent.setup();
    renderFrieze();
    fireEvent.keyDown(frieze(), { key: "End" });
    fireEvent.keyDown(frieze(), { key: "ArrowDown", altKey: true });
    await user.click(screen.getByRole("button", { name: "Exporter en PNG" }));
    expect(canvas.options).toHaveLength(1);
    const option = canvas.options[0] as ChartOption;
    expect(option.title).toMatchObject({
      text: `Comité de pilotage — ${PROJECT}`,
      subtext: `Révision : Révision en cours · Calculé le ${formatTimestamp(READ_AT, "fr")}`,
    });
    const [boxes, milestones] = option.series as { data: number[][] }[];
    // The lanes as laid out: the control station moved down to the second lane.
    expect(boxes?.data.map((box) => box[2])).toEqual([0, 1, 1, 2, 1]);
    expect(milestones?.data).toHaveLength(1);
  });
});
