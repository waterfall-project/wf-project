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

import { inscribe } from "../own-project";
import { seedPlanning } from "../planning-seed";
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

test.beforeAll(async ({ browser, playwright }) => {
  calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  administrator = await accountAdministrator(browser, calls);
  creator = await localAccount(browser, administrator);
  reader = await localAccount(browser, administrator);
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

  // The reader sees the planning unchanged, by the grid she cannot write.
  const unchanged = (await (await calls.get(`${base}/nodes`, { headers })).json()) as {
    items: unknown[];
  };
  expect(unchanged.items).toHaveLength(6);

  // Inscrit comme contributeur, il le modifie.
  await inscribe(browser, calls, creator, reader, seeded.own);
  const created = await calls.post(`${base}/nodes`, {
    headers,
    data: { kind: "task", parent_id: null, task: { label: "Acceptée" } },
  });
  expect(created.status(), "POST nodes once inscribed").toBe(201);
});
