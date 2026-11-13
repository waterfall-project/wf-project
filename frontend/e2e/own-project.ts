// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project the account of the run creates in the service, for the paths that write: the account is
 * its project manager as its creator (WF-PRJ-0060), and no other path reads it. The witness is never
 * written by a path (`mode.ts`: the account of the run is not a project manager of PRJ-001, #2193).
 */
import { randomBytes } from "node:crypto";

import {
  type APIRequestContext,
  type Browser,
  expect,
  type Page,
  type Request,
  type Response,
  test,
} from "@playwright/test";

import type { components } from "../src/api/generated/schema";
import { openHydrated, WORKING } from "./hydration";
import { ADMINISTRATOR, API, frontToken, type LocalPerson } from "./service/realm";

type Schemas = components["schemas"];

/** What a path keeps of the project it created: the address of its screen, and its label. */
export interface OwnProject {
  readonly path: string;
  readonly label: string;
}

/** The address of the screen of a project, which the creation leads to. */
const PROJECT_SCREEN = /\/projects\/[0-9a-f-]{36}$/;

/**
 * Create a project from the home, as a user does, and stay on its screen. No project is opened on
 * the home, nothing witnesses the hydration: the creation is pressed again until React opens its
 * form, and never once it is open.
 */
export async function createOwnProject(page: Page, prefix: string): Promise<OwnProject> {
  const steps = new CreationSteps(page);
  try {
    await page.goto("/");
    steps.mark("home");
    const main = page.getByRole("main");
    const creation = page.getByRole("dialog", { name: "Créer un projet" });
    await expect(async () => {
      if (!(await creation.isVisible())) {
        await main.getByRole("button", { name: "Créer un projet" }).click();
      }
      await expect(creation).toBeVisible({ timeout: 1_000 });
    }).toPass({ timeout: WORKING });
    steps.mark("dialog");
    const label = `${prefix} ${randomBytes(4).toString("hex")}`;
    await creation.getByRole("textbox", { name: "Libellé" }).fill(label);
    steps.press();
    await creation.getByRole("button", { name: "Créer", exact: true }).click();
    try {
      await expect(page).toHaveURL(PROJECT_SCREEN, { timeout: WORKING });
    } catch (error) {
      // A creation refused — a 500 of the service, as the deadlock of the partitions was (#2940) —
      // keeps the address of the home: what the dialog says names the cause in the log. One read,
      // bounded and tolerant (a dialog closed meanwhile is no error), so the failure is delayed by
      // 1 s at most and keeps its own cause.
      steps.mark("address not reached");
      const said = await creation.textContent({ timeout: 1_000 }).catch(() => null);
      steps.tell(said ?? "the dialog closed");
      throw error;
    }
    steps.mark("address");
    return { path: new URL(page.url()).pathname, label };
  } finally {
    steps.report(prefix);
  }
}

/**
 * The steps of the creation of a project, timed in the browser (US-1890): the home loaded, the
 * dialog open, then, from the press of « Créer », the server action that creates the project
 * (`createProject`, asked and answered), the screen of the project the form leads to (its payload
 * asked, its headers answered, its body finished) and the address reached. Written in the log of the
 * run and in an annotation of the test, whether the creation passed or not — the slow path of the
 * guide measures before it corrects. An address missed is a refused creation (a deadlock, #2940),
 * not a slow one; see « Un parcours de bout en bout » in the guide.
 */
class CreationSteps {
  private readonly started = Date.now();
  private last = this.started;
  private pressed: number | undefined;
  private readonly done: string[] = [];
  private readonly network = new Map<string, number>();
  private said: string | undefined;
  private readonly onRequest = (request: Request): void => {
    this.note(request, "asked");
  };
  private readonly onResponse = (response: Response): void => {
    this.note(response.request(), "answered");
  };
  private readonly onFinished = (request: Request): void => {
    this.note(request, "finished");
  };
  private readonly onFailed = (request: Request): void => {
    // A request cancelled by a navigation is not a failure: only the others are named so.
    const cancelled = request.failure()?.errorText.includes("ERR_ABORTED") === true;
    this.note(request, cancelled ? "aborted" : "failed");
  };

  constructor(private readonly page: Page) {
    page.on("request", this.onRequest);
    page.on("response", this.onResponse);
    page.on("requestfinished", this.onFinished);
    page.on("requestfailed", this.onFailed);
  }

  /** A step reached: its duration since the one before. */
  mark(step: string): void {
    const now = Date.now();
    this.done.push(`${step} ${String(now - this.last)} ms`);
    this.last = now;
  }

  /** « Créer » about to be pressed: what follows is timed from it. */
  press(): void {
    this.pressed = Date.now();
    this.last = this.pressed;
  }

  /** What the dialog said when the address was not reached. */
  tell(said: string): void {
    this.said = said.replace(/\s+/g, " ").trim();
  }

  /** Write the steps reached, and when each request of the creation went, from the press. */
  report(prefix: string): void {
    this.page.off("request", this.onRequest);
    this.page.off("response", this.onResponse);
    this.page.off("requestfinished", this.onFinished);
    this.page.off("requestfailed", this.onFailed);
    const network = [...this.network].map(([step, at]) => `${step} +${String(at)} ms`);
    const measured =
      `${this.done.join(", ")}; from the press: ${network.join(", ") || "no request"}; ` +
      `total ${String(Date.now() - this.started)} ms` +
      (this.said === undefined ? "" : `; the dialog said: ${this.said}`);
    console.log(`Own project created (${prefix}): ${measured}`);
    test.info().annotations.push({ type: "own project", description: measured });
  }

  /**
   * The first time a request of the creation reaches an event, from the press. The screen is the one
   * asked once the action has answered: the links of the home to the projects it lists ask theirs
   * before, in advance.
   */
  private note(request: Request, event: string): void {
    if (this.pressed === undefined) {
      return;
    }
    const headers = request.headers();
    const action = request.method() === "POST" && headers["next-action"] !== undefined;
    const screen =
      this.network.has("action answered") &&
      headers.rsc === "1" &&
      PROJECT_SCREEN.test(new URL(request.url()).pathname);
    const step = `${action ? "action" : "screen"} ${event}`;
    if ((action || screen) && !this.network.has(step)) {
      this.network.set(step, Date.now() - this.pressed);
    }
  }
}

/**
 * Open a revision in progress on the project, as a user does from its revisions: the project goes to
 * pricing (WF-CYC-0090), and the address of the revision is reached.
 */
export async function openRevision(page: Page, own: OwnProject): Promise<void> {
  await openHydrated(page, `${own.path}/revisions`);
  await page
    .getByRole("main")
    .getByRole("region", { name: "Commandes" })
    .getByRole("button", { name: "Ouvrir une révision en cours" })
    .click();
  await expect(page).toHaveURL(/\?revision_id=[0-9a-f-]{36}$/, { timeout: WORKING });
}

/**
 * Write the contributors of a project by the API, under the token of its creator: she stays project
 * manager, and the other account is inscribed with the quality given. The screen of the contributors
 * proposes the accounts of the estimate alone (`listContributorSuggestions`), which a project just
 * created has none of.
 */
export async function inscribe(
  browser: Browser,
  calls: APIRequestContext,
  creator: LocalPerson,
  other: LocalPerson,
  own: OwnProject,
  kind: "contributor" | "project_manager" = "contributor",
): Promise<void> {
  const headers = { Authorization: `Bearer ${await frontToken(browser, creator)}` };
  const id = own.path.split("/").at(-1) ?? "";
  const read = await calls.get(`${API}/projects/${id}/contributors`, { headers });
  expect(read.status(), "GET contributors").toBe(200);
  const body = (await read.json()) as Schemas["ContributorList"];
  // A list read whole carries its counter; a null one is a filtered read, which the write refuses.
  if (typeof body.lock_version !== "number") {
    throw new Error("the contributors read whole carry no lock_version");
  }
  const written = await calls.put(`${API}/projects/${id}/contributors`, {
    headers,
    data: {
      contributors: [
        { user_id: creator.id, kind: "project_manager" },
        { user_id: other.id, kind },
      ],
      lock_version: body.lock_version,
    },
  });
  expect(written.status(), "PUT contributors").toBe(200);
}

/** A service of the organisation and a labour role of it, which a path employs. */
export interface EmployedService {
  readonly node: { readonly id: string; readonly label: string };
  readonly role: { readonly id: string; readonly label: string };
}

/**
 * The service and the labour role of the witness that every installation of the paths holds
 * (`fixtures/api`: the workshop of wiring and the cable fitter, active, whom no line employs). The
 * paths create nothing in the reference: a node or a role made here would stay in the installation
 * and change what the paths of the reference of the resources count (`reference-resources.spec.ts`).
 */
export function wiringService(): EmployedService {
  return {
    node: { id: "01926f3a-7c00-7000-8000-000000000472", label: "Atelier de câblage" },
    role: { id: "01926f3a-7c00-7000-8000-000000000454", label: "Monteur câbleur" },
  };
}

/** Attach an account to a node of the organisation, as the administrator does (WF-ADM-0030). */
export async function attachToService(
  browser: Browser,
  calls: APIRequestContext,
  account: LocalPerson,
  service: EmployedService,
): Promise<void> {
  const headers = { Authorization: `Bearer ${await frontToken(browser, ADMINISTRATOR)}` };
  const read = await calls.get(`${API}/users/${account.id}`, { headers });
  expect(read.status(), "GET user").toBe(200);
  const { lock_version } = (await read.json()) as Schemas["User"];
  const attached = await calls.patch(`${API}/users/${account.id}`, {
    headers,
    data: { org_node_id: service.node.id, lock_version },
  });
  expect(attached.status(), "PATCH user").toBe(200);
}

/**
 * Give an account a family name of its own, as the administrator does: the local accounts all bear
 * the same name, and a screen that lists the accounts of a service cannot tell them apart. The
 * account returned is the same, under its new display name (first name, then last name).
 */
export async function renameAccount(
  browser: Browser,
  calls: APIRequestContext,
  account: LocalPerson,
): Promise<LocalPerson> {
  const headers = { Authorization: `Bearer ${await frontToken(browser, ADMINISTRATOR)}` };
  const read = await calls.get(`${API}/users/${account.id}`, { headers });
  expect(read.status(), "GET user").toBe(200);
  const { lock_version, first_name, last_name } = (await read.json()) as Schemas["User"];
  if (!first_name || !last_name) {
    throw new Error("the account read has no first name or no last name");
  }
  const renamed = `${last_name}-${randomBytes(4).toString("hex")}`;
  const written = await calls.patch(`${API}/users/${account.id}`, {
    headers,
    data: { last_name: renamed, lock_version },
  });
  expect(written.status(), "PATCH user name").toBe(200);
  return { ...account, name: `${first_name} ${renamed}` };
}

/**
 * Create a labour line of the role under a task of the main structure of a revision, by the API,
 * under the token of the creator of the project: the line the estimate employs the role by.
 */
export async function employRole(
  calls: APIRequestContext,
  headers: { readonly Authorization: string },
  revision: { project: string; revision: string; structure: string },
  task: string,
  service: EmployedService,
): Promise<void> {
  const base = `${API}/projects/${revision.project}/revisions/${revision.revision}/structures/${revision.structure}`;
  const line = await calls.post(`${base}/nodes`, {
    headers,
    data: {
      kind: "estimate_line",
      parent_id: task,
      estimate_line: { quantity: "1", resource_role_id: service.role.id, hours: "10" },
    },
  });
  expect(line.status(), "POST nodes estimate line").toBe(201);
}
