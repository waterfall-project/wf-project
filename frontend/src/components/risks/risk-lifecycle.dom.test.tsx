// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { forgetMessages } from "@/components/notices/message-history";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { atCommit } from "@/test/committed";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";
import { expectAccessible } from "@/test/axe";
import { tasksRegion } from "@/test/task-panel";

import { type Risk, RiskDetail } from "./risk-detail";

// The server of Next, as far as these commands need it: the fake back, the page read anew, and the
// router the screen leaves a risk deleted by.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
// The query of the address, which a test sets before it renders.
const address = vi.hoisted(() => ({ query: "risk=01926f3a-7c00-7000-8000-000000000751" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/r/risks",
  useSearchParams: () => new URLSearchParams(address.query),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const DELETE = "DELETE /projects/{project_id}/risks/{risk_id}";
const OCCURRENCE = "POST /projects/{project_id}/risks/{risk_id}/occurrence";
const OCCURRENCE_REPORT = "GET /projects/{project_id}/risks/{risk_id}/occurrence";

const IDENTIFIED = example("risk") as Risk;
const OCCURRED = example("risk_occurred_detail") as Risk;
// The risk no marked revision cites: its deletion is listed available, as an example of the
// contract shows it.
const UNCITED = example("risk_uncited") as Risk;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The detail of a risk, in French, in the shell that follows the tasks. */
function detail(risk: Risk) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <PendingAddress>
          <RiskDetail risk={risk} reviews={[]} projectId={PROJECT} options={undefined} />
        </PendingAddress>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  router.push.mockClear();
  router.refresh.mockClear();
  address.query = "risk=01926f3a-7c00-7000-8000-000000000751";
});

describe("« Supprimer le risque »", () => {
  it("is offered unavailable for a risk a marked revision cites, saying why, and deletes nothing [WF-RIS-0020-A]", async () => {
    const client = serve({});
    render(detail(IDENTIFIED));
    const command = screen.getByRole("button", { name: "Supprimer le risque" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(
      /^Condition non remplie\s: risque cité par aucune révision marquée\.$/,
    );
    await userEvent.click(command);
    expect(screen.queryByRole("form", { name: "Supprimer le risque" })).toBeNull();
    expect(client.calls).toHaveLength(0);
  });

  it("says the risk written since it was read under its confirmation, with the offer to read the page anew, and deletes nothing [WF-IHM-0110-A]", async () => {
    serve({ [DELETE]: { problem: example("risk_delete_stale") as Problem & { status: 412 } } });
    render(detail(UNCITED));
    await userEvent.click(screen.getByRole("button", { name: "Supprimer le risque" }));
    const form = screen.getByRole("form", { name: "Supprimer le risque" });
    await userEvent.click(within(form).getByRole("button", { name: "Supprimer le risque" }));
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("tells the refusal of a risk a marked revision cites under its confirmation, which stays open [WF-RIS-0020-A]", async () => {
    serve({ [DELETE]: { problem: example("risk_delete_cited") as Problem & { status: 409 } } });
    render(detail(UNCITED));
    await userEvent.click(screen.getByRole("button", { name: "Supprimer le risque" }));
    const form = screen.getByRole("form", { name: "Supprimer le risque" });
    // Whether the confirmation was still busy in the commit that told the refusal: the request
    // over, never while it holds its cancellation (#1484).
    const busyWhenTold = atCommit(
      form,
      () => within(form).queryByRole("alert") !== null,
      () => form.getAttribute("aria-busy"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Supprimer le risque" }));
    const refusal = await within(form).findByRole("alert");
    expect(busyWhenTold.stop()).toEqual(["false"]);
    expect(refusal).toHaveTextContent(/risque cité par aucune révision marquée/);
    expect(screen.getByRole("form", { name: "Supprimer le risque" })).toBe(form);
    expect(router.push).not.toHaveBeenCalled();
  });

  it("asks a confirmation, deletes the risk, and leaves its detail for the address without it [WF-IHM-0110-A]", async () => {
    const client = serve({ [DELETE]: { status: 204 } });
    render(detail(UNCITED));
    await userEvent.click(screen.getByRole("button", { name: "Supprimer le risque" }));
    const form = screen.getByRole("form", { name: "Supprimer le risque" });
    // Abandoned, nothing is sent.
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(client.calls).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "Supprimer le risque" }));
    await userEvent.click(
      within(screen.getByRole("form", { name: "Supprimer le risque" })).getByRole("button", {
        name: "Supprimer le risque",
      }),
    );
    await vi.waitFor(() => {
      expect(router.push).toHaveBeenCalledOnce();
    });
    expect(client.calls).toHaveLength(1);
    expect(client.calls[0]?.route).toBe(DELETE);
    // The counter the risk was read at, which a concurrent write would have moved (WF-IHM-0110).
    expect(client.calls[0]?.query.get("lock_version")).toBe(String(IDENTIFIED.lock_version));
    expect(client.calls[0]?.path).toBe(`/projects/${PROJECT}/risks/${IDENTIFIED.risk_id}`);
    expect(router.push).toHaveBeenCalledWith(
      "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/r/risks",
    );
    expect(
      screen.getAllByText("Risque « Risque de reprise du câblage » supprimé."),
    ).not.toHaveLength(0);
  });

  it("leaves the detail for the address that keeps the sort and drops the risk shown", async () => {
    address.query =
      "sort_by=provision_amount&sort_order=asc&risk=01926f3a-7c00-7000-8000-000000000751";
    serve({ [DELETE]: { status: 204 } });
    render(detail(UNCITED));
    await userEvent.click(screen.getByRole("button", { name: "Supprimer le risque" }));
    await userEvent.click(
      within(screen.getByRole("form", { name: "Supprimer le risque" })).getByRole("button", {
        name: "Supprimer le risque",
      }),
    );
    await vi.waitFor(() => {
      expect(router.push).toHaveBeenCalledOnce();
    });
    expect(router.push).toHaveBeenCalledWith(
      "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/r/risks?sort_by=provision_amount&sort_order=asc",
    );
  });
});

describe("« Déclarer survenu »", () => {
  /** Open the confirmation of the declaration, and wait for its report. */
  async function openDeclare() {
    await userEvent.click(screen.getByRole("button", { name: "Déclarer survenu" }));
    const form = screen.getByRole("form", { name: "Déclarer survenu" });
    await within(form).findByRole("table", { name: /écarts/i });
    return form;
  }

  it("presents the report in the marks, says the provision withdrawn, and confirms with the counters read [WF-RIS-0060-A] [WF-IHM-0110-A]", async () => {
    const client = serve({
      [OCCURRENCE_REPORT]: { example: "risk_occurrence_report", status: 200 },
      [OCCURRENCE]: { example: "task_occurrence_queued", status: 202 },
    });
    render(detail(IDENTIFIED));
    const form = await openDeclare();
    expect(form).toHaveTextContent(/sa ligne de provision est retirée du reste à engager/);
    expect(form).toHaveTextContent(/définitive/);
    // The report as the server read it: added, modified and removed, in the marks, and the amount.
    expect(form).toHaveTextContent(/500\s000,00 de provision en moins/);
    const table = within(form).getByRole("table", { name: /écarts/i });
    const markOf = (label: string) =>
      within(within(table).getByRole("row", { name: new RegExp(label) })).getAllByRole("cell")[0];
    expect(markOf("Diagnostic des défauts de câblage")).toHaveAccessibleName("Ajouté");
    expect(markOf("Câblage des armoires")).toHaveAccessibleName("Modifié");
    expect(markOf("Provision — risque de reprise du câblage")).toHaveAccessibleName("Retiré");
    expect(within(form).queryByRole("note")).toBeNull();
    await expectAccessible(form);
    // Abandoned, nothing is written: the report was a read.
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(client.calls.map((call) => call.route)).toEqual([OCCURRENCE_REPORT]);
    const again = await openDeclare();
    await userEvent.click(
      within(again).getByRole("button", { name: "Déclarer le risque survenu" }),
    );
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === OCCURRENCE)).toHaveLength(1);
    });
    // The counters of the report shown, and `creates_current_revision`, as read.
    const report = example("risk_occurrence_report") as {
      main_structure_lock_version: number;
      risk_lock_version: number;
      creates_current_revision: boolean;
    };
    const sent = client.calls.find((call) => call.route === OCCURRENCE);
    expect(sent?.path).toBe(`/projects/${PROJECT}/risks/${IDENTIFIED.risk_id}/occurrence`);
    expect(sent?.body).toEqual({
      confirmed: true,
      main_structure_lock_version: report.main_structure_lock_version,
      risk_lock_version: report.risk_lock_version,
      creates_current_revision: report.creates_current_revision,
    });
    // Handed to the worker, the task is followed in the tasks like a merge.
    expect(
      await screen.findAllByText(/La survenance de « Risque de reprise du câblage » est confiée/),
    ).not.toHaveLength(0);
    const tasks = tasksRegion();
    expect(
      await within(tasks).findByText("Survenance d’un risque « Risque de reprise du câblage »"),
    ).toBeVisible();
    expect(within(tasks).getByText("En attente")).toBeVisible();
  });

  it("tells the refusal of the report read, and does not offer the confirmation [WF-RIS-0060-A]", async () => {
    const client = serve({
      [OCCURRENCE_REPORT]: {
        problem: example("risk_occurrence_not_identified") as Problem & { status: 409 },
      },
    });
    render(detail(IDENTIFIED));
    await userEvent.click(screen.getByRole("button", { name: "Déclarer survenu" }));
    const form = screen.getByRole("form", { name: "Déclarer survenu" });
    expect(await within(form).findByRole("alert")).toBeVisible();
    const confirm = within(form).getByRole("button", { name: "Déclarer le risque survenu" });
    expect(confirm).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(confirm);
    expect(client.calls.map((call) => call.route)).toEqual([OCCURRENCE_REPORT]);
  });

  it("proposes to read the report again on a stale version (412), and shows it anew [WF-IHM-0110-A]", async () => {
    const client = serve({
      [OCCURRENCE_REPORT]: { example: "risk_occurrence_report", status: 200 },
      [OCCURRENCE]: {
        problem: example("risk_occurrence_report_stale") as Problem & { status: 412 },
      },
    });
    render(detail(IDENTIFIED));
    const form = await openDeclare();
    await userEvent.click(within(form).getByRole("button", { name: "Déclarer le risque survenu" }));
    const reread = await within(form).findByRole("button", { name: "Relire le compte rendu" });
    await userEvent.click(reread);
    await within(form).findByRole("table", { name: /écarts/i });
    expect(client.calls.filter((call) => call.route === OCCURRENCE_REPORT)).toHaveLength(2);
    expect(screen.getByRole("form", { name: "Déclarer survenu" })).toBe(form);
  });

  it("does not run a failed task again with the counters read before: the command is started anew from the screen [WF-RIS-0060-A]", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const client = serve({
      [OCCURRENCE_REPORT]: { example: "risk_occurrence_report", status: 200 },
      [OCCURRENCE]: { example: "task_occurrence_queued", status: 202 },
      "GET /tasks/{task_id}": ["task_failed"],
    });
    render(detail(IDENTIFIED));
    const form = await openDeclare();
    await userEvent.click(within(form).getByRole("button", { name: "Déclarer le risque survenu" }));
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    const tasks = tasksRegion();
    expect(within(tasks).getByText("Échouée")).toBeVisible();
    expect(within(tasks).queryByRole("button", { name: /Relancer/ })).toBeNull();
    expect(within(tasks).getByText(/repartez de l’écran de son objet/)).toBeVisible();
    // Started anew from the screen, the command reads the report again and shows it.
    await userEvent.keyboard("{Escape}");
    await openDeclare();
    expect(client.calls.filter((call) => call.route === OCCURRENCE_REPORT)).toHaveLength(2);
    expect(client.calls.filter((call) => call.route === OCCURRENCE)).toHaveLength(1);
  });

  it("leaves a risk occurred with no command of entry, each saying why [WF-RIS-0020-A]", () => {
    render(detail(OCCURRED));
    for (const name of ["Modifier", "Réexaminer", "Déclarer survenu", "Supprimer le risque"]) {
      expect(screen.getByRole("button", { name })).toHaveAttribute("aria-disabled", "true");
    }
    expect(screen.getByRole("button", { name: "Réexaminer" })).toHaveAccessibleDescription(
      /risque non survenu/,
    );
    expect(screen.getByRole("button", { name: "Déclarer survenu" })).toHaveAccessibleDescription(
      /risque identifié/,
    );
  });
});
