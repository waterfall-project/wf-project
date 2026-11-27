// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the backups against the service (US-2910): its schedule, the marking of a backup,
 * its list filtered and sorted, and the locations of the external copy, played with the service
 * that keeps them — no mock-up notice stands on the screen any more.
 *
 * The schedule: a local account of the path, that reads and modifies the backups, finds the
 * schedule the platform ships — on, daily, at 01:00 UTC, seven backups kept, no external copy —
 * without anyone having entered it (WF-ADM-0170-A); sets it weekly, on a Wednesday, at 03:15 UTC,
 * ten kept, and finds it so once the page is read anew; a write made from a version another write
 * has outdated is refused (412). The refusal of a retention out of its bounds is not played: the
 * proxy of the contract refuses that request itself (422 of Prism, 1 to 365), before the service.
 * The refusal of the service the contract lets through, a copy to an unknown location, is played
 * by the second path. The path puts back the schedule it found, whatever happened: the
 * platform backs up by it, and no other path must meet a backup at a strange hour.
 *
 * The backups: one is taken by the worker, as a manual one is, and the screen read lists it,
 * verified. The marking « Conserver » is kept by the service and read anew, « Ne plus conserver »
 * lifts it; the list is filtered by the origin and the marking, sorted by size, under the names of
 * the contract — the order of the screen is the order of the service, which the path reads at the
 * API, never recomputed.
 *
 * The external copy: the installation declares its locations in a file its deployment mounts
 * (`external_backup_locations_file`), and the platform of the paths declares one, `mounted_share`,
 * a folder (`/srv/external-share`, a volume) the API and the worker see alike (#4655, #4667). The
 * second path plays what the service serves: that location listed, the form of the schedule
 * offering it, the test of a location the installation does not declare refused (404), a copy set
 * to such a location refused at its field (422, `UNKNOWN_EXTERNAL_BACKUP_LOCATION`). The third
 * plays the copy up to the location (WF-ADM-0170-A): the location chosen in the form and tested
 * (the sentence « fichier témoin écrit puis effacé »), the copy kept and read anew from the
 * service, then a scheduled backup — due at the minute the path sets, deposited by the command of
 * the planners (`waterfall-worker schedule`, which the platform runs every five minutes) — copied
 * by the worker: the copy is found in the folder of the location, read from the container of the
 * worker, the volume having no path on the host.
 */
import { execFileSync } from "node:child_process";

import { expect, type Locator, type Page, test } from "@playwright/test";

import catalogue from "../../messages/fr.json" with { type: "json" };
import type { components } from "../../src/api/generated/schema";
import { BACKUP_DONE, SCHEDULED_BACKUP_COPIED, WORKING } from "../bounds";
import { menuButton, openFilters, pick } from "../check-menu";
import { compileAnswered } from "../compile";
import { untilHydrated } from "../hydration";
import { container } from "./components";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  API,
  frontToken,
  localAccount,
  signIn,
  withdrawRoles,
} from "./realm";

type Schemas = components["schemas"];

heldToTheContract();

const BACKUPS = "/admin/backups";
const KEEPER = "Sauvegardes (parcours)";
const SCHEDULE = `${API}/backup-schedule`;
const LOCATIONS = `${API}/external-backup-locations`;
const LOCATION = "mounted_share";
// Where the API and the worker see that location (`service-external-locations.json`).
const FOLDER = "/srv/external-share";
const PERMISSIONS: Schemas["PermissionCode"][] = ["backups.read", "backups.write"];

interface Schedule {
  is_enabled: boolean;
  frequency: "daily" | "weekly";
  at_time: string;
  weekday: number | null;
  retained_count: number;
  external_copy?: unknown;
  lock_version: number;
}

interface Backup {
  backup_id: string;
  origin: "manual" | "scheduled";
  verification: "pending" | "passed" | "failed";
  is_retained: boolean;
  size_bytes: number;
}

const withoutVersion = (schedule: Schedule): Omit<Schedule, "lock_version"> => ({
  is_enabled: schedule.is_enabled,
  frequency: schedule.frequency,
  at_time: schedule.at_time,
  weekday: schedule.weekday,
  retained_count: schedule.retained_count,
  ...(schedule.external_copy === undefined ? {} : { external_copy: schedule.external_copy }),
});

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", BACKUPS);
});

test("the schedule shipped is read without having been entered, set weekly from the screen, kept, refused from a version outdated [WF-ADM-0170-A] [US-2910]", async ({
  browser,
  page,
  playwright,
}) => {
  test.setTimeout(180_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const holder = await localAccount(browser, administrator);
  const headers = { Authorization: `Bearer ${await frontToken(browser, holder)}` };
  const current = async (): Promise<Schedule> => {
    const answer = await calls.get(SCHEDULE, { headers });
    expect(answer.status(), "GET backup-schedule").toBe(200);
    return (await answer.json()) as Schedule;
  };
  let shipped: Schedule | undefined;
  try {
    await administrator.give(holder.id, KEEPER, PERMISSIONS);
    shipped = await current();
    // What the platform ships, read before anything was entered: every path puts it back at its
    // end.
    expect(shipped).toMatchObject({
      is_enabled: true,
      frequency: "daily",
      at_time: "01:00",
      weekday: null,
      retained_count: 7,
    });
    expect(shipped.external_copy).toBeUndefined();

    await signIn(page, holder, BACKUPS);
    const section = page.getByRole("region", { name: "Planification", exact: true });
    await expect(section).toBeVisible();
    await untilHydrated(page);
    await expect(section).toContainText("Active");
    await expect(section).toContainText("Quotidienne");
    await expect(section).toContainText("01:00 UTC");
    await expect(section).toContainText("7 sauvegardes conservées");
    await expect(section).toContainText("Aucune");
    await expect(page.getByText("Maquette")).toHaveCount(0);

    // Set weekly, on a Wednesday, at 03:15 UTC, ten kept, from the version the form opened on.
    await section.getByRole("button", { name: "Modifier la planification" }).click();
    const form = page.getByRole("dialog", { name: "Modifier la planification" });
    await form.getByRole("combobox", { name: "Fréquence" }).selectOption("weekly");
    await form.getByRole("combobox", { name: "Jour" }).selectOption("3");
    await form.getByLabel("Heure (UTC)").fill("03:15");

    await form.getByLabel("Sauvegardes conservées").fill("10");
    await form.getByRole("button", { name: "Enregistrer" }).click();
    await expect(form).toBeHidden({ timeout: WORKING });
    await expect(section.getByRole("status")).toHaveText("Planification enregistrée.");
    await expect(section).toContainText("Hebdomadaire");
    await expect(section).toContainText("Mercredi");
    await expect(section).toContainText("03:15 UTC");
    await expect(section).toContainText("10 sauvegardes conservées");
    const written = await current();
    expect(written).toMatchObject({
      frequency: "weekly",
      weekday: 3,
      at_time: "03:15",
      retained_count: 10,
    });
    expect(written.lock_version).toBe(shipped.lock_version + 1);

    // Kept by the service: the page read anew shows it.
    await page.reload();
    const reread = page.getByRole("region", { name: "Planification", exact: true });
    await expect(reread).toContainText("Mercredi");
    await expect(reread).toContainText("03:15 UTC");
    await expect(reread).toContainText("10 sauvegardes conservées");

    // A form opened, then the schedule written elsewhere: the version it holds is outdated (412).
    await untilHydrated(page);
    await reread.getByRole("button", { name: "Modifier la planification" }).click();
    const stale = page.getByRole("dialog", { name: "Modifier la planification" });
    await expect(stale.getByLabel("Heure (UTC)")).toHaveValue("03:15");
    const elsewhere = await calls.put(SCHEDULE, {
      headers,
      data: { ...written, at_time: "04:45" },
    });
    expect(elsewhere.status()).toBe(200);
    await stale.getByLabel("Heure (UTC)").fill("05:00");
    await stale.getByRole("button", { name: "Enregistrer" }).click();
    await expect(stale.getByRole("alert")).toContainText(catalogue.errors.STALE_LOCK_VERSION, {
      timeout: WORKING,
    });
    await expect(stale).toBeVisible();
    expect((await current()).at_time).toBe("04:45");
  } finally {
    try {
      if (shipped !== undefined) {
        // Put back whole as it was shipped, from the version the service holds now.
        const now = await current();
        const whole = withoutVersion(shipped);
        const back = await calls.put(SCHEDULE, {
          headers,
          data: { ...whole, lock_version: now.lock_version },
        });
        expect(back.status(), "PUT backup-schedule, shipped value put back").toBe(200);
        expect(withoutVersion(await current())).toEqual(whole);
      }
    } finally {
      withdrawRoles(holder.email);
      await calls.dispose();
    }
  }
});

/**
 * The identifiers of the backups a grid lists, by the download each row offers, in the order
 * shown.
 */
async function listed(grid: Locator): Promise<string[]> {
  const links = grid.getByRole("link", { name: /^Télécharger la sauvegarde du / });
  return Promise.all(
    (await links.all()).map(
      async (link) =>
        new RegExp(`^${BACKUPS}/([^/?]+)/content`).exec(
          (await link.getAttribute("href")) ?? "",
        )?.[1] ?? "",
    ),
  );
}

/**
 * The backups a grid lists once it holds rows: a page opened on a sort shows its header before
 * its rows, so a read taken on the header alone finds none (#5005). Read once, then compared to
 * the order of the service by prefix.
 */
async function listedOnceFilled(grid: Locator): Promise<string[]> {
  await expect(
    grid.getByRole("link", { name: /^Télécharger la sauvegarde du / }).first(),
  ).toBeVisible({ timeout: WORKING });
  return listed(grid);
}

/** The row of a backup in the grid, known by its download. */
function rowOf(page: Page, id: string): Locator {
  return page
    .getByRole("grid", { name: "Sauvegardes" })
    .getByRole("row")
    .filter({ has: page.locator(`a[href^="${BACKUPS}/${id}/content"]`) });
}

test("a backup taken is listed, marked to keep and released, filtered and sorted by the service, and the locations of the copy are those the installation declares [WF-ADM-0170-A] [US-2910]", async ({
  browser,
  page,
  playwright,
}) => {
  // A backup by the worker, its verification: a minute or more.
  test.setTimeout(420_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const holder = await localAccount(browser, administrator);
  const headers = { Authorization: `Bearer ${await frontToken(browser, holder)}` };
  const backups = async (query = ""): Promise<Backup[]> => {
    const answer = await calls.get(`${API}/backups${query}`, { headers });
    expect(answer.status(), `GET backups${query}`).toBe(200);
    return ((await answer.json()) as { items: Backup[] }).items;
  };
  try {
    await administrator.give(holder.id, KEEPER, PERMISSIONS);
    const before = new Set((await backups("?limit=100")).map((one) => one.backup_id));

    // The backup of the path, taken by the worker, as « Sauvegarder maintenant » asks it.
    const started = await calls.post(`${API}/backups`, { headers });
    expect(started.status(), "POST backups").toBe(202);
    const { task_id: task } = (await started.json()) as { task_id: string };
    await expect
      .poll(
        async () => {
          const read = await calls.get(`${API}/tasks/${task}`, { headers });
          return ((await read.json()) as { status: string }).status;
        },
        { timeout: 240_000, intervals: [2_000] },
      )
      .toBe("succeeded");
    // The contract links a backup to no task (`BackgroundTaskRef` names no backup, and the task has
    // no result to read), so the backup is the one the list did not hold before. No other path of
    // the project `service` takes one: `backups.spec.ts`, which does, is `@platform-wide` and plays
    // alone, after the others (`playwright.config.ts`, project `restoration`).
    const taken = (await backups("?limit=100")).find((one) => !before.has(one.backup_id));
    expect(taken, "the backup of the path in the list").toBeDefined();
    const id = taken?.backup_id ?? "";
    expect(taken).toMatchObject({ origin: "manual", verification: "passed", is_retained: false });

    await signIn(page, holder, BACKUPS);
    await untilHydrated(page);
    const grid = page.getByRole("grid", { name: "Sauvegardes" });
    await expect(page.getByText("Maquette")).toHaveCount(0);
    const row = rowOf(page, id);
    await expect(row).toContainText("Manuelle");
    await expect(row).toContainText("Vérifiée");

    // Marked to keep: the service keeps the marking, the page read anew shows it.
    await row.getByRole("button", { name: /^Conserver la sauvegarde du / }).click();
    await expect(
      page.getByRole("status").filter({ hasText: "est marquée à conserver" }),
    ).toBeVisible({ timeout: WORKING });
    await expect(row).toContainText("Marquée à conserver");
    expect((await backups("?limit=100")).find((one) => one.backup_id === id)?.is_retained).toBe(
      true,
    );
    await page.reload();
    await untilHydrated(page);
    await expect(rowOf(page, id)).toContainText("Marquée à conserver");

    // Filtered by the marking, under the name of the contract: the backup is there marked, not
    // among those the rotation takes.
    await openFilters(page);
    await page.getByRole("combobox", { name: "Conservation" }).selectOption({
      label: "Marquées à conserver",
    });
    await expect(page).toHaveURL(/is_retained=true/, { timeout: WORKING });
    await expect(rowOf(page, id)).toHaveCount(1);
    expect(await listed(grid)).toEqual(
      (await backups("?is_retained=true&limit=100")).map((one) => one.backup_id),
    );
    await page.getByRole("combobox", { name: "Conservation" }).selectOption({
      label: "Soumises à la rotation",
    });
    await expect(page).toHaveURL(/is_retained=false/, { timeout: WORKING });
    await expect(page.locator(`a[href^="${BACKUPS}/${id}/content"]`)).toHaveCount(0);
    await page.getByRole("combobox", { name: "Conservation" }).selectOption({
      label: "Toutes les sauvegardes",
    });
    await expect(page).not.toHaveURL(/is_retained/, { timeout: WORKING });

    // Filtered by the origin: the backup of the path is a manual one, no scheduled one.
    await pick(page, "Filtrer par déclenchement", "Planifiée");
    await expect(page).toHaveURL(/origins=scheduled/, { timeout: WORKING });
    await expect(page.locator(`a[href^="${BACKUPS}/${id}/content"]`)).toHaveCount(0);
    for (const one of await listed(grid)) {
      expect((await backups("?origins=scheduled&limit=100")).map((b) => b.backup_id)).toContain(
        one,
      );
    }
    await pick(page, "Filtrer par déclenchement", "Planifiée");
    await pick(page, "Filtrer par déclenchement", "Manuelle");
    await expect(page).toHaveURL(/origins=manual/, { timeout: WORKING });
    await expect(menuButton(page, "Filtrer par déclenchement")).toContainText("Manuelle");
    await expect(rowOf(page, id)).toHaveCount(1);

    // Sorted by size, in the order of the service, never recomputed here.
    await page.goto(`${BACKUPS}?sort_by=size_bytes&sort_order=desc`);
    await untilHydrated(page);
    await expect(grid.getByRole("columnheader", { name: /^Taille/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    const bySize = (await backups("?sort_by=size_bytes&sort_order=desc")).map(
      (one) => one.backup_id,
    );
    const bySizeShown = await listedOnceFilled(grid);
    expect(bySizeShown).toEqual(bySize.slice(0, bySizeShown.length));
    await page.goto(`${BACKUPS}?sort_by=size_bytes&sort_order=asc`);
    await untilHydrated(page);
    await expect(grid.getByRole("columnheader", { name: /^Taille/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    const ascending = (await backups("?sort_by=size_bytes&sort_order=asc")).map(
      (one) => one.backup_id,
    );
    const ascendingShown = await listedOnceFilled(grid);
    expect(ascendingShown).toEqual(ascending.slice(0, ascendingShown.length));

    // Released: « Ne plus conserver », kept by the service as well.
    await page.goto(BACKUPS);
    await untilHydrated(page);
    await rowOf(page, id)
      .getByRole("button", { name: /^Ne plus conserver la sauvegarde du / })
      .click();
    await expect(
      page.getByRole("status").filter({ hasText: "n’est plus marquée à conserver" }),
    ).toBeVisible({ timeout: WORKING });
    await expect(rowOf(page, id)).not.toContainText("Marquée à conserver");
    expect((await backups("?limit=100")).find((one) => one.backup_id === id)?.is_retained).toBe(
      false,
    );

    // The locations of the copy: the one the platform of the paths declares, and no other. The
    // test of an unknown one is refused (404); a copy set to a location it does not declare is
    // refused at its field (422); the form of the schedule offers the one declared.
    const listing = await calls.get(LOCATIONS, { headers });
    expect(listing.status(), "GET external-backup-locations").toBe(200);
    expect(await listing.json()).toEqual([
      {
        name: LOCATION,
        kind: "mounted_share",
        description: "Partage monté du parcours de service, le volume external-share.",
      },
    ]);
    const tested = await calls.post(`${LOCATIONS}/ailleurs/test`, { headers, data: {} });
    expect(tested.status(), "POST external-backup-locations/ailleurs/test").toBe(404);
    const schedule = (await (await calls.get(SCHEDULE, { headers })).json()) as Schedule;
    const unknown = await calls.put(SCHEDULE, {
      headers,
      data: {
        ...schedule,
        external_copy: { is_enabled: true, location: "ailleurs", path: "a", retained_count: 7 },
      },
    });
    expect(unknown.status(), "PUT backup-schedule, a copy to an unknown location").toBe(422);
    const problem = (await unknown.json()) as { fields?: { pointer: string; code: string }[] };
    expect(problem.fields).toContainEqual(
      expect.objectContaining({
        pointer: "/external_copy/location",
        code: "UNKNOWN_EXTERNAL_BACKUP_LOCATION",
      }),
    );
    expect((await calls.get(SCHEDULE, { headers })).status()).toBe(200);
    await page.goto(BACKUPS);
    await untilHydrated(page);
    await page
      .getByRole("region", { name: "Planification", exact: true })
      .getByRole("button", { name: "Modifier la planification" })
      .click();
    const form = page.getByRole("dialog", { name: "Modifier la planification" });
    await expect(form.getByLabel("Sauvegardes conservées")).toBeVisible();
    await expect(form.getByLabel("Copie externe vers")).toContainText(LOCATION);
  } finally {
    withdrawRoles(holder.email);
    await calls.dispose();
  }
});

/** What the worker sees in a folder of the location: the volume has no path on the host. */
function onTheLocation(path: string): string[] {
  const worker = container("worker");
  try {
    return execFileSync("docker", ["exec", worker, "ls", `${FOLDER}/${path}`], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    })
      .split("\n")
      .filter((name) => name !== "");
  } catch (error) {
    // The folder is written with the first copy: none yet. Any other failure is not an empty folder.
    const said = (error as { stderr?: string }).stderr ?? "";
    if (said.includes("No such file or directory")) {
      return [];
    }
    throw error;
  }
}

/** Deposit what is due, as the planners do every five minutes: the container of the worker has the settings. */
function planDue(): void {
  execFileSync("docker", ["exec", container("worker"), "waterfall-worker", "schedule"], {
    stdio: "ignore",
  });
}

/** The name of the copy of a backup: its date, in universal time (`copy_name` of the service). */
const copyName = (takenAt: string): string =>
  `waterfall-backup-${new Date(takenAt)
    .toISOString()
    .replace(/\.\d+Z$/, "Z")
    .replaceAll(/[-:]/g, "")}.tar`;

test("the copy of a schedule to a declared location is chosen, its location tested (« fichier témoin écrit puis effacé »), kept and found on the location [WF-ADM-0170-A] [US-2910]", async ({
  browser,
  page,
  playwright,
}) => {
  // A scheduled backup by the worker, its verification, its copy: a minute or two, after the
  // minute the schedule is set to.
  test.setTimeout(SCHEDULED_BACKUP_COPIED + BACKUP_DONE + 2 * WORKING);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const holder = await localAccount(browser, administrator);
  const headers = { Authorization: `Bearer ${await frontToken(browser, holder)}` };
  const current = async (): Promise<Schedule> => {
    const answer = await calls.get(SCHEDULE, { headers });
    expect(answer.status(), "GET backup-schedule").toBe(200);
    return (await answer.json()) as Schedule;
  };
  const scheduled = async (): Promise<(Backup & { taken_at: string })[]> => {
    const answer = await calls.get(`${API}/backups?origins=scheduled&limit=100`, { headers });
    expect(answer.status(), "GET backups, scheduled").toBe(200);
    return ((await answer.json()) as { items: (Backup & { taken_at: string })[] }).items;
  };
  const folder = `parcours-${String(Date.now())}`;
  let shipped: Schedule | undefined;
  try {
    await administrator.give(holder.id, KEEPER, PERMISSIONS);
    shipped = await current();
    const before = new Set((await scheduled()).map((one) => one.backup_id));

    await signIn(page, holder, BACKUPS);
    await untilHydrated(page);
    const section = page.getByRole("region", { name: "Planification", exact: true });
    await section.getByRole("button", { name: "Modifier la planification" }).click();
    const form = page.getByRole("dialog", { name: "Modifier la planification" });

    // The location chosen, its folder given, then tested: the service writes a witness file on it
    // and erases it.
    await form.getByLabel("Copie externe vers").selectOption(LOCATION);
    await form.getByLabel("Dossier dans l’emplacement").fill(folder);
    await form.getByRole("textbox", { name: "Copies gardées" }).fill("7");
    await form.getByRole("button", { name: "Tester l’emplacement" }).click();
    await expect(form.getByRole("status")).toContainText(`« ${LOCATION} » éprouvé le`, {
      timeout: WORKING,
    });
    await expect(form.getByRole("status")).toContainText(
      `dossier ${folder} : le fichier témoin a été écrit puis effacé.`,
    );
    expect(onTheLocation(folder), "the witness file is erased").toEqual([]);

    // Due at the next minute, with a margin to save before it: the occurrence must come after the
    // writing of the schedule (`backup_is_due`).
    // At least forty seconds of margin: the next minute, or the one after it.
    const ahead = new Date(Date.now() + (new Date().getUTCSeconds() > 20 ? 120_000 : 60_000));
    ahead.setUTCSeconds(0, 0);
    const at = ahead.toISOString().slice(11, 16);
    await form.getByLabel("Heure (UTC)").fill(at);
    await form.getByRole("button", { name: "Enregistrer" }).click();
    await expect(form).toBeHidden({ timeout: WORKING });
    await expect(section.getByRole("status")).toHaveText("Planification enregistrée.");
    await expect(section).toContainText(`Vers ${LOCATION}, dossier ${folder}`);

    // Saved before the minute, or the occurrence is tomorrow's and nothing would be deposited.
    expect(
      Date.now(),
      `the schedule was saved after ${at} UTC, the minute it is due: the runner is too slow`,
    ).toBeLessThan(ahead.getTime());

    // The copy kept by the service: the schedule read anew carries it, and the page too.
    const written = await current();
    expect(written).toMatchObject({
      at_time: at,
      external_copy: { is_enabled: true, location: LOCATION, path: folder, retained_count: 7 },
    });
    await page.reload();
    await expect(page.getByRole("region", { name: "Planification", exact: true })).toContainText(
      `Vers ${LOCATION}, dossier ${folder}`,
    );

    // The minute passed, the planners' command deposits the backup due; the worker takes it,
    // verifies it, and copies it.
    let taken: (Backup & { taken_at: string }) | undefined;
    await expect
      .poll(
        async () => {
          if (taken === undefined && Date.now() > ahead.getTime()) {
            planDue();
          }
          taken = (await scheduled()).find((one) => !before.has(one.backup_id));
          return taken?.verification;
        },
        { timeout: SCHEDULED_BACKUP_COPIED, intervals: [5_000] },
      )
      .toBe("passed");
    const name = copyName(taken?.taken_at ?? "");
    await expect
      .poll(() => onTheLocation(folder), { timeout: BACKUP_DONE, intervals: [2_000] })
      .toEqual([name]);
  } finally {
    try {
      if (shipped !== undefined) {
        // Put back whole as it was shipped, without the copy, from the version held now.
        const now = await current();
        const whole = withoutVersion(shipped);
        const back = await calls.put(SCHEDULE, {
          headers,
          data: { ...whole, lock_version: now.lock_version },
        });
        expect(back.status(), "PUT backup-schedule, shipped value put back").toBe(200);
        expect(withoutVersion(await current())).toEqual(whole);
      }
    } finally {
      withdrawRoles(holder.email);
      await calls.dispose();
    }
  }
});
