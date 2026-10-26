// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { forgetMessages } from "@/components/notices/message-history";
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

const IDENTIFIED = example("risk") as Risk;
const OCCURRED = example("risk_occurred_detail") as Risk;
// A counterfactual, from the risk of the contract: no marked revision cites it, so its deletion is
// listed available — the contract's risks are all cited or occurred.
const UNCITED: Risk = {
  ...IDENTIFIED,
  available_commands: IDENTIFIED.available_commands.map((offer) =>
    offer.command === "delete" ? { ...offer, is_available: true, missing_conditions: [] } : offer,
  ),
};

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

  it("tells the refusal of a risk a marked revision cites under its confirmation, which stays open [WF-RIS-0020-A]", async () => {
    serve({ [DELETE]: { problem: example("risk_delete_cited") as Problem & { status: 409 } } });
    render(detail(UNCITED));
    await userEvent.click(screen.getByRole("button", { name: "Supprimer le risque" }));
    const form = screen.getByRole("form", { name: "Supprimer le risque" });
    // Whether the confirmation was still busy in the commit that told the refusal: the request over,
    // never while it holds its cancellation (#1484).
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

  it("asks a confirmation, deletes the risk, and leaves its detail for the address without it", async () => {
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
  it("asks a confirmation that says what the declaration does, hands it to the worker, and follows it in the tasks", async () => {
    const client = serve({
      [OCCURRENCE]: { example: "task_occurrence_queued", status: 202 },
    });
    render(detail(IDENTIFIED));
    await userEvent.click(screen.getByRole("button", { name: "Déclarer survenu" }));
    const form = screen.getByRole("form", { name: "Déclarer survenu" });
    expect(form).toHaveTextContent(/sa ligne de provision est retirée du reste à engager/);
    expect(form).toHaveTextContent(/définitive/);
    // Abandoned, nothing is sent.
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(client.calls).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "Déclarer survenu" }));
    await userEvent.click(
      within(screen.getByRole("form", { name: "Déclarer survenu" })).getByRole("button", {
        name: "Déclarer le risque survenu",
      }),
    );
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.route).toBe(OCCURRENCE);
    expect(client.calls[0]?.path).toBe(
      `/projects/${PROJECT}/risks/${IDENTIFIED.risk_id}/occurrence`,
    );
    expect(client.calls[0]?.body).toEqual({ confirmed: true });
    expect(
      await screen.findAllByText(/La survenance de « Risque de reprise du câblage » est confiée/),
    ).not.toHaveLength(0);
    const tasks = tasksRegion();
    expect(
      await within(tasks).findByText("Survenance d’un risque « Risque de reprise du câblage »"),
    ).toBeVisible();
    expect(within(tasks).getByText("En attente")).toBeVisible();
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
