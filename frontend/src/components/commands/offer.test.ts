// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { findOffer, platformOffer } from "./offer";

type Session = components["schemas"]["Session"];
type Revision = components["schemas"]["Revision"];

/** The permissions of a session of the contract. */
function permissions(name: string) {
  return (example(name) as Session).permissions;
}

describe("the offer of a command", () => {
  it("is the one the object lists, and none when it does not list the command", () => {
    const draft = example("revision") as Revision;
    const reader = example("revision_reader") as Revision;
    expect(findOffer(draft.available_commands, "mark")).toEqual({
      command: "mark",
      is_available: true,
      missing_conditions: [],
    });
    expect(findOffer(reader.available_commands, "mark")).toBeUndefined();
  });

  it("follows, outside any project, the permission of modification of the function", () => {
    const granted = { is_available: true, missing_conditions: [] };
    expect(platformOffer(permissions("session"), "users")).toEqual(granted);
    expect(platformOffer(permissions("session_without_administration"), "users")).toBeUndefined();
    expect(platformOffer(permissions("session_without_administration"), "cost_settings")).toEqual(
      granted,
    );
    expect(platformOffer(undefined, "cost_settings")).toBeUndefined();
  });

  it("follows the permission of its own for the restoration of a backup", () => {
    expect(platformOffer(permissions("session"), "platform_restore")).toEqual({
      is_available: true,
      missing_conditions: [],
    });
    // Reading and writing the backups does not grant their restoration.
    const withoutRestore = permissions("session").filter((code) => code !== "platform_restore");
    expect(withoutRestore).toContain("backups.write");
    expect(platformOffer(withoutRestore, "platform_restore")).toBeUndefined();
  });
});
