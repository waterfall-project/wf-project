// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accounts of the measure of the journey of the grids (US-2210): one for each user, made by the
 * preparation of the measure through the operations of the contract — never by an `INSERT` —, as an
 * administrator and a project manager would, before anything is measured.
 *
 * The administrator of the installation, whom the bootstrap made (`make measure` gives the link of
 * its password, `E2E_INSTALLATION_LINK`, empty once set), creates each account (`createUser`),
 * gives its link (`createPasswordSetupLink`), whose page sets its password, and its roles
 * (`setUserAccessRoles`): « Manager », which reads every project, and « Chef de projet », which
 * writes them — the account of `e2e/mode.ts`.
 *
 * A user of the measure writes on PRJ-001 — a label, a duration —, which only its contributors may
 * do, and only a project manager of the project registers one (`setContributors`, WF-PRJ-0060). The
 * project managers of the witness have no password: the witness creates its accounts without the
 * identity provider. The contract leaves one entry to a non-contributor: when no project manager of
 * the project has an active account, the holder of the settings of the projects and of « voir tous
 * les projets » — the first user of the measure — registers one. So the administrator deactivates
 * the project managers of the witness (`setUserActivation`), the first user registers every user of
 * the measure as a project manager beside the contributors of the witness, and the administrator
 * reactivates them, whatever happened meanwhile. The witness keeps its contributors, with the users
 * of the measure beside them; a measure starts from a witness freshly loaded.
 */
import { type APIRequestContext, type Browser, expect } from "@playwright/test";

import type { components } from "../../src/api/generated/schema";
import {
  accountAdministrator,
  ADMINISTRATOR,
  API,
  expectPasswordSet,
  frontToken,
  LOCAL_PASSWORD,
  localAccount,
  type LocalPerson,
  openLink,
  setPassword,
} from "../service/realm";

type Schemas = components["schemas"];

/** The predefined roles of a user of the measure, which every installation holds (WF-EXP-0020). */
const ROLES = ["Manager", "Chef de projet"] as const;

/**
 * Set the password of the administrator of the installation by the link of the bootstrap, unless
 * an earlier run on the platform has: the link is empty then, and the password the paths give it.
 */
export async function administratorReady(browser: Browser): Promise<void> {
  expect(ADMINISTRATOR.email, "E2E_ADMIN_EMAIL, as make measure gives it").not.toBe("");
  const link = process.env.E2E_INSTALLATION_LINK ?? "";
  if (link === "") {
    return;
  }
  const page = await browser.newPage({ locale: "fr-FR", ignoreHTTPSErrors: true });
  try {
    await openLink(page, link);
    await setPassword(page, LOCAL_PASSWORD);
    await expectPasswordSet(page);
  } finally {
    await page.close();
  }
}

/** The API as an account calls it, by its token. */
function calling(request: APIRequestContext, token: string) {
  const headers = { Authorization: `Bearer ${token}` };
  return {
    read: async <T>(path: string): Promise<T> => {
      const answer = await request.get(`${API}${path}`, { headers });
      expect(answer.status(), `GET ${path}`).toBe(200);
      return (await answer.json()) as T;
    },
    put: async <T>(path: string, data: unknown): Promise<T> => {
      const answer = await request.put(`${API}${path}`, { headers, data });
      expect(answer.status(), `PUT ${path}`).toBe(200);
      return (await answer.json()) as T;
    },
  };
}

/** The accounts of the measure: the users who play the journey, and the one that asks `getMe`. */
export interface MeasureAccounts {
  /** Each with its roles; the first holds the settings of projects. */
  readonly users: readonly LocalPerson[];
  /**
   * The account of the client of `getMe`: without any role, never a contributor, it plays no
   * journey, and its requests, which the log of the API writes under its own actor, enter no step.
   */
  readonly probe: LocalPerson;
}

/** Make the users of the measure, each with its roles, and the account of the client of `getMe`. */
export async function measureUsers(
  browser: Browser,
  request: APIRequestContext,
  count: number,
): Promise<MeasureAccounts> {
  const administrator = await accountAdministrator(browser, request);
  const users: LocalPerson[] = [];
  for (let made = 0; made < count; made += 1) {
    const user = await localAccount(browser, administrator);
    await administrator.giveAlso(
      user.id,
      ROLES.map((role) => [role, []] as const),
    );
    users.push(user);
  }
  return { users, probe: await localAccount(browser, administrator) };
}

/** Deactivate or reactivate an account, as the administrator, at the version read. */
async function setActive(
  administrator: ReturnType<typeof calling>,
  id: string,
  active: boolean,
): Promise<void> {
  const { lock_version: version } = await administrator.read<Schemas["User"]>(`/users/${id}`);
  const write: Schemas["UserActivationWrite"] = { is_active: active, lock_version: version };
  await administrator.put<Schemas["User"]>(`/users/${id}/activation`, write);
}

/**
 * Register the users of the measure as project managers of a project, beside its contributors, by
 * the one entry the contract leaves a non-contributor: its active project managers deactivated for
 * the time of the registration, then reactivated.
 */
export async function contributorsOf(
  browser: Browser,
  request: APIRequestContext,
  project: string,
  users: readonly LocalPerson[],
): Promise<void> {
  const [rescuer] = users;
  expect(rescuer, "a user of the measure").toBeDefined();
  const administrator = calling(request, await frontToken(browser, ADMINISTRATOR));
  const first = calling(request, await frontToken(browser, rescuer ?? ADMINISTRATOR));
  const path = `/projects/${project}/contributors`;
  const before = await first.read<Schemas["ContributorList"]>(path);
  const managers = before.items
    .filter((contributor) => contributor.kind === "project_manager" && contributor.is_active)
    .map((contributor) => contributor.user_id);
  for (const manager of managers) {
    await setActive(administrator, manager, false);
  }
  try {
    const read = await first.read<Schemas["ContributorList"]>(path);
    // A reading of the whole list carries its version, which the write sends back.
    expect(read.lock_version, "the version of the list of contributors").not.toBeNull();
    const registered = new Set(read.items.map((contributor) => contributor.user_id));
    const write: Schemas["ContributorsWrite"] = {
      contributors: [
        ...read.items.map(({ user_id: id, kind }) => ({ user_id: id, kind })),
        ...users
          .filter((user) => !registered.has(user.id))
          .map((user) => ({ user_id: user.id, kind: "project_manager" as const })),
      ],
      lock_version: read.lock_version ?? 0,
    };
    await first.put<Schemas["ContributorList"]>(path, write);
  } finally {
    await reactivated(administrator, managers);
  }
}

/**
 * Reactivate the project managers of the witness, every one though one fails: the first failure is
 * raised once all were tried, and a project manager left deactivated says which.
 */
async function reactivated(
  administrator: ReturnType<typeof calling>,
  managers: readonly string[],
): Promise<void> {
  const settled = await Promise.allSettled(
    managers.map((manager) => setActive(administrator, manager, true)),
  );
  const failed = managers.flatMap((manager, index) => {
    const outcome = settled[index];
    return outcome?.status === "rejected" ? [{ manager, reason: outcome.reason as unknown }] : [];
  });
  const [first] = failed;
  if (first !== undefined) {
    const left = failed.map(({ manager }) => manager).join(", ");
    throw new Error(`project managers of the witness left deactivated: ${left}`, {
      cause: first.reason,
    });
  }
}

/** How old the token of the user of the browser may grow before it is asked again. */
const TOKEN_RENEWED_AFTER = 4 * 60_000;

/** The token of an account, asked again once it grows old. */
export function renewedToken(browser: Browser, person: LocalPerson): () => Promise<string> {
  let kept: { token: string; obtained: number } | undefined;
  return async () => {
    if (kept === undefined || Date.now() - kept.obtained > TOKEN_RENEWED_AFTER) {
      kept = { token: await frontToken(browser, person), obtained: Date.now() };
    }
    return kept.token;
  };
}
