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
import type { components } from "../src/api/generated/schema";
import { workbook } from "./workbook";

/** How long the worker is given to mark a revision: a task taken from the queue, one transaction. */
export const MARKING = 60_000;

type Schemas = components["schemas"];

type Headers = Readonly<Record<string, string>>;

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

/** What a path asserts along the way of `bringInProgress`, between two of its steps. */
export interface Between {
  /** After the line is under its task, before the revision is marked. */
  readonly beforeMarking?: () => Promise<void>;
  /** After the reference is designated, before the code is entered. */
  readonly afterDesignation?: () => Promise<void>;
}

/**
 * Take a project seeded with a planning to In progress by the way of the cycle: a line under a task,
 * its revision marked by the worker, designated as the reference, and the code of the project
 * entered. Returns the code, which the WBS elements of an extraction begin with. A path that
 * asserts what the screen says along the way gives it as `between`.
 */
export async function bringInProgress(
  page: Page,
  calls: APIRequestContext,
  seeded: Seeded,
  between: Between = {},
): Promise<string> {
  const main = page.getByRole("main");
  await employRole(calls, seeded.headers, seeded.ids, seeded.nodes[6] ?? "", wiringService());
  await between.beforeMarking?.();
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

  await between.afterDesignation?.();

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

/*
 * The path of the remaining to commit (US-1630) takes its project In progress by the operations of
 * the service, under the token of its creator, and opens the current revision from the reference.
 */

/** The identifier of the current revision a project In progress opens. */
export interface Successor {
  readonly revision: string;
}

/** Read a counter of an object of the service, which a write must send back. */
async function lockOf(
  calls: APIRequestContext,
  headers: Headers,
  address: string,
): Promise<number> {
  const read = await calls.get(address, { headers });
  expect(read.status(), `GET ${address}`).toBe(200);
  return ((await read.json()) as Pick<Schemas["Revision"], "lock_version">).lock_version;
}

/**
 * Mark a revision as the screen does, by the API under the token of its project manager, and follow
 * the task of the worker to its end. The wait ends with the task, whatever its end: a task that
 * failed ends it at once, and its problem is what the path fails on, not the whole delay given to
 * the worker (#2835).
 */
export async function markRevision(
  calls: APIRequestContext,
  headers: Headers,
  project: string,
  revision: Pick<Schemas["Revision"], "revision_id" | "lock_version">,
  versionName: string,
): Promise<void> {
  const marking: Schemas["RevisionMark"] = {
    version_name: versionName,
    lock_version: revision.lock_version,
  };
  const marked = await calls.post(
    `${API}/projects/${project}/revisions/${revision.revision_id}/mark`,
    {
      headers,
      data: marking,
    },
  );
  expect(marked.status(), "POST mark").toBe(202);
  const { task_id: task } = (await marked.json()) as Schemas["BackgroundTaskRef"];
  let ended: Schemas["BackgroundTaskRef"] | undefined;
  const finished = async (): Promise<boolean> => {
    const read = await calls.get(`${API}/tasks/${task}`, { headers });
    expect(read.status(), "GET task").toBe(200);
    const body = (await read.json()) as Schemas["BackgroundTaskRef"];
    const over = body.status === "succeeded" || body.status === "failed";
    ended = over ? body : undefined;
    return over;
  };
  await expect.poll(finished, { timeout: MARKING }).toBe(true);
  expect(ended?.status, JSON.stringify(ended?.problem)).toBe("succeeded");
}

/**
 * Mark the revision seeded, designate it as the reference, enter the code of the project — which
 * takes it In progress — and open the current revision. The seeded revision must bear a task and a
 * line (`employRole`).
 */
export async function takeInProgress(
  calls: APIRequestContext,
  seeded: Seeded,
  code: string,
): Promise<Successor> {
  const { headers } = seeded;
  const project = `${API}/projects/${seeded.ids.project}`;
  const revision = `${project}/revisions/${seeded.ids.revision}`;

  await markRevision(
    calls,
    headers,
    seeded.ids.project,
    {
      revision_id: seeded.ids.revision,
      lock_version: await lockOf(calls, headers, revision),
    },
    "v1.0",
  );

  const designated = await calls.put(`${project}/reference-revision`, {
    headers,
    data: {
      revision_id: seeded.ids.revision,
      confirmed: true,
      lock_version: await lockOf(calls, headers, project),
    },
  });
  expect(designated.status(), "PUT reference-revision").toBe(200);
  const coded = await calls.patch(project, {
    headers,
    data: { code, lock_version: await lockOf(calls, headers, project) },
  });
  expect(coded.status(), "PATCH project").toBe(200);
  expect(((await coded.json()) as Schemas["Project"]).state).toBe("in_progress");

  const opened = await calls.post(`${project}/revisions`, { headers, data: {} });
  expect(opened.status(), "POST revisions").toBe(201);
  const successor = ((await opened.json()) as Schemas["Revision"]).revision_id;
  // The main structure is made by the worker as the revision opens.
  await expect(async () => {
    const structures = await calls.get(`${project}/revisions/${successor}/structures`, { headers });
    expect(structures.status(), "GET structures").toBe(200);
    const listed = (await structures.json()) as Schemas["CostStructure"][];
    expect(listed.some(({ kind }) => kind === "main")).toBe(true);
  }).toPass({ timeout: WORKING });
  return { revision: successor };
}
