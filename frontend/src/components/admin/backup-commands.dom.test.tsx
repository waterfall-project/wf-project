// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TaskTracker } from "@/components/tasks/task-tracker";
import type { ResultRefusal } from "@/components/tasks/result-refusal";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  type Problem,
} from "@/test/fixtures";

import { NEWEST_FIRST, readBackupFilters, readDownloadRefusal } from "./backup-address";
import { BackupList } from "./platform-lists";

// The server of Next, as far as the commands need it: the fake back, the page read anew once a
// backup is marked — or once a restoration is refused for its date —, and the address the list reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const shown = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams(shown.search),
}));

type Backup = components["schemas"]["Backup"];

/** A refusal of the contract, by the example that describes it, on the status it declares. */
function refusal<Status extends number>(name: string, status: Status) {
  return { problem: { ...(example(name) as Problem), status } };
}

const START = "POST /backups";
const RETAIN = "PATCH /backups/{backup_id}";
const RESTORE = "POST /restores";
const TASK = "GET /tasks/{task_id}";

const backups = example("backups") as {
  items: Backup[];
  meta: components["schemas"]["PaginationMeta"];
};
/** A backup of the witness, by its place in the list. */
function backupAt(at: number): Backup {
  const found = backups.items[at];
  if (found === undefined) {
    throw new Error(`the witness lists a backup at ${String(at)}`);
  }
  return found;
}

/** The backup of last night, the first of the list, and the one kept since January, the last. */
const LAST_NIGHT = backupAt(0);
const KEPT = backupAt(7);
/** The backup taken by hand today, read before its verification: neither downloads nor restores. */
const PENDING = example("backup_pending") as Backup;
/** The backups read by a session that may neither modify them nor restore the platform. */
const READ_ALONE = (example("backups_reader") as { items: Backup[] }).items;
/** The backups read while a backup runs: none restores. */
const DURING_BACKUP = (example("backups_during_backup") as { items: Backup[] }).items;
/** A date of a backup as the browser writes it, in the time zone of the workstation. */
const dated = (backup: Backup) => formatTimestamp(backup.taken_at, "fr");

/** The refusal the route sends back for a session that may not download the backups. */
const REFUSED = "refusal=403%3APERMISSION_MISSING";

/** The download of a backup, refused for want of the permission, as the page reads it. */
function refusedDownload(backup: Backup) {
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
      [RESTORE]: { example: "task_restore_queued", status: 202 },
      [TASK]: "task_running",
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

/**
 * The list of the backups, within the shell that follows the tasks, as the page renders it: the rows
 * given, for a session that may start a backup unless said otherwise.
 */
function list(
  rows: readonly Backup[] = backups.items,
  options: {
    readonly startable?: boolean;
    readonly refused?: { readonly id: string; readonly refusal: ResultRefusal };
    readonly page?: ListPage;
  } = {},
): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TaskPanel />
        <PendingAddress>
          <BackupList
            read={{ kind: "read", items: rows, page: options.page ?? backups.meta }}
            filters={readBackupFilters(new URLSearchParams(shown.search))}
            query={{ sort: NEWEST_FIRST, search: undefined }}
            preferences={undefined}
            startable={options.startable ?? true}
            refused={options.refused}
          />
        </PendingAddress>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** The grid of the backups. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Sauvegardes" });
}

/** The row of a backup in the grid, found by its date. */
function row(backup: Backup): HTMLElement {
  const found = within(grid())
    .getAllByRole("row")
    .find((each) => each.querySelector(`time[datetime="${backup.taken_at}"]`) !== null);
  if (found === undefined) {
    throw new Error(`no row of the backup of ${backup.taken_at}`);
  }
  return found;
}

/** What the regions of the list announce. */
function announced(): (string | null)[] {
  return screen.getAllByRole("status").map((status) => status.textContent);
}

/** The bodies of the calls made of an operation. */
function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
  shown.search = "";
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
    const { rerender } = render(list(READ_ALONE, { startable: false }));
    expect(screen.queryByRole("button", { name: "Sauvegarder maintenant" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Ne plus c|C)onserver/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Télécharger/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Restaurer/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();

    // Each backup lists the marking that changes its state, its download and its restoration; who
    // may modify the backups starts one.
    rerender(list(backups.items));
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
    render(list([PENDING], { startable: false }));
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
    render(list(DURING_BACKUP));
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
    const { container } = render(list([PENDING]));
    await expectAccessible(container);
  });

  it("start a backup now, its task handed over to the tracker with the command, which starts another if it fails [WF-ADM-0150-A]", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const client = serve({ [TASK]: "task_failed" });
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    await vi.waitFor(() => {
      expect(announced()).toContain(
        "Sauvegarde lancée\u00a0: son avancement se suit dans les tâches de fond.",
      );
    });
    expect(bodies(client, START)).toEqual([undefined]);
    const tasks = screen.getByRole("region", { name: "Tâches de fond" });
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
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(
      within(screen.getByRole("region", { name: "Tâches de fond" })).queryByText("Sauvegarde"),
    ).toBeNull();
  });

  it("say above the list a backup refused while another runs, naming the condition that lacks (409) [WF-IHM-0090-A]", async () => {
    serve({ [START]: refusal("backup_start_refused", 409) });
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : aucune sauvegarde en cours.",
    );
  });

  it("say above the list a marking refused while a restoration runs, naming the condition that lacks (409), the row left as read", async () => {
    serve({ [RETAIN]: refusal("backup_retain_refused", 409) });
    render(list());
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
    const { rerender } = render(list());
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
    rerender(list([...backups.items]));
    expect(
      within(row(LAST_NIGHT)).getByRole("button", {
        name: `Ne plus conserver la sauvegarde du ${dated(LAST_NIGHT)}`,
      }),
    ).toBeVisible();
    // A reading that has changed the backup prevails: another marked it no longer meanwhile.
    rerender(list([{ ...LAST_NIGHT, is_retained: true }, ...backups.items.slice(1)]));
    rerender(list(backups.items));
    expect(row(LAST_NIGHT)).not.toHaveTextContent("Marquée à conserver");
  });

  it("mark a backup no longer to be kept, the rotation then free to delete it", async () => {
    const client = serve({ [RETAIN]: "backup_released" });
    render(list());
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
    render(list());
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
    render(list(READ_ALONE, { startable: false, refused: refusedDownload(KEPT) }));
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
    render(list(backups.items.slice(0, 7), { refused: refusedDownload(KEPT) }));
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
    render(list([PENDING], { startable: false, refused }));
    const told = screen.getByRole("group", {
      name: `Le téléchargement de la sauvegarde du ${dated(PENDING)} n’a pas pu se faire.`,
    });
    expect(within(told).getByRole("alert")).toHaveTextContent(
      `L’état actuel ne permet pas cette opération. Condition non remplie : ${CATALOGUES.fr.enums.CommandCondition.backup_verified}.`,
    );
  });
});

describe("the restoration of the platform", () => {
  it("is confirmed by the identifier of the backup typed, in a dialog that states its date and that it cannot be undone, and is never started again from the tracker [WF-ADM-0160-A]", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const client = serve({ [TASK]: "task_failed" });
    // A session that may not start a backup hears it all the same.
    render(list(backups.items, { startable: false }));
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
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(bodies(client, RESTORE)).toEqual([
      {
        backup_id: LAST_NIGHT.backup_id,
        acknowledged_backup_taken_at: LAST_NIGHT.taken_at,
        confirmed: true,
      },
    ]);
    expect(announced()).toContain(
      `Restauration depuis la sauvegarde du ${dated(LAST_NIGHT)} lancée\u00a0: son avancement se suit dans les tâches de fond.`,
    );
    // Followed as any task, named by the date of the backup; never started again but from here.
    const tasks = screen.getByRole("region", { name: "Tâches de fond" });
    expect(
      within(tasks).getByRole("progressbar", {
        name: `Restauration «\u00a0${dated(LAST_NIGHT)}\u00a0»`,
      }),
    ).toBeVisible();
    expect(command.closest("td")).toHaveFocus();
    // Failed, a restoration offers nothing to run it again: it restarts from the confirmation alone.
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    expect(within(tasks).getByRole("log")).toHaveTextContent(/^Tâche échouée/);
    expect(within(tasks).queryByRole("button", { name: /^Relancer/ })).toBeNull();
  });

  it("stays open while the restoration is asked, closed neither by Escape nor by « Annuler », and tells the refusal that answers it", async () => {
    let release = () => undefined as unknown;
    const answered = new Promise((settle) => {
      release = () => {
        settle(undefined);
      };
    });
    serve(
      { [RESTORE]: refusal("restore_during_backup_refused", 409) },
      { hold: (route) => (route === RESTORE ? answered : undefined) },
    );
    render(list());
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

  it("says at the date it states a date confirmed that is not that of the backup (422), the page read anew, and stays open [WF-ADM-0160-A]", async () => {
    const client = serve({ [RESTORE]: refusal("restore_date_mismatch", 422) });
    const { rerender } = render(list());
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
    expect(said).toHaveTextContent("La date confirmée n’est pas celle de la sauvegarde désignée.");
    // Said at the date, right after the sentence that states it; nothing else is told.
    expect(said.previousElementSibling).toHaveTextContent(
      `sauvegarde du ${dated(LAST_NIGHT)}, vérifiée`,
    );
    expect(within(dialog).getAllByRole("alert")).toHaveLength(1);
    expect(bodies(client, RESTORE)).toHaveLength(1);
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(within(dialog).getByRole("button", { name: "Annuler" })).toBeEnabled();

    // The page read anew gives the backup at another date: the dialog states the date read, and a
    // second confirmation sends it — never again the one captured at the press.
    const reread = { ...LAST_NIGHT, taken_at: "2026-06-03T01:00:30Z" };
    rerender(list([reread, ...backups.items.slice(1)]));
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
    const { baseElement } = render(list());
    await userEvent.click(
      within(row(KEPT)).getByRole("button", {
        name: `Restaurer la plateforme depuis la sauvegarde du ${dated(KEPT)}`,
      }),
    );
    expect(screen.getByRole("dialog", { name: "Restaurer la plateforme" })).toBeVisible();
    await expectAccessible(baseElement);
  });

  it("tells a restoration refused in the dialog, which stays open; Escape closes it asking nothing more", async () => {
    const client = serve({ [RESTORE]: refusal("restore_unverified_refused", 409) });
    render(list());
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
    expect(
      within(screen.getByRole("region", { name: "Tâches de fond" })).queryByText(/^Restauration/),
    ).toBeNull();
  });

  it.each([
    ["failed", "dont la vérification a échoué"],
    ["pending", "dont la vérification est en attente"],
  ] as const)(
    "says in its confirmation a backup whose verification is %s [WF-ADM-0160-A]",
    async (verification, said) => {
      serve();
      render(list([{ ...LAST_NIGHT, verification }]));
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
});
