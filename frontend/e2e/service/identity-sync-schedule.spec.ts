// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The periodicity of the reading of the accounts, set from the screen of the accounts, against the
 * service (US-3040): a local account of the path, that reads and modifies the accounts,
 * finds the periodicity the platform ships — on, daily, at 01:30 UTC — without anyone having entered
 * it; sets it weekly, on a Wednesday, at 03:15 UTC, and finds it so once the page is read anew; and
 * a write made from a version of it another write has outdated is refused (412), what the form says
 * without losing the schedule. The service keeps the schedule in its database: the path puts back
 * the one it shipped, whatever happened, so that no other path meets a reading at a strange hour.
 * The path carries the criterion of the story alone; the Vérif of WF-ADM-0070 is covered elsewhere.
 * No write of the schedule asks a reading: the reading on demand is the business of
 * `identity-sync.spec.ts`.
 */
import { expect, test } from "@playwright/test";

import catalogue from "../../messages/fr.json" with { type: "json" };
import { WORKING } from "../bounds";
import { compileAnswered } from "../compile";
import { untilHydrated } from "../hydration";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  API,
  frontToken,
  localAccount,
  signIn,
  withdrawRoles,
} from "./realm";

heldToTheContract();

const USERS = "/admin/users";
const SCHEDULER = "Périodicité de la lecture des comptes (parcours)";
const SCHEDULE = `${API}/identity-sync-schedule`;

interface Schedule {
  is_enabled: boolean;
  frequency: "daily" | "weekly";
  at_time: string;
  weekday: number | null;
  lock_version: number;
}

const withoutVersion = (schedule: Schedule): Omit<Schedule, "lock_version"> => ({
  is_enabled: schedule.is_enabled,
  frequency: schedule.frequency,
  at_time: schedule.at_time,
  weekday: schedule.weekday,
});

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", USERS);
});

test("the periodicity shipped is read without having been entered, set weekly from the screen, kept, and refused from a version outdated [US-3040]", async ({
  browser,
  page,
  playwright,
}) => {
  test.setTimeout(180_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const holder = await localAccount(browser, administrator);
  const token = await frontToken(browser, holder);
  const headers = { Authorization: `Bearer ${token}` };
  const current = async (): Promise<Schedule> => {
    const answer = await calls.get(SCHEDULE, { headers });
    expect(answer.status(), "GET identity-sync-schedule").toBe(200);
    return (await answer.json()) as Schedule;
  };
  let shipped: Schedule | undefined;
  try {
    await administrator.give(holder.id, SCHEDULER, ["users.read", "users.write"]);
    shipped = await current();
    await signIn(page, holder, USERS);
    const section = page.getByRole("region", { name: "Périodicité de la lecture", exact: true });
    await expect(section).toBeVisible();
    await untilHydrated(page);
    // What the platform ships, read before anything was entered: every path puts it back at its end.
    expect(shipped).toMatchObject({
      is_enabled: true,
      frequency: "daily",
      at_time: "01:30",
      weekday: null,
    });
    await expect(section).toContainText("Active");
    await expect(section).toContainText("Quotidienne");
    await expect(section).toContainText("01:30 UTC");
    await expect(section).not.toContainText("Mercredi");

    // Set weekly, on a Wednesday, at 03:15 UTC, from the version the form opened on.
    await section.getByRole("button", { name: "Modifier la périodicité" }).click();
    const form = page.getByRole("dialog", { name: "Modifier la périodicité" });
    await form.getByRole("combobox", { name: "Fréquence" }).selectOption("weekly");
    await form.getByRole("combobox", { name: "Jour" }).selectOption("3");
    await form.getByLabel("Heure (UTC)").fill("03:15");
    await form.getByRole("button", { name: "Enregistrer" }).click();
    await expect(form).toBeHidden({ timeout: WORKING });
    await expect(section.getByRole("status")).toHaveText("Périodicité enregistrée.");
    await expect(section).toContainText("Hebdomadaire");
    await expect(section).toContainText("Mercredi");
    await expect(section).toContainText("03:15 UTC");
    const written = await current();
    expect(written).toMatchObject({ frequency: "weekly", weekday: 3, at_time: "03:15" });
    expect(written.lock_version).toBe(shipped.lock_version + 1);

    // Kept by the service: the page read anew shows it.
    await page.reload();
    const reread = page.getByRole("region", { name: "Périodicité de la lecture", exact: true });
    await expect(reread).toContainText("Mercredi");
    await expect(reread).toContainText("03:15 UTC");

    // A form opened, then the schedule written elsewhere: the version it holds is outdated (412).
    await untilHydrated(page);
    await reread.getByRole("button", { name: "Modifier la périodicité" }).click();
    const stale = page.getByRole("dialog", { name: "Modifier la périodicité" });
    await expect(stale.getByLabel("Heure (UTC)")).toHaveValue("03:15");
    const elsewhere = await calls.put(SCHEDULE, {
      headers,
      data: { ...written, at_time: "04:45" },
    });
    expect(elsewhere.status()).toBe(200);
    await stale.getByLabel("Heure (UTC)").fill("05:00");
    await stale.getByRole("button", { name: "Enregistrer" }).click();
    await expect(stale.getByRole("alert")).toContainText(
      catalogue.errors.STALE_LOCK_VERSION,
      { timeout: WORKING },
    );
    await expect(stale).toBeVisible();
    await expect(stale.getByLabel("Heure (UTC)")).toHaveValue("05:00");
    expect((await current()).at_time).toBe("04:45");
  } finally {
    try {
      if (shipped !== undefined) {
        // The schedule put back whole as it was shipped, from the version the service holds now.
        const now = await current();
        const whole = withoutVersion(shipped);
        const back = await calls.put(SCHEDULE, {
          headers,
          data: { ...whole, lock_version: now.lock_version },
        });
        expect(back.status(), "PUT identity-sync-schedule, shipped value put back").toBe(200);
        expect(withoutVersion(await current())).toEqual(whole);
      }
    } finally {
      withdrawRoles(holder.email);
      await calls.dispose();
    }
  }
});
