// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the list of the backups (EP-02/L43c, EP-14/L42h): those each backup lists — its
 * marking, its download, its restoration —, the start of a backup, and the refusal of a download the
 * route came back with. The confirmation of a restoration is `restore-dialog.dom.test.tsx`, the
 * deposit of a backup of another installation `backup-deposit.dom.test.tsx`.
 */
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  announced,
  backupList,
  backups,
  bodies,
  dated,
  DURING_BACKUP,
  KEPT,
  LAST_NIGHT,
  PENDING,
  READ_ALONE,
  row,
} from "@/test/backups";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  type Problem,
} from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

import { readDownloadRefusal } from "./backup-address";

// The server of Next, as far as the commands need it: the fake back, and the page read anew once a
// backup is marked.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams(),
}));

const START = "POST /backups";
const RETAIN = "PATCH /backups/{backup_id}";
const TASK = "GET /tasks/{task_id}";

/** The refusal the route sends back for a session that may not download the backups. */
const REFUSED = "refusal=403%3APERMISSION_MISSING";

/** The download of a backup, refused for want of the permission, as the page reads it. */
function refusedDownload(backup: (typeof backups.items)[number]) {
  return {
    id: backup.backup_id,
    refusal: {
      kind: "refused",
      problem: { code: "PERMISSION_MISSING", status: 403 },
      conflictingObjectId: null,
    },
  } as const;
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(
    {
      [START]: { example: "task_backup_queued", status: 202 },
      [RETAIN]: "backup_retained",
      [TASK]: "task_running",
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  refresh.mockClear();
  router.refresh.mockClear();
});

describe("the commands of the backups", () => {
  it("offer on each backup the commands it lists, none to who reads them alone, and none that deletes [WF-ADM-0100-A] [WF-IHM-0090-A]", () => {
    serve();
    // Who reads the backups alone: no backup lists a command, and no command is deduced.
    const { rerender } = render(backupList(READ_ALONE, { startable: false }));
    expect(screen.queryByRole("button", { name: "Sauvegarder maintenant" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Ne plus c|C)onserver/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Télécharger/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Restaurer/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();

    // Each backup lists the marking that changes its state, its download and its restoration; who
    // may modify the backups starts one.
    rerender(backupList(backups.items));
    expect(screen.getByRole("button", { name: "Sauvegarder maintenant" })).toBeVisible();
    expect(
      within(row(LAST_NIGHT)).getByRole("button", {
        name: `Conserver la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    ).toBeVisible();
    expect(
      within(row(KEPT)).getByRole("button", {
        name: `Ne plus conserver la sauvegarde du ${dated(KEPT)}`,
      }),
    ).toBeVisible();
    expect(
      within(row(LAST_NIGHT)).getByRole("link", {
        name: `Télécharger la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    ).toHaveAttribute(
      "href",
      `/admin/backups/${LAST_NIGHT.backup_id}/content?from=%2Fadmin%2Fbackups`,
    );
    expect(
      within(row(KEPT)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(KEPT)}`,
      }),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();
  });

  it("present a command the backup lists unavailable, described by the condition it lacks, which a press says, asking nothing [WF-IHM-0090-A]", async () => {
    const client = serve();
    render(backupList([PENDING], { startable: false }));
    // Not yet verified: its marking is available, its download and its restoration are not.
    expect(
      within(row(PENDING)).getByRole("button", {
        name: `Conserver la sauvegarde du ${dated(PENDING)}`,
      }),
    ).not.toHaveAttribute("aria-disabled");
    const download = within(row(PENDING)).getByRole("button", {
      name: `Télécharger la sauvegarde du ${dated(PENDING)}`,
    });
    expect(download).toHaveAttribute("aria-disabled", "true");
    expect(download).toHaveAccessibleDescription(
      "Condition non remplie\u00a0: sauvegarde vérifiée.",
    );
    expect(screen.queryByRole("link", { name: /^Télécharger/ })).toBeNull();
    expect(
      within(row(PENDING)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(PENDING)}`,
      }),
    ).toHaveAccessibleDescription("Condition non remplie\u00a0: sauvegarde vérifiée.");
    await userEvent.click(download);
    expect(announced()).toContain(
      `Télécharger la sauvegarde du ${dated(PENDING)}\u00a0: indisponible. Condition non remplie\u00a0: sauvegarde vérifiée.`,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
  });

  it("present the restoration unavailable on every backup while a backup runs, the download available all the same [WF-IHM-0090-A]", () => {
    serve();
    render(backupList(DURING_BACKUP));
    expect(
      within(row(LAST_NIGHT)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    ).toHaveAccessibleDescription("Condition non remplie\u00a0: aucune sauvegarde en cours.");
    expect(
      within(row(LAST_NIGHT)).getByRole("link", {
        name: `Télécharger la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    ).toBeVisible();
  });

  it("break no rule of accessibility with a command unavailable", async () => {
    serve();
    const { container } = render(backupList([PENDING]));
    await expectAccessible(container);
  });

  it("start a backup now, its task handed over to the tracker with the command, which starts another if it fails [WF-ADM-0150-A]", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const client = serve({ [TASK]: "task_failed" });
    render(backupList());
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    await vi.waitFor(() => {
      expect(announced()).toContain(
        "Sauvegarde lancée\u00a0: son avancement se suit dans les tâches de fond.",
      );
    });
    expect(bodies(client, START)).toEqual([undefined]);
    const tasks = tasksRegion();
    expect(within(tasks).getByText("Sauvegarde")).toBeVisible();
    // Failed, the task offers to run its command again: another backup is started.
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await userEvent.click(within(tasks).getByRole("button", { name: /^Relancer/ }));
    await vi.waitFor(() => {
      expect(bodies(client, START)).toHaveLength(2);
    });
  });

  it("say above the list a backup the server refuses to start, nothing tracked", async () => {
    serve({ [START]: { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } } });
    render(backupList());
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(within(tasksRegion()).queryByText("Sauvegarde")).toBeNull();
  });

  it("say above the list a backup refused while another runs, naming the condition that lacks (409) [WF-IHM-0090-A]", async () => {
    serve({ [START]: { problem: example("backup_start_refused") as Problem & { status: 409 } } });
    render(backupList());
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : aucune sauvegarde en cours.",
    );
  });

  it("say above the list a marking refused while a restoration runs, naming the condition that lacks (409), the row left as read", async () => {
    serve({ [RETAIN]: { problem: example("backup_retain_refused") as Problem & { status: 409 } } });
    render(backupList());
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Ne plus conserver la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Condition non remplie : aucune restauration en cours.",
    );
    expect(row(KEPT)).toHaveTextContent("Marquée à conserver");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("mark a backup to be kept, the backup shown as the server answered it while the page reads it as before", async () => {
    const client = serve();
    const { rerender } = render(backupList());
    await userEvent.click(
      within(row(LAST_NIGHT)).getByRole("button", {
        name: `Conserver la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    );
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(bodies(client, RETAIN)).toEqual([{ is_retained: true }]);
    expect(client.calls.find((call) => call.route === RETAIN)?.path).toBe(
      `/backups/${LAST_NIGHT.backup_id}`,
    );
    await vi.waitFor(() => {
      expect(announced()).toContain(
        `La sauvegarde du ${dated(LAST_NIGHT)} est marquée à conserver.`,
      );
    });
    expect(row(LAST_NIGHT)).toHaveTextContent("Marquée à conserver");
    // The page read anew, as the fake back serves it, keeps the answer: it reads the backup as before.
    rerender(backupList([...backups.items]));
    expect(
      within(row(LAST_NIGHT)).getByRole("button", {
        name: `Ne plus conserver la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    ).toBeVisible();
    // A reading that has changed the backup prevails: another marked it no longer meanwhile.
    rerender(backupList([{ ...LAST_NIGHT, is_retained: true }, ...backups.items.slice(1)]));
    rerender(backupList(backups.items));
    expect(row(LAST_NIGHT)).not.toHaveTextContent("Marquée à conserver");
  });

  it("mark a backup no longer to be kept, the rotation then free to delete it", async () => {
    const client = serve({ [RETAIN]: "backup_released" });
    render(backupList());
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Ne plus conserver la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    await vi.waitFor(() => {
      expect(announced()).toContain(
        `La sauvegarde du ${dated(KEPT)} n’est plus marquée à conserver.`,
      );
    });
    expect(bodies(client, RETAIN)).toEqual([{ is_retained: false }]);
    expect(row(KEPT)).not.toHaveTextContent("Marquée à conserver");
  });

  it("say above the list a marking refused, or answered for another backup, the row left as read", async () => {
    serve({ [RETAIN]: [{ problem: { code: "NOT_FOUND", status: 404 } }, "backup_retained"] });
    render(backupList());
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Ne plus conserver la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /^Introuvable.*vous n’y avez pas accès\./,
    );
    // The fake back answers the backup of last night: a failure of the service, told as such.
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Ne plus conserver la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    await vi.waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Erreur inattendue du service.");
    });
    expect(row(KEPT)).toHaveTextContent("Marquée à conserver");
    expect(row(LAST_NIGHT)).not.toHaveTextContent("Marquée à conserver");
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("say above the list the refusal of a download the browser came back with, naming the backup, the focus on it, and rid the address of it even dismissed at once", async () => {
    serve();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const replaced = vi.spyOn(window.history, "replaceState");
    window.history.pushState(
      null,
      "",
      `/admin/backups?refused_backup=${KEPT.backup_id}&${REFUSED}`,
    );
    render(backupList(READ_ALONE, { startable: false, refused: refusedDownload(KEPT) }));
    const told = screen.getByRole("group", {
      name: `Le téléchargement de la sauvegarde du ${dated(KEPT)} n’a pas pu se faire.`,
    });
    // Rendered with the page, a refusal is heard only once it takes the focus.
    expect(told).toHaveFocus();
    expect(within(told).getByRole("alert")).toHaveTextContent(
      /^Vous n’avez pas la permission nécessaire\./,
    );
    await userEvent.click(within(told).getByRole("button", { name: "Fermer l’avis" }));
    expect(screen.queryByRole("group", { name: /^Le téléchargement/ })).toBeNull();
    await act(() => vi.advanceTimersByTimeAsync(1_500));
    expect(replaced).toHaveBeenLastCalledWith(null, "", "/admin/backups");
  });

  it("say the refusal of the download of a backup the page does not hold without naming it", () => {
    serve();
    window.history.pushState(null, "", "/admin/backups");
    render(backupList(backups.items.slice(0, 7), { refused: refusedDownload(KEPT) }));
    expect(
      screen.getByRole("group", {
        name: "Le téléchargement d’une sauvegarde n’a pas pu se faire.",
      }),
    ).toHaveFocus();
  });

  it("name the condition a download was refused for, as the route carried it back from the API (409) [WF-IHM-0090-A]", () => {
    serve();
    window.history.pushState(null, "", "/admin/backups");
    // The address the route of the download sends the browser back to, as the page reads it.
    const refused = readDownloadRefusal(
      new URLSearchParams(
        `refused_backup=${PENDING.backup_id}&refusal=409%3ASTATE_FORBIDS_OPERATION%3Abackup_verified`,
      ),
    );
    if (refused === undefined) {
      throw new Error("the address names the backup and the refusal");
    }
    render(backupList([PENDING], { startable: false, refused }));
    const told = screen.getByRole("group", {
      name: `Le téléchargement de la sauvegarde du ${dated(PENDING)} n’a pas pu se faire.`,
    });
    expect(within(told).getByRole("alert")).toHaveTextContent(
      `L’état actuel ne permet pas cette opération. Condition non remplie : ${CATALOGUES.fr.enums.CommandCondition.backup_verified}.`,
    );
  });
});
