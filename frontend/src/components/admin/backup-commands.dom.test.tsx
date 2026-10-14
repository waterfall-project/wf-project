// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { TaskPanel, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { DownloadRefusal, StartBackup } from "./backup-commands";

// The server of Next, as far as the commands need it: the fake back behind its client.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn(), replace: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams("offset=50&download_refusal=404%3ANOT_FOUND"),
}));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The command of the screen of the backups, within the shell that follows the tasks. */
function open() {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TaskPanel />
        <main>
          <StartBackup />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  window.sessionStorage.clear();
  router.replace.mockClear();
});

describe("the backup asked from the screen", () => {
  it("gives the hand back at once, and hands its task over to the tracker [WF-ADM-0150-A]", async () => {
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
