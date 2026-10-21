// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EstimateGrid } from "@/components/grid/estimate-grid";
import type { NodesWritten } from "@/components/grid/nodes";
import { RemainingGrid } from "@/components/grid/remaining-grid";
import { forgetMessages } from "@/components/notices/message-history";
import { expectAccessible } from "@/test/axe";
import {
  cache,
  cellAt,
  COMMAND,
  LABOUR,
  PROVISION,
  TESTS,
  estimate,
  estimateGrid,
  FREIGHT,
  intl,
  LINE,
  NO_QUERY,
  openMenu,
  openSubmenu,
  REMINDER,
  remainingGrid,
  router,
  SHOWN,
  select,
  sent,
  serve,
  server,
  STRUCTURE,
  subprojects,
  THREE,
  threeLines,
  prepareMenuTests,
} from "@/test/choice-menu";
import { example, held, type Problem } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

// The submenu « Sous-projet » of the menu of a cell (US-0480), through the grids that offer it: the
// estimate and the remaining to commit. Some tests render a variant of a row of `nodes_estimate`,
// passed to the grid as a prop and never served as an answer (guide, « Tests »), each saying what
// it changes: the version of a row, so that its own is sent; the `editable_fields` of a row, so that
// it does not name the field; the sub-project a line bears; and the identifier of the line the
// example of the answer is about, so that the answer takes the place of the row read.

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({
  refresh: () => {
    cache.refresh();
  },
}));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

prepareMenuTests(forgetMessages);

describe("the submenu « Sous-projet » of a line", () => {
  it("lists the sub-projects as radio buttons, « Aucun sous-projet » first, the one of the line checked [WF-PRJ-0050-A]", async () => {
    serve();
    const read = structuredClone(estimate);
    const line = read.items[FREIGHT]?.estimate_line;
    if (line === undefined || line === null) {
      throw new Error("the example holds no such line");
    }
    line.subproject_id = COMMAND;
    render(estimateGrid(read));
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    const radios = within(menu).getAllByRole("menuitemradio");
    expect(radios.map((radio) => radio.textContent)).toEqual([
      "Aucun sous-projet",
      "SP-CMD — Poste de commande",
      "SP-ESS — Essais et mise en service",
    ]);
    expect(radios.map((radio) => radio.getAttribute("aria-checked"))).toEqual([
      "true",
      "false",
      "false",
    ]);
    await userEvent.keyboard("{Escape}{Escape}");
    const other = await openSubmenu(FREIGHT, "Sous-projet");
    expect(
      within(other)
        .getAllByRole("menuitemradio")
        .map((radio) => radio.getAttribute("aria-checked")),
    ).toEqual(["false", "true", "false"]);
  });

  it("names each sub-project by its code, which alone is unique in a project: two of the same label have radio buttons of their own, in the estimate and in the remaining to commit [WF-PRJ-0050-A]", async () => {
    serve();
    const twins = [
      { id: "01926f3a-7c00-7000-8000-0000000008a1", label: "Lot", code: "SP-A" },
      { id: "01926f3a-7c00-7000-8000-0000000008a2", label: "Lot", code: "SP-B" },
    ];
    const view = render(
      intl(
        <RemainingGrid
          nodes={estimate}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{ progress: ["started"] }}
          editable
          subprojects={twins}
          query={NO_QUERY}
          preferences={SHOWN}
        />,
      ),
    );
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    expect(within(menu).getByRole("menuitemradio", { name: "SP-A — Lot" })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitemradio", { name: "SP-B — Lot" })).toBeInTheDocument();
    view.unmount();
    render(estimateGrid());
    const named = await openSubmenu(REMINDER, "Sous-projet");
    expect(
      within(named)
        .getAllByRole("menuitemradio")
        .map((radio) => radio.textContent),
    ).toEqual([
      "Aucun sous-projet",
      "SP-CMD — Poste de commande",
      "SP-ESS — Essais et mise en service",
    ]);
  });

  it("carries a line to a sub-project, and takes it out of any: one write of the line with its version [WF-PRJ-0050-A]", async () => {
    // Le passage à un autre sous-projet d'une ligne d'une tâche non démarrée aboutit.
    const client = serve({ [LINE]: "estimate_line_subproject_changed" });
    render(estimateGrid());
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-ESS — Essais et mise en service" }),
    );
    await waitFor(() => {
      expect(sent(client, LINE)).toHaveLength(1);
    });
    expect(sent(client, LINE)).toEqual([{ subproject_id: TESTS, lock_version: 1 }]);
    expect(
      await screen.findByText("Sous-projet de « Frais de relance » mis à jour."),
    ).toBeInTheDocument();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("takes a line out of its sub-project by « Aucun sous-projet » [WF-PRJ-0050-A]", async () => {
    const client = serve({ [LINE]: "estimate_line_subproject_changed" });
    const read = structuredClone(estimate);
    const line = read.items[REMINDER]?.estimate_line;
    if (line === undefined || line === null) {
      throw new Error("the example holds no such line");
    }
    line.subproject_id = COMMAND;
    render(estimateGrid(read));
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    await userEvent.click(within(menu).getByRole("menuitemradio", { name: "Aucun sous-projet" }));
    await waitFor(() => {
      expect(sent(client, LINE)).toHaveLength(1);
    });
    expect(sent(client, LINE)).toEqual([{ subproject_id: null, lock_version: 1 }]);
  });

  it("offers no submenu on a line that does not name its sub-project among the fields it accepts: a line of a task started whose sub-project has actual costs, a provision [WF-PRJ-0050-A]", async () => {
    // Celui de la ligne de provision d'un risque identifié passe par le risque.
    serve();
    render(estimateGrid());
    for (const row of [LABOUR, PROVISION]) {
      const menu = await openMenu(row);
      expect(within(menu).queryByRole("menuitem", { name: "Sous-projet" })).toBeNull();
      await userEvent.keyboard("{Escape}");
    }
  });

  it("offers no submenu in an estimate read only, nor when the sub-projects of the project were refused [WF-PRJ-0050-A]", async () => {
    serve();
    const view = render(estimateGrid(estimate, false));
    fireEvent.contextMenu(cellAt(REMINDER, "label"), { clientX: 300, clientY: 200 });
    expect(screen.queryByRole("menuitem", { name: "Sous-projet" })).toBeNull();
    view.unmount();
    render(
      intl(
        <EstimateGrid
          nodes={estimate}
          structure={STRUCTURE}
          structureVersion={1}
          reference={{ ...estimateReference(), subprojects: undefined }}
          editable
          tasksEditable
          query={NO_QUERY}
          filters={{}}
          preferences={SHOWN}
        />,
      ),
    );
    const menu = await openMenu(REMINDER);
    expect(within(menu).queryByRole("menuitem", { name: "Sous-projet" })).toBeNull();
  });

  it("tells the refusal of a sub-project that has actual costs at the row, naming the sub-project [WF-PRJ-0050-A]", async () => {
    // Le passage à un autre sous-projet d'une ligne d'une tâche démarrée, dont le sous-projet a reçu
    // des coûts réels, est refusé et nomme ce sous-projet.
    const client = serve({
      [LINE]: {
        problem: example("estimate_line_subproject_has_actual_costs") as Problem & { status: 422 },
      },
    });
    render(estimateGrid());
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-ESS — Essais et mise en service" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Refusé à la ligne 15,");
    expect(alert).toHaveTextContent("Cette ligne ne peut pas quitter ce sous-projet");
    expect(alert).toHaveTextContent("Poste de commande");
    expect(sent(client, LINE)).toHaveLength(1);
  });

  it("applies to each line of the selection that names its sub-project, one write per line with its version, the task between them left aside [WF-PRJ-0050-A]", async () => {
    const read = structuredClone(estimate);
    const [first, last] = [read.items[REMINDER], read.items[FREIGHT]];
    if (first === undefined || last === undefined) {
      throw new Error("the example holds no such rows");
    }
    first.lock_version = 3;
    last.lock_version = 9;
    const client = serve({ [LINE]: "estimate_line_subproject_changed" });
    render(estimateGrid(read));
    await select(REMINDER, FREIGHT);
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-CMD — Poste de commande" }),
    );
    await waitFor(() => {
      expect(sent(client, LINE)).toHaveLength(2);
    });
    expect(sent(client, LINE)).toEqual([
      { subproject_id: COMMAND, lock_version: 3 },
      { subproject_id: COMMAND, lock_version: 9 },
    ]);
  });

  it("stops at the first refusal of a selection of three lines, told for its line, the third left as it was [WF-PRJ-0050-A]", async () => {
    const refusal = {
      problem: example("estimate_line_subproject_has_actual_costs") as Problem & { status: 422 },
    };
    const client = serve({
      [LINE]: ["estimate_line_subproject_changed", refusal, "estimate_line_subproject_changed"],
    });
    render(estimateGrid(threeLines()));
    await select(THREE[0], THREE[2]);
    const menu = await openSubmenu(THREE[0], "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-ESS — Essais et mise en service" }),
    );
    const second = estimate.items[THREE[1]]?.row_number ?? 0;
    expect(await screen.findByRole("alert")).toHaveTextContent(
      `Refusé à la ligne ${second.toString()},`,
    );
    expect(sent(client, LINE)).toHaveLength(2);
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("writes no line that already bears the sub-project chosen [WF-PRJ-0050-A]", async () => {
    // The first two lines bear « Poste de commande » already, the third bears none.
    const read = threeLines();
    const third = read.items[THREE[2]];
    if (third === undefined) {
      throw new Error("the example holds no such row");
    }
    third.lock_version = 5;
    const client = serve({ [LINE]: "estimate_line_subproject_changed" });
    render(estimateGrid(read));
    await select(THREE[0], THREE[2]);
    const menu = await openSubmenu(THREE[0], "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-CMD — Poste de commande" }),
    );
    await waitFor(() => {
      expect(sent(client, LINE)).toHaveLength(1);
    });
    expect(sent(client, LINE)).toEqual([{ subproject_id: COMMAND, lock_version: 5 }]);
    expect(await screen.findByText(/mis à jour\./)).toBeInTheDocument();
  });

  it("writes nothing for a line that already bears the sub-project chosen, alone [WF-PRJ-0050-A]", async () => {
    const client = serve({ [LINE]: "estimate_line_subproject_changed" });
    render(estimateGrid(threeLines()));
    const menu = await openSubmenu(THREE[0], "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-CMD — Poste de commande" }),
    );
    expect(sent(client, LINE)).toHaveLength(0);
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("keeps the menu open and sends nothing when a radio button is chosen while a write is under way [WF-PRJ-0050-A]", async () => {
    const hold = held();
    const client = serve({ [LINE]: "estimate_line_subproject_changed" }, hold.timing);
    render(estimateGrid());
    const first = await openSubmenu(REMINDER, "Sous-projet");
    await userEvent.click(
      within(first).getByRole("menuitemradio", { name: "SP-CMD — Poste de commande" }),
    );
    await waitFor(() => {
      expect(sent(client, LINE)).toHaveLength(1);
    });
    const again = await openSubmenu(REMINDER, "Sous-projet");
    expect(within(again).getByRole("menuitemradio", { name: "Aucun sous-projet" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await userEvent.click(
      within(again).getByRole("menuitemradio", { name: "SP-ESS — Essais et mise en service" }),
    );
    expect(screen.getByRole("menu", { name: "Sous-projet" })).toBeInTheDocument();
    expect(sent(client, LINE)).toHaveLength(1);
    hold.release();
    await screen.findByText(/mis à jour\./);
  });

  it("is reached and chosen from the keyboard alone, the focus coming back to the cell [WF-PRJ-0050-A]", async () => {
    const client = serve({ [LINE]: "estimate_line_subproject_changed" });
    render(estimateGrid());
    const cell = cellAt(REMINDER, "label");
    await userEvent.click(cell);
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
    for (let step = 0; step < 20; step += 1) {
      if (document.activeElement?.textContent === "Sous-projet") {
        break;
      }
      await userEvent.keyboard("{ArrowDown}");
    }
    expect(document.activeElement).toHaveTextContent("Sous-projet");
    expect(menu).toContainElement(document.activeElement as HTMLElement);
    await userEvent.keyboard("{ArrowRight}");
    await screen.findByRole("menu", { name: "Sous-projet" });
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    expect(document.activeElement).toHaveTextContent("Essais et mise en service");
    await userEvent.keyboard(" ");
    await waitFor(() => {
      expect(sent(client, LINE)).toHaveLength(1);
    });
    expect(sent(client, LINE)).toEqual([{ subproject_id: TESTS, lock_version: 1 }]);
    await screen.findByText(/mis à jour\./);
    await userEvent.keyboard("{Escape}{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("menu")).toBeNull();
    });
    await waitFor(() => {
      expect(cell).toHaveFocus();
    });
  });

  it("breaks no rule of accessibility in the submenu « Sous-projet » [WF-PRJ-0050-A]", async () => {
    serve();
    render(estimateGrid());
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    await expectAccessible(menu);
  });

  it("starts with the column « Sous-projet » hidden in the estimate, read only once shown [WF-PRJ-0050-A]", async () => {
    serve({ "PATCH /me/preferences": "preferences" });
    const view = render(estimateGrid(estimate, true, null));
    expect(screen.queryByRole("columnheader", { name: "Sous-projet" })).toBeNull();
    view.unmount();
    render(estimateGrid());
    expect(screen.getByRole("columnheader", { name: "Sous-projet" })).toBeInTheDocument();
    expect(cellAt(REMINDER, "subproject")).toHaveAttribute("aria-readonly", "true");
    await act(async () => {
      await Promise.resolve();
    });
  });
});

describe("the submenu « Sous-projet » of a line of the remaining to commit", () => {
  it("carries a line to a sub-project from the remaining to commit, once the project is in progress [WF-PRJ-0050-A] [WF-RAE-0040-A]", async () => {
    // Une ligne ajoutée après la référence peut y être portée à un sous-projet.
    const client = serve({ [LINE]: "estimate_line_subproject_changed" });
    render(remainingGrid());
    expect(screen.getByRole("columnheader", { name: "Sous-projet" })).toBeInTheDocument();
    expect(cellAt(REMINDER, "subproject")).toHaveAttribute("aria-readonly", "true");
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-CMD — Poste de commande" }),
    );
    await waitFor(() => {
      expect(sent(client, LINE)).toHaveLength(1);
    });
    expect(sent(client, LINE)).toEqual([{ subproject_id: COMMAND, lock_version: 1 }]);
  });

  it("shows the line answered in place of the line read, in the column of the sub-project [WF-PRJ-0050-A] [WF-RAE-0040-A]", async () => {
    // The line the example of the answer is about, « Mise en service sur site », carried from
    // « Poste de commande » to « Essais et mise en service ».
    const answered = (example("estimate_line_subproject_changed") as NodesWritten).nodes[0];
    const read = structuredClone(estimate);
    const line = read.items[REMINDER];
    if (answered === undefined || !line?.estimate_line) {
      throw new Error("the example holds no such line");
    }
    line.node_id = answered.node_id;
    line.estimate_line.subproject_id = COMMAND;
    line.estimate_line.subproject_label = "Poste de commande";
    serve({ [LINE]: "estimate_line_subproject_changed" });
    render(
      intl(
        <RemainingGrid
          nodes={read}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{ progress: ["started"] }}
          editable
          subprojects={subprojects}
          query={NO_QUERY}
          preferences={SHOWN}
        />,
      ),
    );
    expect(cellAt(REMINDER, "subproject")).toHaveTextContent("Poste de commande");
    const menu = await openSubmenu(REMINDER, "Sous-projet");
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: "SP-ESS — Essais et mise en service" }),
    );
    await waitFor(() => {
      expect(cellAt(REMINDER, "subproject")).toHaveTextContent("Essais et mise en service");
    });
  });

  it("offers no submenu without the sub-projects of the project [WF-PRJ-0050-A]", async () => {
    serve();
    render(remainingGrid(null));
    const menu = await openMenu(REMINDER);
    expect(within(menu).queryByRole("menuitem", { name: "Sous-projet" })).toBeNull();
  });
});
