// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { onTask } from "@/components/grid/planning-target";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatDecimal } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { workloadDetail } from "./detail-rows";
import type { WorkloadPlan } from "./workload-chart";
import { WorkloadDetailGrid } from "./workload-detail";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: FakeClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/workload",
  useSearchParams: () => new URLSearchParams(),
}));

// The workload of the witness on the remaining of the revision under way: three roles, the third,
// « Monteur câbleur », loaded on eight months of the thirty-nine of the plan.
const WITNESS = example("workload") as WorkloadPlan;
const PLANNING = `/projects/p/revisions/${WITNESS.context.revision_id}/planning`;

/** The grid of the detail of a plan, in French, a task leading to the planning when `linked`. */
function grid(plan: WorkloadPlan, linked = true) {
  const detail = workloadDetail(plan, (task) =>
    linked ? onTask(PLANNING, task.node_id) : undefined,
  );
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <WorkloadDetailGrid
        detail={detail}
        revision={plan.context.revision_id}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row, by its index among the rows of the grid, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The plan reduced to its first role and to its first tasks: a grid a test reads whole. */
function firstRole(tasks: number): WorkloadPlan {
  const [role] = WITNESS.roles;
  if (role === undefined) {
    throw new Error("the witness has no role");
  }
  return { ...WITNESS, roles: [{ ...role, tasks: role.tasks.slice(0, tasks) }] };
}

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  // Laid out as a browser would: a window of rows in view.
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("the detail of the workload by role and by task", () => {
  it("is a tree grid from the role to the task, a column for each month of the plan, the totals of the plan at its foot [WF-DEV-0090-A]", () => {
    // Propre à l'US : l'écran du plan de charge présente ce détail sous l'histogramme, en grille
    // arborescente du rôle à la tâche, une colonne par mois, en lecture seule ; la grille ne somme rien.
    const plan = firstRole(3);
    render(grid(plan));
    const treegrid = screen.getByRole("treegrid", {
      name: "Détail du plan de charge par rôle et par tâche",
    });
    // The role, then its three tasks, in the order of the API.
    expect(treegrid).toHaveAttribute("aria-rowcount", "6");
    const headers = within(treegrid).getAllByRole("columnheader");
    expect(headers).toHaveLength(5 + plan.monthly_totals.length);
    expect(headers[5]).toHaveTextContent("juin 2026");
    expect(cell(0, "label")).toHaveTextContent("Ingénieur électricien");
    expect(cell(0, "label").closest("tr")).toHaveAttribute("aria-level", "1");
    expect(cell(0, "label").closest("tr")).toHaveAttribute("aria-expanded", "true");
    expect(cell(1, "label")).toHaveTextContent("Câblage des armoires");
    expect(cell(1, "label").closest("tr")).toHaveAttribute("aria-level", "2");
    expect(cell(1, "task_row")).toHaveTextContent("9");
    expect(cell(1, "start")).toHaveTextContent("04/05/2026");
    expect(cell(1, "finish")).toHaveTextContent("30/06/2026");
    expect(cell(1, "hours")).toHaveTextContent("12,5");
    // The part of the month the API gives, blank where it gives none — never a zero.
    expect(cell(1, "month_2026-06")).toHaveTextContent("12,5");
    expect(cell(1, "month_2026-07")).toBeEmptyDOMElement();
    // The role's month is the plan's, the hours of a role the API does not sum left blank.
    const [role] = plan.roles;
    const month = role?.months[0];
    expect(cell(0, `month_${month?.month ?? ""}`)).not.toBeEmptyDOMElement();
    expect(cell(0, "hours")).toBeEmptyDOMElement();
    // The totals of the months are those of the plan, never a sum of the rows shown.
    // The caption spans the columns without a figure, then each month in its order.
    const totals = [...treegrid.querySelectorAll("tfoot td")].map((each) => each.textContent);
    expect(totals).toEqual([
      "Total du plan",
      ...plan.monthly_totals.map(({ hours }) => formatDecimal(hours, "fr")),
    ]);
  });

  it("keeps the order of the API, a task starting in March before one starting in April [WF-DEV-0090-A]", () => {
    // Sous un rôle, une tâche qui débute en mars précède une tâche qui débute en avril, quelle que
    // soit leur place dans l'arbre du planning : the service orders them, the grid keeps its order.
    const plan = firstRole(3);
    const [role] = plan.roles;
    render(grid(plan));
    role?.tasks.forEach((task, at) => {
      expect(cell(at + 1, "label")).toHaveTextContent(task.label);
    });
  });

  it("leads from a task to its row in the planning grid of the revision the basis reads [WF-DEV-0090-A]", () => {
    // Depuis une tâche du détail, l'utilisateur atteint cette tâche dans la grille de planning, la
    // révision conservée.
    const plan = firstRole(2);
    const task = plan.roles[0]?.tasks[0];
    render(grid(plan));
    const link = within(cell(1, "label")).getByRole("link", { name: "Câblage des armoires" });
    expect(link).toHaveAttribute("href", `${PLANNING}?task=${task?.node_id ?? ""}`);
    // Out of the order of tabulation: the grid is one stop, Enter on the cell follows the link.
    expect(link).toHaveAttribute("tabindex", "-1");
    // A role leads nowhere.
    expect(within(cell(0, "label")).queryByRole("link")).toBeNull();
  });

  it("follows the link of a task on Enter, from its cell", async () => {
    render(grid(firstRole(2)));
    const link = within(cell(1, "label")).getByRole("link");
    const followed = vi.fn((event: Event) => {
      event.preventDefault();
    });
    link.addEventListener("click", followed);
    await userEvent.click(cell(1, "hours"));
    fireEvent.keyDown(cell(1, "hours"), { key: "ArrowLeft" });
    fireEvent.keyDown(cell(1, "start"), { key: "ArrowLeft" });
    fireEvent.keyDown(cell(1, "task_row"), { key: "ArrowLeft" });
    expect(cell(1, "label")).toHaveFocus();
    fireEvent.keyDown(cell(1, "label"), { key: "Enter" });
    expect(followed).toHaveBeenCalledTimes(1);
  });

  it("names a task without a link for a session that does not read the planning", () => {
    render(grid(firstRole(2), false));
    expect(cell(1, "label")).toHaveTextContent("Câblage des armoires");
    expect(within(cell(1, "label")).queryByRole("link")).toBeNull();
  });

  it("folds a role, its tasks taken out of the grid", async () => {
    render(grid(firstRole(3)));
    await userEvent.click(within(cell(0, "label")).getByRole("button", { name: "Plier" }));
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-rowcount", "3");
  });

  it("shows the roles alone when the API details no task", () => {
    // The service before US-2040/L2 (#3512): every role with `tasks: []`.
    const plan = { ...WITNESS, roles: WITNESS.roles.map((role) => ({ ...role, tasks: [] })) };
    render(grid(plan));
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-rowcount", "5");
    expect(cell(2, "label")).toHaveTextContent("Monteur câbleur");
  });

  it("is accessible", async () => {
    const { container } = render(grid(firstRole(2)));
    await expectAccessible(container);
  });
});
