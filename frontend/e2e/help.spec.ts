// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The help of every screen of the table of the functions, the seven of the portfolio among them
 * (WF-IHM-0140-A, US-2760): each screen opens, by the « Aide » button of its header, a panel named
 * by the title of its page, which says what the screen shows. The pages are written and tested
 * against the table by EP-16 (`src/help/help.test.ts`); here each screen is opened and its help
 * read — against the fake back, which grants every permission, and against the service, as the
 * account of the run, the manager, or, for the administration and the state of the system, the
 * reader of the administration (`@administration`, US-1330).
 */
import { expect } from "@playwright/test";

import { WORKING } from "./bounds";
import { untilHydrated } from "./hydration";
import { inService, test } from "./mode";
import { type AppScreen, tableScreens } from "./routes";

test.describe.configure({ mode: "parallel" });

/**
 * The screens neither the account of the run nor the reader of the administration read: the state of
 * the system and the installation, held by the administrator of the installation, whose account no
 * path of this file signs in (the fake back grants every permission).
 */
const ADMINISTRATOR_ONLY: readonly string[] = ["FBS-1.3", "FBS-1.6"];

/** Whether the screen belongs to the administration, which its reader alone opens. */
function administered(screen: AppScreen): boolean {
  return screen.route.startsWith("/admin") || screen.route === "/system";
}

for (const screen of tableScreens()) {
  const reader = administered(screen) ? " @administration" : "";
  test(`${screen.code} ${screen.route}: the help of the screen opens, named by its page, and says what the screen shows @shared${reader} [WF-IHM-0140-A]`, async ({
    page,
  }) => {
    test.skip(
      inService && ADMINISTRATOR_ONLY.includes(screen.code),
      "the administrator of the installation alone reads this screen",
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
    // l’extraction des coûts réels » for the screen « Correspondance des coûts réels »).
    const panel = page.getByRole("dialog");
    await expect(panel).toHaveAccessibleName(/.+/);
    await expect(panel.getByRole("heading", { name: "Ce que montre l’écran" })).toBeVisible({
      timeout: WORKING,
    });
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(help).toBeFocused();
  });
}
