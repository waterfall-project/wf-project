// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { Project } from "@/components/context/reading";
import type { Revision } from "@/components/context/read-only";
import { example } from "@/test/fixtures";

import { exportOffers, importHref, importOffers } from "./offers";

const project = (name = "project") => example(name) as Project;
const revision = (name: string) => example(name) as Revision;

/** A command the server lists available. */
const available = (command: string) => ({ command, is_available: true, missing_conditions: [] });

describe("the imports a project offers", () => {
  it("are the commands of the project the server lists, one for each kind of file", () => {
    expect(importOffers(project())).toEqual({
      ms_project_schedule: available("import_planning"),
      estimate: available("import_estimate"),
      remaining: available("import_remaining"),
      actual_costs: available("import_actual_costs"),
    });
  });

  it("keep unavailable what the server says so, with its conditions", () => {
    const offers = importOffers(project("project_completed"));
    expect(offers.estimate).toEqual({
      command: "import_estimate",
      is_available: false,
      missing_conditions: ["project_not_terminal"],
    });
    expect(offers.actual_costs?.missing_conditions).toEqual(["project_not_terminal"]);
  });

  it("are offered without a current revision, which the import creates, and name the permission to create it when it lacks", () => {
    expect(importOffers(project("project_pricing")).ms_project_schedule).toEqual(
      available("import_planning"),
    );
    const offers = importOffers(project("project_pricing_estimator"));
    expect(offers).toEqual({
      ms_project_schedule: undefined,
      estimate: {
        command: "import_estimate",
        is_available: false,
        missing_conditions: ["can_create_revision"],
      },
      remaining: undefined,
      actual_costs: undefined,
    });
  });
});

describe("the exports a revision offers", () => {
  it("are the commands of the revision read the server lists, one for each kind of file", () => {
    expect(exportOffers(revision("revision"))).toEqual({
      ms_project_schedule: available("export_planning"),
      estimate: available("export_estimate"),
      remaining: available("export_remaining"),
      task_tree_image: available("export_task_tree_image"),
    });
    expect(exportOffers(revision("revision_marked")).estimate?.is_available).toBe(true);
  });

  it("leave out what the server does not list, and are none without a revision", () => {
    expect(exportOffers(revision("revision_estimator"))).toEqual({
      ms_project_schedule: undefined,
      estimate: available("export_estimate"),
      remaining: undefined,
      task_tree_image: undefined,
    });
    for (const offers of [exportOffers(revision("revision_reader")), exportOffers(undefined)]) {
      expect(Object.values(offers)).toEqual([undefined, undefined, undefined, undefined]);
    }
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
