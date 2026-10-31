// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { openHydrated } from "./hydration";

// The fake back serves the first example of each operation: the project in progress, which lists
// only the exits its state allows, and its current revision, a draft, read by a session granted
// the whole catalogue, which cannot be opened while a draft is under way. The project in pricing,
// whose completion lacks the state in progress, is an example the fake back does not serve first:
// the tests of the commands show it (`exit-command.dom.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("a command the project cannot take now is shown unavailable, naming the condition it lacks [WF-IHM-0090-A]", async ({
  page,
}) => {
  // The example of the Vérif (completing a project in pricing) is not served by the fake back: only
  // `exit-command.dom.test.tsx` proves it. This journey plays the same rule on a command it does
  // serve, opening a revision. `revision-cycle.spec.ts` reads the same condition for its refusal
  // (WF-REV-0010-A); this one proves its presentation: shown beside the command, kept in the
  // keyboard order, doing nothing when pressed.
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });

  const lose = commands.getByRole("button", { name: "Ouvrir une révision en cours" });
  await expect(lose).toHaveAttribute("aria-disabled", "true");
  // Named in a text shown beside it, which describes it to a screen reader too.
  const unmet = /^Condition non remplie\s: aucune révision en cours d’élaboration\.$/;
  await expect(lose).toHaveAccessibleDescription(unmet);
  await expect(commands.getByText(unmet)).toBeVisible();

  // It stays in the order of the keyboard, and pressed, it does nothing: nothing is told.
  await lose.focus();
  await page.keyboard.press("Enter");
  await expect(lose).toBeFocused();
  await expect(commands.getByRole("alert")).toHaveCount(0);

  // The command the revision can take now is offered.
  await expect(commands.getByRole("button", { name: "Marquer la révision" })).not.toHaveAttribute(
    "aria-disabled",
    "true",
  );
});

test("a revision offers the commands its reader may exercise, marking among them", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  await expect(commands.getByRole("button", { name: "Marquer la révision" })).toBeVisible();
  const amendment = commands.getByRole("button", { name: "Préparer un avenant" });
  await expect(amendment).toBeVisible();
  await expect(amendment).not.toHaveAttribute("aria-disabled", "true");
});
