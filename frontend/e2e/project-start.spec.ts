// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type APIRequestContext, type Browser, expect, type Page } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { createOwnProject, type OwnProject } from "./own-project";
import { API, frontToken, type LocalPerson } from "./service/realm";

// The start of the planning of a project (US-0490/L3, #1058, L4 #1358), against the fake back and,
// tagged `@shared`, against the service (US-1460), which serves the work breakdown (US-0950), the
// revision in progress and the generation of the skeleton: it plays them on a project the run creates.
//
// Against the fake back, as far as a fake back that keeps no state lets a journey go. It serves the
// project of the witness, its revision in progress with its thousand tasks, whatever the address but
// one: there the encart cannot be reached, and the journeys that need a service that remembers —
// create, work breakdown, generate, planning; create, drop a file, report, planning — wait for it
// (#1350). The project created today is served at its own address, with no revision: its encart is
// reached, and its generation played to the planning. The rest is proved on the examples of the
// contract by the tests of the components (`project-start.dom.test.tsx`) and of the pages
// (`page.test.tsx`, `screens.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";

// What the fake back does not replay: it keeps nothing of the work breakdown it is given.
const FAKE_BACK_FORGETS = "the fake back keeps nothing of the work breakdown it is given";

// Enter a lot in the work breakdown of a project the run created, on the screen of its start, as a
// user does: the structure the skeleton is generated from.
async function enterLot(page: Page, own: OwnProject, label: string): Promise<void> {
  await openHydrated(page, `${own.path}/settings?start=skeleton`);
  const section = page.getByRole("region", { name: "Lotissement" });
  await expect(section).toBeVisible({ timeout: WORKING });
  await section.getByRole("button", { name: "Nouveau lot" }).click();
  const form = page.getByRole("dialog", { name: "Nouveau lot" });
  await form.getByRole("textbox", { name: "Libellé" }).fill(label);
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toHaveCount(0);
}

// Generate the skeleton of the work breakdown of a project the run created, by the API, under the
// token of its creator: the revision opened, then the skeleton written on it. The structure bears
// tasks then, and the planning is not shown (the test proves the offer of the work breakdown, not the
// journey that leads to the grid).
async function generateByTheApi(
  browser: Browser,
  calls: APIRequestContext,
  creator: LocalPerson,
  own: OwnProject,
): Promise<void> {
  const headers = { Authorization: `Bearer ${await frontToken(browser, creator)}` };
  const project = own.path.split("/").at(-1) ?? "";
  const opened = await calls.post(`${API}/projects/${project}/revisions`, {
    headers,
    data: { apply_rate_update: false },
  });
  expect(opened.status(), "POST revisions").toBe(201);
  const revision = (await opened.json()) as { revision_id: string };
  const generated = await calls.post(
    `${API}/projects/${project}/revisions/${revision.revision_id}/skeleton`,
    { headers },
  );
  expect(generated.status(), "POST skeleton").toBe(201);
}

test("leads a project with a revision in progress to its planning, where no encart is offered @shared [WF-PRJ-0030-A]", async ({
  page,
}) => {
  // `goto`, not `openHydrated`: the page leads elsewhere, and the probe of hydration would run on a
  // document that is being left.
  await page.goto(`/projects/${PROJECT}`);
  // The project of the witness has a revision in progress: its page leads to the planning of it
  // (US-0720), where the encart is not by construction. The proof is the address reached, that of
  // the revision, then the planning shown without the encart; the encart that could be missing on
  // the page of a project is reached, on the project with no revision, by the last test below.
  await expect(page).toHaveURL(new RegExp(`/projects/${PROJECT}/revisions/[^/]+/planning$`), {
    timeout: WORKING,
  });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: WORKING });
  await expect(page.getByRole("region", { name: "Démarrer le projet" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Démarrer le projet" })).toHaveCount(0);
});

test("offers « Engendrer le planning » on the work breakdown reached from the encart, unavailable once the structure bears a task, naming the condition @shared [WF-PRJ-0030-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.slow();
  // The witness of the fake back bears tasks; the service has none of them before its filler
  // (#2340): the project the run created bears the tasks the generation wrote.
  let address = `/projects/${PROJECT}/settings?start=skeleton`;
  if (inService) {
    if (manager === undefined) {
      throw new Error("the manager of the worker is made against the service");
    }
    const own = await createOwnProject(page, "Squelette");
    await enterLot(page, own, "Armoires");
    await generateByTheApi(browser, request, manager, own);
    address = `${own.path}/settings?start=skeleton`;
  }
  await openHydrated(page, address);
  const section = page.getByRole("region", { name: "Engendrer le planning" });
  await expect(section).toBeVisible({ timeout: WORKING });
  const generate = section.getByRole("button", { name: "Engendrer le planning" });
  await expect(generate).toHaveAttribute("aria-disabled", "true");
  await expect(generate).toHaveAccessibleDescription(
    /Condition non remplie\s: .*structure principale sans aucune tâche/,
  );

  // Pressed, from the keyboard as from the pointer, it asks nothing and leads nowhere.
  const sent: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET") {
      sent.push(`${request.method()} ${request.url()}`);
    }
  });
  await generate.focus();
  await page.keyboard.press("Enter");
  // `force`: the button is aria-disabled, not disabled, and Playwright waits for an enabled one.
  await generate.click({ force: true });
  await expect(page).toHaveURL(/\/settings\?start=skeleton$/);
  expect(sent).toEqual([]);
});

test("offers no « Engendrer le planning » on the work breakdown when it is not asked for and unavailable @shared [WF-PRJ-0030-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/settings`);
  await expect(page.getByRole("region", { name: "Lotissement" })).toBeVisible({ timeout: WORKING });
  await expect(page.getByRole("button", { name: "Engendrer le planning" })).toHaveCount(0);
});

// The project created today, which the fake back serves at its own address with no revision (US-0490/L4,
// #1358): `createRevision` answers the revision 103, `generatePlanningSkeleton` the skeleton generated.
const CREATED = "01926f3a-7c00-7000-8000-000000000003";
const OPENED = "01926f3a-7c00-7000-8000-000000000103";

test("starts the planning of the project created from its encart: the work breakdown, then « Engendrer le planning » opens the revision and generates @shared [WF-PRJ-0030-A]", async ({
  page,
}) => {
  test.slow();
  // The fake back serves a project of its own for the start; the service, the project the run creates.
  let path = `/projects/${CREATED}`;
  let planning = new RegExp(`/revisions/${OPENED}/planning`);
  if (inService) {
    const own = await createOwnProject(page, "Démarrage");
    await enterLot(page, own, "Armoires");
    path = own.path;
    planning = new RegExp(`${own.path}/revisions/[^/]+/planning`);
  }
  // A proof of the fake back alone before `openHydrated` (the compiled route must exist before the page
  // opens): the service compiles nothing. The encart offers the import of a schedule to both, since the
  // service lists `import_planning` (US-1430).
  if (!inService) {
    await compile(
      page.request,
      `${path}/settings?start=skeleton`,
      `${path}/revisions/${OPENED}/planning`,
    );
  }
  await openHydrated(page, path);
  const encart = page.getByRole("region", { name: "Démarrer le projet" });
  await expect(encart).toBeVisible({ timeout: WORKING });
  await expect(
    encart.getByRole("button", { name: "Importer un fichier MS Project" }),
  ).toBeVisible();
  await encart.getByRole("link", { name: "Planning automatique depuis le lotissement" }).click();
  await expect(page).toHaveURL(/\/settings\?start=skeleton$/, { timeout: WORKING });
  const generate = page
    .getByRole("region", { name: "Engendrer le planning" })
    .getByRole("button", { name: "Engendrer le planning" });
  await expect(generate).not.toHaveAttribute("aria-disabled", "true", { timeout: WORKING });
  await generate.click();
  await expect(page).toHaveURL(planning, { timeout: WORKING });
});

test("enters the work breakdown of a project created on the screen of its start, kept by the service and read anew @shared [WF-PRJ-0020-A]", async ({
  page,
}) => {
  test.skip(!inService, FAKE_BACK_FORGETS);
  test.slow();
  const own = await createOwnProject(page, "Démarrage");
  await enterLot(page, own, "Armoires");
  // The work breakdown the service kept, read anew.
  await openHydrated(page, `${own.path}/settings?start=skeleton`);
  await expect(
    page
      .getByRole("region", { name: "Lotissement" })
      .getByRole("treegrid", { name: "Lotissement" })
      .getByText("Armoires", { exact: true }),
  ).toBeVisible({ timeout: WORKING });
});
