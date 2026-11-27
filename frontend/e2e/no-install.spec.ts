// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * « Aucune fonction n'exige une installation sur le poste » (WF-CMP-0010-A, US-0290): every path of
 * the part `browsers` opens a context of its own — a profile with no extension, no plug-in, no
 * installed application — in each browser of the specification, and the front asks nothing of the
 * workstation there: no application to install (no manifest of web application, no service worker
 * that would keep it), no embedded plug-in object, nothing downloaded of itself.
 */
import { expect } from "@playwright/test";

import { openHydrated } from "./hydration";
import { test } from "./mode";

const REVISION =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102";

test("asks nothing to install on the workstation, in a bare profile of the browser @browsers [WF-CMP-0010-A]", async ({
  page,
}) => {
  const downloads: string[] = [];
  page.on("download", (download) => downloads.push(download.suggestedFilename()));
  await openHydrated(page, `${REVISION}/indicators`);
  await expect(page.getByRole("heading", { level: 1, name: "Indicateurs projets" })).toBeVisible();
  const document_ = await page.evaluate(() => ({
    manifests: document.querySelectorAll("link[rel~='manifest']").length,
    plugins: document.querySelectorAll("object, embed, applet").length,
    controlled: "serviceWorker" in navigator && navigator.serviceWorker.controller !== null,
  }));
  expect(document_).toEqual({ manifests: 0, plugins: 0, controlled: false });
  await expect
    .poll(() =>
      page.evaluate(async () =>
        "serviceWorker" in navigator
          ? (await navigator.serviceWorker.getRegistrations()).length
          : 0,
      ),
    )
    .toBe(0);
  expect(downloads).toEqual([]);
});
