// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The home of a signed-in session (`/`), against the fake back and, tagged `@shared`, against the
 * service: it reads the projects (`listProjects`) and the readiness of the reference data
 * (`getReferenceReadiness`) the service serves since EP-04, and no longer renders « Introuvable »
 * for want of them (#1004).
 */
import { expect } from "@playwright/test";

import { inService, test } from "./mode";

test("the home of a signed-in session renders against the service: its title, the filter of its list, no note of the mock-up and neither « not found » nor a request for a session; it only renders, the filter being carried by the back and projects.spec.ts (US-0920/L2, #1004) @shared [WF-IHM-0120-A]", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");
  await expect(
    page.getByRole("main").getByRole("region", { name: "Filtre de la liste" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Introuvable" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Session requise" })).toHaveCount(0);
  await expect(page.getByRole("note")).toHaveCount(0);
});

// Against the service alone: the fake back grants one session, which reads the projects. The reader
// of the administration holds no permission of a project; that the list is not read is the unit
// test's, the request being the server's, which the browser does not see (#2915).
test("an account that reads no project lands on a home that says so and leads to the administration, without « Introuvable » [WF-IHM-0120-A] @shared @administration", async ({
  page,
}) => {
  test.skip(!inService, "the fake back grants a session that reads the projects");
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 1, name: "Aucun projet à ouvrir" }),
  ).toBeVisible();
  await expect(
    page.getByRole("main").getByRole("link", { name: "Gestion des utilisateurs" }),
  ).toHaveAttribute("href", "/admin/users");
  await expect(page.getByRole("heading", { name: "Introuvable" })).toHaveCount(0);
});
