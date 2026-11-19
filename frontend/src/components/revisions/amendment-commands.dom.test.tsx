// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { findOffer } from "@/components/commands/offer";
import { listedStructure } from "@/components/context/structure";
import type { Revision } from "@/components/context/read-only";
import { TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { AmendmentCommands } from "./amendment-commands";

// The server of Next, as far as these commands need it: the fake back behind serverClient, and the
// router that leads the screen.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn(), push: vi.fn(), replace: vi.fn() }));

const PATHNAME = "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/r/planning";
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams("structure=01926f3a-7c00-7000-8000-000000000203"),
}));

type CostStructure = components["schemas"]["CostStructure"];
type Command = components["schemas"]["StructureCommand"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const DELETE = "DELETE /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}";
const REBASE_REPORT =
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rebase";
const REBASE =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rebase";
const MERGE_REPORT =
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge";

type Problem = components["schemas"]["Problem"];

/** The refusal of a write sent with a counter gone stale, as an example of the contract gives it. */
function stale(name: string) {
  return { problem: { ...(example(name) as Problem), status: 412 as const } };
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The amendment of an example of the structures of a revision, as the screen reads it. */
function amendment(name: string): CostStructure {
  const found = (example(name) as CostStructure[]).find(
    (structure) => structure.kind === "amendment" && !structure.is_merged,
  );
  if (found === undefined) {
    throw new Error(`${name} lists no amendment not merged`);
  }
  return found;
}

/** The commands of the amendment, as the screen of its grid offers them. */
function commands(structure: CostStructure, available: readonly Command[], merge = true) {
  const revision = example("revision") as Revision;
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <main>
          <AmendmentCommands
            structure={listedStructure(structure)}
            version={structure.lock_version}
            commands={new Set(available)}
            mergeOffer={
              merge ? findOffer(revision.available_commands, "merge_structure") : undefined
            }
            revision={{ projectId: PROJECT, revisionId: REVISION }}
          />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  router.refresh.mockClear();
  router.replace.mockClear();
});

describe("the abandon of an amendment", () => {
  it("is offered where the structure lists `delete` available, and says on its help what it does [US-2640]", async () => {
    const structure = amendment("structures");
    commands(structure, ["edit_planning", "delete"]);
    const command = screen.getByRole("button", { name: "Abandonner l’avenant" });
    await userEvent.hover(command);
    expect(await screen.findByRole("tooltip")).toHaveTextContent("un différentiel non fusionné");
  });

  it("is not offered where the structure does not list `delete` available [US-2640]", () => {
    commands(amendment("structures"), ["edit_planning"]);
    expect(screen.queryByRole("button", { name: "Abandonner l’avenant" })).toBeNull();
  });

  it("asks for a confirmation, sends the counter read, tells it done and leads back to the main structure [US-2640] [WF-IHM-0110-A]", async () => {
    const client = serve({ [DELETE]: { status: 204 } });
    const structure = amendment("structures");
    commands(structure, ["delete"]);
    await userEvent.click(screen.getByRole("button", { name: "Abandonner l’avenant" }));
    const form = screen.getByRole("form", { name: "Abandonner l’avenant" });
    expect(form).toHaveTextContent("irréversible");
    expect(client.calls).toHaveLength(0);
    await expectAccessible(form);
    await userEvent.click(within(form).getByRole("button", { name: /Confirmer l’abandon/ }));
    const call = client.calls.find((one) => one.route === DELETE);
    expect(call?.path).toBe(
      `/projects/${PROJECT}/revisions/${REVISION}/structures/${structure.structure_id}`,
    );
    expect(call?.query.get("lock_version")).toBe(String(structure.lock_version));
    await waitFor(() => {
      expect(router.replace).toHaveBeenCalledWith(PATHNAME);
    });
  });

  it("tells a counter gone stale (412) and leads nowhere, the screen to be read anew [US-2640] [WF-IHM-0110-A]", async () => {
    serve({ [DELETE]: stale("structure_delete_stale") });
    commands(amendment("structures"), ["delete"]);
    await userEvent.click(screen.getByRole("button", { name: "Abandonner l’avenant" }));
    await userEvent.click(screen.getByRole("button", { name: /Confirmer l’abandon/ }));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(router.replace).not.toHaveBeenCalled();
  });
});

describe("an amendment in arrears", () => {
  it("says it is late, offers its update, and does not offer the merge [US-2640]", () => {
    const late = amendment("structures_amendments");
    expect(late.is_up_to_date).toBe(false);
    commands(late, ["edit_planning", "rebase", "delete"]);
    expect(screen.getByRole("note")).toHaveTextContent("est en retard");
    expect(screen.getByRole("button", { name: "Mettre à jour l’avenant" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Contractualiser l’avenant" })).toBeNull();
  });

  it("offers the merge, and neither the note nor the update, on an amendment up to date [US-2640]", () => {
    const current = amendment("structures");
    expect(current.is_up_to_date).toBe(true);
    commands(current, ["edit_planning", "delete"]);
    expect(screen.queryByRole("note")).toBeNull();
    expect(screen.queryByRole("button", { name: "Mettre à jour l’avenant" })).toBeNull();
    expect(screen.getByRole("button", { name: "Contractualiser l’avenant" })).toBeVisible();
  });

  it("presents the report of the update — carried, kept with its fields — and confirms with the two counters read [US-2640]", async () => {
    const client = serve({
      [REBASE_REPORT]: "structure_rebase_report",
      [REBASE]: "structure_rebased",
    });
    commands(amendment("structures_amendments"), ["rebase"]);
    await userEvent.click(screen.getByRole("button", { name: "Mettre à jour l’avenant" }));
    const form = screen.getByRole("form", { name: "Mettre à jour l’avenant" });
    const counts = await within(form).findByRole("list", { name: "Écarts par changement" });
    expect(counts).toHaveTextContent("1 reportée comme ajout");
    expect(counts).toHaveTextContent("2 reportées comme modifications");
    expect(counts).toHaveTextContent("1 reportée comme retrait");
    expect(counts).toHaveTextContent("1 gardée par l’avenant");
    const table = within(form).getByRole("table", { name: /écarts/i });
    expect(within(table).getByText("Réception provisoire sur site")).toBeVisible();
    // What the amendment keeps, with the field it keeps.
    const kept = within(table).getByRole("row", { name: /Mise en service sur site/ });
    expect(kept).toHaveTextContent("Conservé");
    expect(within(form).queryByRole("alert")).toBeNull();
    await expectAccessible(form);

    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(client.calls.filter((call) => call.route === REBASE).map((call) => call.body)).toEqual([
      { confirmed: true, main_structure_lock_version: 6, structure_lock_version: 2 },
    ]);
    expect(await screen.findByText(/est à jour\./)).toBeVisible();
  });

  it("refuses the confirmation while a motive of the report refuses the update, and sends nothing [US-2640]", async () => {
    const client = serve({ [REBASE_REPORT]: "structure_rebase_report_refused" });
    commands(amendment("structures_amendments"), ["rebase"]);
    await userEvent.click(screen.getByRole("button", { name: "Mettre à jour l’avenant" }));
    const form = screen.getByRole("form", { name: "Mettre à jour l’avenant" });
    expect(await within(form).findByRole("alert")).toHaveTextContent("motif refuse la mise à jour");
    const confirm = within(form).getByRole("button", { name: "Confirmer la mise à jour" });
    expect(confirm).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(confirm);
    expect(client.calls.filter((call) => call.route === REBASE)).toEqual([]);
  });

  it("offers to read the report anew when the confirmation went stale (412) [US-2640] [WF-IHM-0110-A]", async () => {
    const client = serve({
      [REBASE_REPORT]: ["structure_rebase_report", "structure_rebase_report"],
      [REBASE]: stale("structure_rebase_stale"),
    });
    commands(amendment("structures_amendments"), ["rebase"]);
    await userEvent.click(screen.getByRole("button", { name: "Mettre à jour l’avenant" }));
    const form = screen.getByRole("form", { name: "Mettre à jour l’avenant" });
    await within(form).findByRole("list", { name: "Écarts par changement" });
    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la mise à jour" }));
    await userEvent.click(
      await within(form).findByRole("button", { name: "Relire le compte rendu" }),
    );
    await waitFor(() => {
      expect(client.calls.filter((call) => call.route === REBASE_REPORT)).toHaveLength(2);
    });
  });

  it("does not read the merge report of a late amendment: the command is not there [US-2640]", () => {
    const client = serve({ [MERGE_REPORT]: "structure_merge_report" });
    commands(amendment("structures_amendments"), ["rebase"]);
    expect(client.calls).toEqual([]);
  });
});
