// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The help of every screen of the table of the functions, the seven of the portfolio among them
 * (WF-IHM-0140-A, US-2760): each screen opens, by the « Aide » button of its header, a panel named
 * by the title of its page, which says what the screen shows. The pages are written and tested
 * against the table by EP-16 (`src/help/help.test.ts`); here each screen is opened and its help
 * read — against the fake back, which grants every permission, and against the service, as the
 * account of the run, the manager; for the administration, the reader of the administration
 * (`@administration`, US-1330); for the installation, the administrator.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect } from "@playwright/test";

import { WORKING } from "./bounds";
import { untilHydrated } from "./hydration";
import { inService, test } from "./mode";
import { type AppScreen, tableScreens } from "./routes";

test.describe.configure({ mode: "parallel" });

/**
 * The installation, which the reader of the administration does not read (it holds no
 * `installation.read`): the administrator of the installation reads it (`@administrator`, `mode.ts`).
 */
const ADMINISTRATOR_ONLY: readonly string[] = ["FBS-1.6"];

/**
 * The screen the service cannot serve yet, whoever reads it: the state of the system reads
 * `GET /system/status`, which the service does not serve (the administrator and the reader of the
 * administration both receive « Introuvable »), until US-2890 of EP-13 (#2307).
 */
const NOT_SERVED = "FBS-1.3";

/** Whether the screen belongs to the administration, which its reader alone opens. */
function administered(screen: AppScreen): boolean {
  return screen.route.startsWith("/admin") || screen.route === "/system";
}

/** The title of the page of the help of a code: the heading of the first line of its file. */
function pageTitle(code: string): string {
  const first = readFileSync(join(import.meta.dirname, "../help/fr", `${code}.md`), "utf-8").split(
    "\n",
    1,
  )[0];
  return (first ?? "").replace(/^# /, "");
}

for (const screen of tableScreens()) {
  const reader = ADMINISTRATOR_ONLY.includes(screen.code)
    ? " @administrator"
    : administered(screen)
      ? " @administration"
      : "";
  test(`${screen.code} ${screen.route}: the help of the screen opens, named by its page, and says what the screen shows @shared${reader} [WF-IHM-0140-A]`, async ({
    page,
  }) => {
    test.skip(
      inService && screen.code === NOT_SERVED,
      "the service does not serve getSystemStatus",
    );
    test.slow();
    await page.goto(screen.address);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(screen.name, {
      timeout: WORKING,
    });
    await untilHydrated(page);
    const help = page.getByRole("button", { name: "Aide", exact: true });
    await help.focus();
    await page.keyboard.press("F1");
    // Named by the title of its page, which is the screen's own, or longer (« Correspondance de
    // l’extraction des coûts réels » for the screen « Correspondance des coûts réels »): the first
    // line of the page of its code.
    const panel = page.getByRole("dialog");
    await expect(panel).toHaveAccessibleName(pageTitle(screen.code));
    await expect(panel.getByRole("heading", { name: "Ce que montre l’écran" })).toBeVisible({
      timeout: WORKING,
    });
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(help).toBeFocused();
  });
}
