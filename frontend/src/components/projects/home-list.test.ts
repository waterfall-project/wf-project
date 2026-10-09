// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { HOME_LIST, homeQuery } from "./home-list";

describe("what the list of the home reads of its address", () => {
  it("holds every parameter the list asks of the server, but its page: a filter under way reads another list", () => {
    const query = homeQuery({
      filtered: true,
      states: ["pricing"],
      period: { from: "2026-02-28T23:00:00.000Z", to: "2026-03-16T23:00:00.000Z" },
      query: { sort: { column: "code", order: "desc" }, search: "poste" },
      offset: 50,
    });
    const asked = Object.keys(query).filter((name) => name !== HOME_LIST.page);
    expect(asked).toHaveLength(7);
    expect(HOME_LIST.reads).toEqual(expect.arrayContaining(asked));
  });

  it("asks every state when the address names none", () => {
    const query = homeQuery({
      filtered: false,
      states: [],
      period: { from: undefined, to: undefined },
      query: { sort: undefined, search: undefined },
      offset: undefined,
    });
    expect(query).toEqual({
      states: ["created", "pricing", "in_progress", "completed", "lost", "abandoned"],
    });
  });
});
