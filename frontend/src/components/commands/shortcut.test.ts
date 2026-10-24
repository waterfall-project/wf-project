// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { NAMED_KEYS, shownWays } from "./shortcut";
import fr from "../../../messages/fr.json";

describe("the ways of pressing a command a workstation shows (US-0580)", () => {
  it.each([
    ["Control+Z Meta+Z", "other", [["Control", "Z"]]],
    ["Control+Z Meta+Z", "mac", [["Meta", "Z"]]],
    ["Control+Shift+Z Meta+Shift+Z", "mac", [["Meta", "Shift", "Z"]]],
    // Ctrl stands for itself on a Mac where no way with Cmd stands for it.
    ["Control+Insert", "mac", [["Control", "Insert"]]],
    ["Alt+Shift+ArrowUp", "other", [["Alt", "Shift", "ArrowUp"]]],
    // Two ways that are no workstation's: both shown.
    ["Shift+F10 ContextMenu", "other", [["Shift", "F10"], ["ContextMenu"]]],
    // Cmd alone is shown off a Mac, as nothing else presses the command.
    ["Meta+K", "other", [["Meta", "K"]]],
    ["Alt+Plus", "other", [["Alt", "Plus"]]],
  ] as const)("shows %s on %s as %j", (keys, platform, ways) => {
    expect(shownWays(keys, platform)).toEqual(ways);
  });

  it("shows nothing for no keys", () => {
    expect(shownWays(undefined, "other")).toEqual([]);
    expect(shownWays("", "mac")).toEqual([]);
  });

  it("names each key it names in the catalogue, and each modifier by its sign on a Mac", () => {
    expect(Object.keys(fr.commands.keys).sort()).toEqual([...NAMED_KEYS].sort());
    expect(Object.keys(fr.commands.macKeys).sort()).toEqual(["Alt", "Control", "Meta", "Shift"]);
  });
});
