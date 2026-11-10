// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/workload`;
const ORG_NODE = "01926f3a-7c00-7000-8000-000000000471";

// The service serves the workload; the estimate it leads from and the lines that load it come with
// the grid of the estimate (US-1560) and the witness (US-1570): the paths that need them stay on
// the fake back until then.
const BEFORE_THE_ESTIMATE = "US-1560 serves the estimate, US-1570 the lines of the witness";

test.use({ colorScheme: "light" });

test("leads from the estimate to the workload on the reference budget, drawn in stacked bars, the capacity in its table, which a node of organisation filters at the server's @shared [WF-DEV-0070-A]", async ({
  page,
}) => {
  test.skip(inService, BEFORE_THE_ESTIMATE);
  await compile(page.request, SCREEN);
  await openHydrated(page, `${ESTIMATE}?as_of=2026-03-16`);
  await page.getByRole("main").getByRole("link", { name: "Plan de charge" }).click();
  // The arrival on the workload keeps the bound of a screen of grid (`WORKING`), as the paths of
  // the screens follow a link, because the measure of the departure (`departure.spec.ts`, US-0800,
  // #1230) covers neither the departure from the estimate nor the arrival on the workload.
  await expect(page).toHaveURL(`${SCREEN}?as_of=2026-03-16&basis=reference_budget`, {
    timeout: WORKING,
  });
  await expect(page.getByRole("heading", { level: 1, name: "Plan de charge" })).toBeVisible({
    timeout: WORKING,
  });
  const region = page.getByRole("region", { name: "Plan de charge du projet" });
  const figure = region.getByRole("figure", { name: "Charge par rôle et par mois" });
  await expect(
    figure.getByRole("img", { name: /^Barres empilées de la charge/ }).locator("svg"),
  ).toBeVisible();
  // The capacity of each role in the table of the values, in regard of its load; no ratio of the
  // load to it in the plan of a project (#375, option b) [WF-DEV-0070-A].
  await figure.getByText("Valeurs du graphique").click();
  await expect(figure.getByRole("table").getByRole("columnheader")).toHaveText([
    "Rôle",
    "Mois",
    "Charge (h)",
    "Capacité (h par mois)",
    "Zone",
  ]);
  await region.getByLabel("Nœud d’organisation").selectOption(ORG_NODE);
  await region.getByRole("button", { name: "Afficher" }).click();
  // The choice is an address, the context kept: the server asks the API, the front filters nothing.
  await expect(page).toHaveURL(
    new RegExp(
      `^[^?]*${SCREEN}\\?as_of=2026-03-16&basis=reference_budget&.*org_node_id=${ORG_NODE}$`,
    ),
  );
});

// That the server filters the load on the node chosen is checked against the service once the lines
// of the witness exist to be filtered (US-1570); here the context is kept and the node read again.
test("reads the workload of the revision under way from its address, the context kept, the node of organisation chosen read again @shared [WF-DEV-0070-A]", async ({
  page,
}) => {
  await openHydrated(page, `${SCREEN}?as_of=2026-03-16`);
  const region = page.getByRole("region", { name: "Plan de charge du projet" });
  await expect(page.getByRole("heading", { level: 1, name: "Plan de charge" })).toBeVisible({
    timeout: WORKING,
  });
  await expect(region.getByText(/^Base : /)).toBeVisible();
  await region.getByLabel("Nœud d’organisation").selectOption(ORG_NODE);
  await region.getByRole("button", { name: "Afficher" }).click();
  await expect(page).toHaveURL(new RegExp(`as_of=2026-03-16&.*org_node_id=${ORG_NODE}$`));
  // The node is read again by the server, which names it: the reading follows the filter.
  await expect(region.getByLabel("Nœud d’organisation")).toHaveValue(ORG_NODE);
  await expect(region.getByText(/^Base : /)).toBeVisible();
});

test("exports the workload, at the keyboard, as a PNG image drawn on a canvas, named after the project @shared [WF-IHM-0130-A]", async ({
  page,
}) => {
  test.skip(inService, BEFORE_THE_ESTIMATE);
  await openHydrated(page, SCREEN);
  const figure = page.getByRole("figure", { name: "Charge par rôle et par mois" });
  const command = figure.getByRole("button", { name: "Exporter en PNG" });
  await command.focus();
  await expect(command).toBeFocused();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.keyboard.press("Enter"),
  ]);
  expect(download.suggestedFilename()).toBe("plan-de-charge-PRJ-001.png");
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(chunk as Buffer);
  }
  const image = Buffer.concat(chunks);
  // The signature of a PNG, then the width and the height of its header: an image of its own
  // size, twice as dense as the screen, whatever the size of the window.
  expect(image.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
  expect([image.readUInt32BE(16), image.readUInt32BE(20)]).toEqual([2560, 1440]);
  // The instance out of the screen is gone with its canvas.
  await expect(page.locator("canvas")).toHaveCount(0);
});

test("offers the revision under way and only the other bases the project admits, the marked revision chosen with its basis alone @shared [WF-DEV-0070-A]", async ({
  page,
}) => {
  await openHydrated(page, `${SCREEN}?basis=current_remaining`);
  const region = page.getByRole("region", { name: "Plan de charge du projet" });
  const bases = await region
    .getByLabel("Base", { exact: true })
    .locator("option")
    .evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value));
  // A basis the project does not admit is absent, never offered to be refused (409, 422). The
  // witness PRJ-001 has a reference revision (the offer 100, designated by the loader) and marked
  // ones (100, 101), as the fake back's project does: both offer the three bases, the reference
  // budget first.
  expect(bases).toEqual(["reference_budget", "marked_remaining", "current_remaining"]);
  await expect(region.getByLabel("Révision marquée")).toHaveCount(1);
});
