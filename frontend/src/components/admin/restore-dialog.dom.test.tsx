// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The restoration of the platform from a backup of the list (WF-ADM-0160, EP-02/L43c, US-0440): its
 * confirmation, by the identifier typed, the date stated and sent, the refusals told in it; then the
 * screen of its maintenance in place of the page, which follows the task while the platform serves,
 * then the probe (`Restoration`, `maintenance.tsx`). The restoration from a deposit is
 * `backup-deposit.dom.test.tsx`.
 */
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { RESTORATION_POLL } from "@/components/system/maintenance";
import { expectAccessible } from "@/test/axe";
import { backupList, backups, bodies, dated, KEPT, LAST_NIGHT, row } from "@/test/backups";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  type Problem,
} from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

// The server of Next, as far as the restoration needs it: the fake back behind both clients — the
// probe asked without any token —, and the page read anew once a date is refused.
const server = vi.hoisted((): { client: ApiClient | undefined; open: ApiClient | undefined } => ({
  client: undefined,
  open: undefined,
}));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({
  serverClient: () => server.client,
  publicClient: () => server.open,
}));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams(),
}));

type Backup = components["schemas"]["Backup"];

const RESTORE = "POST /restores";
const TASK = "GET /tasks/{task_id}";
const HEALTH = "GET /health";

/** Serve the fake back, and the probe apart; give the back to read its calls. */
function serve(
  answers: FakeAnswers = {},
  probe: FakeAnswers = { [HEALTH]: "liveness" },
  timing: FakeTiming = {},
): FakeClient {
  const client = fakeClient(
    {
      [RESTORE]: { example: "task_restore_queued", status: 202 },
      [TASK]: "task_running",
      ...answers,
    },
    timing,
  );
  server.client = client;
  server.open = fakeClient(probe);
  return client;
}

/** Confirm the restoration of a backup of the list, its identifier typed. */
async function confirmRestore(backup: Backup) {
  await userEvent.click(
    within(row(backup)).getByRole("button", {
      name: `Restaurer la plateforme depuis la sauvegarde du ${dated(backup)}`,
    }),
  );
  const dialog = screen.getByRole("dialog", { name: "Restaurer la plateforme" });
  await userEvent.click(within(dialog).getByRole("textbox"));
  await userEvent.paste(backup.backup_id);
  await userEvent.click(within(dialog).getByRole("button", { name: "Restaurer" }));
}

/** Let the time of one read of the restoration go by, and the read be answered. */
async function tick() {
  await act(() => vi.advanceTimersByTimeAsync(RESTORATION_POLL));
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  router.refresh.mockClear();
});

describe("the restoration of the platform", () => {
  it("is confirmed by the identifier of the backup typed, in a dialog that states its date and that it cannot be undone, then gives way to the screen of its maintenance, never to the tracker [WF-ADM-0160-A]", async () => {
    const client = serve();
    // A session that may not start a backup restores all the same.
    render(backupList(backups.items, { startable: false }));
    const command = within(row(LAST_NIGHT)).getByRole("button", {
      name: `Restaurer la plateforme depuis la sauvegarde du ${dated(LAST_NIGHT)}`,
    });
    await userEvent.click(command);
    const dialog = screen.getByRole("dialog", { name: "Restaurer la plateforme" });
    // La confirmation nomme la date de la sauvegarde. Aucune restauration partielle n'est proposée.
    expect(dialog).toHaveAccessibleDescription(
      `La plateforme entière sera remplacée par la sauvegarde du ${dated(LAST_NIGHT)}, vérifiée\u00a0: tout ce qui a été saisi depuis sera perdu, sans retour possible. Les utilisateurs sont déconnectés pendant la restauration, qui sera inscrite au journal d’audit.`,
    );
    expect(within(dialog).queryByRole("checkbox")).toBeNull();
    expect(within(dialog).queryByRole("combobox")).toBeNull();
    const restore = within(dialog).getByRole("button", { name: "Restaurer" });
    expect(restore).toBeDisabled();
    const typed = within(dialog).getByRole("textbox", {
      name: "Pour confirmer, saisissez l’identifiant de la sauvegarde",
    });
    expect(typed).toHaveAccessibleDescription(`Identifiant\u00a0: ${LAST_NIGHT.backup_id}`);
    // Another backup's identifier does not confirm this one; its own does, whatever its case.
    await userEvent.click(typed);
    await userEvent.paste(KEPT.backup_id);
    expect(restore).toBeDisabled();
    await userEvent.clear(typed);
    await userEvent.paste(LAST_NIGHT.backup_id.toUpperCase());
    expect(restore).toBeEnabled();
    expect(client.calls.filter((call) => call.route === RESTORE)).toEqual([]);

    await userEvent.click(restore);
    const status = await screen.findByRole("status", {
      name: "Restauration de la plateforme en cours",
    });
    expect(status).toHaveTextContent("La restauration est en attente");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(bodies(client, RESTORE)).toEqual([
      {
        backup_id: LAST_NIGHT.backup_id,
        acknowledged_backup_taken_at: LAST_NIGHT.taken_at,
        confirmed: true,
      },
    ]);
    // The screen of the maintenance follows it, never the tracker: it restarts from the
    // confirmation alone.
    expect(within(tasksRegion()).queryAllByRole("listitem")).toEqual([]);
  });

  it("stays open while the restoration is asked, closed neither by Escape nor by « Annuler », and tells the refusal that answers it", async () => {
    let release = () => undefined as unknown;
    const answered = new Promise((settle) => {
      release = () => {
        settle(undefined);
      };
    });
    serve(
      {
        [RESTORE]: {
          problem: example("restore_during_backup_refused") as Problem & { status: 409 },
        },
      },
      {},
      { hold: (route) => (route === RESTORE ? answered : undefined) },
    );
    render(backupList());
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    const dialog = screen.getByRole("dialog", { name: "Restaurer la plateforme" });
    await userEvent.click(within(dialog).getByRole("textbox"));
    await userEvent.paste(KEPT.backup_id);
    await userEvent.click(within(dialog).getByRole("button", { name: "Restaurer" }));
    await userEvent.keyboard("{Escape}");
    const cancel = within(dialog).getByRole("button", { name: "Annuler" });
    expect(cancel).toBeDisabled();
    await userEvent.click(cancel);
    expect(screen.getByRole("dialog", { name: "Restaurer la plateforme" })).toBe(dialog);
    release();
    // Refused while a backup runs: the condition that lacks, as the command said it in the list.
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Condition non remplie : aucune sauvegarde en cours.",
    );
    await vi.waitFor(() => {
      expect(cancel).toBeEnabled();
    });
  });

  it("says at the date it states a date confirmed that is not that of the backup (400), the page read anew, and stays open [WF-ADM-0160-A]", async () => {
    const client = serve({
      [RESTORE]: {
        problem: example("restore_confirmation_mismatch") as Problem & { status: 400 },
      },
    });
    const { rerender } = render(backupList());
    await userEvent.click(
      within(row(LAST_NIGHT)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    );
    const dialog = screen.getByRole("dialog", { name: "Restaurer la plateforme" });
    await userEvent.click(within(dialog).getByRole("textbox"));
    await userEvent.paste(LAST_NIGHT.backup_id);
    await userEvent.click(within(dialog).getByRole("button", { name: "Restaurer" }));
    const said = await within(dialog).findByRole("alert");
    expect(said).toHaveTextContent("Cette opération demande une confirmation explicite.");
    // Said at the date, right after the sentence that states it; nothing else is told.
    expect(said.previousElementSibling).toHaveTextContent(
      `sauvegarde du ${dated(LAST_NIGHT)}, vérifiée`,
    );
    expect(within(dialog).getAllByRole("alert")).toHaveLength(1);
    // Said at the date, out of a notice, and kept in the history of the messages [WF-IHM-0080-A].
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        tone: "refusal",
        sentence: "Cette opération demande une confirmation explicite.",
      }),
    ]);
    expect(bodies(client, RESTORE)).toHaveLength(1);
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(within(dialog).getByRole("button", { name: "Annuler" })).toBeEnabled();

    // The page read anew gives the backup at another date: the dialog states the date read, and a
    // second confirmation sends it — never again the one captured at the press.
    const reread = { ...LAST_NIGHT, taken_at: "2026-06-03T01:00:30Z" };
    rerender(backupList([reread, ...backups.items.slice(1)]));
    expect(said.previousElementSibling).toHaveTextContent(
      `sauvegarde du ${dated(reread)}, vérifiée`,
    );
    await userEvent.click(within(dialog).getByRole("button", { name: "Restaurer" }));
    await vi.waitFor(() => {
      expect(bodies(client, RESTORE)).toHaveLength(2);
    });
    expect(bodies(client, RESTORE)[1]).toEqual({
      backup_id: LAST_NIGHT.backup_id,
      acknowledged_backup_taken_at: reread.taken_at,
      confirmed: true,
    });
  });

  it("breaks no rule of accessibility, open", async () => {
    serve();
    const { baseElement } = render(backupList());
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    expect(screen.getByRole("dialog", { name: "Restaurer la plateforme" })).toBeVisible();
    await expectAccessible(baseElement);
  });

  it("tells a restoration refused in the dialog, which stays open; Escape closes it asking nothing more", async () => {
    const client = serve({
      [RESTORE]: { problem: example("restore_unverified_refused") as Problem & { status: 409 } },
    });
    render(backupList());
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    const dialog = screen.getByRole("dialog", { name: "Restaurer la plateforme" });
    await userEvent.click(within(dialog).getByRole("textbox"));
    await userEvent.paste(` ${KEPT.backup_id} `);
    await userEvent.click(within(dialog).getByRole("button", { name: "Restaurer" }));
    expect(await within(dialog).findByRole("alert")).toBeVisible();
    await vi.waitFor(() => {
      expect(within(dialog).getByRole("button", { name: "Annuler" })).toBeEnabled();
    });
    expect(bodies(client, RESTORE)).toHaveLength(1);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(bodies(client, RESTORE)).toHaveLength(1);
    expect(within(tasksRegion()).queryByText(/^Restauration/)).toBeNull();
  });

  it.each([
    ["failed", "dont la vérification a échoué"],
    ["pending", "dont la vérification est en attente"],
  ] as const)(
    "says in its confirmation a backup whose verification is %s [WF-ADM-0160-A]",
    async (verification, said) => {
      serve();
      render(backupList([{ ...LAST_NIGHT, verification }]));
      await userEvent.click(
        within(row(LAST_NIGHT)).getByRole("button", {
          name: `Restaurer la plateforme depuis la sauvegarde du ${dated(LAST_NIGHT)}`,
        }),
      );
      expect(
        screen.getByRole("dialog", { name: "Restaurer la plateforme" }),
      ).toHaveAccessibleDescription(
        `La plateforme entière sera remplacée par la sauvegarde du ${dated(LAST_NIGHT)}, ${said}\u00a0: tout ce qui a été saisi depuis sera perdu, sans retour possible. Les utilisateurs sont déconnectés pendant la restauration, qui sera inscrite au journal d’audit.`,
      );
    },
  );

  it("replaces the screen by that of the restoration waiting, then of the maintenance, every user signed out, until it is done, then offers to sign in again — pendant une restauration, les utilisateurs sont déconnectés, et l’écran le dit", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const client = serve(
      { [TASK]: "task_running" },
      {
        [HEALTH]: [
          "liveness",
          "liveness",
          { status: 200, example: "liveness_maintenance" },
          "liveness",
        ],
      },
    );
    render(backupList());
    await confirmRestore(LAST_NIGHT);
    // The page gives way at once: the platform still serves, the task waits, no one is signed out.
    const status = await screen.findByRole("status", {
      name: "Restauration de la plateforme en cours",
    });
    expect(status).toHaveTextContent("La restauration est en attente");
    expect(status).toHaveTextContent("la plateforme va passer en maintenance");
    expect(status).not.toHaveTextContent("ont été déconnectés");
    expect(screen.queryByRole("button", { name: "Sauvegarder maintenant" })).toBeNull();
    await tick();
    expect(client.calls.filter(({ route }) => route === TASK)).toHaveLength(2);
    expect(
      screen.getByRole("status", { name: "Restauration de la plateforme en cours" }),
    ).not.toHaveTextContent("ont été déconnectés");
    await tick();
    // The probe says the maintenance: now every user is signed out.
    expect(
      screen.getByRole("status", { name: "Restauration de la plateforme en cours" }),
    ).toHaveTextContent("tous les utilisateurs ont été déconnectés");
    // Under maintenance, the task is no longer read: the probe alone says the end.
    expect(client.calls.filter(({ route }) => route === TASK)).toHaveLength(2);
    await tick();
    const done = screen.getByRole("status", { name: "Restauration de la plateforme en cours" });
    expect(done).toHaveTextContent("Restauration terminée");
    expect(within(done).getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      expect.stringContaining("/login"),
    );
  });

  it("gives the page back with the motive of a restoration refused before the maintenance", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    serve({ [TASK]: "task_restore_backup_newer_version" }, { [HEALTH]: "liveness" });
    render(backupList());
    await confirmRestore(LAST_NIGHT);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cette sauvegarde vient d’une version plus récente que celle installée",
    );
    expect(screen.getByRole("button", { name: "Sauvegarder maintenant" })).toBeVisible();
  });

  it("affirms nothing of a restoration whose task can no longer be read before any maintenance was seen, and offers to sign in again", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    serve(
      { [TASK]: { problem: { code: "SESSION_EXPIRED", status: 401 } } },
      { [HEALTH]: "liveness" },
    );
    render(backupList());
    await confirmRestore(LAST_NIGHT);
    const said = await screen.findByRole("status", { name: "Session terminée" });
    expect(said).toHaveTextContent("avant que l’issue de la restauration soit connue");
    expect(said).not.toHaveTextContent("Restauration terminée");
    expect(said).not.toHaveTextContent("restaurée");
    expect(within(said).getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      expect.stringContaining("/login"),
    );
  });

  it("says the maintenance of a restoration that closed the session between the probe and the read of its task, then its end — pendant une restauration, les utilisateurs sont déconnectés, et l’écran le dit", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    serve(
      { [TASK]: { problem: { code: "SESSION_EXPIRED", status: 401 } } },
      { [HEALTH]: ["liveness", { status: 200, example: "liveness_maintenance" }, "liveness"] },
    );
    render(backupList());
    await confirmRestore(LAST_NIGHT);
    const status = await screen.findByRole("status", {
      name: "Restauration de la plateforme en cours",
    });
    await vi.waitFor(() => {
      expect(status).toHaveTextContent("tous les utilisateurs ont été déconnectés");
    });
    expect(screen.queryByRole("status", { name: "Session terminée" })).toBeNull();
    await tick();
    expect(
      screen.getByRole("status", { name: "Restauration de la plateforme en cours" }),
    ).toHaveTextContent("Restauration terminée");
  });
});
