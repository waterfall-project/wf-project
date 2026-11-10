// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * A backup taken from the screen, downloaded, deposited and restored, against the service
 * (US-0440): the administrator of the installation presses « Sauvegarder maintenant »; the worker
 * backs the platform up and the tracker follows the task to its end (WF-ADM-0150); the screen read
 * anew lists the backup, which the administrator downloads, then deposits as the archive of another
 * installation would be (#350), and the deposit says the date its manifest says. The backup of the
 * list is then restored, its identifier typed, the confirmation naming its date (WF-ADM-0160). The
 * screen gives way to that of the maintenance, every user signed out, until the restoration is
 * done; the administrator signs in again, with the password of the backup, and finds the screen.
 * What was written after the backup is not found any more (US-0970): a project manager of the
 * path, whose account the backup holds, marks by the worker the revision of a project it had opened
 * before the backup, and creates another project, after it; once restored, the revision is current
 * again, the version name gone, and the other project is not found.
 *
 * The backup of the path is the row the list did not hold before « Sauvegarder maintenant », known
 * by the backup its download names: a backup of a run played minutes before is never taken for it
 * (#2751). The archive downloaded comes through the proxy of the contract byte for byte — Prism,
 * which would spoil the bytes of a body that is not JSON, is passed them by the two legs around it
 * (`bench/contract-proxy.ts`, #1025) —, and is compared with the digests its manifest gives of each
 * dump. Once the platform is restored from the list, the archive is deposited back, accepted with
 * its date, and restored in its turn (WF-ADM-0160, « ou depuis une sauvegarde copiée hors de la
 * plateforme »): the service checks the digests of a deposit only then, so that the restoration
 * succeeding proves the upload crossed the legs byte for byte. The archive
 * of a new installation, about half a mebibyte, is deposited in one part: the cut of an archive in
 * parts of 5 MiB, on a byte inside a character (#2695), is proven by the test of the legs
 * (`bench/contract-proxy.test.ts`), not here. The restoration replaces the whole platform and
 * closes every session: the path plays alone, last (`playwright.config.ts`, the project
 * `restoration`).
 */
import { createHash, randomBytes } from "node:crypto";
import { readFile } from "node:fs/promises";

import { type APIRequestContext, expect, type Locator, type Page, test } from "@playwright/test";

import type { components } from "../../src/api/generated/schema";
import { compileAnswered } from "../compile";
import { untilHydrated, WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  ADMINISTRATOR,
  API,
  frontToken,
  giveIdentifiers,
  localAccount,
  type LocalPerson,
  signIn,
} from "./realm";

type Schemas = components["schemas"];

heldToTheContract();

// The predefined role that creates a project, opens and marks its revisions (WF-EXP-0020).
const PROJECT_MANAGER = "Chef de projet";
// How long the worker is given to mark a revision: a task taken from the queue, one transaction.
const MARKING = 60_000;
const BACKUPS = "/admin/backups";
const JOURNAL = "/admin/audit-log";
const ANY_BACKUP = `${BACKUPS}/01926f3a-7c00-7000-8000-000000000907/content`;

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", BACKUPS, ANY_BACKUP, JOURNAL);
});

/** The project manager of the path at the API, as the front calls it with its token. */
function projectManagerAt(request: APIRequestContext, token: string) {
  const asked = async <T>(
    method: "GET" | "POST",
    path: string,
    status: number,
    data?: unknown,
  ): Promise<T> => {
    const options = {
      headers: { Authorization: `Bearer ${token}` },
      ...(data === undefined ? {} : { data }),
    };
    const answer =
      method === "GET"
        ? await request.get(`${API}${path}`, options)
        : await request.post(`${API}${path}`, options);
    expect(answer.status(), `${method} ${path}`).toBe(status);
    return (await answer.json()) as T;
  };
  return {
    /** Create a project, its creator its project manager, and open its current revision. */
    projectWithRevision: async (label: string) => {
      const created: Schemas["ProjectCreate"] = { label };
      const project = await asked<Schemas["Project"]>("POST", "/projects", 201, created);
      const opened: Schemas["RevisionCreate"] = { apply_rate_update: false };
      const revision = await asked<Schemas["Revision"]>(
        "POST",
        `/projects/${project.project_id}/revisions`,
        201,
        opened,
      );
      return { project: project.project_id, revision };
    },
    /** Mark a revision as the screen does, and follow the task of the worker to its success. */
    mark: async (project: string, revision: Schemas["Revision"], versionName: string) => {
      const marking: Schemas["RevisionMark"] = {
        version_name: versionName,
        lock_version: revision.lock_version,
      };
      const { task_id: task } = await asked<Schemas["BackgroundTaskRef"]>(
        "POST",
        `/projects/${project}/revisions/${revision.revision_id}/mark`,
        202,
        marking,
      );
      // The wait ends with the task, whatever its end: a task that failed ends it at once, and its
      // problem is what the path fails on, not the whole delay given to the worker.
      let ended: Schemas["BackgroundTaskRef"] | undefined;
      const finished = async (): Promise<boolean> => {
        const read = await asked<Schemas["BackgroundTaskRef"]>("GET", `/tasks/${task}`, 200);
        const over = read.status === "succeeded" || read.status === "failed";
        ended = over ? read : undefined;
        return over;
      };
      await expect.poll(finished, { timeout: MARKING }).toBe(true);
      expect(ended?.status, JSON.stringify(ended?.problem)).toBe("succeeded");
    },
    /** The revisions of a project, as its history lists them. */
    revisions: async (project: string) =>
      (await asked<{ items: Schemas["Revision"][] }>("GET", `/projects/${project}/revisions`, 200))
        .items,
    /** Assert a project is not found: the answer has no body to read as a project. */
    notFound: async (project: string) => {
      const answer = await request.get(`${API}/projects/${project}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(answer.status(), `GET /projects/${project}`).toBe(404);
    },
  };
}

// A block of a tar archive, which the archive of a backup is, uncompressed.
const BLOCK = 512;

/**
 * The members of a tar archive, by their names: each header block, then the data, to the end of its
 * last block; an extended header (PAX) may give the name of the member that follows it.
 */
function members(archive: Buffer): Map<string, Buffer> {
  const found = new Map<string, Buffer>();
  let at = 0;
  let named: string | undefined;
  while (at + BLOCK <= archive.length && archive[at] !== 0) {
    const field = (from: number, length: number) =>
      archive.toString("latin1", at + from, at + from + length).split("\0")[0] ?? "";
    const size = Number.parseInt(field(124, 12).trim(), 8);
    const kind = field(156, 1);
    const data = archive.subarray(at + BLOCK, at + BLOCK + size);
    if (kind === "x") {
      named = /\d+ path=([^\n]*)\n/.exec(data.toString("utf8"))?.[1] ?? named;
    } else if (kind !== "g") {
      found.set(named ?? field(0, 100), data);
      named = undefined;
    }
    at += BLOCK + Math.ceil(size / BLOCK) * BLOCK;
  }
  return found;
}

/**
 * Assert that an archive downloaded is the backup the service took, byte for byte: each dump of the
 * length and of the digest its manifest gives — a byte rewritten on the way, and the digest differs.
 */
function expectWhole(archive: Buffer): void {
  const read = members(archive);
  const manifest = read.get("manifest.json");
  expect(manifest, "the manifest of the archive").toBeDefined();
  const { databases } = JSON.parse(manifest?.toString("utf8") ?? "{}") as {
    databases: { file: string; size_bytes: number; sha256: string }[];
  };
  expect(databases.length, "the dumps the manifest lists").toBeGreaterThan(0);
  for (const { file, size_bytes, sha256 } of databases) {
    const dump = read.get(file) ?? Buffer.alloc(0);
    expect(dump.length, `the length of ${file}`).toBe(size_bytes);
    expect(createHash("sha256").update(dump).digest("hex"), `the digest of ${file}`).toBe(sha256);
  }
}

/** The backup a link of download names, by the address it leaves for. */
async function backupOf(link: Locator): Promise<string> {
  const address = (await link.getAttribute("href")) ?? "";
  return new RegExp(`^${BACKUPS}/([^/?]+)/content`).exec(address)?.[1] ?? address;
}

/**
 * Press a command that hands a task over to the tracker, on a page that may not be hydrated yet:
 * again until React answered — a press answered is never repeated, which would ask a second task.
 * `followed` is the button of the panel once it counts a task.
 */
async function handOver(command: Locator, followed: Locator): Promise<void> {
  await expect(async () => {
    if ((await command.getAttribute("aria-busy")) !== "true" && (await followed.count()) === 0) {
      await command.click();
    }
    await expect
      .poll(
        async () =>
          (await command.getAttribute("aria-busy")) === "true" || (await followed.count()) > 0,
        { timeout: 1_000 },
      )
      .toBe(true);
  }).toPass({ timeout: WORKING });
}

/**
 * Follow a restoration confirmed to its end: the screen says it waiting, then done once the probe
 * said the maintenance — every user signed out — and its end. A restoration this small may hold the
 * maintenance between two reads of the probe: the screen then sees the session closed and nothing
 * more, and says that alone, without affirming the restoration done: the journal of audit says it,
 * after the sign-in. The administrator then signs in again and finds the screen.
 */
async function untilRestored(page: Page): Promise<void> {
  const maintenance = page.getByRole("status", {
    name: "Restauration de la plateforme en cours",
  });
  await expect(maintenance).toContainText("La restauration est en attente");
  const signedOut = page.getByRole("status", { name: "Session terminée" });
  // Its title is the whole text of its element: the paragraph of the maintenance names the
  // restoration « terminée » too, as what the users wait for (#2219).
  const ended = maintenance.getByText("Restauration terminée", { exact: true }).or(signedOut);
  // A restoration refused before the maintenance gives the page back with its motive: said at
  // once, rather than waited for until the end of the path.
  const refused = page.getByRole("main").getByRole("alert");
  await expect(ended.or(refused)).toBeVisible({ timeout: 420_000 });
  await expect(refused).toHaveCount(0);

  await page.getByRole("link", { name: "Se connecter" }).click();
  await giveIdentifiers(page, ADMINISTRATOR);
  await expect(page).toHaveURL(BACKUPS);
  await expect(page.getByRole("grid", { name: "Sauvegardes" })).toBeVisible();
}

test(
  "a backup taken, downloaded, deposited and restored: the screen says the restoration waiting, then its end, and the administrator signs in again [WF-ADM-0150-A] [WF-ADM-0160-A]",
  { tag: "@platform-wide" },
  async ({ page, browser, request, playwright }, testInfo) => {
    // A backup by the worker, its verification, then a restoration that replaces both databases
    // and applies the realm again: minutes, not seconds.
    test.setTimeout(600_000);

    // Before the backup, a project manager of the path, and a project of hers with its current
    // revision: the backup holds them, and the restoration keeps them. A path played again on the
    // same installation adds one account and one project to the platform, no more: what it writes
    // after the backup, the restoration takes back, and the installation of a run is new (#2221).
    const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
    let manager: LocalPerson;
    try {
      const administrator = await accountAdministrator(browser, calls);
      manager = await localAccount(browser, administrator);
      await administrator.give(manager.id, PROJECT_MANAGER, []);
    } finally {
      await calls.dispose();
    }
    const suffix = randomBytes(4).toString("hex");
    const before = projectManagerAt(request, await frontToken(browser, manager));
    const kept = await before.projectWithRevision(`Avant la sauvegarde ${suffix}`);

    await signIn(page, ADMINISTRATOR, BACKUPS);
    // The backups the list holds before the one of the path, by the backup their download names —
    // none, on a new installation: the row of the path is the one that is none of them, whatever
    // its date, so that a backup of a run played minutes before is never taken for it (#2751).
    // Read once the screen is hydrated and its grid holds its rows: read before, the list held
    // nothing, and the row of a backup taken an hour before was taken for that of the path. A list
    // without any backup shows no grid, only its count: the screen is served whole, so the grid is
    // there or is not once the command that starts a backup is, and none held is the empty set.
    const grid = page.getByRole("grid", { name: "Sauvegardes" });
    await expect(page.getByRole("button", { name: "Sauvegarder maintenant" })).toBeVisible();
    await untilHydrated(page);
    const downloads = grid.getByRole("link", { name: /^Télécharger la sauvegarde du / });
    const listed = async (): Promise<string[]> =>
      Promise.all((await downloads.all()).map(async (link) => backupOf(link)));
    const held = new Set<string>();
    if ((await grid.count()) > 0) {
      const rowsListed = async () => Number((await grid.getAttribute("aria-rowcount")) ?? "0") - 2;
      // More than one row listed, the first is a backup whose download the grid offers; one row
      // alone may be the notice of a list without any.
      await expect
        .poll(async () => (await rowsListed()) <= 1 || (await downloads.count()) > 0, {
          timeout: WORKING,
        })
        .toBe(true);
      for (const backup of await listed()) {
        held.add(backup);
      }
    }

    // The backup, followed by the tracker until the worker has taken and verified it.
    const followed = page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ });
    const tasks = page.getByRole("region", { name: "Tâches de fond" });
    const entries = tasks.getByRole("listitem");
    await handOver(page.getByRole("button", { name: "Sauvegarder maintenant" }), followed);
    await followed.click();
    await expect(entries.getByText("Réussie")).toBeVisible({ timeout: 180_000 });
    await entries.getByRole("button", { name: "Recharger l’écran" }).click();
    // Listed once the screen is read anew, with its date, the instant it was taken, which the
    // browser writes in its local time, and with its size. The grid is there once a backup is.
    await expect(grid).toBeVisible();
    let taken = "";
    await expect
      .poll(async () => {
        taken = (await listed()).find((backup) => !held.has(backup)) ?? "";
        return taken;
      })
      .not.toBe("");
    const newest = grid
      .getByRole("row")
      .filter({ has: page.locator(`a[href^="${BACKUPS}/${taken}/content"]`) });
    await expect(newest).toHaveCount(1);
    await expect(newest).toContainText("Vérifiée");
    const date = newest.locator("time");
    await expect(date).not.toBeEmpty();
    const takenAt = Date.parse((await date.getAttribute("datetime")) ?? "");

    // After the backup, the revision of the project is marked by the worker, and another project
    // is created.
    const after = projectManagerAt(request, await frontToken(browser, manager));
    await after.mark(kept.project, kept.revision, `Après la sauvegarde ${suffix}`);
    expect((await after.revisions(kept.project)).map((one) => one.status)).toEqual(["marked"]);
    const { project: later } = await after.projectWithRevision(`Après la sauvegarde ${suffix}`);
    await expect(newest).toContainText(/\d+(,\d)?\s(octet|kilooctet|mégaoctet|gigaoctet)s?/);

    // Downloaded through the front, which hands the archive on under its name.
    const downloading = page.waitForEvent("download");
    await newest.getByRole("link", { name: /^Télécharger la sauvegarde du / }).click();
    const download = await downloading;
    expect(download.suggestedFilename()).not.toBe("");
    const archive = testInfo.outputPath(download.suggestedFilename());
    await download.saveAs(archive);
    expectWhole(await readFile(archive));

    // The backup of the list restored once its identifier is typed, the confirmation naming its
    // date: first the restoration waiting, no one signed out yet. The deposit follows, restored in
    // its turn (WF-ADM-0160: from a backup of the list, or from one copied out of the platform).
    // The date as the list writes it, read before the dialog opens: modal, it hides the page
    // behind it, the grid with it.
    const takenText = await date.innerText();
    const confirmed = Date.now();
    await newest
      .getByRole("button", { name: /^Restaurer la plateforme depuis la sauvegarde du / })
      .click();
    const dialog = page.getByRole("dialog", { name: "Restaurer la plateforme" });
    await expect(dialog).toContainText(`sauvegarde du ${takenText}`);
    const identifier = await dialog.locator("code").innerText();
    await dialog
      .getByRole("textbox", { name: "Pour confirmer, saisissez l’identifiant de la sauvegarde" })
      .fill(identifier);
    await dialog.getByRole("button", { name: "Restaurer", exact: true }).click();
    await untilRestored(page);

    // Whatever end the screen saw, the restoration took place and succeeded: the last inscription
    // of the journal of audit is the restoration itself, of the backup, which the service writes
    // only once the task succeeded, the maintenance lifted after it (WF-ADM-0160). The
    // administrator, « Administrateur », reads the journal.
    await page.goto(JOURNAL);
    const last = page.getByRole("grid", { name: "Journal d’audit" }).getByRole("row").nth(1);
    await expect(last).toContainText("Restauration", { timeout: WORKING });
    await expect(last).toContainText("Sauvegarde");
    await expect(last).not.toContainText("Sauvegarde déposée");
    const restoredAt = Date.parse((await last.locator("time").getAttribute("datetime")) ?? "");
    expect(restoredAt).toBeGreaterThanOrEqual(confirmed - 60_000);

    // Nothing written after the backup is found: the revision marked after it is current again,
    // without its version name, and the project created after it is not found (WF-ADM-0160).
    const restored = projectManagerAt(request, await frontToken(browser, manager));
    const revisions = await restored.revisions(kept.project);
    expect(revisions.map((one) => [one.revision_id, one.status, one.version_name])).toEqual([
      [kept.revision.revision_id, "draft", null],
    ]);
    await restored.notFound(later);

    // Deposited as the archive of another installation, which says the date of its backup, and
    // restored in its turn: the service checks the digests of a deposit only then, so that the
    // archive sent byte for byte is proven by the restoration succeeding (#1025).
    await page.goto(BACKUPS);
    const deposit = page.getByRole("region", {
      name: "Restaurer une sauvegarde d’une autre installation",
    });
    await deposit.getByLabel("Archive de la sauvegarde").setInputFiles(archive);
    await deposit.getByRole("button", { name: "Déposer" }).click();
    await expect(deposit.getByRole("button", { name: "Restaurer cette sauvegarde" })).toBeVisible({
      timeout: 60_000,
    });
    const deposited = await deposit.getByRole("time").getAttribute("datetime");
    expect(Date.parse(deposited ?? "")).toBe(takenAt);
    const confirmedDeposit = Date.now();
    await deposit.getByRole("button", { name: "Restaurer cette sauvegarde" }).click();
    const depositDialog = page.getByRole("dialog", { name: "Restaurer la plateforme" });
    await depositDialog
      .getByRole("textbox", { name: "Pour confirmer, saisissez l’identifiant de la sauvegarde" })
      .fill(await depositDialog.locator("code").innerText());
    await depositDialog.getByRole("button", { name: "Restaurer", exact: true }).click();
    await untilRestored(page);
    await page.goto(JOURNAL);
    const lastDeposit = page.getByRole("grid", { name: "Journal d’audit" }).getByRole("row").nth(1);
    await expect(lastDeposit).toContainText("Restauration", { timeout: WORKING });
    await expect(lastDeposit).toContainText("Sauvegarde déposée");
    const restoredDepositAt = Date.parse(
      (await lastDeposit.locator("time").getAttribute("datetime")) ?? "",
    );
    expect(restoredDepositAt).toBeGreaterThanOrEqual(confirmedDeposit - 60_000);
  },
);
