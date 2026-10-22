// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { openHydrated } from "./hydration";

// The cycle of the revisions, as far as a fake back that keeps no state lets a journey go: it serves
// the project in progress, its current revision and the history of three revisions, and answers each
// write with the first example of its operation. The commands are therefore read as the server lists
// them — the opening unavailable while a revision is current, the designation unavailable once the
// reference cannot be corrected —, and the abandon, available, is played to its end. The chain of
// the states — marked, designated, code entered, in progress, opened, the remaining entered — needs
// a service that remembers: each step is proved on the examples of the contract by the tests of the
// commands (`revision-commands.dom.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("the opening of a second current revision and the designation beyond the correction are unavailable, naming their condition [WF-REV-0010-A] [WF-REV-0040-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const main = page.getByRole("main");
  const commands = main.getByRole("region", { name: "Commandes" });
  const create = commands.getByRole("button", { name: "Ouvrir une révision en cours" });
  await expect(create).toHaveAttribute("aria-disabled", "true");
  await expect(create).toHaveAccessibleDescription(
    /^Condition non remplie\s: aucune révision en cours d’élaboration\.$/,
  );

  const designation = main.getByRole("region", { name: "Désignation de la référence" });
  const offer = designation.getByRole("listitem", { name: "Offre v1.0" });
  const designate = offer.getByRole("button", { name: "Désigner comme référence" });
  await expect(designate).toHaveAttribute("aria-disabled", "true");
  await expect(designate).toHaveAccessibleDescription(/référence encore corrigeable/);
  // Pressed from the keyboard, as the order of the keyboard keeps it, it does nothing.
  await designate.focus();
  await page.keyboard.press("Enter");
  await expect(designation.getByRole("form")).toHaveCount(0);
});

test("abandoning the current revision asks for a confirmation that says the return and the irreversibility, then leaves the revision [WF-REV-0010-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const main = page.getByRole("main");
  const commands = main.getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Abandonner la révision en cours" }).click();
  const form = commands.getByRole("form", { name: "Abandonner la révision en cours" });
  await expect(form).toContainText("dernière révision marquée");
  await expect(form).toContainText("irréversible");
  await form.getByRole("button", { name: "Confirmer l’abandon" }).click();
  // The screen leaves the address of the revision, which is no more, and its commands with it: the
  // history of the messages, in the shell, keeps what was told.
  await expect(page).toHaveURL(`/projects/${PROJECT}/revisions`);
  await page.getByRole("button", { name: /^Tâches et messages/ }).click();
  const told = page
    .getByRole("dialog", { name: "Tâches et messages" })
    .getByRole("region", { name: "Messages" })
    .getByRole("listitem")
    .first();
  await expect(told).toContainText("La révision en cours est abandonnée");
});
