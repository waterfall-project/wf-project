// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { Project } from "@/components/context/reading";
import type { Revision } from "@/components/context/read-only";
import { example } from "@/test/fixtures";

import { importHref, importOffers } from "./offers";

const project = (name = "project") => example(name) as Project;
const revision = (name: string) => example(name) as Revision;

describe("the imports a project offers", () => {
  it("are the commands the server lists: the actual costs on the project, the rest on its current revision", () => {
    expect(importOffers(project(), revision("revision"))).toEqual({
      ms_project_schedule: { command: "edit_planning", is_available: true, missing_conditions: [] },
      estimate: { command: "edit_estimate", is_available: true, missing_conditions: [] },
      remaining: { command: "edit_remaining", is_available: true, missing_conditions: [] },
      actual_costs: { command: "import_actual_costs", is_available: true, missing_conditions: [] },
    });
  });

  it("leave out what the server does not list, and keep unavailable what it says so, with its conditions", () => {
    const offers = importOffers(project("project_completed"), revision("revision_estimator"));
    expect(offers.ms_project_schedule).toBeUndefined();
    expect(offers.remaining).toBeUndefined();
    expect(offers.estimate?.is_available).toBe(true);
    expect(offers.actual_costs).toEqual({
      command: "import_actual_costs",
      is_available: false,
      missing_conditions: ["project_not_terminal"],
    });
  });

  it("offer no import into a revision when the project has no current revision", () => {
    const offers = importOffers(project(), undefined);
    expect([offers.ms_project_schedule, offers.estimate, offers.remaining]).toEqual([
      undefined,
      undefined,
      undefined,
    ]);
    expect(offers.actual_costs?.is_available).toBe(true);
  });
});

describe("the address of the report of an import", () => {
  it("keeps the context of the screen, and names the import", () => {
    expect(importHref("/projects/p/exchanges?revision_id=r", "i")).toBe(
      "/projects/p/exchanges?revision_id=r&import=i",
    );
    expect(importHref("/projects/p/exchanges?import=old", "i")).toBe(
      "/projects/p/exchanges?import=i",
    );
    expect(importHref("/projects/p/exchanges", "i")).toBe("/projects/p/exchanges?import=i");
  });
});
