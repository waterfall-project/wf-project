// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * A reader of the planning who is no contributor of the project, against the service (US-1470,
 * WF-ADM-0110-A): an account that holds the role « Manager » — which carries « consulter tous les
 * projets » and the writing of the planning — reads the planning of a project it is not a
 * contributor of, and cannot modify it, by the grid or by an import; inscribed as a contributor,
 * it modifies it.
 *
 * The first account makes the project and its tasks as a user does; the other is inscribed by the
 * API under the token of the first (the screen of the contributors proposes the accounts of the
 * estimate alone). Both hold the roles « Manager » and « Chef de projet », made by the administrator
 * of the installation.
 */
import { randomUUID } from "node:crypto";

import { type APIRequestContext, expect, test } from "@playwright/test";

import { openHydrated, WORKING } from "../hydration";
import { inscribe } from "../own-project";
import { SEEDED, seedPlanning } from "../planning-seed";
import { heldToTheContract } from "./contract";
import {
  type Administrator,
  accountAdministrator,
  API,
  frontToken,
  localAccount,
  type LocalPerson,
  signIn,
} from "./realm";

heldToTheContract();

const ROLES = [
  ["Manager", []],
  ["Chef de projet", []],
] as const;

let administrator: Administrator;
let calls: APIRequestContext;
let creator: LocalPerson;
let reader: LocalPerson;
let outsider: LocalPerson;

test.beforeAll(async ({ browser, playwright }) => {
  calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  administrator = await accountAdministrator(browser, calls);
  creator = await localAccount(browser, administrator);
  reader = await localAccount(browser, administrator);
  // An account that holds no role: it reads no project.
  outsider = await localAccount(browser, administrator);
  for (const person of [creator, reader]) {
    await administrator.giveAlso(person.id, ROLES);
  }
});

test.afterAll(async () => {
  await calls.dispose();
});

test("an account that reads every project and is no contributor reads the planning, is refused every write and the opening of an import, and modifies it once inscribed [WF-ADM-0110-A]", async ({
  page,
  browser,
}) => {
  test.slow();
  await signIn(page, creator, "/account");
  const seeded = await seedPlanning(page, browser, calls, creator, "Lecteur");
  const { project, revision, structure } = seeded.ids;
  const base = `${API}/projects/${project}/revisions/${revision}/structures/${structure}`;
  const headers = { Authorization: `Bearer ${await frontToken(browser, reader)}` };
  const node = seeded.nodes[2] ?? "";

  // Voit ce planning : the planning is read, 200.
  const read = await calls.get(`${base}/nodes`, { headers });
  expect(read.status(), "GET nodes").toBe(200);

  // Ne peut pas le modifier, ni par la grille ni par import : each write is refused 403
  // NOT_CONTRIBUTOR.
  const writes = {
    createNode: calls.post(`${base}/nodes`, {
      headers,
      data: { kind: "task", parent_id: null, task: { label: "Refusée" } },
    }),
    updateTaskFacet: calls.patch(`${base}/nodes/${node}/task`, {
      headers,
      data: { lock_version: 1, label: "Refusée" },
    }),
    setPredecessors: calls.put(`${base}/nodes/${node}/predecessors`, {
      headers,
      data: { predecessors: [], lock_version: 1 },
    }),
    moveNodes: calls.post(`${base}/nodes/move`, {
      headers,
      data: { node_ids: [node], parent_id: null, lock_version: 1 },
    }),
    deleteNode: calls.delete(`${base}/nodes/${node}?lock_version=1`, { headers }),
    updateCostStructure: calls.patch(base, {
      headers,
      data: { planning_start_on: "2030-02-04", lock_version: 1 },
    }),
    openImport: calls.post(`${API}/projects/${project}/imports`, {
      headers,
      data: { kind: "ms_project_schedule", upload_id: randomUUID() },
    }),
  };
  for (const [operation, pending] of Object.entries(writes)) {
    const answer = await pending;
    expect(answer.status(), operation).toBe(403);
    const problem = (await answer.json()) as { code: string };
    expect(problem.code, operation).toBe("NOT_CONTRIBUTOR");
  }

  // Ni par la grille: the reader opens the grid of the planning, her cells are not enterable, and the
  // validation of a cell she tries sends no write.
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const screen = await context.newPage();
    await signIn(screen, reader, "/account");
    await openHydrated(screen, seeded.planning);
    const grid = screen.getByRole("treegrid", { name: "Grille de planning" });
    const label = grid
      .getByRole("row", { name: new RegExp(`^2 .*${SEEDED[2]}`) })
      .getByRole("gridcell", { name: new RegExp(SEEDED[2]) })
      .first();
    await expect(label).toBeVisible({ timeout: WORKING });
    const sent: string[] = [];
    screen.on("request", (request) => {
      if (request.method() !== "GET") {
        sent.push(`${request.method()} ${request.url()}`);
      }
    });
    await label.click();
    await screen.keyboard.press("F2");
    await expect(label).toHaveAttribute("aria-readonly", "true");
    await expect(grid.getByRole("textbox")).toHaveCount(0);
    await screen.keyboard.type("Refusée");
    await screen.keyboard.press("Enter");
    await expect(grid.getByRole("textbox")).toHaveCount(0);
    expect(sent).toEqual([]);
  } finally {
    await context.close();
  }

  // The reader sees the planning unchanged, by the grid she cannot write.
  const unchanged = (await (await calls.get(`${base}/nodes`, { headers })).json()) as {
    items: unknown[];
  };
  expect(unchanged.items).toHaveLength(6);

  // Une adresse d’objet inexistant et une adresse d’objet non consultable mènent au même écran: the
  // same 404 on a structure, a node and a row number, whether the object does not exist or the
  // account may not read its project.
  const unknown = randomUUID();
  const outsiderHeaders = { Authorization: `Bearer ${await frontToken(browser, outsider)}` };
  const root = `${API}/projects/${project}/revisions/${revision}/structures`;
  const addresses = {
    structure: [`${root}/${unknown}/nodes`, `${base}/nodes`],
    node: [
      `${base}/nodes/${unknown}/dependencies?field=task.duration`,
      `${base}/nodes/${node}/dependencies?field=task.duration`,
    ],
    row: [`${base}/rows/99999`, `${base}/rows/2`],
  } as const;
  for (const [object, [missing, existing]] of Object.entries(addresses)) {
    const absent = await calls.get(missing, { headers });
    const hidden = await calls.get(existing, { headers: outsiderHeaders });
    expect(absent.status(), `${object} that does not exist`).toBe(404);
    expect(hidden.status(), `${object} of a project not readable`).toBe(404);
    const [wanted, got] = [
      (await absent.json()) as { code: string },
      (await hidden.json()) as { code: string },
    ];
    expect(got.code, `${object}: the same refusal`).toBe(wanted.code);
  }

  // Inscrit comme contributeur, il le modifie.
  await inscribe(browser, calls, creator, reader, seeded.own);
  const created = await calls.post(`${base}/nodes`, {
    headers,
    data: { kind: "task", parent_id: null, task: { label: "Acceptée" } },
  });
  expect(created.status(), "POST nodes once inscribed").toBe(201);
});
