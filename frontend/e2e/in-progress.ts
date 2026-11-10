// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project the run creates, taken to In progress as a user does, and the extraction of its actual
 * costs imported by the API: what the paths that write the actual costs start from (US-1620, #2193).
 * The project is the account's own — the witness is never written by a path.
 */
import { type APIRequestContext, expect, type Page } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { employRole, wiringService } from "./own-project";
import type { Seeded } from "./planning-seed";
import { API } from "./service/realm";
import { workbook } from "./workbook";

const MARKING = 60_000;

/** The headers of an extraction, as the mapping of the installation declares them (WF-REF-0190). */
const HEADERS = [
  "Elément d'OTP",
  "Nº pièce référence",
  "Poste",
  "Date de la pièce",
  "Val./Devise objet",
];

/** A line of an extraction: its WBS element, its document, its date and its amount. */
export type ExtractedLine = readonly [
  element: string,
  document: string,
  on: string,
  amount: number,
];

/**
 * Take a project seeded with a planning to In progress by the way of the cycle: a line under a task,
 * its revision marked by the worker, designated as the reference, and the code of the project
 * entered. Returns the code, which the WBS elements of an extraction begin with.
 */
export async function bringInProgress(
  page: Page,
  calls: APIRequestContext,
  seeded: Seeded,
): Promise<string> {
  const main = page.getByRole("main");
  await employRole(calls, seeded.headers, seeded.ids, seeded.nodes[6] ?? "", wiringService());
  await openHydrated(page, `${seeded.own.path}/revisions?revision_id=${seeded.ids.revision}`);
  const commands = main.getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Marquer la révision" }).click();
  const marking = commands.getByRole("form");
  await marking.getByRole("textbox", { name: "Nom de version" }).fill("v1.0");
  await marking.getByRole("button", { name: "Marquer", exact: true }).click();
  await expect(commands.getByRole("form")).toHaveCount(0);
  await page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ }).click();
  const task = page
    .getByRole("dialog", { name: "Tâches et messages" })
    .getByRole("region", { name: "Tâches de fond" })
    .getByRole("listitem")
    .filter({ hasText: "Marquage d’une révision « v1.0 »" });
  await expect(task.getByText("Réussie")).toBeVisible({ timeout: MARKING });
  await task.getByRole("button", { name: "Recharger l’écran" }).click();
  const designation = main.getByRole("region", { name: "Désignation de la référence" });
  const offer = designation.getByRole("listitem").filter({ hasText: "v1.0" });
  const designate = offer.getByRole("button", { name: "Désigner comme référence" });
  await expect(designate).not.toHaveAttribute("aria-disabled", "true", { timeout: WORKING });
  await designate.click();
  await designation.getByRole("button", { name: "Confirmer la désignation" }).click();
  const history = main.getByRole("table", { name: "Historique des révisions" });
  await expect(history.getByRole("row").nth(1)).toContainText("Référence", { timeout: WORKING });

  // The code entered takes the project In progress, without another action (WF-CYC-0020).
  await openHydrated(page, `${seeded.own.path}/settings`);
  await main.getByRole("button", { name: "Modifier le projet" }).click();
  const identity = page.getByRole("dialog", { name: /^Modifier/ });
  const code = `ENC-${seeded.own.label.slice(-8).toUpperCase()}`;
  await identity.getByRole("textbox", { name: /^Code projet/ }).fill(code);
  await identity.getByRole("button", { name: "Enregistrer" }).click();
  await expect(identity).toBeHidden({ timeout: WORKING });
  await openHydrated(page, `${seeded.own.path}/lifecycle`);
  await expect(
    main.getByRole("table", { name: "Historique des états" }).getByRole("row").last(),
  ).toContainText("En cours", { timeout: WORKING });
  return code;
}

/**
 * Import an extraction of actual costs as the project manager does, by the API under her token:
 * the file deposited, the import opened, its analysis awaited, then confirmed and awaited applied
 * (WF-ARC-0100, WF-INTF-0140).
 */
export async function importActualCosts(
  calls: APIRequestContext,
  seeded: Seeded,
  lines: readonly ExtractedLine[],
): Promise<void> {
  const { headers } = seeded;
  const project = `${API}/projects/${seeded.ids.project}`;
  const rows = lines.map(([element, document, on, amount]) => [
    element,
    document,
    null,
    on,
    amount,
  ]);
  const deposited = await calls.post(`${API}/file-uploads`, {
    headers,
    multipart: {
      purpose: "import",
      file: {
        name: "couts-reels.xlsx",
        mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        buffer: workbook([HEADERS, ...rows]),
      },
    },
  });
  expect(deposited.status(), "POST file-uploads").toBe(201);
  const { upload_id } = (await deposited.json()) as { upload_id: string };
  const opened = await calls.post(`${project}/imports`, {
    headers,
    data: { kind: "actual_costs", upload_id },
  });
  expect(opened.status(), `POST imports: ${await opened.text()}`).toBe(202);
  const { import_id } = (await opened.json()) as { import_id: string };
  const address = `${project}/imports/${import_id}`;
  const statusOf = async (): Promise<string> => {
    const read = await calls.get(address, { headers });
    expect(read.status(), "GET import").toBe(200);
    return ((await read.json()) as { status: string }).status;
  };
  await expect.poll(statusOf, { timeout: WORKING }).toBe("analysed");
  const applied = await calls.post(`${address}/apply`, { headers, data: { confirmed: true } });
  expect(applied.status(), `POST apply: ${await applied.text()}`).toBe(202);
  await expect.poll(statusOf, { timeout: WORKING }).toBe("applied");
}
