// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { estimateBasis, onBasis } from "./workload-basis";

const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";

describe("the basis a link opens the workload on (#1069)", () => {
  it("adds the basis to an address that has no query, or to the query of its context [WF-DEV-0070-A]", () => {
    expect(onBasis("/projects/p/revisions/r/workload", "current_remaining")).toBe(
      "/projects/p/revisions/r/workload?basis=current_remaining",
    );
    expect(onBasis("/projects/p/revisions/r/workload?as_of=2026-03-16", "reference_budget")).toBe(
      "/projects/p/revisions/r/workload?as_of=2026-03-16&basis=reference_budget",
    );
    expect(onBasis(undefined, "current_remaining")).toBeUndefined();
  });

  it("opens the estimate of a project in progress or completed on its reference budget, a priced one on the remaining of the revision under way [WF-DEV-0070-A]", () => {
    expect(estimateBasis({ state: "in_progress", reference_revision_id: REFERENCE })).toBe(
      "reference_budget",
    );
    expect(estimateBasis({ state: "completed", reference_revision_id: REFERENCE })).toBe(
      "reference_budget",
    );
    expect(estimateBasis({ state: "pricing", reference_revision_id: null })).toBe(
      "current_remaining",
    );
  });

  it("never asks the reference budget of a project that has no reference revision, which the API refuses [WF-DEV-0070-A]", () => {
    expect(estimateBasis({ state: "in_progress", reference_revision_id: null })).toBe(
      "current_remaining",
    );
    expect(estimateBasis({ state: "in_progress" })).toBe("current_remaining");
  });
});
