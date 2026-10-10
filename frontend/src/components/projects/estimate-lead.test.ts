// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import type { Project } from "@/components/context/reading";
import { example } from "@/test/fixtures";

import { estimatedRevision, leadsToEstimate } from "./estimate-lead";

type Session = components["schemas"]["Session"];

const witness = example("project") as Project;

describe("where the deletion of a sub-project estimate lines bear leads", () => {
  it.each([
    ["session", "project", witness.current_revision_id],
    // No role, and so no permission to read the estimate.
    ["session_without_roles", "project", undefined],
    ["session", "project_without_current_revision", undefined],
  ])(
    "to the estimate of the revision in progress, read by the session (%s, %s)",
    (session, project, revision) => {
      expect(estimatedRevision(example(project) as Project, example(session) as Session)).toBe(
        revision,
      );
    },
  );

  it("to nowhere without a session", () => {
    expect(estimatedRevision(witness, undefined)).toBeUndefined();
  });

  it.each([
    [["subproject_without_estimate_lines"], true],
    [["subproject_without_estimate_lines", "project_not_terminal"], true],
    [["subproject_not_cited", "subproject_without_estimate_lines"], false],
    [["subproject_without_actual_costs", "subproject_without_estimate_lines"], false],
    [["subproject_without_actual_costs"], false],
    [["project_not_terminal"], false],
  ] as const)("when the passing of the lines alone lacks: %o → %s", (missing, leads) => {
    expect(leadsToEstimate(missing)).toBe(leads);
  });
});
