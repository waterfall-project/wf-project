// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/indicators`;

// The first series of a chart in the token `--chart-1`, as the browser resolves it in each mode.
const SERIES_LIGHT = "rgb(2, 112, 179)";
const SERIES_DARK = "rgb(17, 149, 225)";

test.use({ colorScheme: "light" });

test("draws the evolution of an index in SVG, an image described in a sentence, its values in a table [WF-IHM-0100-A]", async ({
  page,
}) => {
  await page.goto(SCREEN);
  await expect(page.getByRole("heading", { level: 1, name: "Indicateurs projets" })).toBeVisible();
  const cost = page.getByRole("img", { name: /^Courbes de l’indice de coût du projet/ });
  await expect(cost.locator("svg")).toBeVisible();
  // The thresholds of the reference, drawn by a series of their own.
  await expect(cost.locator("svg text", { hasText: "Seuil de vigilance" })).toBeAttached();
  await expect(cost.locator("svg text", { hasText: "Seuil d’alerte" })).toBeAttached();
  const figure = page.getByRole("figure", { name: "Évolution de l’indice de coût" });
  await figure.getByText("Valeurs du graphique").click();
  const row = figure.getByRole("row", { name: /^Projet entier Révision en cours/ });
  await row.scrollIntoViewIfNeeded();
  await expect(row).toBeInViewport();
  // The date of the evolution, under the caption of its figure.
  await expect(figure.getByText(/^Calculé le/)).toBeVisible();
});

test("paints its series with the tokens of the charter, drawn again when the account forces the dark mode", async ({
  page,
}) => {
  await page.goto(SCREEN);
  const cost = page.getByRole("img", { name: /^Courbes de l’indice de coût du projet/ });
  await expect(cost.locator(`path[stroke="${SERIES_LIGHT}"]`).first()).toBeAttached();
  // The attribute the root layout sets for an account that chose `dark`.
  await page.locator("html").evaluate((html) => {
    html.setAttribute("data-theme", "dark");
  });
  await expect(cost.locator(`path[stroke="${SERIES_DARK}"]`).first()).toBeAttached();
  await expect(cost.locator(`path[stroke="${SERIES_LIGHT}"]`)).toHaveCount(0);
});

test("names each curve at its end, two names ending close together drawn apart, their letters never overlapping", async ({
  page,
}) => {
  await page.goto(SCREEN);
  const schedule = page.getByRole("img", { name: /^Courbes de l’indice de délai du projet/ });
  // The whole project and what belongs to no sub-project end close on the current day, at
  // 0.9879 and 1.
  const project = schedule.locator("svg text", { hasText: /^Projet entier$/ });
  const unassigned = schedule.locator("svg text", { hasText: /^Hors sous-projet$/ });
  await expect(project).toBeAttached();
  await expect(unassigned).toBeAttached();
  // The baselines of the two names are at least the size of their font apart: their letters
  // do not overlap. ECharts writes where it places a name in its transform.
  const placed = async (name: typeof project) => {
    const [transform, size] = await name.evaluate((text) => [
      text.getAttribute("transform") ?? "",
      getComputedStyle(text).fontSize,
    ]);
    const baseline = /translate\([\d.]+ ([\d.]+)\)/.exec(transform)?.[1];
    return { baseline: Number(baseline), size: Number.parseFloat(size) };
  };
  const [a, b] = await Promise.all([placed(project), placed(unassigned)]);
  expect(Math.abs(a.baseline - b.baseline)).toBeGreaterThanOrEqual(Math.max(a.size, b.size));
});

test("exports a curve, at the keyboard, as a PNG image drawn on a canvas, named after the project", async ({
  page,
}) => {
  await page.goto(SCREEN);
  const figure = page.getByRole("figure", { name: "Diagramme temps/temps" });
  const command = figure.getByRole("button", { name: "Exporter en PNG" });
  await command.focus();
  await expect(command).toBeFocused();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.keyboard.press("Enter"),
  ]);
  expect(download.suggestedFilename()).toBe("suivi-des-jalons-PRJ-001.png");
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

test("draws the cumulative costs, and shifts them by the payment delays at the server's", async ({
  page,
}) => {
  await page.goto(SCREEN);
  await expect(page.getByRole("figure", { name: "Courbe en S" }).locator("svg")).toBeVisible();
  await page.getByRole("link", { name: "Décaler des délais de paiement" }).click();
  await expect(page).toHaveURL(/payment_delays=true/);
});
