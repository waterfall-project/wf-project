// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { RESTORATION_POLL } from "@/components/system/maintenance";
import { TaskPanel, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { BackupDeposit, DownloadRefusal, RestoreBackup, StartBackup } from "./backup-commands";
import { Restoration } from "./restoration";

// The server of Next, as far as the commands need it: the fake back behind both clients.
const server = vi.hoisted((): { client: ApiClient | undefined; open: ApiClient | undefined } => ({
  client: undefined,
  open: undefined,
}));

vi.mock("@/api/server", () => ({
  serverClient: () => server.client,
  publicClient: () => server.open,
}));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn(), replace: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams("offset=50&download_refusal=404%3ANOT_FOUND"),
}));

const BACKUP = "01926f3a-7c00-7000-8000-000000000906";
const TAKEN_AT = "2026-06-02T01:00:00Z";
const RESTORE = "POST /restores";
const TASK = "GET /tasks/{task_id}";
const HEALTH = "GET /health";
const PART = "PUT /chunked-uploads/{chunked_upload_id}/parts/{part_number}";
const COMPLETION = "POST /chunked-uploads/{chunked_upload_id}/completion";

/** Serve the fake back, and the probe apart, without any token; give the back to read its calls. */
function serve(answers: FakeAnswers, probe: FakeAnswers = {}): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  server.open = fakeClient(probe);
  return client;
}

/** The screen of the backups, as far as the commands go, within the shell that follows the tasks. */
function open() {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TaskPanel />
        <main>
          <Restoration>
            <StartBackup />
            <RestoreBackup backupId={BACKUP} takenAt={TAKEN_AT} />
            <BackupDeposit />
          </Restoration>
        </main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** Let the time of one read of the restoration go by, and the read be answered. */
async function tick() {
  await act(() => vi.advanceTimersByTimeAsync(RESTORATION_POLL));
}

/** Ask the restoration of the backup of the list, and give the confirmation. */
async function askRestore() {
  await userEvent.click(screen.getByRole("button", { name: "Restaurer" }));
  return screen.getByRole("alertdialog", { name: "Restaurer la plateforme entière" });
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
  router.replace.mockClear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the backup asked from the screen", () => {
  it("gives the hand back as soon as the backup is queued, and hands its task over to the tracker [WF-ARC-0090-A]", async () => {
    const client = serve({ "POST /backups": { status: 202, example: "task_backup_queued" } });
    open();
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    expect(client.calls.map(({ route }) => route)).toEqual(["POST /backups"]);
    const tasks = screen.getByRole("region", { name: "Tâches de fond" });
    expect(within(tasks).getByText("Sauvegarde")).toBeVisible();
    expect(within(tasks).getByText("En attente")).toBeVisible();
  });

  it("tells its refusal under it", async () => {
    serve({ "POST /backups": { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    open();
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    expect(screen.getByRole("alert")).toBeVisible();
    const tasks = screen.getByRole("region", { name: "Tâches de fond" });
    expect(within(tasks).queryAllByRole("listitem")).toEqual([]);
  });
});

describe("the restoration of the platform", () => {
  it("asks a confirmation that names the date of the backup: la confirmation nomme la date de la sauvegarde [WF-ADM-0160-A]", async () => {
    const client = serve({});
    open();
    const dialog = await askRestore();
    const date = formatTimestamp(TAKEN_AT, "fr");
    expect(dialog).toHaveTextContent(`sera remplacée par la sauvegarde du ${date}`);
    expect(within(dialog).getAllByRole("time")[0]).toHaveAttribute("datetime", TAKEN_AT);
    expect(
      within(dialog).getByRole("button", { name: `Restaurer la sauvegarde du ${date}` }),
    ).toBeVisible();
    await userEvent.click(within(dialog).getByRole("button", { name: "Annuler" }));
    expect(client.calls).toEqual([]);
  });

  it("proposes the whole platform alone: aucune restauration partielle n’est proposée [WF-ADM-0160-A]", async () => {
    const client = serve({});
    open();
    const dialog = await askRestore();
    const date = formatTimestamp(TAKEN_AT, "fr");
    expect(dialog).toHaveTextContent(
      `La plateforme entière — projets, comptes, rôles et réglages — sera remplacée par la sauvegarde du ${date}`,
    );
    // Nothing to choose but to restore all of it, or nothing.
    expect(within(dialog).queryAllByRole("checkbox")).toEqual([]);
    expect(within(dialog).queryAllByRole("combobox")).toEqual([]);
    expect(
      within(dialog)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual(["Annuler", `Restaurer la sauvegarde du ${date}`]);
    await expectAccessible(dialog);
    await userEvent.click(within(dialog).getByRole("button", { name: "Annuler" }));
    expect(client.calls).toEqual([]);
  });

  it("replaces the screen by that of the maintenance, every user signed out, until it is done, then offers to sign in again — pendant une restauration, les utilisateurs sont déconnectés, et l’écran le dit", async () => {
    const client = serve(
      {
        [RESTORE]: { status: 202, example: "task_restore_queued" },
        [TASK]: "task_running",
      },
      {
        [HEALTH]: [
          "liveness",
          "liveness",
          { status: 200, example: "liveness_maintenance" },
          "liveness",
        ],
      },
    );
    open();
    const dialog = await askRestore();
    await userEvent.click(within(dialog).getByRole("button", { name: /^Restaurer la sauvegarde/ }));
    expect(client.calls.find(({ route }) => route === RESTORE)?.body).toEqual({
      backup_id: BACKUP,
      acknowledged_backup_taken_at: TAKEN_AT,
      confirmed: true,
    });
    // The page gives way at once: the platform still serves, the task waits.
    const status = screen.getByRole("status", { name: "Restauration de la plateforme en cours" });
    expect(status).toHaveTextContent("tous les utilisateurs ont été déconnectés");
    expect(screen.queryByRole("button", { name: "Sauvegarder maintenant" })).toBeNull();
    await tick();
    expect(client.calls.filter(({ route }) => route === TASK)).toHaveLength(2);
    await tick();
    expect(screen.getByRole("status")).toHaveTextContent("Restauration de la plateforme en cours");
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
    serve(
      {
        [RESTORE]: { status: 202, example: "task_restore_queued" },
        [TASK]: "task_restore_backup_newer_version",
      },
      { [HEALTH]: "liveness" },
    );
    open();
    const dialog = await askRestore();
    await userEvent.click(within(dialog).getByRole("button", { name: /^Restaurer la sauvegarde/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cette sauvegarde vient d’une version plus récente que celle installée",
    );
    expect(screen.getByRole("button", { name: "Sauvegarder maintenant" })).toBeVisible();
  });

  it("tells a confirmation the API refuses, and keeps the page", async () => {
    serve({
      [RESTORE]: { problem: { code: "CONFIRMATION_REQUIRED", status: 400 } },
    });
    open();
    const dialog = await askRestore();
    await userEvent.click(within(dialog).getByRole("button", { name: /^Restaurer la sauvegarde/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cette opération demande une confirmation explicite.",
    );
    expect(
      screen.queryByRole("status", { name: "Restauration de la plateforme en cours" }),
    ).toBeNull();
  });
});

describe("the deposit of a backup of another installation", () => {
  it("sends the archive in the parts the server cuts it into, then restores it at the date its manifest says [WF-ADM-0160-A]", async () => {
    const client = serve({
      "POST /chunked-uploads": { status: 201, example: "chunked_upload" },
      [PART]: { status: 200, example: "chunked_upload_part" },
      [COMPLETION]: { status: 201, example: "chunked_upload_completed" },
      [RESTORE]: { problem: { code: "CONFIRMATION_REQUIRED", status: 400 } },
    });
    open();
    const deposit = screen.getByRole("region", {
      name: "Restaurer une sauvegarde d’une autre installation",
    });
    const send = within(deposit).getByRole("button", { name: "Déposer" });
    expect(send).toBeDisabled();
    const archive = new File(["0123456789AB"], "waterfall-2026-06-02.tar");
    await userEvent.upload(within(deposit).getByLabelText("Archive de la sauvegarde"), archive);
    await userEvent.click(send);
    const date = formatTimestamp("2026-06-02T01:00:00Z", "fr");
    const restore = await within(deposit).findByRole("button", {
      name: "Restaurer cette sauvegarde",
    });
    expect(deposit).toHaveTextContent(`Sauvegarde du ${date} déposée : waterfall-2026-06-02.tar.`);
    expect(client.calls.map(({ path }) => path)).toEqual([
      "/chunked-uploads",
      "/chunked-uploads/01926f3a-7c00-7000-8000-000000000a02/parts/1",
      "/chunked-uploads/01926f3a-7c00-7000-8000-000000000a02/parts/2",
      "/chunked-uploads/01926f3a-7c00-7000-8000-000000000a02/parts/3",
      "/chunked-uploads/01926f3a-7c00-7000-8000-000000000a02/completion",
    ]);
    expect(client.calls[0]?.body).toEqual({
      filename: "waterfall-2026-06-02.tar",
      size_bytes: 12,
    });
    await userEvent.click(restore);
    const dialog = screen.getByRole("alertdialog", { name: "Restaurer la plateforme entière" });
    expect(dialog).toHaveTextContent(`sera remplacée par la sauvegarde du ${date}`);
    await userEvent.click(within(dialog).getByRole("button", { name: /^Restaurer la sauvegarde/ }));
    expect(client.calls.at(-1)?.body).toEqual({
      external_backup_upload_id: "01926f3a-7c00-7000-8000-000000000a03",
      acknowledged_backup_taken_at: "2026-06-02T01:00:00Z",
      confirmed: true,
    });
  });

  it("stops at the first refusal, and offers no confirmation of an archive whose date does not read [WF-ADM-0160-A]", async () => {
    serve({
      "POST /chunked-uploads": { status: 201, example: "chunked_upload" },
      [PART]: { status: 200, example: "chunked_upload_part" },
      [COMPLETION]: { problem: { code: "FILE_FORMAT_UNREADABLE", status: 422 } },
    });
    open();
    await userEvent.upload(
      screen.getByLabelText("Archive de la sauvegarde"),
      new File(["x"], "notes.txt"),
    );
    await userEvent.click(screen.getByRole("button", { name: "Déposer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le format du fichier est illisible.",
    );
    expect(screen.queryByRole("button", { name: "Restaurer cette sauvegarde" })).toBeNull();
  });
});

describe("the refusal of a download", () => {
  it("is told until dismissed, which takes it from the address and keeps the page of the list", async () => {
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <DownloadRefusal
          refusal={{
            kind: "refused",
            problem: { code: "NOT_FOUND", status: 404 },
            conflictingObjectId: null,
          }}
        />
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Introuvable");
    await userEvent.click(screen.getByRole("button", { name: "Fermer l’avis" }));
    expect(router.replace).toHaveBeenCalledWith("/admin/backups?offset=50", { scroll: false });
  });
});
