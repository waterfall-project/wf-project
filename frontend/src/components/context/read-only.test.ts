// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { availableEdits, isReadOnly, type Revision } from "./read-only";

/** A revision of the contract, by the name of its example. */
function revision(name: string): Revision {
  return example(name) as Revision;
}

describe("a revision read only", () => {
  it("is a marked one, whose commands of modification are all unavailable [WF-IHM-0020-A]", () => {
    expect(isReadOnly(revision("revision_marked"))).toBe(true);
    expect(availableEdits(revision("revision_marked"))).toEqual(new Set());
  });

  it("is not a draft whose commands of modification are available", () => {
    expect(isReadOnly(revision("revision"))).toBe(false);
    expect(availableEdits(revision("revision"))).toEqual(
      new Set(["edit_planning", "edit_estimate", "edit_remaining", "edit_risks"]),
    );
  });

  it("is a draft the caller may exercise no command of modification on", () => {
    expect(isReadOnly(revision("revision_reader"))).toBe(true);
  });

  it("is a marked one, even were a command of modification said available", () => {
    const draft = revision("revision");
    expect(isReadOnly({ ...draft, status: "marked" })).toBe(true);
  });

  it("counts only the commands of modification, not the others available", () => {
    const draft = revision("revision");
    const others = draft.available_commands.map((offered) =>
      offered.command.startsWith("edit_") ? { ...offered, is_available: false } : offered,
    );
    expect(isReadOnly({ ...draft, available_commands: others })).toBe(true);
    const planning = draft.available_commands.filter(
      (offered) => offered.command === "edit_planning",
    );
    expect(availableEdits({ ...draft, available_commands: planning })).toEqual(
      new Set(["edit_planning"]),
    );
  });
});
