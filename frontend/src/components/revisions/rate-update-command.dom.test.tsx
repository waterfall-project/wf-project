// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { refresh } from "next/cache";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient } from "@/api/client";
import type { Revision } from "@/components/context/read-only";
import { RevisionCommands } from "@/components/commands/object-commands";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ProjectContext } from "@/navigation/context";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient, held } from "@/test/fixtures";

// The server of Next, as far as the command needs it: the fake back behind serverClient, and the
// render of the page again once a write is answered.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn(), push: vi.fn(), replace: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const DRAFT = "01926f3a-7c00-7000-8000-000000000101";
const CONTEXT: ProjectContext = {
  projectId: PROJECT,
  revisionId: DRAFT,
  revisionInPath: true,
  parameters: new URLSearchParams(),
};
const PROPOSAL = "GET /projects/{project_id}/revisions/{revision_id}/rate-update";
const RATES = "POST /projects/{project_id}/revisions/{revision_id}/rate-update";
const COMMAND = "Appliquer la mise à jour des taux";

function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The commands of a revision, at the right of the title of the screen of the revisions. */
function show(revision: string) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <main>
        <RevisionCommands revision={example(revision) as Revision} context={CONTEXT} />
      </main>
    </NextIntlClientProvider>,
  );
}

function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

function reads(client: FakeClient): number {
  return client.calls.filter((call) => call.route === PROPOSAL).length;
}

beforeEach(() => {
  vi.mocked(refresh).mockClear();
  router.refresh.mockReset();
  server.client = undefined;
});

describe("the rate update, a command of the current revision (US-2370)", () => {
  it("is offered as the revision lists it, the proposal read only when the dialog opens [WF-REV-0060-A]", async () => {
    const client = serve({ [PROPOSAL]: { example: "rate_update", status: 200 } });
    show("revision_rate_update_offered");
    const command = screen.getByRole("button", { name: COMMAND });
    expect(command).toHaveAttribute("aria-haspopup", "dialog");
    expect(command).not.toHaveAttribute("aria-disabled");
    // Rendering the command reads nothing.
    expect(reads(client)).toBe(0);

    await userEvent.click(command);
    const dialog = await screen.findByRole("dialog", { name: COMMAND });
    expect(await within(dialog).findByText("Ingénierie électrique")).toBeVisible();
    expect(reads(client)).toBe(1);
    expect(client.calls[0]?.path).toBe(`/projects/${PROJECT}/revisions/${DRAFT}/rate-update`);
    expect(within(dialog).getAllByRole("checkbox")).toHaveLength(2);
    expect(dialog).toHaveTextContent("Taux proposé");
    await expectAccessible(dialog);
  });

  it("is presented unavailable, naming the condition the revision lists as lacking, and reads nothing [WF-IHM-0090-A]", async () => {
    // `revision` lists `apply_rate_update` lacking `rate_update_available`.
    const client = serve({});
    show("revision");
    const command = screen.getByRole("button", { name: COMMAND });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: une mise à jour des taux disponible.",
    );
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
  });

  it("presents what changes category by category, then applies the categories retained [WF-REV-0060-A]", async () => {
    const client = serve({
      [PROPOSAL]: { example: "rate_update", status: 200 },
      [RATES]: { example: "rate_update_applied", status: 200 },
    });
    show("revision_rate_update_offered");
    await userEvent.click(screen.getByRole("button", { name: COMMAND }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("Ingénierie électrique");

    // A category refused is left out of the update.
    await userEvent.click(within(dialog).getByRole("checkbox", { name: /Mise en service/ }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(bodies(client, RATES)).toEqual([
      { cost_category_ids: ["01926f3a-7c00-7000-8000-000000000402"], lock_version: 1 },
    ]);
    // The dialog closes, what it told stays under the command, and the screen is read again.
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(screen.getByText("Les taux d’1 catégorie sont mis à jour.")).toBeVisible();
    expect(screen.getByRole("button", { name: COMMAND })).toHaveFocus();
    expect(refresh).toHaveBeenCalled();
  });

  it("asks nothing while no category is retained [WF-REV-0060-A]", async () => {
    const client = serve({ [PROPOSAL]: { example: "rate_update", status: 200 } });
    show("revision_rate_update_offered");
    await userEvent.click(screen.getByRole("button", { name: COMMAND }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("Ingénierie électrique");
    for (const box of within(dialog).getAllByRole("checkbox")) {
      await userEvent.click(box);
    }
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Retenez au moins une catégorie.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(bodies(client, RATES)).toEqual([]);
  });

  it("says that no update is proposed when the reference has not changed, and offers none to apply [WF-REV-0060-A]", async () => {
    serve({ [PROPOSAL]: { example: "rate_update_none", status: 200 } });
    show("revision_rate_update_offered");
    await userEvent.click(screen.getByRole("button", { name: COMMAND }));
    const dialog = await screen.findByRole("dialog");
    expect(
      await within(dialog).findByText(/aucune mise à jour des taux n’est proposée/),
    ).toBeVisible();
    expect(within(dialog).queryByRole("button", { name: "Confirmer la mise à jour" })).toBeNull();
  });

  it("tells the refusal of a revision marked, naming the condition, and keeps the dialog [WF-REV-0060-A]", async () => {
    serve({
      [PROPOSAL]: { example: "rate_update", status: 200 },
      [RATES]: {
        problem: { ...(example("rate_update_revision_marked") as object), status: 409 as const },
      } as never,
    });
    show("revision_rate_update_offered");
    await userEvent.click(screen.getByRole("button", { name: COMMAND }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("Ingénierie électrique");
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas",
    );
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the version read is stale, offers to read the page anew, and reads it [WF-REV-0060-A]", async () => {
    const client = serve({
      [PROPOSAL]: { example: "rate_update", status: 200 },
      [RATES]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 5 } },
      },
    });
    show("revision_rate_update_offered");
    await userEvent.click(screen.getByRole("button", { name: COMMAND }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("Ingénierie électrique");
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(bodies(client, RATES)).toHaveLength(1);
    await userEvent.click(await within(dialog).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    // The dialog closes with the reload: the proposal read before the refusal is never confirmed
    // again; the command reads a new one when it opens anew.
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it("tells a proposal it cannot read, and applies nothing [WF-REV-0060-A]", async () => {
    const client = serve({
      [PROPOSAL]: {
        problem: { ...(example("rate_update_revision_marked") as object), status: 409 as const },
      } as never,
    });
    show("revision_rate_update_offered");
    await userEvent.click(screen.getByRole("button", { name: COMMAND }));
    expect(await screen.findByRole("alert")).toHaveTextContent("L’état actuel ne permet pas");
    expect(bodies(client, RATES)).toEqual([]);
  });

  // The dialog stays while the update is on its way, so that a refusal is told in it: no Vérif
  // of an exigence says it.
  it("holds its dialog while the update is written, then closes it with the answer", async () => {
    const wait = held();
    const client = fakeClient(
      {
        [PROPOSAL]: { example: "rate_update", status: 200 },
        [RATES]: { example: "rate_update_applied", status: 200 },
      },
      { hold: (route) => (route === RATES ? wait.until : undefined) },
    );
    server.client = client;
    show("revision_rate_update_offered");
    await userEvent.click(screen.getByRole("button", { name: COMMAND }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("Ingénierie électrique");
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirmer la mise à jour" }));
    expect(dialog).toHaveAttribute("aria-busy", "true");
    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("dialog")).toBeVisible();

    await act(async () => {
      wait.release();
      await wait.until;
    });
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });
});
