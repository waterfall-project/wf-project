// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated } from "./hydration";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/workload`;
const ORG_NODE = "01926f3a-7c00-7000-8000-000000000471";

test.use({ colorScheme: "light" });

test("leads from the estimate to the workload, drawn in bars, which a node of organisation filters at the server's", async ({
  page,
}) => {
  await compile(page.request, SCREEN);
  await openHydrated(page, `${ESTIMATE}?as_of=2026-03-16`);
  await page.getByRole("link", { name: "Plan de charge" }).click();
  await expect(page).toHaveURL(`${SCREEN}?as_of=2026-03-16`);
  // The five seconds of an assertion, which the screen overran once under load: measures in #500.
  await expect(page.getByRole("heading", { level: 1, name: "Plan de charge" })).toBeVisible();
  const region = page.getByRole("region", { name: "Plan de charge du projet" });
  const figure = region.getByRole("figure", { name: "Charge par rôle et par mois" });
  await expect(
    figure.getByRole("img", { name: /^Barres de la charge/ }).locator("svg"),
  ).toBeVisible();
  await region.getByLabel("Nœud d’organisation").selectOption(ORG_NODE);
  await region.getByRole("button", { name: "Afficher" }).click();
  // The choice is an address, the context kept: the server asks the API, the front filters nothing.
  await expect(page).toHaveURL(
    new RegExp(
      `^[^?]*${SCREEN}\\?as_of=2026-03-16&basis=current_remaining&.*org_node_id=${ORG_NODE}$`,
    ),
  );
});

test("exports the workload, at the keyboard, as a PNG image drawn on a canvas, named after the project [WF-IHM-0130-A]", async ({
  page,
}) => {
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
