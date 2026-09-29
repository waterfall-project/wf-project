// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

// The fake back serves the first example of each operation: the project in progress, whose
// exit as lost lacks the pricing state, and its current revision, a draft, read by a session
// granted the whole catalogue. The project in pricing, whose completion lacks the state in
// progress, is an example the fake back does not serve first: the tests of the commands show
// it (`command.dom.test.tsx`, `[...path]/page.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("a command the project cannot take now is shown unavailable, naming the condition it lacks [WF-IHM-0090-A]", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/lifecycle`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });

  const lose = commands.getByRole("button", { name: "Déclarer le projet perdu" });
  await expect(lose).toHaveAttribute("aria-disabled", "true");
  // Named in a text shown beside it, which describes it to a screen reader too.
  const unmet = /^Condition non remplie\s: projet en chiffrage\.$/;
  await expect(lose).toHaveAccessibleDescription(unmet);
  await expect(commands.getByText(unmet)).toBeVisible();

  // It stays in the order of the keyboard, and pressed, it does nothing: nothing is told.
  await lose.focus();
  await page.keyboard.press("Enter");
  await expect(lose).toBeFocused();
  await expect(commands.getByRole("alert")).toHaveCount(0);

  // The command the project can take now is offered.
  await expect(commands.getByRole("button", { name: "Terminer le projet" })).not.toHaveAttribute(
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
  await expect(commands.getByRole("button", { name: "Modifier le planning" })).not.toHaveAttribute(
    "aria-disabled",
    "true",
  );
});
