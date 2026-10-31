// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { isContributorFiltered, isDefaultStates, readHomeStates } from "./home";

describe("the filter of the home", () => {
  it.each([
    ["", true],
    ["is_contributor=true", true],
    ["is_contributor=false", false],
  ])(
    "at the address ?%s, filters on the projects the user contributes to: %s",
    (query, filtered) => {
      expect(isContributorFiltered(new URLSearchParams(query))).toBe(filtered);
    },
  );
});

describe("the states of the home", () => {
  it.each([
    ["", undefined, ["pricing", "in_progress"]],
    ["", "completed,pricing", ["pricing", "completed"]],
    ["states=lost,created", "completed", ["created", "lost"]],
    ["states=all", "completed", []],
    ["states=", undefined, []],
    ["", "all", []],
  ])(
    "at the address ?%s, the account having kept %s, retains %j (WF-IHM-0130)",
    (query, kept, expected) => {
      expect(readHomeStates(new URLSearchParams(query), kept)).toEqual(expected);
    },
  );

  it("tells the states by default from any other choice", () => {
    expect(isDefaultStates(["in_progress", "pricing"])).toBe(true);
    expect(isDefaultStates(["pricing"])).toBe(false);
    expect(isDefaultStates([])).toBe(false);
  });
});
