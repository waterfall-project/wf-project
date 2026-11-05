// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { createsFirstRevision, openedRevision } from "./opened-revision";

const MARKED = [
  { revision_id: "newest", marked_at: null },
  { revision_id: "last-marked", marked_at: "2026-02-01T09:00:00Z" },
  { revision_id: "older", marked_at: "2025-12-15T16:00:00Z" },
];

describe("the revision a project opens on [WF-IHM-0010-A]", () => {
  it("is the one in progress, else the reference, else the last marked", () => {
    const none = { current_revision_id: null, reference_revision_id: null };
    expect(openedRevision({ ...none, current_revision_id: "c" }, MARKED)).toBe("c");
    expect(openedRevision({ ...none, reference_revision_id: "r" }, MARKED)).toBe("r");
    expect(openedRevision(none, MARKED)).toBe("last-marked");
  });

  it("is none for a project that lists no revision, and none when nothing is marked", () => {
    const none = { current_revision_id: null, reference_revision_id: null };
    expect(openedRevision({ ...none, current_revision_id: "c" }, [])).toBeUndefined();
    expect(openedRevision(none, MARKED.slice(0, 1))).toBeUndefined();
  });
});

describe("the import that creates the first revision", () => {
  it("writes in no revision yet, and its kind writes in one", () => {
    expect(createsFirstRevision({ kind: "estimate", revision_id: null })).toBe(true);
    expect(createsFirstRevision({ kind: "estimate", revision_id: "r" })).toBe(false);
    expect(createsFirstRevision({ kind: "actual_costs", revision_id: null })).toBe(false);
  });
});
